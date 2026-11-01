# -*- coding: utf-8 -*-
import json, os, time, urllib.request
BASE = "http://localhost:8083/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
tokens = json.load(open(os.path.join(HERE, "tokens.json"), encoding="utf-8-sig"))
TOK = tokens["dev_acme"]

def call(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + TOK})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

t0 = time.time()
found = None
for i in range(15):
    time.sleep(1)
    page = call("/executions?pageNo=1&pageSize=20")
    for it in page["data"]["records"]:
        if it.get("triggerType") == "mqtt" and it.get("versionId") == 5 and it.get("status") in ("SUCCESS", "FAILED"):
            found = it
            break
    if found:
        break
if found:
    print("MQTT_EXEC id=%s status=%s latency_s=%.1f" % (found["id"], found["status"], time.time() - t0))
    for n in call("/executions/%s/nodes" % found["id"])["data"]:
        print("  node=%s status=%s output=%s err=%s" % (n["nodeId"], n["status"],
              json.dumps(n.get("outputJson"), ensure_ascii=False)[:200], n.get("errorMessage")))
else:
    print("NO_NEW_MQTT_EXEC")
