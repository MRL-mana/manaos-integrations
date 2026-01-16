# 🧪 Cursor MCP設定のテスト方法

## ✅ Cursor再起動後の確認事項

### 1. MCPサーバーが認識されているか確認

Cursorのコマンドパレット（`Ctrl+Shift+P`）で以下を実行：
- `MCP: Show Servers` または `MCP: List Servers`

`llm-routing` サーバーが表示されていればOKです。

### 2. MCPツールが利用可能か確認

Cursorのチャットで以下を試してください：

```
@llm-routing analyze_difficulty このコードをリファクタリングして
```

または

```
@llm-routing get_available_models
```

### 3. 利用可能なMCPツール

#### `analyze_difficulty`
プロンプトの難易度を分析します。

**使用例：**
```
@llm-routing analyze_difficulty このシステムのアーキテクチャを設計して
```

#### `route_llm`
難易度に応じて最適なモデルを選択し、LLMにリクエストを送信します。

**使用例：**
```
@llm-routing route_llm このコードを最適化して
```

#### `get_available_models`
利用可能なLLMモデル一覧を取得します。

**使用例：**
```
@llm-routing get_available_models
```

---

## 🔧 トラブルシューティング

### MCPサーバーが表示されない場合

1. **設定ファイルを確認**
   ```powershell
   # MCP設定ファイルのパス
   $env:APPDATA\Cursor\User\globalStorage\rooveterinaryinc.roo-cline\cline_mcp_settings.json
   ```

2. **設定を再適用**
   ```powershell
   .\llm_routing_mcp_server\add_to_cursor_mcp.ps1
   ```

3. **Cursorを再起動**

### エラーが発生する場合

1. **サービスが起動しているか確認**
   ```powershell
   .\check_running_status.ps1
   ```

2. **ログを確認**
   - LLMルーティングAPIのログ
   - 統合APIサーバーのログ

---

## 📊 動作確認の流れ

1. ✅ Cursorを再起動
2. ✅ MCPサーバーが認識されているか確認
3. ✅ 簡単なタスクでテスト
4. ✅ 高難易度タスクでテスト（14B/32Bモデルがある場合）

---

**準備完了です！CursorからLLMルーティング機能を使い始めましょう！🎉**


















