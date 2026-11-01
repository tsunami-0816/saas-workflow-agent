"""python-agent：saas-workflow-agent 的 Agent 运行时服务（L5 链路）。

职责：接收 java-backend DAG 引擎的 Agent 任务（POST /agent/run），
经 LangGraph 状态机编排三角色（规划者/执行者/审核者）执行，
LLM 调用统一经 java-backend /internal/llm/chat 出口（禁止直连 LLM 厂商）。

R2 降级：不再依赖 CrewAI（原 crewai 1.15.30 与 fastapi/langgraph 依赖冲突，
且 MVP 三角色仅需「带身份调一次 LLM」，已在 agents.run_role 直接实现）。
"""

__version__ = "1.0.0"
