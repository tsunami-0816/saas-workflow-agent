"""requests 封装：自动带 token、统一打请求/响应日志（L2/L3/L4 共用）。"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

_LOGS: list[dict[str, Any]] = []


def request_logs() -> list[dict[str, Any]]:
    """返回本次进程内已记录的请求日志（测试报告可与用例失败一起取证）。"""
    return list(_LOGS)


class ApiClient:
    """单个角色的 HTTP 客户端（httpx.Client 连接复用）。"""

    def __init__(self, base_url: str, token: str | None = None, timeout: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def with_token(self, token: str) -> "ApiClient":
        """返回共享连接的另一个 token 客户端（用于同用例内切换角色）。"""
        c = ApiClient(self.base_url, token, timeout=self._client.timeout.read or 30)
        c.token = token
        return c

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        if self.token:
            headers.setdefault("Authorization", f"Bearer {self.token}")
        start = time.monotonic()
        resp = self._client.request(method, path, headers=headers, **kwargs)
        elapsed = round((time.monotonic() - start) * 1000)
        _LOGS.append({
            "method": method.upper(), "path": path, "status": resp.status_code,
            "elapsed_ms": elapsed, "body": _safe_text(resp),
        })
        return resp

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        return self.request("DELETE", path, **kwargs)

    def close(self) -> None:
        self._client.close()


def _safe_text(resp: httpx.Response) -> str:
    try:
        return resp.text[:800]
    except Exception:
        return "<unreadable>"


def login(base_url: str, username: str, password: str, timeout: float = 15) -> dict[str, Any]:
    """登录并返回统一响应体；调用方断言 code。"""
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout) as c:
        resp = c.post("/api/v1/auth/login", json={"username": username, "password": password})
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        body.setdefault("_http_status", resp.status_code)
        return body


def jbody(resp: httpx.Response) -> dict[str, Any]:
    """取 JSON body；非 JSON 时返回 {"_raw": text, "_http_status": status}（便于失败取证）。"""
    try:
        body = resp.json()
    except json.JSONDecodeError:
        return {"_raw": resp.text[:500], "_http_status": resp.status_code}
    body.setdefault("_http_status", resp.status_code)
    return body
