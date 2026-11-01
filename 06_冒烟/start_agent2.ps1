$ErrorActionPreference = 'Stop'
$envFile = "d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python\.env"
Get-Content $envFile | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
  $i = $_.IndexOf('=')
  if ($i -gt 0) {
    $k = $_.Substring(0, $i).Trim()
    $v = $_.Substring($i + 1).Trim()
    [Environment]::SetEnvironmentVariable($k, $v, 'Process')
  }
}
Set-Location "d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\agent-python"
$log = "d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\python-agent.log"
$err = "d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\python-agent-err.log"
$p = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8085" -RedirectStandardOutput $log -RedirectStandardError $err -PassThru -WindowStyle Hidden
"STARTED pid=$($p.Id)"
$p.Id | Out-File "d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\agent.pid" -Encoding ascii
