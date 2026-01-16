# FWPKM統合設計書：ManaOSへの実装計画

## 📋 概要

FWPKM（Forward Product Key Memory）の思想をManaOSに統合し、**長期記憶・短期記憶・検索精度・128K汎化**を実現する設計図。

---

## 🎯 設計目標

### 1. 長期記憶（PKM的機能）
- **既存のRAGメモリシステム**を活用
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

## 🏗️ アーキテクチャ設計

### 全体構成

```
┌─────────────────────────────────────────────────────────┐
│                    ManaOS FWPKM統合システム                │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────┐      ┌──────────────────┐         │
│  │   長期記憶層      │      │   短期記憶層      │         │
│  │  (PKM-like)      │      │  (FWPKM-like)    │         │
│  │                  │      │                  │         │
│  │  - RAG Memory    │      │  - Chunk Memory  │         │
│  │  - Obsidian      │      │  - Inference Mem │         │
│  │  - Fixed         │      │  - Dynamic       │         │
│  └──────────────────┘      └──────────────────┘         │
│           │                        │                     │
│           └──────────┬─────────────┘                     │
│                      │                                    │
│              ┌───────▼───────┐                          │
│              │  メモリ統合層   │                          │
│              │  (Unified)     │                          │
│              └───────┬───────┘                          │
│                      │                                    │
│              ┌───────▼───────┐                          │
│              │  LLMルーティング │                          │
│              │  (Router)       │                          │
│              └─────────────────┘                          │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 コンポーネント設計

### 1. 短期記憶システム（FWPKM Core）

#### 1.1 チャンク処理エンジン

```python
class ChunkMemoryProcessor:
    """
    推論中のチャンク処理とメモリ更新
    """
    
    def __init__(
        self,
        chunk_size: int = 2048,  # チャンクサイズ（トークン）
        memory_slots: int = 10000,  # メモリスロット数
        update_rate: float = 0.1  # 更新率
    ):
        self.chunk_size = chunk_size
        self.memory_slots = memory_slots
        self.update_rate = update_rate
        
        # メモリ構造（Product Key方式）
        self.key1_slots = int(memory_slots ** 0.5)  # 例: 100
        self.key2_slots = int(memory_slots ** 0.5)  # 例: 100
        self.value_matrix = np.zeros((self.key1_slots, self.key2_slots, 768))  # 例: 768次元
        
        # 使用頻度追跡（崩壊防止用）
        self.slot_usage = np.zeros((self.key1_slots, self.key2_slots))
        
        # ゲーティング機構
        self.gate_weight = 0.5  # デフォルトゲート重み
    
    def process_chunk(
        self,
        chunk_text: str,
        model_output: str,
        target: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        チャンクを処理してメモリを更新
        
        Args:
            chunk_text: 入力チャンク
            model_output: モデルの出力
            target: 教師信号（オプション）
        
        Returns:
            更新情報
        """
        # 1. チャンクから重要情報を抽出
        key_vectors = self._extract_keys(chunk_text)
        
        # 2. メモリスロットを選択（Product Key方式）
        slot_indices = self._select_slots(key_vectors)
        
        # 3. MSE lossでメモリを更新
        if target:
            self._update_memory_mse(slot_indices, model_output, target)
        else:
            # 自己教師学習的な更新
            self._update_memory_self_supervised(slot_indices, chunk_text, model_output)
        
        # 4. 使用頻度を更新
        self._update_usage(slot_indices)
        
        # 5. メモリ崩壊防止チェック
        self._prevent_collapse()
        
        return {
            "slots_updated": len(slot_indices),
            "chunk_length": len(chunk_text),
            "memory_state": self._get_memory_state()
        }
    
    def _extract_keys(self, text: str) -> np.ndarray:
        """テキストからキーベクトルを抽出"""
        # 簡易実装：埋め込みベクトルを使用
        # 本番では専用のエンコーダーを使用
        pass
    
    def _select_slots(self, key_vectors: np.ndarray) -> List[Tuple[int, int]]:
        """Product Key方式でスロットを選択"""
        # Key1とKey2を別々に選択
        # 組み合わせでスロットを決定
        pass
    
    def _update_memory_mse(
        self,
        slot_indices: List[Tuple[int, int]],
        model_output: str,
        target: str
    ):
        """MSE lossでメモリを更新"""
        # 予測値とターゲットの差を計算
        # Value行列を更新
        pass
    
    def _prevent_collapse(self):
        """メモリ崩壊を防止"""
        # 使用頻度が偏っている場合、リバランス
        # 未使用スロットを活性化
        pass
```

#### 1.2 推論時メモリ更新

```python
class InferenceMemoryUpdater:
    """
    推論中のメモリ更新を管理
    """
    
    def __init__(self, chunk_processor: ChunkMemoryProcessor):
        self.chunk_processor = chunk_processor
        self.session_memory = {}  # セッションごとのメモリ状態
        self.update_history = []  # 更新履歴
    
    def process_long_text(
        self,
        text: str,
        model: str,
        session_id: str
    ) -> Iterator[Dict[str, Any]]:
        """
        長文をチャンクに分けて処理
        
        Args:
            text: 入力テキスト
            model: 使用モデル
            session_id: セッションID
        
        Yields:
            処理結果
        """
        # チャンクに分割
        chunks = self._split_into_chunks(text)
        
        # セッションメモリを初期化
        if session_id not in self.session_memory:
            self.session_memory[session_id] = {
                "chunks_processed": 0,
                "memory_snapshot": None
            }
        
        accumulated_context = ""
        
        for i, chunk in enumerate(chunks):
            # 前のチャンクのコンテキストを追加
            full_chunk = accumulated_context + chunk
            
            # LLMで処理
            model_output = self._call_llm(model, full_chunk)
            
            # メモリを更新
            update_info = self.chunk_processor.process_chunk(
                chunk_text=chunk,
                model_output=model_output,
                target=None  # 自己教師学習
            )
            
            # コンテキストを蓄積（重要情報のみ）
            accumulated_context = self._accumulate_context(
                accumulated_context,
                chunk,
                update_info
            )
            
            # セッションメモリを更新
            self.session_memory[session_id]["chunks_processed"] += 1
            self.session_memory[session_id]["memory_snapshot"] = update_info
            
            yield {
                "chunk_index": i,
                "chunk_length": len(chunk),
                "update_info": update_info,
                "accumulated_context_length": len(accumulated_context)
            }
    
    def retrieve_from_memory(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        メモリから情報を検索
        
        Args:
            query: 検索クエリ
            session_id: セッションID（Noneの場合は全セッション）
        
        Returns:
            検索結果
        """
        # Product Key方式で検索
        # 関連スロットを取得
        # Value行列から情報を抽出
        pass
```

---

### 2. 長期記憶システム（既存RAG拡張）

#### 2.1 RAG Memory Enhanced との統合

```python
class UnifiedMemorySystem:
    """
    長期記憶（RAG）と短期記憶（FWPKM）を統合
    """
    
    def __init__(
        self,
        rag_memory: RAGMemoryEnhanced,
        chunk_processor: ChunkMemoryProcessor
    ):
        self.rag_memory = rag_memory  # 長期記憶
        self.chunk_processor = chunk_processor  # 短期記憶
    
    def process_with_memory(
        self,
        text: str,
        session_id: str,
        use_long_term: bool = True,
        use_short_term: bool = True
    ) -> Dict[str, Any]:
        """
        長期記憶と短期記憶の両方を使用して処理
        
        Args:
            text: 入力テキスト
            session_id: セッションID
            use_long_term: 長期記憶を使用するか
            use_short_term: 短期記憶を使用するか
        
        Returns:
            処理結果
        """
        results = {
            "long_term_results": [],
            "short_term_results": [],
            "unified_context": ""
        }
        
        # 長期記憶から検索
        if use_long_term:
            long_term_results = self.rag_memory.search_memories(text, limit=5)
            results["long_term_results"] = long_term_results
        
        # 短期記憶から検索
        if use_short_term:
            short_term_results = self.chunk_processor.retrieve_from_memory(
                text,
                session_id
            )
            results["short_term_results"] = short_term_results
        
        # 統合コンテキストを構築
        results["unified_context"] = self._build_unified_context(
            long_term_results if use_long_term else [],
            short_term_results if use_short_term else []
        )
        
        return results
    
    def update_memory_hierarchy(
        self,
        content: str,
        importance: float,
        session_id: str
    ):
        """
        メモリ階層を更新
        
        - 重要度が高い → 長期記憶（RAG）に保存
        - 重要度が低い → 短期記憶（FWPKM）のみ
        """
        threshold = 0.7
        
        if importance >= threshold:
            # 長期記憶に保存
            self.rag_memory.add_memory(
                content=content,
                force_importance=importance
            )
        
        # 短期記憶にも一時的に保存（セッション中）
        # （実装はChunkMemoryProcessorで）
        pass
```

---

### 3. LLMルーティング統合

#### 3.1 メモリ対応LLMルーター

```python
class MemoryAwareLLMRouter(LLMRouter):
    """
    メモリを意識したLLMルーティング
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unified_memory = UnifiedMemorySystem(...)
        self.chunk_processor = ChunkMemoryProcessor()
    
    def route_with_memory(
        self,
        task_type: str,
        prompt: str,
        session_id: str,
        context_length: int = 0
    ) -> Dict[str, Any]:
        """
        メモリを活用したルーティング
        
        Args:
            task_type: タスクタイプ
            prompt: プロンプト
            session_id: セッションID
            context_length: コンテキスト長
        
        Returns:
            ルーティング結果
        """
        # 長文の場合はチャンク処理を有効化
        use_chunk_processing = context_length > 4096
        
        if use_chunk_processing:
            # チャンク処理モード
            return self._route_with_chunk_processing(
                task_type,
                prompt,
                session_id
            )
        else:
            # 通常モード（既存のルーティング）
            return self._route_normal(
                task_type,
                prompt,
                session_id
            )
    
    def _route_with_chunk_processing(
        self,
        task_type: str,
        prompt: str,
        session_id: str
    ) -> Dict[str, Any]:
        """チャンク処理を使用したルーティング"""
        # 1. メモリから関連情報を取得
        memory_context = self.unified_memory.process_with_memory(
            prompt,
            session_id
        )
        
        # 2. チャンクに分割
        chunks = self._split_into_chunks(prompt)
        
        # 3. 各チャンクを処理
        results = []
        for chunk in chunks:
            # メモリコンテキストを追加
            enhanced_prompt = self._build_enhanced_prompt(
                chunk,
                memory_context
            )
            
            # LLMで処理
            llm_result = self.route(
                task_type,
                enhanced_prompt
            )
            
            # メモリを更新
            self.chunk_processor.process_chunk(
                chunk_text=chunk,
                model_output=llm_result.get("response", ""),
                target=None
            )
            
            results.append(llm_result)
        
        # 4. 結果を統合
        return self._merge_results(results)
```

---

## 🔧 実装詳細

### 1. チャンク処理アルゴリズム

```python
def split_into_chunks(
    text: str,
    chunk_size: int = 2048,
    overlap: int = 256
) -> List[str]:
    """
    テキストをチャンクに分割（オーバーラップ付き）
    
    Args:
        text: 入力テキスト
        chunk_size: チャンクサイズ（トークン）
        overlap: オーバーラップサイズ（トークン）
    
    Returns:
        チャンクのリスト
    """
    # トークナイザーで分割
    tokens = tokenize(text)
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = detokenize(chunk_tokens)
        chunks.append(chunk_text)
        
        # オーバーラップ
        start = end - overlap
    
    return chunks
```

### 2. MSE更新アルゴリズム

```python
def update_memory_mse(
    value_matrix: np.ndarray,
    slot_indices: List[Tuple[int, int]],
    predicted: np.ndarray,
    target: np.ndarray,
    learning_rate: float = 0.01
):
    """
    MSE lossでメモリを更新
    
    Args:
        value_matrix: Value行列
        slot_indices: 更新するスロットのインデックス
        predicted: 予測値
        target: ターゲット値
        learning_rate: 学習率
    """
    mse_loss = np.mean((predicted - target) ** 2)
    
    # 勾配を計算
    gradient = 2 * (predicted - target) / len(predicted)
    
    # 各スロットを更新
    for i, j in slot_indices:
        # ゲーティングで更新量を調整
        gate = calculate_gate(i, j)
        update = learning_rate * gate * gradient
        
        value_matrix[i, j] += update
```

### 3. メモリ崩壊防止

```python
def prevent_memory_collapse(
    slot_usage: np.ndarray,
    value_matrix: np.ndarray,
    threshold: float = 0.8
):
    """
    メモリ崩壊を防止
    
    Args:
        slot_usage: スロット使用頻度
        value_matrix: Value行列
        threshold: 使用頻度の閾値
    """
    # 使用頻度の分散を計算
    usage_variance = np.var(slot_usage)
    
    # 分散が大きすぎる場合（偏りがある）
    if usage_variance > threshold:
        # 未使用スロットを活性化
        unused_slots = np.where(slot_usage < 0.1)
        
        for i, j in zip(unused_slots[0], unused_slots[1]):
            # ランダムな初期化で活性化
            value_matrix[i, j] = np.random.normal(0, 0.1, value_matrix.shape[2])
            slot_usage[i, j] = 0.5  # 中間値に設定
```

### 4. ゲーティング機構

```python
def calculate_gate(
    slot_index: Tuple[int, int],
    memory_state: Dict[str, Any],
    confidence_threshold: float = 0.7
) -> float:
    """
    ゲート重みを計算
    
    Args:
        slot_index: スロットインデックス
        memory_state: メモリ状態
        confidence_threshold: 信頼度閾値
    
    Returns:
        ゲート重み（0.0-1.0）
    """
    # スロットの信頼度を計算
    confidence = calculate_slot_confidence(slot_index, memory_state)
    
    # 信頼度が閾値以上なら高ゲート、以下なら低ゲート
    if confidence >= confidence_threshold:
        return 0.8  # 高ゲート
    else:
        return 0.3  # 低ゲート
```

---

## 📊 設定ファイル設計

### `fwpkm_config.yaml`

```yaml
# FWPKM統合設定

# チャンク処理設定
chunk_processing:
  enabled: true
  chunk_size: 2048  # トークン数
  overlap: 256  # オーバーラップサイズ
  min_chunk_size: 512  # 最小チャンクサイズ

# メモリ設定
memory:
  # 短期記憶（FWPKM）
  short_term:
    enabled: true
    memory_slots: 10000  # メモリスロット数
    key1_slots: 100  # Key1スロット数
    key2_slots: 100  # Key2スロット数
    value_dim: 768  # Value次元
    update_rate: 0.1  # 更新率
    learning_rate: 0.01  # 学習率
  
  # 長期記憶（RAG）
  long_term:
    enabled: true
    importance_threshold: 0.7  # 長期記憶への保存閾値
    auto_promote: true  # 自動昇格（短期→長期）
  
  # 統合設定
  unified:
    enabled: true
    balance_weight: 0.5  # 長期/短期のバランス重み

# メモリ崩壊防止
collapse_prevention:
  enabled: true
  usage_variance_threshold: 0.8  # 使用頻度分散の閾値
  rebalance_interval: 100  # リバランス間隔（チャンク数）
  unused_slot_threshold: 0.1  # 未使用スロットの閾値

# ゲーティング設定
gating:
  enabled: true
  confidence_threshold: 0.7  # 信頼度閾値
  high_gate_weight: 0.8  # 高ゲート重み
  low_gate_weight: 0.3  # 低ゲート重み
  adaptive: true  # 適応的ゲーティング

# 長文処理設定
long_context:
  enabled: true
  max_context_length: 128000  # 最大コンテキスト長（トークン）
  chunk_processing_threshold: 4096  # チャンク処理開始閾値
  accumulation_strategy: "important_only"  # コンテキスト蓄積戦略

# 復習効果設定
review_effect:
  enabled: true
  review_threshold: 2  # 復習回数の閾値
  memory_enhancement_rate: 0.2  # メモリ強化率
```

---

## 🔌 API設計

### REST API

```python
# POST /api/fwpkm/process
# 長文をチャンク処理してメモリを更新
{
    "text": "長文テキスト...",
    "session_id": "session_123",
    "model": "qwen2.5:14b",
    "options": {
        "chunk_size": 2048,
        "use_long_term": true,
        "use_short_term": true
    }
}

# GET /api/fwpkm/memory/{session_id}
# セッションのメモリ状態を取得
{
    "session_id": "session_123",
    "include_long_term": true,
    "include_short_term": true
}

# POST /api/fwpkm/search
# メモリから検索
{
    "query": "検索クエリ",
    "session_id": "session_123",
    "scope": "all"  # "all", "long_term", "short_term"
}

# POST /api/fwpkm/review
# 復習効果を適用
{
    "text": "復習するテキスト",
    "session_id": "session_123",
    "review_count": 2
}
```

### Python API

```python
from fwpkm_integration import FWPKMIntegration

# 初期化
fwpkm = FWPKMIntegration(
    config_path="fwpkm_config.yaml"
)

# 長文処理
results = fwpkm.process_long_text(
    text="長文テキスト...",
    session_id="session_123",
    model="qwen2.5:14b"
)

# メモリ検索
memory_results = fwpkm.search_memory(
    query="検索クエリ",
    session_id="session_123"
)

# 復習効果
review_results = fwpkm.apply_review_effect(
    text="復習するテキスト",
    session_id="session_123",
    review_count=2
)
```

---

## 🧪 実装フェーズ

### Phase 1: 基盤実装（1-2週間）
- [ ] `ChunkMemoryProcessor`の実装
- [ ] 基本的なチャンク処理
- [ ] メモリ構造の定義

### Phase 2: メモリ更新（2-3週間）
- [ ] MSE更新アルゴリズム
- [ ] メモリ崩壊防止
- [ ] ゲーティング機構

### Phase 3: 統合（2-3週間）
- [ ] 既存RAGメモリとの統合
- [ ] LLMルーティングとの統合
- [ ] API実装

### Phase 4: 最適化（1-2週間）
- [ ] パフォーマンス最適化
- [ ] 128K長文対応の検証
- [ ] 復習効果の実証

---

## 📈 期待される効果

### 1. 長文読解能力
- **従来**: 4K-8Kトークンが限界
- **FWPKM統合後**: 128Kトークンまで対応可能

### 2. 検索精度
- **従来**: 外部RAGのみ
- **FWPKM統合後**: 内部メモリ + 外部RAGのハイブリッド

### 3. 復習効果
- **従来**: 毎回同じ処理
- **FWPKM統合後**: 読むたびに記憶が強化

### 4. メモリ効率
- **従来**: アテンションに依存（重い）
- **FWPKM統合後**: メモリ参照に逃がせる（軽い）

---

## ⚠️ 注意事項

### 1. 計算コスト
- 推論中のメモリ更新は追加コスト
- チャンク処理のオーバーヘッド
- **対策**: バッチ処理、非同期処理

### 2. メモリ使用量
- メモリスロットの保持
- セッションごとの状態管理
- **対策**: 定期的なクリーンアップ、圧縮

### 3. 実装の複雑さ
- Product Key方式の実装
- メモリ崩壊防止の調整
- **対策**: 段階的実装、テスト駆動開発

---

## 🚀 次のステップ

1. **プロトタイプ実装**: 最小限の機能で動作確認
2. **既存システムとの統合テスト**: RAGメモリとの連携
3. **パフォーマンス測定**: 128K長文での実証
4. **本番デプロイ**: 段階的なロールアウト

---

## 📚 参考資料

- FWPKM論文（元のソース）
- PKM（Product Key Memory）の実装
- ManaOS既存メモリシステム（`rag_memory_enhanced.py`）
- LLMルーティングシステム（`llm_routing.py`）

---

**作成日**: 2024年
**バージョン**: 1.0
**ステータス**: 設計完了、実装待ち
