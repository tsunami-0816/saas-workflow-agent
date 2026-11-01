# -*- coding: utf-8 -*-
"""MQTT e2e 单独复验（2026-10-31 第二轮）：唯一主题，复用 smoke-1031 已发布版本。"""
import json, os, subprocess, sys, time
import requests

BASE = "http://127.0.0.1:8083/api/v1"
EV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence", "1031")
os.makedirs(EV, exist_ok=True)

sc = requests.post(BASE + "/auth/login", json={"username": "dev_acme", "password": "Swa@123456"}, timeout=15).json()
tok = sc["data"]["token"]
H = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}

# 找 smoke-1031 最新 published 版本
wfs = requests.get(BASE + "/workflows?pageNo=1&pageSize=50", headers=H, timeout=10).json()
wid = max(w["id"] for w in wfs["data"]["records"] if w.get("name") == "smoke-1031")
vers = requests.get(BASE + "/workflows/%s/versions" % wid, headers=H, timeout=10).json()
vid = max(v["id"] for v in vers["data"]["records"] if v.get("status") == "published")
print("workflow=%s version=%s" % (wid, vid))

topic = "factory/smoke/u%d" % int(time.time())
sub = requests.post(BASE + "/mqtt/subscriptions", headers=H,
                    json={"topic": topic, "workflowVersionId": vid, "status": "active"}, timeout=10).json()
print("sub:", json.dumps(sub, ensure_ascii=False))
assert sub.get("code") == 0, "sub create failed"

prev = requests.get(BASE + "/executions?pageNo=1&pageSize=50", headers=H, timeout=10).json()
prev_ids = {e["id"] for e in prev["data"]["records"]}

time.sleep(2)  # 等后端重订阅生效
t0 = time.time()
msg = {"temp": 97, "deviceId": "s-1031r2"}
r = subprocess.run(["docker", "exec", "swa-mosquitto", "mosquitto_pub", "-h", "localhost",
                    "-t", topic, "-m", json.dumps(msg)], capture_output=True, timeout=15)
print("pub rc=%s err=%s" % (r.returncode, r.stderr.decode(errors="ignore")[:200]))

found = None
for _ in range(24):
    time.sleep(0.5)
    cur = requests.get(BASE + "/executions?pageNo=1&pageSize=50", headers=H, timeout=10).json()
    for e in cur["data"]["records"]:
        if e["id"] not in prev_ids and e.get("triggerType") == "mqtt" and e.get("versionId") == vid:
            found = e
            break
    if found:
        break
latency = time.time() - t0
if not found:
    print("FAIL mqtt_e2e_r2 NO_NEW_EXEC")
    sys.exit(1)

# 等终态
st = None
for _ in range(60):
    d = requests.get(BASE + "/executions/%s" % found["id"], headers=H, timeout=10).json()
    st = d["data"]["status"]
    if st in ("SUCCESS", "FAILED"):
        break
    time.sleep(1)
nodes = requests.get(BASE + "/executions/%s/nodes" % found["id"], headers=H, timeout=10).json()["data"]
nm = {n["nodeId"]: n for n in nodes}
ok = st == "SUCCESS" and latency <= 3.0 and nm.get("h1", {}).get("status") == "SUCCESS"
with open(os.path.join(EV, "13_mqtt_e2e.json"), "w", encoding="utf-8") as f:
    json.dump({"topic": topic, "exec": found, "status": st, "latency_s": round(latency, 2),
               "nodes": nm}, f, ensure_ascii=False, indent=2, default=str)
print("PASS" if ok else "FAIL", "| mqtt_e2e_r2 | exec=%s st=%s latency=%.2fs h1=%s" % (
    found["id"], st, latency, nm.get("h1", {}).get("status")))
sys.exit(0 if ok else 1)
