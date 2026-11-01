# -*- coding: utf-8 -*-
import os, subprocess, time, urllib.request, sys

AGENT_DIR = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
OUT_FILE = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\agent_launch.log"
ENV_FILE = os.path.join(AGENT_DIR, ".env")

env = os.environ.copy()
with open(ENV_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

log = open(OUT_FILE, "w", encoding="utf-8")
def w(msg):
    log.write(msg + "\n"); log.flush()
    print(msg, flush=True)

w("ENV_CREWAI=%s" % env.get("CREWAI_STORAGE_DIR"))
w("ENV_TOKEN=%s..." % (env.get("INTERNAL_API_TOKEN") or "")[:20])

py = os.path.join(AGENT_DIR, ".venv", "Scripts", "python.exe")
p = subprocess.Popen([py, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"],
                     cwd=AGENT_DIR, env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
w("AGENT_STARTED pid=%d" % p.pid)

# read stdout in thread + wait for health
import threading
def drain():
    for line in p.stdout:
        w("UVICORN> " + line.rstrip())
threading.Thread(target=drain, daemon=True).start()

up = False
for i in range(60):
    time.sleep(2)
    try:
        with urllib.request.urlopen("http://localhost:8085/health", timeout=3) as r:
            if r.status == 200:
                up = True
                break
    except Exception:
        pass
    rc = p.poll()
    if rc is not None:
        w("AGENT_EXITED rc=%d after %ds" % (rc, i * 2))
        sys.exit(1)

w("AGENT_UP=%s after %ds" % (up, i * 2))
if up:
    with open(r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\agent.ready", "w") as f:
        f.write(str(p.pid))
    # keep alive
    try:
        p.wait()
    except KeyboardInterrupt:
        pass
