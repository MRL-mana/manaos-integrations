#!/usr/bin/env python3
"""
X280直接転送システム
現在操作中のX280に直接ファイルを転送
"""

import shutil
from pathlib import Path
from datetime import datetime

class DirectX280Transfer:
    def __init__(self):
        self.source_dir = Path('/home/mana/Desktop/X280デスクトップ用_20251007_094645')
        self.x280_desktop = Path('/home/mana/Desktop')  # X280のデスクトップを想定
        
        print("🚀 X280直接転送システム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
        print("📱 転送先: X280のデスクトップ")
    
    def create_x280_desktop_folder(self):
        """X280デスクトップ用フォルダ作成"""
        print("\n📁 X280デスクトップ用フォルダ作成中...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        x280_folder = self.x280_desktop / f"PDF変換結果_X280用_{timestamp}"
        x280_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ X280用フォルダ作成完了: {x280_folder}")
        return x280_folder
    
    def copy_files_to_x280(self, x280_folder):
        """ファイルをX280フォルダにコピー"""
        print("\n📤 ファイルをX280フォルダにコピー中...")
        
        copied_files = []
        failed_files = []
        
        # ソースディレクトリの全ファイルをコピー
        for item in self.source_dir.iterdir():
            if item.is_file():
                try:
                    dest_path = x280_folder / item.name
                    shutil.copy2(item, dest_path)
                    copied_files.append(item.name)
                    print(f"  ✅ コピー完了: {item.name} ({item.stat().st_size:,} bytes)")
                except Exception as e:
                    failed_files.append(item.name)
                    print(f"  ❌ コピー失敗: {item.name} - {e}")
        
        return copied_files, failed_files
    
    def create_x280_launcher(self, x280_folder):
        """X280用ランチャー作成"""
        print("\n🚀 X280用ランチャー作成中...")
        
        launcher_script = f"""@echo off
REM X280用PDF変換結果ランチャー

echo 🚀 X280 PDF変換結果ランチャー起動
echo ==================================

cd /d "{x280_folder}"

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
echo 📁 ファイル場所: {x280_folder}
pause
"""
        
        launcher_path = x280_folder / "X280用PDF変換結果を開く.bat"
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_script)
        
        print(f"✅ X280用ランチャー作成完了: {launcher_path}")
        return launcher_path
    
    def create_x280_readme(self, x280_folder, copied_files):
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
{x280_folder}
```

## 📋 作成日時
{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

---
X280デスクトップ用PDF変換結果パッケージ
"""
        
        readme_path = x280_folder / "README_X280用.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✅ X280用README作成完了: {readme_path}")
        return readme_path
    
    def create_x280_zip(self, x280_folder):
        """X280用ZIPファイル作成"""
        print("\n📦 X280用ZIPファイル作成中...")
        
        import zipfile
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"PDF変換結果_X280用_{timestamp}.zip"
        zip_path = x280_folder / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in x280_folder.glob('*'):
                if file_path.is_file() and file_path.name != zip_filename:
                    zipf.write(file_path, arcname=file_path.name)
                    print(f"  📦 ZIP追加: {file_path.name}")
        
        print(f"✅ X280用ZIPファイル作成完了: {zip_path.name}")
        print(f"📏 ZIPサイズ: {zip_path.stat().st_size:,} bytes")
        return zip_path
    
    def create_x280_html(self, x280_folder, copied_files):
        """X280用HTMLダウンロードページ作成"""
        print("\n🌐 X280用HTMLダウンロードページ作成中...")
        
        html_content = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>X280用PDF変換結果 ダウンロードセンター</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .content {
            padding: 30px;
        }
        .file-list {
            display: grid;
            gap: 15px;
            margin: 20px 0;
        }
        .file-item {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .file-info h3 {
            margin: 0 0 5px 0;
            color: #333;
        }
        .file-info p {
            margin: 0;
            color: #666;
            font-size: 14px;
        }
        .download-btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .download-btn:hover {
            background: #0056b3;
        }
        .launcher {
            background: #28a745;
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            margin: 20px 0;
        }
        .launcher h2 {
            margin: 0 0 10px 0;
        }
        .launcher p {
            margin: 0;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 X280用PDF変換結果 ダウンロードセンター</h1>
            <p>PDF変換結果ファイルのダウンロードと管理</p>
        </div>
        
        <div class="content">
            <div class="launcher">
                <h2>🚀 ランチャー実行</h2>
                <p>X280用PDF変換結果を開く.bat をダブルクリックして実行してください</p>
            </div>
            
            <h2>📊 ファイル一覧</h2>
            <div class="file-list">
"""
        
        for file in copied_files:
            file_size = (x280_folder / file).stat().st_size if (x280_folder / file).exists() else 0
            html_content += f"""
                <div class="file-item">
                    <div class="file-info">
                        <h3>{file}</h3>
                        <p>サイズ: {file_size:,} bytes</p>
                    </div>
                    <a href="{file}" class="download-btn" download>📥 ダウンロード</a>
                </div>
"""
        
        html_content += f"""
            </div>
            
            <div class="launcher">
                <h2>📋 使用方法</h2>
                <p>1. ランチャーを実行: X280用PDF変換結果を開く.bat</p>
                <p>2. 個別ファイル: ダブルクリックで開く</p>
                <p>3. ファイル場所: {x280_folder}</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        html_path = x280_folder / "X280用ダウンロードセンター.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ X280用HTMLダウンロードページ作成完了: {html_path.name}")
        return html_path
    
    def run_direct_transfer(self):
        """直接転送実行"""
        print("🚀 X280直接転送システム開始")
        print("=" * 60)
        
        # 1. X280デスクトップ用フォルダ作成
        x280_folder = self.create_x280_desktop_folder()
        
        # 2. ファイルをX280フォルダにコピー
        copied_files, failed_files = self.copy_files_to_x280(x280_folder)
        
        if failed_files:
            print(f"⚠️ コピー失敗ファイル: {failed_files}")
        
        # 3. X280用ランチャー作成
        launcher_path = self.create_x280_launcher(x280_folder)
        
        # 4. X280用README作成
        readme_path = self.create_x280_readme(x280_folder, copied_files)
        
        # 5. X280用ZIPファイル作成
        zip_path = self.create_x280_zip(x280_folder)
        
        # 6. X280用HTMLダウンロードページ作成
        html_path = self.create_x280_html(x280_folder, copied_files)
        
        print("\n🎉 X280直接転送完了！")
        print("=" * 60)
        print(f"📁 X280用フォルダ: {x280_folder}")
        print(f"✅ コピー成功ファイル: {len(copied_files)}個")
        print(f"📋 コピーファイル一覧: {copied_files}")
        print(f"🚀 ランチャー: {launcher_path.name}")
        print(f"📋 README: {readme_path.name}")
        print(f"📦 ZIPファイル: {zip_path.name}")
        print(f"🌐 HTMLページ: {html_path.name}")
        print("")
        print("🚀 使用方法:")
        print("1. X280用フォルダをX280のデスクトップにコピー")
        print("2. X280用PDF変換結果を開く.bat を実行")
        print("3. X280用ダウンロードセンター.html をブラウザで開く")
        
        return True

def main():
    """メイン実行関数"""
    transfer = DirectX280Transfer()
    success = transfer.run_direct_transfer()
    
    if success:
        print("\n✅ X280直接転送完了！")
        print("📁 X280用フォルダを確認してください")
    else:
        print("\n❌ X280直接転送失敗")

if __name__ == "__main__":
    main()


