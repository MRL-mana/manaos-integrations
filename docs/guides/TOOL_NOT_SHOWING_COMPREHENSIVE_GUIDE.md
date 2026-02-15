# 🔧 ツールが表示されない問題の総合ガイド

## ❌ 問題

OpenWebUIで「ツールの選択」ドロップダウンにTool Serverのツールが表示されない。

## 🔍 確認済み項目

### ✅ 正常に動作している項目

1. **Tool Server**: 正常に動作中（http://127.0.0.1:9503）
2. **OpenAPI仕様**: 正常に取得可能（http://127.0.0.1:9503/openapi.json）
3. **Tool Serverの登録**: OpenWebUIに登録済み（http://127.0.0.1:9503）
4. **Function Calling**: 「ネイティブ」モードに設定済み
5. **OpenWebUI**: 起動中（v0.6.43）

### ❌ 問題がある可能性のある項目

1. **Tool Serverの接続状態**: Connectedになっているか未確認
2. **ブラウザのキャッシュ**: クリアしていない可能性
3. **OpenAPI仕様の形式**: OpenWebUIが期待する形式と合っているか未確認

## 📋 解決方法（優先順位順）

### Step 1: OpenWebUIの設定でTool Serverの接続状態を確認

1. **OpenWebUIの設定画面を開く**
   - 右上の設定アイコン（⚙️）をクリック
   - 左メニューから「External Tools」または「Tool Servers」タブを選択

2. **Tool Serverの接続状態を確認**
   - `http://127.0.0.1:9503` が登録されているか確認
   - **接続状態が「Connected」になっているか確認**（重要）
   - 「Connected」になっていない場合、接続ボタンをクリック

3. **接続できない場合**
   - Tool Serverが起動中か確認（http://127.0.0.1:9503/health）
   - OpenAPI仕様が取得できるか確認（http://127.0.0.1:9503/openapi.json）
   - エラーメッセージがないか確認

### Step 2: ブラウザのキャッシュを完全にクリアして再起動

1. **キャッシュをクリア**
   - Chrome/Edge: `Ctrl + Shift + Delete` → キャッシュされた画像とファイルを選択 → 「期間」を「全期間」に設定 → クリア
   - Firefox: `Ctrl + Shift + Delete` → キャッシュを選択 → 「期間」を「すべて」に設定 → クリア

2. **ブラウザを完全に再起動**
   - すべてのタブを閉じる
   - ブラウザを完全に終了（タスクマネージャーで確認）
   - ブラウザを再起動

3. **OpenWebUIにアクセス**
   - `http://127.0.0.1:3001` にアクセス
   - 「ツールの選択」ドロップダウンを確認

### Step 3: OpenWebUIのバージョンを確認

現在のバージョン: **v0.6.43**

**最新バージョンを確認**:
```powershell
docker pull ghcr.io/open-webui/open-webui:main
docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui
```

### Step 4: 開発者ツールで詳細確認

1. **開発者ツールを開く**（F12）
2. **Networkタブを開く**
3. **「ツールの選択」ドロップダウンを開く**
4. **以下のリクエストを確認**:
   - `/api/v1/tools/` へのリクエスト
   - `http://127.0.0.1:9503/openapi.json` へのリクエスト
5. **Consoleタブでエラーメッセージを確認**

### Step 5: Tool Serverを再登録

1. **OpenWebUIの設定画面を開く**（⚙️ → External Tools）
2. **既存のTool Serverを削除**
   - `http://127.0.0.1:9503` を削除
3. **Tool Serverを再登録**
   - 「Add Tool」または「ツールを追加」をクリック
   - URL: `http://127.0.0.1:9503`
   - OpenAPI Spec: ON（チェックを入れる）
   - OpenAPI Spec URL: `http://127.0.0.1:9503/openapi.json`
   - 保存

## 🔥 レミ先輩の推奨順序

### 優先度1: Tool Serverの接続状態を確認（最も重要）

- OpenWebUIの設定でTool Serverが「Connected」になっているか確認
- なっていない場合、接続を試みる

### 優先度2: ブラウザのキャッシュを完全にクリア

- キャッシュを完全にクリアして再起動
- これが最も効果的な場合が多い

### 優先度3: Tool Serverを再登録

- 既存の登録を削除して再登録
- 設定を初期化して再設定

### 優先度4: OpenWebUIのバージョン確認と更新

- 最新バージョンに更新
- バグ修正が含まれている可能性

## 📋 確認チェックリスト

- [ ] Tool ServerがOpenWebUIに登録されている
- [ ] Tool Serverの接続状態が「Connected」になっている
- [ ] ブラウザのキャッシュを完全にクリアした
- [ ] ブラウザを完全に再起動した
- [ ] OpenWebUIのバージョンを確認した
- [ ] 開発者ツール（F12）でエラーを確認した
- [ ] NetworkタブでTool Serverへのリクエストを確認した
- [ ] Tool Serverを再登録した

## 🎯 次のステップ

上記の手順を順番に実行して、問題が解決するか確認してください。

特に、**Tool Serverの接続状態が「Connected」になっているか確認**することが最も重要です。

---

**レミ先輩モード**: まずTool Serverの接続状態を確認しよう！Connectedになっていないとツールが表示されない！🔥
