# サーバー起動状況

**最終確認**: 2025-12-28

---

## ✅ サーバー起動確認

統合APIサーバーは正常に起動しています。

- **URL**: http://localhost:9500
- **状態**: 起動中

---

## 📋 利用可能なエンドポイント

### 拡張フェーズ API

- `POST /api/llm/route` - LLMルーティング
- `POST /api/memory/store` - 記憶への保存
- `GET /api/memory/recall` - 記憶からの検索
- `POST /api/notification/send` - 通知送信
- `POST /api/secretary/morning` - 朝のルーチン
- `POST /api/secretary/noon` - 昼のルーチン
- `POST /api/secretary/evening` - 夜のルーチン
- `POST /api/image/stock` - 画像をストック
- `GET /api/image/search` - 画像検索
- `GET /api/image/statistics` - 画像統計情報

---

## 🚀 起動方法

### 方法1: 簡易起動スクリプト（推奨）

```bash
cd manaos_integrations
python start_server_simple.py
```

### 方法2: 直接起動

```bash
cd manaos_integrations
python unified_api_server.py
```

---

## 🔧 トラブルシューティング

### エンコーディングエラー

Windows環境で絵文字が表示できない場合は、`start_server_simple.py`を使用してください。

### ポートが使用中

ポート9500が使用中の場合は、環境変数で変更：

```bash
export MANAOS_INTEGRATION_PORT=9501
```

### モジュールインポートエラー

```bash
# モジュールチェック
python check_extension_modules.py
```

---

**最終更新**: 2025-12-28


















