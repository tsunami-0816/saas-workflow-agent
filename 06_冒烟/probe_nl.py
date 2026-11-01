# -*- coding: utf-8 -*-
import json, os, time, urllib.request, urllib.error
BASE = "http://localhost:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
tokens = json.load(open(os.path.join(HERE, "tokens.json"), encoding="utf-8-sig"))
TOK = tokens["dev_acme"]

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, data=(json.dumps(body, ensure_ascii=False).encode() if body is not None else None),
                                 headers={"Authorization": "Bearer " + TOK, "Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"raw": ""}

# NL-draft
s, r = call("POST", "/workflows/nl-draft", {"text": "收到设备温度消息后，温度大于80度时调用告警接口，否则记录温度", "workflowName": "smoke-nl-draft"})
print("NL_DRAFT http=%s code=%s" % (s, r.get("code")))
print("RAW=%s" % json.dumps(r, ensure_ascii=False)[:800])
