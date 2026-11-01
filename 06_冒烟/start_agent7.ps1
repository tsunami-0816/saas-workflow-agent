$ErrorActionPreference = 'Stop'
$work = 'd:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python'
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
$err = 'd:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\python-agent-final-err.log'
Remove-Item $log, $err -ErrorAction SilentlyContinue
$pyExe = "$work\.venv\Scripts\python.exe"
# Start-Process: working dir via -WorkingDirectory; env inherited from current process
$p = Start-Process -FilePath $pyExe -ArgumentList '-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8085' -WorkingDirectory $work -RedirectStandardOutput $log -RedirectStandardError $err -PassThru -WindowStyle Hidden
"STARTED pid=$($p.Id)"
$p.Id | Out-File 'd:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\agent.pid' -Encoding ascii
