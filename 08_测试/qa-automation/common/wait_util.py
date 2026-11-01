"""执行状态轮询工具（L2/L4 共用）。"""
from __future__ import annotations

import time
from typing import Any


def wait_execution(client, exec_id: int, timeout: float = 60) -> dict[str, Any]:
    """轮询执行状态直到终态（SUCCESS/FAILED）。"""
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        body = client.get(f"/api/v1/executions/{exec_id}").json()
        last = body.get("data") or {}
        if last.get("status") in ("SUCCESS", "FAILED"):
            return last
        time.sleep(0.5)
    raise AssertionError(f"执行 {exec_id} 在 {timeout}s 内未到终态，最后状态: {last.get('status')}")


def wait_execution_status(client, exec_id: int, target: list[str], timeout: float = 60) -> dict[str, Any]:
    """轮询直到状态命中 target 集合（用于 WAITING 场景）。"""
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = (client.get(f"/api/v1/executions/{exec_id}").json().get("data")) or {}
        if last.get("status") in target:
            return last
        time.sleep(0.5)
    raise AssertionError(f"执行 {exec_id} 未到达 {target}，最后: {last.get('status')}")
