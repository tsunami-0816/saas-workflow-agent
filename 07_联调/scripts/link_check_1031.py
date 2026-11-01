# -*- coding: utf-8 -*-
"""
第 7 步全链路联调脚本（saas-workflow-agent · 2026-10-31）
覆盖：认证权限 / 流程 CRUD / DSL 负向 / 版本门槛 / 主执行链 / 幂等 / SSE / 回放 /
      延时恢复 / 失败路径 / Agent 计量 / NL 生成 / MQTT / 额度台账 / 内部接口 / 跨租户 / 租户用户凭据
证据：07_联调/evidence/1031/link_result.json
"""
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import redis
import requests

BASE = "http://127.0.0.1:8083"
API = BASE + "/api/v1"
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "evidence" / "1031"
OUT.mkdir(parents=True, exist_ok=True)

R = redis.Redis(host="127.0.0.1", port=6379, db=3, decode_responses=True)
RESULTS = []
ART = {}
TS = time.strftime("%H%M%S")


def http(method, path, token=None, body=None, stream=False, timeout=30):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    url = path if path.startswith("http") else API + path
    return requests.request(method, url, headers=headers, json=body, timeout=timeout, stream=stream)


def api(method, path, token=None, body=None, timeout=30):
    r = http(method, path, token, body, timeout=timeout)
    try:
        data = r.json()
    except Exception:
        data = {"code": -1, "message": r.text[:200]}
    return r.status_code, data


def ok_code(data):
    return data.get("code") == 0


def login(username, password="Swa@123456"):
    sc, d = api("POST", "/auth/login", body={"username": username, "password": password})
    assert ok_code(d), f"login {username} failed: {d}"
    return d["data"]["token"]


