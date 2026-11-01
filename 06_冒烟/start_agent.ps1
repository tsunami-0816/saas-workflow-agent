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
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8085
