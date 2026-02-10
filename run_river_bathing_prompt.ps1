# 川で沐浴・濡れ透けプロンプトで1枚生成
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$prompt = Get-Content (Join-Path $root "prompt_river_bathing.txt") -Raw
$negative = Get-Content (Join-Path $root "negative_river.txt") -Raw
Set-Location $root
python -u generate_50_mana_mufufu_manaos.py -n 1 --profile lab --prompt $prompt --negative $negative
