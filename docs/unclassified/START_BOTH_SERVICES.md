# 🔥 ComfyUI & Tool Server 起動手順

## 📋 起動手順

### Step 1: ComfyUIを起動 ✅

ComfyUIを別ウィンドウで起動しました。

**起動確認:**
- ブラウザで http://localhost:8188 にアクセス
- ComfyUIのWeb UIが表示されればOK

**起動に時間がかかる場合:**
- 初回起動時は数分かかる場合があります
- モデルのダウンロードが必要な場合があります

---

### Step 2: Tool Serverを再起動

#### 現在のTool Serverを停止

Tool Serverを実行しているPowerShellウィンドウで：
- `Ctrl + C` を押して停止

#### Tool Serverを再起動

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\START_TOOL_SERVER_HOST.ps1
```

**または、別ウィンドウで起動:**

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\mana4\Desktop\manaos_integrations'; .\START_TOOL_SERVER_HOST.ps1"
```

**再起動後:**
- ✅ `check_errors`ツールの修正が反映されます
- ✅ `service_name`が指定されなくても動作します
- ✅ すべてのDockerコンテナのログを確認できます
- ✅ ComfyUIが起動中なので、`generate_image`ツールも使用可能になります

---

## ✅ 確認チェックリスト

- [ ] ComfyUIが起動中（http://localhost:8188）
- [ ] Tool Serverが再起動中（http://localhost:9503/health）
- [ ] `check_errors`ツールの修正が反映されている
- [ ] OpenWebUIのチャットで`check_errors`ツールをテスト
- [ ] OpenWebUIのチャットで`generate_image`ツールをテスト

---

## 🎯 テスト

### テスト1: check_errorsツール

**OpenWebUIのチャットで:**
```
最近のログにエラーがないか確認して
```

**期待される動作:**
- ✅ `service_name`を指定しなくても動作
- ✅ すべてのDockerコンテナのログを確認
- ✅ エラーパターンを検索して返す

### テスト2: generate_imageツール

**OpenWebUIのチャットで:**
```
ComfyUIで美しい風景の画像を生成して
```

**期待される動作:**
- ✅ ComfyUIが起動中なので、画像生成が可能
- ✅ `generate_image`ツールが呼び出される
- ✅ 画像が生成される

---

## 🔥 レミ先輩の推奨

### 優先度1: ComfyUIの起動確認

1. **ComfyUIが起動しているか確認**
   - http://localhost:8188 にアクセス

2. **起動に時間がかかる場合**
   - 数分待ってから確認

### 優先度2: Tool Serverの再起動

1. **現在のTool Serverを停止**
   - `Ctrl + C` で停止

2. **Tool Serverを再起動**
   - `.\START_TOOL_SERVER_HOST.ps1` を実行

3. **修正が反映されていることを確認**
   - `check_errors`ツールをテスト

---

**レミ先輩モード**: ComfyUIを起動しました！次はTool Serverを再起動して、修正を反映させましょう！🔥
