$ErrorActionPreference = 'Stop'
$tok = (Get-Content "$PSScriptRoot\tokens.json" | ConvertFrom-Json).dev_acme
$H = @{ Authorization = "Bearer $tok" }
$base = "http://localhost:8083/api/v1"

# 1. 创建流程
$wfBody = @{ name = "冒烟-高温告警e2e"; description = "阶段一冒烟：3节点含条件分支" } | ConvertTo-Json
$wf = Invoke-RestMethod -Uri "$base/workflows" -Method Post -Headers $H -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($wfBody))
"CREATE_WF code=$($wf.code) id=$($wf.data.id) name=$($wf.data.name)"
$wfId = $wf.data.id

# 2. 保存 DSL 版本: mqtt-trigger t1 -> condition c1 --true--> http h1, --false--> code d1
$dsl = @{
  nodes = @(
    @{ id = "t1"; type = "mqtt-trigger"; config = @{ topic = "factory/+/temperature" } },
    @{ id = "c1"; type = "condition"; config = @{ expression = "t1.payload.temp > 80" } },
    @{ id = "h1"; type = "http"; config = @{ method = "GET"; url = "http://localhost:8083/actuator/health" } },
    @{ id = "d1"; type = "code"; config = @{ expression = "'low-temp:' + string(t1.payload.temp)" } }
  )
  edges = @(
    @{ source = "t1"; target = "c1" },
    @{ source = "c1"; target = "h1"; branch = "true" },
    @{ source = "c1"; target = "d1"; branch = "false" }
  )
} | ConvertTo-Json -Depth 6 -Compress
$verBody = @{ dslJson = $dsl } | ConvertTo-Json
$ver = Invoke-RestMethod -Uri "$base/workflows/$wfId/versions" -Method Post -Headers $H -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($verBody))
"SAVE_VER code=$($ver.code) versionId=$($ver.data.id) versionNo=$($ver.data.versionNo) status=$($ver.data.status)"
if ($ver.code -ne 0) { $ver | ConvertTo-Json -Depth 5 }

@{ wfId = $wfId; versionId = $ver.data.id } | ConvertTo-Json | Set-Content "$PSScriptRoot\smoke_wf.json" -Encoding UTF8
