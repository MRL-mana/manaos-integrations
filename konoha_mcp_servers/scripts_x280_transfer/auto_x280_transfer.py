#!/usr/bin/env python3
"""
X280自動転送システム
X280のIPアドレスを自動検出してファイルを転送
"""

import subprocess
import time
from pathlib import Path
from datetime import datetime

class AutoX280Transfer:
    def __init__(self):
        self.source_dir = Path('/home/mana/Desktop/X280デスクトップ用_20251007_094645')
        self.common_ips = [
            "192.168.1.100", "192.168.1.101", "192.168.1.1",
            "192.168.0.100", "192.168.0.101", "192.168.0.1",
            "10.0.1.100", "10.0.1.101", "10.0.1.1",
            "172.16.1.100", "172.16.1.101", "172.16.1.1",
            "localhost", "127.0.0.1"
        ]
        
        print("🚀 X280自動転送システム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
        print("📱 転送先: X280のデスクトップ")
    
    def ping_host(self, host):
        """ホストのPingテスト"""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", host],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def test_ssh_connection(self, host):
        """SSH接続テスト"""
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "ConnectTimeout=3",
                    "-o",
                    "BatchMode=yes",
                    f"mana@{host}",
                    "echo SSH接続成功",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def transfer_to_x280(self, host):
        """X280にファイル転送"""
        print(f"\n📤 {host} へのファイル転送開始...")
        
        # X280にディレクトリ作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        x280_dir = f"~/Desktop/PDF変換結果_{timestamp}"
        
        print(f"📁 X280にディレクトリ作成: {x280_dir}")
        result = subprocess.run(
            ["ssh", f"mana@{host}", f"mkdir -p {x280_dir}"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            print(f"❌ ディレクトリ作成失敗: {result.stderr}")
            return False
        
        # ファイル転送
        print("📤 ファイル転送中...")
        result = subprocess.run(
            ["scp", "-r", str(self.source_dir), f"mana@{host}:{x280_dir}/"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            print(f"❌ ファイル転送失敗: {result.stderr}")
            return False
        
        # 転送結果確認
        print("🔍 転送結果確認...")
        result = subprocess.run(
            ["ssh", f"mana@{host}", f"ls -la {x280_dir}/"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print("✅ 転送成功！")
            print(f"📁 X280ダウンロード先: {x280_dir}")
            print("📊 転送されたファイル:")
            print(result.stdout)
            return True
        else:
            print(f"❌ 転送確認失敗: {result.stderr}")
            return False
    
    def run_auto_transfer(self):
        """自動転送実行"""
        print("🚀 X280自動転送開始")
        print("=" * 50)
        
        found_x280 = None
        
        # 一般的なIPアドレスをテスト
        for ip in self.common_ips:
            print(f"🔍 テスト中: {ip}", end=" ")
            
            if self.ping_host(ip):
                print("✅ Ping成功", end=" ")
                
                if self.test_ssh_connection(ip):
                    print("✅ SSH接続成功")
                    found_x280 = ip
                    break
                else:
                    print("❌ SSH接続失敗")
            else:
                print("❌ Ping失敗")
            
            time.sleep(0.5)
        
        if found_x280:
            print(f"\n🎉 X280発見: {found_x280}")
            success = self.transfer_to_x280(found_x280)
            
            if success:
                print("\n🎉 X280への転送完了！")
                print("📁 X280ダウンロード先: ~/Desktop/PDF変換結果_YYYYMMDD_HHMMSS/")
                print("🚀 X280でランチャーを実行してください")
                return True
            else:
                print("\n❌ X280への転送失敗")
                return False
        else:
            print("\n❌ X280が見つかりませんでした")
            print("💡 手動でX280のIPアドレスを確認してください")
            return False
    
    def create_manual_transfer_guide(self):
        """手動転送ガイド作成"""
        print("\n📋 手動転送ガイド作成中...")
        
        guide_content = f"""# X280手動転送ガイド

## 🚀 手動転送方法

### 方法1: ディレクトリ全体をコピー
```
ソース: {self.source_dir}
転送先: X280のデスクトップ
```

### 方法2: 個別ファイル転送
```bash
# X280のIPアドレスを確認してから実行
scp -r {self.source_dir}/* mana@X280のIPアドレス:~/Desktop/PDF変換結果_$(date +%Y%m%d_%H%M%S)/
```

### 方法3: 手動コピー
1. {self.source_dir} の内容を確認
2. ファイルを個別にX280のデスクトップにコピー
3. X280用PDF変換結果を開く.bat を実行

## 📁 転送対象ファイル
- テスト変換_20251007_090158.xlsx
- 変換結果_20251005_100104.xlsx
- PDF変換結果_20251007_091052.zip
- ダウンロードセンター.html
- download_info.json
- X280用PDF変換結果を開く.bat
- README_X280用.md

---
作成日: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
"""
        
        guide_path = Path('/home/mana/Desktop/X280手動転送ガイド.md')
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print(f"✅ 手動転送ガイド作成完了: {guide_path}")
        return guide_path

def main():
    """メイン実行関数"""
    transfer = AutoX280Transfer()
    
    print("🚀 X280自動転送システム開始")
    print("=" * 60)
    
    # 自動転送試行
    success = transfer.run_auto_transfer()
    
    if not success:
        print("\n📋 手動転送ガイドを作成します...")
        guide_path = transfer.create_manual_transfer_guide()
        print(f"✅ 手動転送ガイド作成完了: {guide_path}")
        print("\n💡 手動転送方法:")
        print("1. X280のIPアドレスを確認")
        print("2. ディレクトリ全体をX280にコピー")
        print("3. 個別ファイルをX280に転送")
    
    print("\n🎯 X280転送システム完了")

if __name__ == "__main__":
    main()


