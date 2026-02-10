# メイドプロンプトで1枚生成（prompt_maid.txt / negative_maid.txt を使用）
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$prompt = Get-Content (Join-Path $root "prompt_maid.txt") -Raw
$negative = Get-Content (Join-Path $root "negative_maid.txt") -Raw
Set-Location $root
python -u generate_50_mana_mufufu_manaos.py -n 1 --profile lab --prompt $prompt --negative $negative
