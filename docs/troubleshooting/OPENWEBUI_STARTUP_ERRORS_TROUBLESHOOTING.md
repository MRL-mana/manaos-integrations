# 🔧 OpenWebUI起動エラーのトラブルシューティング

## ❌ 問題

Consoleタブで以下のエラーが表示される：

1. **WebSocket接続エラー**: `ws://localhost:3001/ws/socket.io/` への接続が失敗
2. **GET エラー**: `http://127.0.0.1:3001/app/version.json` が `ERR_EMPTY_RESPONSE` を返す

## 🔍 原因

これらのエラーは、OpenWebUIがまだ完全に起動していないことを示しています。

## ✅ 解決方法

### Step 1: OpenWebUIコンテナの状態を確認

```powershell
docker ps -a --filter "name=open-webui" --format "{{.Names}}|{{.Status}}"
```

**確認事項**:
- コンテナが起動中か確認（Statusが「Up」になっているか）
- ポートが正しくマッピングされているか確認（3001:8080）

### Step 2: OpenWebUIが完全に起動するまで待機

**原因**: 再起動後、OpenWebUIが完全に起動するまで1～2分かかることがあります。

**解決方法**:
1. **1～2分待機**
2. **OpenWebUIにアクセス**: `http://127.0.0.1:3001`
3. **応答があるか確認**

### Step 3: OpenWebUIのログを確認

```powershell
docker logs --tail 50 open-webui
```

**確認事項**:
- エラーメッセージがないか確認
- 起動完了のメッセージがあるか確認

### Step 4: ブラウザを更新

1. **ブラウザを更新（F5）**
2. **エラーが解消されているか確認**
3. **Consoleタブでエラーが消えているか確認**

### Step 5: それでもエラーが続く場合

**OpenWebUIを再起動**:

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
docker-compose -f docker-compose.always-ready-llm.yml restart openwebui
```

**完全に再起動**:

```powershell
docker-compose -f docker-compose.always-ready-llm.yml stop openwebui
docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui
```

## 🔥 レミ先輩のアドバイス

### ✅ やるべき

1. **OpenWebUIが完全に起動するまで待機**
   - 再起動後、1～2分待機する

2. **ブラウザを更新**
   - OpenWebUIが完全に起動したら、ブラウザを更新（F5）

3. **エラーが解消されているか確認**
   - Consoleタブでエラーが消えているか確認
   - 「ツールの選択」ドロップダウンを確認

### ❌ やっちゃダメ

- 再起動後すぐにアクセスして問題を判断する
- エラーを無視してTool Serverの設定を進める
- ブラウザを更新せずに問題を判断する

## 📋 確認チェックリスト

- [ ] OpenWebUIコンテナが起動中（Status: Up）
- [ ] ポートが正しくマッピングされている（3001:8080）
- [ ] OpenWebUIが完全に起動するまで1～2分待機
- [ ] ブラウザを更新（F5）
- [ ] Consoleタブでエラーが消えているか確認
- [ ] 「ツールの選択」ドロップダウンを確認

## 🎯 次のステップ

1. **OpenWebUIが完全に起動するまで待機**（1～2分）
2. **ブラウザを更新（F5）**
3. **エラーが解消されているか確認**
4. **「ツールの選択」ドロップダウンを確認**

---

**レミ先輩モード**: OpenWebUIの再起動後、完全に起動するまで待機しよう！🔥
