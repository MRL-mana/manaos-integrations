# 🔧 CASTLE-EX 学習開始時の問題と解決策

## 🚨 確認された問題

### 1. LLaMA-Factory: Pythonバージョン要件
- **問題**: LLaMA-FactoryはPython 3.11.0以上が必要
- **現在**: Python 3.10.6
- **エラー**: `Package 'llamafactory' requires a different Python: 3.10.6 not in '>=3.11.0'`

### 2. Axolotl: 依存関係の競合
- **問題**: tritonの依存関係で競合が発生
- **エラー**: `Cannot install axolotl... because these package versions have conflicting dependencies`

### 3. PowerShellでのバッチファイル実行
- **問題**: PowerShellでは `.\quick_start_training.bat` のように実行する必要がある

---

## ✅ 解決策

### オプション1: Transformersを直接使用（推奨・最も簡単）

PyTorchとTransformersが既にインストールされているので、これらを直接使用して学習できます。

```bash
# 学習スクリプトを作成して実行
python train_with_transformers.py
```

### オプション2: Python 3.11以上にアップグレード

```bash
# Python 3.11以上をインストール
# その後、LLaMA-Factoryを再インストール
cd LLaMA-Factory
pip install -e .
```

### オプション3: Axolotlの依存関係を解決

```bash
# tritonを先にインストール
pip install triton>=3.0.0,<3.4.0
# その後、Axolotlをインストール
pip install axolotl --no-deps
pip install -r requirements.txt  # Axolotlのrequirements.txt
```

### オプション4: 仮想環境を使用

```bash
# 新しい仮想環境を作成
python -m venv venv_castle_ex
venv_castle_ex\Scripts\activate
pip install --upgrade pip
# その後、必要なパッケージをインストール
```

---

## 🚀 推奨: Transformers直接使用の実装

PyTorch 2.11.0とTransformersが利用可能なので、これらを直接使用して学習を開始できます。
