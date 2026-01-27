# 管理者権限でシンボリックリンクを作成するスクリプト
# 管理者権限でPowerShellを開いて実行してください

$ErrorActionPreference = "Stop"

# シンボリックリンクのマッピング
$symlinks = @(
    @{
        Source = "C:\Users\mana4\Desktop\manaos_integrations\organized_images"
        Target = "D:\manaos_integrations\organized_images"
    },
    @{
        Source = "C:\Users\mana4\Desktop\manaos_integrations\gallery_images"
        Target = "D:\manaos_integrations\gallery_images"
    },
    @{
        Source = "C:\Users\mana4\Desktop\manaos_integrations\generated_images"
        Target = "D:\manaos_integrations\generated_images"
    },
    @{
        Source = "C:\Users\mana4\Desktop\manaos_integrations\data"
        Target = "D:\manaos_integrations\data"
    },
    @{
        Source = "C:\Users\mana4\Desktop\manaos_integrations\snapshots"
        Target = "D:\manaos_integrations\snapshots"
    },
    @{
        Source = "C:\Users\mana4\Desktop\manaos_integrations\logs"
        Target = "D:\manaos_integrations\logs"
    },
    @{
        Source = "C:\Users\mana4\Desktop\manaos_integrations\comfyui"
        Target = "D:\manaos_integrations\comfyui"
    }
)

Write-Host "========================================"
Write-Host "シンボリックリンク作成スクリプト"
Write-Host "========================================"
Write-Host ""

$successCount = 0
$skipCount = 0
$errorCount = 0

foreach ($link in $symlinks) {
    $source = $link.Source
    $target = $link.Target

    Write-Host "[$source]"

    # ソースが既に存在する場合はスキップ
    if (Test-Path $source) {
        if ((Get-Item $source).LinkType -eq "SymbolicLink") {
            Write-Host "  既にシンボリックリンクが存在します - スキップ"
            $skipCount++
            Write-Host ""
            continue
        } else {
            Write-Host "  警告: ソースが既に存在します（シンボリックリンクではありません）"
            Write-Host "  手動で確認してください"
            $skipCount++
            Write-Host ""
            continue
        }
    }

    # ターゲットが存在するか確認
    if (-not (Test-Path $target)) {
        Write-Host "  エラー: ターゲットが存在しません: $target"
        $errorCount++
        Write-Host ""
        continue
    }

    try {
        # シンボリックリンクを作成
        New-Item -ItemType SymbolicLink -Path $source -Target $target -Force | Out-Null
        Write-Host "  [OK] シンボリックリンク作成成功"
        Write-Host "  $source -> $target"
        $successCount++
    } catch {
        Write-Host "  [ERROR] シンボリックリンク作成失敗: $_"
        $errorCount++
    }

    Write-Host ""
}

Write-Host "========================================"
Write-Host "完了"
Write-Host "========================================"
Write-Host "成功: $successCount"
Write-Host "スキップ: $skipCount"
Write-Host "エラー: $errorCount"
Write-Host ""
