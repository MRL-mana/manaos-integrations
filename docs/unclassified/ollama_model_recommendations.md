# Ollamaモデル推奨ガイド（RAGタスク向け）

## 📊 RAGタスクに最適なモデル比較

### 🏆 最推奨モデル（RAGタスク）

#### 1. **Qwen3-4B / Qwen3:4b** ⭐⭐⭐⭐⭐ (最新・推奨)
```
推奨度: ★★★★★
用途: RAG、日本語対応、汎用チャット（最新モデル）
```

**特徴:**
- ✅ **Qwen2.5-72B-Instructに匹敵する性能**（4Bパラメータで72B相当）
- ✅ **GPT-4oと同等の性能**を小型モデルで実現
- ✅ 日本語対応が大幅に強化（多言語対応強化）
- ✅ 推論速度が10倍以上高速（Qwen3-Next）
- ✅ VRAM: 約4-6GB（2.5の7Bより軽量）
- ✅ 2025年4月発表の最新モデル

**推奨設定:**
```python
model = "qwen3:4b"  # または qwen3:8b（より高性能）
```

**インストール:**
```bash
# Ollamaで利用可能か確認が必要
ollama pull qwen3:4b
# または
ollama pull qwen3-4b
```

**注意:** Ollamaにまだ追加されていない可能性があります。その場合はQwen2.5を使用してください。

---

#### 2. **Qwen2.5:7b** ⭐⭐⭐⭐ (安定版)
```
推奨度: ★★★★☆
用途: RAG、日本語対応、汎用チャット（安定版）
```

**特徴:**
- ✅ 日本語対応が優秀（日本語特化版あり）
- ✅ RAGタスクに最適化されている
- ✅ コンテキスト理解が優れている
- ✅ 推論速度が速い
- ✅ VRAM: 約6-8GB
- ✅ Ollamaで確実に利用可能

**推奨設定:**
```python
model = "qwen2.5:7b"  # Qwen3が利用できない場合の代替
```

**インストール:**
```bash
ollama pull qwen2.5:7b
```

---

#### 3. **Mistral NeMo:12b** ⭐⭐⭐⭐
```
推奨度: ★★★★☆
用途: 多言語RAG、推論タスク
```

**特徴:**
- ✅ 128Kトークンのコンテキストウィンドウ
- ✅ 多言語対応（日本語含む）
- ✅ 推論・知識タスクが得意
- ✅ VRAM: 約10-12GB

**推奨設定:**
```python
model = "mistral-nemo:12b"
```

**インストール:**
```bash
ollama pull mistral-nemo:12b
```

---

#### 4. **Llama 3.1:8b** ⭐⭐⭐⭐
```
推奨度: ★★★★☆
用途: 長文処理、多段階推論
```

**特徴:**
- ✅ 128Kトークンのコンテキストウィンドウ
- ✅ 長文処理に優れている
- ✅ 多段階推論が得意
- ⚠️ 日本語はコミュニティ版が必要
- ✅ VRAM: 約8-10GB

**推奨設定:**
```python
model = "llama3.1:8b"  # 日本語版: llama3.1-jp:8b
```

**インストール:**
```bash
ollama pull llama3.1:8b
# 日本語版
ollama pull llama3.1-jp:8b
```

---

#### 5. **Phi-3:mini** ⭐⭐⭐
```
推奨度: ★★★☆☆
用途: 軽量・高速、小規模RAG
```

**特徴:**
- ✅ 非常に軽量（3.8Bパラメータ）
- ✅ 推論速度が速い
- ✅ VRAM: 約3-4GB
- ⚠️ 日本語対応は限定的
- ⚠️ 複雑なRAGタスクには不向き

**推奨設定:**
```python
model = "phi3:mini"  # 現在のデフォルト
```

**インストール:**
```bash
ollama pull phi3:mini
```

---

### 📋 タスク別推奨モデル

| タスクタイプ | 推奨モデル | 理由 |
|---|---|---|
| **日本語RAG** | `qwen3:4b` | 最新モデル、日本語対応強化、高性能 |
| **日本語RAG（安定版）** | `qwen2.5:7b` | 日本語対応が優秀、確実に利用可能 |
| **長文RAG** | `mistral-nemo:12b` | 128Kコンテキストウィンドウ |
| **高速RAG** | `qwen3:4b` | 10倍以上高速、軽量 |
| **高精度RAG** | `qwen3:8b` または `qwen2.5:14b` | より高い精度 |
| **多言語RAG** | `mistral-nemo:12b` | 多言語対応が優秀 |

