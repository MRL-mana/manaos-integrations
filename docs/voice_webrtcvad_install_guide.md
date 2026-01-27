# 🎤 webrtcvad インストールガイド（Windows）

**VAD改善機能のためのwebrtcvadインストール方法**

---

## 📋 概要

webrtcvadは、WebRTCのVoice Activity Detection（VAD）ライブラリのPythonバインディングです。
Windowsではビルドが必要なため、以下のいずれかの方法でインストールします。

---

## 方法1: ビルド済みwheelをダウンロードしてインストール（推奨・最も簡単）

### ステップ1: ビルド済みwheelをダウンロード

1. **Christoph Gohlkeのサイトからダウンロード**
   - URL: https://www.lfd.uci.edu/~gohlke/pythonlibs/#webrtcvad
   - ページを開いて、Python 3.10用のwheelファイルを探す
   - ファイル名例: `webrtcvad-2.0.10-cp310-cp310-win_amd64.whl`
   - または、最新版の `webrtcvad-2.0.10-cp310-cp310-win_amd64.whl` をダウンロード

2. **ダウンロード場所を確認**
   - 通常は `Downloads` フォルダに保存されます
   - ファイル名を確認: `webrtcvad-*.whl`

### ステップ2: wheelファイルをインストール

```powershell
# ダウンロードしたwheelファイルのパスを指定
pip install C:\Users\mana4\Downloads\webrtcvad-2.0.10-cp310-cp310-win_amd64.whl

# または、ダウンロードフォルダに移動してから
cd C:\Users\mana4\Downloads
pip install webrtcvad-2.0.10-cp310-cp310-win_amd64.whl
```

### ステップ3: インストール確認

```powershell
python -c "import webrtcvad; print('webrtcvad installed successfully')"
```

---

## 方法2: Visual C++ Build Toolsを使用

### ステップ1: Visual C++ Build Toolsをインストール

1. **Microsoft公式サイトからダウンロード**
   - URL: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - 「Build Tools for Visual Studio」をダウンロード

2. **インストーラーを実行**
   - 「C++ ビルドツール」ワークロードを選択
   - インストール（数GB、時間がかかります）

### ステップ2: 新しいコマンドプロンプトを開く

**重要**: Visual C++ Build Toolsをインストール後、**新しいコマンドプロンプト**を開く必要があります。

### ステップ3: webrtcvadをインストール

```powershell
pip install webrtcvad
```

### ステップ4: インストール確認

```powershell
python -c "import webrtcvad; print('webrtcvad installed successfully')"
```

---

## 方法3: condaを使用（condaが利用可能な場合）

### ステップ1: condaの確認

```powershell
conda --version
```

### ステップ2: webrtcvadをインストール

```powershell
conda install -c conda-forge webrtcvad
```

### ステップ3: インストール確認

```powershell
python -c "import webrtcvad; print('webrtcvad installed successfully')"
```

---

## 方法4: 自動インストールスクリプト（推奨）

以下のスクリプトを実行すると、自動的に最適な方法を試します：

```powershell
# スクリプトを実行
python scripts/voice/auto_install_webrtcvad.py
```

---

## 🔍 トラブルシューティング

### 問題1: "Microsoft Visual C++ 14.0 or greater is required"

**原因**: Visual C++ Build Toolsがインストールされていない

**解決策**:
- 方法1（ビルド済みwheel）を使用する
- または、Visual C++ Build Toolsをインストールする

### 問題2: "No matching distribution found"

**原因**: PyPIにwebrtcvadのWindows用wheelがない

**解決策**:
- 方法1（ビルド済みwheel）を使用する
- または、GitHubからソースをビルドする

### 問題3: condaが見つからない

**原因**: condaがインストールされていない、またはPATHに追加されていない

**解決策**:
- 方法1（ビルド済みwheel）を使用する
- または、方法2（Visual C++ Build Tools）を使用する

---

## ✅ インストール後の確認

インストールが成功したら、以下で確認できます：

```powershell
# 動作確認スクリプトを実行
python scripts/voice/check_voice_integration.py
```

webrtcvadがインストールされている場合、以下のように表示されます：
```
✅ webrtcvad: OK
```

---

## 💡 推奨方法

**最も簡単な方法**: **方法1（ビルド済みwheel）**

理由：
- Visual C++ Build Toolsのインストールが不要
- すぐにインストール可能
- エラーが少ない

---

## 📚 参考リンク

- [webrtcvad GitHub](https://github.com/wiseman/py-webrtcvad)
- [Christoph Gohlke's Pythonlibs](https://www.lfd.uci.edu/~gohlke/pythonlibs/)
- [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

---

**インストール後、VAD改善機能が有効になります！** 🚀
