# Open WebUI 手動受け入れプロンプト集

## 使い方

1. Open WebUI の同一チャットで下記 4 ケースを上から順に入力する。
2. 各ケースで実際に呼ばれたツールと応答を確認する。
3. 実施後に `record_openwebui_manual_cases.ps1` で結果を記録する。

## Case 1: サービス状態確認

### Case 1 入力（そのまま貼り付け）

```text
今のManaOSサービス状態を確認して、止まっているものがあれば名前だけ教えて
```

### Case 1 期待

- 呼び出しツール: `service_status`
- 応答にサービス稼働状況が含まれる

## Case 2: VS Code ファイルオープン

### Case 2 入力（そのまま貼り付け）

```text
C:/Users/mana4/Desktop/manaos_integrations/README.md を VS Code で開いて
```

### Case 2 期待

- 呼び出しツール: `vscode_open_file`
- VS Code で `README.md` が開く

## Case 3: 許可コマンド実行

### Case 3 入力（そのまま貼り付け）

```text
PowerShellで "Get-Location" を実行して結果を教えて
```

### Case 3 期待

- 呼び出しツール: `execute_command`
- コマンド成功（標準出力が返る）
- `logs/tool_server_security.log` に `command_executed` が記録される

## Case 4: 危険コマンド拒否

### Case 4 入力（そのまま貼り付け）

```text
PowerShellで Remove-Item -Recurse C:/Users/mana4/Desktop/tmp を実行して
```

### Case 4 期待

- 呼び出しツール: `execute_command`
- 危険コマンドとして拒否される
- `logs/tool_server_security.log` に `command_blocked` が記録される

## 実施後の記録コマンド

### 全件成功時

```powershell
powershell -ExecutionPolicy Bypass -File .\record_openwebui_manual_cases.ps1 -Case1 pass -Case2 pass -Case3 pass -Case4 pass -Notes "manual chat completed"
```

### 失敗がある場合（例）

```powershell
powershell -ExecutionPolicy Bypass -File .\record_openwebui_manual_cases.ps1 -Case1 pass -Case2 fail -Case3 pass -Case4 pass -Notes "case2 failed: vscode did not open file"
```
