# 🔥 OpenWebUI Tool Server登録ガイド

## 📋 「接続を追加」ダイアログでの入力情報

### ✅ 必須項目

1. **URL (APIベースURL)** ⚠️重要⚠️
   ```
   http://host.docker.internal:9503
   ```
   - Tool ServerのベースURLを入力
   - ⚠️ **`localhost`ではなく`host.docker.internal`を使用**
   - OpenWebUIはDockerコンテナ上で動作しているため、`localhost`ではTool Server（Windowsホスト）に到達できません
   - Windows + Docker Desktopの場合、`host.docker.internal`を使用してください

2. **OpenAPI仕様URL** ⚠️重要⚠️
   ```
   http://host.docker.internal:9503/openapi.json
   ```
   - または、`openapi.json`（相対パス）
   - ⚠️ **`localhost`ではなく`host.docker.internal`を使用**
   - Tool Serverは `http://host.docker.internal:9503/openapi.json` から仕様を取得します

3. **名前 (Name)**
   ```
   manaOS Tool Server
   ```
   - Tool Serverの表示名を入力

### 📋 推奨設定

4. **認証 (Authentication)**
   - **現状**: APIキー (API Key)
   - **推奨**: なし (None) または パブリック (Public)
   - **理由**: Tool Serverは認証なしで動作します
   - **注意**: 認証が「APIキー」のままの場合、APIキーを入力する必要があります

5. **説明 (Description)**
   ```
   Docker/service status, log check, ComfyUI image generation
   ```
   - Tool Serverの説明を入力（任意）

6. **耐性 (Tolerance)**
   - **現状**: プライベート (Private)
   - **推奨**: パブリック (Public) または プライベート (Private) のまま
   - **注意**: プライベートのままでも問題ありません

### 📋 任意項目

7. **ヘッダー (Header)**
   - 空欄のまま（JSON形式で追加のヘッダーが必要な場合のみ入力）

8. **ID (任意)**
   - 空欄のまま（自動生成されます）

9. **関数名フィルターリスト (Function Name Filter List)**
   - 空欄のまま（すべての関数を使用する場合）
   - 特定の関数のみを使用する場合: `service_status,check_errors,generate_image`

10. **グループ (Group)**
    - デフォルトのまま

---

## 🎯 入力手順

1. **URLを入力**
   - `http://localhost:9503` を入力

2. **OpenAPI仕様URLを確認**
   - `openapi.json` が選択されていることを確認
   - トグルスイッチがON（緑色）になっていることを確認

3. **認証を変更（推奨）**
   - 「認証 (Authentication)」の「APIキー」をクリック
   - 「なし」または「パブリック」を選択

4. **名前を入力**
   - `manaOS Tool Server` を入力

5. **説明を入力（任意）**
   - `Docker/service status, log check, ComfyUI image generation` を入力

6. **「保存」をクリック**

---

## 🔥 レミ先輩の推奨

### 優先度1: 必須項目を入力

1. **URL**: `http://localhost:9503`
2. **OpenAPI仕様URL**: `openapi.json`（既に選択済み）
3. **名前**: `manaOS Tool Server`

### 優先度2: 認証を変更

1. **認証を「なし」または「パブリック」に変更**
   - Tool Serverは認証なしで動作します
   - APIキーが不要です

### 優先度3: その他の設定

1. **説明を入力**（任意）
2. **耐性は「プライベート」のまま**（問題なし）

---

## 📋 確認チェックリスト

- [ ] URL: `http://localhost:9503` を入力
- [ ] OpenAPI仕様URL: `openapi.json` が選択されている
- [ ] OpenAPI仕様のトグルスイッチがON（緑色）
- [ ] 認証を「なし」または「パブリック」に変更
- [ ] 名前: `manaOS Tool Server` を入力
- [ ] 説明を入力（任意）
- [ ] 「保存」をクリック

---

## 🎯 次のステップ

1. **「保存」をクリック**
2. **Tool Serverの接続状態を確認**
   - 「Connected」になっているか確認
3. **チャット画面に戻る**
4. **「ツールの選択」ドロップダウンで確認**
   - Tool Serverのツール（service_status, check_errors, generate_image）が表示されることを確認

---

**レミ先輩モード**: 必須項目を入力して「保存」をクリック！認証は「なし」または「パブリック」に変更することを推奨！🔥
