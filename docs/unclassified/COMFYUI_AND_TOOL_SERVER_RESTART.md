# 🔥 ComfyUI起動 & Tool Server再起動ガイド

## 📋 手順

### Step 1: ComfyUIを起動

#### 方法1: 起動スクリプトを使用（推奨）

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\start_comfyui_svi.ps1
```

**注意:** 別のPowerShellウィンドウで実行することを推奨します（Tool Serverの再起動のため）

#### 方法2: 手動で起動

```powershell
cd C:\ComfyUI
python main.py --port 8188
```

**起動確認:**
- ブラウザで http://localhost:8188 にアクセス
- ComfyUIのWeb UIが表示されればOK

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

**再起動後:**
- ✅ `check_errors`ツールの修正が反映されます
- ✅ `service_name`が指定されなくても動作します
- ✅ すべてのDockerコンテナのログを確認できます

---

## ✅ 確認チェックリスト

- [ ] ComfyUIが起動中（http://localhost:8188）
- [ ] Tool Serverが再起動中（http://localhost:9503/health）
- [ ] `check_errors`ツールの修正が反映されている
- [ ] OpenWebUIのチャットで`check_errors`ツールをテスト

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
ComfyUIで画像を生成して
```

**期待される動作:**
- ✅ ComfyUIが起動中なので、画像生成が可能
- ✅ `generate_image`ツールが呼び出される

---

## 🔥 レミ先輩の推奨

### 優先度1: ComfyUIを起動

1. **ComfyUIを起動**
   - 別のPowerShellウィンドウで実行
   - Tool Serverの再起動のため

2. **起動確認**
   - http://localhost:8188 にアクセス

### 優先度2: Tool Serverを再起動

1. **現在のTool Serverを停止**
   - `Ctrl + C` で停止

2. **Tool Serverを再起動**
   - `.\START_TOOL_SERVER_HOST.ps1` を実行

3. **修正が反映されていることを確認**
   - `check_errors`ツールをテスト

---

**レミ先輩モード**: ComfyUIを起動してからTool Serverを再起動！これで完璧！🔥
