# 自動保存機能の実装完了

Cursorでの会話履歴とManaOSの操作を自動的に記憶システムに保存する機能を実装しました。

## 実装内容

### ✅ 実装済み機能

1. **ManaOS操作の自動保存**
   - `act()`メソッド実行時に重要な操作を自動保存
   - 保存対象: `llm_call`, `generate_image`, `generate_video`, `svi_generate`, `svi_extend`, `svi_story`, `run_workflow`, `search_models`, `get_model_info`
   - 保存先: Obsidian（`System`フォルダ）

2. **重要なイベントの自動保存**
   - `emit()`メソッドで`critical`または`important`優先度のイベントを自動保存
   - 保存先: Obsidian（`System`フォルダ）

3. **Cursor会話の手動保存**
   - `save_conversation()`メソッドでCursorでの会話を手動保存可能
   - 保存先: Obsidian（`Conversations`フォルダ）

## 使い方

### ManaOS操作の自動保存（自動）

```python
import manaos_core_api as manaos

# LLM呼び出し（自動保存される）
result = manaos.act("llm_call", {
    "task_type": "conversation",
    "prompt": "こんにちは"
})

# 画像生成（自動保存される）
result = manaos.act("generate_image", {
    "prompt": "beautiful landscape"
})
```

### 重要なイベントの自動保存（自動）

```python
# criticalまたはimportant優先度のイベントは自動保存される
manaos.emit("task_completed", {"message": "タスク完了"}, "important")
manaos.emit("error_occurred", {"error": "エラー発生"}, "critical")
```

### Cursor会話の手動保存

```python
# Cursorでの会話を手動保存
memory_id = manaos.save_conversation(
    user_message="こんにちは、ManaOSについて教えて",
    assistant_response="ManaOSは統合AIシステムです。",
    context={"user": "mana", "session_id": "123"}
)
```

## 保存先

- **ManaOS操作**: `Obsidian Vault/System/システム YYYY-MM-DD.md`
- **重要なイベント**: `Obsidian Vault/System/システム YYYY-MM-DD.md`
- **Cursor会話**: `Obsidian Vault/Conversations/会話 YYYY-MM-DD.md`

## 動作確認

テストスクリプトを実行:

```bash
python manaos_integrations/test_auto_save.py
```

## 今後の拡張予定

- [ ] Cursorでの会話の完全自動保存（MCP統合）
- [ ] 操作履歴の要約機能
- [ ] 記憶の自動整理機能
- [ ] 検索機能の強化



