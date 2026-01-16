# SDモデル対応ガイド（SD3、SD1.5、SDXL）

## 📋 概要

現在のManaOS統合システムで使用可能なStable Diffusionモデルと、その使用方法をまとめました。

## ✅ 対応状況

### 1. **SD1.5（Stable Diffusion 1.5）** ✅ **完全対応**

**対応状況:**
- ✅ ComfyUIで完全にサポート
- ✅ 標準的なワークフローで使用可能
- ✅ `CheckpointLoaderSimple`で読み込み可能

**使用例:**
```python
# gallery_api_server.py や direct_comfyui_generate.py で使用可能
model = "runwayml/stable-diffusion-v1-5.safetensors"
# または
model = "realisian_v60.safetensors"  # SD1.5ベースのモデル
```

**特徴:**
- 512x512〜768x1024の解像度が標準
- 軽量で高速
- 多くのカスタムモデルが利用可能

### 2. **SDXL（Stable Diffusion XL）** ✅ **完全対応**

**対応状況:**
- ✅ ComfyUIで完全にサポート
- ✅ 標準的なワークフローで使用可能
- ✅ `CheckpointLoaderSimple`で読み込み可能

**使用例:**
```python
# SDXLモデルの例
sdxl_models = [
    "sd_xl_base_1.0.safetensors",
    "speciosa25D_v12.safetensors",
    "uwazumimixILL_v50.safetensors"
]
```

**特徴:**
- 1024x1024以上の解像度が標準
- 高品質な画像生成
- より詳細なプロンプト理解

**現在の実装:**
- `generate_mana_mufufu.py`でSDXLモデルを使用
- `direct_comfyui_generate.py`でSDXL判定ロジックあり

### 3. **SD3（Stable Diffusion 3）** ⚠️ **部分的対応（要確認）**

**対応状況:**
- ⚠️ ComfyUIはSD3をサポート（2024年4月以降）
- ⚠️ ただし、特別なワークフローまたはカスタムノードが必要な可能性
- ⚠️ 現在の実装では標準ワークフローを使用（要検証）

**SD3の特徴:**
- より高品質な画像生成
- 改善されたプロンプト理解
- 複数のバリエーション（Medium、Large、Large Turbo）

**必要な準備:**
1. ComfyUIを最新版に更新
2. SD3モデルファイルをダウンロード
3. 必要に応じてカスタムノードをインストール

**使用可能性:**
- SD3モデルファイル（.safetensors）がComfyUIのcheckpointsディレクトリにあれば、理論的には使用可能
- ただし、SD3専用のワークフローが必要な場合がある

### 4. **SD3.5（Stable Diffusion 3.5）** ⚠️ **部分的対応（要確認）**

**対応状況:**
- ⚠️ ComfyUIはSD3.5をサポート（2024年10月以降）
- ⚠️ Medium、Large、Large Turboが利用可能
- ⚠️ 現在の実装では標準ワークフローを使用（要検証）

**SD3.5の特徴:**
- SD3の改良版
- Mediumモデルは消費級ハードウェア向け
- 0.25〜2メガピクセルの解像度をサポート

## 🔧 現在の実装状況

### ワークフロー作成関数

現在の`create_comfyui_workflow`関数は、標準的なSD1.5/SDXLワークフローを作成します：

```python
def create_comfyui_workflow(
    prompt: str,
    negative_prompt: str = "",
    model: str = "realisian_v60.safetensors",
    steps: int = 50,
    guidance_scale: float = 7.5,
    width: int = 768,
    height: int = 1024,
    sampler: str = "euler",
    scheduler: str = "normal",
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """ComfyUIワークフローを作成"""
    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": model_path
            },
            "class_type": "CheckpointLoaderSimple"  # SD1.5/SDXL用
        },
        # ... その他のノード
    }
    return workflow
```

### モデル検出機能

現在の実装では、モデル名からSDXLを判定しています：

```python
# direct_comfyui_generate.py より
if "sdxl" in model.lower() or "speciosa25D" in model or "uwazumimix" in model:
    steps = random.choice([50, 55, 60])
    width, height = random.choice([(1024, 1024), (1024, 1280)])
else:
    steps = random.choice([45, 50, 55])
    width, height = random.choice([(768, 1024), (1024, 768), (832, 1216)])
```

## 💡 SD3/SD3.5を使用するための改善提案

