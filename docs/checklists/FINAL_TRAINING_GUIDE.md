# 🚀 CASTLE-EX 学習開始 - 最終ガイド

## ✅ 現在の環境状況

### 利用可能
- ✅ Python 3.10.6
- ✅ PyTorch 2.11.0 (CUDA対応)
- ✅ Transformers
- ✅ datasets 4.5.0
- ✅ accelerate
- ✅ CUDA利用可能 (NVIDIA GeForce RTX 5080)
- ✅ Ollama (qwen2.5:7b)

### 問題点
- ❌ LLaMA-Factory: Python 3.11.0以上が必要（現在3.10.6）
- ❌ Axolotl: 依存関係の競合（triton）

---

## 🎯 解決策（優先順位順）

### オプション1: Python 3.11以上にアップグレード（最も推奨）

**メリット**: LLaMA-Factoryが使用可能、最も確実

```powershell
# 1. Python 3.11以上をインストール
#    https://www.python.org/downloads/

# 2. 新しいPythonでLLaMA-Factoryをインストール
cd LLaMA-Factory
python -m pip install -e .

# 3. 学習を開始
llama-factory train --model_name_or_path <ベースモデル> --dataset ..\castle_ex_dataset_v1_0_train.jsonl --output_dir ..\outputs\castle_ex_v1_0 --num_train_epochs 25
```

### オプション2: 仮想環境でAxolotlをインストール

**メリット**: 現在のPython環境を維持

```powershell
# 1. 新しい仮想環境を作成
python -m venv venv_axolotl

# 2. 仮想環境をアクティベート
venv_axolotl\Scripts\activate

# 3. pipをアップグレード
python -m pip install --upgrade pip

# 4. tritonを先にインストール
pip install triton>=3.0.0,<3.4.0

# 5. Axolotlをインストール
pip install axolotl

# 6. 学習を開始
axolotl train ..\castle_ex_training_config.yaml
```

### オプション3: PowerShellでバッチファイルを実行

**注意**: 外部トレーナーがインストールされている必要があります

```powershell
# PowerShellでは .\ を付けて実行
.\quick_start_training.bat
```

---

## 📋 推奨アクション

1. **Python 3.11以上をインストール**（最も確実）
2. **LLaMA-Factoryを使用して学習を開始**
3. **学習完了後、評価を実行**

---

## 🎯 学習開始コマンド（Python 3.11以上の場合）

```powershell
# LLaMA-Factoryディレクトリに移動
cd LLaMA-Factory

# 学習を開始（ベースモデルを指定）
llama-factory train `
  --model_name_or_path microsoft/Phi-3-mini-4k-instruct `
  --dataset ..\castle_ex_dataset_v1_0_train.jsonl `
  --output_dir ..\outputs\castle_ex_v1_0 `
  --num_train_epochs 25 `
  --per_device_train_batch_size 2 `
  --gradient_accumulation_steps 4 `
  --learning_rate 2.0e-5 `
  --warmup_steps 100 `
  --logging_steps 100 `
  --save_steps 500 `
  --eval_strategy steps `
  --eval_steps 500
```

---

## 📝 学習完了後の評価

```powershell
# 評価を実行
python castle_ex_evaluator_fixed.py `
  --eval-data castle_ex_dataset_v1_0_eval.jsonl `
  --output evaluation_v1_0.json `
  --model-type ollama `
  --model <学習済みモデル名>
```

---

**準備完了！Python 3.11以上をインストールして学習を開始してください。** 🚀
