"""
Google Photos API接続確認スクリプト
認証情報が設定されているか、アクセス可能かを確認します
"""

import os
import sys
from pathlib import Path

# Windowsコンソールの文字コード設定
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def check_credentials():
    """認証情報ファイルの存在を確認"""
    print("=" * 60)
    print("Google Photos API 接続確認")
    print("=" * 60)
    
    # 認証情報ファイルのパス候補
    credential_paths = [
        Path("credentials.json"),
        Path("manaos_integrations/credentials.json"),
        Path(__file__).parent / "credentials.json",
    ]
    
    credentials_found = False
    for path in credential_paths:
        if path.exists():
            print(f"[OK] 認証情報ファイルが見つかりました: {path}")
            credentials_found = True
            break
    
    if not credentials_found:
        print("[NG] 認証情報ファイルが見つかりません")
        print("\n認証情報ファイル（credentials.json）を以下のいずれかの場所に配置してください:")
        for path in credential_paths:
            print(f"  - {path.absolute()}")
        print("\n設定手順は GOOGLE_PHOTOS_SETUP.md を参照してください")
        return False
    
    # トークンファイルの確認
    token_paths = [
        Path("token_photos.json"),
        Path("manaos_integrations/token_photos.json"),
        Path(__file__).parent / "token_photos.json",
    ]
    
    token_found = False
    for path in token_paths:
        if path.exists():
            print(f"[OK] トークンファイルが見つかりました: {path}")
            token_found = True
            break
    
    if not token_found:
        print("[WARN] トークンファイルが見つかりません（初回認証が必要）")
    
    return True


def test_connection():
    """実際にAPI接続をテスト"""
    print("\n" + "=" * 60)
    print("API接続テスト")
    print("=" * 60)
    
    try:
        from google_photos_integration import GooglePhotosIntegration
        
        photos = GooglePhotosIntegration()
        
        if not photos.is_available():
            print("[NG] Google Photos APIが利用できません")
            print("認証情報を確認してください")
            return False
        
        print("[OK] 認証成功")
        
        # アルバム一覧を取得してみる
        print("\nアルバム一覧を取得中...")
        albums_response = photos.list_albums(page_size=5)
        albums = albums_response.get('albums', [])
        
        if albums:
            print(f"[OK] アルバム数: {len(albums)}")
            print("\nアルバム一覧:")
            for album in albums[:5]:
                title = album.get('title', 'Unknown')
                album_id = album.get('id', 'Unknown')
                print(f"  - {title}")
        else:
            print("[WARN] アルバムが見つかりませんでした")
        
        # 最近のメディアを取得してみる
        print("\n最近のメディアを取得中...")
        media_response = photos.list_media_items(page_size=5)
        media_items = media_response.get('mediaItems', [])
        
        if media_items:
            print(f"[OK] メディア数: {len(media_items)}")
            print("\n最近のメディア:")
            for item in media_items[:5]:
                filename = item.get('filename', 'Unknown')
                mime_type = item.get('mimeType', 'Unknown')
                print(f"  - {filename} ({mime_type})")
        else:
            print("[WARN] メディアが見つかりませんでした")
        
        print("\n" + "=" * 60)
        print("[OK] Google Photos APIへの接続が正常に動作しています")
        print("=" * 60)
        return True
        
    except ImportError as e:
        print(f"[NG] 必要なライブラリがインストールされていません: {e}")
        print("\n以下のコマンドでインストールしてください:")
        print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return False
    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        print("\nトラブルシューティング:")
        print("1. credentials.jsonが正しい場所にあるか確認")
        print("2. Google Photos Library APIが有効になっているか確認")
        print("3. OAuth同意画面の設定を確認")
        return False


def main():
    """メイン関数"""
    # 認証情報の確認
    if not check_credentials():
        sys.exit(1)
    
    # 接続テスト
    if not test_connection():
        sys.exit(1)


if __name__ == "__main__":
    main()

