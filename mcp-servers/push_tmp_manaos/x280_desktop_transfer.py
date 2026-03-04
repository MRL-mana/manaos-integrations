#!/usr/bin/env python3
"""
X280デスクトップへのファイル転送システム
現在操作中のX280のデスクトップにファイルを転送
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

class X280DesktopTransfer:
    def __init__(self):
        self.source_dir = Path('/home/mana/Downloads/PDF変換結果_20251007_091805')
        self.server_ip = "163.44.120.49"
        self.tailscale_ip = "100.93.120.33"
        
        print("🚀 X280デスクトップファイル転送システム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
        print(f"🌐 サーバーIP: {self.server_ip}")
        print(f"🔗 Tailscale IP: {self.tailscale_ip}")
        print("📱 転送先: X280のデスクトップ")
    
    def create_x280_desktop_package(self):
        """X280デスクトップ用パッケージ作成"""
        print("\n📦 X280デスクトップ用パッケージ作成中...")
        
        # X280用デスクトップディレクトリ作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        x280_desktop_dir = Path(f'/home/mana/Desktop/X280デスクトップ用_{timestamp}')
        x280_desktop_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 X280用デスクトップディレクトリ: {x280_desktop_dir}")
        
        # ファイルコピー
        copied_files = []
        print("\n📤 ファイルをX280用デスクトップにコピー中...")
        
        # Excelファイルコピー
        for excel_file in self.source_dir.glob('*.xlsx'):
            dest_path = x280_desktop_dir / excel_file.name
            shutil.copy2(excel_file, dest_path)
            copied_files.append(excel_file.name)
            print(f"  ✅ コピー完了: {excel_file.name} ({excel_file.stat().st_size:,} bytes)")
        
        # ZIPファイルコピー
        for zip_file in self.source_dir.glob('*.zip'):
            dest_path = x280_desktop_dir / zip_file.name
            shutil.copy2(zip_file, dest_path)
            copied_files.append(zip_file.name)
            print(f"  ✅ コピー完了: {zip_file.name} ({zip_file.stat().st_size:,} bytes)")
        
        # HTMLファイルコピー
        for html_file in self.source_dir.glob('*.html'):
            dest_path = x280_desktop_dir / html_file.name
            shutil.copy2(html_file, dest_path)
            copied_files.append(html_file.name)
            print(f"  ✅ コピー完了: {html_file.name} ({html_file.stat().st_size:,} bytes)")
        
        # JSONファイルコピー
        for json_file in self.source_dir.glob('*.json'):
            dest_path = x280_desktop_dir / json_file.name
            shutil.copy2(json_file, dest_path)
            copied_files.append(json_file.name)
            print(f"  ✅ コピー完了: {json_file.name} ({json_file.stat().st_size:,} bytes)")
        
        return x280_desktop_dir, copied_files
    
    def create_x280_windows_launcher(self, x280_dir):
        """X280用Windowsランチャー作成"""
        print("\n🚀 X280用Windowsランチャー作成中...")
        
        launcher_script = f"""@echo off
REM X280用PDF変換結果ランチャー

echo 🚀 X280 PDF変換結果ランチャー起動
echo ==================================

cd /d "{x280_dir}"

echo 📁 現在のディレクトリ: %cd%
echo 📊 ファイル一覧:
dir

echo.
echo 🌐 ブラウザでHTMLページを開く...
start "" "ダウンロードセンター.html"

echo 📄 Excelファイルを開く...
for %%f in ("*.xlsx") do (
    echo 📊 開く: %%f
    start "" "%%f"
)

echo.
echo 📦 ZIPファイルを開く...
for %%f in ("*.zip") do (
    echo 📦 開く: %%f
    start "" "%%f"
)

echo.
echo ✅ X280ランチャー実行完了
echo 📁 ファイル場所: {x280_dir}
pause
"""
        
        launcher_path = x280_dir / "X280用PDF変換結果を開く.bat"
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_script)
        
        print(f"✅ X280用Windowsランチャー作成完了: {launcher_path}")
        return launcher_path
    
    def create_x280_readme(self, x280_dir, copied_files):
        """X280用README作成"""
        print("\n📋 X280用README作成中...")
        
        readme_content = """# X280デスクトップ用PDF変換結果

## 📊 ファイル一覧

### Excelファイル
"""
        
        for file in copied_files:
            if file.endswith('.xlsx'):
                readme_content += f"- **{file}**\n"
        
        readme_content += """
