# cuteGirlMix4 風・nude/nsfw プロンプトで1枚生成
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$prompt = Get-Content (Join-Path $root "prompt_nude_nsfw.txt") -Raw
$negative = Get-Content (Join-Path $root "negative_short.txt") -Raw
Set-Location $root
python -u generate_50_mana_mufufu_manaos.py -n 1 --profile lab --prompt $prompt --negative $negative
