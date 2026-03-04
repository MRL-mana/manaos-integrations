#!/usr/bin/env pwsh
# setup_git_hooks.ps1
# git hooks をセットアップ（CLAUDE.md への教訓自動注入）
#
# 使い方:
#   cd manaos_integrations
#   .\scripts\setup_git_hooks.ps1

$ErrorActionPreference = "Stop"

$RepoRoot  = (Get-Item "$PSScriptRoot\..").FullName
$HooksDir  = Join-Path $RepoRoot ".git\hooks"
$HookFile  = Join-Path $HooksDir "pre-commit"
$InjectPy  = Join-Path $RepoRoot "scripts\misc\git_hook_inject_lessons.py"

Write-Host "📦 MANAOS git hooks セットアップ" -ForegroundColor Cyan
Write-Host "   RepoRoot : $RepoRoot"
Write-Host "   HooksDir : $HooksDir"

# .git/hooks が存在するか確認
if (-not (Test-Path $HooksDir)) {
    Write-Host "❌ .git/hooks が見つかりません。git リポジトリのルートで実行してください。" -ForegroundColor Red
    exit 1
}

# pre-commit hook の内容（bash スクリプト）
$hookContent = @'
#!/bin/bash
# ManaOS: 教訓自動注入 pre-commit hook
REPO_ROOT="$(git rev-parse --show-toplevel)"
INJECT="$REPO_ROOT/scripts/misc/inject_lessons_to_claude_md.py"
CLAUDE_MD="$REPO_ROOT/CLAUDE.md"

if [ ! -f "$INJECT" ]; then
  exit 0
fi

python "$INJECT" 2>/dev/null

# CLAUDE.md が変更されていたらステージング
if git diff --name-only -- "$CLAUDE_MD" | grep -q "CLAUDE.md"; then
  git add "$CLAUDE_MD"
  echo "[hook] CLAUDE.md updated + staged"
fi

exit 0
'@

# 既存のhookをバックアップ
if (Test-Path $HookFile) {
    $backup = "$HookFile.bak"
    Copy-Item $HookFile $backup -Force
    Write-Host "⚠ 既存のpre-commitをバックアップ: $backup" -ForegroundColor Yellow
}

# hook ファイルを書き込み（bash は LF 改行必須）
$lf = $hookContent -replace "`r`n", "`n" -replace "`r", "`n"
[System.IO.File]::WriteAllText($HookFile, $lf, [System.Text.Encoding]::UTF8)
Write-Host "✅ pre-commit hook を作成しました: $HookFile" -ForegroundColor Green

# Unix実行権限は Windowsでは不要だが、WSLで使う場合は chmod を促す
Write-Host ""
Write-Host "💡 WSL から使う場合は:" -ForegroundColor Cyan
Write-Host "   chmod +x .git/hooks/pre-commit"
Write-Host ""
Write-Host "✅ セットアップ完了！次のコミットから自動で教訓が CLAUDE.md に注入されます。"
