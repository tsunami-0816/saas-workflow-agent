$ErrorActionPreference = 'Stop'
$envFile = "d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\.env"
Get-Content $envFile | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
  $i = $_.IndexOf('=')
  if ($i -gt 0) {
    $k = $_.Substring(0, $i).Trim()
    $v = $_.Substring($i + 1).Trim()
    [Environment]::SetEnvironmentVariable($k, $v, 'Process')
  }
}
Set-Location "d:\lg\project\工作流测试\projects\saas-workflow-agent\05_代码\backend"
$log = "d:\lg\project\工作流测试\projects\saas-workflow-agent\06_冒烟\java-backend.log"
if (Test-Path $log) { Remove-Item $log -Force }
java -jar target\java-backend-1.0.0.jar *>> $log
