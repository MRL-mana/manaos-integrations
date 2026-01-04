# manaOS 標準API 仕様書

**作成日**: 2025-12-28  
**バージョン**: 1.0.0

---

## 📋 概要

manaOS標準APIは、manaOSの全機能にアクセスするための統一インターフェースです。

### 設計思想

- **単一I/O**: 全機能は4つのAPIを通じてアクセス
- **統一フォーマット**: 入力・出力を統一フォーマットで管理
- **自動統合**: 各機能が自動的に統合される

---

## 🔌 API一覧

### 1. emit - イベント発行

**説明**: 通知・ログ・状態変化を発行

**シグネチャ**:
```python
manaos.emit(event_type: str, payload: Dict[str, Any], priority: str = "normal") -> Dict[str, Any]
```

**パラメータ**:
- `event_type`: イベントタイプ（例: "task_completed", "error", "alert"）
- `payload`: ペイロード（辞書形式）
- `priority`: 優先度（"critical", "important", "normal", "low"）

**戻り値**:
```python
{
    "event_id": "uuid",
    "event_type": "string",
    "payload": {},
    "priority": "string",
    "timestamp": "ISO8601"
}
```

**使用例**:
```python
import manaos_integrations.manaos_core_api as manaos

# 通常通知
manaos.emit("task_completed", {"task_id": "123"}, "normal")

# 重要通知
manaos.emit("error", {"message": "エラー発生"}, "important")

# 緊急通知
manaos.emit("system_down", {"service": "database"}, "critical")
```

---

### 2. remember - 記憶への保存

**説明**: 記憶システムに保存（入口が1個）

**シグネチャ**:
```python
manaos.remember(input_data: Dict[str, Any], format_type: str = "auto") -> Dict[str, Any]
```

**パラメータ**:
- `input_data`: 入力データ（辞書形式）
- `format_type`: フォーマットタイプ（"conversation", "memo", "research", "system", "auto"）

**戻り値**:
```python
{
    "memory_id": "uuid",
    "format_type": "string",
    "input_data": {},
    "timestamp": "ISO8601"
}
```

**使用例**:
```python
import manaos_integrations.manaos_core_api as manaos

# 会話を保存
manaos.remember({
    "type": "conversation",
    "content": "こんにちは、今日はいい天気ですね。"
}, format_type="conversation")

# メモを保存
manaos.remember({
    "content": "明日の会議の準備",
    "tags": ["会議", "準備"]
}, format_type="memo")

# 自動判定
manaos.remember({
    "content": "システムログ"
}, format_type="auto")
```

---

### 3. recall - 記憶からの検索

**説明**: 記憶システムから検索（出口が1個）

**シグネチャ**:
```python
manaos.recall(query: str, scope: str = "all", limit: int = 10) -> List[Dict[str, Any]]
```

**パラメータ**:
- `query`: 検索クエリ
- `scope`: スコープ（"all", "today", "week", "month"）
- `limit`: 取得件数

**戻り値**:
```python
[
    {
        "id": "uuid",
        "type": "string",
        "timestamp": "ISO8601",
        "content": "string",
        "metadata": {}
    },
    ...
]
```

**使用例**:
```python
import manaos_integrations.manaos_core_api as manaos

# 全期間から検索
results = manaos.recall("会議", scope="all", limit=10)

# 今日のログから検索
results = manaos.recall("エラー", scope="today", limit=5)

# 今週のログから検索
results = manaos.recall("タスク", scope="week", limit=20)
```

---

### 4. act - アクション実行

**説明**: タスク・ツール呼び出しを実行

**シグネチャ**:
```python
manaos.act(action_type: str, args: Dict[str, Any]) -> Dict[str, Any]
```

**パラメータ**:
- `action_type`: アクションタイプ（"llm_call", "generate_image", "run_workflow", etc.）
- `args`: 引数（辞書形式）

**戻り値**:
```python
{
    "action_id": "uuid",
    "action_type": "string",
    "result": {},
    "timestamp": "ISO8601"
}
```

**使用例**:
```python
import manaos_integrations.manaos_core_api as manaos

# LLM呼び出し
result = manaos.act("llm_call", {
    "task_type": "conversation",
    "prompt": "こんにちは"
})

# 推論タスク
result = manaos.act("llm_call", {
    "task_type": "reasoning",
    "prompt": "プロジェクトの優先順位を決定してください"
})

# 自動処理タスク
result = manaos.act("llm_call", {
    "task_type": "automation",
    "prompt": "Pythonでファイルを読み込むコードを生成してください"
})
```

---

## 📐 フォーマットタイプ

### 入力フォーマット

- `conversation`: 会話ログ
- `memo`: メモ
- `research`: 自動リサーチ結果
- `system`: システム状態
- `auto`: 自動判定

### 出力フォーマット

- `summary`: 要約
- `judgment`: 判断材料
- `action`: 次アクション
- `learning`: 学習データ

---

## 🔔 優先度

- `critical`: 緊急（Slack + Discord + Email）
- `important`: 重要（Slack + Discord）
- `normal`: 通常（Slackのみ）
- `low`: 低（Slackのみ、優先度低）

---

## 🎯 タスクタイプ（LLMルーティング）

- `conversation`: 会話（軽量・高速）
  - Primary: `llama3.2:3b`
  - Fallback: `qwen2.5:7b`, `llama3.1:8b`

- `reasoning`: 推論（重い・強い）
  - Primary: `qwen2.5:72b`
  - Fallback: `qwen2.5:32b`, `llama3.1:70b`

- `automation`: 自動処理（ツール呼び出し得意）
  - Primary: `qwen2.5:14b`
  - Fallback: `llama3.1:8b`, `mistral:7b`

---

## 🌐 HTTP API エンドポイント

### LLMルーティング

**POST** `/api/llm/route`

```json
{
  "task_type": "conversation|reasoning|automation",
  "prompt": "プロンプト",
  "memory_refs": ["note_id1", "note_id2"],
  "tools_used": ["tool1", "tool2"]
}
```

**レスポンス**:
```json
{
  "response": "LLM応答",
  "model": "使用したモデル",
  "source": "primary|fallback",
  "request_id": "uuid",
  "latency_ms": 1234
}
```

### 記憶システム

**POST** `/api/memory/store`

```json
{
  "content": {
    "type": "conversation",
    "content": "コンテンツ"
  },
  "format_type": "conversation|memo|research|system|auto"
}
```

**GET** `/api/memory/recall?query=検索クエリ&scope=all&limit=10`

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

**POST** `/api/image/stock`

```json
{
  "image_path": "画像ファイルのパス",
  "prompt": "プロンプト",
  "model": "モデル名",
  "parameters": {}
}
```

**GET** `/api/image/search?query=検索クエリ&limit=20`  
**GET** `/api/image/statistics`

---

## 📚 関連ドキュメント

- `ManaOS_Extension_Phase_CoreSpec.md` - 中核仕様書
- `ManaOS_Extension_Phase_Roadmap.md` - ロードマップ
- `README_LLM_ROUTING.md` - LLMルーティング仕様
- `USAGE_GUIDE.md` - 使い方ガイド

---

**最終更新**: 2025-12-28

