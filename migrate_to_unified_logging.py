#!/usr/bin/env python3
"""
統一ログシステムへの移行スクリプト
すべてのサービスを unified_logging.py に移行
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# 対象ディレクトリ
MANAOS_DIR = Path(__file__).parent
EXCLUDED_DIRS = {
    "tests", "konoha_mcp_servers", "castle_ex", "scripts", "__pycache__",
    ".venv", "venv", "node_modules", "migrations", ".git"
}
EXCLUDED_FILES = {
    "migrate_to_unified_logging.py", "unified_logging.py", "manaos_logger.py",
    "apply_unified_modules.py", "check_logger_usage.py"
}


def find_py_files_with_manaos_logger() -> List[Path]:
    """manaos_logger を使用しているPythonファイルを検出"""
    files = []
    
    for py_file in MANAOS_DIR.rglob("*.py"):
        # 除外対象をスキップ
        if any(excluded in py_file.parts for excluded in EXCLUDED_DIRS):
            continue
        if py_file.name in EXCLUDED_FILES:
            continue
        
        try:
            content = py_file.read_text(encoding="utf-8")
            if "from manaos_logger import" in content or "from manaos_logger import get_logger" in content:
                files.append(py_file)
        except Exception as e:
            print(f"⚠️  {py_file}: {e}")
    
    return files


def get_logger_name(file_path: Path) -> str:
    """ファイルに適切なロガー名を決定"""
    stem = file_path.stem
    
    # APIサーバー
    if "api" in stem.lower() and "server" in stem.lower():
        return f'"{stem.replace("_api_server", "").replace("_", "-")}"'
    
    # MCPサーバー
    if "mcp" in stem.lower() or "server" in stem.lower():
        return f'"{stem.replace("_server", "").replace("_mcp", "").replace("_", "-")}"'
    
    # その他のモジュール
    return f'"{stem.replace("_", "-")}"'


def migrate_file(file_path: Path) -> Tuple[bool, str]:
    """ファイルを統一ログに移行"""
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content
        
        # パターン1: try-except でインポートしている場合
        pattern1 = r"try:\s+from manaos_logger import get_logger.*?(?=\n\w)"
        if re.search(pattern1, content, re.DOTALL):
            logger_name = get_logger_name(file_path)
            
            # try-except ブロック全体を置き換え
            new_code = f'''try:
    from unified_logging import get_service_logger
    logger = get_service_logger({logger_name})
except ImportError:
    try:
        from manaos_logger import get_logger
        logger = get_logger(__name__)
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)'''
            
            content = re.sub(
                r"try:\s+from manaos_logger import get_logger.*?except ImportError:.*?logging\.basicConfig\(level=logging\.INFO\)",
                new_code,
                content,
                flags=re.DOTALL
            )
        
        # パターン2: シンプルなインポート
        if "from manaos_logger import get_logger" in content:
            logger_name = get_logger_name(file_path)
            
            content = re.sub(
                r"from manaos_logger import get_logger\s*\n\s*logger = get_logger\(__name__\)",
                f'from unified_logging import get_service_logger\nlogger = get_service_logger({logger_name})',
                content
            )
        
        # パターン3: logger == get_logger(__name__)
        if "logger = get_logger(__name__)" in content:
            if "from unified_logging" not in content:
                logger_name = get_logger_name(file_path)
                content = re.sub(
                    r"logger = get_logger\(__name__\)",
                    f'logger = get_service_logger({logger_name})',
                    content
                )
        
        # 変更があった場合のみファイルに書き込み
        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return True, "✅ 移行成功"
        else:
            return False, "⏭️  既に移行済みまたは変更なし"
    
    except Exception as e:
        return False, f"❌ エラー: {str(e)[:100]}"


def main():
    """メイン処理"""
    print("=" * 70)
    print("🔄 統一ログシステム移行スクリプト")
    print("=" * 70)
    
    files = find_py_files_with_manaos_logger()
    print(f"\n📊 対象ファイル数: {len(files)}\n")
    
    success_count = 0
    failed_count = 0
    skip_count = 0
    
    for idx, file_path in enumerate(files, 1):
        relative_path = file_path.relative_to(MANAOS_DIR)
        success, message = migrate_file(file_path)
        
        if success:
            print(f"{idx:3d}. ✅ {relative_path}")
            success_count += 1
        elif "既に移行済み" in message:
            print(f"{idx:3d}. ⏭️  {relative_path}")
            skip_count += 1
        else:
            print(f"{idx:3d}. ❌ {relative_path} - {message}")
            failed_count += 1
    
    print("\n" + "=" * 70)
    print("📈 移行結果")
    print("=" * 70)
    print(f"✅ 移行成功: {success_count}")
    print(f"⏭️  スキップ: {skip_count}")
    print(f"❌ 失敗:   {failed_count}")
    print(f"📊 合計:   {len(files)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
