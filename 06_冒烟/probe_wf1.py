# -*- coding: utf-8 -*-
import json, os, urllib.request

BASE = "http://localhost:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
tokens = json.load(open(os.path.join(HERE, "tokens.json"), encoding="utf-8-sig"))
TOK = tokens["dev_acme"]

def call(method, path, body=None, token=TOK, extra_headers=None):
    url = BASE + path
    data = None
    headers = {"Authorization": "Bearer " + token}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

# 1. create workflow
s, wf = call("POST", "/workflows", {"name": "smoke-high-temp-e2e", "description": "stage1 smoke: 3 nodes with condition branch"})
wf_id = wf.get("data", {}).get("id")
print("CREATE_WF http=%s code=%s id=%s" % (s, wf.get("code"), wf_id))

# 2. save DSL version: mqtt-trigger t1 -> condition c1 -true-> http h1, -false-> code d1
dsl = {
    "nodes": [
        {"id": "t1", "type": "mqtt-trigger", "config": {"topic": "factory/+/temperature"}},
        {"id": "c1", "type": "condition", "config": {"expression": "t1.payload.temp > 80"}},
        {"id": "h1", "type": "http", "config": {"method": "GET", "url": "http://localhost:8083/actuator/health"}},
        {"id": "d1", "type": "code", "config": {"expression": "'low-temp'"}}
    ],
    "edges": [
        {"source": "t1", "target": "c1"},
        {"source": "c1", "target": "h1", "branch": "true"},
        {"source": "c1", "target": "d1", "branch": "false"}
    ]
}
s, ver = call("POST", "/workflows/%s/versions" % wf_id, {"dslJson": json.dumps(dsl)})
ver_id = ver.get("data", {}).get("id")
print("SAVE_VER http=%s code=%s versionId=%s versionNo=%s status=%s" % (
    s, ver.get("code"), ver_id, ver.get("data", {}).get("versionNo"), ver.get("data", {}).get("status")))
if ver.get("code") != 0:
    print(json.dumps(ver, ensure_ascii=False))

json.dump({"wfId": wf_id, "versionId": ver_id}, open(os.path.join(HERE, "smoke_wf.json"), "w"))
