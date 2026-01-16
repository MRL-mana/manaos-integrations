# ManaOS 外部公開時のリスク分析

**作成日時**: 2025-01-28  
**対象**: ManaOS v1.1

---

## ⚠️ 外部公開した場合の具体的な影響

### 🔴 重大なセキュリティリスク

#### 1. **誰でもAPIにアクセス可能**

現在の状態：
- **認証なし** - 誰でもAPIを呼び出せる
- **認可なし** - 権限チェックなし
- **CORS全開放** - すべてのオリジンからアクセス可能

**具体的な攻撃シナリオ**：

```bash
# 悪意のあるユーザーが任意のIPから実行可能
curl -X POST http://your-server:5106/api/execute \
  -H "Content-Type: application/json" \
  -d '{"text": "画像を生成して", "mode": "creative"}'

# 誰でもタスクを実行できる
curl -X POST http://your-server:5104/api/enqueue \
  -H "Content-Type: application/json" \
  -d '{"task_type": "image_generation", "priority": "urgent"}'

# 誰でも商品化APIを呼び出せる
curl -X POST http://your-server:5118/api/auto-productize
```

#### 2. **リソースの無制限消費**

**問題点**：
- レート制限が不十分（Task Queueのみ）
- IPベースの制限なし
- 同時実行数の制限なし

**攻撃例**：
```bash
# 1000リクエストを同時に送信
for i in {1..1000}; do
  curl -X POST http://your-server:5106/api/execute \
    -d '{"text": "画像を生成して"}' &
done
```

**影響**：
- CPU/メモリの枯渇
- GPUリソースの独占
- データベースの負荷増加
- 正常なユーザーへの影響

#### 3. **機密情報の漏洩リスク**

**現在の脆弱性**：
- HTTP通信（暗号化なし）
- ログに機密情報が含まれる可能性
- データベースファイルへの直接アクセス（設定次第）

**漏洩される可能性のある情報**：
- 実行履歴
- 生成されたコンテンツ
- システム内部情報
- ログファイル

#### 4. **不正なコマンド実行**

**リスク**：
- Executor Enhanced (5107) がコマンド実行可能
- スクリプト実行機能あり
- n8nワークフロー実行可能

**攻撃例**：
```json
{
  "text": "システムファイルを削除して",
  "mode": "work"
}
```

→ Task Plannerが悪意のある計画を作成
→ Executorが実行
→ システム破壊の可能性

#### 5. **データベースへの不正アクセス**

**現在の状態**：
- SQLiteデータベースファイルが直接アクセス可能な場所にある可能性
- バックアップファイルへのアクセス

**影響**：
- データの改ざん
- データの削除
- 個人情報の漏洩

---

## 📊 外部公開時の具体的な被害想定

### シナリオ1: DDoS攻撃

**攻撃**：
- 1000リクエスト/秒でAPIにアクセス
- 画像生成タスクを大量に実行

**影響**：
- サーバーが応答不能
- GPUリソースの枯渇
- 正常なユーザーが使用不可
- 電気代の増加

### シナリオ2: データ窃取

**攻撃**：
- 実行履歴APIにアクセス
- 生成コンテンツを取得
- データベースファイルをダウンロード

**影響**：
- 機密情報の漏洩
- プライバシーの侵害
- 知的財産の流出

### シナリオ3: システム破壊

**攻撃**：
- 悪意のあるコマンドを実行
- システムファイルを削除
- 設定ファイルを改ざん

**影響**：
- システムの停止
- データの損失
- 復旧に時間がかかる

### シナリオ4: 不正な課金

**攻撃**：
- 大量のAPIリクエスト
- 外部API（有料）の呼び出し
- クラウドサービスの利用

**影響**：
- 予想外のコスト発生
- 課金の増加
- 予算の超過

---

## 🛡️ 外部公開前に必要な対策

### 必須対策（外部公開時）

#### 1. **API認証の実装**

```python
# 実装例：APIキー認証
from functools import wraps
from flask import request, jsonify

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('MANAOS_API_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/execute', methods=['POST'])
@require_api_key
def execute():
    # ...
```

#### 2. **HTTPSの使用**

```nginx
# nginx設定例
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5106;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 3. **IPベースのレート制限**

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/api/execute', methods=['POST'])
@limiter.limit("10 per minute")
@require_api_key
def execute():
    # ...
```

#### 4. **CORS設定の制限**

```python
from flask_cors import CORS

# 特定のオリジンのみ許可
CORS(app, origins=["https://your-domain.com"])
```

#### 5. **入力検証の強化**

```python
from marshmallow import Schema, fields, validate

class ExecuteRequestSchema(Schema):
    text = fields.Str(required=True, validate=validate.Length(max=1000))
    mode = fields.Str(validate=validate.OneOf(["work", "creative", "fun", "auto"]))

@app.route('/api/execute', methods=['POST'])
@require_api_key
def execute():
    schema = ExecuteRequestSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': err.messages}), 400
    # ...
```

#### 6. **ログの機密情報マスキング**

```python
import re

def mask_sensitive_data(text):
    # APIキーをマスキング
    text = re.sub(r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\']+)', 
                  r'api_key="***"', text, flags=re.IGNORECASE)
    return text

logger.info(mask_sensitive_data(f"Request: {request.json}"))
```

---

## 📋 外部公開時のチェックリスト

### セキュリティ

- [ ] API認証の実装（APIキーまたはJWT）
- [ ] HTTPSの使用（SSL/TLS証明書）
- [ ] IPベースのレート制限
- [ ] CORS設定の制限
- [ ] 入力検証の強化
- [ ] SQLインジェクション対策
- [ ] XSS対策
- [ ] CSRF対策

### 監視・ログ

- [ ] アクセスログの記録
- [ ] 異常検知システム
- [ ] アラート設定（Slack/メール）
- [ ] ログの機密情報マスキング
- [ ] ログの長期保存

### パフォーマンス

- [ ] 負荷テストの実施
- [ ] キャッシュ機能の実装
- [ ] CDNの導入（静的コンテンツ）
- [ ] データベースの最適化

### バックアップ・復旧

- [ ] 自動バックアップの設定
- [ ] 復旧手順の文書化
- [ ] 災害復旧計画

---

## 🎯 推奨される段階的な公開

### Phase 1: 内部ネットワークのみ

- Tailscale VPN経由でのアクセスのみ
- 認証なしでも安全
- 現在の状態で可能

### Phase 2: 限定公開

- 特定のIPアドレスのみ許可
- 基本的なAPI認証
- レート制限の実装

### Phase 3: 一般公開

- 完全な認証・認可
- HTTPS必須
- 包括的なセキュリティ対策

---

## ⚠️ 結論

**現在の状態で外部公開すると**：

1. **誰でもAPIにアクセス可能** → リソースの無制限消費
2. **機密情報の漏洩リスク** → HTTP通信、ログ漏洩
3. **システム破壊の可能性** → 不正なコマンド実行
4. **予想外のコスト発生** → 大量のAPIリクエスト

**推奨**：
- **ローカル環境での運用**：現在の状態で問題なし ✅
- **外部公開**：上記の必須対策を実装してから ⚠️

---

**作成日時**: 2025-01-28  
**状態**: 外部公開には追加対策が必要 ⚠️

