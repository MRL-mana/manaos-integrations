#!/usr/bin/env pwsh
# OH MY OPENCODE APIキー設定スクリプト
# 注意: OH MY OPENCODEは既存のLLMプロバイダのAPIキーを使用します
# OpenRouter / OpenAI / Anthropic などのAPIキーを設定してください

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("OpenRouter", "OpenAI", "Anthropic")]
    [string]$Provider = "OpenRouter"
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "OH MY OPENCODE APIキー設定" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "プロバイダ: $Provider" -ForegroundColor Yellow
Write-Host ""

# プロバイダに応じた環境変数を設定
switch ($Provider) {
    "OpenRouter" {
        $envVarName = "OPENROUTER_API_KEY"
        $env:OPENROUTER_API_KEY = $ApiKey
        [System.Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY", $ApiKey, "User")
        Write-Host "[OK] OpenRouter APIキーを設定しました" -ForegroundColor Green
    }
    "OpenAI" {
        $envVarName = "OPENAI_API_KEY"
        $env:OPENAI_API_KEY = $ApiKey
        [System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $ApiKey, "User")
        Write-Host "[OK] OpenAI APIキーを設定しました" -ForegroundColor Green
    }
    "Anthropic" {
        $envVarName = "ANTHROPIC_API_KEY"
        $env:ANTHROPIC_API_KEY = $ApiKey
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $ApiKey, "User")
        Write-Host "[OK] Anthropic APIキーを設定しました" -ForegroundColor Green
    }
}

# 後方互換性のため、OH_MY_OPENCODE_API_KEYも設定（非推奨）
$env:OH_MY_OPENCODE_API_KEY = $ApiKey
[System.Environment]::SetEnvironmentVariable("OH_MY_OPENCODE_API_KEY", $ApiKey, "User")

Write-Host "[OK] 環境変数に設定しました" -ForegroundColor Green
Write-Host ""

# .envファイルにも追加（存在する場合）
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    
    # プロバイダに応じた環境変数を追加/更新
    if ($envContent -match "$envVarName=") {
        $envContent = $envContent -replace "$envVarName=.*", "$envVarName=$ApiKey"
        Set-Content -Path $envFile -Value $envContent -NoNewline
        Write-Host "[OK] .envファイルを更新しました ($envVarName)" -ForegroundColor Green
    } else {
        Add-Content -Path $envFile -Value "`n$envVarName=$ApiKey"
        Write-Host "[OK] .envファイルに追加しました ($envVarName)" -ForegroundColor Green
    }
    
    # 後方互換性のため、OH_MY_OPENCODE_API_KEYも追加（非推奨）
    if ($envContent -notmatch "OH_MY_OPENCODE_API_KEY=") {
        Add-Content -Path $envFile -Value "`nOH_MY_OPENCODE_API_KEY=$ApiKey"
    }
} else {
    # .envファイルが存在しない場合は作成
    $content = "$envVarName=$ApiKey`nOH_MY_OPENCODE_API_KEY=$ApiKey"
    Set-Content -Path $envFile -Value $content
    Write-Host "[OK] .envファイルを作成しました" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "設定完了！" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "1. 新しいPowerShellウィンドウを開く（環境変数を反映）" -ForegroundColor White
$providerMsg = "2. oh_my_opencode_config.yamlを更新（api.base_urlを" + $Provider + "に合わせる）"
Write-Host $providerMsg -ForegroundColor White
Write-Host "3. 統合APIサーバーを起動: python unified_api_server.py" -ForegroundColor White
Write-Host "4. 動作確認: curl -X POST http://localhost:9500/api/oh_my_opencode/execute ..." -ForegroundColor White
Write-Host ""
Write-Host "注意: OH MY OPENCODEは既存のLLMプロバイダのAPIキーを使用します" -ForegroundColor Yellow
$keyMsg = "      " + $Provider + " のAPIキーを設定しました"
Write-Host $keyMsg -ForegroundColor Yellow
Write-Host ""
