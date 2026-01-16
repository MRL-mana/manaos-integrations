# 🐌 通信速度が遅い原因と改善策

## 📊 問題点の分析

### 1. **タイムアウト設定が長すぎる**

#### 問題箇所
- `llm_routing.py`: `timeout=300.0`（**5分！**）
- `manaos_timeout_config.json`: 
  - `llm_call: 30.0`秒
  - `workflow_execution: 300.0`秒（5分）
  - `external_service: 30.0`秒
- `rows_integration.py`: `timeout=30`秒

#### 影響
- リクエストが失敗しても5分待つまで応答がない
- ユーザー体験が悪い

---

### 2. **セッションプールが使われていない**

#### 問題箇所
- `llm_routing.py`: `requests.post`を直接呼び出し（セッションプール未使用）
- 多くのファイルで`requests.get`/`requests.post`を直接使用

#### 影響
- 毎回新しいTCP接続を確立する必要がある
- 接続確立に時間がかかる（通常50-200ms）

---

### 3. **リトライ設定が多すぎる**

#### 問題箇所
- `intelligent_retry.py`: 
  - `max_retries: 3`
  - `initial_delay: 1.0`秒
  - `max_delay: 60.0`秒
  - 指数バックオフ

#### 影響
- リトライが3回あると、最悪の場合：
  - 1回目: 1秒待機
  - 2回目: 2秒待機
  - 3回目: 4秒待機
  - **合計7秒以上**の遅延

---

### 4. **非同期クライアントが使われていない**

#### 問題箇所
- `manaos_async_client.py`は良い実装だが、多くの場所で同期の`requests`を使用

#### 影響
- 並列処理ができない
- 複数のAPI呼び出しが順次実行される

---

## 🚀 改善策

### 改善1: タイムアウト設定の最適化

```json
{
  "timeouts": {
    "health_check": 2.0,        // ✅ そのまま
    "api_call": 5.0,           // ✅ そのまま
    "llm_call": 15.0,          // ⬇️ 30.0 → 15.0（半分に）
    "llm_call_heavy": 30.0,    // ⬇️ 60.0 → 30.0（半分に）
    "workflow_execution": 120.0, // ⬇️ 300.0 → 120.0（2分に）
    "script_execution": 60.0,   // ✅ そのまま
    "command_execution": 30.0,  // ✅ そのまま
    "database_query": 10.0,     // ✅ そのまま
    "file_operation": 30.0,     // ✅ そのまま
    "network_request": 10.0,    // ✅ そのまま
    "external_service": 20.0    // ⬇️ 30.0 → 20.0
  }
}
```

### 改善2: セッションプールの使用

**変更前** (`llm_routing.py`):
```python
response = requests.post(
    f"{self.ollama_url}/api/generate",
    json=params,
    timeout=300.0
)
```

**変更後**:
```python
from http_session_pool import get_http_session_pool

session_pool = get_http_session_pool()
response = session_pool.request(
    "POST",
    f"{self.ollama_url}/api/generate",
    base_url=self.ollama_url,
    json=params,
    timeout=15.0  # タイムアウトも短縮
)
```

### 改善3: リトライ設定の最適化

```python
RetryConfig(
    max_retries=2,          # ⬇️ 3 → 2
    initial_delay=0.5,       # ⬇️ 1.0 → 0.5
    max_delay=10.0,         # ⬇️ 60.0 → 10.0
    exponential_base=2.0
)
```

### 改善4: 非同期クライアントの使用

**変更前**:
```python
response = requests.post(url, json=data, timeout=30)
```

**変更後**:
```python
async with AsyncUnifiedAPIClient() as client:
    result = await client.call_service(
        service="service_name",
        endpoint="/endpoint",
        method="POST",
        data=data,
        timeout=10.0
    )
```

---

## 📈 期待される改善効果

| 項目 | 改善前 | 改善後 | 改善率 |
|------|--------|--------|--------|
| LLM呼び出しタイムアウト | 30秒 | 15秒 | **50%削減** |
| ワークフロー実行タイムアウト | 300秒 | 120秒 | **60%削減** |
| 接続確立時間 | 50-200ms/回 | 0ms（再利用） | **100%削減** |
| リトライ最大遅延 | 7秒 | 1.5秒 | **78%削減** |

---

## 🔧 実装優先順位

### 優先度1（即座に実施）
1. ✅ タイムアウト設定の最適化
2. ✅ `llm_routing.py`のタイムアウト短縮（300秒 → 15秒）

### 優先度2（今週中）
3. ✅ セッションプールの使用（`llm_routing.py`など）
4. ✅ リトライ設定の最適化

### 優先度3（来週）
5. ✅ 非同期クライアントへの移行（段階的）

---

## 📝 注意事項

- タイムアウトを短くしすぎると、正常なリクエストもタイムアウトする可能性がある
- 段階的に短縮して、エラー率を監視する
- 特にLLM呼び出しは、モデルサイズによって応答時間が大きく変わる

---

## 🎯 次のステップ

1. タイムアウト設定ファイルを更新
2. `llm_routing.py`のタイムアウトを修正
3. セッションプールの使用を推進
4. パフォーマンステストを実施
