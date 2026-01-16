# FWPKM統合システム 使用例

## 📚 概要

FWPKM（Forward Product Key Memory）の思想をManaOSに統合したシステムの使用例です。

---

## 🚀 クイックスタート

### 1. Python APIから使用

```python
from fwpkm_integration import UnifiedMemorySystem

# 初期化
system = UnifiedMemorySystem()

# 長文を処理（チャンク処理 + メモリ更新）
text = "長文テキスト..."  # 128Kトークンまで対応可能
session_id = "session_123"

for result in system.process_long_text(
    text=text,
    model="qwen2.5:14b",
    session_id=session_id
):
    print(f"チャンク {result['chunk_index']}: {result['chunk_length']}文字")
    print(f"更新スロット数: {result['update_info'].slots_updated}")
```

### 2. REST APIから使用

```bash
# 長文を処理
curl -X POST http://localhost:5104/api/fwpkm/process \
  -H "Content-Type: application/json" \
  -d '{
    "text": "長文テキスト...",
    "session_id": "session_123",
    "model": "qwen2.5:14b"
  }'

# メモリから検索
curl -X POST http://localhost:5104/api/fwpkm/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "検索クエリ",
    "session_id": "session_123",
    "scope": "all"
  }'
```

---

## 📖 詳細な使用例

### 例1: 長文読解（128K対応）

```python
from fwpkm_integration import UnifiedMemorySystem

system = UnifiedMemorySystem()
session_id = "long_doc_session"

# 長文を読み込む（例: 仕様書、契約書など）
with open("long_document.txt", "r", encoding="utf-8") as f:
    long_text = f.read()

# チャンク処理でメモリを更新しながら処理
results = []
for result in system.process_long_text(
    text=long_text,
    model="qwen2.5:14b",
    session_id=session_id
):
    results.append(result)
    print(f"処理中: {result['chunk_index']}/{len(results)}")

# 後で質問する
query = "この文書の主要なポイントは？"
search_results = system.search_memory(
    query=query,
    session_id=session_id,
    scope="all"
)

print(f"検索結果: {len(search_results['unified'])}件")
for result in search_results['unified'][:5]:
    print(f"- {result.get('content', result.get('similarity', 0))}")
```

### 例2: 復習効果の活用

```python
from fwpkm_integration import UnifiedMemorySystem

system = UnifiedMemorySystem()
session_id = "review_session"

# 1回目: 初めて読む
text = "重要な情報を含むテキスト..."
for result in system.process_long_text(
    text=text,
    model="qwen2.5:14b",
    session_id=session_id
):
    pass

# 2回目: 復習（メモリが強化される）
review_result = system.apply_review_effect(
    text=text,
    session_id=session_id,
    review_count=2
)

print(f"復習完了: 強化率={review_result['enhancement_rate']}")
print(f"メモリ状態: {review_result['memory_state']}")
```

### 例3: 長期記憶と短期記憶の統合

```python
from fwpkm_integration import UnifiedMemorySystem

system = UnifiedMemorySystem()
session_id = "unified_session"

# 重要度の高い情報を長期記憶に保存
system.update_memory_hierarchy(
    content="重要な設定情報: API_KEY=xxx",
    importance=0.9,  # 高重要度
    session_id=session_id
)

# 一時的な情報は短期記憶のみ
text = "一時的な作業メモ..."
for result in system.process_long_text(
    text=text,
    model="qwen2.5:14b",
    session_id=session_id
):
    pass

# 統合検索（長期 + 短期）
search_results = system.search_memory(
    query="API_KEY",
    session_id=session_id,
    scope="all"
)

# 長期記憶から見つかる
long_term_results = [r for r in search_results['unified'] if r['type'] == 'long_term']
print(f"長期記憶から: {len(long_term_results)}件")
```

### 例4: LLMルーティングとの統合

```python
from llm_routing import LLMRouter
from fwpkm_integration import UnifiedMemorySystem

# LLMルーターを初期化
router = LLMRouter()

# FWPKMシステムを初期化
memory_system = UnifiedMemorySystem()

# 長文を処理
text = "長文テキスト..."
session_id = "routing_session"

# メモリから関連情報を取得
memory_context = memory_system.process_with_memory(
    text=text,
    session_id=session_id
)

# メモリコンテキストを追加してLLMに送信
enhanced_prompt = f"""
{memory_context['unified_context']}

ユーザーの質問: {text}
"""

# LLMで処理
result = router.route(
    task_type="reasoning",
    prompt=enhanced_prompt
)

print(f"回答: {result['response']}")
```

