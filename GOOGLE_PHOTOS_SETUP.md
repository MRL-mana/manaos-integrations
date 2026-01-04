# Google Photos API セットアップガイド

## 概要
Google Photos APIを使用して、まなアカウントのGoogle Photosにアクセスするための設定手順です。

## 必要な準備

### 1. Google Cloud Consoleでの設定

#### ステップ1: プロジェクトの作成
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
3. プロジェクト名を設定（例: "ManaOS-Photos"）

#### ステップ2: Google Photos Library APIの有効化
1. 左側メニューから「APIとサービス」→「ライブラリ」を選択
2. 「Google Photos Library API」を検索
3. 「有効にする」をクリック

#### ステップ3: OAuth 2.0認証情報の作成
1. 「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「OAuth クライアント ID」を選択
3. アプリケーションの種類: 「デスクトップアプリ」を選択
4. 名前を設定（例: "ManaOS Photos Client"）
5. 「作成」をクリック
6. 表示された認証情報をダウンロード（JSON形式）
7. ダウンロードしたファイルを `credentials.json` として保存

#### ステップ4: OAuth同意画面の設定
1. 「OAuth同意画面」を選択
2. ユーザータイプ: 「外部」を選択（個人アカウントの場合）
3. アプリ名、ユーザーサポートメール、デベロッパーの連絡先情報を入力
4. スコープを追加:
   - `https://www.googleapis.com/auth/photoslibrary.readonly`
   - `https://www.googleapis.com/auth/photoslibrary.appendonly`
   - `https://www.googleapis.com/auth/photoslibrary.sharing`
5. テストユーザーに自分のGoogleアカウントを追加（開発中の場合）

### 2. 認証情報ファイルの配置

1. ダウンロードした `credentials.json` を以下の場所に配置:
   - `C:\Users\mana4\OneDrive\Desktop\credentials.json`
   - または `manaos_integrations/credentials.json`

### 3. 初回認証の実行

以下のコマンドを実行して認証を開始:

```bash
cd "C:\Users\mana4\OneDrive\Desktop"
python manaos_integrations/google_photos_integration.py
```

初回実行時:
1. ブラウザが自動的に開きます
2. Googleアカウントでログイン
3. アプリへのアクセス許可を承認
4. 認証が完了すると `token_photos.json` が作成されます

## 使用方法

### 基本的な使用例

```python
from manaos_integrations.google_photos_integration import GooglePhotosIntegration

# 初期化
photos = GooglePhotosIntegration()

# 利用可能かチェック
if photos.is_available():
    # アルバム一覧を取得
    albums = photos.list_albums()
    print(f"アルバム数: {len(albums.get('albums', []))}")
    
    # 最近の写真を取得
    media = photos.list_media_items(page_size=10)
    print(f"写真数: {len(media.get('mediaItems', []))}")
```

### 主な機能

1. **アルバム一覧の取得**
   ```python
   albums = photos.list_albums()
   ```

2. **写真・動画の一覧取得**
   ```python
   media_items = photos.list_media_items(page_size=50)
   ```

3. **特定のアルバムの写真を取得**
   ```python
   album_media = photos.get_album_media_items(album_id="YOUR_ALBUM_ID")
   ```

4. **写真を検索**
   ```python
   # 日付範囲で検索
   filters = {
       'dateFilter': {
           'ranges': [{
               'startDate': {'year': 2024, 'month': 1, 'day': 1},
               'endDate': {'year': 2024, 'month': 12, 'day': 31}
           }]
       }
   }
   results = photos.search_media_items(filters=filters)
   ```

## トラブルシューティング

### 認証エラーが発生する場合
- `credentials.json` が正しい場所にあるか確認
- Google Photos Library APIが有効になっているか確認
- OAuth同意画面でスコープが正しく設定されているか確認

### アクセス権限エラーが発生する場合
- テストユーザーに自分のアカウントが追加されているか確認（開発中の場合）
- OAuth同意画面で公開済みになっているか確認（本番環境の場合）

### トークンの有効期限切れ
- `token_photos.json` を削除して再認証
- または、自動的にリフレッシュされるはずですが、問題がある場合は再認証

## 注意事項

- Google Photos Library APIは有料プランがあります（無料枠あり）
- 大量の写真を取得する場合は、レート制限に注意
- プライバシーに配慮して、必要な権限のみを要求

## 参考リンク

- [Google Photos Library API ドキュメント](https://developers.google.com/photos/library/guides/overview)
- [OAuth 2.0 設定ガイド](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)


















