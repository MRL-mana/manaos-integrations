# LFM 2.5 最適化機会：活用場所の特定

**Liquid AI LFM 2.5**をManaOS内で活用できる具体的な場所を特定しました。

---

## 🎯 優先度：高（即座に効果が出る）

### 1. Intent Router（意図分類システム）

**ファイル**: `intent_router.py`

**現状**:
- モデル: `llama3.2:3b`
- 用途: 入力（音声/テキスト/イベント）の意図分類
- 使用頻度: **非常に高い**（すべての入力で実行）

**LFM 2.5への置き換え効果**:
- ✅ **レイテンシ削減**: 10秒 → 1-3秒（期待値）
- ✅ **CPU前提**: GPU不要で高速
- ✅ **日本語性能**: LFM 2.5の方が日本語が強い
- ✅ **コスト削減**: より軽量なモデルで動作

**実装方法**:
```python
# intent_router.py の __init__ を変更
model: str = "lfm2.5:1.2b",  # LFM 2.5に変更
```

**期待される効果**:
- 意図分類の速度が3-5倍向上
- CPUだけで動作可能（GPU不要）
- 日本語の分類精度向上

---

### 2. Secretary Routines（秘書機能）の要約生成

**ファイル**: `secretary_routines.py`

**現状**:
- タスクタイプ: `reasoning`（重いモデル）
- 用途: ログ要約、未完了タスク分析、日報生成
- 使用頻度: **高**（朝・昼・夜のルーチンで実行）

**LFM 2.5への置き換え効果**:
- ✅ **タスクタイプ変更**: `reasoning` → `lightweight_conversation`
- ✅ **レイテンシ削減**: 30-60秒 → 5-10秒（期待値）
- ✅ **コスト削減**: 重いモデル（qwen2.5:72b）を使わない

**実装箇所**:

#### 2.1 ログ要約（`_get_log_diff`メソッド）
```python
# 現在（138行目）
summary_result = manaos.act("llm_call", {
    "task_type": "reasoning",  # ← これを変更
    "prompt": summary_prompt
})

# 変更後
summary_result = manaos.act("llm_call", {
    "task_type": "lightweight_conversation",  # LFM 2.5使用
    "prompt": summary_prompt
})
```

#### 2.2 未完了タスク分析（`_analyze_incomplete_tasks`メソッド）
```python
# 現在（381行目）
analysis_result = manaos.act("llm_call", {
    "task_type": "reasoning",  # ← これを変更
    "prompt": analysis_prompt
})

# 変更後
analysis_result = manaos.act("llm_call", {
    "task_type": "lightweight_conversation",  # LFM 2.5使用
    "prompt": analysis_prompt
})
```

#### 2.3 日報生成（`evening_routine`メソッド）
```python
# 現在（580行目）
report_result = manaos.act("llm_call", {
    "task_type": "reasoning",  # ← これを変更
    "prompt": report_prompt
})

# 変更後
report_result = manaos.act("llm_call", {
    "task_type": "lightweight_conversation",  # LFM 2.5使用
    "prompt": report_prompt
})
```

**期待される効果**:
- 秘書機能の実行時間が大幅短縮
- コスト削減（重いモデルを使わない）
- より頻繁に実行可能

---

## 🎯 優先度：中（効果は大きいが実装がやや複雑）

### 3. Task Planner（実行計画作成）

**ファイル**: `task_planner.py`

**現状**:
- モデル: 設定ファイル依存（通常は中規模モデル）
- 用途: 実行計画の作成
- 使用頻度: **中**（タスク実行時に使用）

**LFM 2.5への置き換え効果**:
- ⚠️ **部分的に適用可能**: 簡単な計画はLFM 2.5で十分
- ✅ **複雑な計画は従来通り**: 重いモデルを使用

**実装方法**:
```python
# 計画の複雑度を判定
if is_simple_plan(input_text):
    # 簡単な計画はLFM 2.5を使用
    model = "lfm2.5:1.2b"
    task_type = "lightweight_conversation"
else:
    # 複雑な計画は従来通り
    model = "qwen2.5:14b"
    task_type = "automation"
```

**期待される効果**:
- 簡単な計画の作成速度向上
- コスト削減（簡単な計画で重いモデルを使わない）

---

### 4. Content Generation（成果物自動生成）

**ファイル**: `content_generation_loop.py`

**現状**:
- モデル: 設定依存
- 用途: 成果物（レポート、メモ等）の自動生成
- 使用頻度: **中**

