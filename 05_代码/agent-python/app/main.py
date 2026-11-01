"""FastAPI 入口（PY-1.1/PY-1.2）。

- GET  /health       探活（PY-1.1；compose/第 6 步冒烟用）
- POST /agent/run    Agent 执行（PY-1.2；java BE-4.8 调用，java 侧超时 120s）
- GET  /openapi.json FastAPI 自动产出（第 6.5 步契约校验用）

启动：uvicorn app.main:app --host 0.0.0.0 --port 8085
注意：/agent/run 为同步 def 路由，Starlette 自动放线程池执行，
避免 CrewAI/LangGraph 的同步阻塞调用卡住事件循环。
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from loguru import logger

from app import __version__
from app.config import get_settings
from app.graph import build_agent_graph, initial_state
from app.llm_client import JavaLLMClient
from app.logging_config import setup_logging
from app.schemas import AgentRunRequest, AgentRunResponse, ReasoningStep

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动建图与网关客户端，shutdown 释放连接池。"""
    app.state.llm_client = JavaLLMClient(settings.java_backend_url, settings.llm_timeout_seconds,
                                         settings.internal_api_token)
    app.state.graph = build_agent_graph(app.state.llm_client, settings)
    logger.info("python-agent 启动完成 port={} javaBackend={}", settings.port, settings.java_backend_url)
    yield
    app.state.llm_client.close()
    logger.info("python-agent 已停止")


app = FastAPI(
    title="saas-workflow-agent python-agent",
    version=__version__,
    description="Agent 运行时服务：CrewAI 三角色 + LangGraph 状态机 + ReAct 推理链；"
                "LLM 统一走 java-backend /internal/llm/chat。",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    """探活接口（PY-1.1）。出参：{"status":"UP","service":"python-agent","version":...}"""
    return {"status": "UP", "service": "python-agent", "version": __version__}


@app.post("/agent/run", response_model=AgentRunResponse)
def agent_run(req: AgentRunRequest, request: Request) -> AgentRunResponse:
    """执行 Agent 任务（PY-1.2~1.4）。

    入参：AgentRunRequest（executionId/nodeId/task/inputData/constraints/taskType）。
    出参：AgentRunResponse（status/output/reasoning/error/durationMs）。
    口径：恒返回 HTTP 200，成败看 status；LLM 网关等失败记 status=FAILED +
          error + 失败前的部分推理链，java BE-4.8 据此按节点失败处理写 retry_log。
    """
    started = time.monotonic()
    with logger.contextualize(traceId=req.execution_id):  # traceId=executionId 全链串联
        logger.info("收到 agent 任务 nodeId={} task={!r}", req.node_id, req.task[:120])
        try:
            final = request.app.state.graph.invoke(initial_state(req))
        except Exception as exc:  # noqa: BLE001 —— 图外兜底（理论上节点已自兜底）
            logger.exception("agent 图执行异常")
            return AgentRunResponse(
                execution_id=req.execution_id, node_id=req.node_id, status="FAILED",
                error=f"graph: {exc!r}", reasoning=[],
                duration_ms=int((time.monotonic() - started) * 1000))

        status = final.get("status", "FAILED")
        error = final.get("error")
        output = (
            {"plan": final.get("plan", ""), "result": final.get("draft", ""),
             "review": final.get("review", ""), "final": final.get("review", "")}
            if status == "SUCCESS" else {}
        )
        reasoning = [ReasoningStep(**s) for s in final.get("reasoning", [])]
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info("agent 任务结束 status={} durationMs={} steps={}", status, duration_ms, len(reasoning))
        return AgentRunResponse(
            execution_id=req.execution_id, node_id=req.node_id, status=status,
            output=output, reasoning=reasoning, error=error, duration_ms=duration_ms)


if __name__ == "__main__":
    # 便捷自测入口：python -m app.main（正式启动建议用 README 中的 uvicorn 命令）
    uvicorn.run("app.main:app", host=settings.host, port=settings.port)
