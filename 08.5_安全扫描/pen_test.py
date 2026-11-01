"""第 8.5 步接口级渗透实测（Agent 代跑）。覆盖：未授权/越权/弱口令/SQLi/内部令牌。"""
from __future__ import annotations
import httpx

BASE = "http://localhost:8083"
AGENT = "http://localhost:8085"


def login(username: str, password: str) -> str | None:
    r = httpx.post(f"{BASE}/api/v1/auth/login", json={"username": username, "password": password}, timeout=10)
    return r.json().get("data", {}).get("token")


def main() -> None:
    # 1. 未授权访问内部接口
    r = httpx.post(f"{BASE}/internal/llm/chat", json={"taskType": "nl2flow", "prompt": "hi"}, timeout=10)
    print(f"[1] /internal/llm/chat 无令牌: HTTP {r.status_code} | {r.text[:100]}")

    # 2. 未授权访问业务接口
    r = httpx.get(f"{BASE}/api/v1/workflows", timeout=10)
    print(f"[2] /api/v1/workflows 无 token: HTTP {r.status_code} | {r.text[:100]}")

    # 3. 弱口令
    r = httpx.post(f"{BASE}/api/v1/auth/login", json={"username": "admin_acme", "password": "admin"}, timeout=10)
    print(f"[3] 弱口令 admin/admin: HTTP {r.status_code} | {r.text[:100]}")

    # 4. dev_acme 登录
    dev_tok = login("dev_acme", "Swa@123456")
    print(f"[4] dev_acme 登录成功: {bool(dev_tok)}")

    # 5. 垂直越权：dev 调审计接口（admin 专用）
    r = httpx.get(f"{BASE}/api/v1/admin/audits", headers={"Authorization": f"Bearer {dev_tok}"}, timeout=10)
    print(f"[5] dev 调 /admin/audits: HTTP {r.status_code} | {r.text[:120]}")

    # 6. SQL 注入：name 搜索
    r = httpx.get(f"{BASE}/api/v1/workflows", params={"name": "' OR '1'='1"},
                  headers={"Authorization": f"Bearer {dev_tok}"}, timeout=10)
    print(f"[6] SQLi name=' OR '1'='1: HTTP {r.status_code} | code={r.json().get('code')} | {r.text[:120]}")

    # 7. 水平越权：dev_acme(tenant1) 尝试访问 tenant2 的流程（构造一个超大 id 或直接列表应只返回 tenant1）
    r = httpx.get(f"{BASE}/api/v1/workflows", headers={"Authorization": f"Bearer {dev_tok}"}, timeout=10)
    data = r.json().get("data", {})
    tenants = {row.get("tenantId") for row in data.get("records", [])}
    print(f"[7] dev_acme 列表 tenantId 集合: {tenters if False else tenants}")

    # 8. python-agent /agent/run 无鉴权（已知 P2，登记 Q-012）
    r = httpx.post(f"{AGENT}/agent/run", json={"executionId": "pen-test", "nodeId": "n1", "task": "x"}, timeout=10)
    print(f"[8] python-agent /agent/run 无鉴权: HTTP {r.status_code} | {r.text[:100]}")

    # 9. python-agent /health 公开探活（正常）
    r = httpx.get(f"{AGENT}/health", timeout=10)
    print(f"[9] python-agent /health: HTTP {r.status_code} | {r.text[:80]}")


if __name__ == "__main__":
    main()
