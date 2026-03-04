#!/usr/bin/env python3
"""
Google Drive Sync
生成された画像をGoogle Driveに同期
"""

import os
import json
from pathlib import Path
from datetime import datetime
import subprocess
import time

class GoogleDriveSync:
    def __init__(self):
        self.images_dir = Path("/root/trinity_workspace/generated_images")
        self.gdrive_dir = Path("/root/GoogleDrive/Trinity_AI_Images")
        self.gdrive_dir.mkdir(parents=True, exist_ok=True)
        
        # 同期設定
        self.sync_config = {
            "last_sync": None,
            "synced_files": [],
            "sync_interval_hours": 1
        }
        
        self.config_file = Path("/root/trinity_workspace/sync_config.json")
        self.load_config()
    
    def load_config(self):
        """設定読み込み"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.sync_config = json.load(f)
            except:
                pass
    
    def save_config(self):
        """設定保存"""
        with open(self.config_file, 'w') as f:
            json.dump(self.sync_config, f, indent=2)
    
    def setup_google_drive(self):
        """Google Drive設定"""
        print("🌐 Google Drive 設定中...")
        
        # rclone設定確認
        try:
            result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True)
            if 'gdrive:' in result.stdout:
                print("✅ Google Drive 接続確認済み")
                return True
            else:
                print("❌ Google Drive 接続が見つかりません")
                print("rclone config でGoogle Driveを設定してください")
                return False
        except FileNotFoundError:
            print("❌ rclone がインストールされていません")
            print("rclone をインストールしてGoogle Driveを設定してください")
            return False
    
    def sync_to_google_drive(self):
        """Google Driveに同期"""
        print("📤 Google Drive 同期開始")
        print("=" * 60)
        
        if not self.setup_google_drive():
            return False
        
        # 新しい画像を検索
        new_images = self.find_new_images()
        
        if not new_images:
            print("📭 新しい画像がありません")
            return True
        
        print(f"📸 新しい画像: {len(new_images)}枚")
        
        # 各画像をGoogle Driveにアップロード
        success_count = 0
        for image_path in new_images:
            print(f"\n📤 アップロード中: {image_path.name}")
            
            if self.upload_to_gdrive(image_path):
                success_count += 1
                self.sync_config["synced_files"].append(str(image_path))
                print(f"✅ アップロード完了")
            else:
                print(f"❌ アップロード失敗")
        
        # 設定更新
        self.sync_config["last_sync"] = datetime.now().isoformat()
        self.save_config()
        
        print(f"\n🎉 同期完了: {success_count}/{len(new_images)} 成功")
        return success_count == len(new_images)
    
    def find_new_images(self):
        """新しい画像を検索"""
        new_images = []
        
        if not self.images_dir.exists():
            return new_images
        
        for image_file in self.images_dir.glob("*.png"):
            if not image_file.name.endswith('.backup'):
                # 既に同期済みかチェック
                if str(image_file) not in self.sync_config["synced_files"]:
                    new_images.append(image_file)
        
        # 作成日時順でソート
        new_images.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return new_images
    
    def upload_to_gdrive(self, image_path):
        """単一画像をGoogle Driveにアップロード"""
        try:
            # リモートパス設定
            remote_path = f"gdrive:Trinity_AI_Images/{image_path.name}"
            
            # rclone でアップロード
            result = subprocess.run([
                'rclone', 'copy', str(image_path), remote_path,
                '--progress', '--transfers', '1'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return True
            else:
                print(f"❌ アップロードエラー: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ アップロードエラー: {str(e)}")
            return False
    
    def create_gdrive_gallery(self):
        """Google Drive用ギャラリーHTML作成"""
        print("🌐 Google Drive ギャラリー作成中...")
        
        # 画像一覧取得
        images = []
        if self.images_dir.exists():
            for image_file in self.images_dir.glob("*.png"):
                if not image_file.name.endswith('.backup'):
                    stat = image_file.stat()
                    images.append({
                        "name": image_file.name,
                        "size_mb": stat.st_size / (1024 * 1024),
                        "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        # HTML生成
        gallery_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trinity AI Images - Google Drive</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
        }}
        .stats {{
            background: #e9ecef;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .image-card {{
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .image-card:hover {{
            transform: translateY(-5px);
        }}
        .image-card img {{
            width: 100%;
            height: 300px;
            object-fit: cover;
        }}
        .image-info {{
            padding: 15px;
            background: #f8f9fa;
        }}
        .image-name {{
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        .image-details {{
            font-size: 0.9em;
            color: #666;
        }}
        .sync-info {{
            background: #d4edda;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #28a745;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 Trinity AI Images</h1>
        
        <div class="sync-info">
            <h3>📤 Google Drive 同期情報</h3>
            <p>最終同期: {self.sync_config.get('last_sync', '未同期')}</p>
            <p>同期済みファイル: {len(self.sync_config.get('synced_files', []))}個</p>
        </div>
        
        <div class="stats">
            <h3>📊 画像統計</h3>
            <p>総画像数: {len(images)}枚</p>
            <p>総サイズ: {sum(img['size_mb'] for img in images):.1f}MB</p>
        </div>
        
        <div class="gallery">
            {self._generate_image_cards(images)}
        </div>
    </div>
</body>
</html>
        """
        
        # HTMLファイル保存
        gallery_path = self.gdrive_dir / "gallery.html"
        with open(gallery_path, 'w', encoding='utf-8') as f:
            f.write(gallery_html)
        
        print(f"✅ Google Drive ギャラリー作成完了: {gallery_path}")
        return str(gallery_path)
    
    def _generate_image_cards(self, images):
        """画像カードHTML生成"""
        cards_html = ""
        
        for image in images:
            cards_html += f"""
            <div class="image-card">
                <img src="{image['name']}" alt="{image['name']}">
                <div class="image-info">
                    <div class="image-name">{image['name']}</div>
                    <div class="image-details">
                        サイズ: {image['size_mb']:.1f}MB<br>
                        作成日時: {image['created'][:19]}
                    </div>
                </div>
            </div>
            """
        
        return cards_html
    
    def get_sync_status(self):
        """同期状況表示"""
        print("📤 Google Drive 同期状況")
        print("=" * 60)
        
        print(f"最終同期: {self.sync_config.get('last_sync', '未同期')}")
        print(f"同期済みファイル: {len(self.sync_config.get('synced_files', []))}個")
        
        # 新しい画像数
        new_images = self.find_new_images()
        print(f"新しい画像: {len(new_images)}枚")
        
        if new_images:
            print("新しい画像一覧:")
            for image in new_images[:5]:  # 最新5枚
                print(f"  📸 {image.name}")


def main():
    """メイン関数"""
    sync = GoogleDriveSync()
    
    print("🌐 Google Drive Sync")
    print("=" * 60)
    
    # 同期状況表示
    sync.get_sync_status()
    
    # Google Drive設定確認
    if sync.setup_google_drive():
        # 同期実行
        sync.sync_to_google_drive()
        
        # ギャラリー作成
        sync.create_gdrive_gallery()
    else:
        print("❌ Google Drive 設定が必要です")
        print("1. rclone をインストール")
        print("2. rclone config でGoogle Driveを設定")
        print("3. 再度実行してください")


if __name__ == "__main__":
    main()


