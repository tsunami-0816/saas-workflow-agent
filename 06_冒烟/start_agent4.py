# -*- coding: utf-8 -*-
import os, subprocess, time, urllib.request

AGENT_DIR = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
LOG = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\python-agent3.log"
ENV_FILE = os.path.join(AGENT_DIR, ".env")

env = os.environ.copy()
with open(ENV_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

py = os.path.join(AGENT_DIR, ".venv", "Scripts", "python.exe")
# inherit stdout/stderr to this console so we can see uvicorn output
p = subprocess.Popen([py, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"],
                     cwd=AGENT_DIR, env=env)
print("AGENT_STARTED pid=%d" % p.pid)

# wait for health
up = False
for i in range(30):
    time.sleep(2)
    try:
        with urllib.request.urlopen("http://localhost:8085/health", timeout=3) as r:
            if r.status == 200:
                up = True
                break
    except Exception:
        pass
print("AGENT_UP=%s after %ds" % (up, i * 2))
if up:
    # detach: leave process running, just exit this launcher
    print("AGENT_DETACHED pid=%d" % p.pid)
else:
    p.terminate()
