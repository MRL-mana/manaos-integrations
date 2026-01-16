# FWPKM統合システム - ManaOS

## 🎯 概要

FWPKM（Forward Product Key Memory）の思想をManaOSに統合し、**長期記憶・短期記憶・検索精度・128K汎化**を実現するシステムです。

---

## ✨ 主な機能

### 1. 長期記憶（PKM的機能）
- 既存のRAGメモリシステムを活用
- 学習済み知識の固定保存
- 安定した百科事典的メモリ

### 2. 短期記憶（FWPKM的機能）
- **推論中に更新されるメモリ**
- チャンク処理による逐次記憶
- 文脈に即適応する作業メモリ

### 3. 検索精度の向上
- 内部メモリからの高速検索
- 推論中に蓄積された情報の即時参照
- メモリ崩壊防止による安定性

### 4. 128K超長文対応
- チャンク処理による長文読解
- メモリ更新による一貫性保持
- 反復学習効果の実現

---

## 📦 ファイル構成

```
.
├── FWPKM_INTEGRATION_DESIGN.md  # 設計書
├── FWPKM_USAGE_EXAMPLES.md      # 使用例
├── FWPKM_README.md              # このファイル
├── fwpkm_core.py                # コア実装（チャンク処理・メモリ更新）
├── fwpkm_integration.py         # 統合システム（長期+短期記憶）
├── fwpkm_api.py                 # REST API
└── fwpkm_config.yaml            # 設定ファイル
```

---

## 🚀 インストール

### 必要な依存関係

```bash
pip install numpy flask flask-cors pyyaml
```

### 既存システムとの統合

既存のManaOSシステムと統合する場合:

```python
# 既存のRAGメモリシステムが必要
from rag_memory_enhanced import RAGMemoryEnhanced

# 既存の統一メモリシステム（オプション）
from memory_unified import UnifiedMemory
```

---

## 📖 クイックスタート

### 1. 基本的な使用

```python
from fwpkm_integration import UnifiedMemorySystem

# 初期化
system = UnifiedMemorySystem()

# 長文を処理
text = "長文テキスト..."
session_id = "session_123"

for result in system.process_long_text(
    text=text,
    model="qwen2.5:14b",
    session_id=session_id
):
    print(f"チャンク {result['chunk_index']}: 処理完了")

# メモリから検索
results = system.search_memory(
    query="検索クエリ",
    session_id=session_id
)
```

### 2. REST APIサーバーの起動

```bash
python fwpkm_api.py
```

デフォルトでポート5104で起動します。

---

## 🔧 設定

`fwpkm_config.yaml`で設定をカスタマイズできます:

```yaml
# チャンク処理設定
chunk_processing:
  chunk_size: 2048  # チャンクサイズ（トークン）
  overlap: 256      # オーバーラップサイズ

# メモリ設定
memory:
  short_term:
    memory_slots: 10000  # メモリスロット数
    learning_rate: 0.01  # 学習率
  
  long_term:
    importance_threshold: 0.7  # 長期記憶への保存閾値
```

詳細は[使用例](./FWPKM_USAGE_EXAMPLES.md)を参照してください。

---

## 📊 アーキテクチャ

```
┌─────────────────────────────────────────┐
│         UnifiedMemorySystem              │
├─────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐   │
│  │  長期記憶層    │    │  短期記憶層    │   │
│  │  (RAG)       │    │  (FWPKM)     │   │
│  └──────────────┘    └──────────────┘   │
│           │                │            │
│           └────────┬───────┘            │
│                    │                     │
│            ┌───────▼───────┐            │
│            │  メモリ統合層   │            │
│            └───────────────┘            │
└─────────────────────────────────────────┘
```

---

## 🎓 理論的背景

### FWPKMとは？

FWPKMは、**推論中にメモリを更新できるPKM（Product Key Memory）**です。

- **PKM**: 固定の百科事典（長期記憶）
- **FWPKM**: 推論中に更新されるメモ帳（短期記憶）

### なぜ128Kに対応できる？

- 4Kで学習した「メモリ更新のルール」を覚える
- ルールを覚えたら、長さに関係なく動く
- チャンク処理で長文を分割して処理

### 復習効果とは？

- 同じ文章を読むたびにメモリが強化される
- 1回目: 10%未満の正答率
- 2回目: 70%以上の正答率

詳細は[設計書](./FWPKM_INTEGRATION_DESIGN.md)を参照してください。

---

## 📈 パフォーマンス

### 期待される効果

- **長文読解**: 4K-8K → 128Kトークンまで対応
- **検索精度**: 内部メモリ + 外部RAGのハイブリッド
- **復習効果**: 読むたびに記憶が強化
- **メモリ効率**: アテンション依存からメモリ参照へ

---

## ⚠️ 注意事項

### 計算コスト

- 推論中のメモリ更新は追加コスト
- チャンク処理のオーバーヘッド
- **対策**: バッチ処理、非同期処理

### メモリ使用量

- メモリスロットの保持
- セッションごとの状態管理
- **対策**: 定期的なクリーンアップ、圧縮

### 実装の複雑さ

- Product Key方式の実装
- メモリ崩壊防止の調整
- **対策**: 段階的実装、テスト駆動開発

---

## 🔗 関連リンク

- [設計書](./FWPKM_INTEGRATION_DESIGN.md) - 詳細な設計仕様
- [使用例](./FWPKM_USAGE_EXAMPLES.md) - 実装例とベストプラクティス
- [RAGメモリシステム](./rag_memory_enhanced.py) - 既存の長期記憶システム
- [LLMルーティング](./llm_routing.py) - LLMルーティングシステム

---

## 📝 ライセンス

ManaOSプロジェクトの一部として提供されます。

---

## 🤝 コントリビューション

改善提案やバグ報告は、ManaOSプロジェクトのIssueトラッカーに投稿してください。

---

**作成日**: 2024年  
**バージョン**: 1.0  
**ステータス**: 設計完了、実装中
