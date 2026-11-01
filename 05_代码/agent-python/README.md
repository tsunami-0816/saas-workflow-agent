# python-agent（Agent 运行时服务，:8085）

saas-workflow-agent 链路 L5 的 Agent 运行时：接收 java-backend DAG 引擎的 Agent 任务，
经 **LangGraph 状态机** 编排 **CrewAI 三角色**（规划者 Planner → 执行者 Executor → 审核者 Reviewer）执行，
产出结构化结果与 **ReAct 推理链**（前端逐步展示）。

**铁律：本服务不直连任何 LLM 厂商**，所有 LLM 调用统一走
`POST {JAVA_BACKEND_URL}/internal/llm/chat`（java 模型路由层，超时 60s，失败上抛由 java 记 retry_log）。

## 目录结构

```
agent-python/
├── requirements.txt      # 钉死版本（dependency_checker 已机器校验，勿改）
├── .env.example          # 配置样例（密钥/地址全走环境变量）
└── app/
    ├── main.py           # FastAPI 入口：/health、/agent/run（自动产出 /openapi.json）
    ├── config.py         # 环境变量配置
    ├── logging_config.py # loguru 结构化日志（traceId=executionId）
    ├── schemas.py        # /agent/run 契约（Pydantic，JSON camelCase）
    ├── llm_client.py     # java /internal/llm/chat 客户端（httpx，60s 超时）
    ├── crew_llm.py       # CrewAI BaseLLM 适配器 → java 网关
    ├── agents.py         # CrewAI 三角色定义与单角色执行
    └── graph.py          # LangGraph 状态机（planner→executor→reviewer）+ ReAct 链
```

## 启动

```bash
pip install -r requirements.txt   # Python ≥3.10（本机 3.11 实测）
cp .env.example .env              # 按需修改（也可直接设环境变量）

# Windows 实测启动命令（读取 .env；uvicorn --env-file 依赖 python-dotenv，crewai 传递依赖已带）
.\.venv\Scripts\python.exe -u -m uvicorn app.main:app --env-file .env --host 0.0.0.0 --port 8085
```

> 本服务用 `os.getenv` 读配置，**`.env` 不会自动加载**：要么用上面的 `--env-file .env`，
> 要么先在 shell 里 export 同名变量。便捷方式 `python -m app.main` 同样只读进程环境变量。

## 配置说明

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `JAVA_BACKEND_URL` | `http://localhost:8083` | java-backend 地址（LLM 统一出口） |
| `AGENT_HOST` / `AGENT_PORT` | `0.0.0.0` / `8085` | 监听地址/端口 |
| `LOG_LEVEL` | `INFO` | loguru 级别 |
| `LLM_TIMEOUT_SECONDS` | `60` | python→java LLM 网关超时（架构口径 60s） |
| `LLM_TASK_TYPE` | `agent_reasoning` | 默认 LLM 路由 taskType |
| `LLM_MAX_TOKENS` / `LLM_TEMPERATURE` | `2048` / `0.3` | 单次调用采样参数 |
| `INTERNAL_API_TOKEN` | 空 | java `/internal/**` 内部令牌（须与 java 侧一致） |
| `CREWAI_CONFIG_DIR` | `./crewai_data` | CrewAI 配置目录。crewai 在 import 阶段会对该目录做 `tempfile.mkstemp` 写探测；默认 `~/.config/crewai` 在 Windows 受限目录策略下该探测会长期阻塞导致 `import crewai` 卡死，故必须指向可写目录 |
| `CREWAI_STORAGE_DIR` | `./crewai_data/storage` | CrewAI 长期记忆存储目录（本服务 `memory=False`，仅作防御性设置） |

## 接口

### `GET /health`
返回 `{"status":"UP","service":"python-agent","version":"1.0.0"}`。

### `POST /agent/run`
入参（JSON，camelCase；snake_case 亦兼容）：

```json
{
  "executionId": "exec-1001",
  "nodeId": "node-agent-1",
  "task": "为新品发布会写一份 200 字宣传文案",
  "inputData": {"product": "智能台灯"},
  "constraints": {"tone": "活泼", "forbid": "夸大宣传"},
  "taskType": "agent_reasoning"
}
```

出参（恒 HTTP 200，成败看 `status`；java BE-4.8 据 `FAILED` 记 retry_log）：

```json
{
  "executionId": "exec-1001",
  "nodeId": "node-agent-1",
  "status": "SUCCESS",
  "output": {"plan": "...", "result": "...", "review": "...", "final": "..."},
  "reasoning": [
    {"step": 1, "node": "planner",  "thought": "...", "action": "Planner.kickoff",  "observation": "..."},
    {"step": 2, "node": "executor", "thought": "...", "action": "Executor.kickoff", "observation": "..."},
    {"step": 3, "node": "reviewer", "thought": "...", "action": "Reviewer.kickoff", "observation": "..."}
  ],
  "error": null,
  "durationMs": 8421
}
```

`/openapi.json` 由 FastAPI 自动产出，供第 6.5 步契约校验。

## 自测

```bash
# 1) 探活（无需 java-backend）
curl http://localhost:8085/health

# 2) 契约结构自测（需 java-backend /internal/llm/chat 可用；不可用时应返回 status=FAILED 且 error 指明网关原因）
curl -X POST http://localhost:8085/agent/run -H "Content-Type: application/json" -d "{\"executionId\":\"exec-t1\",\"nodeId\":\"n1\",\"task\":\"用一句话介绍 SaaS 工作流平台\"}"

# 3) OpenAPI 契约
curl http://localhost:8085/openapi.json
```

## 联调假设点（第 7 步与 java 侧核对）

1. java 统一响应壳成功码：本服务兼容 `code==0` 或 `code==200` 视为成功（`llm_client.py::_SUCCESS_CODES`）。
2. LLM 网关响应体：`data.content` 为 assistant 文本（`data.model`/`data.usage` 可选，未强依赖）。
3. `/agent/run` 恒返回 HTTP 200 + `status` 字段判定成败（未用 5xx 表达业务失败），以便保留失败前推理链。
4. CrewAI 1.15.30 / LangGraph 1.2.18 API 假设见 `crew_llm.py`、`agents.py`、`graph.py` 模块 docstring，
   第 6 步装依赖后若实测不符，仅需适配对应模块。
