# サーバー起動エラー修正完了

## 修正内容

**エラー**: `AssertionError: View function mapping is overwriting an existing endpoint function: rows_batch_update`

**原因**: `unified_api_server.py`で`/api/rows/batch/update`エンドポイントが重複定義されていた

**修正**: 1668行目の重複定義を削除

---

## サーバー再起動

修正が完了したので、サーバーを再起動してください:

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python start_server_with_notification.py
```

---

## 起動確認

サーバーが起動したら、別のターミナルで以下を実行:

```powershell
python check_server_status.py
```

または、ブラウザで以下にアクセス:
- http://127.0.0.1:9510/health
- http://127.0.0.1:9510/status
- http://127.0.0.1:9510/ready

---

**修正日**: 2025-12-29











