"""L2 接口测试：认证（正向 / 反向 / 边界 / 未授权）。"""
from __future__ import annotations

import httpx
import pytest

from common.assert_util import assert_code, assert_http, assert_ok
from common.request_util import jbody

pytestmark = pytest.mark.l2


def test_login_success_returns_token_and_role(cfg, password):
    """正向：正确凭证登录返回 token + userId/tenantId/role。"""
    r = httpx.post(f"{cfg['java_base']}/api/v1/auth/login",
                   json={"username": "dev_acme", "password": password}, timeout=cfg["timeout"])
    data = assert_ok(r, "登录")
    assert data["token"]
    assert data["tenantId"] == 1
    assert data["role"] in ("admin", "dev", "viewer")


def test_login_wrong_password_returns_401(cfg, password):
    """反向：密码错误 → HTTP 401 + code 10401。"""
    r = httpx.post(f"{cfg['java_base']}/api/v1/auth/login",
                   json={"username": "dev_acme", "password": password + "_wrong"}, timeout=cfg["timeout"])
    body = assert_http(r, 401, "错误密码")
    assert body["code"] == 10401


def test_login_blank_username_returns_10000(cfg, password):
    """边界：空用户名 → 参数错误 10000。"""
    r = httpx.post(f"{cfg['java_base']}/api/v1/auth/login",
                   json={"username": "", "password": password}, timeout=cfg["timeout"])
    assert_code(r, 10000, "空用户名")


def test_login_overlong_username(cfg):
    """边界：超长用户名不得 500（应业务失败或 401）。"""
    r = httpx.post(f"{cfg['java_base']}/api/v1/auth/login",
                   json={"username": "u" * 300, "password": "x"}, timeout=cfg["timeout"])
    assert r.status_code in (200, 400, 401), f"超长用户名返回 {r.status_code}: {r.text[:200]}"
    assert jbody(r).get("code") != 10500, "超长用户名触发了 10500 内部错误"


def test_me_without_token_returns_401(cfg):
    """未授权：不带 token 访问 /auth/me → 401。"""
    r = httpx.get(f"{cfg['java_base']}/api/v1/auth/me", timeout=cfg["timeout"])
    assert_http(r, 401, "无 token")


def test_me_with_invalid_token_returns_401(cfg):
    """未授权：伪造 token → 401。"""
    r = httpx.get(f"{cfg['java_base']}/api/v1/auth/me",
                  headers={"Authorization": "Bearer not-a-jwt"}, timeout=cfg["timeout"])
    assert_http(r, 401, "伪造 token")


def test_me_success(dev):
    """正向：带 token 取当前用户，字段与本账号一致。"""
    data = assert_ok(dev.get("/api/v1/auth/me"), "me")
    assert data["tenantId"] == 1
    assert data["role"] == "dev"
