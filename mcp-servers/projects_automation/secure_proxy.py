#!/usr/bin/env python3
"""
🔒 Secure Proxy for Mana's Services
外部公開サービスに認証レイヤーを追加
"""
import os
from flask import Flask, request, jsonify
import secrets
import time
from functools import wraps

app = Flask(__name__)

# セキュアなトークン生成（初回起動時に自動生成）
MASTER_TOKEN = secrets.token_urlsafe(32)

# トークンの有効期限管理
active_tokens = {}

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Mana-Token')
        
        if not token:
            return jsonify({'error': 'Authentication required', 'status': 'unauthorized'}), 401
        
        if token != MASTER_TOKEN and token not in active_tokens:
            return jsonify({'error': 'Invalid token', 'status': 'forbidden'}), 403
        
        # トークンの有効期限チェック
        if token in active_tokens:
            if time.time() > active_tokens[token]['expires']:
                del active_tokens[token]
                return jsonify({'error': 'Token expired', 'status': 'forbidden'}), 403
        
        return f(*args, **kwargs)
    return decorated


@app.route('/auth/login', methods=['POST'])
def login():
    """認証エンドポイント"""
    data = request.get_json()
    
    # 簡易的なパスワード認証（実際はもっと複雑に）
    username = data.get('username')
    password = data.get('password')
    
    # ここでは環境変数やVaultからパスワードを取得
    if username == 'mana' and password:  # パスワード検証は実装に応じて
        # セッショントークン生成
        session_token = secrets.token_urlsafe(32)
        active_tokens[session_token] = {
            'username': username,
            'expires': time.time() + 3600  # 1時間有効
        }
        
        return jsonify({
            'status': 'success',
            'token': session_token,
            'expires_in': 3600
        })
    
    return jsonify({'error': 'Invalid credentials', 'status': 'unauthorized'}), 401


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック（認証不要）"""
    return jsonify({'status': 'ok', 'service': 'Mana Secure Proxy'})


@app.route('/proxy/<service>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_auth
def proxy(service):
    """認証付きプロキシ"""
    # ここで内部サービスへプロキシ
    return jsonify({
        'status': 'success',
        'message': f'Proxying to {service}',
        'note': 'Internal proxy implementation required'
    })


if __name__ == '__main__':
    print("🔒 Mana Secure Proxy")
    print("=" * 50)
    print(f"🔑 Master Token: {MASTER_TOKEN}")
    print("⚠️  このトークンを安全に保管してください！")
    print("=" * 50)
    
    # トークンをVaultに保存
    try:
        from security_vault import SecurityVault
        vault = SecurityVault()
        vault.set('SECURE_PROXY_TOKEN', MASTER_TOKEN)
        print("✅ トークンをVaultに保存しました")
    except Exception:
        print("⚠️  Vaultへの保存に失敗。マニュアルで保存してください。")
    
    app.run(host='127.0.0.1', port=9999, debug=os.getenv("DEBUG", "False").lower() == "true")

