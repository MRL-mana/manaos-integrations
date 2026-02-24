# LoRA用: 画像→.txt キャプション自動生成（Ollama Vision）

param(
  [Parameter(Mandatory=$true)][string]$InputDir,
  [string]$Model = $env:MANAOS_VISION_MODEL,
  [string]$Trigger = "",
  [string]$Ignore = "",
  [ValidateSet('none','sequential')][string]$Rename = 'none',
  [switch]$Overwrite,
  [switch]$DryRun
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$argsList = @(
  "$root\lora_caption_prep.py",
  $InputDir,
  "--rename", $Rename
)

if($Model){ $argsList += @("--model", $Model) }
if($Trigger){ $argsList += @("--trigger", $Trigger) }
if($Ignore){ $argsList += @("--ignore", $Ignore) }
if($Overwrite){ $argsList += @("--overwrite") }
if($DryRun){ $argsList += @("--dry-run") }

py -3.10 @argsList
