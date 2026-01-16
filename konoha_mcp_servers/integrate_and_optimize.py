"""
MCPサーバーの統合・最適化スクリプト
"""
import os
import shutil
from pathlib import Path
import json

def create_unified_structure():
    """統合されたディレクトリ構造を作成"""
    base_dir = Path("konoha_mcp_servers")
    unified_dir = base_dir / "unified"
    
    # 統合ディレクトリを作成
    categories = {
        "n8n": unified_dir / "n8n",
        "chatgpt": unified_dir / "chatgpt",
        "manaos": unified_dir / "manaos",
        "x280": unified_dir / "x280",
        "stitch": unified_dir / "stitch",
        "image": unified_dir / "image",
        "office": unified_dir / "office",
        "gateway": unified_dir / "gateway",
        "proxy": unified_dir / "proxy",
        "other": unified_dir / "other"
    }
    
    for cat_dir in categories.values():
        cat_dir.mkdir(parents=True, exist_ok=True)
    
    return categories

def organize_duplicates():
    """重複ファイルを整理"""
    base_dir = Path("konoha_mcp_servers")
    unified_dir = base_dir / "unified"
    
    # 重複ファイルのリスト
    duplicates = {
        "manaos_mcp_server.py": [
            "archive_20251106/manaos_mcp_server.py",
            "manaos-knowledge_mcp/manaos_mcp_server.py"
        ],
        "stitch_mcp_server.py": [
            "archive_20251106/stitch_mcp_server.py",
            "scripts_additional/stitch_mcp_server.py"
        ],
        "image_editor_mcp_server.py": [
            "archive_20251106/image_editor_mcp_server.py",
            "manaos-knowledge_mcp/image_editor_mcp_server.py"
        ],
        "alita_mct_mcp_server.py": [
            "archive_20251106/alita_mct_mcp_server.py",
            "manaos-knowledge_mcp/alita_mct_mcp_server.py"
        ],
        "reflection_mcp_server.py": [
            "archive_20251106/reflection_mcp_server.py",
            "manaos-knowledge_mcp/reflection_mcp_server.py"
        ],
        "mcp_server_gateway.py": [
            "archive_20251106/mcp_server_gateway.py",
            "manaos-knowledge/mcp_server_gateway.py"
        ]
    }
    
    # 最新版を選択（ファイルサイズが大きい方を優先）
    best_versions = {}
    
    for filename, paths in duplicates.items():
        best_path = None
        best_size = 0
        
        for rel_path in paths:
            full_path = base_dir / rel_path
            if full_path.exists():
                size = full_path.stat().st_size
                if size > best_size:
                    best_size = size
                    best_path = full_path
        
        if best_path:
            best_versions[filename] = best_path
    
    return best_versions

def create_requirements_txt():
    """統合されたrequirements.txtを作成"""
    base_dir = Path("konoha_mcp_servers")
    requirements = set()
    
    # 既存のrequirementsファイルを読み込む
    for req_file in base_dir.rglob("*requirements*.txt"):
        with open(req_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    requirements.add(line)
    
    # 共通の依存関係を追加
    common_deps = [
        "mcp>=0.9.0",
        "requests>=2.31.0",
        "httpx>=0.24.0",
        "pydantic>=2.0.0"
    ]
    
    requirements.update(common_deps)
    
    # requirements.txtを書き込み
    unified_dir = base_dir / "unified"
    unified_dir.mkdir(exist_ok=True)
    
    with open(unified_dir / "requirements.txt", 'w', encoding='utf-8') as f:
        for req in sorted(requirements):
            f.write(f"{req}\n")
    
    print(f"[OK] requirements.txtを作成しました: {unified_dir / 'requirements.txt'}")

def create_startup_script():
    """起動スクリプトを作成"""
    base_dir = Path("konoha_mcp_servers")
    unified_dir = base_dir / "unified"
    
    startup_script = unified_dir / "start_mcp_servers.ps1"
    
    script_content = """# MCPサーバー起動スクリプト

Write-Host "=== MCPサーバー起動 ===" -ForegroundColor Cyan
Write-Host ""

$baseDir = Split-Path -Parent $PSScriptRoot
$unifiedDir = Join-Path $baseDir "unified"

# 環境変数の設定
$env:PYTHONPATH = "$baseDir;$env:PYTHONPATH"

# 利用可能なMCPサーバーをリスト
Write-Host "利用可能なMCPサーバー:" -ForegroundColor Yellow
Get-ChildItem $unifiedDir -Recurse -Filter "*mcp*.py" | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "使用方法:" -ForegroundColor Yellow
Write-Host "  python -m <module_name>" -ForegroundColor Gray
Write-Host ""
Write-Host "例:" -ForegroundColor Yellow
Write-Host "  python unified/n8n/n8n_mcp_server.py" -ForegroundColor Gray
"""
    
    with open(startup_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"[OK] 起動スクリプトを作成しました: {startup_script}")

def main():
    """メイン処理"""
    print("=== MCPサーバー統合・最適化 ===")
    print("")
    
    # 1. 統合ディレクトリ構造を作成
    print("[1] 統合ディレクトリ構造を作成中...")
    categories = create_unified_structure()
    print("[OK] 完了")
    print("")
    
    # 2. 重複ファイルを整理
    print("[2] 重複ファイルを整理中...")
    best_versions = organize_duplicates()
    print(f"[OK] 最適版を選択: {len(best_versions)}個")
    print("")
    
    # 3. requirements.txtを作成
    print("[3] requirements.txtを作成中...")
    create_requirements_txt()
    print("")
    
    # 4. 起動スクリプトを作成
    print("[4] 起動スクリプトを作成中...")
    create_startup_script()
    print("")
    
    print("[OK] 統合・最適化完了！")
    print("")
    print("次のステップ:")
    print("  1. pip install -r konoha_mcp_servers/unified/requirements.txt")
    print("  2. python konoha_mcp_servers/unified/start_mcp_servers.ps1")

if __name__ == "__main__":
    main()

