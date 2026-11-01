"""第 9 步 · Agent 辅助走查脚本（接口级实测，不替代用户人工走查）
覆盖 A 基础可用性 / B 核心链路 / C 基线与隔离权限 / 幂等 / 配额台账。
"""
import json
import time
import uuid

import httpx

B = "http://localhost:8083"
AGENT = "http://localhost:8085"
R = []


def rec(tag, ok, detail):
    R.append((tag, ok, detail))
    print(f"[{tag}] {'PASS' if ok else 'FAIL'} | {detail}", flush=True)


def login(u, p="Swa@123456"):
    r = httpx.post(f"{B}/api/v1/auth/login", json={"username": u, "password": p}, timeout=10)
    d = r.json()
    return d["data"]["token"] if d.get("code") == 0 else None


def H(t):
    return {"Authorization": f"Bearer {t}"}


def main():
    # ---------- A1 未登录 ----------
    r = httpx.get(f"{B}/api/v1/workflows", timeout=10)
    rec("A1 未登录访问", r.status_code == 401, f"HTTP {r.status_code} {r.text[:80]}")

    # ---------- A2 登录 + 角色 ----------
    at = login("admin_acme")
    me = httpx.get(f"{B}/api/v1/auth/me", headers=H(at), timeout=10).json()
    rec("A2 admin 登录+me", at is not None and me.get("code") == 0, str(me.get("data"))[:120])

    devt = login("dev_acme")
    vwt = login("viewer_acme")
    gt = login("dev_globex")
    rec("A2b 多账号登录", all([devt, vwt, gt]), "dev_acme/viewer_acme/dev_globex 均登录成功")

    # ---------- A3 新建流程 ----------
    name = f"验收走查-全节点-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{B}/api/v1/workflows", headers=H(at),
                   json={"name": name, "description": "覆盖 6 类节点/双分支/延时/Agent"}, timeout=10).json()
    wid = r["data"]["id"]
    rec("A3 新建流程", r.get("code") == 0, f"id={wid} name={name}")

    lst = httpx.get(f"{B}/api/v1/workflows", headers=H(at), params={"name": "验收走查"}, timeout=10).json()
    rec("A3b 列表可搜到", any(x["id"] == wid for x in lst["data"]["records"]), f"total={lst['data']['total']}")

    # ---------- A7 空态 ----------
    e = httpx.get(f"{B}/api/v1/workflows", headers=H(at), params={"name": "不存在xyz"}, timeout=10).json()
    rec("A7 搜索空态", e["data"]["total"] == 0, f"total={e['data']['total']}")

    # ---------- A4 保存 DSL（6 类节点 + 双分支） ----------
    dsl = {
        "nodes": [
            {"id": "t1", "type": "mqtt-trigger", "name": "温度采集", "config": {}},
            {"id": "c1", "type": "condition", "name": "高温判断", "config": {"expression": "t1.payload.temp > 80"}},
            {"id": "h1", "type": "http", "name": "告警通知",
             "config": {"url": "http://127.0.0.1:8083/actuator/health", "method": "GET", "timeoutMs": 10000}},
            {"id": "d1", "type": "code", "name": "正常记录", "config": {"expression": "'normal: ' + t1.payload.temp"}},
            {"id": "dly1", "type": "delay", "name": "延时5秒", "config": {"delayMs": 5000}},
            {"id": "a1", "type": "agent", "name": "智能研判",
             "config": {"task": "用中文一句话总结本次温度读数并判断是否需要告警"}},
        ],
        "edges": [
            {"source": "t1", "target": "c1"},
            {"source": "c1", "target": "h1", "branch": "true"},
            {"source": "h1", "target": "dly1"},
            {"source": "dly1", "target": "a1"},
            {"source": "c1", "target": "d1", "branch": "false"},
        ],
    }
    r = httpx.post(f"{B}/api/v1/workflows/{wid}/versions", headers=H(at),
                   json={"dslJson": json.dumps(dsl, ensure_ascii=False)}, timeout=15).json()
    vid = r["data"]["id"]
    rec("A4 保存 6 节点 DSL", r.get("code") == 0, f"versionId={vid}")

    # A4b 重载不丢
    g = httpx.get(f"{B}/api/v1/workflows/versions/{vid}", headers=H(at), timeout=10).json()["data"]
    back = json.loads(g["dslJson"])
    ok = len(back["nodes"]) == 6 and len(back["edges"]) == 5 and back["nodes"][4]["config"]["delayMs"] == 5000
    rec("A4b 重载一致", ok, f"nodes={len(back['nodes'])} edges={len(back['edges'])}")

    # ---------- A5 发布 ----------
    p = httpx.put(f"{B}/api/v1/workflows/versions/{vid}/publish", headers=H(at), timeout=10).json()
    rec("A5 发布版本", p.get("code") == 0 and p["data"]["status"] == "published", f"status={p['data']['status']}")

    # ---------- B2 执行：true 分支（http→delay→agent 真调 LLM） ----------
    creq = uuid.uuid4().hex[:16]
    ex = httpx.post(f"{B}/api/v1/executions", headers=H(at),
                    json={"versionId": vid, "clientReqId": creq,
                          "triggerPayload": json.dumps({"temp": 95})}, timeout=15).json()
    eid = ex["data"]["id"]
    rec("B2 创建执行", ex.get("code") == 0, f"executionId={eid}")

    # 幂等重发
    ex2 = httpx.post(f"{B}/api/v1/executions", headers=H(at),
                     json={"versionId": vid, "clientReqId": creq,
                           "triggerPayload": json.dumps({"temp": 95})}, timeout=15).json()
    rec("B2b 幂等 clientReqId", ex2["data"]["id"] == eid, f"重发得到同一 id={ex2['data']['id']}")

    # SSE 观测
    sse_lines = []
    try:
        with httpx.stream("GET", f"{B}/api/v1/executions/{eid}/events", headers=H(at), timeout=30) as s:
            for i, line in enumerate(s.iter_lines()):
                if line.strip():
                    sse_lines.append(line.strip())
                if len(sse_lines) >= 6 or i > 80:
                    break
    except Exception as ex_:
        sse_lines.append(f"SSE异常:{type(ex_).__name__}")
    rec("B2c SSE 实时事件", any("event" in x or "data" in x for x in sse_lines), f"{len(sse_lines)} 行: {sse_lines[:4]}")

    # 轮询执行终态
    status, nodes = None, []
    t0 = time.time()
    while time.time() - t0 < 150:
        d = httpx.get(f"{B}/api/v1/executions/{eid}", headers=H(at), timeout=10).json()["data"]
        status = d["status"]
        nodes = httpx.get(f"{B}/api/v1/executions/{eid}/nodes", headers=H(at), timeout=10).json()["data"]
        if status in ("SUCCESS", "FAILED", "PARTIAL_FAILED"):
            break
        time.sleep(3)
    nd = {n["nodeId"]: (n["status"], str(n.get("output"))[:70]) for n in nodes}
    rec("B2d 执行终态", status == "SUCCESS", f"status={status} 耗时={int(time.time()-t0)}s")
    rec("B2e 节点快照", len(nodes) >= 4, f"{nd}")

    # 延时节点 WAITING 观测：单独再跑一次并在 2 秒内抓
    creq2 = uuid.uuid4().hex[:16]
    exd = httpx.post(f"{B}/api/v1/executions", headers=H(at),
                     json={"versionId": vid, "clientReqId": creq2,
                           "triggerPayload": json.dumps({"temp": 95})}, timeout=15).json()
    eid2 = exd["data"]["id"]
    saw_waiting, wait_snap = False, {}
    t1 = time.time()
    while time.time() - t1 < 25:
        n2 = httpx.get(f"{B}/api/v1/executions/{eid2}/nodes", headers=H(at), timeout=10).json()["data"]
        wait_snap = {n["nodeId"]: n["status"] for n in n2}
        if wait_snap.get("dly1") == "WAITING":
            saw_waiting = True
            break
        time.sleep(1)
    rec("B7 延时节点 WAITING", saw_waiting, f"{wait_snap}")
    # 等恢复
    t2 = time.time()
    while time.time() - t2 < 120:
        d2 = httpx.get(f"{B}/api/v1/executions/{eid2}", headers=H(at), timeout=10).json()["data"]
        if d2["status"] in ("SUCCESS", "FAILED", "PARTIAL_FAILED"):
            break
        time.sleep(3)
    rec("B7b 延时后恢复完成", d2["status"] == "SUCCESS", f"status={d2['status']} 等待={int(time.time()-t2)}s")

    # Agent 真调校验
    agent_node = next((n for n in nodes if n["nodeId"] == "a1"), None)
    out = json.loads(agent_node["output"]) if agent_node and agent_node.get("output") else {}
    rec("B5 Agent 真调 LLM", bool(out.get("output")),
        f"reasoning={str(out.get('reasoning'))[:60]} output={str(out.get('output'))[:80]}")

    # ---------- B4 false 分支 ----------
    creq3 = uuid.uuid4().hex[:16]
    ex3 = httpx.post(f"{B}/api/v1/executions", headers=H(at),
                     json={"versionId": vid, "clientReqId": creq3,
                           "triggerPayload": json.dumps({"temp": 25})}, timeout=15).json()
    eid3 = ex3["data"]["id"]
    t3 = time.time()
    while time.time() - t3 < 60:
        d3 = httpx.get(f"{B}/api/v1/executions/{eid3}", headers=H(at), timeout=10).json()["data"]
        if d3["status"] in ("SUCCESS", "FAILED", "PARTIAL_FAILED"):
            break
        time.sleep(2)
    n3 = {n["nodeId"]: n["status"] for n in
          httpx.get(f"{B}/api/v1/executions/{eid3}/nodes", headers=H(at), timeout=10).json()["data"]}
    rec("B4 false 分支", d3["status"] == "SUCCESS" and n3.get("d1") == "SUCCESS" and "h1" not in n3,
        f"status={d3['status']} nodes={n3}")

    # ---------- B3 回放 ----------
    rp = httpx.post(f"{B}/api/v1/executions/{eid}/replay", headers=H(at), timeout=15).json()
    rec("B3 回放产生新实例", rp.get("code") == 0 and rp["data"]["id"] != eid, f"newId={rp['data']['id']}")

    # ---------- C4/C5 台账与 NL ----------
    q = httpx.get(f"{B}/api/v1/quota", headers=H(at), timeout=10).json()
    lc = httpx.get(f"{B}/api/v1/quota/llm-calls", headers=H(at), timeout=10).json()
    rec("C4 LLM 台账", lc["data"]["total"] >= 2, f"llm_call_log={lc['data']['total']} quota={q['data']}")

    nl = httpx.post(f"{B}/api/v1/workflows/nl-draft", headers=H(at),
                    json={"text": "当设备温度超过 80 度时发 HTTP 告警，否则记录到日志",
                          "workflowName": "NL验收-温度告警"}, timeout=120).json()
    nl_dsl = json.loads(nl["data"]["dslJson"]) if nl.get("code") == 0 else {}
    rec("C5 NL 生成流程", nl.get("code") == 0 and len(nl_dsl.get("nodes", [])) >= 2,
        f"nodes={[(n['id'], n['type']) for n in nl_dsl.get('nodes', [])]}")

    # ---------- A6 退出重登数据仍在 ----------
    httpx.post(f"{B}/api/v1/auth/logout", headers=H(at), timeout=10)
    at2 = login("admin_acme")
    a6 = httpx.get(f"{B}/api/v1/workflows/{wid}", headers=H(at2), timeout=10).json()
    rec("A6 退出重登数据仍在", a6.get("code") == 0 and a6["data"]["name"] == name, a6["data"]["name"])

    # ---------- C7 多租户隔离 ----------
    gw = httpx.get(f"{B}/api/v1/workflows", headers=H(gt), timeout=10).json()
    ids = [x["name"] for x in gw["data"]["records"]]
    rec("C7 跨租户不可见", name not in ids, f"globex 可见={ids}")
    cross = httpx.get(f"{B}/api/v1/workflows/{wid}", headers=H(gt), timeout=10)
    rec("C7b 跨租户直连 403/404", cross.status_code in (403, 404) or cross.json().get("code") in (10403, 10404),
        f"HTTP {cross.status_code} {cross.text[:80]}")

    # ---------- C8 viewer 只读 ----------
    vc = httpx.post(f"{B}/api/v1/workflows", headers=H(vwt), json={"name": "viewer越权建"}, timeout=10)
    rec("C8 viewer 建流程被拒", vc.status_code == 403 or vc.json().get("code") == 10403,
        f"HTTP {vc.status_code} {vc.text[:70]}")
    vl = httpx.get(f"{B}/api/v1/workflows", headers=H(vwt), timeout=10)
    rec("C8b viewer 可读列表", vl.status_code == 200 and vl.json().get("code") == 0, f"HTTP {vl.status_code}")

    # ---------- B6 MQTT ----------
    try:
        import paho.mqtt.client as mqtt
        pub = mqtt.Client(client_id="swa-acc-test")
        pub.connect("127.0.0.1", 1883, 10)
        pub.loop_start()
        before = httpx.get(f"{B}/api/v1/executions", headers=H(at2), timeout=10).json()["data"]["total"]
        pub.publish("factory/line1/temperature", json.dumps({"temp": 95}), qos=1)
        time.sleep(6)
        pub.loop_stop()
        after = httpx.get(f"{B}/api/v1/executions", headers=H(at2), timeout=10).json()["data"]["total"]
        rec("B6 MQTT 触发新实例", after > before, f"executions {before} → {after}")
    except Exception as ex_:
        rec("B6 MQTT 触发", False, f"异常 {type(ex_).__name__}: {ex_}")

    # ---------- A5 删除 ----------
    dl = httpx.delete(f"{B}/api/v1/workflows/{wid}", headers=H(at2), timeout=10).json()
    gone = httpx.get(f"{B}/api/v1/workflows", headers=H(at2), params={"name": "验收走查"}, timeout=10).json()
    rec("A5 删除流程", dl.get("code") == 0 and gone["data"]["total"] == 0, f"total={gone['data']['total']}")

    # ---------- 汇总 ----------
    print("\n===== 汇总 =====")
    bad = [x for x in R if not x[1]]
    print(f"共 {len(R)} 项，PASS {len(R)-len(bad)}，FAIL {len(bad)}")
    for t, ok, d in bad:
        print(f"FAIL {t} :: {d}")


if __name__ == "__main__":
    main()
