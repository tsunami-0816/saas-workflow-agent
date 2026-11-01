# -*- coding: utf-8 -*-
import os, subprocess, sys

AGENT_DIR = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
SCRIPT = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\test_crewai.py"
OUT = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\crewai_run.log"

env = os.environ.copy()
env["CREWAI_STORAGE_DIR"] = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\crewai_storage"

py = os.path.join(AGENT_DIR, ".venv", "Scripts", "python.exe")
with open(OUT, "wb") as f:
    p = subprocess.run([py, SCRIPT], cwd=AGENT_DIR, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=120)
print("exit=%d" % p.returncode)
