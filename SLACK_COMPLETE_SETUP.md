# Slack App完全設定ガイド

## 🎯 この機会に設定すべき項目

Slack Integrationを完全に機能させるために、以下の設定をまとめて行いましょう。

---

## 1. ✅ Bot Events（現在設定中）

### 既に追加済み
- ✅ `app_mentions` - Botメンション
- ✅ `message.im` - DM（直接メッセージ）

### 追加推奨イベント

#### チャンネルメッセージ（オプション）
- `message.channels` - パブリックチャンネルのメッセージ
  - **説明**: パブリックチャンネルでメッセージが投稿されたときに通知
  - **用途**: チャンネル全体の会話に参加
  - **Required Scope**: `channels:history`

#### ファイル共有（オプション）
- `file_shared` - ファイルが共有されたとき
  - **説明**: ファイルがアップロードされたときに通知
  - **用途**: ファイル処理や分析
  - **Required Scope**: `files:read`

#### リアクション（オプション）
- `reaction_added` - リアクションが追加されたとき
  - **説明**: メッセージにリアクションが追加されたときに通知
  - **用途**: リアクションに基づく処理
  - **Required Scope**: `reactions:read`

---

## 2. 🔑 OAuth & Permissions（必須）

### Bot Token Scopes（推奨）

#### 基本権限
- ✅ `app_mentions:read` - Botメンションを読み取る
- ✅ `im:history` - DMの履歴を読み取る
- ✅ `im:write` - DMを送信する
- ✅ `chat:write` - メッセージを送信する

#### 追加推奨権限
- `channels:history` - チャンネルの履歴を読み取る（チャンネルメッセージを使用する場合）
- `channels:read` - チャンネル情報を読み取る
- `files:read` - ファイルを読み取る（ファイル処理を使用する場合）
- `reactions:read` - リアクションを読み取る
- `users:read` - ユーザー情報を読み取る
- `users:read.email` - ユーザーのメールアドレスを読み取る

### User Token Scopes（通常は不要）
- 現在の実装では不要

---

## 3. ⚡ Slash Commands（オプション）

### 便利なSlash Commands例

#### `/manaos` - ManaOSコマンド実行
- **Command**: `/manaos`
- **Request URL**: `https://unrevetted-terrie-organometallic.ngrok-free.dev/api/slack/commands`
- **Short Description**: ManaOSコマンドを実行
- **Usage Hint**: `[command]`

#### `/file-secretary` - File Secretaryコマンド
- **Command**: `/file-secretary`
- **Request URL**: `https://unrevetted-terrie-organometallic.ngrok-free.dev/api/slack/commands`
- **Short Description**: File Secretaryコマンドを実行
- **Usage Hint**: `[command]`

---

## 4. 🎨 Interactive Components（オプション）

### ボタンやメニューを使用する場合

- **Request URL**: `https://unrevetted-terrie-organometallic.ngrok-free.dev/api/slack/interactive`
- **用途**: ボタンクリック、メニュー選択などのインタラクティブな操作

---

## 5. 📱 App Home（オプション）

### ホームタブを有効化

- **用途**: Botのホーム画面をカスタマイズ
- **設定**: 「App Home」→「Show Tabs」→「Home Tab」をON

---

## 6. 🔔 Event Subscriptions（現在設定中）

### Request URL
```
https://unrevetted-terrie-organometallic.ngrok-free.dev/api/slack/events
```

### Subscribe to bot events
- ✅ `app_mentions`
- ✅ `message.im`
- （オプション）`message.channels`
- （オプション）`file_shared`
- （オプション）`reaction_added`

---

## 📋 設定チェックリスト

### 必須項目
- [x] Event Subscriptionsを有効化
- [x] Request URLを設定
- [x] Bot Eventsを追加（`app_mentions`, `message.im`）
- [ ] OAuth & Permissionsで必要な権限を追加
- [ ] Verification Tokenを環境変数に設定
- [ ] Slack Integrationを再起動

### オプション項目
- [ ] 追加のBot Events（`message.channels`, `file_shared`など）
- [ ] Slash Commandsの設定
- [ ] Interactive Componentsの設定
- [ ] App Homeの設定

---

## 🚀 推奨設定手順

### Step 1: Bot Events（完了）
- ✅ `app_mentions`
- ✅ `message.im`

### Step 2: OAuth & Permissions
1. **「OAuth & Permissions」を開く**
2. **「Bot Token Scopes」で以下を追加:**
   - `chat:write` - メッセージを送信
   - `users:read` - ユーザー情報を読み取る
   - `channels:read` - チャンネル情報を読み取る（オプション）

### Step 3: Verification Token設定
1. **「Basic Information」→「App Credentials」を開く**
2. **「Verification Token」をコピー**
3. **環境変数に設定:**
   ```powershell
   $env:SLACK_VERIFICATION_TOKEN = "your_verification_token"
   ```
4. **Slack Integrationを再起動**

### Step 4: Appをワークスペースにインストール
1. **「Install App」を開く**
2. **「Install to Workspace」をクリック**
3. **権限を確認して「許可する」をクリック**

---

## 💡 現在の実装で使用している機能

- ✅ Botメンション（`app_mentions`）
- ✅ DM（`message.im`）
- ✅ Webhook URL送信（`chat:write`）
- ✅ ローカルLLM会話機能

---

## 🎉 完了

**この機会に必要な設定をまとめて行いましょう！**

特に重要なのは:
1. **OAuth & Permissions**で`chat:write`権限を追加
2. **Verification Token**を環境変数に設定
3. **Appをワークスペースにインストール**

これで完全に動作するようになります！