**LFM 2.5への置き換え効果**:
- ✅ **下書き生成**: LFM 2.5で十分
- ✅ **最終版は従来通り**: 重いモデルで品質向上

**実装方法**:
```python
# 下書き生成はLFM 2.5を使用
draft_result = manaos.act("lfm25_call", {
    "message": draft_prompt,
    "task_type": "lightweight_conversation"
})

# 最終版は従来のモデルを使用
final_result = manaos.act("llm_call", {
    "task_type": "generation",
    "prompt": refine_prompt
})
```

**期待される効果**:
- 下書き生成の速度向上
- コスト削減

---

## 🎯 優先度：低（将来的な拡張）

### 5. UI Operations（UI操作）

**ファイル**: `ui_operations_api.py`

**現状**:
- 用途: UI操作の意図理解
- 使用頻度: **低**

**LFM 2.5への置き換え効果**:
- ✅ **軽量タスク**: UI操作の理解は軽量で十分

---

### 6. Unified Orchestrator（統合オーケストレーター）

**ファイル**: `unified_orchestrator.py`

**現状**:
- 用途: タスクの統合管理
- 使用頻度: **高**

**LFM 2.5への置き換え効果**:
- ⚠️ **部分的に適用可能**: 簡単なタスク管理はLFM 2.5で十分

---

## 📊 期待される総合効果

### パフォーマンス向上

| 項目 | 現在 | LFM 2.5適用後 | 改善率 |
|------|------|--------------|--------|
| Intent Router | 10秒 | 1-3秒 | **70-90%削減** |
| Secretary要約 | 30-60秒 | 5-10秒 | **80-85%削減** |
| Secretary分析 | 30-60秒 | 5-10秒 | **80-85%削減** |
| Secretary日報 | 30-60秒 | 5-10秒 | **80-85%削減** |

### コスト削減

- **重いモデル（qwen2.5:72b）の使用頻度**: 70-80%削減
- **中規模モデル（qwen2.5:14b）の使用頻度**: 30-40%削減
- **軽量モデル（LFM 2.5）の使用頻度**: 大幅増加

### リソース使用量

- **GPU使用率**: 30-40%削減
- **CPU使用率**: 軽微な増加（許容範囲）
- **メモリ使用量**: 20-30%削減

---

## 🚀 実装優先順位

### Phase 1（即座に実装）

1. ✅ **Intent Router**: モデルを`lfm2.5:1.2b`に変更
2. ✅ **Secretary Routines**: 要約・分析・日報生成を`lightweight_conversation`に変更

**期待効果**: 即座にパフォーマンス向上・コスト削減

### Phase 2（短期実装）

3. **Task Planner**: 簡単な計画はLFM 2.5を使用
4. **Content Generation**: 下書き生成はLFM 2.5を使用

**期待効果**: さらなるパフォーマンス向上・コスト削減

### Phase 3（将来的な拡張）

5. **UI Operations**: UI操作理解にLFM 2.5を使用
6. **Unified Orchestrator**: 簡単なタスク管理にLFM 2.5を使用

---

## 💡 実装例

### Intent Routerの変更

```python
# intent_router.py
def __init__(
    self,
    ollama_url: str = "http://127.0.0.1:11434",
    model: str = "lfm2.5:1.2b",  # ← LFM 2.5に変更
    config_path: Optional[Path] = None
):
```

### Secretary Routinesの変更

```python
# secretary_routines.py
# 要約生成
summary_result = manaos.act("llm_call", {
    "task_type": "lightweight_conversation",  # ← 変更
    "prompt": summary_prompt
})

# 未完了タスク分析
analysis_result = manaos.act("llm_call", {
    "task_type": "lightweight_conversation",  # ← 変更
    "prompt": analysis_prompt
})

# 日報生成
report_result = manaos.act("llm_call", {
    "task_type": "lightweight_conversation",  # ← 変更
    "prompt": report_prompt
})
```

---

## 🎉 まとめ

**LFM 2.5を活用できる場所**:

1. ✅ **Intent Router** - 意図分類（最優先）
2. ✅ **Secretary Routines** - 要約・分析・日報生成（最優先）
3. ⚠️ **Task Planner** - 簡単な計画作成（部分的）
4. ⚠️ **Content Generation** - 下書き生成（部分的）

**期待される効果**:
- パフォーマンス: **70-90%向上**
- コスト: **70-80%削減**
- リソース: **GPU使用率30-40%削減**

**実装優先度**: Phase 1（Intent Router + Secretary Routines）を最優先で実装推奨

---

**最終更新**: 2025-01-28
