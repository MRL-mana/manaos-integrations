# 🎯 Cursor × ローカルLLM モデル選定ガイド

**RTX 5080前提の完全ガイド**

---

## 🎯 選定方針

**常駐用 = 速さ重視（7B〜14B）**  
**高精度用 = 品質重視（20B〜32B）**

RTX 5080なら、**常駐は7B〜14Bで"ヌルヌル運用"**が正義。

---

## 🚀 常駐用モデル（7B〜14B）⭐推奨

### Qwen2.5-Coder-7B-Instruct

**スペック**:
- VRAM: ~4GB
- 速度: ⚡⚡⚡（超高速）
- 品質: ⭐⭐⭐（コード生成に特化）

**用途**:
- コード補完
- 軽量チャット
- リファクタリング
- バグ修正

**推奨設定**:
```json
{
  "model": "Qwen2.5-Coder-7B-Instruct",
  "temperature": 0.3,
  "max_tokens": 2048,
  "top_p": 0.9
}
```

**ダウンロード**:
- LM Studio: `Qwen2.5-Coder-7B-Instruct`
- Ollama: `ollama pull qwen2.5-coder:7b`

---

### DeepSeek-Coder-6.7B-Instruct

**スペック**:
- VRAM: ~4GB
- 速度: ⚡⚡⚡（超高速）
- 品質: ⭐⭐⭐（コード生成に特化）

**用途**:
- コード補完
- 軽量チャット
- リファクタリング
- バグ修正

**推奨設定**:
```json
{
  "model": "DeepSeek-Coder-6.7B-Instruct",
  "temperature": 0.3,
  "max_tokens": 2048,
  "top_p": 0.9
}
```

**ダウンロード**:
- LM Studio: `DeepSeek-Coder-6.7B-Instruct`
- Ollama: `ollama pull deepseek-coder:6.7b`

---

### Qwen2.5-Coder-14B-Instruct

**スペック**:
- VRAM: ~8GB
- 速度: ⚡⚡（高速）
- 品質: ⭐⭐⭐⭐（高品質コード生成）

**用途**:
- コード生成
- 中規模チャット
- 設計レビュー
- 複雑なリファクタリング

**推奨設定**:
```json
{
  "model": "Qwen2.5-Coder-14B-Instruct",
  "temperature": 0.5,
  "max_tokens": 4096,
  "top_p": 0.9
}
```

**ダウンロード**:
- LM Studio: `Qwen2.5-Coder-14B-Instruct`
- Ollama: `ollama pull qwen2.5-coder:14b`

---

## 🎯 高精度用モデル（20B〜32B）

### Qwen2.5-Coder-32B-Instruct

**スペック**:
- VRAM: ~20GB
- 速度: ⚡（中速）
- 品質: ⭐⭐⭐⭐⭐（最高品質）

**用途**:
- 複雑なコード生成
- 設計レビュー
- アーキテクチャ設計
- 難易度の高い問題解決

**推奨設定**:
```json
{
  "model": "Qwen2.5-Coder-32B-Instruct",
  "temperature": 0.3,
  "max_tokens": 8192,
  "top_p": 0.9
}
```

**ダウンロード**:
- LM Studio: `Qwen2.5-Coder-32B-Instruct`
- Ollama: `ollama pull qwen2.5-coder:32b`

**注意**：RTX 5080でも重いので、**必要時のみ**使用

---

### DeepSeek-Coder-33B-Instruct

**スペック**:
- VRAM: ~20GB
- 速度: ⚡（中速）
- 品質: ⭐⭐⭐⭐⭐（最高品質）

**用途**:
- 複雑なコード生成
- 設計レビュー
- アーキテクチャ設計
- 難易度の高い問題解決

**推奨設定**:
```json
{
  "model": "DeepSeek-Coder-33B-Instruct",
  "temperature": 0.3,
  "max_tokens": 8192,
  "top_p": 0.9
}
```

**ダウンロード**:
- LM Studio: `DeepSeek-Coder-33B-Instruct`
- Ollama: `ollama pull deepseek-coder:33b`

---

## 📊 モデル比較表

