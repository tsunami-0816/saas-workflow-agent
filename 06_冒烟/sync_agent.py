# -*- coding: utf-8 -*-
import os, subprocess, sys, time

AGENT_DIR = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
OUT_FILE = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\agent_sync.log"
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

# 直接同步 run，最多 30s，看启动到哪个阶段
with open(OUT_FILE, "wb") as f:
    try:
        p = subprocess.run([py, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"],
                           cwd=AGENT_DIR, env=env, stdin=subprocess.DEVNULL,
                           stdout=f, stderr=subprocess.STDOUT, timeout=30)
        print("EXIT rc=%d" % p.returncode)
    except subprocess.TimeoutExpired:
        print("TIMEOUT_30S (uvicorn still running, this is expected for a server)")
