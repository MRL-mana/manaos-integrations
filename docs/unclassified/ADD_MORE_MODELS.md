# 📥 より多くのモデルの追加（14B/32Bモデル）

## 🎯 目的

高難易度タスクに対応するため、より強力なモデル（14B/32B）を追加します。

---

## 📋 モデル追加手順

### ステップ1: LM Studioでモデルを検索

1. **LM Studioを起動**
2. **「Search」タブ**を開く
3. **モデルを検索**:
   - `Qwen2.5-Coder-14B-Instruct`
   - `Qwen2.5-Coder-32B-Instruct`
   - `DeepSeek-Coder-33B-Instruct`

### ステップ2: モデルをダウンロード

1. **検索結果からモデルを選択**
2. **「Download」ボタンをクリック**
3. **ダウンロード完了まで待機**
   - 14Bモデル: 約8-10GB
   - 32Bモデル: 約20-25GB
   - 時間がかかります（数時間の可能性）

### ステップ3: モデルをサーバーに読み込む

1. **「Server」タブ**を開く
2. **「Select a model to load」**でダウンロードしたモデルを選択
3. **モデルが「READY」になるまで待機**

### ステップ4: 設定ファイルを更新

`llm_routing_config_lm_studio.yaml` を編集：

```yaml
difficulty_routing:
  high:
    threshold_min: 50
    models:
      primary: "qwen2.5-coder-14b-instruct"  # 14Bモデルに変更
      fallback:
        - "qwen2.5-coder-7b-instruct"  # 7Bモデルをフォールバックに
```

32Bモデルを使用する場合：

```yaml
difficulty_routing:
  high:
    threshold_min: 50
    models:
      primary: "qwen2.5-coder-32b-instruct"  # 32Bモデルに変更
      fallback:
        - "qwen2.5-coder-14b-instruct"  # 14Bモデルをフォールバックに
        - "qwen2.5-coder-7b-instruct"  # 7Bモデルを最終フォールバックに
```

---

## 💡 推奨モデル

### RTX 5080（16GB VRAM）の場合

| モデル | VRAM使用量 | 用途 | 推奨度 |
|--------|-----------|------|--------|
| **7B** | ~4GB | コード補完、簡単な修正 | ⭐⭐⭐⭐⭐ |
| **14B** | ~8GB | コード生成、リファクタリング | ⭐⭐⭐⭐ |
| **32B** | ~20GB+ | アーキテクチャ設計、最適化 | ⭐⭐⭐（VRAMに余裕がある場合） |

**推奨設定：**
- **常駐用**: 7Bモデル
- **高難易度用**: 14Bモデル（利用可能な場合）
- **32Bモデル**: VRAMに十分な余裕がある場合のみ

---

## 🔧 設定の最適化

### VRAM使用量を確認

```powershell
# GPU使用状況を確認
nvidia-smi
```

### モデル選択の最適化

VRAMが不足している場合、軽量モデルを優先的に使用するように設定：

```yaml
difficulty_routing:
  high:
    models:
      primary: "qwen2.5-coder-7b-instruct"  # VRAM不足時は7Bを使用
      fallback:
        - "nvidia/nemotron-3-nano"  # さらに軽量なモデル
```

---

## ✅ 確認方法

### 1. モデルが読み込まれているか確認

```powershell
Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -Method GET
```

### 2. ルーティング設定を確認

```powershell
python -c "import yaml; print(yaml.safe_load(open('llm_routing_config_lm_studio.yaml')))"
```

### 3. 高難易度タスクでテスト

```python
import requests

response = requests.post(
    "http://localhost:9501/api/llm/route",
    json={
        "prompt": "このシステムのアーキテクチャを設計して、マイクロサービス化を検討して",
        "context": {
            "code_context": "既存のモノリシックアプリケーションのコード..."
        }
    }
)

result = response.json()
print(f"選択されたモデル: {result['model']}")
print(f"難易度スコア: {result['difficulty_score']}")
```

---

## 📊 モデル比較

### 7B vs 14B vs 32B

| 特徴 | 7B | 14B | 32B |
|------|----|----|----|
| **VRAM** | ~4GB | ~8GB | ~20GB+ |
| **速度** | ⚡⚡⚡ | ⚡⚡ | ⚡ |
| **品質** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **用途** | コード補完、簡単な修正 | コード生成、リファクタリング | アーキテクチャ設計、最適化 |

---

## 🎯 推奨ワークフロー

1. **まず7Bモデルで試す**
   - ほとんどのタスクは7Bで十分

2. **7Bで不十分な場合、14Bを試す**
   - 複雑なリファクタリング
   - 大規模なコード生成

3. **32Bは最後の手段**
   - アーキテクチャ設計
   - システム全体の最適化

---

**モデルを追加して、より高品質な応答を実現しましょう！🎉**



















