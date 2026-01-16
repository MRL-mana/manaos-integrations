# MCPサーバー分析・整理スクリプト

Write-Host "=== MCPサーバー分析・整理 ===" -ForegroundColor Cyan
Write-Host ""

$baseDir = "konoha_mcp_servers"
$reportFile = "konoha_mcp_servers/ANALYSIS_REPORT.md"

# 1. 重複ファイルの検出
Write-Host "[1] 重複ファイルを検出中..." -ForegroundColor Yellow
$duplicates = Get-ChildItem $baseDir -Recurse -File -Filter "*.py" | 
    Select-Object Name, DirectoryName | 
    Group-Object Name | 
    Where-Object {$_.Count -gt 1}

if ($duplicates) {
    Write-Host "  重複が見つかりました:" -ForegroundColor Yellow
    $duplicates | ForEach-Object {
        Write-Host "    - $($_.Name): $($_.Count)個" -ForegroundColor Gray
    }
} else {
    Write-Host "  重複は見つかりませんでした" -ForegroundColor Green
}

Write-Host ""

# 2. MCPサーバーの分類
Write-Host "[2] MCPサーバーを分類中..." -ForegroundColor Yellow

$categories = @{
    "n8n" = @()
    "chatgpt" = @()
    "manaos" = @()
    "x280" = @()
    "stitch" = @()
    "image" = @()
    "office" = @()
    "gateway" = @()
    "proxy" = @()
    "other" = @()
}

Get-ChildItem $baseDir -Recurse -File -Filter "*mcp*.py" | ForEach-Object {
    $name = $_.Name.ToLower()
    $path = $_.FullName
    
    if ($name -like "*n8n*") {
        $categories["n8n"] += $path
    } elseif ($name -like "*chatgpt*") {
        $categories["chatgpt"] += $path
    } elseif ($name -like "*manaos*") {
        $categories["manaos"] += $path
    } elseif ($name -like "*x280*") {
        $categories["x280"] += $path
    } elseif ($name -like "*stitch*") {
        $categories["stitch"] += $path
    } elseif ($name -like "*image*") {
        $categories["image"] += $path
    } elseif ($name -like "*office*" -or $name -like "*powerpoint*") {
        $categories["office"] += $path
    } elseif ($name -like "*gateway*") {
        $categories["gateway"] += $path
    } elseif ($name -like "*proxy*") {
        $categories["proxy"] += $path
    } else {
        $categories["other"] += $path
    }
}

Write-Host "  分類結果:" -ForegroundColor Green
$categories.GetEnumerator() | Where-Object {$_.Value.Count -gt 0} | ForEach-Object {
    Write-Host "    $($_.Key): $($_.Value.Count)個" -ForegroundColor Gray
}

Write-Host ""

# 3. 依存関係の確認
Write-Host "[3] 依存関係を確認中..." -ForegroundColor Yellow

$requirementsFiles = Get-ChildItem $baseDir -Recurse -Filter "*requirements*.txt"
if ($requirementsFiles) {
    Write-Host "  見つかったrequirementsファイル:" -ForegroundColor Green
    $requirementsFiles | ForEach-Object {
        Write-Host "    - $($_.FullName)" -ForegroundColor Gray
    }
} else {
    Write-Host "  requirementsファイルは見つかりませんでした" -ForegroundColor Yellow
}

Write-Host ""

# 4. レポート生成
Write-Host "[4] 分析レポートを生成中..." -ForegroundColor Yellow

$report = @"
# MCPサーバー分析レポート

**作成日**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## 📊 統計

- **Pythonファイル数**: $(Get-ChildItem $baseDir -Recurse -File -Filter "*.py" | Measure-Object | Select-Object -ExpandProperty Count)個
- **JavaScriptファイル数**: $(Get-ChildItem $baseDir -Recurse -File -Filter "*.js" | Measure-Object | Select-Object -ExpandProperty Count)個

## 🔍 分類結果

"@

$categories.GetEnumerator() | Where-Object {$_.Value.Count -gt 0} | ForEach-Object {
    $report += "`n### $($_.Key) ($($_.Value.Count)個)`n`n"
    $_.Value | ForEach-Object {
        $relativePath = $_.Replace((Get-Location).Path + "\", "")
        $report += "- $relativePath`n"
    }
}

$report += @"

## 🔄 重複ファイル

"@

if ($duplicates) {
    $duplicates | ForEach-Object {
        $report += "`n### $($_.Name)`n`n"
        $_.Group | ForEach-Object {
            $relativePath = $_.DirectoryName.Replace((Get-Location).Path + "\", "")
            $report += "- $relativePath\$($_.Name)`n"
        }
    }
} else {
    $report += "`n重複ファイルは見つかりませんでした。`n"
}

$report | Out-File -FilePath $reportFile -Encoding UTF8

Write-Host "  レポートを生成しました: $reportFile" -ForegroundColor Green
Write-Host ""
Write-Host "[OK] 分析完了！" -ForegroundColor Green