def db(sql):
    p = subprocess.run(
        ["docker", "exec", "swa-mysql", "mysql", "-uswa", "-pswa123",
         "--default-character-set=utf8mb4", "-N", "-e", "USE swa; " + sql],
        capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return [ln.split("\t") for ln in p.stdout.strip().splitlines() if ln.strip()]


def dsl(nodes, edges):
    return {
        "nodes": [{"id": i, "type": t, "name": n, "config": c} for i, t, n, c in nodes],
        "edges": [{"source": s, "target": t, "branch": b} for s, t, b in edges],
    }


def create_wf(token, name, desc=""):
    sc, d = api("POST", "/workflows", token, {"name": name, "description": desc})
    assert ok_code(d), f"create workflow failed: {d}"
    return d["data"]["id"]


def save_ver(token, wf_id, d):
    sc, r = api("POST", f"/workflows/{wf_id}/versions", token, {"dslJson": json.dumps(d, ensure_ascii=False)})
    assert ok_code(r), f"save version failed: {r}"
    return r["data"]["id"]


def publish(token, vid):
    return api("PUT", f"/workflows/versions/{vid}/publish", token)


def execute(token, vid, payload, req_id=None):
    req_id = req_id or f"link-{TS}-{uuid.uuid4().hex[:6]}"
    return api("POST", "/executions", token,
               {"versionId": vid, "clientReqId": req_id, "triggerPayload": json.dumps(payload)})


def exec_detail(token, eid):
    sc, d = api("GET", f"/executions/{eid}", token)
    return d.get("data") or {}


def node_map(token, eid):
    sc, d = api("GET", f"/executions/{eid}/nodes", token)
    out = {}
    for n in d.get("data") or []:
        o = n.get("outputJson")
        if isinstance(o, str):
            try:
                o = json.loads(o)
            except Exception:
                pass
        n["outputJson"] = o
        out[n["nodeId"]] = n
    return out


def wait_exec(token, eid, timeout=120, allow_waiting=False):
    t0 = time.time()
    last = {}
    while time.time() - t0 < timeout:
        last = exec_detail(token, eid)
        st = last.get("status")
        if st in ("SUCCESS", "FAILED"):
            return last, time.time() - t0
        if allow_waiting and st == "WAITING":
            return last, time.time() - t0
        time.sleep(0.4)
    return last, time.time() - t0


def audit_counts():
    rows = db("SELECT action, COUNT(*) FROM audit_log GROUP BY action;")
    return {r[0]: int(r[1]) for r in rows if len(r) == 2}


def case(cid, title, fn):
    checks = []

    def ck(name, cond, detail=""):
        checks.append({"name": name, "ok": bool(cond), "detail": str(detail)})

    t0 = time.time()
    try:
        fn(ck)
    except Exception as e:
        checks.append({"name": "case exception", "ok": False, "detail": repr(e)})
    passed = all(c["ok"] for c in checks)
    RESULTS.append({"id": cid, "title": title, "passed": passed,
                    "seconds": round(time.time() - t0, 2), "checks": checks})
    print(f"[{'PASS' if passed else 'FAIL'}] {cid} {title}")
    for c in checks:
        if not c["ok"]:
            print(f"       ✗ {c['name']} :: {c['detail']}")


# ---------------- L-01 认证与权限矩阵 ----------------
def l01(ck):
    tokens = {}
    for u in ("admin_acme", "dev_acme", "viewer_acme", "admin_globex"):
        tokens[u] = login(u)
    ART["tokens_ok"] = {u: bool(t) for u, t in tokens.items()}
    ck("三角色+跨租户 4 账号登录", all(tokens.values()))
    sc, d = api("GET", "/workflows")
    ck("无 token 访问 → 401", sc == 401, f"status={sc}")
    sc, d = api("POST", "/workflows", tokens["viewer_acme"], {"name": "link-viewer-should-fail"})
    ck("viewer 创建流程 → 403/10403", sc == 403 or d.get("code") == 10403, f"{sc} {d.get('code')}")
    sc, d = api("GET", "/quota/audit-logs", tokens["viewer_acme"])
    ck("viewer 查审计日志 → 403/10403", sc == 403 or d.get("code") == 10403, f"{sc} {d.get('code')}")
    ART["tokens"] = tokens


# ---------------- L-02 流程 CRUD + 审计 ----------------
def l02(ck):
    tok = ART["tokens"]["dev_acme"]
    before = audit_counts()
    wf = create_wf(tok, f"联调-CRUD-{TS}", "CRUD 全链")
    sc, d = api("GET", f"/workflows/{wf}", tok)
    ck("创建后详情可读", ok_code(d) and d["data"]["id"] == wf, d.get("code"))
    ck("BUG-001 回填 tenantId", d["data"].get("tenantId") == 1, d["data"].get("tenantId"))
    sc, d = api("PUT", f"/workflows/{wf}", tok, {"name": f"联调-CRUD-改名-{TS}", "description": "updated"})
    ck("更新流程成功", ok_code(d), d.get("code"))
    sc, d = api("GET", f"/workflows?pageNo=1&pageSize=20&name=联调-CRUD-改名", tok)
    ck("列表按名称搜索命中", ok_code(d) and len(d["data"]["records"]) >= 1,
       d.get("data", {}).get("total"))
    sc, d = api("DELETE", f"/workflows/{wf}", tok)
    ck("删除流程成功", ok_code(d), d.get("code"))
    sc, d = api("GET", f"/workflows/{wf}", tok)
    ck("删除后详情 → 20001", d.get("code") == 20001, d.get("code"))
    after = audit_counts()
    ck("审计 workflow.create +1", after.get("workflow.create", 0) == before.get("workflow.create", 0) + 1,
       f"{before.get('workflow.create')}->{after.get('workflow.create')}")
    ck("审计 workflow.update +1", after.get("workflow.update", 0) == before.get("workflow.update", 0) + 1,
       f"{before.get('workflow.update')}->{after.get('workflow.update')}")
    ck("审计 workflow.delete +1", after.get("workflow.delete", 0) == before.get("workflow.delete", 0) + 1,
       f"{before.get('workflow.delete')}->{after.get('workflow.delete')}")
    ck("DB 逻辑删 deleted=1", db(f"SELECT deleted FROM workflow WHERE id={wf};")[0][0] == "1")


# ---------------- L-03 DSL 负向校验 ----------------
def l03(ck):
    tok = ART["tokens"]["dev_acme"]
    wf = create_wf(tok, f"联调-DSL负向-{TS}")
    cases = {
        "环形依赖": (dsl([("t1", "mqtt-trigger", "触发", {}),
                          ("delay1", "delay", "延时A", {"delayMs": 1000}),
                          ("delay2", "delay", "延时B", {"delayMs": 1000})],
                         [("t1", "delay1", None), ("delay1", "delay2", None), ("delay2", "delay1", None)]), 20002),
        "未知节点类型": (dsl([("x1", "ocr-mock", "假节点", {})], []), 20003),
        "连线指向不存在节点": (dsl([("t1", "mqtt-trigger", "触发", {})], [("t1", "ghost", None)]), 20005),
    }
    got = {}
    for name, (d, expect) in cases.items():
        sc, r = api("POST", f"/workflows/{wf}/versions", tok, {"dslJson": json.dumps(d, ensure_ascii=False)})
        got[name] = r.get("code")
        ck(f"{name} → {expect}", r.get("code") == expect, r.get("code"))
    ART["dsl_negative"] = got


# ---------------- L-04 版本状态门槛 ----------------
def l04(ck):
    tok = ART["tokens"]["dev_acme"]
    wf = create_wf(tok, f"联调-版本门槛-{TS}")
    vid = save_ver(tok, wf, dsl([("t1", "mqtt-trigger", "触发", {})], []))
    sc, d = api("POST", "/executions", tok, {"versionId": vid, "clientReqId": f"link-draft-{TS}",
                                             "triggerPayload": "{}"})
    ck("draft 版本不可执行 → 20009", d.get("code") == 20009, d.get("code"))
    sc, d = publish(tok, vid)
    ck("发布 draft→published", ok_code(d) and d["data"]["status"] == "published",
       d.get("data", {}).get("status"))
    sc, d = api("PUT", f"/workflows/versions/{vid}/disable", tok)
    ck("禁用 published→disabled", ok_code(d) and d["data"]["status"] == "disabled",
       d.get("data", {}).get("status"))
    sc, d = api("POST", "/executions", tok, {"versionId": vid, "clientReqId": f"link-disabled-{TS}",
                                             "triggerPayload": "{}"})
    ck("disabled 版本不可执行 → 20008", d.get("code") == 20008, d.get("code"))
    rows = db(f"SELECT status FROM workflow_version WHERE id={vid};")
    ck("DB 版本状态一致", rows and rows[0][0] == "disabled", rows)


# ---------------- L-05 主执行链 / 幂等 / SSE / 回放 ----------------
def l05(ck):
    tok = ART["tokens"]["dev_acme"]
    wf = create_wf(tok, f"联调-主链路-{TS}")
    expire = dsl(
        [("t1", "mqtt-trigger", "温度采集", {}),
         ("c1", "condition", "高温判断", {"expression": "t1.payload.temp > 80"}),
         ("h1", "http", "健康检查", {"url": BASE + "/actuator/health", "method": "GET", "timeoutMs": 10000}),
         ("d1", "code", "正常记录", {"expression": "'normal: ' + t1.payload.temp"})],
        [("t1", "c1", None), ("c1", "h1", "true"), ("c1", "d1", "false")])
    vid = save_ver(tok, wf, expire)
    publish(tok, vid)
    ART["main_version"] = vid

    payload = {"temp": 95}
    sc, d = execute(tok, vid, payload, f"link-main-{TS}")
    eid = d["data"]["id"]
    ART["main_exec"] = eid
    detail, cost = wait_exec(tok, eid, 30)
    ck("true 分支执行 SUCCESS", detail.get("status") == "SUCCESS", detail.get("status"))
    nodes = node_map(tok, eid)
    ck("c1 判定 branch=true", nodes["c1"]["outputJson"].get("branch") is True, nodes["c1"]["outputJson"])
    ck("h1 SUCCESS / d1 SKIPPED",
       nodes["h1"]["status"] == "SUCCESS" and nodes["d1"]["status"] == "SKIPPED",
       f"h1={nodes['h1']['status']} d1={nodes['d1']['status']}")
    rows = db(f"SELECT tenant_id,status,fail_reason,ended_at FROM execution WHERE id={eid};")
    ck("DB 执行行租户/终态/结束时间", rows and rows[0][0] == "1" and rows[0][1] == "SUCCESS" and rows[0][3],
       rows)
    ck("DB 节点行数=4", len(db(f"SELECT id FROM node_execution WHERE execution_id={eid};")) == 4)

    sc, d2 = execute(tok, vid, payload, f"link-main-{TS}")
    ck("同 clientReqId 幂等复用实例", d2.get("code") == 0 and d2["data"]["id"] == eid,
       f"{d2.get('code')} id={d2.get('data', {}).get('id')}")

    # SSE：新执行 temp=60，立刻订阅
    sc, d3 = execute(tok, vid, {"temp": 60}, f"link-sse-{TS}")
    sid = d3["data"]["id"]
    r = http("GET", f"/executions/{sid}/events", tok, stream=True, timeout=8)
    events = set()
    t0 = time.time()
    try:
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("event:"):
                events.add(line.split(":", 1)[1].strip())
            if time.time() - t0 > 6:
                break
    except requests.exceptions.RequestException:
        # SSE 长连接在事件停止后读超时属预期行为，保留已收集事件
        pass
    finally:
        r.close()
    ck("SSE 收到 connected", "connected" in events, events)
    ck("SSE 收到 node/execution 事件", ("node" in events) or ("execution" in events), events)
    ART["sse_events"] = sorted(events)
    wait_exec(tok, sid, 30)
    snodes = node_map(tok, sid)
    ck("false 分支 d1 SUCCESS / h1 SKIPPED",
       snodes["d1"]["status"] == "SUCCESS" and snodes["h1"]["status"] == "SKIPPED",
       f"d1={snodes['d1']['status']} h1={snodes['h1']['status']}")

    sc, d = api("POST", f"/executions/{eid}/replay", tok, {})
    rid = d.get("data", {}).get("id")
    ck("回放创建新实例", ok_code(d) and rid and rid != eid, f"{d.get('code')} rid={rid}")
    rd = exec_detail(tok, rid)
    ck("回放保留触发参数", "95" in str(rd.get("triggerPayload")), rd.get("triggerPayload"))
    wait_exec(tok, rid, 30)
    ART["replay_exec"] = rid


# ---------------- L-06 延时节点 WAITING → 恢复 ----------------
def l06(ck):
    tok = ART["tokens"]["dev_acme"]
    wf = create_wf(tok, f"联调-延时-{TS}")
    d = dsl(
        [("t1", "mqtt-trigger", "触发", {}),
         ("delay1", "delay", "延时3秒", {"delayMs": 3000}),
         ("d1", "code", "收尾", {"expression": "'delay done'"})],
        [("t1", "delay1", None), ("delay1", "d1", None)])
    vid = save_ver(tok, wf, d)
    publish(tok, vid)
    t_create = time.time()
    sc, r = execute(tok, vid, {"temp": 70}, f"link-delay-{TS}")
    eid = r["data"]["id"]
    time.sleep(1.2)
    detail = exec_detail(tok, eid)
    nodes = node_map(tok, eid)
    ck("1.2s 时执行 WAITING", detail.get("status") == "WAITING", detail.get("status"))
    ck("delay1 节点 WAITING", nodes["delay1"]["status"] == "WAITING", nodes["delay1"]["status"])
    detail, _ = wait_exec(tok, eid, 25)
    nodes = node_map(tok, eid)
    ck("延时到点后执行 SUCCESS", detail.get("status") == "SUCCESS", detail.get("status"))
    ck("delay1 SUCCESS 且 resumed=true",
       nodes["delay1"]["status"] == "SUCCESS" and nodes["delay1"]["outputJson"].get("resumed") is True,
       f"{nodes['delay1']['status']} {nodes['delay1']['outputJson']}")
    ck("下游 d1 SUCCESS", nodes["d1"]["status"] == "SUCCESS", nodes["d1"]["status"])
    # 时延从创建执行时刻起算（含 1.2s 观察点 + 3s 延时 + 轮询粒度）
    elapsed = time.time() - t_create
    ck("恢复总时延 2.5~20s", 2.5 <= elapsed <= 20, f"{elapsed:.2f}s")
    ART["delay_seconds"] = round(elapsed, 2)


# ---------------- L-07 节点失败路径 ----------------
def l07(ck):
    tok = ART["tokens"]["dev_acme"]
    wf = create_wf(tok, f"联调-失败路径-{TS}")
    d = dsl([("t1", "mqtt-trigger", "触发", {}),
             ("h1", "http", "不可达接口", {"url": "http://127.0.0.1:65535/x", "method": "GET", "timeoutMs": 3000})],
            [("t1", "h1", None)])
    vid = save_ver(tok, wf, d)
    publish(tok, vid)
    sc, r = execute(tok, vid, {"temp": 1}, f"link-fail-{TS}")
    eid = r["data"]["id"]
    detail, cost = wait_exec(tok, eid, 40)
    ck("执行收敛 FAILED", detail.get("status") == "FAILED", detail.get("status"))
    ck("failReason=node_failed", detail.get("failReason") == "node_failed", detail.get("failReason"))
    nodes = node_map(tok, eid)
    ck("h1 节点 FAILED", nodes["h1"]["status"] == "FAILED", nodes["h1"]["status"])
    ck("h1 errorMessage 非空", bool(nodes["h1"].get("errorMessage")), nodes["h1"].get("errorMessage"))
    rl = nodes["h1"].get("retryLog")
    if isinstance(rl, str):
        try:
            rl = json.loads(rl)
        except Exception:
            rl = []
    ck("重试记录 ≥2 次", isinstance(rl, list) and len(rl) >= 2, len(rl) if isinstance(rl, list) else rl)
    ART["fail_seconds"] = round(cost, 2)


# ---------------- L-08 Agent 全链 + 计量一致性 ----------------
def l08(ck):
    tok = ART["tokens"]["dev_acme"]
    wf = create_wf(tok, f"联调-Agent-{TS}")
    d = dsl([("t1", "mqtt-trigger", "触发", {}),
             ("a1", "agent", "智能体", {"task": "用中文一句话解释什么是工作流引擎的幂等触发",
                                        "taskType": "agent_reasoning"})],
            [("t1", "a1", None)])
    vid = save_ver(tok, wf, d)
    publish(tok, vid)
    before_log = int(db("SELECT COUNT(*) FROM llm_call_log;")[0][0])
    before_quota = [int(x) for x in db("SELECT token_total, token_used FROM tenant_quota WHERE tenant_id=1;")[0]]
    before_redis = int(R.get("quota:remain:1") or 0)
    sc, r = execute(tok, vid, {"temp": 88}, f"link-agent-{TS}")
    eid = r["data"]["id"]
    detail, cost = wait_exec(tok, eid, 150)
    ck("Agent 执行 SUCCESS", detail.get("status") == "SUCCESS", f"{detail.get('status')} {detail.get('failReason')}")
    nodes = node_map(tok, eid)
    ck("a1 SUCCESS", nodes["a1"]["status"] == "SUCCESS", nodes["a1"]["status"])
    ck("a1 含 reasoning", bool(nodes["a1"]["outputJson"].get("reasoning")),
       str(nodes["a1"]["outputJson"].get("reasoning"))[:80])
    ck("a1 含 durationMs", nodes["a1"]["outputJson"].get("durationMs") is not None,
       nodes["a1"]["outputJson"].get("durationMs"))
    after_log = int(db("SELECT COUNT(*) FROM llm_call_log;")[0][0])
    rows = db(f"SELECT tenant_id,provider,model,task_type,prompt_tokens,completion_tokens FROM llm_call_log WHERE id>{before_log};")
    ck("新增 LLM 台账 ≥1 行", after_log - before_log >= 1, after_log - before_log)
    ck("台账归租=1 且 dashscope",
       all(rw[0] == "1" and rw[1] == "dashscope" for rw in rows), rows[:3])
    tokens = sum(int(rw[4]) + int(rw[5]) for rw in rows)
    after_quota = [int(x) for x in db("SELECT token_total, token_used FROM tenant_quota WHERE tenant_id=1;")[0]]
    ck("tenant_quota.token_used 增量=台账 token 增量",
       after_quota[1] - before_quota[1] == tokens, f"{before_quota[1]}->{after_quota[1]} vs {tokens}")
    after_redis = int(R.get("quota:remain:1") or 0)
    ck("Redis 余额下降=台账 token 增量", before_redis - after_redis == tokens,
       f"{before_redis}->{after_redis} vs {tokens}")
    ART["agent_seconds"] = round(cost, 2)
    ART["llm_rows"] = len(rows)


# ---------------- L-09 NL 生成全链 ----------------
def l09(ck):
    tok = ART["tokens"]["dev_acme"]
    before = int(db("SELECT COUNT(*) FROM llm_call_log WHERE task_type='nl2flow';")[0][0])
    sc, d = api("POST", "/workflows/nl-draft", tok,
                {"text": "收到工厂温度消息后，温度超过80度就调用 http://127.0.0.1:8083/actuator/health 告警，否则记录正常",
                 "workflowName": f"联调-NL-{TS}"}, timeout=120)
    ck("NL-draft code=0", ok_code(d), f"{d.get('code')} {d.get('message')}")
    ver = d.get("data") or {}
    dsl_obj = json.loads(ver.get("dslJson") or "{}")
    ck("生成 DSL 可解析且含节点/边", len(dsl_obj.get("nodes") or []) >= 2 and len(dsl_obj.get("edges") or []) >= 1,
       f"nodes={len(dsl_obj.get('nodes') or [])} edges={len(dsl_obj.get('edges') or [])}")
    ck("版本为 draft", ver.get("status") == "draft", ver.get("status"))
    sc, d2 = api("GET", f"/workflows/versions/{ver.get('id')}", tok)
    ck("回读版本 dslJson 一致", ok_code(d2) and d2["data"]["dslJson"] == ver.get("dslJson"))
    after = int(db("SELECT COUNT(*) FROM llm_call_log WHERE task_type='nl2flow';")[0][0])
    ck("新增 nl2flow 台账", after - before >= 1, after - before)
    ART["nl_version"] = ver.get("id")


# ---------------- L-10 MQTT 订阅 + e2e + 停用 ----------------
def l10(ck):
    tok = ART["tokens"]["dev_acme"]
    vid = ART["main_version"]
    topic = f"link/{TS}/temperature"
    base_max = int(db("SELECT IFNULL(MAX(id),0) FROM execution;")[0][0])
    sc, d = api("POST", "/mqtt/subscriptions", tok, {"topic": topic, "workflowVersionId": vid, "status": "active"})
    ck("创建订阅成功", ok_code(d), f"{d.get('code')} {d.get('message')}")
    sid = d.get("data", {}).get("id")
    sc, d2 = api("POST", "/mqtt/subscriptions", tok, {"topic": topic, "workflowVersionId": vid, "status": "active"})
    ck("重复 topic 冲突", not ok_code(d2), d2.get("message"))
    subprocess.run(["docker", "exec", "swa-mosquitto", "mosquitto_pub", "-h", "localhost",
                    "-t", topic, "-m", json.dumps({"temp": 95})], capture_output=True, text=True)
    t0 = time.time()
    eid = None
    while time.time() - t0 < 10:
        sc, lst = api("GET", "/executions?pageNo=1&pageSize=20", tok)
        for it in lst.get("data", {}).get("records", []):
            if it.get("triggerType") == "mqtt" and it.get("versionId") == vid and it.get("id") > base_max:
                eid = it["id"]
                break
        if eid:
            break
        time.sleep(0.5)
    latency = time.time() - t0
    ck("MQTT 消息创建执行", eid is not None, f"eid={eid}")
    ck("M6 触发时延 ≤5s", latency <= 5, f"{latency:.2f}s")
    if eid:
        wait_exec(tok, eid, 30)
        nodes = node_map(tok, eid)
        ck("MQTT 执行走到 h1", nodes.get("h1", {}).get("status") in ("SUCCESS", "FAILED"),
           nodes.get("h1", {}).get("status"))
    ART["mqtt_latency"] = round(latency, 2)
    sc, d3 = api("PUT", f"/mqtt/subscriptions/{sid}", tok, {"topic": topic, "workflowVersionId": vid, "status": "disabled"})
    ck("订阅改为停用", ok_code(d3) and d3.get("data", {}).get("status") == "disabled",
       f"{d3.get('code')} {d3.get('data', {}).get('status')}")
    before2 = int(db("SELECT IFNULL(MAX(id),0) FROM execution;")[0][0])
    subprocess.run(["docker", "exec", "swa-mosquitto", "mosquitto_pub", "-h", "localhost",
                    "-t", topic, "-m", json.dumps({"temp": 99})], capture_output=True, text=True)
    time.sleep(5)
    after2 = int(db("SELECT IFNULL(MAX(id),0) FROM execution;")[0][0])
    ck("停用后不再触发", after2 == before2, f"{before2}->{after2}")
    sc, d4 = api("DELETE", f"/mqtt/subscriptions/{sid}", tok)
    ck("删除订阅", ok_code(d4), d4.get("code"))


# ---------------- L-11 额度 / 台账 / 审计接口 ----------------
def l11(ck):
    dev = ART["tokens"]["dev_acme"]
    admin = ART["tokens"]["admin_acme"]
    viewer = ART["tokens"]["viewer_acme"]
    sc, d = api("GET", "/quota", dev)
    q = d.get("data") or {}
    used_db = int(db("SELECT token_used FROM tenant_quota WHERE tenant_id=1;")[0][0])
    ck("额度 tokenUsed=DB", q.get("tokenUsed") == used_db, f"{q.get('tokenUsed')} vs {used_db}")
    ck("额度 remain=total-used", q.get("tokenRemainRedis") == int(q.get("tokenTotal", 0)) - used_db,
       q)
    ck("Redis 余额键=接口值", int(R.get("quota:remain:1") or -1) == q.get("tokenRemainRedis"),
       R.get("quota:remain:1"))
    sc, d = api("GET", "/quota/llm-calls?pageNo=1&pageSize=10", dev)
    recs = d.get("data", {}).get("records", [])
    ck("台账分页返回本租户", ok_code(d) and len(recs) >= 1 and all(x.get("tenantId") == 1 for x in recs),
       len(recs))
    ck("台账含 provider/model/cost", all(x.get("provider") and x.get("model") and x.get("cost") is not None for x in recs),
       recs[0] if recs else None)
    sc, d = api("GET", "/quota/audit-logs?pageNo=1&pageSize=10", admin)
    ck("admin 审计日志可读", ok_code(d) and len(d.get("data", {}).get("records", [])) >= 1)
    sc, d = api("GET", "/quota", viewer)
    ck("viewer 可读额度", ok_code(d), d.get("code"))


# ---------------- L-12 内部接口鉴权 ----------------
def l12(ck):
    r = requests.post(BASE + "/internal/llm/chat",
                      json={"taskType": "agent_reasoning", "messages": [{"role": "user", "content": "ping"}]},
                      timeout=10)
    ck("无 X-Internal-Token → 401", r.status_code == 401, f"status={r.status_code}")


# ---------------- L-13 跨租户隔离 ----------------
def l13(ck):
    g = ART["tokens"]["admin_globex"]
    acme_wf = int(db("SELECT id FROM workflow WHERE tenant_id=1 AND deleted=0 ORDER BY id LIMIT 1;")[0][0])
    sc, d = api("GET", f"/workflows/{acme_wf}", g)
    ck("跨租户读流程 → 20001", d.get("code") == 20001, d.get("code"))
    acme_exec = int(db("SELECT id FROM execution WHERE tenant_id=1 ORDER BY id DESC LIMIT 1;")[0][0])
    sc, d = api("GET", f"/executions/{acme_exec}", g)
    ck("跨租户读执行 → 30001", d.get("code") == 30001, d.get("code"))
    sc, d = api("POST", "/workflows", g, {"name": f"联调-globex-{TS}", "description": "租户2"})
    ck("globex 创建流程 tenantId=2", ok_code(d) and d["data"]["tenantId"] == 2, d.get("data", {}).get("tenantId"))
    sc, d = api("GET", "/workflows?pageNo=1&pageSize=20", g)
    ck("globex 列表不含 acme 流程",
       all(x["tenantId"] == 2 for x in d.get("data", {}).get("records", [])),
       len(d.get("data", {}).get("records", [])))


# ---------------- L-14 租户/用户/凭据（admin） ----------------
def l14(ck):
    admin = ART["tokens"]["admin_acme"]
    viewer = ART["tokens"]["viewer_acme"]
    sc, d = api("GET", "/tenants?pageNo=1&pageSize=20", admin)
    ck("租户列表含 1/2", ok_code(d) and {1, 2} <= {x["id"] for x in d["data"]["records"]})
    sc, d = api("PUT", "/tenants/1/quota", admin, {"tokenTotal": 1000000})
    ck("配置额度成功", ok_code(d), d.get("code"))
    used = int(db("SELECT token_used FROM tenant_quota WHERE tenant_id=1;")[0][0])
    ck("额度 Redis 重算=total-used", int(R.get("quota:remain:1") or -1) == 1000000 - used,
       R.get("quota:remain:1"))
    uname = f"linku{TS}"
    sc, d = api("POST", "/users", admin, {"username": uname, "password": "Abcdef123",
                                          "displayName": "联调用户", "role": "dev"})
    ck("创建用户", ok_code(d), f"{d.get('code')} {d.get('message')}")
    sc, d = api("GET", f"/users?pageNo=1&pageSize=20&username={uname}", admin)
    ck("用户列表命中", ok_code(d) and len(d["data"]["records"]) >= 1)
    sc, d = api("DELETE", f"/users/{d['data']['records'][0]['id'] if d.get('data', {}).get('records') else 1}", admin)
    ck("删除用户", ok_code(d), d.get("code"))
    sc, d = api("POST", "/credentials", admin, {"connectorType": "http", "name": f"联调凭据-{TS}",
                                                "configJson": '{"apiKey":"sk-test-1031"}'})
    ck("创建凭据", ok_code(d), f"{d.get('code')} {d.get('message')}")
    cid = d.get("data", {}).get("id")
    sc, d = api("GET", f"/credentials/{cid}", admin)
    ck("凭据读取脱敏", ok_code(d) and "******" in json.dumps(d.get("data") or {}, ensure_ascii=False),
       d.get("data"))
    sc, d = api("DELETE", f"/credentials/{cid}", admin)
    ck("删除凭据", ok_code(d), d.get("code"))
    sc, d = api("GET", "/tenants?pageNo=1&pageSize=5", viewer)
    ck("viewer 租户管理 → 403", sc == 403 or d.get("code") == 10403, f"{sc} {d.get('code')}")
    sc, d = api("GET", "/credentials?pageNo=1&pageSize=5", viewer)
    ck("viewer 凭据管理 → 403", sc == 403 or d.get("code") == 10403, f"{sc} {d.get('code')}")


def main():
    t0 = time.time()
    case("L-01", "认证与权限矩阵", l01)
    case("L-02", "流程 CRUD + 审计", l02)
    case("L-03", "DSL 负向校验", l03)
    case("L-04", "版本状态门槛", l04)
    case("L-05", "主执行链/幂等/SSE/回放", l05)
    case("L-06", "延时节点 WAITING→恢复", l06)
    case("L-07", "节点失败路径", l07)
    case("L-08", "Agent 全链 + 计量一致性", l08)
    case("L-09", "NL 生成全链", l09)
    case("L-10", "MQTT 订阅+e2e+停用", l10)
    case("L-11", "额度/台账/审计接口", l11)
    case("L-12", "内部接口鉴权", l12)
    case("L-13", "跨租户隔离", l13)
    case("L-14", "租户/用户/凭据", l14)
    passed = sum(1 for x in RESULTS if x["passed"])
    total = len(RESULTS)
    out = {"run_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": total, "passed": passed,
           "seconds": round(time.time() - t0, 1), "cases": RESULTS, "artifacts": ART}
    (OUT / "link_result.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== 联调结果 {passed}/{total} 通过，耗时 {out['seconds']}s ===")
    print(f"证据：{OUT / 'link_result.json'}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
