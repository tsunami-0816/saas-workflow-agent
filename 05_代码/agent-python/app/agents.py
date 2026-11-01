"""三角色编排（PY-1.3，按架构 R2 预案降级实现）：
规划者 Planner / 执行者 Executor / 审核者 Reviewer。

R2 降级说明：原方案依赖 CrewAI 1.15.30，但其传递依赖（cel-python/mcp 等）
与 fastapi/langgraph 反复冲突，且 MVP 阶段三角色仅需「以某身份调一次 LLM」，
CrewAI 的 Agent+Task+Crew 抽象在此场景是壳。降级为：
  - 直接用 JavaLLMClient.chat()，把 role/goal/backstory 拼成 system message；
  - 三节点先后顺序仍由 LangGraph 状态机编排（graph.py），保证推理链可观测；
  - python 不直连 LLM 厂商的铁律不变（仍走 java 网关 /internal/llm/chat）。
"""
from __future__ import annotations

from app.llm_client import JavaLLMClient

# 三角色定义（角色名保留中英文，便于前端推理链展示辨认，PY-1.3 验收「三角色分工产出可辨」）
ROLE_PLANNER: dict[str, str] = {
    "role": "规划者 Planner",
    "goal": "把用户任务拆解为清晰、可执行、可验证的分步计划",
    "backstory": "你是资深方案规划专家，擅长把模糊任务结构化为有序步骤，并指出关键风险与依赖。",
}
ROLE_EXECUTOR: dict[str, str] = {
    "role": "执行者 Executor",
    "goal": "严格按照计划逐步执行，产出完整、可直接使用的结果",
    "backstory": "你是严谨的执行专家，忠实执行既定计划，不省略步骤，遇到约束会显式说明处理方式。",
}
ROLE_REVIEWER: dict[str, str] = {
    "role": "审核者 Reviewer",
    "goal": "审核执行结果的正确性/完整性/约束符合度，并给出修订后的最终交付",
    "backstory": "你是挑剔的质量审核专家，能发现结果中的错误与遗漏，并输出修订后的最终版本。",
}


def run_role(
    role_cfg: dict[str, str],
    client: JavaLLMClient,
    task_description: str,
    expected_output: str,
    task_type: str,
    tenant_id: int | None = None,
) -> str:
    """以单个角色身份调一次 LLM（R2 降级实现）。

    入参：role_cfg 角色定义（role/goal/backstory）；client=java LLM 网关客户端；
          task_description 任务描述；expected_output 期望产出说明；
          task_type=java 路由类型；tenant_id 透传 X-Tenant-Id。
    出参：该角色的 LLM 产出原文。
    异常：底层 LLMGatewayError 等异常直接上抛，由 graph 节点兜底记 FAILED。
    """
    system = (
        f"你现在扮演{role_cfg['role']}。\n"
        f"目标：{role_cfg['goal']}\n"
        f"背景：{role_cfg['backstory']}\n"
        f"产出要求：{expected_output}\n"
        "请严格按角色身份与目标输出，不要暴露你是 AI，不要寒暄。"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task_description},
    ]
    return client.chat(messages, task_type=task_type, tenant_id=tenant_id)
