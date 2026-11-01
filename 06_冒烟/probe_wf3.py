# -*- coding: utf-8 -*-
import json, os, time, urllib.request

BASE = "http://localhost:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
tokens = json.load(open(os.path.join(HERE, "tokens.json"), encoding="utf-8-sig"))
TOK = tokens["dev_acme"]
ids = json.load(open(os.path.join(HERE, "smoke_wf.json"), encoding="utf-8-sig"))
VER = ids["versionId"]

def call(method, path, body=None, token=TOK):
    url = BASE + path
    data = None
    headers = {"Authorization": "Bearer " + token}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

# trigger twice with same clientReqId -> idempotent
req = {"versionId": VER, "clientReqId": "smoke-req-002", "triggerPayload": json.dumps({"payload": {"temp": 95}})}
s, e1 = call("POST", "/executions", req)
ex1 = e1.get("data", {}).get("id")
print("EXEC_1 http=%s code=%s id=%s status=%s" % (s, e1.get("code"), ex1, e1.get("data", {}).get("status")))
s, e2 = call("POST", "/executions", req)
ex2 = e2.get("data", {}).get("id")
print("EXEC_2 http=%s code=%s id=%s (idempotent=%s)" % (s, e2.get("code"), ex2, ex1 == ex2))

# poll detail
st = None
for i in range(20):
    time.sleep(1)
    s, det = call("GET", "/executions/%s" % ex1)
    st = det.get("data", {}).get("status")
    if st in ("SUCCESS", "FAILED"):
        break
print("DETAIL http=%s code=%s status=%s failReason=%s" % (s, det.get("code"), st, det.get("data", {}).get("failReason")))

# node snapshot
s, nodes = call("GET", "/executions/%s/nodes" % ex1)
print("NODES http=%s code=%s" % (s, nodes.get("code")))
for n in nodes.get("data", []):
    print("  node=%s status=%s output=%s err=%s" % (n.get("nodeId"), n.get("status"),
          json.dumps(n.get("outputData") or n.get("outputJson"), ensure_ascii=False)[:180], n.get("errorMessage")))

# replay
s, rp = call("POST", "/executions/%s/replay" % ex1)
print("REPLAY http=%s code=%s newId=%s status=%s" % (s, rp.get("code"), rp.get("data", {}).get("id"), rp.get("data", {}).get("status")))
rp_id = rp.get("data", {}).get("id")
if rp_id:
    for i in range(20):
        time.sleep(1)
        s, det = call("GET", "/executions/%s" % rp_id)
        if det.get("data", {}).get("status") in ("SUCCESS", "FAILED"):
            break
    print("REPLAY_DETAIL status=%s" % det.get("data", {}).get("status"))

json.dump({"wfId": ids["wfId"], "versionId": VER, "execId": ex1}, open(os.path.join(HERE, "smoke_wf.json"), "w"))
