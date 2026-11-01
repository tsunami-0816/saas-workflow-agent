# -*- coding: utf-8 -*-
import os, subprocess
AGENT_DIR = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
py = os.path.join(AGENT_DIR, ".venv", "Scripts", "python.exe")
p = subprocess.run([py, "-c", "from app.main import app; print('IMPORT_OK')"],
                   cwd=AGENT_DIR, capture_output=True, timeout=90)
print("rc=%d" % p.returncode)
print("stdout=%s" % p.stdout.decode("utf-8", "replace"))
print("stderr=%s" % p.stderr.decode("utf-8", "replace"))
