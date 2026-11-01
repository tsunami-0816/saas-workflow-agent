from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class AgentRequest(BaseModel):
    task: str

@app.post("/api/agent/plan")
def plan(req: AgentRequest):
    return {
        "steps": ["1. 理解需求", "2. 拆解子任务", "3. 执行并验证"],
        "summary": f"已为任务「{req.task}」生成3步计划",
        "agent": "CrewAI(规划者+执行者+审核者)"
    }

@app.get("/api/llm/models")
def list_models():
    return {
        "models": [
            {"provider": "deepseek", "model": "deepseek-chat", "cost_per_1k_tokens": 0.001},
            {"provider": "openai", "model": "gpt-3.5-turbo", "cost_per_1k_tokens": 0.002},
            {"provider": "claude", "model": "claude-3-haiku", "cost_per_1k_tokens": 0.0008}
        ],
        "routing_rule": "简单任务→deepseek，复杂任务→gpt-4"
    }
