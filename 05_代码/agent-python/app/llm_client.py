"""LLM 统一出口客户端（PY-1.5，链路 L5/L6）。

铁律：python-agent 禁止直连任何 LLM 厂商（DeepSeek/OpenAI/Claude），
所有 LLM 请求统一走 java-backend 模型路由层：
    POST {JAVA_BACKEND_URL}/internal/llm/chat
超时 60s（可配），失败一律抛 LLMGatewayError 上抛 —— java 侧据此记 retry_log。

接口契约（与 java BE-6.1 对齐，假设点见下）：
    请求  {"taskType": str, "messages": [{"role","content"}...],
           "temperature": float, "maxTokens": int}
    响应  java 统一壳 {"code","message","data"}，
          data = {"content": str, "model": str?, "usage": {...}?}
假设（第 7 步联调需与 java 核对一处常量）：
    统一壳成功码口径按 BE-1.1 尚未钉死，本客户端兼容 code==0 或 code==200 视为成功。
"""
from __future__ import annotations

from typing import Any

import httpx

# java 统一响应壳成功码（假设：0 或 200 均为成功；第 7 步联调与 BE-1.1 口径核对）
_SUCCESS_CODES = {0, 200}


class LLMGatewayError(RuntimeError):
    """LLM 网关调用失败（超时/网络/非 2xx/业务码非成功/响应缺字段）。

    必须上抛：调用方（图节点）捕获后记 FAILED，java 侧按节点失败写 retry_log（PY-1.5）。
    """


class JavaLLMClient:
    """java /internal/llm/chat 同步客户端（httpx.Client 连接复用）。"""

    def __init__(self, base_url: str, timeout_seconds: float = 60.0,
                 internal_api_token: str = "") -> None:
        """入参：base_url=java-backend 地址；timeout_seconds=单次调用超时（架构口径 60s）；
                internal_api_token=内部接口令牌（/internal/** 必须带 X-Internal-Token，否则 401）。"""
        self._timeout = timeout_seconds
        headers = {"X-Internal-Token": internal_api_token} if internal_api_token else {}
        self._client = httpx.Client(base_url=base_url, timeout=timeout_seconds, headers=headers)

    def chat(
        self,
        messages: list[dict[str, str]],
        task_type: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tenant_id: int | None = None,
    ) -> str:
        """发起一次对话补全。

        入参：messages OpenAI 风格消息列表；task_type 供 java 模型路由层选 provider；
              temperature/max_tokens 为 None 时不传（由 java 侧默认）；
              tenant_id 非 None 时带 X-Tenant-Id 头（java 侧据此扣额度/台账归租，
              缺省 java 记 tenantId=0 占位并跳过扣减）。
        出参：LLM 文本内容（data.content）。
        异常：LLMGatewayError（超时/网络错误/HTTP 非 2xx/业务失败/响应结构缺失）。
        """
        payload: dict[str, Any] = {"taskType": task_type, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["maxTokens"] = max_tokens
        headers = {"X-Tenant-Id": str(tenant_id)} if tenant_id is not None else None

        try:
            resp = self._client.post("/internal/llm/chat", json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMGatewayError(f"LLM 网关超时（>{self._timeout:g}s）: {exc!r}") from exc
        except httpx.HTTPError as exc:
            raise LLMGatewayError(f"LLM 网关网络错误: {exc!r}") from exc

        if resp.status_code != 200:
            raise LLMGatewayError(
                f"LLM 网关 HTTP {resp.status_code}: {resp.text[:300]}"
            )

        try:
            body = resp.json()
        except ValueError as exc:
            raise LLMGatewayError(f"LLM 网关响应非 JSON: {resp.text[:300]}") from exc

        code = body.get("code")
        if code not in _SUCCESS_CODES:
            raise LLMGatewayError(f"LLM 网关业务失败 code={code} message={body.get('message')}")

        data = body.get("data") or {}
        content = data.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMGatewayError("LLM 网关响应缺少 data.content 或内容为空")
        return content

    def close(self) -> None:
        """关闭底层连接池（应用 shutdown 时调用）。"""
        self._client.close()
