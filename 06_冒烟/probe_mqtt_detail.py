# -*- coding: utf-8 -*-
import json, os, urllib.request
BASE = "http://localhost:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
tokens = json.load(open(os.path.join(HERE, "tokens.json"), encoding="utf-8-sig"))
TOK = tokens["dev_acme"]
req = urllib.request.Request(BASE + "/executions/9/nodes", headers={"Authorization": "Bearer " + TOK})
with urllib.request.urlopen(req, timeout=30) as r:
    nodes = json.loads(r.read().decode())["data"]
for n in nodes:
    print("node=%s status=%s input=%s output=%s err=%s" % (n["nodeId"], n["status"],
          json.dumps(n.get("inputJson"), ensure_ascii=False)[:200],
          json.dumps(n.get("outputJson"), ensure_ascii=False)[:200],
          n.get("errorMessage")))
