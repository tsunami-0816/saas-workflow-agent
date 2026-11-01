$ErrorActionPreference = 'Continue'
$work = "d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
$script = "d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\test_crewai.py"
$out = "d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\crewai_stdout.log"
$err = "d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\crewai_stderr.log"
Remove-Item $out, $err -ErrorAction SilentlyContinue
$p = Start-Process -FilePath "$work\.venv\Scripts\python.exe" -ArgumentList "`"$script`"" -WorkingDirectory $work -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
"started pid=$($p.Id)"
$done = $p.WaitForExit(90000)
"exited=$exited exitCode=$($p.ExitCode)"
