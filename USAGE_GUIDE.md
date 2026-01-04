# manaOS拡張フェーズ 使い方ガイド

**作成日**: 2025-12-28  
**バージョン**: 1.0.0

---

## 🚀 クイックスタート

### 1. 標準APIの使用

```python
import manaos_integrations.manaos_core_api as manaos

# イベント発行
manaos.emit("task_completed", {"task_id": "123"}, "normal")

# 記憶への保存
manaos.remember({"content": "メモ"}, "memo")

# 記憶からの検索
results = manaos.recall("メモ", scope="all", limit=10)

# LLM呼び出し
result = manaos.act("llm_call", {
    "task_type": "conversation",
    "prompt": "こんにちは"
})
```

---

## 📐 Phase 1: OSコア固定

### LLMルーティング

```python
from manaos_integrations.llm_routing import LLMRouter

router = LLMRouter()

# 会話タスク
result = router.route(
    task_type="conversation",
    prompt="こんにちは"
)

# 推論タスク
result = router.route(
    task_type="reasoning",
    prompt="プロジェクトの優先順位を決定してください"
)

# 自動処理タスク
result = router.route(
    task_type="automation",
    prompt="Pythonでファイルを読み込むコードを生成してください"
)
```

### 統一記憶システム

```python
from manaos_integrations.memory_unified import UnifiedMemory

memory = UnifiedMemory()

# 記憶への保存
memory_id = memory.store({
    "content": "今日はいい天気でした。",
    "metadata": {"source": "conversation"}
}, format_type="conversation")

# 記憶からの検索
results = memory.recall("天気", scope="all", limit=10)
```

### 通知ハブ

```python
from manaos_integrations.notification_hub import NotificationHub

hub = NotificationHub()

# 通常通知
hub.notify("テスト通知", priority="normal")

# 重要通知
hub.notify("重要な通知", priority="important")

# 緊急通知
hub.notify("緊急通知", priority="critical")
```

---

## 📋 Phase 2: 秘書機能

### 朝のルーチン

```python
from manaos_integrations.secretary_routines import SecretaryRoutines

secretary = SecretaryRoutines()
result = secretary.morning_routine()

# 結果
print(result["schedule"])  # 今日の予定
print(result["tasks"])     # 最重要3タスク
print(result["log_diff"])  # 昨日のログ差分
```

### 昼のルーチン

```python
secretary = SecretaryRoutines()
result = secretary.noon_routine()

# 結果
print(result["progress"])  # 進捗情報
```

### 夜のルーチン

```python
secretary = SecretaryRoutines()
result = secretary.evening_routine()

# 結果
print(result["daily_report"])  # 日報
print(result["tomorrow_prep"]) # 明日の仕込み
```

### n8nワークフロー

1. n8nを開く（http://localhost:5678）
2. ワークフロー → インポート
3. `n8n_workflows/core_routines/` のJSONファイルをインポート
4. Webhook URLを設定
5. スケジュールを設定

---

## 🎨 Phase 3: 創作機能

### 画像ストック

```python
from manaos_integrations.image_stock import ImageStock

stock = ImageStock()

# 画像をストック
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

### 画像生成統合

```python
from manaos_integrations.image_generation_integration import ImageGenerationIntegration

integration = ImageGenerationIntegration()

# 画像生成とストック
result = integration.generate_and_stock(
    prompt="a beautiful landscape",
    model="stable-diffusion-v1-5"
)

# 検索
results = integration.search_stock(query="landscape", limit=10)
```

---

## 🧪 テスト

### 統合テスト

```bash
cd manaos_integrations
python test_integration_all.py
```

### 個別テスト

```bash
# LLMルーティング
python test_llm_routing.py

# 統一記憶システム
python test_memory_unified.py

# 通知ハブ
python test_notification_hub.py

# 秘書機能
python test_secretary_routines.py
```

---

## ⚙️ 設定

### LLMルーティング設定

`llm_routing_config.yaml` を編集：

```yaml
routing:
  conversation:
    primary: "llama3.2:3b"
    fallback: ["qwen2.5:7b", "llama3.1:8b"]
```

### 通知ハブ設定

`notification_hub_config.yaml` を編集：

```yaml
primary: "slack"
routing:
  critical:
    slack: true
    discord: true
    email: true
```

### Obsidian Vault設定

環境変数を設定：

```bash
export OBSIDIAN_VAULT_PATH="C:/Users/mana4/Documents/Obsidian Vault"
```

---

## 🔧 トラブルシューティング

### LLMルーティングが動作しない

1. Ollamaが起動しているか確認
   ```bash
   Get-Process ollama  # Windows
   ```

2. モデルがインストールされているか確認
   ```bash
   ollama list
   ```

3. モデルをインストール
   ```bash
   ollama pull llama3.2:3b
   ```

### 統一記憶システムが動作しない

1. Obsidian Vaultパスを確認
2. 環境変数 `OBSIDIAN_VAULT_PATH` を設定
3. Vaultが存在するか確認

### 通知ハブが動作しない

1. Slack Webhook URLを設定
   ```python
   from notification_system import NotificationSystem
   ns = NotificationSystem()
   ns.configure_slack("https://hooks.slack.com/services/...")
   ```

2. 通知システムの状態を確認

---

## 📚 関連ドキュメント

- `API_SPEC.md` - API仕様書
- `ManaOS_Extension_Phase_CoreSpec.md` - 中核仕様書
- `ManaOS_Extension_Phase_Roadmap.md` - ロードマップ
- `README_LLM_ROUTING.md` - LLMルーティング仕様

---

**最終更新**: 2025-12-28


















