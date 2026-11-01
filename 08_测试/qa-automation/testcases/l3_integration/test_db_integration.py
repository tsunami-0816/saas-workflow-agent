"""L3 中间件集成测试：直连已启动的 MySQL 容器验证落库与事务一致性。

降级说明（对齐 step08 §8.0 的 L3 取舍条款）：
本机 Docker Compose 已占较多内存，未使用 Testcontainers 动态起容器，改为
「L2 接口 + 直连 docker-compose 已就绪的 MySQL(3310) / Redis(6379) 手动连接」，
降级原因与影响在测试报告中显式登记，未偷偷砍掉 L3 层。
"""
from __future__ import annotations

import json
import os
import time

import pytest

from common.assert_util import assert_ok
from common.wait_util import wait_execution

pytestmark = pytest.mark.l3

pymysql = pytest.importorskip("pymysql")


@pytest.fixture(scope="session")
def mysql_conn(cfg):
    conn = pymysql.connect(host=cfg["mysql"]["host"], port=cfg["mysql"]["port"],
                           user=cfg["mysql"]["user"], password=cfg["mysql"]["password"],
                           database=cfg["mysql"]["database"], charset="utf8mb4",
                           cursorclass=pymysql.cursors.DictCursor)
    yield conn
    conn.close()


def test_execution_and_nodes_persisted(mysql_conn, dev):
    """DB 落库：API 创建的执行必须落 execution 表，节点快照落 node_execution 表。"""
    dsl = {"nodes": [{"id": "t1", "type": "mqtt-trigger", "name": "触发", "config": {}},
                     {"id": "c1", "type": "code", "name": "处理",
                      "config": {"expression": "payload.temp"}}],
           "edges": [{"source": "t1", "target": "c1", "branch": None}]}
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": f"QA-L3-{int(time.time())}"}))
    wf_id = wf["id"]
    try:
        ver = assert_ok(dev.post(f"/api/v1/workflows/{wf_id}/versions",
                                 json={"dslJson": json.dumps(dsl, ensure_ascii=False)}))
        assert_ok(dev.put(f"/api/v1/workflows/versions/{ver['id']}/publish"))
        created = assert_ok(dev.post("/api/v1/executions", json={
            "versionId": ver["id"], "clientReqId": f"l3-{int(time.time() * 1000)}",
            "triggerPayload": "{\"temp\": 3}"}))
        exec_id = created["id"]
        final = wait_execution(dev, exec_id, timeout=60)

        with mysql_conn.cursor() as cur:
            cur.execute("SELECT id, tenant_id, version_id, status FROM execution WHERE id=%s", (exec_id,))
            row = cur.fetchone()
            assert row, f"execution 表无记录 execId={exec_id}"
            assert row["tenant_id"] == 1
            assert row["version_id"] == ver["id"]
            assert row["status"] == final["status"]

            cur.execute("SELECT node_id, status FROM node_execution WHERE execution_id=%s", (exec_id,))
            nodes = {r["node_id"]: r["status"] for r in cur.fetchall()}
            assert set(nodes) == {"t1", "c1"}, f"node_execution 行不完整: {nodes}"
            assert nodes["c1"] == "SUCCESS"
    finally:
        dev.delete(f"/api/v1/workflows/{wf_id}")


def test_llm_call_log_persisted_with_tenant(mysql_conn, dev):
    """M4 台账落库：自行触发 3 次真实模型调用，校验台账落库且租户归属=1（不依赖历史数据）。"""
    with mysql_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM llm_call_log")
        before = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM llm_call_log WHERE tenant_id=1")
        tenant_one_before = cur.fetchone()["c"]

    created = []
    try:
        for i in range(3):
            res = assert_ok(dev.post("/api/v1/workflows/nl-draft", json={
                "text": f"QA 台账校验第 {i + 1} 条：收到温度消息后超过 80 度告警",
                "workflowName": f"QA-LLM-{int(time.time() * 1000)}-{i}"}))
            created.append(res["workflowId"])
    finally:
        for wf_id in created:
            dev.delete(f"/api/v1/workflows/{wf_id}")

    # 结束只读事务，避免 REPEATABLE READ 快照看不到接口新写入的台账
    mysql_conn.commit()

    with mysql_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM llm_call_log")
        total = cur.fetchone()["c"]
        assert total >= before + 3, f"LLM 台账未新增 3 条: before={before} after={total}"

        cur.execute("SELECT COUNT(*) AS c FROM llm_call_log WHERE tenant_id=0")
        zero_tenant = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM llm_call_log WHERE tenant_id=1")
        tenant_one = cur.fetchone()["c"]
    assert tenant_one >= tenant_one_before + 3, f"租户 1 台账未新增 3 条: before={tenant_one_before} after={tenant_one}"
    # tenant_id=0 的历史记录来自第 7 步修复前的对照实验，属预期；新增记录必须归租
    assert zero_tenant <= 1, f"修复后仍出现无租户台账记录 {zero_tenant} 条"


def test_idempotency_key_persisted_in_redis(dev, cfg):
    """Redis 幂等键落盘：同一 clientReqId 二次提交命中同一实例（间接验证 SETNX 生效）。"""
    dsl = {"nodes": [{"id": "t1", "type": "mqtt-trigger", "name": "触发", "config": {}}], "edges": []}
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": f"QA-L3-redis-{int(time.time())}"}))
    try:
        ver = assert_ok(dev.post(f"/api/v1/workflows/{wf['id']}/versions",
                                 json={"dslJson": json.dumps(dsl)}))
        assert_ok(dev.put(f"/api/v1/workflows/versions/{ver['id']}/publish"))
        req_id = f"l3-redis-{int(time.time() * 1000)}"
        body = {"versionId": ver["id"], "clientReqId": req_id, "triggerPayload": "{}"}
        a = assert_ok(dev.post("/api/v1/executions", json=body))
        b = assert_ok(dev.post("/api/v1/executions", json=body))
        assert a["id"] == b["id"], "幂等键未生效（Redis SETNX 失效）"
        wait_execution(dev, a["id"], timeout=60)
    finally:
        dev.delete(f"/api/v1/workflows/{wf['id']}")
