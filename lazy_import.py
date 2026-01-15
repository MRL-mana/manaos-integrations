#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ ManaOS遅延インポートシステム
モジュールの遅延読み込みで起動時間を短縮
"""

import sys
import importlib
from typing import Any, Optional, Dict
from functools import wraps

# 遅延インポートのキャッシュ
_lazy_cache: Dict[str, Any] = {}


class LazyImport:
    """遅延インポートクラス"""
    
    def __init__(self, module_name: str, package: Optional[str] = None):
        """
        初期化
        
        Args:
            module_name: モジュール名
            package: パッケージ名（相対インポート用）
        """
        self.module_name = module_name
        self.package = package
        self._module: Optional[Any] = None
    
    def __getattr__(self, name: str) -> Any:
        """属性アクセス時にモジュールをインポート"""
        if self._module is None:
            try:
                if self.package:
                    self._module = importlib.import_module(
                        f".{self.module_name}",
                        package=self.package
                    )
                else:
                    self._module = importlib.import_module(self.module_name)
            except ImportError as e:
                raise ImportError(
                    f"モジュール '{self.module_name}' のインポートに失敗しました: {e}"
                )
        
        return getattr(self._module, name)
    
    def __call__(self, *args, **kwargs):
        """呼び出し可能な場合の処理"""
        if self._module is None:
            self.__getattr__("__call__")
        return self._module(*args, **kwargs)


def lazy_import(module_name: str, package: Optional[str] = None):
    """
    遅延インポートデコレータ
    
    Args:
        module_name: モジュール名
        package: パッケージ名
    
    Returns:
        遅延インポートオブジェクト
    """
    cache_key = f"{package}.{module_name}" if package else module_name
    
    if cache_key not in _lazy_cache:
        _lazy_cache[cache_key] = LazyImport(module_name, package)
    
    return _lazy_cache[cache_key]


def lazy_function(module_name: str, function_name: str, package: Optional[str] = None):
    """
    関数の遅延インポート
    
    Args:
        module_name: モジュール名
        function_name: 関数名
        package: パッケージ名
    
    Returns:
        遅延インポートされた関数
    """
    @wraps(function_name)
    def wrapper(*args, **kwargs):
        module = lazy_import(module_name, package)
        func = getattr(module, function_name)
        return func(*args, **kwargs)
    
    return wrapper


# よく使うモジュールの遅延インポート定義
def get_lazy_imports() -> Dict[str, LazyImport]:
    """よく使うモジュールの遅延インポート定義を取得"""
    return {
        "flask": lazy_import("flask"),
        "flask_cors": lazy_import("flask_cors"),
        "httpx": lazy_import("httpx"),
        "requests": lazy_import("requests"),
        "sqlite3": lazy_import("sqlite3"),
        "redis": lazy_import("redis"),
        "psutil": lazy_import("psutil"),
        "numpy": lazy_import("numpy"),
        "pandas": lazy_import("pandas"),
    }


def main():
    """テスト用メイン関数"""
    print("ManaOS遅延インポートシステムテスト")
    print("=" * 60)
    
    # 遅延インポートのテスト
    json_module = lazy_import("json")
    print(f"jsonモジュール: {json_module}")
    
    # 実際に使用するまでインポートされない
    data = json_module.dumps({"test": "value"})
    print(f"JSON出力: {data}")


if __name__ == "__main__":
    main()






















