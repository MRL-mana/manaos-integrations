# manaOS拡張フェーズ 完全ガイド

**作成日**: 2025-12-28  
**バージョン**: 1.0.0

---

## 📋 概要

manaOS拡張フェーズは、manaOSを「分身AIを中核に、秘書と創作を周辺ユニット化するOS」として完成させるための実装です。

### 設計思想

- **分身AIを中核**: 記憶＋判断＋文脈保持
- **秘書を周辺**: 通知・自動化・整頓
- **創作を周辺**: 生成・データセット・ワークフロー
- **「決めないこと」を排除**: 製品レベルのOSコアを構築

---

## 🚀 クイックスタート

### 1. サーバー起動

```bash
cd manaos_integrations
python start_extension_phase.py
```

### 2. 標準APIを使用

```python
import manaos_integrations.manaos_core_api as manaos

# イベント発行
manaos.emit("task_completed", {"task_id": "123"}, "normal")

# 記憶への保存
manaos.remember({"content": "メモ"}, "memo")

# 記憶からの検索
results = manaos.recall("メモ", limit=10)

# LLM呼び出し
result = manaos.act("llm_call", {
    "task_type": "conversation",
    "prompt": "こんにちは"
})
```

### 3. HTTP APIを使用

```bash
# LLMルーティング
curl -X POST http://localhost:9500/api/llm/route \
  -H "Content-Type: application/json" \
  -d '{"task_type": "conversation", "prompt": "こんにちは"}'

# 朝のルーチン
curl -X POST http://localhost:9500/api/secretary/morning
```

---

## 📐 Phase 1: OSコア固定

### LLMルーティング

**機能**: タスクタイプに応じて最適なモデルを自動選択

**タスクタイプ**:
- `conversation`: 会話（軽量・高速）
- `reasoning`: 推論（重い・強い）
- `automation`: 自動処理（ツール呼び出し得意）

**使用方法**:
```python
from manaos_integrations.llm_routing import LLMRouter

router = LLMRouter()
result = router.route("conversation", "こんにちは")
```

### 統一記憶システム

**機能**: Obsidianを母艦として、入力・出力を統一フォーマットで管理

**使用方法**:
```python
from manaos_integrations.memory_unified import UnifiedMemory

memory = UnifiedMemory()
memory_id = memory.store({"content": "..."}, "conversation")
results = memory.recall("検索", scope="all", limit=10)
```

### 通知ハブ

**機能**: Slackを一次通知先に固定、Discord/メールを転送

**使用方法**:
```python
from manaos_integrations.notification_hub import NotificationHub

hub = NotificationHub()
hub.notify("メッセージ", priority="normal")
```

---

## 📋 Phase 2: 秘書機能

### 朝のルーチン

**機能**: 今日の予定＋最重要3タスク＋昨日のログ差分

**使用方法**:
```python
from manaos_integrations.secretary_routines import SecretaryRoutines

secretary = SecretaryRoutines()
result = secretary.morning_routine()
```

### 昼のルーチン

**機能**: 進捗確認＋未完了の理由を1行で

**使用方法**:
```python
secretary = SecretaryRoutines()
result = secretary.noon_routine()
```

### 夜のルーチン

**機能**: 日報自動生成＋明日の仕込み

**使用方法**:
```python
secretary = SecretaryRoutines()
result = secretary.evening_routine()
```

### n8nワークフロー

1. n8nを開く（http://localhost:5678）
2. ワークフロー → インポート
3. `n8n_workflows/core_routines/` のJSONファイルをインポート
4. Webhook URLを設定: `http://localhost:9500/api/secretary/{morning|noon|evening}`
5. スケジュールを設定

---

## 🎨 Phase 3: 創作機能

### 画像ストック

**機能**: 生成された画像を自動で整理し、次回の精度が上がる仕組み

**使用方法**:
```python
from manaos_integrations.image_stock import ImageStock

stock = ImageStock()
stock_info = stock.store(
    image_path=Path("image.png"),
    prompt="a beautiful landscape",
    model="stable-diffusion-v1-5"
)

# 検索
results = stock.search(query="landscape", limit=10)

# 統計情報
stats = stock.get_statistics()
```

---

## 🌐 HTTP API エンドポイント

### LLMルーティング

**POST** `/api/llm/route`
```json
{
  "task_type": "conversation|reasoning|automation",
  "prompt": "プロンプト",
  "memory_refs": [],
  "tools_used": []
}
```

