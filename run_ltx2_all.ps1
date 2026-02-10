# LTX-2: patch + generate in one go
# Usage: .\run_ltx2_all.ps1
#        .\run_ltx2_all.ps1 "your prompt here"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
$prompt = if ($args.Count -gt 0) { $args[0] } else { "a calm sea, sunset" }
python run_ltx2_all.py --prompt $prompt
exit $LASTEXITCODE
