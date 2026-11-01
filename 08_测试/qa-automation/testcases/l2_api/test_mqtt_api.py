"""L2 接口测试：MQTT 订阅管理。"""
from __future__ import annotations

import time

import pytest

from common.assert_util import assert_code, assert_ok

pytestmark = pytest.mark.l2


def test_create_and_delete_subscription(dev, flow_factory):
    """正向：创建订阅绑定 published 版本 → 详情可查 → 删除。"""
    flow = flow_factory(publish=True)
    topic = f"qa/t/{int(time.time() * 1000)}/temperature"
    sub = assert_ok(dev.post("/api/v1/mqtt/subscriptions", json={
        "topic": topic, "workflowVersionId": flow["versionId"], "status": "active"}))
    try:
        detail = assert_ok(dev.get(f"/api/v1/mqtt/subscriptions/{sub['id']}"))
        assert detail["topic"] == topic
    finally:
        dev.delete(f"/api/v1/mqtt/subscriptions/{sub['id']}")


def test_duplicate_topic_rejected(dev, flow_factory):
    """反向：(tenantId, topic) 唯一，重复创建 → 10000。"""
    flow = flow_factory(publish=True)
    topic = f"qa/dup/{int(time.time() * 1000)}/temperature"
    first = assert_ok(dev.post("/api/v1/mqtt/subscriptions", json={
        "topic": topic, "workflowVersionId": flow["versionId"], "status": "active"}))
    try:
        r = dev.post("/api/v1/mqtt/subscriptions", json={
            "topic": topic, "workflowVersionId": flow["versionId"], "status": "active"})
        assert_code(r, 10000, "重复 topic")
    finally:
        dev.delete(f"/api/v1/mqtt/subscriptions/{first['id']}")


def test_subscription_with_unknown_version_rejected(dev):
    """反向：绑定不存在的版本 → 20007。"""
    r = dev.post("/api/v1/mqtt/subscriptions", json={
        "topic": f"qa/badver/{int(time.time() * 1000)}", "workflowVersionId": 999999999,
        "status": "active"})
    assert_code(r, 20007, "订阅绑定不存在版本")


def test_subscription_not_found(dev):
    """反向：订阅不存在 → 50003。"""
    assert_code(dev.get("/api/v1/mqtt/subscriptions/999999999"), 50003, "订阅不存在")
