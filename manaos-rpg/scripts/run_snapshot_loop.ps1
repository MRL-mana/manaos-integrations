$ErrorActionPreference = 'Stop'

param(
  [int]$IntervalSec = 15,
  [string]$BaseUrl = 'http://127.0.0.1:9510'
)

Write-Host "[manaos-rpg] snapshot loop start: interval=${IntervalSec}s base=${BaseUrl}" -ForegroundColor Green

while ($true) {
  try {
    $r = Invoke-RestMethod "$BaseUrl/api/snapshot" -TimeoutSec 8
    $ts = $r.ts
    $danger = $r.danger
    $msg = "ts=$ts danger=$danger"
    if ($r.next_actions -and $r.next_actions.Count -gt 0) {
      $msg += " next='" + ($r.next_actions[0]) + "'"
    }
    Write-Host "[snapshot] $msg" -ForegroundColor Cyan
  } catch {
    Write-Host "[snapshot] ERR: $($_.Exception.Message)" -ForegroundColor Red
  }
  Start-Sleep -Seconds $IntervalSec
}
