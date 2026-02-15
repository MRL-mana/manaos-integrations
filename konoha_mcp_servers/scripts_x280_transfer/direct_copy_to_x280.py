#!/usr/bin/env python3
"""
X280のデスクトップに直接コピーするスクリプト
"""

import os
import shutil
import subprocess
from datetime import datetime

def main():
    print('🚀 Windows共有フォルダ経由でX280に直接コピー')
    print('=' * 50)

    # 変換済みファイル
    source_file = '/home/mana/Desktop/10月3日変換結果_20251004_161625.xlsx'

    if not os.path.exists(source_file):
        print('❌ 変換ファイルが見つかりません')
        return

    print(f'✅ 変換ファイル確認: {source_file}')
    print(f'   ファイルサイズ: {os.path.getsize(source_file)}バイト')

    # 方法1: Windowsの共有フォルダを探す
    print('\n🔍 Windows共有フォルダを検索中...')
    possible_shares = [
        '/mnt/c/',
        '/mnt/windows/',
        '/media/',
        '/run/user/',
        '/tmp/'
    ]

    found_shares = []
    for share in possible_shares:
        if os.path.exists(share):
            found_shares.append(share)
            print(f'✅ 共有フォルダ発見: {share}')

    print(f'\n📁 発見された共有フォルダ: {len(found_shares)}個')

    # 方法2: Windowsの一時フォルダにコピー
    print('\n📁 Windows一時フォルダにコピー試行...')
    temp_paths = [
        '/tmp/windows_desktop/',
        '/tmp/x280_desktop/',
        '/root/windows_desktop/',
        '/home/mana/windows_desktop/'
    ]

    for temp_path in temp_paths:
        try:
            os.makedirs(temp_path, exist_ok=True)
            target = f'{temp_path}10月3日変換結果_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            shutil.copy2(source_file, target)
            print(f'✅ 一時フォルダにコピー成功: {target}')
        except Exception as e:
            print(f'❌ 一時フォルダコピー失敗: {temp_path} - {e}')

    # 方法3: Windowsのコマンドプロンプト経由でコピー
    print('\n🖥️ Windowsコマンドプロンプト経由でコピー試行...')
    try:
        # Windowsのコピーコマンドを実行
        copy_cmd = (
            f'copy "{source_file}" '
            f'"%USERPROFILE%\\Desktop\\10月3日変換結果_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        )
        result = subprocess.run(
            ["cmd.exe", "/c", copy_cmd],
            capture_output=True,
            text=True,
            timeout=15,
        )
        
        if result.returncode == 0:
            print('✅ Windowsコマンドプロンプト経由でコピー成功！')
            print('🎉 X280のデスクトップに直接保存完了！')
        else:
            print(f'❌ Windowsコマンドプロンプト実行失敗: {result.stderr}')
            
    except Exception as e:
        print(f'❌ Windowsコマンドプロンプト実行エラー: {e}')

    print('\n📋 **最終確認方法:**')
    print('1. Windowsのデスクトップを確認')
    print('2. 10月3日変換結果_*.xlsx ファイルを探す')
    print('3. ファイルが見つかれば成功！')
    
    print('\n📋 **代替アクセス方法:**')
    print('1. Windowsキー + E でファイルマネージャーを開く')
    print('2. アドレスバーに以下を入力:')
    print('   \\\\wsl$\\Ubuntu\\home\\mana\\Desktop\\')
    print('3. 10月3日変換結果_20251004_161625.xlsx を探す')
    print('4. 右クリック → コピー → Windowsデスクトップに貼り付け')

if __name__ == "__main__":
    main()



