# add_castle_ex_layer2_to_cursor.ps1
# Register castle_ex_layer2 MCP server to Cursor MCP config

$CursorMcpConfig = "$env:APPDATA\Cursor\User\globalStorage\cursor.cursor\mcp.json"
$FallbackConfig  = "$env:USERPROFILE\.cursor\mcp.json"
$Python          = "py"
$PythonVer       = "-3.10"

# Find config file
$ConfigPath = if (Test-Path $CursorMcpConfig) { $CursorMcpConfig } else { $FallbackConfig }

Write-Host "=== Castle-EX Layer2 MCP server registration ==="
Write-Host "Config: $ConfigPath"

# Load current config or create empty
$cfg = if (Test-Path $ConfigPath) {
    Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    [PSCustomObject]@{ mcpServers = [PSCustomObject]@{} }
}
if (-not $cfg.PSObject.Properties["mcpServers"]) {
    $cfg | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{})
}

# Add server entry
$entry = [PSCustomObject]@{
    command = $Python
    args    = @($PythonVer, "-m", "castle_ex_layer2_mcp_server")
    cwd     = "C:\Users\mana4\Desktop\manaos_integrations"
    env     = [PSCustomObject]@{
        LAYER2_INFER_URL = "http://127.0.0.1:9520"
        PORT             = "5140"
    }
}
$cfg.mcpServers | Add-Member -Force -NotePropertyName "castle-ex-layer2" -NotePropertyValue $entry

# Write config
$ConfigDir = Split-Path $ConfigPath
if (-not (Test-Path $ConfigDir)) { New-Item -ItemType Directory -Force $ConfigDir | Out-Null }
$cfg | ConvertTo-Json -Depth 10 | Set-Content $ConfigPath -Encoding UTF8

Write-Host "[OK] castle-ex-layer2 added to MCP config"
Write-Host "Please restart Cursor to activate"
