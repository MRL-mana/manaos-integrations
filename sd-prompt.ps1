# Stable Diffusion 専用プロンプターコマンド (PowerShell版)
# Uncensored Llama3モデルを使用して画像生成プロンプトを生成

param(
    # 例: .\sd-prompt.ps1 "猫がベッドで寝ている"
    #     .\sd-prompt.ps1 -Temperature 0.8 "宇宙船が星間空間を航行している"
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Prompt,

    [string]$Model = "llama3-uncensored",
    [double]$Temperature = 0.9,

    # Negative promptも生成する（A1111/Forge/ComfyUI用）
    [switch]$WithNegative,

    # LLMでNegative promptも生成する（遅い/詰まる場合があるため任意）
    [switch]$GenerateNegative,

    # クリップボードへのコピー対象
    [ValidateSet("positive", "both", "none")]
    [string]$Clipboard = "positive",

    # ollama run のタイムアウト（秒）
    [int]$TimeoutSec = 180,

    # Negative 生成時のタイムアウト（秒・GenerateNegative 時のみ）
    [int]$NegativeTimeoutSec = 120
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
        '  -WithNegative        Negative prompt も生成する',
        '  -GenerateNegative    LLMでNegative promptも生成する（遅い場合あり）',
        '  -Clipboard MODE      クリップボード copy 対象 (positive/both/none)',
        '  -TimeoutSec N        ollama run タイムアウト秒（デフォルト: 180）',
        '  -NegativeTimeoutSec N Negative 生成のタイムアウト秒（デフォルト: 120）',
        '',
        '例:',
        '  .\sd-prompt.ps1 "猫がベッドで寝ている"',
        '  .\sd-prompt.ps1 "美しい夕日と海"',
        '  .\sd-prompt.ps1 -Temperature 0.8 "宇宙船が星間空間を航行している"',
        '  .\sd-prompt.ps1 -WithNegative "夜の街のネオン"',
        '  .\sd-prompt.ps1 -WithNegative -GenerateNegative "夜の街のネオン"',
        '  .\sd-prompt.ps1 -WithNegative -Clipboard both "夜の街のネオン"',
        ''
    ) -join "`n"

    Write-Host $usage
}

function Normalize-PromptText {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $Text }
    $t = $Text.Trim()

    # 先頭の定型句を除去（SDでは不要）
    $t = $t -replace '^(?i)\s*(create|generate|make)\s+(an?\s+)?(image|picture|photo(graph)?|illustration|artwork)\s+of\s*[:,-]?\s*', ''
    $t = $t -replace '^(?i)\s*(prompt|positive prompt)\s*[:,-]\s*', ''

    return $t.Trim()
}

