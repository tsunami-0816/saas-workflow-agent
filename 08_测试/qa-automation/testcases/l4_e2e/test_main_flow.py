"""L4 端到端：主业务链路（登录 → 建流程 → 存版本 → 发布 → 执行 → 状态/节点可见 → 列表可见）。

覆盖基线 §1 MVP 最小可用场景的服务端部分（画布操作本身在第 9 步人工走查）。
"""
from __future__ import annotations

import json
import time

import pytest

from common.assert_util import assert_ok
from common.wait_util import wait_execution

pytestmark = [pytest.mark.l4, pytest.mark.p0]


def test_main_flow_end_to_end(dev):
    """P0 主链路：3 类节点（mqtt-trigger/condition/code）全链跑通并落库可回放。"""
    # 1) 建流程
    name = f"QA-E2E-{int(time.time() * 1000)}"
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": name, "description": "E2E"}))
    wf_id = wf["id"]
    try:
        # 2) 存版本（条件分支双覆盖）
        dsl = {
            "nodes": [
                {"id": "t1", "type": "mqtt-trigger", "name": "温度采集", "config": {}},
                {"id": "c1", "type": "condition", "name": "高温判断",
                 "config": {"expression": "payload.temp > 80"}},
                {"id": "h1", "type": "code", "name": "告警文案",
                 "config": {"expression": "'高温告警: ' + payload.temp"}},
                {"id": "n1", "type": "code", "name": "正常记录",
                 "config": {"expression": "'正常: ' + payload.temp"}},
            ],
            "edges": [
                {"source": "t1", "target": "c1", "branch": None},
                {"source": "c1", "target": "h1", "branch": "true"},
                {"source": "c1", "target": "n1", "branch": "false"},
            ],
        }
        ver = assert_ok(dev.post(f"/api/v1/workflows/{wf_id}/versions",
                                 json={"dslJson": json.dumps(dsl, ensure_ascii=False)}))
        # 3) 发布
        assert_ok(dev.put(f"/api/v1/workflows/versions/{ver['id']}/publish"))

        # 4) 执行（高温 → 走 true 分支）
        exec_data = assert_ok(dev.post("/api/v1/executions", json={
            "versionId": ver["id"],
            "clientReqId": f"qa-e2e-{int(time.time() * 1000)}",
            "triggerPayload": json.dumps({"temp": 95}),
        }))
        exec_id = exec_data["id"]

        # 5) 等终态
        final = wait_execution(dev, exec_id, timeout=60)
        assert final["status"] == "SUCCESS", f"主链路未成功: {final}"

        # 6) 节点快照：true 分支 SUCCESS，false 分支 SKIPPED
        nodes = {n["nodeId"]: n for n in assert_ok(dev.get(f"/api/v1/executions/{exec_id}/nodes"))}
        assert nodes["c1"]["status"] == "SUCCESS"
        assert nodes["h1"]["status"] == "SUCCESS"
        assert nodes["n1"]["status"] == "SKIPPED", f"条件未选中分支应 SKIPPED: {nodes['n1']}"
        assert "95" in (nodes["h1"].get("outputJson") or "") or "高温" in (nodes["h1"].get("outputJson") or "")

        # 7) 执行记录列表可见 + 详情可回放
        listed = assert_ok(dev.get("/api/v1/executions", params={"pageNo": 1, "pageSize": 20}))
        assert exec_id in [row["id"] for row in listed["records"]], "执行记录未出现在列表"
        detail = assert_ok(dev.get(f"/api/v1/executions/{exec_id}"))
        assert detail["versionId"] == ver["id"]
    finally:
        dev.delete(f"/api/v1/workflows/{wf_id}")


def test_sse_events_endpoint_connects(dev, flow_factory):
    """SSE 订阅可用：连接后先收到 connected 事件（不阻塞主流程）。"""
    flow = flow_factory(publish=True)
    created = assert_ok(dev.post("/api/v1/executions", json={
        "versionId": flow["versionId"],
        "clientReqId": f"qa-sse-{int(time.time() * 1000)}",
        "triggerPayload": "{\"temp\": 20}",
    }))
    exec_id = created["id"]
    got = ""
    try:
        with dev._client.stream("GET", f"/api/v1/executions/{exec_id}/events",
                                headers={"Authorization": f"Bearer {dev.token}"},
                                timeout=10) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                got += line + "\n"
                if "connected" in got:
                    break
    finally:
        wait_execution(dev, exec_id, timeout=60)
    assert "connected" in got, f"SSE 未收到 connected 事件: {got[:300]}"
