"""L2 接口测试：流程 CRUD / DSL 校验 / 版本状态机（含 M1 画布复杂度）。"""
from __future__ import annotations

import json

import pytest

from common.assert_util import assert_code, assert_ok

pytestmark = pytest.mark.l2


def _dsl(nodes, edges=None) -> str:
    return json.dumps({"nodes": list(nodes), "edges": edges or []}, ensure_ascii=False)


def test_create_workflow_success(dev):
    """正向：创建流程返回 id/name，详情可查回（含 tenantId）。"""
    name = "QA-创建-正向-001"
    data = assert_ok(dev.post("/api/v1/workflows", json={"name": name, "description": "自动化"}))
    wf_id = data["id"]
    try:
        assert data["name"] == name
        detail = assert_ok(dev.get(f"/api/v1/workflows/{wf_id}"))
        assert detail["id"] == wf_id
        # 注：创建响应体未回填 tenantId（BUG-001，P2 延后修），详情接口可正常读回 tenantId
        assert detail["tenantId"] == 1
    finally:
        dev.delete(f"/api/v1/workflows/{wf_id}")


def test_create_workflow_blank_name_rejected(dev):
    """反向：空名称 → 参数错误 10000（@NotBlank 生效）。"""
    r = dev.post("/api/v1/workflows", json={"name": "", "description": "x"})
    assert_code(r, 10000, "空名称")


def test_create_workflow_overlong_name_rejected(dev):
    """边界：名称 300 字符超过 @Size(max=128) → 10000，不得落库。"""
    r = dev.post("/api/v1/workflows", json={"name": "长" * 300})
    assert_code(r, 10000, "超长名称")


def test_list_pagination_boundary(dev):
    """边界：pageNo=0 / pageSize=999 不得 500，返回结构含 records/total。"""
    for params in ({"pageNo": 0, "pageSize": 20}, {"pageNo": 1, "pageSize": 999},
                   {"pageNo": -1, "pageSize": -5}):
        r = dev.get("/api/v1/workflows", params=params)
        assert r.status_code != 500, f"分页参数 {params} 触发 500: {r.text[:200]}"
        body = r.json()
        assert body.get("code") in (0, 10000), f"分页参数 {params} 返回 {body.get('code')}"
        if body.get("code") == 0:
            assert "records" in body["data"] and "total" in body["data"]


@pytest.mark.m1
@pytest.mark.p0
def test_m1_save_and_reload_30_nodes(dev):
    """M1：30 节点含条件分支的 DAG，保存后重载节点/连线/配置不丢。"""
    nodes = [{"id": "t1", "type": "mqtt-trigger", "name": "触发", "config": {}},
             {"id": "c1", "type": "condition", "name": "温度判断",
              "config": {"expression": "payload.temp > 80"}}]
    for i in range(1, 29):
        nodes.append({"id": f"s{i}", "type": "code", "name": f"步骤{i}",
                      "config": {"expression": f"payload.step{i} == {i}"}})
    edges = [{"source": "t1", "target": "c1", "branch": None},
             {"source": "c1", "target": "s1", "branch": "true"},
             {"source": "c1", "target": "s2", "branch": "false"}]
    for i in range(1, 28):
        edges.append({"source": f"s{i}", "target": f"s{i + 1}", "branch": None})

    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": "QA-M1-30节点"}))
    wf_id = wf["id"]
    try:
        ver = assert_ok(dev.post(f"/api/v1/workflows/{wf_id}/versions",
                                 json={"dslJson": _dsl(nodes, edges)}))
        loaded = assert_ok(dev.get(f"/api/v1/workflows/versions/{ver['id']}"))
        saved = json.loads(loaded["dslJson"])
        assert len(saved["nodes"]) == 30, f"节点数丢失: {len(saved['nodes'])}"
        assert len(saved["edges"]) == len(edges), f"连线数丢失: {len(saved['edges'])} != {len(edges)}"
        cfg = next(n for n in saved["nodes"] if n["id"] == "s28")["config"]
        assert cfg["expression"] == "payload.step28 == 28", f"节点配置丢失: {cfg}"
    finally:
        dev.delete(f"/api/v1/workflows/{wf_id}")


