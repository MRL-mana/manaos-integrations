# VSCode vs Cursor 比較ガイド

ManaOS IntegrationsをVSCodeとCursorで使う際の違いと、それぞれの利点をまとめました。

---

## 📊 機能比較

| 機能 | VSCode | Cursor | 備考 |
|------|--------|--------|------|
| **基本機能** | ✅ | ✅ | どちらも同じVSCodeベース |
| **タスク実行** | ✅ | ✅ | `.vscode/tasks.json` を共有 |
| **Python開発** | ✅ | ✅ | 同じ拡張機能を使用 |
| **デバッグ** | ✅ | ✅ | 同じ設定ファイル |
| **AI補完** | 拡張機能次第 | ✅ 標準搭載 | Cursorの強み |
| **MCP統合** | 手動設定 | ✅ ネイティブ | Cursorの強み |
| **軽量性** | ✅ | △ | VSCodeの方が軽い |
| **安定性** | ✅ 非常に高い | ✅ 高い | VSCodeの方が枯れている |

---

## 🎯 推奨される使い分け

### VSCodeを使うべき場合

✅ **安定性重視**
- 本番環境での作業
- 重要なコードの編集
- 長時間の作業セッション

✅ **軽量性重視**
- リソースが限られたマシン
- 複数のエディタを同時起動
- リモートSSH接続

✅ **標準環境**
- チーム開発での統一環境
- CI/CD パイプライン
- 標準的なPython開発

### Cursorを使うべき場合

✅ **AI支援重視**
- コード生成の頻繁な利用
- リファクタリング支援
- コードレビュー支援

✅ **MCP統合**
- ManaOSのMCPサーバーを頻繁に使用
- AI Agentとの対話が必要
- 自動化されたワークフロー

✅ **実験的開発**
- 新機能の試作
- アイデアの素早い検証
- プロトタイピング

---

## 🔧 共通設定ファイル

### 両方で使える設定

以下のファイルはVSCodeとCursorで**完全に共有**されます：

```
.vscode/
├── tasks.json          # タスク定義（共通）
├── launch.json         # デバッグ設定（共通）
├── extensions.json     # 推奨拡張機能（共通）
├── settings.json       # ワークスペース設定（共通）
└── keybindings.json    # キーバインド（共通）
```

### エディタ固有の設定

```
.cursor/
└── mcp.json           # Cursor専用のMCP設定

~/.vscode/
└── settings.json      # VSCode個人設定

~/.cursor/
└── mcp.json           # Cursor個人設定
```

---

## 🚀 ManaOS の使い方（両エディタ共通）

### 1. サービス起動

どちらのエディタでも同じタスクを使用：

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: すべてのサービスを起動"
```

または

```
Ctrl+Shift+B （デフォルトビルドタスク）
```

### 2. ヘルスチェック

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: サービスヘルスチェック"
```

### 3. 緊急停止

```
Ctrl+Shift+P → "Tasks: Run Task" → "🚨 ManaOS: 緊急停止"
```

---

## 🔌 MCP統合の違い

### Cursorでの使用

**設定ファイル:** `~/.cursor/mcp.json`

**特徴:**
- ✅ ネイティブMCPサポート
- ✅ AIチャットからMCPツールを直接呼び出し
- ✅ Composer機能との統合
- ✅ 自動的にサーバーを起動・管理

**設定例:**
```json
{
  "mcpServers": {
    "manaos-unified": {
      "command": "python",
      "args": ["-m", "manaos_unified_mcp_server.server"],
      "env": {
      "MANAOS_INTEGRATION_API_URL": "http://127.0.0.1:9502",
        "PYTHONPATH": "C:\\Users\\mana4\\Desktop\\manaos_integrations"
      },
      "cwd": "C:\\Users\\mana4\\Desktop\\manaos_integrations"
    }
  }
}
```

### VSCodeでの使用

**方法:** REST API経由

**特徴:**
- REST APIで統合（`http://127.0.0.1:9502`）
- 独自の拡張機能開発が必要
- Task Providerとして統合可能

**使用例:**
```powershell
# PowerShellから直接API呼び出し
$response = Invoke-RestMethod -Uri "http://127.0.0.1:9502/api/integrations/status"
$response | ConvertTo-Json
```

---

## 💡 ベストプラクティス

### 両方を併用する場合

1. **基本開発はVSCode**
   - 安定した環境で基本実装
   - デバッグや詳細な分析

2. **AI支援が必要な時はCursor**
   - コード生成
   - リファクタリング
   - ドキュメント作成

3. **設定ファイルを共有**
   - `.vscode/` 配下は両方で使える
   - Git管理して同期

### 設定の同期

```powershell
# VSCodeからCursorへ設定をコピー
Copy-Item -Recurse ~/.vscode/extensions ~/.cursor/
Copy-Item ~/.vscode/settings.json ~/.cursor/

# .vscode/ は自動的に共有される（同じワークスペース）
```

---

## 🆚 パフォーマンス比較

### 起動時間

| エディタ | 起動時間 | メモリ使用量 |
|---------|----------|--------------|
| VSCode | 1-2秒 | 200-300MB |
| Cursor | 2-3秒 | 300-400MB |

**結論:** VSCodeの方がわずかに軽量

### ManaOS サービスへの影響

どちらのエディタを使用しても、ManaOSサービス自体のパフォーマンスは**同じ**です。
サービスは独立したPythonプロセスとして動作するため。

---

## 🔄 エディタ間の移行

### CursorからVSCodeへ移行

1. **拡張機能を確認**
   ```
   Ctrl+Shift+X → インストール済み拡張機能の一覧
   ```

2. **同じ拡張機能をVSCodeにインストール**
   ```
   VSCodeで .vscode/extensions.json の推奨拡張をインストール
   ```

3. **MCP設定を確認**
   - Cursorの `mcp.json` は使えない
   - REST API（ポート9502）経由でアクセス

4. **個人設定を移行（オプション）**
   ```powershell
   Copy-Item ~/.cursor/settings.json ~/.vscode/settings.json -Confirm
   ```

### VSCodeからCursorへ移行

1. **MCP設定を追加**
   - `~/.cursor/mcp.json` を作成
   - [VSCODE_SETUP_GUIDE.md](VSCODE_SETUP_GUIDE.md) 参照

2. **拡張機能は自動で引き継がれる**
   - VSCodeの拡張機能はCursorでも動作

3. **設定ファイルは共有**
   - `.vscode/` 配下はそのまま使える

---

## 📝 推奨セットアップ

### 初心者向け

**VSCode単独**
- シンプルで安定
- チュートリアルやドキュメントが豊富
- トラブルシューティングしやすい

### 中級者向け

**VSCode + Cursor併用**
- 基本開発はVSCode
- AI支援が必要な時だけCursor
- 両方のメリットを活用

### 上級者向け

**Cursor主体 + VSCodeをサブ**
- 日常的にCursorを使用
- 本番環境やCI/CDはVSCode
- MCPサーバーをフル活用

---

## 🆘 トラブルシューティング

### 両方で同時に開くとどうなる？

**安全:** 問題なく両方で開けます
- ファイルシステムベースなので競合しない
- ただし、同じファイルを同時編集すると保存時に警告

### 設定が反映されない

**原因:** グローバル設定とワークスペース設定の優先順位

**対処:**
1. ワークスペース設定を優先
2. グローバル設定は最小限に
3. 設定を確認： `Ctrl+,` → "Open Settings (JSON)"

---

**最終更新**: 2026年2月7日  
**推奨:** 用途に応じて使い分け
