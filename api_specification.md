# ManaOS API仕様書

**バージョン**: 1.0  
**最終更新**: 2025-01-28

---

## 📋 目次

1. [共通仕様](#共通仕様)
2. [エラーコード一覧](#エラーコード一覧)
3. [各サービスAPI](#各サービスapi)
4. [使用例](#使用例)

---

## 共通仕様

### ベースURL

```
http://localhost:{PORT}
```

### 共通エンドポイント

#### `GET /health`

ヘルスチェック

**レスポンス**:
```json
{
  "status": "healthy",
  "service": "Service Name"
}
```

### 共通エラーレスポンス

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "user_message": "User-friendly message",
    "category": "network|timeout|validation|configuration|resource|external_service|internal|unknown",
    "severity": "low|medium|high|critical",
    "service": "Service Name",
    "timestamp": "2025-01-28T12:00:00",
    "retryable": true,
    "details": {}
  }
}
```

---

## エラーコード一覧

### Network Errors

- `NET_CONNECTION_ERROR`: 接続エラー
- `NET_TIMEOUT_ERROR`: タイムアウトエラー

### Timeout Errors

- `TIM_TIMEOUT`: タイムアウト

### Validation Errors

- `VALIDATION_ERROR`: バリデーションエラー

### Configuration Errors

- `CONFIG_ERROR`: 設定エラー

### Resource Errors

- `RESOURCE_MEMORY_ERROR`: メモリエラー
- `RESOURCE_ERROR`: リソースエラー

### External Service Errors

- `EXT_SERVICE_ERROR`: 外部サービスエラー

### Internal Errors

- `INTERNAL_ERROR`: 内部エラー

---

## 各サービスAPI

### Intent Router (5100)

#### `POST /api/classify`

意図分類

**リクエスト**:
```json
{
  "text": "画像を生成して"
}
```

**レスポンス**:
```json
{
  "intent_type": "image_generation",
  "confidence": 0.9,
  "entities": {},
  "reasoning": "分類理由",
  "suggested_actions": ["execute_workflow"],
  "timestamp": "2025-01-28T12:00:00"
}
```

---

### Task Planner (5101)

#### `POST /api/plan`

実行計画作成

**リクエスト**:
```json
{
  "text": "画像を生成して"
}
```

**レスポンス**:
```json
{
  "plan_id": "plan_20250128_123456",
  "intent_type": "image_generation",
  "steps": [
    {
      "step_id": "step_1",
      "description": "画像生成ワークフローを実行",
      "action": "execute_workflow",
      "target": "image_generation",
      "parameters": {},
      "dependencies": [],
      "estimated_duration": 60,
      "priority": "high"
    }
  ],
  "total_estimated_duration": 60,
  "priority": "high"
}
```

---

### Task Critic (5102)

#### `POST /api/evaluate`

実行結果評価

**リクエスト**:
```json
{
  "intent_type": "image_generation",
  "original_input": "画像を生成して",
  "plan": {},
  "status": "completed",
  "output": {},
  "error": null,
  "duration": 45.5
}
```

**レスポンス**:
```json
{
  "evaluation": "success",
  "score": 0.9,
  "failure_reason": null,
  "issues": [],
  "improvements": [],
  "confidence": 0.95,
  "reasoning": "評価理由"
}
```

---

### Unified Orchestrator (5106)

#### `POST /api/execute`

タスク実行（エンドツーエンド）

**リクエスト**:
```json
{
  "text": "画像を生成して",
  "mode": "creative",
  "auto_evaluate": true,
  "save_to_memory": true
}
```

**レスポンス**:
```json
{
  "execution_id": "exec_20250128_123456",
  "input_text": "画像を生成して",
  "intent_type": "image_generation",
  "plan_id": "plan_20250128_123456",
  "task_id": "task_123456",
  "status": "completed",
  "result": {},
  "evaluation": {},
  "error": null,
  "created_at": "2025-01-28T12:00:00",
  "completed_at": "2025-01-28T12:01:00",
  "duration_seconds": 60.5
}
```

---

### SSOT API (5120)

#### `GET /api/ssot`

完全なSSOT取得

**レスポンス**:
```json
{
  "timestamp": "2025-01-28T12:00:00",
  "version": "1.0",
  "services": [...],
  "system": {...},
  "active_tasks": {...},
  "recent_inputs": [...],
  "last_error": {...},
  "summary": {...}
}
```

#### `GET /api/ssot/summary`

サマリーのみ取得

**レスポンス**:
```json
{
  "timestamp": "2025-01-28T12:00:00",
  "summary": {
    "total_services": 19,
    "up": 18,
    "down": 1,
    "unhealthy": 0
  },
  "system": {
    "cpu_percent": 25.5,
    "ram_percent": 53.1,
    "disk_percent": 50.0
  },
  "active_tasks": {
    "pending": 2,
    "running": 1,
    "total": 10
  },
  "last_error": {...}
}
```

---

## 使用例

### PowerShell

```powershell
# 意図分類
$body = @{
    text = "画像を生成して"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5100/api/classify" `
    -Method POST -Body $body -ContentType "application/json"
```

### Python

```python
import httpx

# 意図分類
response = httpx.post(
    "http://localhost:5100/api/classify",
    json={"text": "画像を生成して"}
)
result = response.json()
```

### cURL

```bash
# 意図分類
curl -X POST http://localhost:5100/api/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "画像を生成して"}'
```

---

**バージョン**: 1.0  
**最終更新**: 2025-01-28