def test_dsl_unknown_node_type_rejected(dev, flow_factory):
    """反向：未知节点类型 → 20003。"""
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": "QA-DSL-未知类型"}))
    try:
        bad = {"nodes": [{"id": "x1", "type": "ocr-mock", "name": "x", "config": {}}], "edges": []}
        r = dev.post(f"/api/v1/workflows/{wf['id']}/versions", json={"dslJson": _dsl(bad["nodes"], bad["edges"])})
        # ocr-mock 不在 6 类合法节点内 → 20003
        assert_code(r, 20003, "未知节点类型")
    finally:
        dev.delete(f"/api/v1/workflows/{wf['id']}")


def test_dsl_cycle_rejected(dev):
    """反向：环形依赖 → 20002。"""
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": "QA-DSL-环"}))
    try:
        nodes = [{"id": "a", "type": "code", "name": "a", "config": {}},
                 {"id": "b", "type": "code", "name": "b", "config": {}}]
        edges = [{"source": "a", "target": "b", "branch": None},
                 {"source": "b", "target": "a", "branch": None}]
        r = dev.post(f"/api/v1/workflows/{wf['id']}/versions", json={"dslJson": _dsl(nodes, edges)})
        assert_code(r, 20002, "环形依赖")
    finally:
        dev.delete(f"/api/v1/workflows/{wf['id']}")


def test_dsl_dangling_edge_rejected(dev):
    """反向：连线指向不存在节点 → 20005。"""
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": "QA-DSL-悬空边"}))
    try:
        nodes = [{"id": "t1", "type": "mqtt-trigger", "name": "t", "config": {}}]
        edges = [{"source": "t1", "target": "ghost", "branch": None}]
        r = dev.post(f"/api/v1/workflows/{wf['id']}/versions", json={"dslJson": _dsl(nodes, edges)})
        assert_code(r, 20005, "悬空边")
    finally:
        dev.delete(f"/api/v1/workflows/{wf['id']}")


def test_dsl_condition_missing_false_branch_rejected(dev):
    """边界：condition 只覆盖 true 分支 → 20004。"""
    wf = assert_ok(dev.post("/api/v1/workflows", json={"name": "QA-DSL-分支缺失"}))
    try:
        nodes = [{"id": "t1", "type": "mqtt-trigger", "name": "t", "config": {}},
                 {"id": "c1", "type": "condition", "name": "c", "config": {"expression": "payload.x > 1"}},
                 {"id": "s1", "type": "code", "name": "s", "config": {}}]
        edges = [{"source": "t1", "target": "c1", "branch": None},
                 {"source": "c1", "target": "s1", "branch": "true"}]
        r = dev.post(f"/api/v1/workflows/{wf['id']}/versions", json={"dslJson": _dsl(nodes, edges)})
        assert_code(r, 20004, "条件分支缺失")
    finally:
        dev.delete(f"/api/v1/workflows/{wf['id']}")


def test_version_publish_disable_state_machine(dev, flow_factory):
    """正向：draft→published→disabled→published（灰度锚点可回切）；draft 直接禁用 → 20010。"""
    flow = flow_factory(publish=False)
    ver_id = flow["versionId"]

    # 非法流转：draft 直接禁用
    assert_code(dev.put(f"/api/v1/workflows/versions/{ver_id}/disable"), 20010, "draft 直接禁用")
    assert_ok(dev.put(f"/api/v1/workflows/versions/{ver_id}/publish"), "发布")
    assert_ok(dev.put(f"/api/v1/workflows/versions/{ver_id}/disable"), "禁用")
    # 设计口径（WorkflowService.publish）：disabled 可重新发布，作为灰度回切锚点
    assert_ok(dev.put(f"/api/v1/workflows/versions/{ver_id}/publish"), "禁用后重新发布")


def test_version_not_found(dev):
    """反向：版本不存在 → 20007。"""
    r = dev.get("/api/v1/workflows/versions/999999999")
    assert_code(r, 20007, "版本不存在")
