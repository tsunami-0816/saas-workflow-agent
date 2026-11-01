"""L1 单元测试：python-agent 纯函数/契约类（不碰 DB/HTTP）。

java 侧 DSL 校验器为强类型实现，无 JUnit 单测（第 5A 步未建），
其行为由 L2 接口用例（保存版本接口）间接覆盖，报告「未覆盖说明」已登记。
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.l1


def test_llm_client_success_codes_and_error_type():
    """统一壳成功码兼容 0/200；网关异常必须是 RuntimeError 子类（图节点按异常兜底）。"""
    from app.llm_client import _SUCCESS_CODES, LLMGatewayError

    assert _SUCCESS_CODES == {0, 200}
    assert issubclass(LLMGatewayError, RuntimeError)


def test_agent_run_request_camel_alias_roundtrip():
    """AgentRunRequest 必须接受 camelCase 入参并回显 camelCase（java 侧契约）。"""
    from app.schemas import AgentRunRequest

    req = AgentRunRequest(**{"executionId": "e1", "nodeId": "n1", "task": "任务",
                             "inputData": {"a": 1}, "tenantId": 1})
    assert req.execution_id == "e1"
    assert req.node_id == "n1"
    assert req.tenant_id == 1

    dumped = req.model_dump(by_alias=True)
    assert dumped["executionId"] == "e1" and dumped["tenantId"] == 1

    # 缺省 tenantId 时不应报错（java 未透传的兼容路径）
    req2 = AgentRunRequest(**{"executionId": "e2", "nodeId": "n2", "task": "任务"})
    assert req2.tenant_id is None


def test_agent_run_request_rejects_blank_task():
    """空 task 必须在入口被拒（400），不能把空任务送进 CrewAI。"""
    from pydantic import ValidationError

    from app.schemas import AgentRunRequest

    with pytest.raises(ValidationError):
        AgentRunRequest(**{"executionId": "e1", "nodeId": "n1", "task": ""})


def test_langgraph_state_step_and_fail_semantics():
    """R2 降级后：LangGraph 节点纯函数口径（_step 序号递增、_fail 短路并写推理链、initial_state 置 RUNNING）。"""
    from app.graph import _fail, _step, _to_json, initial_state
    from app.schemas import AgentRunRequest

    state = {"reasoning": [{"step": 1}]}
    step = _step(state, "executor", "按计划执行", "Executor.run_role", "draft")
    assert step["step"] == 2, f"step 序号应等于已有步数+1，实际 {step['step']}"

    failed = _fail({"reasoning": [{"step": 1}]}, "reviewer", RuntimeError("boom"))
    assert failed["status"] == "FAILED"
    assert failed["error"].startswith("reviewer:")
    assert len(failed["reasoning"]) == 1, "失败也要写入推理链，便于前端定位断点"

    st = initial_state(AgentRunRequest(**{"executionId": "e1", "nodeId": "n1", "task": "t"}))
    assert st["status"] == "RUNNING" and st["reasoning"] == [] and st["tenant_id"] is None

    assert _to_json({"中文": "值"}) == '{"中文": "值"}', "上下文 JSON 必须保留中文（ensure_ascii=False）"


def test_reasoning_step_requires_positive_step():
    """ReAct 推理链 step 必须从 1 起（前端按序号渲染）。"""
    from pydantic import ValidationError

    from app.schemas import ReasoningStep

    ok = ReasoningStep(step=1, node="planner", thought="t", action="a", observation="o")
    assert ok.step == 1
    with pytest.raises(ValidationError):
        ReasoningStep(step=0, node="planner", thought="t", action="a", observation="o")
