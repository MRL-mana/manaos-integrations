# 🎨 ComfyUI起動ガイド

## 📋 ComfyUIの起動方法

ComfyUIを起動することで、Tool Serverの`generate_image`ツールが使用可能になります。

---

## 🔍 Step 1: ComfyUIの状態確認

### 1-1. ComfyUIが既に起動しているか確認

```powershell
# ComfyUIが起動しているか確認
curl http://localhost:8188
```

**期待される結果:**
- HTMLレスポンスが返る
- ComfyUIのWeb UIが表示される

**起動している場合:**
- ✅ ComfyUIは既に起動中
- Tool Serverの`generate_image`ツールが使用可能

### 1-2. ポート8188を使用しているプロセスを確認

```powershell
# ポート8188を使用しているプロセスを確認
netstat -ano | findstr :8188
```

**プロセスが見つからない場合:**
- ComfyUIが起動していない → Step 2へ

---

## 🚀 Step 2: ComfyUIの起動

### 方法1: Pythonで直接起動（推奨）

1. **ComfyUIディレクトリに移動**
   ```powershell
   cd C:\ComfyUI
   ```
   （ComfyUIのインストールパスに応じて変更）

2. **ComfyUIを起動**
   ```powershell
   python main.py --port 8188
   ```

3. **起動確認**
   - ブラウザで http://localhost:8188 を開く
   - ComfyUIのWeb UIが表示されればOK

### 方法2: Dockerで起動

1. **ComfyUIコンテナが存在するか確認**
   ```powershell
   docker ps -a --filter "name=comfyui"
   ```

2. **ComfyUIコンテナを起動**
   ```powershell
   docker start comfyui
   ```
   （コンテナ名に応じて変更）

3. **起動確認**
   - ブラウザで http://localhost:8188 を開く
   - ComfyUIのWeb UIが表示されればOK

### 方法3: バッチファイル/スクリプトで起動

1. **起動スクリプトを実行**
   ```powershell
   .\start_comfyui.ps1
   ```
   （スクリプトが存在する場合）

---

## ✅ Step 3: 起動確認

### 3-1. ComfyUIのWeb UIにアクセス

1. **ブラウザでComfyUIを開く**
   - http://localhost:8188 にアクセス

2. **ComfyUIのWeb UIが表示されることを確認**
   - ワークフローエディタが表示されればOK

### 3-2. Tool Serverから接続確認

1. **Tool ServerからComfyUIに接続できるか確認**
   ```powershell
   curl http://localhost:8188
   ```

2. **期待される結果:**
   - HTMLレスポンスが返る
   - エラーが返らない

---

## 📋 Tool Serverとの統合確認

### ComfyUI起動後、Tool Serverの`generate_image`ツールが使用可能

1. **OpenWebUIのチャット画面で質問を送信**
   ```
   ComfyUIで美しい風景の画像を生成して
   ```

2. **期待される動作:**
   - LLMが`generate_image`ツールを呼び出す
   - ComfyUI APIを叩いて画像を生成
   - 画像ファイルが保存され、ファイルパスが返る

---

## 🔧 トラブルシューティング

### 問題1: ComfyUIが起動しない

**原因:**
- Pythonがインストールされていない
- 依存関係がインストールされていない
- ポート8188が使用中

**解決方法:**
1. **Pythonがインストールされているか確認**
   ```powershell
   python --version
   ```

2. **依存関係をインストール**
   ```powershell
   cd C:\ComfyUI
   pip install -r requirements.txt
   ```

3. **ポート8188が使用中でないか確認**
   ```powershell
   netstat -ano | findstr :8188
   ```

### 問題2: ComfyUIに接続できない

**原因:**
- ComfyUIが起動していない
- ポート番号が間違っている
- ファイアウォールがブロックしている

**解決方法:**
1. **ComfyUIが起動しているか確認**
   ```powershell
   curl http://localhost:8188
   ```

2. **ポート番号を確認**
   - デフォルトは8188
   - 別のポートで起動している場合は、Tool Serverの設定を変更

3. **ファイアウォールの設定を確認**
   - ポート8188がブロックされていないか確認

---

## 📋 確認チェックリスト

- [ ] ComfyUIが起動中（http://localhost:8188）
- [ ] ComfyUIのWeb UIが表示される
- [ ] Tool ServerからComfyUIに接続できる
- [ ] Tool Serverの`generate_image`ツールが使用可能
- [ ] OpenWebUIのチャットで画像生成をテスト

---

## 🔥 レミ先輩の推奨

### 優先度1: ComfyUIの起動確認

1. **ComfyUIが起動しているか確認**
   - http://localhost:8188 にアクセス

2. **ComfyUIのWeb UIが表示されることを確認**

### 優先度2: Tool Serverとの統合確認

1. **Tool ServerからComfyUIに接続できるか確認**
   - `curl http://localhost:8188`

2. **OpenWebUIのチャットで画像生成をテスト**
   - 「ComfyUIで画像を生成して」と送信

---

**レミ先輩モード**: ComfyUIを起動すれば、Tool Serverの`generate_image`ツールが使用可能になる！🔥
