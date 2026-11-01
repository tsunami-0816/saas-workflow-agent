# -*- coding: utf-8 -*-
"""
2026-10-31 step6 阶段一冒烟（回退补落地后复验，DashScope 千问真调）。
真实执行，禁止虚构；证据落盘 06_冒烟/evidence/1031/。
"""
import json, os, subprocess, sys, time

import requests

BASE = "http://127.0.0.1:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(os.path.dirname(HERE), "evidence", "1031")  # 06_冒烟/evidence/1031
os.makedirs(EV, exist_ok=True)
RESULTS = []


def rec(case, ok, detail, fname=None, payload=None):
    RESULTS.append({"case": case, "ok": bool(ok), "detail": detail})
    print(("PASS" if ok else "FAIL"), "|", case, "|", detail, flush=True)
    if fname and payload is not None:
        with open(os.path.join(EV, fname), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


def api(method, path, tok=None, body=None, timeout=30):
    h = {"Content-Type": "application/json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    r = requests.request(method, BASE + path, headers=h, json=body, timeout=timeout)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"_raw": r.text[:500]}


def wait_terminal(tok, eid, timeout=180):
    j = {}
    for _ in range(timeout):
        _, j = api("GET", "/executions/%s" % eid, tok)
        st = (j.get("data") or {}).get("status")
        if st in ("SUCCESS", "FAILED"):
            return st, j
        time.sleep(1)
    return "TIMEOUT", j


def nodes_of(tok, eid):
    _, j = api("GET", "/executions/%s/nodes" % eid, tok)
    return j.get("data") or []


def node_map(nodes):
    out = {}
    for n in nodes:
        for k in ("outputJson", "inputJson"):
            v = n.get(k)
            if isinstance(v, str) and v:
                try:
                    n[k] = json.loads(v)
                except Exception:
                    pass
        out[n.get("nodeId")] = n
    return out


# ---------- 1. 三角色登录 + globex ----------
toks = {}
for u in ("admin_acme", "dev_acme", "viewer_acme", "viewer_globex"):
    sc, j = api("POST", "/auth/login", body={"username": u, "password": "Swa@123456"})
    ok = sc == 200 and j.get("code") == 0 and (j.get("data") or {}).get("token")
    if ok:
        toks[u] = j["data"]["token"]
    rec("login_%s" % u, ok, "http=%s code=%s" % (sc, j.get("code")))
rec("login_tokens", len(toks) == 4, "got %d tokens" % len(toks), "01_tokens.json",
    {k: v for k, v in toks.items()})
if len(toks) < 4:
    print("ABORT: login failed"); sys.exit(1)

dev, viewer, globex = toks["dev_acme"], toks["viewer_acme"], toks["viewer_globex"]

# ---------- 2. 越权与跨租户 ----------
sc, j = api("POST", "/workflows", viewer, {"name": "viewer-forbidden", "description": "x"})
rec("rbac_viewer_write_403", j.get("code") == 10403, "http=%s code=%s" % (sc, j.get("code")),
    "02_viewer_write.json", j)

# ---------- 3. 流程创建（含 BUG-001 tenantId 回填复验） ----------
sc, j = api("POST", "/workflows", dev, {"name": "smoke-1031", "description": "回退补落地复验"})
d = j.get("data") or {}
wid = d.get("id")
rec("workflow_create", sc == 200 and j.get("code") == 0 and wid, "id=%s" % wid)
rec("bug001_tenantId_backfill", d.get("tenantId") is not None, "tenantId=%s" % d.get("tenantId"),
    "03_create_resp.json", j)

# 跨租户：globex 读 acme 的流程详情 + 列表隔离
sc, j1 = api("GET", "/workflows/%s" % wid, globex)
rec("cross_tenant_detail_invisible", j1.get("code") != 0, "code=%s(不可见)" % j1.get("code"),
    "04_cross_detail.json", j1)
sc, j2 = api("GET", "/workflows?pageNo=1&pageSize=50", globex)
items = json.dumps(j2.get("data"), ensure_ascii=False)
rec("cross_tenant_list_isolated", "smoke-1031" not in items, "globex 列表不含 acme 流程",
    "05_cross_list.json", j2)

# ---------- 4. DSL 保存 / 发布 / 执行（条件分支双路径） ----------
DSL = {"nodes": [
    {"id": "t1", "type": "mqtt-trigger", "name": "temp-msg", "config": {}},
    {"id": "c1", "type": "condition", "name": "over80", "config": {"expression": "t1.payload.temp > 80"}},
    {"id": "h1", "type": "http", "name": "alarm",
     "config": {"url": "http://127.0.0.1:8083/actuator/health", "method": "GET", "timeoutMs": 10000}},
    {"id": "d1", "type": "code", "name": "log-temp", "config": {"expression": "t1.payload.temp"}}],
    "edges": [
        {"source": "t1", "target": "c1"},
        {"source": "c1", "target": "h1", "branch": "true"},
        {"source": "c1", "target": "d1", "branch": "false"}]}

sc, j = api("POST", "/workflows/%s/versions" % wid, dev, {"dslJson": json.dumps(DSL, ensure_ascii=False)})
vid = (j.get("data") or {}).get("id")
rec("version_save", j.get("code") == 0 and vid, "versionId=%s" % vid, "06_version.json", j)

sc, j = api("PUT", "/workflows/versions/%s/publish" % vid, dev)
rec("publish", j.get("code") == 0, "code=%s" % j.get("code"))


def run_exec(req_id, temp):
    sc, j = api("POST", "/executions", dev,
                {"versionId": vid, "clientReqId": req_id, "triggerPayload": json.dumps({"temp": temp})})
    eid = (j.get("data") or {}).get("id")
    st, detail = wait_terminal(dev, eid)
    return eid, st, detail, node_map(nodes_of(dev, eid))


eid1, st1, det1, nm1 = run_exec("smoke1031-t95", 95)
rec("exec_true_branch", st1 == "SUCCESS" and nm1.get("h1", {}).get("status") == "SUCCESS"
    and nm1.get("d1", {}).get("status") == "SKIPPED",
    "exec=%s st=%s h1=%s d1=%s" % (eid1, st1, nm1.get("h1", {}).get("status"), nm1.get("d1", {}).get("status")),
    "07_exec_true.json", {"exec": det1, "nodes": nm1})

# 幂等：同 clientReqId 重发
sc, j = api("POST", "/executions", dev,
            {"versionId": vid, "clientReqId": "smoke1031-t95", "triggerPayload": json.dumps({"temp": 95})})
eid_again = (j.get("data") or {}).get("id")
rec("idempotent_same_reqid", eid_again == eid1, "first=%s again=%s" % (eid1, eid_again))

eid2, st2, det2, nm2 = run_exec("smoke1031-t60", 60)
rec("exec_false_branch", st2 == "SUCCESS" and nm2.get("d1", {}).get("status") == "SUCCESS"
    and nm2.get("h1", {}).get("status") == "SKIPPED",
    "exec=%s st=%s h1=%s d1=%s" % (eid2, st2, nm2.get("h1", {}).get("status"), nm2.get("d1", {}).get("status")),
    "08_exec_false.json", {"exec": det2, "nodes": nm2})

# ---------- 5. SSE 事件流 + 节点快照 + 回放 ----------
sc, j = api("POST", "/executions", dev,
            {"versionId": vid, "clientReqId": "smoke1031-sse", "triggerPayload": json.dumps({"temp": 88})})
eid_sse = (j.get("data") or {}).get("id")
sse_lines = []
try:
    with requests.get(BASE + "/executions/%s/events" % eid_sse,
                      headers={"Authorization": "Bearer " + dev}, stream=True, timeout=(5, 90)) as r:
        t0 = time.time()
        for line in r.iter_lines(decode_unicode=True):
            if line:
                sse_lines.append(line)
            if time.time() - t0 > 60 or len(sse_lines) >= 60:
                break
            if line and "SUCCESS" in line and "execution" in "".join(sse_lines[-6:]).lower():
                break
except Exception as e:
    sse_lines.append("SSE_ERR: %s" % e)
wait_terminal(dev, eid_sse)
rec("sse_events", len(sse_lines) >= 3, "got %d lines" % len(sse_lines), "09_sse.txt",
    {"lines": sse_lines})

snap = nodes_of(dev, eid_sse)
rec("nodes_snapshot", len(snap) == 4 and all(n.get("status") for n in snap),
    "nodes=%d" % len(snap), "10_snapshot.json", snap)

sc, j = api("POST", "/executions/%s/replay" % eid_sse, dev)
rid = (j.get("data") or {}).get("id")
rst, rdet = wait_terminal(dev, rid)
rec("replay", rst == "SUCCESS" and rid != eid_sse, "replay=%s st=%s" % (rid, rst),
    "11_replay.json", rdet)

# ---------- 6. MQTT e2e（D-17 / M6） ----------
sc, j = api("POST", "/mqtt/subscriptions", dev,
            {"topic": "factory/smoke/t1031", "workflowVersionId": vid, "status": "active"})
sub_id = (j.get("data") or {}).get("id")
rec("mqtt_sub_create", j.get("code") == 0 and sub_id, "sub=%s" % sub_id, "12_sub.json", j)

_, jlist = api("GET", "/executions?pageNo=1&pageSize=50", dev)
prev_ids = {it.get("id") for it in (jlist.get("data") or {}).get("records", [])}
t_pub = time.time()
subprocess.run(["docker", "exec", "swa-mosquitto", "mosquitto_pub", "-h", "localhost",
                "-t", "factory/smoke/t1031", "-m", json.dumps({"temp": 97, "deviceId": "s-1031"})],
               capture_output=True, timeout=15)
found, latency = None, None
for _ in range(20):
    time.sleep(0.5)
    _, jl = api("GET", "/executions?pageNo=1&pageSize=50", dev)
    for it in (jl.get("data") or {}).get("records", []):
        if it.get("id") not in prev_ids and it.get("triggerType") == "mqtt" and it.get("versionId") == vid:
            found, latency = it, time.time() - t_pub
            break
    if found:
        break
if found:
    mst, mdet = wait_terminal(dev, found["id"])
    mnm = node_map(nodes_of(dev, found["id"]))
    rec("mqtt_e2e", mst == "SUCCESS" and latency <= 3.0,
        "exec=%s st=%s latency=%.2fs h1=%s" % (found["id"], mst, latency, mnm.get("h1", {}).get("status")),
        "13_mqtt_e2e.json", {"exec": mdet, "nodes": mnm, "latency_s": latency})
else:
    rec("mqtt_e2e", False, "NO_NEW_MQTT_EXEC within 10s")

# ---------- 7. NL-draft（DashScope 真调，D-19/D-20/D-12） ----------
sc, j = api("POST", "/workflows/nl-draft", dev,
            {"text": "当温度传感器通过MQTT上报温度超过80度时，调用HTTP告警接口通知，否则用代码块记录温度值",
             "workflowName": "nl-smoke-1031"}, timeout=120)
nd = j.get("data") or {}
dsl_txt = nd.get("dslJson") or ""
nl_ok = j.get("code") == 0 and "nodes" in dsl_txt
rec("nl_draft_dashscope", nl_ok, "code=%s versionId=%s dsl_len=%d" % (j.get("code"), nd.get("id"), len(dsl_txt)),
    "14_nl_draft.json", j)

# ---------- 8. Agent 节点 java→python→java 全链（LangGraph 版，D-21） ----------
AGENT_DSL = {"nodes": [
    {"id": "t1", "type": "mqtt-trigger", "name": "in", "config": {}},
    {"id": "a1", "type": "agent", "name": "gen",
     "config": {"task": "用中文一句话解释什么是工作流引擎的幂等触发", "taskType": "agent_reasoning"}}],
    "edges": [{"source": "t1", "target": "a1"}]}
sc, j = api("POST", "/workflows", dev, {"name": "agent-smoke-1031", "description": "agent 全链复验"})
awid = (j.get("data") or {}).get("id")
sc, j = api("POST", "/workflows/%s/versions" % awid, dev, {"dslJson": json.dumps(AGENT_DSL, ensure_ascii=False)})
avid = (j.get("data") or {}).get("id")
api("PUT", "/workflows/versions/%s/publish" % avid, dev)
sc, j = api("POST", "/executions", dev,
            {"versionId": avid, "clientReqId": "smoke1031-agent", "triggerPayload": json.dumps({"temp": 1})})
aeid = (j.get("data") or {}).get("id")
ast, adet = wait_terminal(dev, aeid, timeout=240)
anm = node_map(nodes_of(dev, aeid))
a1 = anm.get("a1", {})
a1_out = a1.get("outputJson") or {}
reasoning = (a1_out.get("output") or {}) if isinstance(a1_out, dict) else {}
steps = a1_out.get("reasoning") or []
rec("agent_e2e", ast == "SUCCESS" and a1.get("status") == "SUCCESS" and len(steps) >= 3,
    "exec=%s st=%s a1=%s reasoning_steps=%d" % (aeid, ast, a1.get("status"), len(steps)),
    "15_agent_e2e.json", {"exec": adet, "nodes": anm})

# ---------- 9. llm_call_log 台账（dashscope 计量，D-14） ----------
sc, j = api("GET", "/quota/llm-calls", dev)
raw = json.dumps(j, ensure_ascii=False)
rec("llm_call_log_dashscope", j.get("code") == 0 and "dashscope" in raw,
    "code=%s dashscope_in_records=%s" % (j.get("code"), "dashscope" in raw), "16_llm_calls.json", j)

# ---------- 汇总 ----------
ok_n = sum(1 for r in RESULTS if r["ok"])
print("\n==== SUMMARY %d/%d PASS ====" % (ok_n, len(RESULTS)))
for r in RESULTS:
    if not r["ok"]:
        print("FAILED:", r["case"], "-", r["detail"])
with open(os.path.join(EV, "00_summary.json"), "w", encoding="utf-8") as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=2)
sys.exit(0 if ok_n == len(RESULTS) else 1)
