#!/usr/bin/env python3
"""
X280直接接続システム
複数の方法でX280への直接接続を試行
"""

import subprocess
from pathlib import Path
from datetime import datetime

class X280DirectConnector:
    def __init__(self):
        self.source_dir = Path('/home/mana/Downloads/PDF変換結果_20251007_091805')
        self.current_ip = "163.44.120.49"  # 現在のIPアドレス
        
        print("🚀 X280直接接続システム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
        print(f"🌐 現在のIPアドレス: {self.current_ip}")
    
    def scan_network(self):
        """ネットワークスキャンでX280を検索"""
        print("\n🔍 ネットワークスキャン中...")
        
        # 複数のネットワーク範囲をスキャン
        networks = [
            "192.168.1.0/24",
            "192.168.0.0/24", 
            "10.0.0.0/24",
            "172.16.0.0/24"
        ]
        
        found_hosts = []
        
        for network in networks:
            try:
                print(f"📡 スキャン中: {network}")
                result = subprocess.run([
                    'nmap', '-sn', network
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'Nmap scan report' in line:
                            ip = line.split()[-1].strip('()')
                            found_hosts.append(ip)
                            print(f"  📍 発見: {ip}")
                
            except subprocess.TimeoutExpired:
                print(f"  ⏰ タイムアウト: {network}")
            except Exception as e:
                print(f"  ❌ エラー: {network} - {e}")
        
        return found_hosts
    
    def test_ssh_connections(self, hosts):
        """発見されたホストにSSH接続を試行"""
        print("\n🔐 SSH接続テスト中...")
        
        successful_connections = []
        
        for host in hosts:
            try:
                print(f"🔑 SSH接続テスト: {host}")
                
                # SSH接続テスト
                result = subprocess.run([
                    'ssh', '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes',
                    f'mana@{host}',
                    'echo "SSH接続成功"'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"  ✅ SSH接続成功: {host}")
                    successful_connections.append(host)
                else:
                    print(f"  ❌ SSH接続失敗: {host}")
                    
            except subprocess.TimeoutExpired:
                print(f"  ⏰ SSH接続タイムアウト: {host}")
            except Exception as e:
                print(f"  ❌ SSH接続エラー: {host} - {e}")
        
        return successful_connections
    
    def transfer_to_x280(self, x280_host):
        """X280にファイルを転送"""
        print(f"\n📤 X280へのファイル転送開始: {x280_host}")
        
        if not self.source_dir.exists():
            print("❌ ソースディレクトリが見つかりません")
            return False
        
        # X280にディレクトリ作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        x280_dir = f"/home/mana/Desktop/PDF変換結果_{timestamp}"
        
        try:
            print(f"📁 X280にディレクトリ作成: {x280_dir}")
            result = subprocess.run([
                'ssh', f'mana@{x280_host}',
                f'mkdir -p "{x280_dir}"'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"❌ ディレクトリ作成失敗: {result.stderr}")
                return False
            
            print("✅ ディレクトリ作成成功")
            
        except Exception as e:
            print(f"❌ ディレクトリ作成エラー: {e}")
            return False
        
        # ファイル転送
        transferred_files = []
        failed_files = []
        
        for file_path in self.source_dir.glob('*'):
            if file_path.is_file():
                try:
                    print(f"📤 転送中: {file_path.name}")
                    
                    result = subprocess.run([
                        'scp', str(file_path),
                        f'mana@{x280_host}:{x280_dir}/'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        transferred_files.append(file_path.name)
                        print(f"  ✅ 転送完了: {file_path.name}")
                    else:
                        failed_files.append(file_path.name)
                        print(f"  ❌ 転送失敗: {file_path.name} - {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    failed_files.append(file_path.name)
                    print(f"  ⏰ 転送タイムアウト: {file_path.name}")
                except Exception as e:
                    failed_files.append(file_path.name)
                    print(f"  ❌ 転送エラー: {file_path.name} - {e}")
        
        # 転送結果確認
        try:
            print(f"\n🔍 転送結果確認: {x280_host}")
            result = subprocess.run([
                'ssh', f'mana@{x280_host}',
                f'ls -la "{x280_dir}"'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ X280ファイル一覧:")
                print(result.stdout)
            else:
                print(f"❌ ファイル確認失敗: {result.stderr}")
                
        except Exception as e:
            print(f"❌ ファイル確認エラー: {e}")
        
        return {
            'host': x280_host,
            'directory': x280_dir,
            'transferred': transferred_files,
            'failed': failed_files,
            'success': len(failed_files) == 0
        }
    
    def create_x280_launcher(self, x280_host, x280_dir):
        """X280用ランチャースクリプト作成"""
        print(f"\n🚀 X280用ランチャースクリプト作成: {x280_host}")
        
        try:
            launcher_script = f"""#!/bin/bash
# PDF変換結果ランチャー - X280用

echo "🚀 PDF変換結果ランチャー起動"
echo "=================================="

# ダウンロードディレクトリに移動
cd "{x280_dir}"

echo "📁 現在のディレクトリ: $(pwd)"
echo "📊 ファイル一覧:"
ls -la

echo ""
echo "🌐 ブラウザでHTMLページを開く..."
xdg-open "file://{x280_dir}/ダウンロードセンター.html" &

echo "📄 Excelファイルを開く..."
for file in *.xlsx; do
    if [ -f "$file" ]; then
        echo "📊 開く: $file"
        libreoffice --calc "$file" &
    fi
done

echo "✅ ランチャー実行完了"
"""
            
            # X280でランチャースクリプト作成
            result = subprocess.run([
                'ssh', f'mana@{x280_host}',
                f'echo "{launcher_script}" > "{x280_dir}/PDF変換結果を開く.sh" && chmod +x "{x280_dir}/PDF変換結果を開く.sh"'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ X280用ランチャースクリプト作成完了")
                return True
            else:
                print(f"❌ ランチャースクリプト作成失敗: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ ランチャースクリプト作成エラー: {e}")
            return False
    
    def run_direct_connection(self):
        """X280直接接続実行"""
        print("🚀 X280直接接続開始")
        print("=" * 60)
        
        # 1. ネットワークスキャン
        found_hosts = self.scan_network()
        
        if not found_hosts:
            print("❌ ネットワーク上でX280が見つかりません")
            print("💡 手動でX280のIPアドレスを確認してください")
            return False
        
        print(f"✅ 発見されたホスト: {found_hosts}")
        
        # 2. SSH接続テスト
        successful_hosts = self.test_ssh_connections(found_hosts)
        
        if not successful_hosts:
            print("❌ SSH接続に成功したホストがありません")
            print("💡 X280でSSHサービスが有効になっているか確認してください")
            return False
        
        print(f"✅ SSH接続成功ホスト: {successful_hosts}")
        
        # 3. ファイル転送
        for host in successful_hosts:
            print(f"\n📤 {host}へのファイル転送開始")
            transfer_result = self.transfer_to_x280(host)
            
            if transfer_result['success']:
                print(f"🎉 {host}への転送完了！")
                print(f"📁 X280ディレクトリ: {transfer_result['directory']}")
                print(f"✅ 転送成功ファイル: {len(transfer_result['transferred'])}個")
                
                # ランチャースクリプト作成
                self.create_x280_launcher(host, transfer_result['directory'])
                
                return True
            else:
                print(f"❌ {host}への転送失敗")
        
        return False

def main():
    """メイン実行関数"""
    connector = X280DirectConnector()
    success = connector.run_direct_connection()
    
    if success:
        print("\n✅ X280直接接続完了！")
        print("📁 X280デスクトップのダウンロードディレクトリを確認してください")
    else:
        print("\n❌ X280直接接続失敗")
        print("💡 代替手段:")
        print("1. X280のIPアドレスを手動で確認")
        print("2. SSHサービスが有効になっているか確認")
        print("3. ファイアウォール設定を確認")
        print("4. 代替ダウンロードシステムを使用")

if __name__ == "__main__":
    main()
