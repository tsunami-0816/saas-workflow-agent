# -*- coding: utf-8 -*-
import os, subprocess
AGENT_DIR = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
py = os.path.join(AGENT_DIR, ".venv", "Scripts", "python.exe")
p = subprocess.run([py, "-c", "print('HELLO'); import sys; sys.stdout.flush()"],
                   cwd=AGENT_DIR, capture_output=True, timeout=20)
print("rc=%d" % p.returncode)
print("stdout=%s" % p.stdout)
print("stderr=%s" % p.stderr)
