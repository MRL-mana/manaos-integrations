# Slack Integration × ManaOS統合状況

## ✅ 統合されているシステム

### 1. Unified Orchestrator（ポート5106）

**統合方法:**
- `ORCHESTRATOR_URL`環境変数で設定
- `/api/execute`エンドポイントにコマンドを送信
- 自動評価・記憶保存に対応

**使用例:**
```python
# File Secretaryコマンドでない場合、Unified Orchestratorに送信
response = httpx.post(
    f"{ORCHESTRATOR_URL}/api/execute",
    json={
        "text": text,
        "mode": "auto",
        "auto_evaluate": True,
        "save_to_memory": True,
        "metadata": {
            "source": "slack",
            "user": user,
            "channel": channel
        }
    }
)
```

---

### 2. File Secretary（ポート5120）

**統合方法:**
- `FILE_SECRETARY_URL`環境変数で設定
- `/api/slack/handle`エンドポイントにコマンドを送信
- `file_secretary_templates.parse_command()`でコマンド解析

**使用例:**
```python
# File Secretaryコマンドを解析
from file_secretary_templates import parse_command
file_command = parse_command(text)

if file_command:
    response = httpx.post(
        f"{FILE_SECRETARY_URL}/api/slack/handle",
        json={
            "text": text,
            "user": user,
            "channel": channel,
            "thread_ts": thread_ts,
            "files": files or []
        }
    )
```

---

### 3. 常時起動LLM

**統合方法:**
- `always_ready_llm_client.py`を使用
- `AlwaysReadyLLMClient`で会話処理
- モデルロード時間なし（常時ロード済み）

**使用例:**
```python
from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType

LLM_CLIENT = AlwaysReadyLLMClient()
response = LLM_CLIENT.chat(
    text,
    model=ModelType.LIGHT,  # llama3.2:3b
    task_type=TaskType.CONVERSATION
)
```

---

### 4. 統一モジュール

**使用しているモジュール:**
- `manaos_logger`: 統一ログ管理
- `manaos_error_handler`: 統一エラーハンドリング
- `manaos_timeout_config`: 統一タイムアウト設定

**使用例:**
```python
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler
from manaos_timeout_config import get_timeout_config

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("SlackIntegration")
timeout_config = get_timeout_config()
```

---

## 🔄 処理フロー

```
Slackメッセージ受信
  ↓
会話モード判定
  ↓
├─ 会話モード → 常時起動LLMで応答
├─ File Secretaryコマンド → File Secretary API
└─ その他 → Unified Orchestrator
  ↓
結果をSlackに返信
```

---

## 📊 統合状況

| システム | 統合状態 | ポート | 用途 |
|---------|---------|--------|------|
| **Unified Orchestrator** | ✅ 統合済み | 5106 | コマンド実行 |
| **File Secretary** | ✅ 統合済み | 5120 | ファイル操作 |
| **常時起動LLM** | ✅ 統合済み | - | 会話処理 |
| **統一モジュール** | ✅ 統合済み | - | ログ・エラー・タイムアウト |

---

## 🎯 使用例

### 1. 会話モード
```
@remi こんにちは
→ 常時起動LLMで応答
```

### 2. File Secretaryコマンド
```
@remi Inboxどう？
→ File Secretary APIに送信
```

### 3. Unified Orchestratorコマンド
```
@remi ファイルを整理して
→ Unified Orchestratorに送信
```

---

## ✅ 結論

**Slack Integrationは完全にManaOSと統合されています！**

- ✅ Unified Orchestrator統合
- ✅ File Secretary統合
- ✅ 常時起動LLM統合
- ✅ 統一モジュール使用

すべてのManaOS機能がSlackから利用可能です。
