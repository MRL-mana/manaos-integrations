# ManaOS統合APIサーバー起動スクリプト
$ErrorActionPreference = "Stop"

# エンコーディングをUTF-8に設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ManaOS統合APIサーバー起動" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# カレントディレクトリに移動
Set-Location $PSScriptRoot

# サーバーを起動
try {
    python start_server_direct.py
} catch {
    Write-Host "エラーが発生しました: $_" -ForegroundColor Red
    Read-Host "Enterキーを押して終了"
}








