# ComfyUI-LTXVideo で LTXVSeparateAVLatent が存在したコミットを検索する
# 使い方:
#   .\find_ltxv_node_commit.ps1
#   .\find_ltxv_node_commit.ps1 -LtxVideoPath "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo"
param(
    [string]$LtxVideoPath = "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo"
)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if (-not (Test-Path $LtxVideoPath)) {
    Write-Host "ComfyUI-LTXVideo のパスが見つかりません: $LtxVideoPath" -ForegroundColor Red
    Write-Host "  -LtxVideoPath で正しいパスを指定してください。" -ForegroundColor Yellow
    exit 1
}

$repo = Resolve-Path $LtxVideoPath
Write-Host "=== ComfyUI-LTXVideo で LTXVSeparateAVLatent を検索 ===" -ForegroundColor Cyan
Write-Host "リポジトリ: $repo"
Write-Host ""

Push-Location $repo
try {
    # 文字列 LTXVSeparateAVLatent が含まれるコミットを検索（追加 or 削除）
    $out = git log -S "LTXVSeparateAVLatent" --oneline -- "*.py" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "git log でエラー: $out" -ForegroundColor Red
        exit 1
    }
    if (-not $out) {
        Write-Host "LTXVSeparateAVLatent を含むコミットは見つかりませんでした。" -ForegroundColor Yellow
        Write-Host "  - 別のノード名で検索する: git log -S \"LTXVConcatAVLatent\" --oneline -- \"*.py\"" -ForegroundColor Gray
        exit 0
    }
    Write-Host "該当コミット（先頭が最新）:" -ForegroundColor Green
    $out | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    Write-Host "特定のコミットに合わせる例:" -ForegroundColor Yellow
    $first = ($out -split "`n")[0]
    $hash = ($first -split " ")[0]
    Write-Host "  cd $repo"
    Write-Host "  git checkout $hash"
    Write-Host ""
    Write-Host "master に戻す: git checkout master" -ForegroundColor Gray
} finally {
    Pop-Location
}
