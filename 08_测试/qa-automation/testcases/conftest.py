"""pytest 全局 fixture：环境配置、三角色登录、跨租户账号、流程工厂、故障注入 HTTP Server。

设计要点（对齐 step08 硬规则）：
1. 账号不写死密码：从环境变量 SWA_TEST_PASSWORD 读；登录失败的种子账号由 admin 兜底自动创建临时用户；
2. 每条用例自己造数据、自己清理（流程工厂返回 disposable，用例负责删除）；
3. 已知 Bug 用 @pytest.mark.xfail(reason=根因) 标记，修好后自动转 PASS。
"""
from __future__ import annotations

import os
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest
import yaml

_QA_ROOT = Path(__file__).resolve().parents[1]          # 08_测试/qa-automation
_PROJECT_ROOT = Path(__file__).resolve().parents[3]      # projects/saas-workflow-agent
_AGENT_PY = _PROJECT_ROOT / "05_代码" / "agent-python"
for _p in (str(_QA_ROOT), str(_AGENT_PY)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.request_util import ApiClient, login  # noqa: E402


# ---------------------------------------------------------------- 配置与登录
@pytest.fixture(scope="session")
def cfg() -> dict[str, Any]:
    with open(_QA_ROOT / "config" / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def password(cfg) -> str:
    env_key = cfg.get("password_env", "SWA_TEST_PASSWORD")
    return os.environ.get(env_key) or cfg.get("password_default")


def _do_login(base: str, username: str, pwd: str) -> str | None:
    body = login(base, username, pwd)
    if body.get("code") == 0 and body.get("data", {}).get("token"):
        return body["data"]["token"]
    return None


def _ensure_account(cfg, pwd: str, admin_token: str, role: str, username: str) -> str:
    """种子账号登录失败时：admin 建临时用户再登录（CI/新环境无种子数据也能跑）。"""
    temp_name = f"qa_{role}_{int(time.time())}_{random.randint(100, 999)}"
    with httpx.Client(base_url=cfg["java_base"], timeout=cfg["timeout"]) as c:
        resp = c.post("/api/v1/users",
                      headers={"Authorization": f"Bearer {admin_token}"},
                      json={"username": temp_name, "password": pwd,
                            "displayName": f"QA {role}", "role": role})
    token = _do_login(cfg["java_base"], temp_name, pwd)
    assert token, f"自动注册账号 {temp_name} 后仍登录失败（{username} 登录失败且兜底注册不可用）"
    _ = resp
    return token


@pytest.fixture(scope="session")
def tokens(cfg, password) -> dict[str, str]:
    base = cfg["java_base"]
    result: dict[str, str] = {}
    for role, acc in cfg["accounts"].items():
        token = _do_login(base, acc["username"], password)
        if token:
            result[role] = token
    if "admin" not in result:
        pytest.exit(
            f"环境不可用：admin 账号登录失败（{base}）。请确认 java-backend 已启动且种子账号密码正确。",
            returncode=2,
        )
    for role, acc in cfg["accounts"].items():
        if role not in result:
            result[role] = _ensure_account(cfg, password, result["admin"], acc["role"], acc["username"])
    return result


@pytest.fixture(scope="session")
def clients(cfg, tokens) -> dict[str, ApiClient]:
    made = {role: ApiClient(cfg["java_base"], tok, cfg["timeout"]) for role, tok in tokens.items()}
    yield made
    for c in made.values():
        c.close()


@pytest.fixture()
def dev(clients) -> ApiClient:
    """开发者角色客户端（主用例默认）。"""
    return clients["dev"]


@pytest.fixture()
def admin(clients) -> ApiClient:
    return clients["admin"]


@pytest.fixture()
def viewer(clients) -> ApiClient:
    return clients["viewer"]


@pytest.fixture()
def other_tenant(clients) -> ApiClient:
    """另一租户（globex）的开发者，用于 M7 多租户隔离。"""
    return clients["other"]


# ---------------------------------------------------------------- 数据工厂
@pytest.fixture()
def flow_factory(dev) -> Callable[..., dict[str, Any]]:
    """创建流程 → 保存 DSL 版本 → 可选发布；返回 {workflowId, versionId}，用例结束自动删除流程。"""
    created: list[int] = []

    def _make(dsl: dict | None = None, publish: bool = False, name_prefix: str = "QA") -> dict[str, Any]:
        name = f"{name_prefix}-{int(time.time() * 1000)}-{random.randint(100, 999)}"
        r = dev.post("/api/v1/workflows", json={"name": name, "description": "自动化测试流程"})
        assert r.json().get("code") == 0, f"创建流程失败: {r.text[:300]}"
        wf = r.json()["data"]
        wf_id = wf["id"]
        created.append(wf_id)
        dsl = dsl or {"nodes": [{"id": "t1", "type": "mqtt-trigger", "name": "触发", "config": {}},
                                {"id": "c1", "type": "code", "name": "处理",
                                 "config": {"expression": "payload.temp + 1"}}],
                      "edges": [{"source": "t1", "target": "c1", "branch": None}]}
        r = dev.post(f"/api/v1/workflows/{wf_id}/versions", json={"dslJson": _dumps(dsl)})
        assert r.json().get("code") == 0, f"保存版本失败: {r.text[:300]}"
        ver = r.json()["data"]
        if publish:
            r = dev.put(f"/api/v1/workflows/versions/{ver['id']}/publish")
            assert r.json().get("code") == 0, f"发布版本失败: {r.text[:300]}"
        return {"workflowId": wf_id, "versionId": ver["id"], "name": name}

    yield _make
    for wf_id in created:
        try:
            dev.delete(f"/api/v1/workflows/{wf_id}")
        except Exception:
            pass


def _dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)


# ---------------------------------------------------------------- 故障注入 HTTP Server（M3）
@pytest.fixture(scope="session")
def failing_http_endpoint() -> str:
    """起一个恒返 500 的本地 HTTP 端点，用于验证 HTTP 节点重试 ≤3 次。"""

    class _Handler(BaseHTTPRequestHandler):
        def _fail(self):
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"injected 500"}')

        do_GET = _fail
        do_POST = _fail

        def log_message(self, *args):  # 静默
            return

    server = ThreadingHTTPServer(("127.0.0.1", 8099), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:8099/fail"
    server.shutdown()
