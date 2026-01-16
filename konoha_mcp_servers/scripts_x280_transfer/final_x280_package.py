#!/usr/bin/env python3
"""
最終X280パッケージ作成システム
X280のデスクトップに直接使用できる完全パッケージを作成
"""

import shutil
from pathlib import Path
from datetime import datetime
import json

class FinalX280Package:
    def __init__(self):
        self.source_dir = Path('/home/mana/Desktop/PDF変換結果_X280用_20251007_095320')
        self.final_dir = Path('/home/mana/Desktop/X280最終パッケージ')
        
        print("🚀 最終X280パッケージ作成システム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
        print(f"📱 最終パッケージ先: {self.final_dir}")
    
    def create_final_package(self):
        """最終X280パッケージ作成"""
        print("\n📦 最終X280パッケージ作成中...")
        
        # 最終ディレクトリ作成
        self.final_dir.mkdir(parents=True, exist_ok=True)
        
        # ファイルコピー
        copied_files = []
        print("📤 ファイルを最終パッケージにコピー中...")
        
        for item in self.source_dir.iterdir():
            if item.is_file():
                dest_path = self.final_dir / item.name
                shutil.copy2(item, dest_path)
                copied_files.append(item.name)
                print(f"  ✅ コピー完了: {item.name} ({item.stat().st_size:,} bytes)")
        
        return copied_files
    
    def create_final_launcher(self, copied_files):
        """最終ランチャー作成"""
        print("\n🚀 最終ランチャー作成中...")
        
        launcher_script = f"""@echo off
REM X280最終パッケージランチャー

echo 🚀 X280最終パッケージランチャー起動
echo ==================================

cd /d "{self.final_dir}"

echo 📁 現在のディレクトリ: %cd%
echo 📊 ファイル一覧:
dir

echo.
echo 🌐 ブラウザでHTMLページを開く...
start "" "X280用ダウンロードセンター.html"

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
echo ✅ X280最終パッケージランチャー実行完了
echo 📁 ファイル場所: {self.final_dir}
echo 📋 ファイル数: {len(copied_files)}個
pause
"""
        
        launcher_path = self.final_dir / "X280最終パッケージランチャー.bat"
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_script)
        
        print(f"✅ 最終ランチャー作成完了: {launcher_path.name}")
        return launcher_path
    
    def create_final_readme(self, copied_files):
        """最終README作成"""
        print("\n📋 最終README作成中...")
        
        readme_content = f"""# X280最終パッケージ

## 🎉 完全なX280用PDF変換結果パッケージ

### 📊 ファイル一覧 ({len(copied_files)}個)

#### Excelファイル
"""
        
        for file in copied_files:
            if file.endswith('.xlsx'):
                readme_content += f"- **{file}**\n"
        
        readme_content += """
#### ZIPファイル
"""
        
        for file in copied_files:
            if file.endswith('.zip'):
                readme_content += f"- **{file}**\n"
        
        readme_content += """
#### HTMLファイル
"""
        
        for file in copied_files:
            if file.endswith('.html'):
                readme_content += f"- **{file}**\n"
        
        readme_content += """
#### その他のファイル
"""
        
        for file in copied_files:
            if not file.endswith(('.xlsx', '.zip', '.html')):
                readme_content += f"- **{file}**\n"
        
        readme_content += f"""
## 🚀 使用方法

### 1. ランチャー実行
```
X280最終パッケージランチャー.bat
```

### 2. 個別ファイル開く
- Excelファイル: ダブルクリック
- ZIPファイル: ダブルクリック
- HTMLファイル: ブラウザで開く

### 3. ブラウザで開く
```
X280用ダウンロードセンター.html
```

## 📁 ファイル場所
```
{self.final_dir}
```

## 📋 作成日時
{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

## 🎯 完了状況
✅ X280用パッケージ: 完了
✅ ランチャー: 完了
✅ HTMLダウンロードセンター: 完了
✅ ZIPファイル: 完了
✅ README: 完了

---
X280最終パッケージ - 完全版
"""
        
        readme_path = self.final_dir / "README_X280最終パッケージ.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✅ 最終README作成完了: {readme_path.name}")
        return readme_path
    
    def create_final_zip(self, copied_files):
        """最終ZIPファイル作成"""
        print("\n📦 最終ZIPファイル作成中...")
        
        import zipfile
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"X280最終パッケージ_{timestamp}.zip"
        zip_path = self.final_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in copied_files:
                file_path = self.final_dir / file
                if file_path.exists():
                    zipf.write(file_path, arcname=file)
                    print(f"  📦 ZIP追加: {file}")
        
        print(f"✅ 最終ZIPファイル作成完了: {zip_path.name}")
        print(f"📏 ZIPサイズ: {zip_path.stat().st_size:,} bytes")
        return zip_path
    
    def create_final_report(self, copied_files, launcher_path, readme_path, zip_path):
        """最終レポート作成"""
        print("\n📋 最終レポート作成中...")
        
        report = {
            "final_package_info": {
                "created_at": datetime.now().isoformat(),
                "package_directory": str(self.final_dir),
                "total_files": len(copied_files),
                "status": "completed"
            },
            "files": copied_files,
            "tools": {
                "launcher": launcher_path.name,
                "readme": readme_path.name,
                "zip_file": zip_path.name
            },
            "usage_instructions": {
                "launcher": "X280最終パッケージランチャー.bat を実行",
                "html": "X280用ダウンロードセンター.html をブラウザで開く",
                "individual": "ファイルを個別にダブルクリック"
            }
        }
        
        report_path = self.final_dir / "X280最終パッケージレポート.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 最終レポート作成完了: {report_path.name}")
        return report_path
    
    def run_final_package_creation(self):
        """最終パッケージ作成実行"""
        print("🚀 X280最終パッケージ作成開始")
        print("=" * 60)
        
        # 1. 最終パッケージ作成
        copied_files = self.create_final_package()
        
        # 2. 最終ランチャー作成
        launcher_path = self.create_final_launcher(copied_files)
        
        # 3. 最終README作成
        readme_path = self.create_final_readme(copied_files)
        
        # 4. 最終ZIPファイル作成
        zip_path = self.create_final_zip(copied_files)
        
        # 5. 最終レポート作成
        report_path = self.create_final_report(copied_files, launcher_path, readme_path, zip_path)
        
        print("\n🎉 X280最終パッケージ作成完了！")
        print("=" * 60)
        print(f"📁 最終パッケージ: {self.final_dir}")
        print(f"✅ ファイル数: {len(copied_files)}個")
        print(f"🚀 ランチャー: {launcher_path.name}")
        print(f"📋 README: {readme_path.name}")
        print(f"📦 ZIPファイル: {zip_path.name}")
        print(f"📊 レポート: {report_path.name}")
        print("")
        print("🎯 完了状況:")
        print("✅ X280用パッケージ: 完了")
        print("✅ ランチャー: 完了")
        print("✅ HTMLダウンロードセンター: 完了")
        print("✅ ZIPファイル: 完了")
        print("✅ README: 完了")
        print("✅ レポート: 完了")
        print("")
        print("🚀 使用方法:")
        print("1. フォルダ全体をX280のデスクトップにコピー")
        print("2. X280最終パッケージランチャー.bat を実行")
        print("3. X280用ダウンロードセンター.html をブラウザで開く")
        
        return True

def main():
    """メイン実行関数"""
    package = FinalX280Package()
    success = package.run_final_package_creation()
    
    if success:
        print("\n✅ X280最終パッケージ作成完了！")
        print("📁 X280最終パッケージを確認してください")
    else:
        print("\n❌ X280最終パッケージ作成失敗")

if __name__ == "__main__":
    main()


