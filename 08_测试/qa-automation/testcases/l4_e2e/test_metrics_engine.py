"""L4 指标验证：M2 并发执行隔离、M3 HTTP 节点重试。

M2：并发 100 实例，实例间上下文不串（抽查 10 个实例的节点输入含各自 triggerPayload）。
M3：HTTP 节点指向恒 500 端点，断言自动重试 ≤3 次、retryLog 可查、最终 FAILED。
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from common.assert_util import assert_ok
from common.wait_util import wait_execution

pytestmark = pytest.mark.l4


@pytest.mark.m2
@pytest.mark.perf
def test_m2_100_concurrent_executions_isolated(dev):
    """M2：同一已发布版本并发 100 实例，返回 100 个不同 execId，上下文隔离正确。"""
    dsl = {
        "nodes": [
            {"id": "t1", "type": "mqtt-trigger", "name": "触发", "config": {}},
            {"id": "c1", "type": "code", "name": "回显", "config": {"expression": "payload.temp"}},
        ],
        "edges": [{"source": "t1", "target": "c1", "branch": None}],
    }
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": f"QA-M2-{int(time.time())}"}))
    wf_id = wf["id"]
    try:
        ver = assert_ok(dev.post(f"/api/v1/workflows/{wf_id}/versions",
                                 json={"dslJson": json.dumps(dsl, ensure_ascii=False)}))
        assert_ok(dev.put(f"/api/v1/workflows/versions/{ver['id']}/publish"))

        stamp = int(time.time() * 1000)

        def _create(i: int) -> int:
            body = assert_ok(dev.post("/api/v1/executions", json={
                "versionId": ver["id"], "clientReqId": f"m2-{stamp}-{i}",
                "triggerPayload": json.dumps({"temp": 1000 + i}),
            }))
            return body["id"]

        with ThreadPoolExecutor(max_workers=20) as pool:
            exec_ids = list(pool.map(_create, range(100)))
        assert len(set(exec_ids)) == 100, f"并发创建出现重复 id: {len(set(exec_ids))}/100"

        for i, eid in enumerate(exec_ids):
            wait_execution(dev, eid, timeout=180)

        # 抽查 10 个实例：节点 inputJson 必须含各自的 temp 值，不能串
        for i in range(0, 100, 10):
            nodes = assert_ok(dev.get(f"/api/v1/executions/{exec_ids[i]}/nodes"))
            t1 = next(n for n in nodes if n["nodeId"] == "t1")
            assert str(1000 + i) in (t1.get("inputJson") or ""), (
                f"实例 {exec_ids[i]} 上下文串了：期望 temp={1000 + i}，实际 {t1.get('inputJson')}")
    finally:
        dev.delete(f"/api/v1/workflows/{wf_id}")


@pytest.mark.m3
def test_m3_http_node_success_rate_100(dev):
    """M3 成功率子项：可用端点（python-agent /health）连续 100 次调用成功率 ≥99%。"""
    dsl = {
        "nodes": [
            {"id": "t1", "type": "mqtt-trigger", "name": "触发", "config": {}},
            {"id": "h1", "type": "http", "name": "健康检查",
             "config": {"url": "http://localhost:8085/health", "method": "GET", "timeoutMs": 3000}},
        ],
        "edges": [{"source": "t1", "target": "h1", "branch": None}],
    }
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": f"QA-M3-ok-{int(time.time())}"}))
    wf_id = wf["id"]
    try:
        ver = assert_ok(dev.post(f"/api/v1/workflows/{wf_id}/versions",
                                 json={"dslJson": json.dumps(dsl, ensure_ascii=False)}))
        assert_ok(dev.put(f"/api/v1/workflows/versions/{ver['id']}/publish"))
        stamp = int(time.time() * 1000)
        success = 0
        for i in range(100):
            created = assert_ok(dev.post("/api/v1/executions", json={
                "versionId": ver["id"], "clientReqId": f"m3ok-{stamp}-{i}",
                "triggerPayload": "{\"temp\": 1}",
            }))
            final = wait_execution(dev, created["id"], timeout=60)
            if final["status"] == "SUCCESS":
                success += 1
        rate = success / 100
        print(f"[M3] HTTP 节点成功率 {success}/100 = {rate:.0%}")
        assert rate >= 0.99, f"M3 成功率未达标: {success}/100"
    finally:
        dev.delete(f"/api/v1/workflows/{wf_id}")


@pytest.mark.m3
@pytest.mark.p0
def test_m3_http_node_retry_and_retry_log(dev, failing_http_endpoint):
    """M3：HTTP 节点失败自动重试 ≤3 次（退避 1/2/4s），retryLog 可查，最终 FAILED。"""
    dsl = {
        "nodes": [
            {"id": "t1", "type": "mqtt-trigger", "name": "触发", "config": {}},
            {"id": "h1", "type": "http", "name": "故障注入",
             "config": {"url": failing_http_endpoint, "method": "POST", "timeoutMs": 3000}},
        ],
        "edges": [{"source": "t1", "target": "h1", "branch": None}],
    }
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": f"QA-M3-{int(time.time())}"}))
    wf_id = wf["id"]
    try:
        ver = assert_ok(dev.post(f"/api/v1/workflows/{wf_id}/versions",
                                 json={"dslJson": json.dumps(dsl, ensure_ascii=False)}))
        assert_ok(dev.put(f"/api/v1/workflows/versions/{ver['id']}/publish"))
        created = assert_ok(dev.post("/api/v1/executions", json={
            "versionId": ver["id"], "clientReqId": f"m3-{int(time.time() * 1000)}",
            "triggerPayload": "{\"temp\": 1}",
        }))
        final = wait_execution(dev, created["id"], timeout=90)
        assert final["status"] == "FAILED", f"故障注入端点的执行不应成功: {final}"

        nodes = {n["nodeId"]: n for n in assert_ok(dev.get(f"/api/v1/executions/{created['id']}/nodes"))}
        h1 = nodes["h1"]
        assert h1["status"] == "FAILED"
        retry_log = h1.get("retryLog")
        assert retry_log, f"失败节点未记录 retryLog: {h1}"
        attempts = len(json.loads(retry_log))
        assert 1 <= attempts <= 4, f"重试次数不在 1~3 次区间（含首次共 ≤4）: {attempts}"
    finally:
        dev.delete(f"/api/v1/workflows/{wf_id}")