---

### 🎯 現在の設定と推奨変更

#### 現在の設定
```python
# RAGシステム
model = "llama2"  # 古いモデル、日本語対応が弱い

# Ollama統合API
model = "phi3:mini"  # 軽量だが、RAGには不向き
```

#### 推奨変更

**RAGシステム用（最重要）:**
```python
# Systems/konoha_migration/server_projects/projects/automation/manaos_langchain_rag.py
# Qwen3が利用可能な場合（推奨）
self.llm = Ollama(model="qwen3:4b", base_url="http://localhost:11434")
# Qwen3が利用できない場合の代替
self.llm = Ollama(model="qwen2.5:7b", base_url="http://localhost:11434")
```

**Ollama統合API用:**
```python
# Systems/konoha_migration/manaos_unified_system/api/ollama_integration.py
# Qwen3が利用可能な場合（推奨）
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen3:4b")
# Qwen3が利用できない場合の代替
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:7b")
```

---

### 💡 モデル選択の判断基準

#### VRAM別推奨

| VRAM | 推奨モデル | 備考 |
|---|---|---|
| **4GB以下** | `phi3:mini` | 軽量モデルのみ |
| **6-8GB** | `qwen2.5:7b` | バランス型 |
| **10-12GB** | `mistral-nemo:12b` | 高性能型 |
| **16GB以上** | `qwen2.5:14b` | 最高性能型 |

#### 用途別推奨

| 用途 | 推奨モデル | 理由 |
|---|---|---|
| **日本語RAG** | `qwen2.5:7b` | 日本語対応が最も優秀 |
| **英語RAG** | `mistral-nemo:12b` | 多言語対応が優秀 |
| **高速処理** | `phi3:mini` | 最も軽量 |
| **高精度** | `qwen2.5:14b` | より高い精度 |

---

### 🚀 実装手順

#### 1. モデルをインストール
```bash
# 推奨モデルをインストール
ollama pull qwen2.5:7b
```

#### 2. モデルを確認
```bash
# インストール済みモデルを確認
ollama list
```

#### 3. モデルをテスト
```bash
# 簡単なテスト
ollama run qwen2.5:7b "こんにちは、日本語で答えてください"
```

#### 4. コードを更新
RAGシステムとOllama統合APIのモデル設定を更新

---

### 📊 パフォーマンス比較（参考）

| モデル | 日本語精度 | RAG精度 | 速度 | VRAM | 備考 |
|---|---|---|---|---|---|
| `qwen3:4b` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 4-6GB | **最新・最推奨** |
| `qwen2.5:7b` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 6-8GB | 安定版 |
| `mistral-nemo:12b` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 10-12GB | 多言語 |
| `llama3.1:8b` | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 8-10GB | 長文処理 |
| `phi3:mini` | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 3-4GB | 軽量 |
| `llama2` | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 6-8GB | 旧モデル |

---

### ✅ 最終推奨

**RAGタスクには `qwen3:4b` を最優先で推奨します（利用可能な場合）。**

**Qwen3が利用できない場合は `qwen2.5:7b` を推奨します。**

#### Qwen3を推奨する理由:
1. **最新モデル**（2025年4月発表）
2. **Qwen2.5-72B相当の性能**を4Bパラメータで実現
3. **GPT-4oと同等の性能**
4. **日本語対応が大幅に強化**
5. **推論速度が10倍以上高速**（Qwen3-Next）
6. **VRAM使用量が少ない**（4-6GB）

#### Qwen2.5を推奨する理由（Qwen3が利用できない場合）:
1. 日本語対応が優秀
2. RAGタスクに最適化されている
3. バランスが良い（速度・精度・VRAM）
4. Ollamaで確実に利用可能
5. コミュニティサポートが充実

**確認方法:**
```bash
# Qwen3が利用可能か確認
ollama pull qwen3:4b
# または
ollama pull qwen3-4b

# エラーが出る場合はQwen2.5を使用
ollama pull qwen2.5:7b
```

