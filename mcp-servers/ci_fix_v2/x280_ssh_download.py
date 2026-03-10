#!/usr/bin/env python3
"""
X280 SSH接続ダウンロードシステム
X280のデスクトップにPDF変換結果をダウンロード
"""

import subprocess
from pathlib import Path
from datetime import datetime

class X280SSHDownloader:
    def __init__(self):
        self.source_dir = Path('/home/mana/Downloads/PDF変換結果_20251007_091805')
        self.x280_host = "192.168.1.100"  # X280のIPアドレス（要調整）
        self.x280_user = "mana"
        self.x280_desktop = "/home/mana/Desktop"
        self.x280_download_dir = f"{self.x280_desktop}/PDF変換結果_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print("🚀 X280 SSH接続ダウンロードシステム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
        print(f"🌐 X280ホスト: {self.x280_host}")
        print(f"👤 X280ユーザー: {self.x280_user}")
        print(f"📁 X280ダウンロード先: {self.x280_download_dir}")
    
    def test_ssh_connection(self):
        """SSH接続テスト"""
        print("\n🔐 SSH接続テスト中...")
        
        try:
            # SSH接続テスト
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes',
                f'{self.x280_user}@{self.x280_host}',
                'echo "SSH接続成功"'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print("✅ SSH接続成功")
                return True
            else:
                print(f"❌ SSH接続失敗: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ SSH接続タイムアウト")
            return False
        except Exception as e:
            print(f"❌ SSH接続エラー: {e}")
            return False
    
    def create_x280_directory(self):
        """X280にダウンロードディレクトリを作成"""
        print("\n📁 X280にダウンロードディレクトリ作成中...")
        
        try:
            # X280にディレクトリ作成
            result = subprocess.run([
                'ssh', f'{self.x280_user}@{self.x280_host}',
                f'mkdir -p "{self.x280_download_dir}"'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ ディレクトリ作成成功: {self.x280_download_dir}")
                return True
            else:
                print(f"❌ ディレクトリ作成失敗: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ ディレクトリ作成エラー: {e}")
            return False
    
    def transfer_files(self):
        """ファイルをX280に転送"""
        print("\n📤 ファイル転送中...")
        
        if not self.source_dir.exists():
            print("❌ ソースディレクトリが見つかりません")
            return False
        
        transferred_files = []
        failed_files = []
        
        # 各ファイルを転送
        for file_path in self.source_dir.glob('*'):
            if file_path.is_file():
                try:
                    print(f"📤 転送中: {file_path.name}")
                    
                    # scpでファイル転送
                    result = subprocess.run([
                        'scp', str(file_path),
                        f'{self.x280_user}@{self.x280_host}:{self.x280_download_dir}/'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        transferred_files.append(file_path.name)
                        print(f"✅ 転送完了: {file_path.name}")
                    else:
                        failed_files.append(file_path.name)
                        print(f"❌ 転送失敗: {file_path.name} - {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    failed_files.append(file_path.name)
                    print(f"❌ 転送タイムアウト: {file_path.name}")
                except Exception as e:
                    failed_files.append(file_path.name)
                    print(f"❌ 転送エラー: {file_path.name} - {e}")
        
        return {
            'transferred': transferred_files,
            'failed': failed_files,
            'success': len(failed_files) == 0
        }
    
    def verify_transfer(self):
        """転送結果を確認"""
        print("\n🔍 転送結果確認中...")
        
        try:
            # X280でファイル一覧を取得
            result = subprocess.run([
                'ssh', f'{self.x280_user}@{self.x280_host}',
                f'ls -la "{self.x280_download_dir}"'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ X280ファイル一覧:")
                print(result.stdout)
                return True
            else:
                print(f"❌ ファイル確認失敗: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ ファイル確認エラー: {e}")
            return False
    
    def create_desktop_shortcut(self):
        """デスクトップにショートカット作成"""
        print("\n🔗 デスクトップショートカット作成中...")
        
        try:
            # X280でデスクトップショートカット作成
            shortcut_script = f"""
#!/bin/bash
# PDF変換結果ダウンロードフォルダを開く
cd "{self.x280_download_dir}"
nautilus . &
"""
            
            result = subprocess.run([
                'ssh', f'{self.x280_user}@{self.x280_host}',
                f'echo "{shortcut_script}" > "{self.x280_desktop}/PDF変換結果を開く.sh" && chmod +x "{self.x280_desktop}/PDF変換結果を開く.sh"'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ デスクトップショートカット作成完了")
                return True
            else:
                print(f"❌ ショートカット作成失敗: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ ショートカット作成エラー: {e}")
            return False
    
    def run_download(self):
        """X280ダウンロード実行"""
        print("🚀 X280 SSH接続ダウンロード開始")
        print("=" * 60)
        
        # 1. SSH接続テスト
        if not self.test_ssh_connection():
            print("❌ SSH接続に失敗しました")
            return False
        
        # 2. ディレクトリ作成
        if not self.create_x280_directory():
            print("❌ ディレクトリ作成に失敗しました")
            return False
        
        # 3. ファイル転送
        transfer_result = self.transfer_files()
        
        if not transfer_result['success']:  # type: ignore[index]
            print(f"❌ ファイル転送に失敗: {transfer_result['failed']}")  # type: ignore[index]
            return False
        
        # 4. 転送結果確認
        if not self.verify_transfer():
            print("❌ 転送結果確認に失敗しました")
            return False
        
        # 5. デスクトップショートカット作成
        self.create_desktop_shortcut()
        
        print("\n🎉 X280ダウンロード完了！")
        print("=" * 60)
        print(f"📁 X280ダウンロード先: {self.x280_download_dir}")
        print(f"✅ 転送成功ファイル: {len(transfer_result['transferred'])}個")  # type: ignore[index]
        print(f"📋 転送ファイル一覧: {transfer_result['transferred']}")  # type: ignore[index]
        print(f"🔗 デスクトップショートカット: {self.x280_desktop}/PDF変換結果を開く.sh")
        
        return True

def main():
    """メイン実行関数"""
    # X280の接続設定を確認
    print("🔧 X280接続設定確認")
    print("=" * 40)
    
    # 複数のIPアドレスを試す
    x280_ips = [
        "192.168.1.100",
        "192.168.1.101", 
        "192.168.0.100",
        "192.168.0.101",
        "x280.local",
        "localhost"
    ]
    
    for ip in x280_ips:
        print(f"🌐 接続テスト: {ip}")
        downloader = X280SSHDownloader()
        downloader.x280_host = ip
        
        if downloader.test_ssh_connection():
            print(f"✅ 接続成功: {ip}")
            success = downloader.run_download()
            if success:
                print(f"🎉 X280ダウンロード完了: {ip}")
                break
        else:
            print(f"❌ 接続失敗: {ip}")
    
    print("\n📋 手動接続方法:")
    print("1. SSH接続: ssh mana@X280のIPアドレス")
    print("2. ファイル転送: scp ファイル名 mana@X280のIPアドレス:~/Desktop/")
    print("3. ディレクトリ転送: scp -r ディレクトリ名 mana@X280のIPアドレス:~/Desktop/")

if __name__ == "__main__":
    main()


