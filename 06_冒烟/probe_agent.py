# -*- coding: utf-8 -*-
import json, os, time, urllib.request
BASE = "http://localhost:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
tokens = json.load(open(os.path.join(HERE, "tokens.json"), encoding="utf-8-sig"))
TOK = tokens["dev_acme"]

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, data=(json.dumps(body, ensure_ascii=False).encode() if body is not None else None),
                                 headers={"Authorization": "Bearer " + TOK, "Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())

# agent workflow: mqtt-trigger -> agent (task) -> code
wf = call("POST", "/workflows", {"name": "smoke-agent-e2e", "description": "agent node e2e"})
wid = wf["data"]["id"]
dsl = {
    "nodes": [
        {"id": "t1", "type": "mqtt-trigger", "config": {"topic": "factory/smoke/agent"}},
        {"id": "a1", "type": "agent", "config": {"task": "总结输入温度数据并给出建议", "taskType": "agent_reasoning"}},
        {"id": "d1", "type": "code", "config": {"expression": "'done'"}}
    ],
    "edges": [
        {"source": "t1", "target": "a1"},
        {"source": "a1", "target": "d1"}
    ]
}
ver = call("POST", "/workflows/%s/versions" % wid, {"dslJson": json.dumps(dsl)})
vid = ver["data"]["id"]
print("AGENT_WF wf=%s ver=%s code=%s" % (wid, vid, ver.get("code")))
call("PUT", "/workflows/versions/%s/publish" % vid)
e = call("POST", "/executions", {"versionId": vid, "clientReqId": "smoke-agent-001", "triggerPayload": json.dumps({"payload": {"temp": 88}})})
ex = e["data"]["id"]
print("AGENT_EXEC id=%s status=%s" % (ex, e["data"]["status"]))
for i in range(30):
    time.sleep(2)
    det = call("GET", "/executions/%s" % ex)
    if det["data"]["status"] in ("SUCCESS", "FAILED"):
        break
print("AGENT_DETAIL status=%s failReason=%s" % (det["data"]["status"], det["data"].get("failReason")))
for n in call("GET", "/executions/%s/nodes" % ex)["data"]:
    print("  node=%s status=%s output=%s err=%s" % (n["nodeId"], n["status"],
          json.dumps(n.get("outputJson"), ensure_ascii=False)[:300], n.get("errorMessage")))
