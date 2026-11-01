"""环境变量配置（PY-1.1 / 规范 §6.4）。

注意：requirements.txt 未包含 pydantic-settings，统一用 os.getenv 读取；
密钥/地址禁止硬编码，新增 env key 必须同步 .env.example。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """服务运行配置（全部来自环境变量，均有开发默认值）。"""

    host: str  # 监听地址
    port: int  # 监听端口（架构口径 8085）
    log_level: str  # loguru 日志级别
    java_backend_url: str  # java-backend 基础地址（LLM 统一出口）
    llm_timeout_seconds: float  # python→java /internal/llm/chat 超时（架构口径 60s）
    llm_task_type: str  # 默认 LLM 路由 taskType（java 模型路由层按它选 provider）
    llm_max_tokens: int  # 单次 LLM 调用 maxTokens 上限
    llm_temperature: float  # 单次 LLM 调用温度
    internal_api_token: str  # java /internal/** 内部接口令牌（BE-1.5 X-Internal-Token）


def get_settings() -> Settings:
    """读取环境变量构造配置。

    出参：Settings 不可变实例。
    注意：java_backend_url 去掉结尾斜杠，避免拼接出双斜杠。
    """
    return Settings(
        host=os.getenv("AGENT_HOST", "0.0.0.0"),
        port=int(os.getenv("AGENT_PORT", "8085")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        java_backend_url=os.getenv("JAVA_BACKEND_URL", "http://localhost:8083").rstrip("/"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        llm_task_type=os.getenv("LLM_TASK_TYPE", "agent_reasoning"),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        internal_api_token=os.getenv("INTERNAL_API_TOKEN", ""),
    )
