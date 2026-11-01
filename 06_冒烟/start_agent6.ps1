$ErrorActionPreference = 'Stop'
$work = 'd:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python'
# read .env (utf8 explicitly)
$lines = [System.IO.File]::ReadAllLines("$work\.env", [System.Text.Encoding]::UTF8)
foreach ($line in $lines) {
  $t = $line.Trim()
  if ($t -eq '' -or $t.StartsWith('#') -or -not $t.Contains('=')) { continue }
  $i = $t.IndexOf('=')
  $k = $t.Substring(0, $i).Trim()
  $v = $t.Substring($i + 1).Trim()
  Set-Item -Path "env:$k" -Value $v
}
$log = 'd:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\python-agent-final.log'
Remove-Item $log -ErrorAction SilentlyContinue
# 用 cmd 启动并重定向，避开 PS 编码问题
$pyExe = "$work\.venv\Scripts\python.exe"
$cmdLine = "/c `"cd /d `"$work`" && `"$pyExe`" -m uvicorn app.main:app --host 0.0.0.0 --port 8085 > `"$log`" 2>&1`""
$p = Start-Process -FilePath "cmd.exe" -ArgumentList $cmdLine -PassThru -WindowStyle Hidden
"STARTED cmdPid=$($p.Id)"
$p.Id | Out-File 'd:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\agent.pid' -Encoding ascii
