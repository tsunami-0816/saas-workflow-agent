"""loguru 结构化日志配置（PY-1.1 / 规范 §6.5）。

口径：traceId = executionId，全链串联（java logback 同口径）。
用法：请求入口处 `logger.contextualize(traceId=req.execution_id)`，
其后续日志自动携带 traceId；无上下文的启动日志 traceId 显示为 "-"。
"""
from __future__ import annotations

import sys

from loguru import logger

_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | traceId={extra[traceId]} "
    "| {name}:{function}:{line} | {message}"
)


def setup_logging(level: str = "INFO") -> None:
    """初始化 loguru：移除默认 sink，输出到 stdout（容器/终端均可采集）。

    入参：level 日志级别字符串（DEBUG/INFO/...）。
    注意：禁止打印密钥与凭据明文（规范 §6.5）。
    """
    logger.remove()
    logger.configure(extra={"traceId": "-"})  # 无请求上下文时的占位，避免 extra KeyError
    logger.add(sys.stdout, level=level.upper(), format=_LOG_FORMAT, enqueue=True, backtrace=False)
