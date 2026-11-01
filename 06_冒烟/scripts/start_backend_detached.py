# -*- coding: utf-8 -*-
"""以 DETACHED 方式启动 java-backend（避免沙箱会话结束杀子进程）。env 从 05_代码/.env 注入。"""
import os
import subprocess
import sys

ROOT = r"d:\lg\project\工作流测试\projects\saas-workflow-agent"
ENV = os.path.join(ROOT, "05_代码", ".env")
CWD = os.path.join(ROOT, "05_代码", "backend")
LOG = os.path.join(ROOT, "06_冒烟", "java-backend-1031.log")

env = dict(os.environ)
with open(ENV, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

f = open(LOG, "ab")
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
p = subprocess.Popen(["java", "-jar", "target\\java-backend-1.0.0.jar"],
                     cwd=CWD, env=env, stdout=f, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, creationflags=DETACHED, close_fds=True)
print("BACKEND_PID=%d" % p.pid)
sys.exit(0)
