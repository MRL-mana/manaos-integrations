# Alice (Nikke) 風・Kpop idol / slime girl プロンプトで1枚生成
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$prompt = Get-Content (Join-Path $root "prompt_alice_nikke.txt") -Raw
$negative = Get-Content (Join-Path $root "negative_alice.txt") -Raw
Set-Location $root
python -u generate_50_mana_mufufu_manaos.py -n 1 --profile lab --prompt $prompt --negative $negative
