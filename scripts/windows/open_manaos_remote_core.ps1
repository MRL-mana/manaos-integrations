param(
  [ValidateSet("root","docs","health")]
  [string]$Target = "root",

  [int]$LocalPort = 9502
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ServeBaseUrl {
  try {
    $raw = (& tailscale serve status --json 2>$null | Out-String)
    if ($raw) {
      try {
        $obj = $raw | ConvertFrom-Json
        $web = $obj.Web
        if ($web) {
          function Test-ContainsString {
            param(
              [Parameter(Mandatory=$true)]$Value,
              [Parameter(Mandatory=$true)][string]$Needle
            )

            if ($null -eq $Value) { return $false }

            if ($Value -is [string]) {
              return $Value -like "*$Needle*"
            }

            if ($Value -is [System.Collections.IDictionary]) {
              foreach ($k in $Value.Keys) {
                if (Test-ContainsString -Value $Value[$k] -Needle $Needle) { return $true }
              }
              return $false
            }

            if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
              foreach ($item in $Value) {
                if (Test-ContainsString -Value $item -Needle $Needle) { return $true }
              }
              return $false
            }

            # PSCustomObject or other objects
            $props = $Value.PSObject.Properties
            if ($props) {
              foreach ($p in $props) {
                if (Test-ContainsString -Value $p.Value -Needle $Needle) { return $true }
              }
            }

            return $false
          }

          $keys = @($web.PSObject.Properties.Name)
          if ($keys -and $keys.Count -gt 0) {
            $needle = "127.0.0.1:$LocalPort"

            foreach ($k in $keys) {
              try {
                $entry = $web.$k
                if (Test-ContainsString -Value $entry -Needle $needle) {
                  $host = ([string]$k -split ':')[0]
                  if ($host) { return "https://$host" }
                }
              } catch {
              }
            }

            # fallback: first key
            $hostPort = [string]$keys[0]
            $host = ($hostPort -split ':')[0]
            if ($host) { return "https://$host" }
          }
        }
      } catch {
        # fall through to text parse
      }
    }

    $txt = (& tailscale serve status 2>$null | Out-String)
    if ($txt) {
      $needle = "127.0.0.1:$LocalPort"

      # Prefer an URL that proxies to localhost:$LocalPort
      $m = [regex]::Match($txt, '(https://[A-Za-z0-9.-]+)[^\r\n]*\r?\n\|--\s+/\s+proxy\s+http://127\.0\.0\.1:' + [regex]::Escape([string]$LocalPort))
      if ($m.Success) {
        return $m.Groups[1].Value
      }

      if ($txt -match '(https://[A-Za-z0-9.-]+)') {
        return $Matches[1]
      }
    }

    return ""
  } catch {
    return ""
  }
}

$base = Get-ServeBaseUrl
if ([string]::IsNullOrWhiteSpace($base)) {
  Write-Host "[NG] tailscale serve is not configured for localhost:$LocalPort" -ForegroundColor Red
  Write-Host "Run VS Code task: 'ManaOS: Tailscale Serve 有効化（9502→https）'" -ForegroundColor Yellow
  Write-Host "Or run: tailscale serve --bg $LocalPort" -ForegroundColor Yellow
  exit 2
}

$url = switch ($Target) {
  "docs" { "$base/docs" }
  "health" { "$base/health" }
  default { "$base/" }
}

Write-Host "Opening: $url" -ForegroundColor Cyan
Start-Process $url
