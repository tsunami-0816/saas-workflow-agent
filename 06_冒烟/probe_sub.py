# -*- coding: utf-8 -*-
import json, os, time, urllib.request

BASE = "http://localhost:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
tokens = json.load(open(os.path.join(HERE, "tokens.json"), encoding="utf-8-sig"))
TOK = tokens["dev_acme"]
ids = json.load(open(os.path.join(HERE, "smoke_wf.json"), encoding="utf-8-sig"))
V3 = ids["v3"]

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, data=(json.dumps(body, ensure_ascii=False).encode() if body is not None else None),
                                 headers={"Authorization": "Bearer " + TOK, "Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())

# 1. create subscription topic factory/smoke/temperature -> v3
sub = call("POST", "/mqtt/subscriptions", {"topic": "factory/smoke/temperature", "workflowVersionId": V3, "status": "active"})
print("SUB_CREATE code=%s id=%s" % (sub.get("code"), sub.get("data", {}).get("id")))
if sub.get("code") != 0:
    print(json.dumps(sub, ensure_ascii=False))

# list subscriptions
lst = call("GET", "/mqtt/subscriptions")
print("SUB_LIST code=%s total=%s" % (lst.get("code"), lst.get("data", {}).get("total")))
for it in (lst.get("data", {}).get("records") or []):
    print("  sub id=%s topic=%s ver=%s status=%s" % (it.get("id"), it.get("topic"), it.get("workflowVersionId"), it.get("status")))

ids["subId"] = sub.get("data", {}).get("id")
json.dump(ids, open(os.path.join(HERE, "smoke_wf.json"), "w"))