### 記憶システム

**POST** `/api/memory/store` - 記憶への保存  
**GET** `/api/memory/recall?query=検索&scope=all&limit=10` - 記憶からの検索

### 通知ハブ

**POST** `/api/notification/send`
```json
{
  "message": "通知メッセージ",
  "priority": "critical|important|normal|low"
}
```

### 秘書機能

**POST** `/api/secretary/morning` - 朝のルーチン  
**POST** `/api/secretary/noon` - 昼のルーチン  
**POST** `/api/secretary/evening` - 夜のルーチン

### 画像ストック

**POST** `/api/image/stock` - 画像をストック  
**GET** `/api/image/search?query=検索&limit=20` - 画像検索  
**GET** `/api/image/statistics` - 画像統計情報

---

## 🧪 テスト

### 統合テスト

```bash
python test_integration_all.py
```

### APIエンドポイントテスト

```bash
# サーバーを起動
python start_extension_phase.py

# 別ターミナルでテスト
python test_api_endpoints_extension.py
```

---

## ⚙️ 設定

### 必須設定

1. **Obsidian Vaultパス**（環境変数）
   ```bash
   export OBSIDIAN_VAULT_PATH="C:/Users/mana4/Documents/Obsidian Vault"
   ```

2. **Ollama URL**（環境変数）
   ```bash
   export OLLAMA_URL="http://localhost:11434"
   ```

### オプション設定

1. **LLMルーティング設定**（`llm_routing_config.yaml`）
   - モデル名を変更
   - Fallbackモデルを設定

2. **通知ハブ設定**（`notification_hub_config.yaml`）
   - 優先度別ルーティングを設定

3. **Slack Webhook URL**（通知ハブ用）
   ```python
   from notification_system import NotificationSystem
   ns = NotificationSystem()
   ns.configure_slack("https://hooks.slack.com/services/...")
   ```

---

## 📚 ドキュメント

- `API_SPEC.md` - API仕様書
- `USAGE_GUIDE.md` - 使い方ガイド
- `QUICK_START.md` - クイックスタート
- `ManaOS_Extension_Phase_CoreSpec.md` - 中核仕様書
- `ManaOS_Extension_Phase_Roadmap.md` - ロードマップ
- `ManaOS_Extension_Phase_Complete.md` - 実装完了レポート

---

## 🔧 トラブルシューティング

### サーバーが起動しない

1. ポートが使用されていないか確認
   ```bash
   netstat -ano | findstr :9500  # Windows
   ```

2. 依存関係がインストールされているか確認
   ```bash
   pip install flask flask-cors pyyaml requests
   ```

### LLMルーティングが動作しない

1. Ollamaが起動しているか確認
2. モデルがインストールされているか確認
3. 設定ファイル（`llm_routing_config.yaml`）を確認

### 統一記憶システムが動作しない

1. Obsidian Vaultパスを確認
2. 環境変数 `OBSIDIAN_VAULT_PATH` を設定
3. Vaultが存在するか確認

### 通知ハブが動作しない

1. Slack Webhook URLを設定
2. 通知システムの状態を確認

---

## 🎯 完了条件（DoD）

### Phase 1: OSコア固定

- ✅ LLMルーティングが3役割で明確に動作
- ✅ 記憶がObsidianで統一フォーマットで保存・検索可能
- ✅ 通知がSlack中心で優先度別にルーティング

### Phase 2: 秘書機能

- ✅ 朝・昼・夜のルーチンが自動実行
- ✅ n8nワークフローが3本固定で安定動作
- ✅ 他ワークフローは凍結

### Phase 3: 創作機能

- ✅ 画像生成の必須/凍結が判定済み
- ✅ 必須の場合、ストック機能が動作

---

## 🎉 まとめ

manaOS拡張フェーズの実装を完了しました。

**主要成果**:
- ✅ OSコア固定（LLMルーティング、記憶、通知）
- ✅ 秘書機能（朝・昼・夜のルーチン）
- ✅ 創作機能（画像ストック）

**設計思想**:
- 分身AIを中核に、秘書と創作を周辺ユニット化するOS
- 「決めないこと」を排除し、製品レベルのOSコアを構築

---

**最終更新**: 2025-12-28  
**実装完了**: ✅ 全フェーズ完了


















