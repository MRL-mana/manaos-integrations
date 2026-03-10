#!/usr/bin/env python3
"""
X280手動接続システム
一般的なIPアドレス範囲でX280への接続を試行
"""

import subprocess
from pathlib import Path
from datetime import datetime

class X280ManualConnector:
    def __init__(self):
        self.source_dir = Path('/home/mana/Downloads/PDF変換結果_20251007_091805')
        
        print("🚀 X280手動接続システム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
    
    def ping_host(self, host):
        """ホストにpingを送信"""
        try:
            result = subprocess.run([
                'ping', '-c', '1', '-W', '3', host
            ], capture_output=True, text=True, timeout=10)
            
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def test_ssh_connection(self, host):
        """SSH接続をテスト"""
        try:
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes',
                f'mana@{host}',
                'echo "SSH接続成功"'
            ], capture_output=True, text=True, timeout=10)
            
            return result.returncode == 0
        except Exception:
            return False
    
    def scan_common_ips(self):
        """一般的なIPアドレス範囲をスキャン"""
        print("\n🔍 一般的なIPアドレス範囲をスキャン中...")
        
        # 一般的なプライベートIP範囲
        ip_ranges = [
            # 192.168.x.x
            [f"192.168.{i}.100" for i in range(1, 5)],
            [f"192.168.{i}.101" for i in range(1, 5)],
            [f"192.168.{i}.1" for i in range(1, 5)],
            
            # 10.x.x.x
            [f"10.0.{i}.100" for i in range(1, 5)],
            [f"10.0.{i}.101" for i in range(1, 5)],
            [f"10.0.{i}.1" for i in range(1, 5)],
            
            # 172.16.x.x
            [f"172.16.{i}.100" for i in range(1, 5)],
            [f"172.16.{i}.101" for i in range(1, 5)],
            [f"172.16.{i}.1" for i in range(1, 5)],
        ]
        
        # フラット化
        test_ips = []
        for range_list in ip_ranges:
            test_ips.extend(range_list)
        
        print(f"📡 テスト対象IP数: {len(test_ips)}")
        
        pingable_hosts = []
        ssh_connectable_hosts = []
        
        for ip in test_ips:
            print(f"🔍 テスト中: {ip}", end=" ")
            
            # Pingテスト
            if self.ping_host(ip):
                print("✅ Ping成功", end=" ")
                pingable_hosts.append(ip)
                
                # SSH接続テスト
                if self.test_ssh_connection(ip):
                    print("✅ SSH接続成功")
                    ssh_connectable_hosts.append(ip)
                else:
                    print("❌ SSH接続失敗")
            else:
                print("❌ Ping失敗")
        
        return pingable_hosts, ssh_connectable_hosts
    
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
    
    def run_manual_connection(self):
        """X280手動接続実行"""
        print("🚀 X280手動接続開始")
        print("=" * 60)
        
        # 1. 一般的なIP範囲をスキャン
        pingable_hosts, ssh_connectable_hosts = self.scan_common_ips()
        
        print("\n📊 スキャン結果:")
        print(f"  Ping可能ホスト: {len(pingable_hosts)}個")
        print(f"  SSH接続可能ホスト: {len(ssh_connectable_hosts)}個")
        
        if pingable_hosts:
            print(f"  Ping可能: {pingable_hosts}")
        
        if ssh_connectable_hosts:
            print(f"  SSH接続可能: {ssh_connectable_hosts}")
        
        if not ssh_connectable_hosts:
            print("❌ SSH接続可能なホストが見つかりません")
            print("💡 手動でX280のIPアドレスを確認してください")
            return False
        
        # 2. ファイル転送
        for host in ssh_connectable_hosts:
            print(f"\n📤 {host}へのファイル転送開始")
            transfer_result = self.transfer_to_x280(host)
            
            if transfer_result['success']:  # type: ignore[index]
                print(f"🎉 {host}への転送完了！")
                print(f"📁 X280ディレクトリ: {transfer_result['directory']}")  # type: ignore[index]
                print(f"✅ 転送成功ファイル: {len(transfer_result['transferred'])}個")  # type: ignore[index]
                
                # ランチャースクリプト作成
                self.create_x280_launcher(host, transfer_result['directory'])  # type: ignore[index]
                
                return True
            else:
                print(f"❌ {host}への転送失敗")
        
        return False

def main():
    """メイン実行関数"""
    connector = X280ManualConnector()
    success = connector.run_manual_connection()
    
    if success:
        print("\n✅ X280手動接続完了！")
        print("📁 X280デスクトップのダウンロードディレクトリを確認してください")
    else:
        print("\n❌ X280手動接続失敗")
        print("💡 代替手段:")
        print("1. X280のIPアドレスを手動で確認")
        print("2. SSHサービスが有効になっているか確認")
        print("3. ファイアウォール設定を確認")
        print("4. 代替ダウンロードシステムを使用")

if __name__ == "__main__":
    main()


