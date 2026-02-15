param(
  [string]$RepoRoot = "C:\Users\mana4\Desktop\manaos_integrations",
  [string]$Py = "py -3.10",
  [int]$VideoHealthPort = 5112,
  [int]$PicoHealthPort = 5136,
  [string]$UnifiedApiUrl = "http://127.0.0.1:9510"
)

$ErrorActionPreference = "Stop"

function Step([string]$msg) {
  Write-Host $msg -ForegroundColor Cyan
}

function Run([string]$cmd) {
  Write-Host ("`n$ {0}" -f $cmd) -ForegroundColor DarkGray
  cmd /c $cmd
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed (exit=$LASTEXITCODE): $cmd"
  }
}

$smoke = Join-Path $RepoRoot "devtools\mcp_stdio_smoke_test.py"
if (-not (Test-Path $smoke)) {
  throw "Missing: $smoke"
}

Step "[1/3] video-pipeline (initialize -> list_tools -> system_check)"
Run ('cd /d "{0}" && {1} "{2}" --cwd "{0}" --env PYTHONPATH={0} --env VIDEO_PIPELINE_HEALTH_PORT={3} --env MANAOS_LOG_TO_STDERR=1 --call system_check --payload "{{}}" -- -3.10 -m video_pipeline_mcp_server.server' -f $RepoRoot, $Py, $smoke, $VideoHealthPort)

Step "[2/3] pico-hid (initialize -> list_tools -> hid_status)"
Run ('cd /d "{0}" && {1} "{2}" --cwd "{0}" --env PYTHONPATH={0} --env PICO_HID_MCP_HEALTH_PORT={3} --env MANAOS_LOG_TO_STDERR=1 --call hid_status --payload "{{}}" -- -3.10 -m pico_hid_mcp_server' -f $RepoRoot, $Py, $smoke, $PicoHealthPort)

Step "[3/3] unified-api (initialize -> list_tools -> unified_api_health)"
Run ('cd /d "{0}" && {1} "{2}" --cwd "{0}" --env PYTHONPATH={0} --env MANAOS_INTEGRATION_API_URL={3} --env MANAOS_LOG_TO_STDERR=1 --call unified_api_health --payload "{{}}" -- -3.10 -m unified_api_mcp_server.server' -f $RepoRoot, $Py, $smoke, $UnifiedApiUrl)

Write-Host "`nOK: MCP stdio smoke tests passed." -ForegroundColor Green
