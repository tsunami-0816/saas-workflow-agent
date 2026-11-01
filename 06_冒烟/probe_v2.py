# -*- coding: utf-8 -*-
import json, os, time, urllib.request

BASE = "http://localhost:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
tokens = json.load(open(os.path.join(HERE, "tokens.json"), encoding="utf-8-sig"))
TOK = tokens["dev_acme"]
ids = json.load(open(os.path.join(HERE, "smoke_wf.json"), encoding="utf-8-sig"))
WF = ids["wfId"]

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, data=(json.dumps(body, ensure_ascii=False).encode() if body is not None else None),
                                 headers={"Authorization": "Bearer " + TOK, "Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())

# v2: condition reads _payload.payload.temp (real input shape for mqtt/manual json payload)
dsl = {
    "nodes": [
        {"id": "t1", "type": "mqtt-trigger", "config": {"topic": "factory/+/temperature"}},
        {"id": "c1", "type": "condition", "config": {"expression": "_payload.payload.temp > 80"}},
        {"id": "h1", "type": "http", "config": {"method": "GET", "url": "http://localhost:8083/actuator/health"}},
        {"id": "d1", "type": "code", "config": {"expression": "'low-temp'"}}
    ],
    "edges": [
        {"source": "t1", "target": "c1"},
        {"source": "c1", "target": "h1", "branch": "true"},
        {"source": "c1", "target": "d1", "branch": "false"}
    ]
}
ver = call("POST", "/workflows/%s/versions" % WF, {"dslJson": json.dumps(dsl)})
v2 = ver["data"]["id"]
print("SAVE_V2 code=%s versionId=%s versionNo=%s status=%s" % (ver["code"], v2, ver["data"]["versionNo"], ver["data"]["status"]))
pub = call("PUT", "/workflows/versions/%s/publish" % v2)
print("PUBLISH_V2 code=%s status=%s" % (pub["code"], pub["data"]["status"]))

# manual trigger v2 with temp=99 -> expect true branch (http)
e = call("POST", "/executions", {"versionId": v2, "clientReqId": "smoke-req-true99", "triggerPayload": json.dumps({"payload": {"temp": 99}})})
ex = e["data"]["id"]
for i in range(20):
    time.sleep(1)
    det = call("GET", "/executions/%s" % ex)
    if det["data"]["status"] in ("SUCCESS", "FAILED"):
        break
print("MANUAL_TRUE exec=%s status=%s" % (ex, det["data"]["status"]))
for n in call("GET", "/executions/%s/nodes" % ex)["data"]:
    print("  node=%s status=%s output=%s err=%s" % (n["nodeId"], n["status"], json.dumps(n.get("outputData") or n.get("outputJson"), ensure_ascii=False)[:200], n.get("errorMessage")))

json.dump({"wfId": WF, "versionId": ids["versionId"], "v2": v2, "execId": ex}, open(os.path.join(HERE, "smoke_wf.json"), "w"))
