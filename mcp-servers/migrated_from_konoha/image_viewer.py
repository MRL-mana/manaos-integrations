#!/usr/bin/env python3
"""
Image Viewer
生成された画像を表示・管理するツール
"""

import os
import base64
from pathlib import Path
from datetime import datetime
import subprocess

class ImageViewer:
    def __init__(self):
        self.images_dir = Path("/root/trinity_workspace/generated_images")
        self.storage_dir = Path("/mnt/storage500/trinity_images")
        
    def list_images(self):
        """画像一覧表示"""
        print("🖼️ 生成された画像一覧")
        print("=" * 60)
        
        if not self.images_dir.exists():
            print("❌ 画像ディレクトリが存在しません")
            return []
        
        image_files = list(self.images_dir.glob("*.png"))
        
        if not image_files:
            print("❌ 生成された画像がありません")
            return []
        
        # 最新順でソート
        image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        images = []
        for i, image_file in enumerate(image_files, 1):
            size_mb = image_file.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(image_file.stat().st_mtime)
            
            image_info = {
                "name": image_file.name,
                "path": str(image_file),
                "size_mb": size_mb,
                "created": mtime,
                "index": i
            }
            images.append(image_info)
            
            print(f"{i:2d}. {image_file.name}")
            print(f"    サイズ: {size_mb:.1f}MB")
            print(f"    作成日時: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        
        return images
    
    def show_image_info(self, image_path):
        """画像情報表示"""
        if not os.path.exists(image_path):
            print(f"❌ 画像が見つかりません: {image_path}")
            return
        
        print(f"📸 画像情報: {os.path.basename(image_path)}")
        print("-" * 40)
        
        # ファイル情報
        stat = os.stat(image_path)
        size_mb = stat.st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        
        print(f"ファイル名: {os.path.basename(image_path)}")
        print(f"サイズ: {size_mb:.1f}MB")
        print(f"作成日時: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"フルパス: {image_path}")
        
        # 画像詳細情報
        try:
            result = subprocess.run(['file', image_path], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"画像形式: {result.stdout.strip()}")
        except:
            print("画像形式: 不明")
        
        # 画像サイズ取得
        try:
            result = subprocess.run(['identify', image_path], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"画像サイズ: {result.stdout.strip()}")
        except:
            print("画像サイズ: 不明")
    
    def create_ascii_art(self, image_path, width=80):
        """ASCII アート生成"""
        try:
            # jp2a を使用してASCII アート生成
            result = subprocess.run([
                'jp2a', '--width', str(width), '--colors', image_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout
            else:
                return "ASCII アート生成に失敗しました"
        except FileNotFoundError:
            return "jp2a がインストールされていません"
        except Exception as e:
            return f"ASCII アート生成エラー: {str(e)}"
    
    def show_ascii_preview(self, image_path):
        """ASCII プレビュー表示"""
        print(f"🎨 ASCII プレビュー: {os.path.basename(image_path)}")
        print("-" * 40)
        
        ascii_art = self.create_ascii_art(image_path, width=60)
        print(ascii_art)
    
    def move_to_storage(self, image_path, create_backup=True):
        """画像を追加ストレージに移動"""
        if not os.path.exists(image_path):
            print(f"❌ 画像が見つかりません: {image_path}")
            return False
        
        # ストレージディレクトリ作成
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 移動先パス
        filename = os.path.basename(image_path)
        destination = self.storage_dir / filename
        
        try:
            # バックアップ作成
            if create_backup:
                backup_path = self.images_dir / f"{filename}.backup"
                subprocess.run(['cp', image_path, str(backup_path)], check=True)
                print(f"📦 バックアップ作成: {backup_path}")
            
            # 移動実行
            subprocess.run(['mv', image_path, str(destination)], check=True)
            print(f"✅ 移動完了: {destination}")
            
            # シンボリックリンク作成（元の場所からアクセス可能）
            subprocess.run(['ln', '-s', str(destination), image_path], check=True)
            print(f"🔗 シンボリックリンク作成: {image_path}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 移動エラー: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ 予期しないエラー: {str(e)}")
            return False
    
    def move_all_to_storage(self):
        """全画像を追加ストレージに移動"""
        print("📦 全画像を追加ストレージに移動中...")
        print("=" * 60)
        
        images = self.list_images()
        
        if not images:
            print("❌ 移動する画像がありません")
            return
        
        success_count = 0
        for image in images:
            print(f"\n📸 移動中: {image['name']}")
            if self.move_to_storage(image['path']):
                success_count += 1
                print(f"✅ 移動成功")
            else:
                print(f"❌ 移動失敗")
        
        print(f"\n🎉 移動完了: {success_count}/{len(images)} 成功")
    
    def get_storage_status(self):
        """ストレージ状況表示"""
        print("💾 ストレージ状況")
        print("=" * 60)
        
        # 元のディレクトリ
        if self.images_dir.exists():
            original_images = list(self.images_dir.glob("*.png"))
            original_size = sum(img.stat().st_size for img in original_images) / (1024 * 1024)
            print(f"📁 元ディレクトリ: {len(original_images)}枚, {original_size:.1f}MB")
        else:
            print("📁 元ディレクトリ: 存在しません")
        
        # ストレージディレクトリ
        if self.storage_dir.exists():
            storage_images = list(self.storage_dir.glob("*.png"))
            storage_size = sum(img.stat().st_size for img in storage_images) / (1024 * 1024)
            print(f"📁 ストレージ: {len(storage_images)}枚, {storage_size:.1f}MB")
        else:
            print("📁 ストレージ: 存在しません")
        
        # ディスク使用量
        try:
            result = subprocess.run(['df', '-h', '/mnt/storage500'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    print(f"\n💿 追加ストレージ: {lines[1]}")
        except:
            pass


def main():
    """メイン関数"""
    viewer = ImageViewer()
    
    print("🖼️ Trinity AI Image Viewer")
    print("=" * 60)
    
    # 画像一覧表示
    images = viewer.list_images()
    
    if images:
        print(f"\n📊 画像統計:")
        total_size = sum(img['size_mb'] for img in images)
        print(f"総画像数: {len(images)}")
        print(f"総サイズ: {total_size:.1f}MB")
        
        # 最新画像の詳細表示
        latest_image = images[0]
        print(f"\n📸 最新画像詳細:")
        viewer.show_image_info(latest_image['path'])
        
        # ASCII プレビュー
        print(f"\n🎨 ASCII プレビュー:")
        viewer.show_ascii_preview(latest_image['path'])
        
        # ストレージ状況
        print(f"\n💾 ストレージ状況:")
        viewer.get_storage_status()
        
        # 移動オプション
        print(f"\n💡 追加ストレージへの移動:")
        print("全画像を追加ストレージに移動しますか？ (y/N)")
        # 自動で移動実行
        viewer.move_all_to_storage()


if __name__ == "__main__":
    main()