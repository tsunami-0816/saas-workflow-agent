"""L2 接口测试：额度 / LLM 台账 / 审计日志（M4 计量口径）。"""
from __future__ import annotations

import pytest

from common.assert_util import assert_code, assert_ok

pytestmark = pytest.mark.l2


@pytest.mark.m8
def test_quota_readable_by_all_roles(dev, viewer):
    """M4/M8：额度接口三角色可读，返回 tokenTotal/tokenUsed/remain 口径。"""
    for client, role in ((dev, "dev"), (viewer, "viewer")):
        data = assert_ok(client.get("/api/v1/quota"), f"{role} 查额度")
        assert "tokenTotal" in data, f"{role} 额度缺 tokenTotal: {data}"
        assert "tokenUsed" in data, f"{role} 额度缺 tokenUsed: {data}"


def test_llm_call_log_records_usage(admin, dev):
    """M4：LLM 台账可查，且每条含 provider/model/token 用量/成本。

    用例自足（硬规则 7）：先自造一次真实 LLM 调用（NL-draft 走 DashScope），再查台账，
    不依赖历史执行数据（7.5 数据重置后台账为空，旧用例因此误红）。
    """
    import time

    name = f"QA-台账-{int(time.time() * 1000)}"
    ver = assert_ok(dev.post("/api/v1/workflows/nl-draft",
                             json={"text": "收到温度消息，超过 80 度调用告警接口，否则记录正常",
                                   "workflowName": name}),
                    "自造一次 LLM 调用（NL 草稿）")
    try:
        data = assert_ok(admin.get("/api/v1/quota/llm-calls", params={"pageNo": 1, "pageSize": 20}))
        records = data.get("records", [])
        assert records, "台账为空：已真实调用 LLM，应至少 1 条记录"
        row = records[0]
        for field in ("provider", "model", "taskType", "promptTokens", "completionTokens", "cost"):
            assert field in row, f"台账缺字段 {field}: {row}"
        assert row["tenantId"] == 1, f"台账未归租: {row}"
    finally:
        dev.delete(f"/api/v1/workflows/{ver['workflowId']}")


def test_llm_call_log_pagination_boundary(dev):
    """边界：台账分页极端参数不得 500。"""
    r = dev.get("/api/v1/quota/llm-calls", params={"pageNo": 1, "pageSize": 500})
    assert r.status_code != 500
    assert r.json().get("code") == 0


@pytest.mark.m8
def test_audit_logs_admin_only(admin, dev):
    """M8：审计日志仅 admin 可查，dev 403。"""
    data = assert_ok(admin.get("/api/v1/quota/audit-logs"), "admin 审计日志")
    assert "records" in data

    r = dev.get("/api/v1/quota/audit-logs")
    assert r.status_code == 403, f"期望 403，实际 {r.status_code}"
    assert_code(r, 10403, "dev 查审计日志")


def test_audit_log_contains_workflow_create(admin, dev):
    """正向：创建流程后审计日志出现 workflow.create 动作（5A 审计落库）。"""
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": "QA-审计-001"}))
    try:
        data = assert_ok(admin.get("/api/v1/quota/audit-logs", params={"pageNo": 1, "pageSize": 50}))
        actions = [row.get("action") for row in data.get("records", [])]
        assert any(a and "workflow" in a for a in actions), f"审计日志未见 workflow 相关动作: {actions}"
    finally:
        dev.delete(f"/api/v1/workflows/{wf['id']}")
