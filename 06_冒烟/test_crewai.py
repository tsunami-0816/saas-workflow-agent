# -*- coding: utf-8 -*-
import os, sys, traceback
os.environ["CREWAI_STORAGE_DIR"] = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\crewai_storage"
sys.path.insert(0, r"d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python")
from crewai import Agent, Crew, Process, Task
from app.crew_llm import JavaGatewayLLM
from app.llm_client import JavaLLMClient

c = JavaLLMClient("http://localhost:8083", 30, "swa-dev-only-internal-token-20261028-z9y8x7w6")
llm = JavaGatewayLLM(client=c, task_type="agent_reasoning", temperature=0.3, max_tokens=256)
a = Agent(role="t", goal="t", backstory="t", llm=llm, allow_delegation=False, verbose=False)
t = Task(description="say hi", expected_output="hi", agent=a)
cr = Crew(agents=[a], tasks=[t], process=Process.sequential, verbose=False, memory=False)
OUT = r"d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\crewai_test_out.txt"
with open(OUT, "w", encoding="utf-8") as f:
    try:
        r = cr.kickoff()
        f.write("OK: " + getattr(r, "raw", str(r))[:500] + "\n")
    except Exception as e:
        f.write("FAIL: %s %s\n" % (type(e).__name__, e))
        f.write(traceback.format_exc())
print("done")
