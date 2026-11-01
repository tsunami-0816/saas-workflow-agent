"""L2 接口测试：角色权限（M8）与多租户隔离（M7）。"""
from __future__ import annotations

import pytest

from common.assert_util import assert_code, assert_ok

pytestmark = pytest.mark.l2


@pytest.mark.m8
@pytest.mark.p0
def test_viewer_cannot_create_workflow(viewer):
    """M8：查看者创建流程 → HTTP 403 + code 10403。"""
    r = viewer.post("/api/v1/workflows", json={"name": "viewer-不该成功"})
    assert r.status_code == 403, f"期望 403，实际 {r.status_code}: {r.text[:200]}"
    assert_code(r, 10403, "viewer 创建流程")


@pytest.mark.m8
@pytest.mark.p0
def test_viewer_can_read_workflows(viewer):
    """M8 双保险：查看者可读流程列表（UI 只读 + 接口允许 GET）。"""
    data = assert_ok(viewer.get("/api/v1/workflows"), "viewer 读列表")
    assert "records" in data


@pytest.mark.m8
def test_viewer_cannot_execute(viewer, flow_factory):
    """M8：查看者触发执行 → 403。"""
    flow = flow_factory(publish=True)
    r = viewer.post("/api/v1/executions",
                    json={"versionId": flow["versionId"], "clientReqId": "viewer-exec-1"})
    assert r.status_code == 403, f"期望 403，实际 {r.status_code}: {r.text[:200]}"
    assert_code(r, 10403, "viewer 执行")


@pytest.mark.m8
def test_viewer_cannot_access_admin_apis(viewer):
    """M8：非管理员访问租户管理接口 → 403。"""
    r = viewer.get("/api/v1/tenants")
    assert r.status_code == 403, f"期望 403，实际 {r.status_code}"
    assert_code(r, 10403, "viewer 访问租户管理")


@pytest.mark.m8
def test_dev_cannot_access_admin_apis(dev):
    """M8：developer 访问租户管理接口 → 403（仅 admin）。"""
    r = dev.get("/api/v1/tenants")
    assert r.status_code == 403, f"期望 403，实际 {r.status_code}"
    assert_code(r, 10403, "dev 访问租户管理")


@pytest.mark.m8
def test_admin_can_access_admin_apis(admin):
    """M8 正向：管理员访问租户列表成功。"""
    data = assert_ok(admin.get("/api/v1/tenants"), "admin 租户列表")
    assert "records" in data


@pytest.mark.m7
@pytest.mark.p0
def test_cross_tenant_workflow_not_readable(dev, other_tenant):
    """M7：租户 A 的流程对租户 B 不可见（详情报 20001/403，列表不含该 id）。"""
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": "QA-M7-租户隔离"}))
    wf_id = wf["id"]
    try:
        r = other_tenant.get(f"/api/v1/workflows/{wf_id}")
        assert r.status_code in (403, 404, 200), f"意外状态 {r.status_code}"
        body = r.json()
        assert body.get("code") in (20001, 10403), f"跨租户读到了他租户流程: {body}"

        listed = assert_ok(other_tenant.get("/api/v1/workflows", params={"pageNo": 1, "pageSize": 100}))
        ids = [row["id"] for row in listed.get("records", [])]
        assert wf_id not in ids, "跨租户列表泄漏了租户 A 的流程"
    finally:
        dev.delete(f"/api/v1/workflows/{wf_id}")


@pytest.mark.m7
def test_cross_tenant_workflow_not_writable(other_tenant, dev):
    """M7：租户 B 修改/删除租户 A 的流程必须失败（20001 或 403）。"""
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": "QA-M7-写隔离"}))
    wf_id = wf["id"]
    try:
        r = other_tenant.put(f"/api/v1/workflows/{wf_id}", json={"name": "hijacked"})
        assert r.json().get("code") in (20001, 10403), f"跨租户写入成功: {r.text[:200]}"

        r = other_tenant.delete(f"/api/v1/workflows/{wf_id}")
        assert r.json().get("code") in (20001, 10403), f"跨租户删除成功: {r.text[:200]}"

        # 原租户仍可读到，且名称未被篡改
        detail = assert_ok(dev.get(f"/api/v1/workflows/{wf_id}"))
        assert detail["name"] == "QA-M7-写隔离"
    finally:
        dev.delete(f"/api/v1/workflows/{wf_id}")
