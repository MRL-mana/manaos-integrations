# 🚀 ManaOSシステム起動ガイド

**作成日**: 2026-01-07

---

## ✅ 修正完了

1. **CrewAI統合のエラー修正**
   - `Process.sequential` のエラーを修正
   - オプショナルインポートに変更

2. **統合オーケストレーターの初期化確認**
   - ✅ 初期化成功
   - ✅ すべての自己能力システムが初期化完了

---

## 🚀 サーバー起動手順

### ⚠️ 重要: 新しいターミナルウィンドウで実行してください

**手順**:

1. **新しいPowerShellまたはコマンドプロンプトウィンドウを開く**

2. **以下のコマンドを実行**:

```bash
cd C:\Users\mana4\Desktop\manaos_integrations
python start_server_direct.py
```

3. **起動確認**:
   - サーバーが `http://127.0.0.1:9502` で起動することを確認
   - 初期化メッセージが表示されることを確認

4. **別のターミナルで状態確認**:

```bash
# ヘルスチェック
curl http://127.0.0.1:9502/health

# 詳細状態
curl http://127.0.0.1:9502/status
```

---

## 📊 初期化済みシステム

以下のシステムが正常に初期化されています:

- ✅ Comprehensive Self Capabilities System
- ✅ Self Evolution System
- ✅ Self Protection System
- ✅ Self Management System
- ✅ Self Diagnosis System
- ✅ Degraded Mode System
- ✅ Self Adjustment System
- ✅ ManaOS Service Bridge
- ✅ Learning System
- ✅ Unified Orchestrator
- ✅ その他すべての統合システム

---

## ✅ 運用開始確認

サーバーが起動したら、以下を確認してください:

- [ ] `/health` エンドポイントが応答する
- [ ] `/ready` エンドポイントが200を返す（初期化完了後）
- [ ] `/status` で詳細状態が取得できる

---

## ⚠️ 注意事項

1. **サーバー起動**: 新しいターミナルウィンドウで起動してください
2. **初期化時間**: 初期化には数分かかる場合があります
3. **停止方法**: 起動したターミナルで `Ctrl+C` を押してください

---

**次のステップ**: 新しいターミナルウィンドウで `python start_server_direct.py` を実行してサーバーを起動してください。