### その他のファイル
"""
        
        for file in copied_files:
            if not file.endswith('.xlsx'):
                readme_content += f"- **{file}**\n"
        
        readme_content += f"""
## 🚀 使用方法

### 1. ランチャー実行
```
X280用PDF変換結果を開く.bat
```

### 2. 個別ファイル開く
- Excelファイル: ダブルクリック
- ZIPファイル: ダブルクリック
- HTMLファイル: ブラウザで開く

## 📁 ファイル場所
```
{x280_dir}
```

## 📋 作成日時
{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

---
X280デスクトップ用PDF変換結果パッケージ
"""
        
        readme_path = x280_dir / "README_X280用.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✅ X280用README作成完了: {readme_path}")
        return readme_path
    
    def create_x280_transfer_script(self, x280_dir):
        """X280転送用スクリプト作成"""
        print("\n📤 X280転送用スクリプト作成中...")
        
        transfer_script = f"""#!/bin/bash
# X280デスクトップ転送スクリプト

echo "🚀 X280デスクトップ転送開始"
echo "=================================="

echo "📱 X280のIPアドレスを入力してください:"
read X280_IP

if [ -z "$X280_IP" ]; then
    echo "❌ IPアドレスが入力されませんでした"
    exit 1
fi

echo "🔐 X280接続テスト中: $X280_IP"
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes mana@$X280_IP "echo 'X280接続成功'" 2>/dev/null; then
    echo "❌ X280接続失敗"
    echo "💡 X280でSSHサービスが有効になっているか確認してください"
    exit 1
fi

echo "✅ X280接続成功"

# X280にディレクトリ作成
X280_DIR="~/Desktop/PDF変換結果_$(date +%Y%m%d_%H%M%S)"
echo "📁 X280にディレクトリ作成: $X280_DIR"
ssh mana@$X280_IP "mkdir -p $X280_DIR"

# ファイル転送
echo "📤 ファイル転送中..."
scp -r {x280_dir}/* mana@$X280_IP:$X280_DIR/

# 転送結果確認
echo "🔍 転送結果確認:"
ssh mana@$X280_IP "ls -la $X280_DIR/"

echo "🎉 X280デスクトップ転送完了！"
echo "📁 X280ダウンロード先: $X280_DIR"
"""
        
        script_path = Path('/home/mana/Desktop/X280デスクトップ転送.sh')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(transfer_script)
        os.chmod(script_path, 0o755)
        
        print(f"✅ X280転送用スクリプト作成完了: {script_path}")
        return script_path
    
    def run_x280_desktop_transfer(self):
        """X280デスクトップ転送実行"""
        print("🚀 X280デスクトップ転送システム開始")
        print("=" * 60)
        
        # 1. X280用デスクトップパッケージ作成
        x280_dir, copied_files = self.create_x280_desktop_package()
        
        # 2. X280用Windowsランチャー作成
        launcher_path = self.create_x280_windows_launcher(x280_dir)
        
        # 3. X280用README作成
        readme_path = self.create_x280_readme(x280_dir, copied_files)
        
        # 4. X280転送用スクリプト作成
        transfer_script_path = self.create_x280_transfer_script(x280_dir)
        
        print("\n🎉 X280デスクトップ転送準備完了！")
        print("=" * 60)
        print(f"📁 X280用デスクトップディレクトリ: {x280_dir}")
        print(f"✅ コピー成功ファイル: {len(copied_files)}個")
        print(f"📋 コピーファイル一覧: {copied_files}")
        print(f"🚀 ランチャー: {launcher_path}")
        print(f"📋 README: {readme_path}")
        print(f"📤 転送スクリプト: {transfer_script_path}")
        print("")
        print("🚀 X280への転送方法:")
        print("1. 手動転送: ディレクトリ全体をX280にコピー")
        print("2. 自動転送: ./X280デスクトップ転送.sh")
        print("3. 個別転送: ファイルを個別にX280にコピー")
        
        return True

def main():
    """メイン実行関数"""
    transfer = X280DesktopTransfer()
    success = transfer.run_x280_desktop_transfer()
    
    if success:
        print("\n✅ X280デスクトップ転送準備完了！")
        print("📁 X280用デスクトップディレクトリを確認してください")
    else:
        print("\n❌ X280デスクトップ転送準備失敗")

if __name__ == "__main__":
    main()


