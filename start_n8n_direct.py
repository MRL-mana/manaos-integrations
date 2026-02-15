#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""n8nを直接起動するスクリプト"""

import subprocess
import os
import sys
import time
import shutil

def start_n8n():
    """n8nを起動"""
    port = 5679
    
    # n8nコマンドの検索
    n8n_cmd = shutil.which('n8n')
    if not n8n_cmd:
        # npxを試す
        npx_cmd = shutil.which('npx')
        if npx_cmd:
            n8n_cmd = npx_cmd
            args = [npx_cmd, 'n8n', 'start', '--port', str(port)]
        else:
            print("[エラー] n8nコマンドが見つかりません")
            print("n8nをインストールしてください: npm install -g n8n")
            return False
    else:
        args = [n8n_cmd, 'start', '--port', str(port)]
    
    # データディレクトリの確認
    n8n_data_dir = os.path.expanduser('~/.n8n')
    if not os.path.exists(n8n_data_dir):
        os.makedirs(n8n_data_dir, exist_ok=True)
        print(f"[情報] データディレクトリを作成しました: {n8n_data_dir}")
    
    # 環境変数を設定
    env = os.environ.copy()
    env['N8N_USER_FOLDER'] = n8n_data_dir
    env['N8N_PORT'] = str(port)
    env['N8N_LICENSE_KEY'] = 'b01a8246-6a35-4221-917e-b5b25028a21b'
    
    # ポート使用状況確認
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        if result == 0:
            print(f"[情報] ポート {port} は既に使用中です")
            print(f"n8nは既に起動している可能性があります")
            print(f"ブラウザで http://127.0.0.1:{port} にアクセスしてください")
            return True
    except Exception as e:
        print(f"[警告] ポート確認中にエラー: {e}")
    
    print(f"[起動中] n8nを起動します...")
    print(f"  コマンド: {' '.join(args)}")
    print(f"  ポート: {port}")
    print(f"")
    print(f"ブラウザで http://127.0.0.1:{port} にアクセスしてください")
    print(f"")
    
    try:
        # n8nをバックグラウンドで起動
        # Windowsでは.CMDファイルを直接実行する必要がある場合がある
        if n8n_cmd.endswith('.CMD'):
            # .CMDファイルの場合はcmd.exe経由で実行
            process = subprocess.Popen(
                ['cmd.exe', '/c'] + args,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
        else:
            process = subprocess.Popen(
                args,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
        
        # 少し待って起動確認
        time.sleep(5)
        
        # プロセスがまだ実行中か確認
        if process.poll() is None:
            print(f"[成功] n8nを起動しました (PID: {process.pid})")
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"[エラー] n8nの起動に失敗しました")
            if stderr:
                print(f"エラー出力: {stderr.decode('utf-8', errors='ignore')}")
            if stdout:
                print(f"標準出力: {stdout.decode('utf-8', errors='ignore')}")
            return False
            
    except Exception as e:
        print(f"[エラー] n8nの起動中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_n8n()
