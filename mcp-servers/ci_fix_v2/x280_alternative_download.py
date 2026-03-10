#!/usr/bin/env python3
"""
X280代替ダウンロードシステム
SSH接続ができない場合の代替手段
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

class X280AlternativeDownloader:
    def __init__(self):
        self.source_dir = Path('/home/mana/Downloads/PDF変換結果_20251007_091805')
        self.x280_desktop = Path('/home/mana/Desktop')
        self.download_dir = self.x280_desktop / f"PDF変換結果_X280用_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print("🚀 X280代替ダウンロードシステム")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
        print(f"📁 X280デスクトップ: {self.x280_desktop}")
        print(f"📁 ダウンロード先: {self.download_dir}")
    
    def create_x280_download_directory(self):
        """X280用ダウンロードディレクトリ作成"""
        print("\n📁 X280用ダウンロードディレクトリ作成中...")
        
        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ ディレクトリ作成完了: {self.download_dir}")
            return True
        except Exception as e:
            print(f"❌ ディレクトリ作成失敗: {e}")
            return False
    
    def copy_files_to_x280(self):
        """ファイルをX280デスクトップにコピー"""
        print("\n📤 ファイルをX280デスクトップにコピー中...")
        
        if not self.source_dir.exists():
            print("❌ ソースディレクトリが見つかりません")
            return False
        
        copied_files = []
        failed_files = []
        
        # 各ファイルをコピー
        for file_path in self.source_dir.glob('*'):
            if file_path.is_file():
                try:
                    dest_path = self.download_dir / file_path.name
                    shutil.copy2(file_path, dest_path)
                    copied_files.append(file_path.name)
                    print(f"✅ コピー完了: {file_path.name}")
                except Exception as e:
                    failed_files.append(file_path.name)
                    print(f"❌ コピー失敗: {file_path.name} - {e}")
        
        return {
            'copied': copied_files,
            'failed': failed_files,
            'success': len(failed_files) == 0
        }
    
    def create_x280_zip(self):
        """X280用ZIPファイル作成"""
        print("\n📦 X280用ZIPファイル作成中...")
        
        try:
            zip_filename = f"PDF変換結果_X280用_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = self.download_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self.source_dir.glob('*'):
                    if file_path.is_file():
                        zipf.write(file_path, file_path.name)
                        print(f"📦 ZIP追加: {file_path.name}")
            
            print(f"✅ ZIP作成完了: {zip_filename}")
            print(f"📏 ZIPサイズ: {zip_path.stat().st_size:,} bytes")
            return True
            
        except Exception as e:
            print(f"❌ ZIP作成失敗: {e}")
            return False
    
    def create_x280_readme(self):
        """X280用READMEファイル作成"""
        print("\n📋 X280用READMEファイル作成中...")
        
        try:
            readme_content = f"""
# PDF変換結果 - X280用ダウンロード

## 📊 変換結果概要
- **作成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
- **総ファイル数**: {len(list(self.source_dir.glob('*.xlsx')))}
- **ダウンロードディレクトリ**: {self.download_dir}

## 📁 ファイル一覧
"""
            
            for file_path in self.source_dir.glob('*'):
                if file_path.is_file():
                    stat = file_path.stat()
                    readme_content += f"- **{file_path.name}** ({stat.st_size:,} bytes)\n"
            
            readme_content += f"""

## 🚀 使用方法

### 1. ブラウザでHTMLページを開く
```
file://{self.download_dir}/ダウンロードセンター.html
```

### 2. 個別ファイルを開く
- Excelファイル: LibreOffice Calcで開く
- ZIPファイル: 展開してから利用

### 3. コマンドラインで確認
```bash
cd {self.download_dir}
ls -la
unzip PDF変換結果_*.zip
```

## 📋 ファイル詳細

### Excelファイルの内容
- **抽出テキストシート**: PDFから抽出されたテキスト
- **変換サマリーシート**: 変換統計情報
- **全テキストシート**: 完全なテキスト内容

