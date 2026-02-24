#Requires -Version 5.1

<#
.SYNOPSIS
ComfyUI Qwen-Image-2512 ワークフロー環境検証スクリプト

.DESCRIPTION
セットアップガイドで説明されたすべての前提条件をチェック

.EXAMPLE
.\validate_qwen_setup.ps1
#>

Write-Host "=" * 70
Write-Host "COMFYUI QWEN-IMAGE-2512 WORKFLOW VALIDATION"
Write-Host "=" * 70
Write-Host "Environment check timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"

$checks = [ordered]@{}

# 1. ComfyUI サーバーチェック
Write-Host "1️⃣  ComfyUI Server..."
try {
    $response = Invoke-RestMethod "http://localhost:8188/api/" -TimeoutSec 3
    $checks['ComfyUI Server'] = @{
        status = "✓ PASS"
        details = "Running on http://localhost:8188"
    }
    Write-Host "   ✓ http://localhost:8188 - OK"
}
catch {
    $checks['ComfyUI Server'] = @{
        status = "✗ FAIL"
        details = "Not reachable - Start ComfyUI or check port 8188"
    }
    Write-Host "   ✗ http://localhost:8188 - DOWN"
}

# 2. LM Studio サーバーチェック
Write-Host "2️⃣  LM Studio Server..."
try {
    $response = Invoke-RestMethod "http://localhost:1234/v1/models" -TimeoutSec 3
    $checks['LM Studio Server'] = @{
        status = "✓ PASS"
        details = "Running on http://localhost:1234"
    }
    Write-Host "   ✓ http://localhost:1234 - OK"
}
catch {
    $checks['LM Studio Server'] = @{
        status = "✗ FAIL"
        details = "Not reachable - Start LM Studio or check port 1234"
    }
    Write-Host "   ✗ http://localhost:1234 - DOWN"
}

# 3. ワークフロー JSON ファイルチェック
Write-Host "3️⃣  Workflow JSON Files..."
$workflows = @(
    "05_wAnima_preview-Random.json",
    "05_wQween-2512-Real-Random2.json",
    "07_Qwen-2512-real-random.json",
    "FLUX1_real2.json",
    "Qwen-image_2512.json"
)

$workflow_dir = Join-Path $PSScriptRoot "comfyui_workflows"
$all_present = $true
foreach ($wf in $workflows) {
    $path = Join-Path $workflow_dir $wf
    if (Test-Path $path) {
        $size = (Get-Item $path).Length / 1KB
        Write-Host "   ✓ $wf ($([math]::Round($size))KB)"
    }
    else {
        Write-Host "   ✗ $wf - MISSING"
        $all_present = $false
    }
}

$checks['Workflow JSON Files'] = @{
    status = if($all_present) { "✓ PASS" } else { "✗ FAIL" }
    details = "Found $($workflows.Where({ Test-Path (Join-Path $workflow_dir $_) }).Count)/$($workflows.Count) files"
}

# 4. ComfyUI カスタムノード確認
Write-Host "4️⃣  ComfyUI Custom Nodes (optional)..."
$custom_nodes_path = "D:\ComfyUI\custom_nodes"  # 実際のパスに調整
if (Test-Path $custom_nodes_path) {
    $has_was = Test-Path "$custom_nodes_path\ComfyUI_Wassname_nodes"
    $has_lm = Test-Path "$custom_nodes_path\LM-Studio-Nodes-ComfyUI"
    
    Write-Host "   $(if($has_was) {'✓'} else {'⚠'}) Was Node Suite (Load Image Batch)"
    Write-Host "   $(if($has_lm) {'✓'} else {'⚠'}) LM Studio Nodes"
    
    $checks['ComfyUI Custom Nodes'] = @{
        status = if($has_was -and $has_lm) { "✓ PASS" } else { "⚠ PARTIAL" }
        details = "Was: $has_was, LM Studio: $has_lm"
    }
}
else {
    Write-Host "   ⚠ ComfyUI custom_nodes path not found"
    $checks['ComfyUI Custom Nodes'] = @{
        status = "⚠ SKIP"
        details = "Could not locate ComfyUI directory"
    }
}

# 5. Python コンパイルチェック（検証スクリプト）
Write-Host "5️⃣  Setup Guidelines & Scripts..."
$setup_guide = Join-Path $PSScriptRoot "WORKFLOW_SETUP_GUIDE.md"
$validate_py = Join-Path $PSScriptRoot "validate_workflows.py"
if ((Test-Path $setup_guide) -and (Test-Path $validate_py)) {
    Write-Host "   ✓ WORKFLOW_SETUP_GUIDE.md"
    Write-Host "   ✓ validate_workflows.py"
    $checks['Documentation'] = @{
        status = "✓ PASS"
        details = "Setup guide and validation scripts present"
    }
}

# 6. GPU チェック
Write-Host "6️⃣  GPU Status..."
try {
    $gpu_info = nvidia-smi --query-gpu=name,memory.total,utilization.gpu --format=csv,noheader 2>$null
    if ($gpu_info) {
        Write-Host "   ✓ NVIDIA GPU detected"
        Write-Host "      $gpu_info"
        $checks['GPU'] = @{
            status = "✓ PASS"
            details = "NVIDIA GPU ready"
        }
    }
    else {
        Write-Host "   ✗ No GPU detected (CPU mode only)"
        $checks['GPU'] = @{
            status = "⚠ CPU MODE"
            details = "No NVIDIA GPU - processing will be slower"
        }
    }
}
catch {
    Write-Host "   ⚠ nvidia-smi not found"
    $checks['GPU'] = @{
        status = "⚠ CHECK"
        details = "NVIDIA drivers may not be installed"
    }
}

# サマリー表示
Write-Host "`n" + ("=" * 70)
Write-Host "SUMMARY"
Write-Host "=" * 70

$pass_count = 0
$fail_count = 0
$partial_count = 0

foreach ($check in $checks.GetEnumerator()) {
    $status = $check.Value.status
    $col = if ($status -like "*PASS*") { "Green" } 
           elseif ($status -like "*FAIL*") { "Red" }
           else { "Yellow" }
    
    Write-Host "$($check.Key): " -NoNewline -ForegroundColor $col
    Write-Host $status
    Write-Host "         $($check.Value.details)" -ForegroundColor Gray
    
    if ($status -like "*PASS*") { $pass_count++ }
    elseif ($status -like "*FAIL*") { $fail_count++ }
    else { $partial_count++ }
}

Write-Host "`n" + ("=" * 70)
$col = if ($fail_count -eq 0) { "Green" } else { "Red" }
Write-Host "RESULT: $pass_count PASS | $fail_count FAIL | $partial_count PARTIAL" -ForegroundColor $col
Write-Host "=" * 70

if ($fail_count -gt 0) {
    Write-Host "`n⚠️  REQUIRED FIXES:"
    foreach ($check in $checks.GetEnumerator()) {
        if ($check.Value.status -like "*FAIL*") {
            Write-Host "  • $($check.Key): $($check.Value.details)"
        }
    }
}

if ($partial_count -gt 0) {
    Write-Host "`n🔔 OPTIONAL IMPROVEMENTS:"
    foreach ($check in $checks.GetEnumerator()) {
        if ($check.Value.status -like "*PARTIAL*" -or $check.Value.status -like "*CPU*") {
            Write-Host "  • $($check.Key): $($check.Value.details)"
        }
    }
}

Write-Host "`n✅ Setup guide: WORKFLOW_SETUP_GUIDE.md"
Write-Host "📖 More info: Read WORKFLOW_SETUP_GUIDE.md for detailed configuration"
