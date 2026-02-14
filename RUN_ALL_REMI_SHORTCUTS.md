# Remi: HTTP Shortcuts 一括実行

## 一覧確認

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File manaos_integrations/pixel7_list_remi_shortcuts.ps1
```

## 安全に一括実行（デフォルト）

- `GET` のみ実行します（例: Status / Dashboard）
- `stop/cleanup/emergency` を含む名前は危険扱いで除外されます

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File manaos_integrations/pixel7_run_all_remi_shortcuts.ps1
```

## POST も含めて実行

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File manaos_integrations/pixel7_run_all_remi_shortcuts.ps1 -IncludePost
```

## 危険系も含めて全部実行（注意）

- `🚨 Emergency Stop` や `Stop/Cleanup` 系も含まれます

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File manaos_integrations/pixel7_run_all_remi_shortcuts.ps1 -IncludePost -IncludeDangerous
```

## 出力

- 実行ごとに `manaos_integrations/_tmp_all_...` で UIダンプ/XML/スクショ等が保存されます（呼び出し先の `pixel7_run_http_shortcuts_action.ps1` 側の実装に依存）。

## メモ

- HTTP Shortcuts 側で表示ラベルが短縮されることがあります（例: `Remi Dashboard` が `Dashboard` 表示）。ランナー側はフォールバック探索するのでそのままでOKです。
