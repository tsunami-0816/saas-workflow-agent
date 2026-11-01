"""POST /agent/run 接口契约（PY-1.2）。

入参 = 任务描述 + 上下文（executionId / nodeId / 输入数据 / 约束）；
出参 = 结构化结果（状态 / 输出 / ReAct 推理链步骤）。

命名约定：Python 字段 snake_case（规范 §6.2），JSON 一律 camelCase
（与 java 调用方对齐），由 pydantic alias 自动双向转换；
FastAPI 默认 response_model_by_alias=True，响应序列化为 camelCase。
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """基类：接受 camelCase / snake_case 入参，序列化输出 camelCase。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AgentRunRequest(CamelModel):
    """/agent/run 入参（java DAG 引擎 BE-4.8 Agent 任务节点调用）。"""

    execution_id: str = Field(min_length=1, max_length=64,
                              description="执行实例 ID（java 引擎生成；兼作日志 traceId）")
    node_id: str = Field(min_length=1, max_length=64, description="DAG 节点 ID")
    task: str = Field(min_length=1, max_length=8000, description="任务描述（自然语言）")
    input_data: dict[str, Any] = Field(default_factory=dict,
                                       description="上游节点输出 / 本节点输入数据")
    constraints: dict[str, Any] = Field(default_factory=dict,
                                        description="执行约束（格式/禁止事项/超时等业务约束）")
    task_type: str | None = Field(default=None, max_length=64,
                                  description="LLM 路由 taskType；缺省用服务端 LLM_TASK_TYPE")
    tenant_id: int | None = Field(default=None,
                                  description="租户 ID（java 引擎透传）；调 /internal/llm/chat 时带 "
                                              "X-Tenant-Id 头，启用额度扣减与台账归租；缺省 java 侧记 0 占位")


class ReasoningStep(CamelModel):
    """ReAct 推理链单步（前端按此逐条展示，PY-1.4）。

    映射：thought=本步意图，action=执行动作（角色.kickoff / llm.chat），
    observation=动作产出（LLM 原文）。
    """

    step: int = Field(ge=1, description="步骤序号（从 1 递增）")
    node: str = Field(description="产生本步的图节点：planner / executor / reviewer")
    thought: str = Field(description="本步意图（ReAct 的 Thought）")
    action: str = Field(description="本步动作（ReAct 的 Action）")
    observation: str = Field(description="动作结果（ReAct 的 Observation）")


class AgentRunResponse(CamelModel):
    """/agent/run 出参。

    口径（假设，第 7 步与 java 对齐）：接口恒返回 HTTP 200，成败看 status 字段；
    java BE-4.8 据 status=FAILED 按节点失败处理并写 retry_log。
    """

    execution_id: str
    node_id: str
    status: Literal["SUCCESS", "FAILED"]
    output: dict[str, Any] = Field(default_factory=dict,
                                   description="结构化输出：plan/result/review/final（成功时）")
    reasoning: list[ReasoningStep] = Field(default_factory=list,
                                           description="ReAct 推理链（含失败前的部分步骤）")
    error: str | None = Field(default=None, description="失败原因（status=FAILED 时非空）")
    duration_ms: int = Field(ge=0, description="本次执行耗时（毫秒）")
