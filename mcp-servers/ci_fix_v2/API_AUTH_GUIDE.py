"""
API認証統合ガイド
すべてのManaOS APIサービスに認証を追加する方法
"""

# ================================================
# 📚 目次
# ================================================
# 1. 認証システムの概要
# 2. Flask アプリケーションへの統合
# 3. FastAPI アプリケーションへの統合
# 4. 環境変数の設定
# 5. APIキーの管理
# 6. トラブルシューティング

# ================================================
# 1. 認証システムの概要
# ================================================
"""
ManaOS統一認証システムは以下の機能を提供します：

- APIキーベースの認証
- レート制限（デフォルト: 100リクエスト/60秒）
- 複数APIキーのサポート
- 開発環境用のデフォルトキー
- セキュアなキー生成・ハッシュ化

すべてのManaOS APIサービスで統一された認証を使用することで、
セキュリティの一貫性と管理の簡素化を実現します。
"""

# ================================================
# 2. Flask アプリケーションへの統合
# ================================================

# --- 基本的な統合例 ---
from flask import Flask, jsonify
from api_auth import get_auth_manager

app = Flask(__name__)
auth_manager = get_auth_manager()

# 保護されたエンドポイント（APIキー必須）
@app.route("/api/protected")
@auth_manager.require_api_key
def protected_endpoint():
    return jsonify({"message": "Authenticated successfully"})

# 公開エンドポイント（APIキー不要）
@app.route("/api/public")
def public_endpoint():
    return jsonify({"message": "Public access"})

# オプション認証エンドポイント（キーがあれば検証、なくてもOK）
@app.route("/api/optional")
@auth_manager.optional_api_key
def optional_auth_endpoint():
    from flask import request
    if request.api_key_validated:
        return jsonify({"message": "Authenticated user", "premium": True})
    else:
        return jsonify({"message": "Anonymous user", "premium": False})


# --- 既存サービスへの追加例: Gallery API ---
"""
既存の gallery_api_server.py に認証を追加する場合：

1. インポートを追加:
   from api_auth import get_auth_manager

2. 認証マネージャーを初期化:
   auth_manager = get_auth_manager()

3. 保護したいエンドポイントにデコレーターを追加:
   @app.route("/api/generate")
   @auth_manager.require_api_key  # この行を追加
   def generate_image():
       # 既存のコード...

4. ヘルスチェックは公開のままにする:
   @app.route("/health")  # デコレーターなし
   def health():
       return jsonify({"status": "healthy"})
"""

# ================================================
# 3. FastAPI アプリケーションへの統合
# ================================================

# --- FastAPI統合例 ---
try:
    from fastapi import FastAPI, Depends, HTTPException
    from api_auth import require_api_key_fastapi
    
    app_fastapi = FastAPI()
    verify_api_key = require_api_key_fastapi()
    
    # 保護されたエンドポイント
    @app_fastapi.get("/api/protected")
    async def protected_endpoint_fastapi(api_key: str = Depends(verify_api_key)):
        return {"message": "Authenticated successfully", "api_key": api_key}
    
    # 公開エンドポイント
    @app_fastapi.get("/api/public")
    async def public_endpoint_fastapi():
        return {"message": "Public access"}

except ImportError:
    # FastAPIがインストールされていない場合
    pass


# ================================================
# 4. 環境変数の設定
# ================================================
"""
.env ファイルに以下を追加:

# API認証設定
MANAOS_API_KEYS=manaos_abcdef123456,manaos_xyz789012  # 本番用キー（カンマ区切り）
MANAOS_ENV=production  # production または development

# レート制限設定（オプション）
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100  # リクエスト数
RATE_LIMIT_WINDOW=60     # 時間ウィンドウ（秒）

開発環境での使用:
MANAOS_ENV=development
# developmentモードではデフォルトキー "dev_default_key_DO_NOT_USE_IN_PRODUCTION" が有効
"""

# ================================================
# 5. APIキーの管理
# ================================================

# --- 新しいAPIキーの生成 ---
from api_auth import APIAuthManager

auth_manager = APIAuthManager()

# 新しいキーを生成
new_key = auth_manager.generate_api_key(prefix="manaos")
print(f"新しいAPIキー: {new_key}")

# キーをハッシュ化してデータベースに保存
hashed_key = auth_manager.hash_api_key(new_key)
print(f"ハッシュ化されたキー: {hashed_key}")

# --- APIキーのローテーション手順 ---
"""
1. 新しいキーを生成:
   python -c "from api_auth import APIAuthManager; print(APIAuthManager().generate_api_key())"

2. .env ファイルに新しいキーを追加（古いキーも残す）:
   MANAOS_API_KEYS=old_key,new_key

3. クライアントに新しいキーを配布

4. 移行期間後、古いキーを削除:
   MANAOS_API_KEYS=new_key
"""

# ================================================
# 6. トラブルシューティング
# ================================================
"""
Q: "Invalid or missing API key" エラーが出る
A: 
- 環境変数 MANAOS_API_KEYS が設定されているか確認
- APIキーがヘッダー X-API-Key またはクエリパラメータ api_key で送信されているか確認
- 開発環境の場合、MANAOS_ENV=development が設定されているか確認

Q: "Rate limit exceeded" エラーが出る
A:
- レート制限設定を確認（RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW）
- 必要に応じて制限を緩和するか、無効化（RATE_LIMIT_ENABLED=false）

Q: すべてのエンドポイントに認証を追加すべきか？
A:
- /health, /metrics などの監視エンドポイントは公開のままにすることを推奨
- データ変更やリソース消費の多いエンドポイントは保護すべき
- 公開APIとして提供する場合はオプション認証を検討

Q: 認証なしでテストしたい
A:
- MANAOS_ENV=development を設定
- デフォルトキー "dev_default_key_DO_NOT_USE_IN_PRODUCTION" を使用
- または一時的に @require_api_key デコレーターをコメントアウト
"""

# ================================================
# 7. 既存サービスへの適用チェックリスト
# ================================================
"""
各サービスに認証を追加する際のチェックリスト:

□ api_auth.py を import
□ get_auth_manager() で認証マネージャーを取得
□ 保護すべきエンドポイントに @require_api_key を追加
□ /health, /metrics などの監視エンドポイントは公開のまま
□ .env に MANAOS_API_KEYS を設定
□ ドキュメントに認証方法を記載
□ テストケースに認証テストを追加
□ 既存クライアントコードにAPIキーを追加

優先順位（セキュリティ監査結果より）:
1. gallery_api_server.py - 画像生成API
2. learning_system_api.py - 学習システム
3. video_pipeline_mcp_server.py - 動画パイプライン
4. unified_api_server.py - 統合API
5. その他のAPIサービス
"""
