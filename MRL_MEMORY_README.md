# MRL Memory System - ManaOS

## 🎯 概要

FWPKMの思想をManaOSに即戦力として組み込んだ**推論中に短期メモリを更新し続ける**システムです。

**本物のFWPKMを自作するのではなく、FWPKMの思想だけを今のスタックで即戦力化**した実装です。

---

## ✨ 3レイヤ構造

1. **Scratchpad（超短期：数分〜数時間）**
   - 今読んでる/作業してる文章から「キー→事実」を抜き出して追記
   - 例：人物・日付・要件・エラー原因・決定事項

2. **Working Memory（短期：数日）**
   - Scratchpadを圧縮して"使える形"に整える（重複排除・優先度付け）
   - 例：「この案件はAが確定、Bは未確定、Cは保留」

3. **Long-term（長期：Obsidian/Notion/GitHub知識）**
   - 本当に残す価値があるものだけ昇格（＝継続学習っぽい部分）

---

## 🚀 クイックスタート

### 1. 基本的な使用

```python
from mrl_memory_system import MRLMemorySystem

# 初期化
system = MRLMemorySystem()

# テキストを処理（抽出→追記→復習効果）
text = "プロジェクトXの開始日を2024年2月1日に決定しました。"
result = system.process(text, source="test", enable_rehearsal=True)

# メモリから検索
results = system.retrieve("決定", limit=5)

# LLMに渡すコンテキストを取得
context = system.get_context_for_llm("決定", limit=3)
```

### 2. LLMルーティングとの統合

```python
from mrl_memory_integration import MRLMemoryLLMIntegration

# 統合システムを初期化
integration = MRLMemoryLLMIntegration()

# メモリを活用したLLMルーティング
result = integration.route_with_memory(
    task_type="conversation",
    prompt="プロジェクトXの開始日は？",
    source="user_query"
)

print(result["response"])
```

### 3. REST APIサーバーの起動

```bash
python mrl_memory_integration.py
```

デフォルトでポート5105で起動します。

---

## 📦 ファイル構成

```
.
├── mrl_memory/                    # メモリディレクトリ
│   ├── scratchpad.jsonl          # 超短期メモリ（追記型）
│   ├── working_memory.md         # 短期メモリ（人間が読める要約）
│   └── promoted.jsonl            # 昇格済みメモリ
├── mrl_memory_extractor.py        # 抽出器
├── mrl_memory_rehearsal.py       # 復習効果
├── mrl_memory_promoter.py         # 昇格ルール
├── mrl_memory_system.py           # 統合システム
├── mrl_memory_integration.py      # 既存システムとの統合
└── MRL_MEMORY_README.md           # このファイル
```

---

## 🔧 機能詳細

### 抽出器（Extractor）

入力が来たら毎回これを走らせる：

- 固有名詞（人・物・場所）
- 数値（期限、金額、型番、IP、ポート）
- 決定事項（「〜に決めた」）
- 未解決（「わからない」「エラー」）
- TODO（「やる」「次」）

→ `scratchpad.jsonl` に追記

### リトリーバ（Retriever）

次の推論前に：

- 今の質問からキーを作る
- scratchpad + working_memory から関連項目だけ引く
- LLMに渡す（"思い出し"）

### 復習効果（Rehearsal）

同じテーマが出たら：

- 既存メモリに追記 or 強化（confidence↑）
- 重複はマージ

→ これで"2回目に強くなる"現象を作れる。

### 昇格ルール（Promoter）

一定条件を満たしたら長期へ：

- 3回以上参照された
- confidence=high
- ttl切れても残したい

→ Obsidian/Notion/GitHub（manaos-knowledge）に整理して保存

---

## 📊 何が嬉しい？

- **128Kの代わり**：長文を全部コンテキストに詰めないで済む
- **検索精度UP**：作業中に作った"自分専用索引"が効く
- **コストDOWN**：毎回全部読む/貼るが消える
- **復習効果**：同じ案件ほど早く正確になる

要するに「長文脈＝金持ちの殴り方」をやめて、
「賢いメモリ運用＝貧乏でも勝てる殴り方」に変える。

---

## 🔌 API使用例

### n8n/Slackから呼び出し

```bash
# テキストを処理
curl -X POST http://localhost:5105/api/memory/process \
  -H "Content-Type: application/json" \
  -d '{
    "text": "プロジェクトXの開始日を2024年2月1日に決定しました。",
    "source": "slack",
    "enable_rehearsal": true
  }'

# メモリから検索
curl -X POST http://localhost:5105/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "決定",
    "limit": 5
  }'

# LLMコンテキストを取得
curl -X POST http://localhost:5105/api/memory/context \
  -H "Content-Type: application/json" \
  -d '{
    "query": "プロジェクトX",
    "limit": 3
  }'
```

---

## 🎓 実装のポイント

### 1. 推論中に更新

従来のRAGは「事前に保存→後で検索」ですが、
MRL Memoryは「推論中に更新→次の回答で参照」します。

### 2. 3レイヤ構造

- **Scratchpad**: 超短期（数分〜数時間）
- **Working Memory**: 短期（数日）
- **Long-term**: 長期（Obsidian/Notion/GitHub）

### 3. 復習効果

同じテーマが出たらメモリが強化される。
1回目: 10%未満の正答率
2回目: 70%以上の正答率

### 4. 昇格ルール

一定条件を満たしたら長期記憶に昇格。
→ 継続学習っぽい部分を実現。

---

## ⚠️ 注意事項

### メモリ使用量

- `scratchpad.jsonl`は追記型なので、定期的にクリーンアップが必要
- 昇格ルールで長期記憶に移すことで容量を管理

### パフォーマンス

- 大量のエントリがある場合、検索が遅くなる可能性
- 本番ではインデックス（SQLite等）を使うべき

### 実装の簡易性

- 現在の実装は簡易版（全件読み込み/書き込み）
- 本番では最適化が必要

---

## 🔗 関連リンク

- [FWPKM統合設計書](./FWPKM_INTEGRATION_DESIGN.md) - 詳細な設計仕様
- [LLMルーティング](./llm_routing.py) - LLMルーティングシステム
- [RAGメモリシステム](./rag_memory_enhanced.py) - 既存の長期記憶システム

---

**作成日**: 2024年  
**バージョン**: 1.0  
**ステータス**: 実装完了、動作確認中
