# -*- coding: utf-8 -*-
import json, os, threading, time, urllib.request

BASE = "http://localhost:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
tokens = json.load(open(os.path.join(HERE, "tokens.json"), encoding="utf-8-sig"))
TOK = tokens["dev_acme"]
ids = json.load(open(os.path.join(HERE, "smoke_wf.json"), encoding="utf-8-sig"))
VER = ids["versionId"]

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, data=(json.dumps(body).encode() if body is not None else None),
                                 headers={"Authorization": "Bearer " + TOK, "Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())

sse_events = []
def sse_collect(exec_id):
    req = urllib.request.Request(BASE + "/executions/%s/events" % exec_id, headers={"Authorization": "Bearer " + TOK})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").rstrip("\n")
                if line:
                    sse_events.append(line)
    except Exception as e:
        sse_events.append("<<closed:%s>>" % type(e).__name__)

# trigger temp=99 so condition true -> http branch
e = call("POST", "/executions", {"versionId": VER, "clientReqId": "smoke-req-003", "triggerPayload": json.dumps({"payload": {"temp": 95}})})
ex = e["data"]["id"]
print("EXEC_TRUE id=%s status=%s" % (ex, e["data"]["status"]))
t = threading.Thread(target=sse_collect, args=(ex,), daemon=True)
t.start()
for i in range(20):
    time.sleep(1)
    det = call("GET", "/executions/%s" % ex)
    if det["data"]["status"] in ("SUCCESS", "FAILED"):
        break
t.join(timeout=8)
print("DETAIL status=%s" % det["data"]["status"])
nodes = call("GET", "/executions/%s/nodes" % ex)["data"]
for n in nodes:
    print("  node=%s status=%s output=%s" % (n["nodeId"], n["status"], json.dumps(n.get("outputData") or n.get("outputJson"), ensure_ascii=False)[:200]))
print("SSE_LINES=%d" % len(sse_events))
for l in sse_events[:40]:
    print("  " + l[:200])
