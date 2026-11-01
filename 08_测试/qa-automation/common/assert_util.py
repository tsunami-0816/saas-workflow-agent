"""统一返回体断言（本项目统一壳：code=0 成功；HTTP 状态由 GlobalExceptionHandler 映射）。"""
from __future__ import annotations

from typing import Any

import httpx


def assert_ok(resp: httpx.Response, note: str = "") -> dict[str, Any]:
    """断言 HTTP 200 + 业务 code==0，返回 data。"""
    assert resp.status_code == 200, f"{note} 期望 HTTP 200，实际 {resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert body.get("code") == 0, f"{note} 期望 code=0，实际 {body.get('code')}: {body.get('message')}"
    return body.get("data")


def assert_code(resp: httpx.Response, code: int, note: str = "") -> dict[str, Any]:
    """断言业务错误码（HTTP 状态不限，异常映射由各用例单独断言）。"""
    body = resp.json()
    assert body.get("code") == code, f"{note} 期望 code={code}，实际 {body.get('code')}: {body.get('message')}"
    return body


def assert_http(resp: httpx.Response, status: int, note: str = "") -> dict[str, Any]:
    assert resp.status_code == status, f"{note} 期望 HTTP {status}，实际 {resp.status_code}: {resp.text[:300]}"
    try:
        return resp.json()
    except Exception:
        return {}


def assert_fields(data: dict[str, Any] | None, **expected) -> None:
    """断言 data 关键字段（值相等）；用于不只断言 code==0 的场合。"""
    assert isinstance(data, dict), f"data 不是对象: {data!r}"
    for key, value in expected.items():
        assert data.get(key) == value, f"字段 {key} 期望 {value!r}，实际 {data.get(key)!r}"


def assert_contains(data: Any, *keys: str) -> None:
    """断言对象/列表文本包含指定键或子串（用于列表/嵌套结构的关键字段存在性）。"""
    text = str(data)
    for key in keys:
        assert key in text, f"返回体中缺少 {key!r}: {text[:300]}"