### 例5: セッション管理

```python
from fwpkm_integration import UnifiedMemorySystem

system = UnifiedMemorySystem()

# セッション1: ドキュメントAを処理
session_a = "doc_a_session"
for result in system.process_long_text(
    text="ドキュメントAの内容...",
    model="qwen2.5:14b",
    session_id=session_a
):
    pass

# セッション2: ドキュメントBを処理
session_b = "doc_b_session"
for result in system.process_long_text(
    text="ドキュメントBの内容...",
    model="qwen2.5:14b",
    session_id=session_b
):
    pass

# 各セッションの状態を確認
state_a = system.get_session_memory_state(session_a)
state_b = system.get_session_memory_state(session_b)

print(f"セッションA: {state_a['chunk_count']}チャンク, {state_a['slots_used']}スロット")
print(f"セッションB: {state_b['chunk_count']}チャンク, {state_b['slots_used']}スロット")
```

---

## 🔧 設定のカスタマイズ

### 設定ファイルの編集

`fwpkm_config.yaml`を編集して動作をカスタマイズ:

```yaml
# チャンクサイズを変更
chunk_processing:
  chunk_size: 4096  # デフォルト: 2048

# メモリスロット数を増やす
memory:
  short_term:
    memory_slots: 50000  # デフォルト: 10000

# 長期記憶への保存閾値を変更
memory:
  long_term:
    importance_threshold: 0.8  # デフォルト: 0.7
```

### プログラムから設定を変更

```python
from fwpkm_core import ChunkMemoryProcessor
from fwpkm_integration import UnifiedMemorySystem

# カスタムプロセッサを作成
custom_processor = ChunkMemoryProcessor(
    chunk_size=4096,
    memory_slots=50000,
    learning_rate=0.02
)

# 統合システムに設定
system = UnifiedMemorySystem(
    chunk_processor=custom_processor
)
```

---

## 📊 パフォーマンス最適化

### 1. バッチ処理

```python
from fwpkm_integration import UnifiedMemorySystem

system = UnifiedMemorySystem()

# 複数のテキストをバッチ処理
texts = ["テキスト1", "テキスト2", "テキスト3"]
session_ids = [f"session_{i}" for i in range(len(texts))]

for text, session_id in zip(texts, session_ids):
    for result in system.process_long_text(
        text=text,
        model="qwen2.5:14b",
        session_id=session_id
    ):
        pass
```

### 2. メモリ状態の保存/読み込み

```python
from fwpkm_integration import UnifiedMemorySystem
from pathlib import Path

system = UnifiedMemorySystem()

# 処理後、状態を保存
system.save_state(Path("memory_state.json"))

# 次回起動時に状態を読み込み
system.load_state(Path("memory_state.json"))
```

---

## 🐛 トラブルシューティング

### 問題: メモリ使用量が大きい

**解決策**:
- メモリスロット数を減らす（`memory_slots`を減らす）
- 定期的にメモリ状態をクリア
- セッションを定期的に削除

```python
# セッションをクリア
system.chunk_processor.session_states.clear()
```

### 問題: 処理が遅い

**解決策**:
- チャンクサイズを増やす（処理回数を減らす）
- 非同期処理を使用
- GPUを活用

### 問題: メモリ崩壊が発生

**解決策**:
- 崩壊防止の閾値を調整
- リバランス間隔を短くする

```yaml
collapse_prevention:
  usage_variance_threshold: 0.6  # デフォルト: 0.8
  rebalance_interval: 50  # デフォルト: 100
```

---

## 📈 ベストプラクティス

1. **セッションIDの管理**: 各タスクごとに一意のセッションIDを使用
2. **重要度の設定**: 重要な情報は`importance`を高く設定して長期記憶に保存
3. **定期的な復習**: 重要な情報は`apply_review_effect`で復習
4. **メモリ状態の保存**: 定期的にメモリ状態を保存して永続化
5. **パフォーマンス監視**: メモリ状態を定期的に確認して最適化

---

## 🔗 関連ドキュメント

- [FWPKM統合設計書](./FWPKM_INTEGRATION_DESIGN.md)
- [RAGメモリシステム](./rag_memory_enhanced.py)
- [LLMルーティング](./llm_routing.py)
