# -*- coding: utf-8 -*-
import os, subprocess, sys, time, urllib.request

AGENT_DIR = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
READY = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\agent.ready"
ENV_FILE = os.path.join(AGENT_DIR, ".env")

env = os.environ.copy()
with open(ENV_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

if os.path.exists(READY):
    os.remove(READY)

py = os.path.join(AGENT_DIR, ".venv", "Scripts", "python.exe")
p = subprocess.Popen([py, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"],
                     cwd=AGENT_DIR, env=env)
print("AGENT_STARTED pid=%d" % p.pid, flush=True)

up = False
for i in range(45):
    time.sleep(2)
    try:
        with urllib.request.urlopen("http://localhost:8085/health", timeout=3) as r:
            if r.status == 200:
                up = True
                break
    except Exception:
        pass
    if p.poll() is not None:
        print("AGENT_EXITED rc=%d" % p.returncode, flush=True)
        sys.exit(1)

print("AGENT_UP=%s after %ds" % (up, i * 2), flush=True)
if up:
    with open(READY, "w") as f:
        f.write(str(p.pid))
    # keep launcher alive holding the child; blocks until killed
    try:
        p.wait()
    except KeyboardInterrupt:
        pass