function Extract-Generation {
    param([string]$RawText)

    # 出力中の制御文字/スピナーを含むため、最後のJSONオブジェクトを抽出する
    $jsonMatches = [regex]::Matches($RawText, "\{.*?\}", [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if ($jsonMatches.Count -eq 0) {
        throw "JSONレスポンスを抽出できませんでした。出力: $RawText"
    }

    $json = $jsonMatches[$jsonMatches.Count - 1].Value
    $obj = $json | ConvertFrom-Json

    # まず Ollama/モデル側のトップレベル（response/text/prompt）を拾う
    $payload = $null
    foreach ($k in @("response", "text", "prompt", "message", "output")) {
        if ($null -ne $obj.$k -and -not [string]::IsNullOrEmpty([string]$obj.$k)) {
            $payload = [string]$obj.$k
            break
        }
    }

    # payload が JSONっぽいなら、中身をさらに解釈して positive/negative を取り出す
    if (-not [string]::IsNullOrEmpty($payload) -and $payload.TrimStart().StartsWith("{")) {
        try {
            $inner = $payload | ConvertFrom-Json
            $positive = $inner.positive
            $negative = $inner.negative
            $prompt = $inner.prompt
            if (-not [string]::IsNullOrEmpty($positive) -or -not [string]::IsNullOrEmpty($negative)) {
                return @{ positive = [string]$positive; negative = [string]$negative }
            }
            if (-not [string]::IsNullOrEmpty($prompt)) {
                return @{ positive = [string]$prompt; negative = $null }
            }
        } catch {
            # 失敗したら payload をそのまま使う
        }
    }

    # モデルが直接JSONを返しているケースを拾う
    $positive2 = $obj.positive
    $negative2 = $obj.negative
    if (-not [string]::IsNullOrEmpty([string]$positive2) -or -not [string]::IsNullOrEmpty([string]$negative2)) {
        return @{ positive = [string]$positive2; negative = [string]$negative2 }
    }

    # 最終フォールバック: payload / json を prompt として扱う
    if (-not [string]::IsNullOrEmpty($payload)) {
        return @{ positive = [string]$payload; negative = $null }
    }

    return @{ positive = [string]$json; negative = $null }
}

# ollama run を .NET Process で実行（PowerShellのNativeCommandError回避）
function Invoke-OllamaRun {
    param(
        [string]$ModelName,
        [string]$InputText,
        [int]$TimeoutSeconds = 180
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = "ollama"
    $psi.Arguments = "run $ModelName --format json --nowordwrap"
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $p = [System.Diagnostics.Process]::new()
    $p.StartInfo = $psi
    $null = $p.Start()

    $p.StandardInput.WriteLine($InputText)
    $p.StandardInput.WriteLine("/bye")
    $p.StandardInput.Close()

    $timeoutMs = [Math]::Max(1, $TimeoutSeconds) * 1000
    if (-not $p.WaitForExit($timeoutMs)) {
        try { $p.Kill($true) } catch {}
        throw "ollama run がタイムアウトしました（${TimeoutSeconds}s）"
    }

    $stdout = $p.StandardOutput.ReadToEnd()
    $stderr = $p.StandardError.ReadToEnd()
    return ($stdout + "`n" + $stderr)
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

# プロンプト生成のリクエストを作成（まずはPositiveのみを確実に生成）
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
    $rawText = Invoke-OllamaRun -ModelName $Model -InputText $CombinedPrompt -TimeoutSeconds $TimeoutSec

    $gen = Extract-Generation -RawText $rawText
    $positive = Normalize-PromptText -Text $gen.positive
    $negative = $null

    if ([string]::IsNullOrEmpty($positive)) {
        throw "プロンプトの抽出に失敗しました。出力: $rawText"
    }

    if ($WithNegative) {
        # まずは無難なデフォルト（高速・安定）
        $negative = "lowres, worst quality, low quality, blurry, jpeg artifacts, watermark, text, logo, bad anatomy, bad hands, extra fingers"

        # 任意でLLMにNegative生成を依頼（タイムアウトしたらデフォルトにフォールバック）
        if ($GenerateNegative) {
            try {
                Write-Host "Negative prompt を生成中..." -ForegroundColor Yellow
                $negSystem = 'Output ONLY valid JSON with one key "prompt" whose value is a comma-separated list of English negative prompt tags for Stable Diffusion. No other text.'
                $negCombined = @(
                    $negSystem,
                    "",
                    "Scene: $UserInput",
                    "",
                    "JSON:"
                ) -join "`n"

                $negRaw = Invoke-OllamaRun -ModelName $Model -InputText $negCombined -TimeoutSeconds $NegativeTimeoutSec
                $negGen = Extract-Generation -RawText $negRaw
                if (-not [string]::IsNullOrEmpty($negGen.positive)) {
                    $negative = Normalize-PromptText -Text $negGen.positive
                }
            } catch {
                Write-Host "※ Negative はLLMで生成せずデフォルトを使用しました" -ForegroundColor Yellow
            }
        }
    }

    # 結果を表示
    Write-Host "==========================================" -ForegroundColor Cyan
    if ($WithNegative) {
        Write-Host "生成されたプロンプト (Positive / Negative):" -ForegroundColor Cyan
    } else {
        Write-Host "生成されたプロンプト:" -ForegroundColor Cyan
    }
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    if ($WithNegative) {
        Write-Host "POSITIVE:" -ForegroundColor White
        Write-Host $positive -ForegroundColor White
        Write-Host ""
        Write-Host "NEGATIVE:" -ForegroundColor White
        Write-Host $negative -ForegroundColor White
    } else {
        Write-Host $positive -ForegroundColor White
    }
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""

    # クリップボードにコピー（失敗しても生成結果は保持）
    if ($Clipboard -ne "none") {
        try {
            if ($Clipboard -eq "both" -and $WithNegative) {
                ("POSITIVE:`n{0}`n`nNEGATIVE:`n{1}" -f $positive, $negative) | Set-Clipboard
            } else {
                $positive | Set-Clipboard
            }
            Write-Host "✓ クリップボードにコピーしました" -ForegroundColor Green
        } catch {
            Write-Host "※ クリップボードへのコピーに失敗しました（表示されたプロンプトは有効です）" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "エラー: プロンプト生成に失敗しました" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
