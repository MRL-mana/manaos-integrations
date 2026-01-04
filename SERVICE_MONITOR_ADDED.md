# Service Monitor追加完了

**完了日時**: 2025-01-28

---

## ✅ 実施内容

### Service Monitorをstart_all_services.ps1に追加

**追加内容**:
- Service Monitor（ポート5111）をstart_all_services.ps1に追加
- ManaOS統合サービス数: 22サービス → 23サービス

**追加位置**:
```powershell
@{Name="LLM Optimization"; Port=5110; Script="llm_optimization.py"},
@{Name="Service Monitor"; Port=5111; Script="service_monitor.py"},  # 追加
@{Name="System Status API"; Port=5112; Script="system_status_api.py"},
```

---

## 🎯 Service Monitorの役割

### 機能
- **定期的なヘルスチェック**: 30秒間隔で各サービスの状態を確認
- **自動再起動**: サービス停止を検知した場合、自動的に再起動（最大5回）
- **メトリクス収集**: サービス状態、再起動回数、エラー情報を収集
- **ステータスレポート**: `/api/status`エンドポイントで状態を取得可能

### 監視対象サービス
- Intent Router（ポート5100）
- Task Planner（ポート5101）
- Task Critic（ポート5102）
- RAG Memory（ポート5103）
- Task Queue（ポート5104）
- UI Operations（ポート5105）
- Unified Orchestrator（ポート5106）
- Executor Enhanced（ポート5107）
- Portal Integration（ポート5108）
- Content Generation（ポート5109）
- LLM Optimization（ポート5110）

---

## 📊 常時起動設定状況

### 常時起動設定済み（5システム）

1. **ManaOS統合サービス（23サービス）**
   - Service Monitor含む
   - 自動起動設定済み

2. **Unified API Server（ポート9500）**
   - 自動起動設定済み

3. **n8n（ポート5678）**
   - 自動起動設定済み

4. **Ollama（ポート11434）**
   - 常時起動設定済み

5. **Service Monitor（ポート5111）**
   - start_all_services.ps1に追加済み
   - 自動起動設定済み（ManaOS統合サービス経由）

---

## 🔧 起動方法

### 手動起動
```powershell
# Service Monitor単体起動
python service_monitor.py

# 全サービス起動（Service Monitor含む）
.\start_all_services.ps1
```

### 自動起動
- ManaOS統合サービスとして自動起動設定済み
- システム起動時に自動的に起動

---

## 📝 確認方法

### ポート確認
```powershell
netstat -ano | findstr "5111"
```

### API確認
```powershell
curl http://localhost:5111/api/status
```

### ログ確認
```powershell
Get-Content logs\service_monitor.log -Tail 50
```

---

## ✅ 完了

Service Monitorがstart_all_services.ps1に追加され、常時起動設定が完了しました。

**次のステップ**:
- 次回のシステム起動時に自動的に起動
- 他のManaOSサービスを監視・自動再起動

---

**最終更新**: 2025-01-28

