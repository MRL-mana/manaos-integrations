#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サブプロセスヘルパー
すべてのコマンド実行をバックグラウンドで静かに実行するためのユーティリティ
"""
import subprocess
import platform
import sys
from typing import Union, List, Optional, Dict, Any


def get_creation_flags() -> int:
    """
    プラットフォームに応じた適切なcreationフラグを返す
    
    Returns:
        WindowsならCREATE_NO_WINDOW、それ以外は0
    """
    if platform.system() == "Windows":
        # ウィンドウを表示しない
        return subprocess.CREATE_NO_WINDOW
    return 0


def run_silent(
    cmd: Union[str, List[str]],
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    **kwargs
) -> subprocess.CompletedProcess:
    """
    コマンドをバックグラウンドで静かに実行（ウィンドウなし）
    
    Args:
        cmd: 実行するコマンド（文字列またはリスト）
        capture_output: 出力をキャプチャするか
        text: テキストモードで実行するか
        check: 失敗時に例外を発生させるか
        timeout: タイムアウト（秒）
        env: 環境変数
        cwd: 作業ディレクトリ
        **kwargs: その他のsubprocess.run引数
    
    Returns:
        subprocess.CompletedProcessオブジェクト
    """
    # creationflagsがない場合のみ追加
    if "creationflags" not in kwargs:
        kwargs["creationflags"] = get_creation_flags()
    
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=text,
        check=check,
        timeout=timeout,
        env=env,
        cwd=cwd,
        **kwargs
    )


def popen_silent(
    cmd: Union[str, List[str]],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text: bool = True,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    **kwargs
) -> subprocess.Popen:
    """
    バックグラウンドプロセスを静かに起動（ウィンドウなし）
    
    Args:
        cmd: 実行するコマンド
        stdout: 標準出力のリダイレクト先
        stderr: 標準エラー出力のリダイレクト先
        text: テキストモードで実行するか
        env: 環境変数
        cwd: 作業ディレクトリ
        **kwargs: その他のsubprocess.Popen引数
    
    Returns:
        subprocess.Popenオブジェクト
    """
    # creationflagsがない場合のみ追加
    if "creationflags" not in kwargs:
        kwargs["creationflags"] = get_creation_flags()
    
    return subprocess.Popen(
        cmd,
        stdout=stdout,
        stderr=stderr,
        text=text,
        env=env,
        cwd=cwd,
        **kwargs
    )


# 互換性のためのエイリアス
silent_run = run_silent
silent_popen = popen_silent


if __name__ == "__main__":
    # テスト
    print("🧪 サブプロセスヘルパーのテスト")
    print(f"プラットフォーム: {platform.system()}")
    print(f"Creation flags: {get_creation_flags()}")
    
    # テスト実行（Windowsの場合はウィンドウが開かない）
    if platform.system() == "Windows":
        result = run_silent(["cmd", "/c", "echo", "Hello from silent subprocess!"])
    else:
        result = run_silent(["echo", "Hello from silent subprocess!"])
    
    print(f"✅ 実行成功")
    print(f"出力: {result.stdout.strip()}")
