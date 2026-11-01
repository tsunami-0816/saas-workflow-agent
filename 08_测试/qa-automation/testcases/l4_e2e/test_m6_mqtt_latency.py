"""L4 指标验证：M6 MQTT 端到端延迟（Broker 收到消息 → 流程实例创建 ≤3s，P95，连续 20 次）。"""
from __future__ import annotations

import json
import time

import pytest

from common.assert_util import assert_ok

pytestmark = pytest.mark.l4

paho = pytest.importorskip("paho.mqtt.client")


@pytest.mark.m6
@pytest.mark.p0
def test_m6_mqtt_trigger_latency_p95(dev, cfg):
    """M6：连续 20 次发布 MQTT 消息，P95 延迟 ≤3s。"""
    dsl = {
        "nodes": [
            {"id": "t1", "type": "mqtt-trigger", "name": "触发", "config": {}},
            {"id": "c1", "type": "code", "name": "处理", "config": {"expression": "payload.temp"}},
        ],
        "edges": [{"source": "t1", "target": "c1", "branch": None}],
    }
    stamp = int(time.time() * 1000)
    topic = f"qa/m6/{stamp}/temperature"
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": f"QA-M6-{stamp}"}))
    wf_id = wf["id"]
    sub_id = None
    client = None
    try:
        ver = assert_ok(dev.post(f"/api/v1/workflows/{wf_id}/versions",
                                 json={"dslJson": json.dumps(dsl, ensure_ascii=False)}))
        assert_ok(dev.put(f"/api/v1/workflows/versions/{ver['id']}/publish"))
        sub = assert_ok(dev.post("/api/v1/mqtt/subscriptions", json={
            "topic": topic, "workflowVersionId": ver["id"], "status": "active"}))
        sub_id = sub["id"]

        client = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=f"qa-m6-{stamp}")
        client.connect(cfg["mqtt"]["host"], cfg["mqtt"]["port"], 30)
        client.loop_start()
        time.sleep(1)  # 等后端热订阅完成

        latencies: list[float] = []
        seen = {row["id"] for row in
                assert_ok(dev.get("/api/v1/executions", params={"pageNo": 1, "pageSize": 100}))["records"]}

        for i in range(20):
            t0 = time.monotonic()
            client.publish(topic, json.dumps({"temp": 50 + i}))
            new_id = None
            deadline = t0 + 10
            while time.monotonic() < deadline and new_id is None:
                rows = assert_ok(dev.get("/api/v1/executions",
                                         params={"pageNo": 1, "pageSize": 100}))["records"]
                for row in rows:
                    if row["id"] not in seen:
                        new_id = row["id"]
                        seen.add(row["id"])
                        break
                if new_id is None:
                    time.sleep(0.05)
            assert new_id, f"第 {i + 1} 次消息未触发执行实例（topic={topic}）"
            latencies.append(time.monotonic() - t0)

        latencies.sort()
        p95 = latencies[max(0, int(round(0.95 * len(latencies))) - 1)]
        print(f"[M6] 延迟样本(ms)={[round(x * 1000) for x in latencies]} P95={p95 * 1000:.0f}ms")
        assert p95 <= 3.0, f"M6 未达标：P95={p95 * 1000:.0f}ms > 3000ms"
    finally:
        if client is not None:
            client.loop_stop()
            client.disconnect()
        if sub_id:
            dev.delete(f"/api/v1/mqtt/subscriptions/{sub_id}")
        dev.delete(f"/api/v1/workflows/{wf_id}")
