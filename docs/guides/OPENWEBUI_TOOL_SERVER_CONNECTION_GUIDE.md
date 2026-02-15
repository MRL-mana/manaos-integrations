# 🔥 OpenWebUI → Tool Server 接続ガイド（完全版）

## ⚠️ 99%ここで事故る：Dockerからlocalhostは「自分自身」

**重要ポイント：**

OpenWebUIはDockerコンテナ上で動作しているため、**OpenWebUIにとって `localhost:9503` は「コンテナ自身」**を指します。

→ Tool Server（Windowsホスト）には届かない可能性が高い。

---

## ✅ 正解URL（Windowsホストに繋ぐ場合）

OpenWebUI側で登録するURLは、以下を使用してください：

### ① Windows + Docker Desktop の定番（推奨）

✅ **`http://host.docker.internal:9503`**
✅ **OpenAPI URL**: `http://host.docker.internal:9503/openapi.json`

これが一番ラクで最強。

### ② それでもダメなら（IP直指定）

WindowsのIPアドレスを調べて使用：

例：`http://192.168.0.10:9503`
OpenAPI URL: `http://192.168.0.10:9503/openapi.json`

---

## 📋 OpenWebUI側の設定手順（完全版）

### Step 1: OpenWebUIにアクセス

1. **ブラウザでOpenWebUIを開く**
   - http://127.0.0.1:3001 にアクセス
   - ログイン（必要に応じて）

### Step 2: 「外部ツール」設定画面を開く

1. **左サイドバーの「設定」→「外部ツール」をクリック**
   - または、URLから直接: http://127.0.0.1:3001/admin/settings/external-tools

### Step 3: 「接続を追加」をクリック

1. **「接続を追加」ボタンをクリック**

### Step 4: 以下の情報を入力

**重要：URLは `host.docker.internal` を使用**

1. **種類 (Type)**
   - 「オープンAPI (OpenAPI)」を選択（通常は既に選択されている）

2. **URL (APIベースURL)**
   ```
   http://host.docker.internal:9503
   ```
   ⚠️ **`localhost`ではなく`host.docker.internal`を使用**

3. **OpenAPI仕様URL**
   ```
   openapi.json
   ```
   - または、完全なURL: `http://host.docker.internal:9503/openapi.json`
   - トグルスイッチがON（緑色）になっていることを確認

4. **認証 (Authentication)**
   - 「なし (None)」または「パブリック (Public)」を選択
   - ⚠️ **「APIキー (API Key)」を選択しない**

5. **名前 (Name)**
   ```
   manaOS Tool Server
   ```

6. **説明 (Description)**（任意）
   ```
   Docker/service status, log check, ComfyUI image generation
   ```

7. **耐性 (Tolerance)**
   - 「プライベート (Private)」または「パブリック (Public)」のまま

8. **その他のフィールド**
   - ヘッダー: 空欄のまま
   - ID: 空欄のまま（自動生成）
   - 関数名フィルターリスト: 空欄のまま
   - グループ: デフォルトのまま

### Step 5: 「保存」をクリック

1. **「保存」ボタンをクリック**

2. **接続状態を確認**
   - 「Connected」になっているか確認
   - 「Disconnected」または「Error」の場合、以下を確認：
     - URLが正しいか（`host.docker.internal`を使用しているか）
     - Tool Serverが起動中か（http://127.0.0.1:9503/health）
     - OpenAPI仕様が取得できるか（http://127.0.0.1:9503/openapi.json）

---

## ✅ 接続チェックの“最短ルート”

### 1) Tool Server単体確認（既にOK）

ブラウザで以下にアクセス：

- `http://127.0.0.1:9503/openapi.json`
- `http://127.0.0.1:9503/health`

### 2) OpenWebUIコンテナからホストへ届くか確認

**OpenWebUIコンテナ内からcurl**できるか確認（できると勝ち確）

OpenWebUIコンテナ内で実行：

```bash
# OpenWebUIコンテナに入る
docker exec -it open-webui /bin/sh

# または、コンテナ内にcurlがある場合
docker exec open-webui curl http://host.docker.internal:9503/health
docker exec open-webui curl http://host.docker.internal:9503/openapi.json
```

これが通れば **Connected確定**。

---

## 📋 OpenWebUI側の設定で見るべきポイント

### 接続状態

- 「Connected」表示になるか
- エラーメッセージがないか

### ツールの表示

「ツールの選択」ドロップダウンで以下のツールが表示されるか：

- `service_status`
- `check_errors`
- `generate_image`

### Function Calling

- 「高なパラメータ」セクションで「関数呼び出し」を確認
- 「有効 (Enabled)」または「自動 (Auto)」に設定

---

## 🔍 トラブルシューティング

### 問題1: 「Disconnected」または「Error」が表示される

**原因:**
- URLが間違っている（`localhost`を使用している）
- Tool Serverが起動していない
- ネットワークの問題

**解決方法:**
1. URLを `http://host.docker.internal:9503` に変更
2. Tool Serverが起動中か確認（http://127.0.0.1:9503/health）
3. OpenWebUIコンテナから接続確認（上記のcurlコマンド）

### 問題2: ツールが表示されない

**原因:**
- 接続状態が「Disconnected」
- 「関数呼び出し」が無効
- ブラウザのキャッシュ

**解決方法:**
1. 接続状態を「Connected」にする
2. 「関数呼び出し」を「有効 (Enabled)」または「自動 (Auto)」に設定
3. ブラウザのキャッシュをクリア（F5またはCtrl + F5）

### 問題3: `host.docker.internal`で接続できない

**原因:**
- Docker Desktopの設定
- Windowsのネットワーク設定

**解決方法:**
1. WindowsのIPアドレスを確認：
   ```powershell
   ipconfig
   ```
2. IPアドレスを直接指定：
   ```
   http://192.168.0.10:9503
   ```
   （実際のIPアドレスに置き換える）

---

## 🔥 レミ先輩の辛口まとめ（重要ポイントだけ）

### ✅ 完璧な状態

- Tool Server：FastAPIで正常起動 ✅
  `http://127.0.0.1:9503`
- OpenWebUI：Dockerで正常起動 ✅
  `http://127.0.0.1:3001`
- エンドポイント構造：公式と一致 ✅
  `/service_status` `/check_errors` `/generate_image`
- OpenAPI：取得できる ✅

### ⚠️ 問題が起きるとしたら次の1個だけ

> **OpenWebUI（Dockerコンテナ）から Tool Server（Windowsホスト）に繋げられるか？**

### ✅ 正解URL

**`localhost:9503`で繋がらなかったら、それは正常な挙動**

**`host.docker.internal:9503`を使えば勝てる可能性が激高**

---

## 📋 確認チェックリスト

- [ ] Tool Serverが起動中（http://127.0.0.1:9503/health）
- [ ] OpenAPI仕様が取得できる（http://127.0.0.1:9503/openapi.json）
- [ ] OpenWebUIの「外部ツール」設定画面でTool Serverを登録
- [ ] **URL: `http://host.docker.internal:9503`**（`localhost`ではない）
- [ ] **OpenAPI URL: `http://host.docker.internal:9503/openapi.json`**（`localhost`ではない）
- [ ] 認証: 「なし (None)」または「パブリック (Public)」
- [ ] 接続状態が「Connected」
- [ ] 「ツールの選択」ドロップダウンでツールが表示される
- [ ] 「関数呼び出し」が「有効 (Enabled)」または「自動 (Auto)」に設定

---

**レミ先輩モード**: Tool Serverは完璧！問題は接続だけ！`host.docker.internal`を使えば勝てる！🔥
