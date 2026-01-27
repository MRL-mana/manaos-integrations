# Force cleanup logs directory
# Run this script with administrator privileges

$ErrorActionPreference = "Continue"

$source = "C:\Users\mana4\Desktop\manaos_integrations\logs"
$dest = "D:\manaos_integrations\logs"

Write-Host "========================================"
Write-Host "Force Cleanup Logs Directory"
Write-Host "========================================"
Write-Host ""

if (-not (Test-Path $source)) {
    Write-Host "[INFO] Source does not exist: $source"
    Write-Host "Press Enter to exit..."
    Read-Host
    exit 0
}

# Check if already symbolic link
try {
    $item = Get-Item $source -Force -ErrorAction Stop
    if ($item.LinkType -eq "SymbolicLink") {
        Write-Host "[OK] Already a symbolic link"
        Write-Host "Press Enter to exit..."
        Read-Host
        exit 0
    }
} catch {
    # Continue
}

$size = (Get-ChildItem $source -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
Write-Host "Size: $([math]::Round($size/1MB, 2)) MB"
Write-Host ""

# Try to close file handles
Write-Host "Attempting to close file handles..."
try {
    # Get all files
    $files = Get-ChildItem $source -Recurse -File -ErrorAction SilentlyContinue

    foreach ($file in $files) {
        try {
            # Try to unlock the file
            $fileStream = [System.IO.File]::Open($file.FullName, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::Delete)
            $fileStream.Close()
            $fileStream.Dispose()
        } catch {
            Write-Host "  Warning: Could not unlock $($file.Name)"
        }
    }
} catch {
    Write-Host "  Warning: Could not process files"
}

Write-Host ""
Write-Host "Deleting files individually..."
$deletedCount = 0
$failedCount = 0

# Delete files one by one
$files = Get-ChildItem $source -Recurse -File -ErrorAction SilentlyContinue
foreach ($file in $files) {
    try {
        # Change attributes
        $file.Attributes = "Normal"

        # Try to delete
        Remove-Item $file.FullName -Force -ErrorAction Stop
        $deletedCount++
    } catch {
        Write-Host "  Failed to delete: $($file.Name)"
        $failedCount++
    }
}

Write-Host "Deleted: $deletedCount files"
if ($failedCount -gt 0) {
    Write-Host "Failed: $failedCount files"
}

Write-Host ""
Write-Host "Deleting directories..."
try {
    # Delete empty directories
    Get-ChildItem $source -Recurse -Directory -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object {
        try {
            Remove-Item $_.FullName -Force -ErrorAction Stop
        } catch {
            # Ignore
        }
    }

    # Delete main directory
    Remove-Item $source -Recurse -Force -ErrorAction Stop
    Write-Host "[OK] Directory deleted"

    # Create symbolic link
    Write-Host "Creating symbolic link..."
    New-Item -ItemType SymbolicLink -Path $source -Target $dest -Force | Out-Null
    Write-Host "[OK] Symbolic link created"
    Write-Host ""
    Write-Host "Freed space: $([math]::Round($size/1MB, 2)) MB"
} catch {
    Write-Host "[ERROR] Could not delete directory: $_"
    Write-Host ""
    Write-Host "Some files may still be in use."
    Write-Host "Please close applications and try again, or delete manually."
}

Write-Host ""
Write-Host "========================================"
Write-Host "Complete"
Write-Host "========================================"
Write-Host ""
Write-Host "Press Enter to exit..."
Read-Host
