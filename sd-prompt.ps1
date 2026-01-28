# Stable Diffusion 専用プロンプターコマンド (PowerShell版)
# Uncensored Llama3モデルを使用して画像生成プロンプトを生成

param(
    # 例: .\sd-prompt.ps1 "猫がベッドで寝ている"
    #     .\sd-prompt.ps1 -Temperature 0.8 "宇宙船が星間空間を航行している"
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Prompt,

    [string]$Model = "llama3-uncensored",
    [double]$Temperature = 0.9
)

# 外部コマンド（ollama）へ日本語を渡すためのエンコード調整
# - Windows PowerShell では既定がUTF-8でないことがあるため、明示する
try {
    $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {
    # 環境依存: 失敗しても続行
}

# NOTE:
# このスクリプトは HTTP API ではなく `ollama run`（CLI）を使って生成します。
# Windows環境でポート競合（WSL/Docker 等）していても動くようにするためです。

# 使用方法を表示
function Show-Usage {
    $usage = @(
        '使用方法: sd-prompt.ps1 [オプション] <日本語の説明>',
        '',
        'Stable Diffusion用の画像生成プロンプトを生成します。',
        '',
        'オプション:',
        '  -Model NAME          使用するモデル名（デフォルト: llama3-uncensored）',
        '  -Temperature N       温度パラメータ（0.0-1.0、デフォルト: 0.9）',
        '',
        '例:',
        '  .\sd-prompt.ps1 "猫がベッドで寝ている"',
        '  .\sd-prompt.ps1 "美しい夕日と海"',
        '  .\sd-prompt.ps1 -Temperature 0.8 "宇宙船が星間空間を航行している"',
        ''
    ) -join "`n"

    Write-Host $usage
}

# プロンプトが指定されていない場合
if ($null -eq $Prompt -or $Prompt.Count -eq 0) {
    Write-Host "エラー: プロンプトを指定してください" -ForegroundColor Red
    Show-Usage
    exit 1
}

$UserInput = $Prompt -join " "

# Ollama CLI が使えるか確認
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "エラー: 'ollama' コマンドが見つかりません" -ForegroundColor Red
    Write-Host "Ollamaをインストールしてから再実行してください" -ForegroundColor Yellow
    exit 1
}

# プロンプト生成のリクエストを作成
$SystemPrompt = 'You are an expert at creating detailed prompts for Stable Diffusion image generation. Convert the following Japanese description into a detailed, descriptive English prompt suitable for Stable Diffusion. Include style, composition, lighting, and other relevant details. Output STRICTLY valid JSON with a single top-level key "prompt" whose value is the English prompt string. Do not include any other keys or any extra text.'

$CombinedPrompt = @(
    $SystemPrompt,
    "",
    "Japanese description: $UserInput",
    "",
    "English prompt for Stable Diffusion:"
) -join "`n"

Write-Host "プロンプトを生成中..." -ForegroundColor Yellow
Write-Host ""

try {
    # `ollama run` は対話モードになるため、/set と /bye を送って終了させる
    $lines = @(
        "/set parameter temperature $Temperature",
        $CombinedPrompt,
        "/bye"
    )
    $raw = $lines | & ollama run $Model --format json --nowordwrap 2>&1
    $rawText = ($raw | Out-String)

    # 出力中の制御文字/スピナーを含むため、最後のJSONオブジェクトを抽出する
    $jsonMatches = [regex]::Matches($rawText, "\{.*?\}", [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if ($jsonMatches.Count -eq 0) {
        throw "JSONレスポンスを抽出できませんでした。出力: $rawText"
    }

    $json = $jsonMatches[$jsonMatches.Count - 1].Value
    $obj = $json | ConvertFrom-Json
    # ???/??????????????????????: response / prompt?
    $GeneratedPrompt = $obj.response
    if ([string]::IsNullOrEmpty($GeneratedPrompt)) {
        $GeneratedPrompt = $obj.prompt
    }
    if ([string]::IsNullOrEmpty($GeneratedPrompt)) {
        $GeneratedPrompt = $obj.message
    }

    if ([string]::IsNullOrEmpty($GeneratedPrompt)) {
        throw "レスポンスに期待したキー (response/prompt/message) がありません。JSON: $json"
    }

    # 結果を表示
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "生成されたプロンプト:" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host $GeneratedPrompt -ForegroundColor White
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""

    # クリップボードにコピー（失敗しても生成結果は保持）
    try {
        $GeneratedPrompt | Set-Clipboard
        Write-Host "✓ クリップボードにコピーしました" -ForegroundColor Green
    } catch {
        Write-Host "※ クリップボードへのコピーに失敗しました（表示されたプロンプトは有効です）" -ForegroundColor Yellow
    }
} catch {
    Write-Host "エラー: プロンプト生成に失敗しました" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
