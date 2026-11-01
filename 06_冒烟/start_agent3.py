# -*- coding: utf-8 -*-
import os, subprocess, sys

AGENT_DIR = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
LOG = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\python-agent2.log"
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
log_f = open(LOG, "ab", buffering=0)
p = subprocess.Popen([py, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"],
                     cwd=AGENT_DIR, env=env, stdout=log_f, stderr=subprocess.STDOUT,
                     creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
print("AGENT_STARTED pid=%d" % p.pid)
with open(r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\agent.pid", "w") as f:
    f.write(str(p.pid))