| モデル | VRAM | 速度 | 品質 | 用途 |
|--------|------|------|------|------|
| **Qwen2.5-Coder-7B** | ~4GB | ⚡⚡⚡ | ⭐⭐⭐ | コード補完・軽量チャット |
| **DeepSeek-Coder-6.7B** | ~4GB | ⚡⚡⚡ | ⭐⭐⭐ | コード補完・軽量チャット |
| **Qwen2.5-Coder-14B** | ~8GB | ⚡⚡ | ⭐⭐⭐⭐ | コード生成・中規模チャット |
| **Qwen2.5-Coder-32B** | ~20GB | ⚡ | ⭐⭐⭐⭐⭐ | 複雑なコード生成・設計 |
| **DeepSeek-Coder-33B** | ~20GB | ⚡ | ⭐⭐⭐⭐⭐ | 複雑なコード生成・設計 |

---

## 🎯 マナ推奨構成

### 構成1：シンプル（推奨）

**常駐**: `Qwen2.5-Coder-7B-Instruct`
- コード補完・軽量チャットに使用
- VRAM余裕あり、超高速

**高精度**: `Qwen2.5-Coder-32B-Instruct`
- 必要時のみ呼び出し
- 複雑なコード生成・設計に使用

---

### 構成2：バランス型

**常駐**: `Qwen2.5-Coder-14B-Instruct`
- コード生成・中規模チャットに使用
- 品質と速度のバランスが良い

**高精度**: `Qwen2.5-Coder-32B-Instruct`
- 必要時のみ呼び出し
- 複雑なコード生成・設計に使用

---

## 🔧 モデル切替方法

### LM Studioの場合

1. **「Server」タブ**で現在のモデルを確認
2. **「Select a model to load」**で別モデルを選択
3. **「Start Server」**をクリック
4. Cursor側は自動的に新しいモデルを使用

### Ollamaの場合

```powershell
# モデルを切り替え（プロキシ経由の場合）
ollama run qwen2.5-coder:7b

# または直接APIで指定
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "Hello"
}'
```

---

## 💡 量子化レベル選び

### Q4（推奨）

**特徴**:
- 軽量（VRAM使用量が少ない）
- 速度が速い
- 品質は若干低下するが実用レベル

**用途**: 常駐用に最適

### Q8

**特徴**:
- 中量（VRAM使用量が中程度）
- 速度は中程度
- 品質が高い

**用途**: バランス型

### FP16（非量子化）

**特徴**:
- 重量（VRAM使用量が多い）
- 速度が遅い
- 品質が最高

**用途**: 高精度用に最適

---

## 🚨 注意事項

### VRAM不足の場合

1. **モデルサイズを下げる**（32B → 14B → 7B）
2. **量子化レベルを下げる**（FP16 → Q8 → Q4）
3. **同時実行数を制限**（1モデルのみロード）

### 速度が遅い場合

1. **モデルサイズを下げる**（32B → 14B → 7B）
2. **Context長を短くする**（8192 → 4096 → 2048）
3. **量子化レベルを下げる**（FP16 → Q8 → Q4）

### 品質が低い場合

1. **モデルサイズを上げる**（7B → 14B → 32B）
2. **量子化レベルを上げる**（Q4 → Q8 → FP16）
3. **Temperatureを下げる**（0.7 → 0.5 → 0.3）

---

## 📝 まとめ

**マナ推奨構成**:

1. **常駐**: `Qwen2.5-Coder-7B-Instruct`（Q4量子化）
   - VRAM: ~4GB
   - 速度: 超高速
   - 用途: コード補完・軽量チャット

2. **高精度**: `Qwen2.5-Coder-32B-Instruct`（Q8量子化）
   - VRAM: ~20GB
   - 速度: 中速
   - 用途: 複雑なコード生成・設計

**これで"ヌルヌル運用"が実現！🔥**

---

## 🔗 関連ファイル

- `CURSOR_LOCAL_LLM_SETUP.md` - 接続設定手順
- `CURSOR_PROMPT_TEMPLATES.md` - プロンプトテンプレート集
- `MANAOS_LLM_ROUTING.md` - ManaOS統合設計



