### 1. モデルタイプの自動検出

```python
def detect_model_type(model_name: str) -> str:
    """モデルタイプを自動検出"""
    model_lower = model_name.lower()
    
    if "sd3" in model_lower or "stable-diffusion-3" in model_lower:
        return "sd3"
    elif "sd3.5" in model_lower or "stable-diffusion-3.5" in model_lower:
        return "sd3.5"
    elif "sdxl" in model_lower or "xl" in model_lower:
        return "sdxl"
    else:
        return "sd1.5"  # デフォルト
```

### 2. SD3専用ワークフローの作成

```python
def create_sd3_workflow(
    prompt: str,
    negative_prompt: str = "",
    model: str = "sd3_medium.safetensors",
    steps: int = 50,
    guidance_scale: float = 7.5,
    width: int = 1024,
    height: int = 1024,
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """SD3専用ワークフローを作成"""
    # SD3は異なるローダーやノードが必要な可能性
    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": model_path
            },
            "class_type": "CheckpointLoaderSimple"  # またはSD3専用ローダー
        },
        # SD3専用のノード構成
    }
    return workflow
```

### 3. モデルタイプに応じたワークフロー選択

```python
def create_comfyui_workflow(
    prompt: str,
    negative_prompt: str = "",
    model: str = "realisian_v60.safetensors",
    # ... その他のパラメータ
) -> Dict[str, Any]:
    """モデルタイプに応じて適切なワークフローを作成"""
    model_type = detect_model_type(model)
    
    if model_type == "sd3" or model_type == "sd3.5":
        return create_sd3_workflow(
            prompt, negative_prompt, model,
            steps, guidance_scale, width, height, seed
        )
    else:
        return create_standard_workflow(
            prompt, negative_prompt, model,
            steps, guidance_scale, width, height, sampler, scheduler, seed
        )
```

## 📝 使用方法

### SD1.5を使用する場合

```python
# 既存のコードでそのまま使用可能
result = api.act("generate_image", {
    "prompt": "cute anime girl",
    "model_id": "runwayml/stable-diffusion-v1-5",
    "width": 512,
    "height": 512,
    "num_inference_steps": 50
})
```

### SDXLを使用する場合

```python
# SDXLモデルを指定
result = api.act("generate_image", {
    "prompt": "cute anime girl",
    "model_id": "sd_xl_base_1.0.safetensors",
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 50
})
```

### SD3/SD3.5を使用する場合（要検証）

```python
# SD3モデルを指定（動作確認が必要）
result = api.act("generate_image", {
    "prompt": "cute anime girl",
    "model_id": "sd3_medium.safetensors",  # または実際のSD3モデル名
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 50
})
```

## ⚠️ 注意事項

1. **SD3/SD3.5の使用:**
   - ComfyUIを最新版に更新する必要があります
   - SD3専用のワークフローが必要な場合があります
   - 実際に動作するか検証が必要です

2. **モデルファイルの配置:**
   - すべてのモデルは`C:/ComfyUI/models/checkpoints/`に配置
   - または`C:/mana_workspace/models/`に配置（自動コピー）

3. **解像度の推奨:**
   - SD1.5: 512x512〜768x1024
   - SDXL: 1024x1024以上
   - SD3: 1024x1024以上（モデルによる）

## 🔄 今後の改善予定

1. **SD3/SD3.5の完全対応**
   - 専用ワークフローの実装
   - モデルタイプの自動検出
   - パラメータの最適化

2. **モデル管理の改善**
   - モデルタイプの自動判定
   - モデルごとの最適パラメータの設定
   - モデル情報のデータベース化

## 📊 まとめ

| モデル | 対応状況 | 使用可能性 | 備考 |
|--------|----------|------------|------|
| **SD1.5** | ✅ 完全対応 | 即座に使用可能 | 標準ワークフロー |
| **SDXL** | ✅ 完全対応 | 即座に使用可能 | 標準ワークフロー |
| **SD3** | ⚠️ 部分的対応 | 要検証 | 専用ワークフローが必要な可能性 |
| **SD3.5** | ⚠️ 部分的対応 | 要検証 | 専用ワークフローが必要な可能性 |

現在の実装では、**SD1.5とSDXLは完全に使用可能**です。**SD3とSD3.5は、モデルファイルがあれば理論的には使用可能ですが、実際の動作確認が必要**です。
