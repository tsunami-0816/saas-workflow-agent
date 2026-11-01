# -*- coding: utf-8 -*-
import os, subprocess
AGENT_DIR = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
py = os.path.join(AGENT_DIR, ".venv", "Scripts", "python.exe")
OUT = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\import_test.log"
with open(OUT, "wb") as f:
    p = subprocess.run([py, "-c", "from app.main import app; print('IMPORT_OK')"],
                       cwd=AGENT_DIR, stdout=f, stderr=subprocess.STDOUT, timeout=90)
    f.write(b"\n---rc=%d---" % p.returncode)
print("done rc=%d" % p.returncode)
