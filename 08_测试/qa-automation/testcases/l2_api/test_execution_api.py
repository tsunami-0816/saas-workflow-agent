"""L2 接口测试：执行（创建/幂等/状态机/节点快照/重放）。"""
from __future__ import annotations

import time

import pytest

from common.assert_util import assert_code, assert_ok
from common.wait_util import wait_execution

pytestmark = pytest.mark.l2


@pytest.mark.p0
def test_create_execution_on_published_version(dev, flow_factory):
    """P0 正向：published 版本可创建执行，返回执行实体 id + RUNNING/SUCCESS。"""
    flow = flow_factory(publish=True)
    data = assert_ok(dev.post("/api/v1/executions", json={
        "versionId": flow["versionId"],
        "clientReqId": f"qa-exec-{int(time.time() * 1000)}",
        "triggerPayload": "{\"temp\": 90}",
    }))
    assert data.get("id"), f"响应缺执行 id: {data}"
    assert data.get("status") in ("RUNNING", "SUCCESS", "WAITING")


@pytest.mark.p0
def test_execution_idempotent_same_client_req_id(dev, flow_factory):
    """P0 幂等：相同 clientReqId 重复提交返回同一执行实例。"""
    flow = flow_factory(publish=True)
    req_id = f"qa-idem-{int(time.time() * 1000)}"
    body = {"versionId": flow["versionId"], "clientReqId": req_id, "triggerPayload": "{\"temp\": 1}"}
    first = assert_ok(dev.post("/api/v1/executions", json=body))
    second = assert_ok(dev.post("/api/v1/executions", json=body))
    assert first["id"] == second["id"], f"幂等失效: {first} vs {second}"


def test_create_execution_on_draft_rejected(dev, flow_factory):
    """反向：draft 版本不可执行 → 20009。"""
    flow = flow_factory(publish=False)
    r = dev.post("/api/v1/executions", json={
        "versionId": flow["versionId"],
        "clientReqId": f"qa-draft-{int(time.time() * 1000)}",
    })
    assert_code(r, 20009, "draft 执行")


def test_create_execution_on_disabled_rejected(dev, flow_factory):
    """反向：disabled 版本不可执行 → 20008。"""
    flow = flow_factory(publish=True)
    assert_ok(dev.put(f"/api/v1/workflows/versions/{flow['versionId']}/disable"))
    r = dev.post("/api/v1/executions", json={
        "versionId": flow["versionId"],
        "clientReqId": f"qa-disabled-{int(time.time() * 1000)}",
    })
    assert_code(r, 20008, "disabled 执行")


@pytest.mark.p0
def test_execution_success_and_node_snapshots(dev, flow_factory):
    """P0 主链路：执行到 SUCCESS，节点快照含 trigger 与下游节点终态。"""
    flow = flow_factory(publish=True)
    created = assert_ok(dev.post("/api/v1/executions", json={
        "versionId": flow["versionId"],
        "clientReqId": f"qa-snap-{int(time.time() * 1000)}",
        "triggerPayload": "{\"temp\": 42}",
    }))
    exec_id = created["id"]
    final = wait_execution(dev, exec_id, timeout=60)
    assert final["status"] == "SUCCESS", f"执行未成功: {final}"

    nodes = assert_ok(dev.get(f"/api/v1/executions/{exec_id}/nodes"))
    node_ids = {n["nodeId"]: n for n in nodes}
    assert "t1" in node_ids and "c1" in node_ids
    assert node_ids["c1"]["status"] == "SUCCESS"
    assert node_ids["c1"]["outputJson"], "节点输出为空"


def test_execution_not_found(dev):
    """反向：执行不存在 → 30001。"""
    assert_code(dev.get("/api/v1/executions/999999999"), 30001, "执行不存在")


def test_execution_list_filter_by_status(dev):
    """正向：执行列表按 status 过滤，返回行 status 与过滤值一致。"""
    data = assert_ok(dev.get("/api/v1/executions", params={"pageNo": 1, "pageSize": 10, "status": "SUCCESS"}))
    for row in data.get("records", []):
        assert row["status"] == "SUCCESS"


def test_replay_creates_new_execution(dev, flow_factory):
    """正向：重放复制触发入参生成新执行实例（id 不同）。"""
    flow = flow_factory(publish=True)
    created = assert_ok(dev.post("/api/v1/executions", json={
        "versionId": flow["versionId"],
        "clientReqId": f"qa-replay-src-{int(time.time() * 1000)}",
        "triggerPayload": "{\"temp\": 7}",
    }))
    src_id = created["id"]
    wait_execution(dev, src_id, timeout=60)
    replayed = assert_ok(dev.post(f"/api/v1/executions/{src_id}/replay"))
    new_id = replayed.get("id")
    assert new_id and new_id != src_id, f"重放未生成新实例: {replayed}"
