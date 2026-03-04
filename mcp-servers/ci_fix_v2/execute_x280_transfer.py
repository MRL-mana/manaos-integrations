#!/usr/bin/env python3
"""
X280転送実行システム
実際にX280のデスクトップにファイルを転送して自動実行
"""

import subprocess
from pathlib import Path
from datetime import datetime

class ExecuteX280Transfer:
    def __init__(self):
        self.source_dir = Path('/home/mana/Desktop/X280最終パッケージ')
        self.x280_user = "mana"
        self.x280_desktop = f"/home/{self.x280_user}/Desktop"
        
        print("🚀 X280転送実行システム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
        print(f"📱 転送先: X280のデスクトップ ({self.x280_desktop})")
        print(f"👤 X280ユーザー: {self.x280_user}")
    
    def find_x280_ip(self):
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
        
        for i, ip in enumerate(test_ips):
            if i % 100 == 0:
                print(f"🔍 スキャン進捗: {i}/{len(test_ips)}")
            
            try:
                # SSH接続テスト
                result = subprocess.run(
                    [
                        "ssh",
                        "-o",
                        "ConnectTimeout=1",
                        "-o",
                        "BatchMode=yes",
                        f"{self.x280_user}@{ip}",
                        "echo SSH接続成功",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    print(f"🎉 X280発見: {ip}")
                    return ip
                    
            except Exception:
                continue
        
        return None
    
    def transfer_to_x280(self, x280_ip):
        """X280にファイル転送"""
        print(f"\n📤 {x280_ip} へのファイル転送開始...")
        
        # X280にディレクトリ作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        x280_dir = f"{self.x280_desktop}/PDF変換結果_X280最終版_{timestamp}"
        
        print(f"📁 X280にディレクトリ作成: {x280_dir}")
        result = subprocess.run(
            ["ssh", f"{self.x280_user}@{x280_ip}", f"mkdir -p {x280_dir}"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            print(f"❌ ディレクトリ作成失敗: {result.stderr}")
            return False
        
        # ファイル転送
        print("📤 ファイル転送中...")
        result = subprocess.run(
            ["scp", "-r", str(self.source_dir), f"{self.x280_user}@{x280_ip}:{x280_dir}/"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            print(f"❌ ファイル転送失敗: {result.stderr}")
            return False
        
        # 転送結果確認
        print("🔍 転送結果確認...")
        result = subprocess.run(
            ["ssh", f"{self.x280_user}@{x280_ip}", f"ls -la {x280_dir}/"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print("✅ 転送成功！")
            print(f"📁 X280ダウンロード先: {x280_dir}")
            print("📊 転送されたファイル:")
            print(result.stdout)
            return x280_dir
        else:
            print(f"❌ 転送確認失敗: {result.stderr}")
            return False
    
    def create_x280_launcher(self, x280_ip, x280_dir):
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
        remote_cmd = (
            f"cat > {x280_dir}/X280用PDF変換結果を開く.sh << \"EOF\"\n"
            f"{launcher_script}\n"
            "EOF"
        )
        result = subprocess.run(
            ["ssh", f"{self.x280_user}@{x280_ip}", remote_cmd],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            # 実行権限付与
            subprocess.run(
                [
                    "ssh",
                    f"{self.x280_user}@{x280_ip}",
                    f"chmod +x {x280_dir}/X280用PDF変換結果を開く.sh",
                ],
                capture_output=True,
                text=True,
            )
            print(f"✅ X280用ランチャー作成完了: {x280_dir}/X280用PDF変換結果を開く.sh")
            return True
        else:
            print(f"❌ X280用ランチャー作成失敗: {result.stderr}")
            return False
    
    def run_x280_launcher(self, x280_ip, x280_dir):
        """X280上でランチャー実行"""
        print("\n🚀 X280上でランチャー実行中...")
        
        result = subprocess.run(
            [
                "ssh",
                f"{self.x280_user}@{x280_ip}",
                f"cd {x280_dir} && ./X280用PDF変換結果を開く.sh",
            ],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print("✅ X280ランチャー実行完了")
            print("📊 実行結果:")
            print(result.stdout)
            return True
        else:
            print(f"❌ X280ランチャー実行失敗: {result.stderr}")
            return False
    
    def run_execute_transfer(self):
        """転送実行"""
        print("🚀 X280転送実行開始")
        print("=" * 60)
        
        # 1. X280のIPアドレス検出
        x280_ip = self.find_x280_ip()
        
        if not x280_ip:
            print("\n❌ X280が見つかりませんでした")
            print("💡 手動でX280のIPアドレスを確認してください")
            return False
        
        # 2. ファイル転送
        x280_dir = self.transfer_to_x280(x280_ip)
        
        if not x280_dir:
            print("\n❌ X280への転送失敗")
            return False
        
        # 3. X280上でランチャー作成
        self.create_x280_launcher(x280_ip, x280_dir)
        
        # 4. X280上でランチャー実行
        self.run_x280_launcher(x280_ip, x280_dir)
        
        print("\n🎉 X280転送実行完了！")
        print(f"📁 X280ダウンロード先: {x280_dir}")
        print("🚀 X280でランチャーが実行されました")
        print(f"📋 ランチャー: {x280_dir}/X280用PDF変換結果を開く.sh")
        
        return True

def main():
    """メイン実行関数"""
    transfer = ExecuteX280Transfer()
    success = transfer.run_execute_transfer()
    
    if success:
        print("\n✅ X280転送実行完了！")
        print("📁 X280のデスクトップを確認してください")
    else:
        print("\n❌ X280転送実行失敗")
        print("💡 手動転送方法:")
        print("1. X280のIPアドレスを確認")
        print("2. ディレクトリ全体をX280にコピー")
        print("3. 個別ファイルをX280に転送")

if __name__ == "__main__":
    main()


