"""LangGraph 状态机包装执行流程 + ReAct 推理链（PY-1.4）。

状态机：planner → executor → reviewer → END（任一节点 FAILED 直接短路到 END）。
每个节点把 ReAct 步骤（thought/action/observation）追加进 state["reasoning"]，
经 operator.add reducer 累积，最终整体写入 /agent/run 响应，供前端展示推理链。

R2 降级后：节点直接用 JavaLLMClient（经 agents.run_role 带角色 system prompt），
不再依赖 CrewAI / JavaGatewayLLM。
"""
from __future__ import annotations

import json
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger

from app.agents import ROLE_EXECUTOR, ROLE_PLANNER, ROLE_REVIEWER, run_role
from app.config import Settings
from app.llm_client import JavaLLMClient
from app.schemas import AgentRunRequest


class AgentState(TypedDict, total=False):
    """图执行状态（LangGraph 节点间传递；reasoning 经 reducer 累积）。"""

    execution_id: str
    node_id: str
    task: str
    input_data: dict[str, Any]
    constraints: dict[str, Any]
    task_type: str | None
    tenant_id: int | None  # java 引擎透传；LLM 调用带 X-Tenant-Id（额度扣减/台账归租）
    plan: str  # planner 产出
    draft: str  # executor 产出
    review: str  # reviewer 产出（最终交付）
    status: str  # RUNNING / SUCCESS / FAILED
    error: str | None
    reasoning: Annotated[list[dict[str, Any]], operator.add]  # ReAct 链（累积）


def _to_json(data: dict[str, Any]) -> str:
    """上下文 JSON 化（ensure_ascii=False 保中文，default=str 防不可序列化对象炸图）。"""
    return json.dumps(data, ensure_ascii=False, default=str)


def _step(state: AgentState, node: str, thought: str, action: str, observation: str) -> dict[str, Any]:
    """构造一条 ReAct 步骤，step 序号 = 已有步数 + 1。"""
    return {
        "step": len(state.get("reasoning", [])) + 1,
        "node": node,
        "thought": thought,
        "action": action,
        "observation": observation,
    }


def _fail(state: AgentState, node: str, exc: Exception) -> dict[str, Any]:
    """节点失败统一口径：记 FAILED + error，并把失败本身也写入推理链（便于前端定位断点）。"""
    logger.error("节点 {} 失败: {!r}", node, exc)
    return {
        "status": "FAILED",
        "error": f"{node}: {exc!r}",
        "reasoning": [_step(state, node, "本节点执行失败，链路短路终止", "raise", repr(exc))],
    }


def build_agent_graph(llm_client: JavaLLMClient, settings: Settings):
    """构建并编译 Agent 执行状态机（服务启动时构建一次，全局复用）。

    入参：llm_client=java LLM 网关客户端；settings=运行配置。
    出参：编译后的 LangGraph Runnable，`invoke(initial_state) -> AgentState`。
    注意：节点闭包共享 llm_client（httpx.Client 线程安全，FastAPI sync 路由跑在线程池）。
    """

    def planner_node(state: AgentState) -> dict[str, Any]:
        """规划者节点：任务 + 输入 + 约束 → 分步计划。"""
        try:
            desc = (
                f"【任务】{state['task']}\n"
                f"【输入数据】{_to_json(state.get('input_data') or {})}\n"
                f"【约束】{_to_json(state.get('constraints') or {})}\n"
                "请输出分步执行计划（编号列表），每步说明目标与验收要点。"
            )
            plan = run_role(ROLE_PLANNER, llm_client, desc,
                            "分步执行计划（Markdown 编号列表）",
                            state.get("task_type") or settings.llm_task_type,
                            state.get("tenant_id"))
            logger.info("planner 完成，计划长度={}", len(plan))
            return {"plan": plan, "reasoning": [
                _step(state, "planner", "先理解任务与约束，制定分步执行计划",
                      "Planner.run_role", plan)]}
        except Exception as exc:  # noqa: BLE001 —— 图节点兜底，失败结构化上抛给 java
            return _fail(state, "planner", exc)

    def executor_node(state: AgentState) -> dict[str, Any]:
        """执行者节点：按计划执行 → 结果草稿。"""
        try:
            desc = (
                f"【任务】{state['task']}\n"
                f"【执行计划】\n{state['plan']}\n"
                f"【输入数据】{_to_json(state.get('input_data') or {})}\n"
                f"【约束】{_to_json(state.get('constraints') or {})}\n"
                "请严格按计划逐步执行，输出完整结果。"
            )
            draft = run_role(ROLE_EXECUTOR, llm_client, desc,
                             "按计划执行的完整结果",
                             state.get("task_type") or settings.llm_task_type,
                             state.get("tenant_id"))
            logger.info("executor 完成，草稿长度={}", len(draft))
            return {"draft": draft, "reasoning": [
                _step(state, "executor", "按计划逐步执行，产出结果草稿",
                      "Executor.run_role", draft)]}
        except Exception as exc:  # noqa: BLE001
            return _fail(state, "executor", exc)

    def reviewer_node(state: AgentState) -> dict[str, Any]:
        """审核者节点：审核草稿 → 修订后的最终交付；全链完成置 SUCCESS。"""
        try:
            desc = (
                f"【任务】{state['task']}\n"
                f"【约束】{_to_json(state.get('constraints') or {})}\n"
                f"【执行计划】\n{state['plan']}\n"
                f"【执行结果草稿】\n{state['draft']}\n"
                "请审核草稿的正确性、完整性与约束符合度；若有错误/遗漏直接修订，"
                "输出最终交付版本（不要只写评语）。"
            )
            review = run_role(ROLE_REVIEWER, llm_client, desc,
                              "审核并修订后的最终交付版本",
                              state.get("task_type") or settings.llm_task_type,
                              state.get("tenant_id"))
            logger.info("reviewer 完成，最终产出长度={}", len(review))
            return {"review": review, "status": "SUCCESS", "reasoning": [
                _step(state, "reviewer", "审核结果正确性/完整性/约束符合度，输出最终交付",
                      "Reviewer.run_role", review)]}
        except Exception as exc:  # noqa: BLE001
            return _fail(state, "reviewer", exc)

    def _route(state: AgentState) -> str:
        """条件路由：FAILED 短路到 END，否则顺序推进。"""
        return "abort" if state.get("status") == "FAILED" else "continue"

    sg = StateGraph(AgentState)
    sg.add_node("planner", planner_node)
    sg.add_node("executor", executor_node)
    sg.add_node("reviewer", reviewer_node)
    sg.set_entry_point("planner")
    sg.add_conditional_edges("planner", _route, {"continue": "executor", "abort": END})
    sg.add_conditional_edges("executor", _route, {"continue": "reviewer", "abort": END})
    sg.add_edge("reviewer", END)
    return sg.compile()


def initial_state(req: AgentRunRequest) -> AgentState:
    """由请求构造图初始状态。"""
    return AgentState(
        execution_id=req.execution_id,
        node_id=req.node_id,
        task=req.task,
        input_data=req.input_data,
        constraints=req.constraints,
        task_type=req.task_type,
        tenant_id=req.tenant_id,
        status="RUNNING",
        error=None,
        reasoning=[],
    )