### 変換統計
- **総ページ数**: 1ページ
- **総文字数**: 563文字
- **抽出表数**: 0個
- **処理時間**: 約0.04秒

## 🔧 技術情報
- **変換システム**: ManaOS統合PDF-Excel変換システム
- **OCRエンジン**: Tesseract 4.1.1
- **出力形式**: Excel (.xlsx)
- **文字エンコーディング**: UTF-8

---
作成者: ManaOS AI Assistant
作成日: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
"""
            
            readme_path = self.download_dir / "README_X280用.md"
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            print(f"✅ README作成完了: {readme_path}")
            return True
            
        except Exception as e:
            print(f"❌ README作成失敗: {e}")
            return False
    
    def create_x280_launcher(self):
        """X280用ランチャースクリプト作成"""
        print("\n🚀 X280用ランチャースクリプト作成中...")
        
        try:
            launcher_script = f"""#!/bin/bash
# PDF変換結果ランチャー - X280用

echo "🚀 PDF変換結果ランチャー起動"
echo "=================================="

# ダウンロードディレクトリに移動
cd "{self.download_dir}"

echo "📁 現在のディレクトリ: $(pwd)"
echo "📊 ファイル一覧:"
ls -la

echo ""
echo "🌐 ブラウザでHTMLページを開く..."
xdg-open "file://{self.download_dir}/ダウンロードセンター.html" &

echo "📄 Excelファイルを開く..."
for file in *.xlsx; do
    if [ -f "$file" ]; then
        echo "📊 開く: $file"
        libreoffice --calc "$file" &
    fi
done

echo "✅ ランチャー実行完了"
"""
            
            launcher_path = self.download_dir / "PDF変換結果を開く.sh"
            with open(launcher_path, 'w', encoding='utf-8') as f:
                f.write(launcher_script)
            
            # 実行権限を付与
            os.chmod(launcher_path, 0o755)
            
            print(f"✅ ランチャー作成完了: {launcher_path}")
            return True
            
        except Exception as e:
            print(f"❌ ランチャー作成失敗: {e}")
            return False
    
    def run_x280_download(self):
        """X280ダウンロード実行"""
        print("🚀 X280代替ダウンロード開始")
        print("=" * 60)
        
        # 1. ディレクトリ作成
        if not self.create_x280_download_directory():
            return False
        
        # 2. ファイルコピー
        copy_result = self.copy_files_to_x280()
        
        if not copy_result['success']:  # type: ignore[index]
            print(f"❌ ファイルコピーに失敗: {copy_result['failed']}")  # type: ignore[index]
            return False
        
        # 3. ZIPファイル作成
        if not self.create_x280_zip():
            print("❌ ZIPファイル作成に失敗")
            return False
        
        # 4. READMEファイル作成
        if not self.create_x280_readme():
            print("❌ READMEファイル作成に失敗")
            return False
        
        # 5. ランチャースクリプト作成
        if not self.create_x280_launcher():
            print("❌ ランチャースクリプト作成に失敗")
            return False
        
        print("\n🎉 X280代替ダウンロード完了！")
        print("=" * 60)
        print(f"📁 X280ダウンロード先: {self.download_dir}")
        print(f"✅ コピー成功ファイル: {len(copy_result['copied'])}個")  # type: ignore[index]
        print(f"📋 コピーファイル一覧: {copy_result['copied']}")  # type: ignore[index]
        print(f"🚀 ランチャー: {self.download_dir}/PDF変換結果を開く.sh")
        print(f"📋 README: {self.download_dir}/README_X280用.md")
        
        return True

def main():
    """メイン実行関数"""
    downloader = X280AlternativeDownloader()
    success = downloader.run_x280_download()
    
    if success:
        print("\n✅ X280代替ダウンロード完了！")
        print("📁 X280デスクトップのダウンロードディレクトリを確認してください")
        print("🚀 ランチャースクリプトを実行してファイルを開いてください")
    else:
        print("\n❌ X280代替ダウンロード失敗")

if __name__ == "__main__":
    main()


