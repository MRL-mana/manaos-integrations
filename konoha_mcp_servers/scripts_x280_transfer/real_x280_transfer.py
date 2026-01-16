#!/usr/bin/env python3
"""
X280実際転送システム
現在操作中のX280に実際にファイルを転送
"""

import subprocess
from pathlib import Path
from datetime import datetime

class RealX280Transfer:
    def __init__(self):
        self.source_dir = Path('/home/mana/Desktop/X280最終パッケージ')
        self.x280_user = "mana"
        self.x280_desktop = f"/home/{self.x280_user}/Desktop"
        
        print("🚀 X280実際転送システム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
        print(f"📱 転送先: X280のデスクトップ ({self.x280_desktop})")
        print(f"👤 X280ユーザー: {self.x280_user}")
    
    def detect_x280_ip(self):
        """X280のIPアドレスを検出"""
        print("\n🔍 X280のIPアドレス検出中...")
        
        # 一般的なプライベートIPアドレス範囲
        ip_ranges = [
            "192.168.1.", "192.168.0.", "192.168.2.", "192.168.3.",
            "10.0.1.", "10.0.2.", "10.0.3.", "10.0.4.",
            "172.16.1.", "172.16.2.", "172.16.3.", "172.16.4."
        ]
        
        test_ips = []
        for ip_range in ip_ranges:
            for i in range(1, 255):
                test_ips.append(f"{ip_range}{i}")
        
        print(f"📡 スキャン対象IP数: {len(test_ips)}")
        
        found_ips = []
        for i, ip in enumerate(test_ips):
            if i % 50 == 0:
                print(f"🔍 スキャン進捗: {i}/{len(test_ips)} ({ip})")
            
            try:
                # Pingテスト
                result = subprocess.run(
                    f"ping -c 1 -W 1 {ip}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    print(f"✅ Ping成功: {ip}")
                    
                    # SSH接続テスト
                    ssh_result = subprocess.run(
                        f"ssh -o ConnectTimeout=2 -o BatchMode=yes {self.x280_user}@{ip} 'echo SSH接続成功'",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    
                    if ssh_result.returncode == 0:
                        print(f"🎉 X280発見: {ip}")
                        found_ips.append(ip)
                        break
                    else:
                        print(f"❌ SSH接続失敗: {ip}")
                        
            except Exception:
                continue
        
        return found_ips
    
    def transfer_to_x280(self, x280_ip):
        """X280にファイル転送"""
        print(f"\n📤 {x280_ip} へのファイル転送開始...")
        
        # X280にディレクトリ作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        x280_dir = f"{self.x280_desktop}/PDF変換結果_X280最終版_{timestamp}"
        
        print(f"📁 X280にディレクトリ作成: {x280_dir}")
        create_dir_cmd = f"ssh {self.x280_user}@{x280_ip} 'mkdir -p {x280_dir}'"
        result = subprocess.run(create_dir_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ ディレクトリ作成失敗: {result.stderr}")
            return False
        
        # ファイル転送
        print("📤 ファイル転送中...")
        transfer_cmd = f"scp -r {self.source_dir}/* {self.x280_user}@{x280_ip}:{x280_dir}/"
        result = subprocess.run(transfer_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ ファイル転送失敗: {result.stderr}")
            return False
        
        # 転送結果確認
        print("🔍 転送結果確認...")
        check_cmd = f"ssh {self.x280_user}@{x280_ip} 'ls -la {x280_dir}/'"
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 転送成功！")
            print(f"📁 X280ダウンロード先: {x280_dir}")
            print("📊 転送されたファイル:")
            print(result.stdout)
            return True
        else:
            print(f"❌ 転送確認失敗: {result.stderr}")
            return False
    
    def create_x280_launcher_on_x280(self, x280_ip, x280_dir):
        """X280上でランチャー作成"""
        print("\n🚀 X280上でランチャー作成中...")
        
        launcher_script = f"""#!/bin/bash
# X280用PDF変換結果ランチャー

echo "🚀 X280 PDF変換結果ランチャー起動"
echo "=================================="

cd "{x280_dir}"

echo "📁 現在のディレクトリ: $(pwd)"
echo "📊 ファイル一覧:"
ls -la

echo ""
echo "🌐 ブラウザでHTMLページを開く..."
xdg-open "X280用ダウンロードセンター.html" &

echo "📄 Excelファイルを開く..."
for file in *.xlsx; do
    if [ -f "$file" ]; then
        echo "📊 開く: $file"
        libreoffice --calc "$file" &
    fi
done

echo ""
echo "✅ X280ランチャー実行完了"
echo "📁 ファイル場所: {x280_dir}"
"""
        
        # X280上でランチャー作成
        launcher_cmd = f"ssh {self.x280_user}@{x280_ip} 'cat > {x280_dir}/X280用PDF変換結果を開く.sh << \"EOF\"\n{launcher_script}\nEOF'"
        result = subprocess.run(launcher_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # 実行権限付与
            chmod_cmd = f"ssh {self.x280_user}@{x280_ip} 'chmod +x {x280_dir}/X280用PDF変換結果を開く.sh'"
            subprocess.run(chmod_cmd, shell=True, capture_output=True, text=True)
            print(f"✅ X280用ランチャー作成完了: {x280_dir}/X280用PDF変換結果を開く.sh")
            return True
        else:
            print(f"❌ X280用ランチャー作成失敗: {result.stderr}")
            return False
    
    def run_real_transfer(self):
        """実際の転送実行"""
        print("🚀 X280実際転送システム開始")
        print("=" * 60)
        
        # 1. X280のIPアドレス検出
        found_ips = self.detect_x280_ip()
        
        if not found_ips:
            print("\n❌ X280が見つかりませんでした")
            print("💡 手動でX280のIPアドレスを確認してください")
            return False
        
        # 2. 最初に見つかったIPに転送
        x280_ip = found_ips[0]
        print(f"\n🎉 X280発見: {x280_ip}")
        
        # 3. ファイル転送
        success = self.transfer_to_x280(x280_ip)
        
        if not success:
            print("\n❌ X280への転送失敗")
            return False
        
        # 4. X280上でランチャー作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        x280_dir = f"{self.x280_desktop}/PDF変換結果_X280最終版_{timestamp}"
        self.create_x280_launcher_on_x280(x280_ip, x280_dir)
        
        print("\n🎉 X280への転送完了！")
        print(f"📁 X280ダウンロード先: {x280_dir}")
        print("🚀 X280でランチャーを実行してください")
        print(f"📋 ランチャー: {x280_dir}/X280用PDF変換結果を開く.sh")
        
        return True

def main():
    """メイン実行関数"""
    transfer = RealX280Transfer()
    success = transfer.run_real_transfer()
    
    if success:
        print("\n✅ X280実際転送完了！")
        print("📁 X280のデスクトップを確認してください")
    else:
        print("\n❌ X280実際転送失敗")
        print("💡 手動転送方法:")
        print("1. X280のIPアドレスを確認")
        print("2. ディレクトリ全体をX280にコピー")
        print("3. 個別ファイルをX280に転送")

if __name__ == "__main__":
    main()


