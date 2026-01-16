# VS Code設定ガイド

このプロジェクトをVS Codeで効率的に開発するための設定が完了しました。

## 📋 作成された設定ファイル

### `.vscode/settings.json`
プロジェクト固有の設定：
- Python開発環境の設定
- PowerShellスクリプトの設定
- ファイルエンコーディング（UTF-8）
- エディタ設定（フォーマット、保存時処理など）
- ファイル除外設定

### `.vscode/extensions.json`
推奨拡張機能のリスト：
- Python開発ツール（Pylance、Black、Flake8など）
- PowerShell拡張機能
- Gitツール（GitLens、Git Graph）
- Markdown編集ツール
- JSON/YAML編集ツール

### `.vscode/launch.json`
デバッグ設定：
- Pythonスクリプトのデバッグ
- 統合APIサーバーのデバッグ
- PowerShellスクリプトのデバッグ
- pytestのデバッグ

### `.vscode/tasks.json`
タスク設定：
- 依存関係のインストール
- テスト実行
- サービスチェック
- MCP設定更新
- コードフォーマット・Lint

## 🚀 使い方

### 1. 拡張機能のインストール

VS Codeを開くと、右下に「推奨拡張機能をインストールしますか？」という通知が表示されます。
「すべてインストール」をクリックしてください。

または、手動でインストール：
1. `Ctrl+Shift+X` で拡張機能パネルを開く
2. 「推奨」タブを選択
3. 各拡張機能をインストール

### 2. Python環境の設定

1. `Ctrl+Shift+P` でコマンドパレットを開く
2. 「Python: Select Interpreter」を選択
3. 使用するPythonインタープリターを選択

### 3. デバッグの開始

1. `F5` キーを押すか、デバッグパネル（`Ctrl+Shift+D`）を開く
2. デバッグ設定を選択：
   - **Python: 現在のファイル** - 開いているPythonファイルを実行
   - **Python: 統合APIサーバー** - 統合APIサーバーを起動
   - **PowerShell: 現在のスクリプト** - 開いているPowerShellスクリプトを実行

### 4. タスクの実行

1. `Ctrl+Shift+P` でコマンドパレットを開く
2. 「Tasks: Run Task」を選択
3. 実行したいタスクを選択：
   - **Python: 依存関係インストール** - `requirements.txt`から依存関係をインストール
   - **Python: テスト実行** - pytestでテストを実行
   - **PowerShell: 全サービスチェック** - すべてのサービスをチェック
   - **Python: コードフォーマット（Black）** - コードを自動フォーマット

## 🎯 主な機能

### 自動フォーマット
- 保存時に自動的にコードをフォーマット（Black）
- インポート文の自動整理

### コード補完
- Python: Pylanceによる高度な型推論と補完
- PowerShell: 統合されたIntelliSense

### デバッグ
- ブレークポイントの設定
- 変数の監視
- ステップ実行

### 統合ターミナル
- PowerShellがデフォルトのターミナルとして設定
- 統合ターミナルでスクリプトを直接実行可能

## 📝 注意事項

### `.gitignore`について
`.vscode/`フォルダは`.gitignore`に含まれていますが、設定ファイルはプロジェクトに含めています。
チーム開発の場合は、`.gitignore`から`.vscode/`を除外するか、個人設定として扱ってください。

### 環境変数
デバッグ設定では`.env`ファイルを自動的に読み込みます。
`.env`ファイルが存在しない場合は、手動で環境変数を設定してください。

### Pythonインタープリター
仮想環境を使用している場合は、VS Codeで正しいインタープリターを選択してください。

## 🔧 カスタマイズ

### 設定の変更
`.vscode/settings.json`を編集することで、プロジェクト固有の設定を変更できます。

### デバッグ設定の追加
`.vscode/launch.json`に新しい設定を追加することで、他のスクリプトもデバッグ可能です。

### タスクの追加
`.vscode/tasks.json`に新しいタスクを追加することで、よく使うコマンドを簡単に実行できます。

## 🎨 コードスニペット

### Pythonスニペット

以下のプレフィックスでコードスニペットが利用できます：

- `flask-route` - Flask APIエンドポイント
- `flask-route-json` - Flask APIエンドポイント（JSONリクエスト）
- `mcp-tool` - MCPサーバーツール定義
- `mcp-list-tools` - MCPサーバーツール一覧定義
- `py-class-logger` - ロガー付きPythonクラス
- `error-handler` - 統一エラーハンドラー
- `async-def` - 非同期関数
- `http-request` - HTTPリクエスト（httpx）

### PowerShellスニペット

以下のプレフィックスでコードスニペットが利用できます：

- `ps-function` - PowerShell関数テンプレート
- `ps-header` - PowerShellスクリプトヘッダー
- `ps-service-check` - サービス状態チェック
- `ps-file-check` - ファイル存在チェック
- `ps-http-request` - HTTPリクエスト（PowerShell）
- `ps-write-color` - 色付き出力
- `ps-try-catch` - エラーハンドリング

## 🔧 REST Client

`.vscode/http-client.http`ファイルでAPIテストが可能です。

1. REST Client拡張機能をインストール（推奨拡張機能に含まれています）
2. `.vscode/http-client.http`を開く
3. リクエスト行の上に「Send Request」リンクが表示されます
4. クリックしてAPIをテスト

## ⌨️ カスタムキーバインド

以下のキーバインドが設定されています：

- `Ctrl+Shift+B` - 依存関係インストール
- `Ctrl+Shift+T` - テスト実行
- `Ctrl+Shift+F` - コードフォーマット（Black）
- `Ctrl+Shift+L` - Lint（Flake8）

## ✅ 次のステップ

1. **拡張機能をインストール** - 推奨拡張機能をすべてインストール
2. **Python環境を設定** - 使用するPythonインタープリターを選択
3. **依存関係をインストール** - タスクから「Python: 依存関係インストール」を実行
4. **デバッグを試す** - `F5`キーでデバッグを開始
5. **コードスニペットを試す** - Python/PowerShellファイルでスニペットを使用
6. **APIをテスト** - REST ClientでAPIエンドポイントをテスト

VS Codeで快適な開発を！
