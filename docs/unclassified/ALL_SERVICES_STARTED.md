# ManaOS 全サービス起動完了

**起動日時**: 2026-01-11  
**状態**: ✅ 全サービス起動中（18/18）

---

## 🎉 起動完了！

全18サービスの起動が完了しました！

---

## ✅ 起動中サービス（18/18）

### コアサービス（11個）
1. ✅ Intent Router (5100)
2. ✅ Task Planner (5101)
3. ✅ Task Critic (5102)
4. ✅ RAG Memory (5103)
5. ✅ Task Queue (5104)
6. ✅ UI Operations (5105)
7. ✅ Unified Orchestrator (5106)
8. ✅ Executor Enhanced (5107)
9. ✅ Portal Integration (5108)
10. ✅ Content Generation (5109)
11. ✅ LLM Optimization (5110)

### その他
12. ✅ System Status API (5112)

### 拡張サービス（6個）
13. ✅ Personality System (5123)
14. ✅ Autonomy System (5124)
15. ✅ Secretary System (5125)
16. ✅ Learning System API (5126)
17. ✅ Metrics Collector (5127)
18. ✅ Performance Dashboard (5128)

### 統合APIサーバー
19. ✅ Unified API Server (9500)

---

## 🚀 起動方法

### 一括起動

```powershell
# 全サービスを一括起動
.\start_all_manaos_services.ps1
```

このスクリプトで、すべてのサービスが自動的に起動します。

---

## 📋 状態確認

### 全サービスの状態を確認

```powershell
# サービス状態確認
python check_service_status.py
```

### 統合APIサーバーの確認

```powershell
# ヘルスチェック
curl http://localhost:9500/health

# 統合状態確認
curl http://localhost:9500/api/integrations/status
```

---

## 🎯 Open WebUI統合

すべてのサービスが起動しているので、Open WebUIから以下が使用可能です：

- ✅ 記憶系（memory_store, memory_recall）
- ✅ 学習系（learning_record, learning_analyze, learning_get_preferences, learning_get_optimizations）
- ✅ 人格系（personality_get_persona, personality_get_prompt, personality_apply, personality_update）
- ✅ 自律系（autonomy_add_task, autonomy_execute_tasks, autonomy_list_tasks, autonomy_get_level）
- ✅ 秘書系（secretary_morning_routine, secretary_noon_routine, secretary_evening_routine）
- ✅ 母艦操作（Obsidian）（obsidian_create_note, obsidian_search_notes）
- ✅ VS Code操作（vscode_open_file, vscode_open_folder）

**合計23個のツールが利用可能**

---

## 💡 次のステップ

1. **Open WebUIで設定**
   - `openwebui_manaos_tools.json`を参考にツールを追加

2. **MCPサーバー経由で使用**
   - CursorのMCP設定でManaOS統合MCPサーバーを使用

3. **統合APIサーバー経由で使用**
   - HTTP API経由で直接アクセス

---

**🎉 すべてのサービスが起動しました！**
