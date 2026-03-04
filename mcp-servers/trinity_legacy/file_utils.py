#!/usr/bin/env python3
"""
Trinity Reusable Module - File Utils
ファイル操作の共通ユーティリティ
"""

import os
import json
import shutil
from pathlib import Path
from typing import Optional, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def read_json(file_path: str, default: Any = None) -> Any:
    """
    JSONファイルを読み込む
    
    Args:
        file_path: ファイルパス
        default: デフォルト値
        
    Returns:
        JSONデータ、失敗時はdefault
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"⚠️ File not found: {file_path}")
        return default
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
        return default
    except Exception as e:
        logger.error(f"❌ Failed to read JSON: {e}")
        return default


def write_json(file_path: str, data: Any, indent: int = 2, ensure_dir: bool = True) -> bool:
    """
    JSONファイルに書き込む
    
    Args:
        file_path: ファイルパス
        data: 書き込むデータ
        indent: インデント幅
        ensure_dir: ディレクトリを自動作成するか
        
    Returns:
        成功したらTrue
    """
    try:
        if ensure_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        
        logger.info(f"✅ JSON written: {file_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to write JSON: {e}")
        return False


def read_text(file_path: str, default: str = "") -> str:
    """
    テキストファイルを読み込む
    
    Args:
        file_path: ファイルパス
        default: デフォルト値
        
    Returns:
        テキスト、失敗時はdefault
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"❌ Failed to read text: {e}")
        return default


def write_text(file_path: str, text: str, ensure_dir: bool = True) -> bool:
    """
    テキストファイルに書き込む
    
    Args:
        file_path: ファイルパス
        text: 書き込むテキスト
        ensure_dir: ディレクトリを自動作成するか
        
    Returns:
        成功したらTrue
    """
    try:
        if ensure_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        logger.info(f"✅ Text written: {file_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to write text: {e}")
        return False


def append_text(file_path: str, text: str, newline: bool = True) -> bool:
    """
    テキストファイルに追記
    
    Args:
        file_path: ファイルパス
        text: 追記するテキスト
        newline: 改行を追加するか
        
    Returns:
        成功したらTrue
    """
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(text)
            if newline:
                f.write('\n')
        return True
    except Exception as e:
        logger.error(f"❌ Failed to append text: {e}")
        return False


def ensure_dir(dir_path: str) -> bool:
    """
    ディレクトリを確実に作成
    
    Args:
        dir_path: ディレクトリパス
        
    Returns:
        成功したらTrue
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create directory: {e}")
        return False


def file_exists(file_path: str) -> bool:
    """ファイルが存在するか確認"""
    return os.path.exists(file_path) and os.path.isfile(file_path)


def dir_exists(dir_path: str) -> bool:
    """ディレクトリが存在するか確認"""
    return os.path.exists(dir_path) and os.path.isdir(dir_path)


def list_files(dir_path: str, pattern: str = "*", recursive: bool = False) -> List[str]:
    """
    ディレクトリ内のファイル一覧取得
    
    Args:
        dir_path: ディレクトリパス
        pattern: パターン（例: "*.py"）
        recursive: 再帰的に検索するか
        
    Returns:
        ファイルパスのリスト
    """
    try:
        path = Path(dir_path)
        if recursive:
            return [str(p) for p in path.rglob(pattern) if p.is_file()]
        else:
            return [str(p) for p in path.glob(pattern) if p.is_file()]
    except Exception as e:
        logger.error(f"❌ Failed to list files: {e}")
        return []


def copy_file(src: str, dst: str, ensure_dir: bool = True) -> bool:
    """
    ファイルをコピー
    
    Args:
        src: コピー元
        dst: コピー先
        ensure_dir: ディレクトリを自動作成するか
        
    Returns:
        成功したらTrue
    """
    try:
        if ensure_dir:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        shutil.copy2(src, dst)
        logger.info(f"✅ File copied: {src} → {dst}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to copy file: {e}")
        return False


def move_file(src: str, dst: str, ensure_dir: bool = True) -> bool:
    """
    ファイルを移動
    
    Args:
        src: 移動元
        dst: 移動先
        ensure_dir: ディレクトリを自動作成するか
        
    Returns:
        成功したらTrue
    """
    try:
        if ensure_dir:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        shutil.move(src, dst)
        logger.info(f"✅ File moved: {src} → {dst}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to move file: {e}")
        return False


def delete_file(file_path: str) -> bool:
    """
    ファイルを削除
    
    Args:
        file_path: ファイルパス
        
    Returns:
        成功したらTrue
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"✅ File deleted: {file_path}")
            return True
        else:
            logger.warning(f"⚠️ File not found: {file_path}")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to delete file: {e}")
        return False


def get_file_size(file_path: str) -> int:
    """ファイルサイズ取得（バイト）"""
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"❌ Failed to get file size: {e}")
        return 0


def get_file_modified_time(file_path: str) -> Optional[datetime]:
    """ファイル更新日時取得"""
    try:
        timestamp = os.path.getmtime(file_path)
        return datetime.fromtimestamp(timestamp)
    except Exception as e:
        logger.error(f"❌ Failed to get file modified time: {e}")
        return None


def backup_file(file_path: str, backup_dir: str = "/root/backups") -> Optional[str]:
    """
    ファイルをバックアップ
    
    Args:
        file_path: ファイルパス
        backup_dir: バックアップディレクトリ
        
    Returns:
        バックアップファイルパス、失敗時はNone
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return None
        
        # バックアップファイル名（タイムスタンプ付き）
        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{filename}.{timestamp}.bak"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # バックアップ
        if copy_file(file_path, backup_path):
            return backup_path
        else:
            return None
    except Exception as e:
        logger.error(f"❌ Failed to backup file: {e}")
        return None


if __name__ == "__main__":
    # テスト
    logging.basicConfig(level=logging.INFO)
    
    # JSON読み書き
    test_data = {"name": "Trinity", "version": "1.0"}
    write_json("/tmp/test.json", test_data)
    loaded_data = read_json("/tmp/test.json")
    print(f"✅ JSON test: {loaded_data}")
    
    # テキスト読み書き
    write_text("/tmp/test.txt", "Hello, Trinity!")
    loaded_text = read_text("/tmp/test.txt")
    print(f"✅ Text test: {loaded_text}")
    
    # ファイル一覧
    files = list_files("/root/trinity_legacy/reusable", "*.py")
    print(f"✅ List files: {len(files)} files found")
    
    print("✅ All tests passed")



