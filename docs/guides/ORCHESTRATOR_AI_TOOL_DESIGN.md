# AI向け汎用オーケストレーターツール設計

## 概要

外部記事で紹介された「**ask_orchestrator 一本化**」の設計思想と、ManaOS の Unified Orchestrator との対応をまとめます。
クライアント（AIマスコット・チャットボット・卓上端末）は **1つのツールだけ** 知っていればよく、オーケストレータ側が意図解釈・スキル解決・実行・フォールバックを担います。

---

## 設計の核心

> **「AIに“何ができるか”を覚えさせるのをやめた」**

- **クライアント（LLM）**: 意図理解と会話。「知らないことは ask_orchestrator に投げる」だけ。
- **オーケストレータ**: 世界と手を動かす存在。判断・分岐・実行・失敗時の扱いをすべて背負う。

```
LLM = 意図理解 + 会話
Orchestrator = 世界と手を動かす存在
```

---

## v4.0 と v4.1 の違い

| 項目 | v4.0（機能ごとツール） | v4.1（汎用1本） |
|------|------------------------|-----------------|
| クライアント | get_room_environment, get_weather, check_schedule, play_music... とツールが増える | **ask_orchestrator(query)** のみ |
| 機能追加 | クライアント側のツール定義を毎回改修 | オーケストレータ側のスキル追加だけで完了 |
| フォールバック | ツールがない＝できない | スキルなし → SKILL_NOT_FOUND → LLM に戻して自力回答 |

---

## ManaOS での対応

ManaOS では次のように対応しています。

| 記事の概念 | ManaOS での実装 |
|------------|------------------|
| ask_orchestrator(query) | **Unified Orchestrator** `POST /api/execute`（`text` または `query` で自然文を受け付ける） |
| オーケストレーションAPI | `unified_orchestrator.py`（ポート 5106） |
| スキル解決・意図分類 | Intent Router（5100）→ Task Planner（5101）→ Task Queue（5104） |
| スキルが無い場合 | 意図が `unknown` または計画不可のとき **SKILL_NOT_FOUND** を返し、クライアントが LLM に戻す |

### 呼び出し例

```http
POST http://localhost:5106/api/execute
Content-Type: application/json

{
  "text": "部屋の温度教えて",
  "mode": null,
  "auto_evaluate": true,
  "save_to_memory": true
}
```

- **text** または **query**: 自然文でのリクエスト（どちらか一方でよい。`ask_orchestrator(query)` 互換のため `query` を利用可能）。
- オーケストレータが Intent Router で意図を分類し、該当スキルがあれば実行、なければ `SKILL_NOT_FOUND` を返します。

---

## クライアント側のツール定義例（Gemini / マスコット）

AIクライアントには **1ツールだけ** 定義します。

```json
{
  "name": "ask_orchestrator",
  "description": "室温・湿度・天気・照明操作など、ローカル環境に関する情報取得や操作を行う。一般的な知識や検索はこのツールを使わず、Grounding（Google検索）で対応する。",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "自然文でのリクエスト内容"
      }
    },
    "required": ["query"]
  }
}
```

- マスコットは「部屋の温度教えて」「明日の天気は？」→ `ask_orchestrator`
- 「最近のニュース教えて」→ Grounding（検索）など、LLMが使い分けます。

---

## フォールバック設計（SKILL_NOT_FOUND）

ユーザーのリクエストに対応するスキルがオーケストレータに無い場合:

1. オーケストレータは **SKILL_NOT_FOUND** を返す（HTTP 200 の正常レスポンスとして）。
2. クライアントは「ツールでは対応できなかった」と解釈し、**LLM にそのまま返す**。
3. LLM は自己知識や検索（Grounding）で回答する。

```
ユーザー: 「東京タワーの高さは？」
  → ask_orchestrator → SKILL_NOT_FOUND
  → LLM に戻す → 自己知識 or 検索で回答
  → 「333mです」
```

ユーザーからは「裏でスキルが見つからなかった」ことは見えず、**止まらないAI** として振る舞います。

### 共通レスポンス仕様（全入口で固定）

**5106 / Portal / Open WebUI / MCP** のどの入口からでも、返却は次の形に統一されています（返し方がブレると地獄なので固定）。

```json
{
  "status": "ok | skill_not_found | tool_error | error",
  "message": "SKILL_NOT_FOUND | ...",
  "input_text": "...",
  "result": { ... },
  "meta": {
    "trace_id": "exec_...",
    "confidence": 0.0,
    "assumption": ""
  }
}
```

| フィールド | 型 | 説明 |
|------------|-----|------|
| `status` | `"ok"` \| `"skill_not_found"` \| `"tool_error"` \| `"error"` | 必ず文字列で固定。`skill_not_found` のときは LLM に戻す。`tool_error` はスキル実行失敗、`error` はシステムエラー。 |
| `message` | string | 人間／ログ用。`SKILL_NOT_FOUND` やエラー文言。 |
| `input_text` | string | 元の自然文。 |
| `result` | object | 実行結果のペイロード。 |
| `meta.trace_id` | string | ログ突合の命綱（5106 の execution_id）。 |
| `meta.portal_trace_id` | string | Portal 経由時のみ。上流追跡用（Portal ログ突合）。「Portal で落ちた」の切り分けが秒速になる。 |
| `meta.confidence` | number | 将来: 解釈の確信度（0–1）。 |
| `meta.assumption` | string | 将来: 解釈の前提（例: 「天井ライトを想定」）。 |

クライアントは `status === "skill_not_found"` のときに LLM に戻す処理を入れます。ログは `meta.trace_id`（5106）と `meta.portal_trace_id`（Portal）で突き合わせます。

### 将来拡張（confidence / assumption）

オーケストレータ側から `result` 内に `confidence` / `assumption` を返すと、`meta` に流し込まれます。LLM が言い直しや確認を促す制御に使えます。

---

## 導入・統合ガイド（ManaOS）

### 前提

- **Unified Orchestrator** が起動していること（`python unified_orchestrator.py`、ポート 5106）。

### 1. API の窓口

| 用途 | エンドポイント | 備考 |
|------|----------------|------|
| 直接オーケストレータを叩く | `POST http://localhost:5106/api/execute` | ボディ: `{"query": "自然文"}` または `{"text": "自然文"}` |
| Portal 経由（同一ホストで Portal がある場合） | `POST http://<PortalのURL>/api/ask_orchestrator` | ボディ: `{"query": "自然文"}` |

### 2. AI クライアントへのツール追加

- **Gemini / マスコット**: 本文の「クライアント側のツール定義例」をそのまま使う。パラメータは `query` のみ。
- **Open WebUI**: `openwebui_manaos_tools.json` の先頭にある **ask_orchestrator** を有効にする。1ツールだけ使う場合はこれのみ有効にするとオーケストレータ中心になる。
- **ツール定義ファイル**: `config/ask_orchestrator_tool.json` に名前・説明・パラメータ・API URL をまとめてある。他クライアント用にコピーして使える。

### 3. MCP（Cursor 等）での利用

- **unified_api_mcp_server** に **ask_orchestrator** ツールを追加済み。MCP 経由で「自然文を投げる」だけでオーケストレータが実行する。

### 4. 動作確認

```bash
# オーケストレータ直接
curl -X POST http://localhost:5106/api/execute -H "Content-Type: application/json" -d "{\"query\": \"部屋の温度教えて\"}"

# Portal 経由（Portal が起動している場合）
curl -X POST http://<PortalのURL>/api/ask_orchestrator -H "Content-Type: application/json" -d "{\"query\": \"部屋の温度教えて\"}"
```

レスポンスの `status` が `skill_not_found` のときは、クライアント側で LLM に戻す処理を入れる。

### 5. 推奨の使い分け（現場ルール）

| 用途 | 入口 | 理由 |
|------|------|------|
| **開発・内部** | 5106 直叩き | 最短経路。デバッグ・検証向け。 |
| **外部クライアント** | Portal 経由 | 認証・制限・ログ集約。タイムアウト短め（8〜15秒）で UX 死ぬの防止。 |
| **Cursor** | MCP | 人間の作業導線に溶ける。自然文1本で叩ける。 |
| **Open WebUI** | ツール1本モード（ask_orchestrator） | オーケストレータ中心運用。 |

### 6. 事故防止（Portal 側）

- **タイムアウト**: Portal → 5106 は外部クライアント用のため短め（デフォルト 12 秒）。`PORTAL_ORCHESTRATOR_TIMEOUT` で変更可。
- **多重発火防止**: 同一リクエストの重複実行を抑えるため、Portal で `idempotency_key`（なければ `query`/`text` のハッシュ）で数秒の重複排除キャッシュを実施。照明の点滅・音楽の連続再生などの事故を軽減。
- **同時二発抑止（inflight）**: 同じキーで 5106 実行中に後続が来た場合、後続は「待って同じ結果」を受け取る。同時二発が 1 回に収束する。
- **idempotency のスコープ**: 現在は **in-memory 単体プロセス前提**。gunicorn 複数ワーカーや Portal を 2 台にする場合は、idempotency store を **Redis** にすると分散でも効く（将来対応）。

### 7. status の 2 段階（error / tool_error）

運用では `error` を次のように分けるとクライアントの扱いが明確になる。

| status | 意味 | クライアントの扱い |
|--------|------|---------------------|
| `skill_not_found` | 該当スキルなし | LLM へフォールバック |
| `tool_error` | スキル実行はしたが失敗（デバイス死、認証切れ等） | ユーザーへ「デバイス側が死んでる」等の説明 |
| `error` | システムエラー（例外・HTTP失敗） | 「内部で失敗した、再試行して」系 |

5106 の `to_unified_response()` では、実行結果の `result.result` に `status: "tool_error"` があれば `status: "tool_error"` として返す。Executor 側でツール失敗時にその形を返すと、クライアントで上記の分岐ができる。

**tool_error の標準エラーコード（文字列）**
`message` だけだと解析・監視が辛いため、`result` 内に `error_code` を固定しておくと楽。

| error_code | 意味 |
|------------|------|
| `DEVICE_UNREACHABLE` | デバイスに到達できない |
| `AUTH_EXPIRED` | 認証切れ |
| `RATE_LIMITED` | レート制限 |
| `TIMEOUT` | 実行タイムアウト |

Executor が `result.result = {"status": "tool_error", "message": "...", "error_code": "DEVICE_UNREACHABLE"}` のように返すと、監視・アラートで status 別に通知先を変えやすい。

### 8. 仕上げの一発テスト

事故防止が期待どおり動いているか確認するテストを用意している。

```bash
# Portal（例: 5107）と 5106 を起動した状態で
python scripts/test_ask_orchestrator_safety.py
```

| テスト | 内容 |
|--------|------|
| 1. 同一リクエスト連打（5回） | 同じ query を短時間に 5 回送る → すべて同じ `meta.trace_id`（キャッシュで 1 回に収束） |
| 2. 同時 2 発（並列） | 同じ query を 2 スレッドで同時送信 → 同じ `meta.trace_id`（inflight で 1 回に収束） |
| 3. unknown → skill_not_found | 「東京タワーの高さは？」等 → `status === "skill_not_found"`（LLM フォールバック用） |

環境変数 `PORTAL_URL`（デフォルト `http://localhost:5108`）で Portal の URL を指定できる。

### 9. Portal → 5106 の転送ヘッダ（上流追跡）

Portal は 5106 呼び出し時に **`X-Portal-Trace-Id`** ヘッダで `portal_trace_id` を付与する。5106 側でこのヘッダをログに出すと、Portal ログと 5106 ログの相互参照が楽になる（レスポンスの `meta.portal_trace_id` に加えて、転送時点から追える）。

---

## 次の伸びしろ: 監視強化

Redis 化は「スケールした時の必須」だが、**監視は今日から効く**。最初の一手としてコスパが高いもの。

### まず集計したいもの（ログ→集計）

| 種別 | 内容 |
|------|------|
| **status 別カウンタ** | `ok` / `skill_not_found` / `tool_error` / `error` の件数 |
| **tool_error の error_code 別** | `DEVICE_UNREACHABLE` / `AUTH_EXPIRED` / `RATE_LIMITED` / `TIMEOUT` 等の件数 |
| **Portal タイムアウト** | Portal → 5106 の転送でタイムアウトした件数 |

これだけでも「どこが壊れているか」の可視化が一気に上がる。

---

## status 別アラート設計（叩き台・このまま使える形）

運用は「通知うるさすぎると止める」前提。**緊急だけ即通知＋それ以外は集計して定時レポ** がおすすめ。

### アラート設計の基本方針

* **即通知**: 止まる / 危険 / 放置すると損
* **集計**: 傾向監視（スパムを避ける）

### 1) status: `ok`

* **通知**: なし
* メトリクスにはカウント（成功率を見るため）

### 2) status: `skill_not_found`

* **通知**: なし（基本）。フォールバックでユーザー体験は止まらないため。
* **例外**: 急に増えたら「スキル不足」なので **日次/週次レポで可視化**。

**レポで見る指標**

* 上位クエリ（どんな要求が多いか）
* ヒット率（skills found %）

→ 次に何をスキル化するかの優先順位になる。

### 3) status: `tool_error`（現実世界が壊れてる）

通知したいが **うるさくしない** が肝。

| error_code | 通知方針 | 備考 |
|------------|----------|------|
| `AUTH_EXPIRED` | **即通知（高優先）** | 放置すると全部失敗し続ける。通知文に「更新手順」リンク/コマンドを添付。 |
| `DEVICE_UNREACHABLE` | **即通知（中優先）** | 電源/ネット/デバイス死。連続したら抑制（後述のレート制御）。 |
| `RATE_LIMITED` | **即通知しない（低優先）** | まず自動リトライ/バックオフで吸収。「5分で20回超」等の閾値超えたら通知。 |
| `TIMEOUT` | **状況次第** | 単発は無視でOK。「15分でN回」超えたら通知（負荷/外部API遅延の兆候）。 |

### 4) status: `error`（内部の例外/バグ/転送失敗）

* **通知**: **即通知（高優先）**
* Portal タイムアウトと区別したい（後述）

### Portal タイムアウト：通知方針

Portal タイムアウトは UX 影響が大きいので扱いは `error` に近い。

* **単発**: 通知なしでもよい（ネット瞬断ありえる）
* **連続**: 即通知（例: 直近5分で3回 / 15分で10回）

### 通知先：Slack vs ダッシュボード（おすすめ運用）

最初は **Slack 即通知＋ダッシュボード集計** のハイブリッドが強い。

**Slack に出す（即時）**

* `error`（内部エラー）
* `tool_error: AUTH_EXPIRED`
* `tool_error: DEVICE_UNREACHABLE`（連続時）
* Portal タイムアウト（連続時）

**ダッシュボードに集約（傾向）**

* status 別カウンタ（ok / skill_not_found / tool_error / error）
* tool_error の error_code 別
* top skill_not_found queries（次のスキル化候補）

### アラートの「うるささ」制御（必須）

通知は **必ず抑制** を入れる。これがないと人は通知を切る。

| ルール | 内容 |
|--------|------|
| 同一 `portal_trace_id` | 1回だけ（当然） |
| 同一 `error_code` | **30分に1回まで** |
| 重大エラー | **最初の1回＋復旧時1回**（例: DEVICE_UNREACHABLE 発生→通知、直った→復旧通知） |

### 通知メッセージのテンプレ（Slack向け）

最低限入れておくと現場で動ける：

* status / error_code
* query（短縮）
* trace_id / portal_trace_id
* 対処の次の一手（1行）

**例**

```
[AUTH_EXPIRED] SwitchBot token expired.
対応: トークン更新 → 再起動
portal_trace_id=... trace_id=... query="ライトつけて"
```

### 運用方針で決める1点

Slack にするかダッシュボードにするかより先に、これを決めると一気に固まる：

**「即通知を受け取りたい時間帯」**

* 24時間？
* 8:00〜20:00だけ？
* 深夜はまとめて朝？

ここが決まると通知疲れが減る。

---

**次のステップ**: 「Slackで行く」で確定なら、**アラート抑制の具体ルール（閾値）** を決める。例: `AUTH_EXPIRED` は即、`DEVICE_UNREACHABLE` は5分で2回以上、`TIMEOUT` は15分で5回以上、など。

---

## 本格運用（メトリクス＋アラート）

### 有効化

Portal 起動時に **`orchestrator_operational_metrics`** を import できると、自動で以下が有効になる。

* 毎リクエストの **メトリクス記録**（status 別・error_code 別・Portal タイムアウト）
* **抑制付きアラート**（同一 error_code は 30 分に 1 回まで、Portal タイムアウトは直近 5 分で 3 回超で通知）

### 環境変数（任意）

| 変数 | 説明 | デフォルト |
|------|------|------------|
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook（アラート送信先） | 未設定時は `slack_integration.send_to_slack` にフォールバック |
| `ORCHESTRATOR_ALERT_CHANNEL` | Slack チャンネル（Bot Token 利用時） | 未設定時は #general 等 |
| `ORCHESTRATOR_ALERT_SUPPRESSION_MINUTES` | 同一キーで通知を抑止する分数 | 30 |

### 集計取得（ダッシュボード用）

```http
GET http://<PortalのURL>/api/orchestrator/stats
```

戻り値例:

```json
{
  "status": { "ok": 10, "skill_not_found": 2, "tool_error": 0, "error": 0 },
  "error_code": {},
  "portal_timeout_total": 0,
  "portal_timeout_last_5min": 0,
  "last_5min_by_status": { "ok": 5, "skill_not_found": 1 },
  "updated_at": "2026-02-02T12:00:00"
}
```

ダッシュボードや日次レポでこの API を叩いて可視化する。

### 実装ファイル

* **`orchestrator_operational_metrics.py`**: 集計・抑制・Slack テンプレ
* **Portal**: 成功時は `record_and_maybe_alert(body)`、Portal タイムアウト時は `record_and_maybe_alert({}, is_portal_timeout=True)`

---

## ManaOS 統合（本格運用・Slack 通知）

### 方針

**Slack 通知で本格運用する** 場合、ManaOS 側は次のように揃える。

1. **環境変数**（`.env` または OS 環境変数）
   * **Slack**: `SLACK_WEBHOOK_URL` を設定すると ask_orchestrator のアラートが Webhook で送信される。未設定の場合は `SLACK_BOT_TOKEN` で `slack_integration.send_to_slack` にフォールバック。
   * **オプション**: `ORCHESTRATOR_ALERT_CHANNEL`（Slack チャンネル）、`ORCHESTRATOR_ALERT_SUPPRESSION_MINUTES=30`、`PORTAL_ORCHESTRATOR_TIMEOUT=12`。
   * 一覧は `env.example` の「ask_orchestrator 本格運用」を参照。

2. **起動**
   * **Unified Orchestrator（5106）** と **Portal（例: 5108）** を起動する。
   * Portal 起動時に `orchestrator_operational_metrics` が import できれば、メトリクス＋アラートが自動で有効になる（追加の起動スクリプトは不要）。

3. **集計（ダッシュボード用）**
   * **`GET http://<PortalのURL>/api/orchestrator/stats`** で status 別・error_code 別・Portal タイムアウト件数を取得。
   * ManaOS ダッシュボードや日次レポでこの URL を叩いて可視化する。

4. **Runbook との関係**
   * `create_runbook.py` の「Unified Orchestrator (5106)」「Portal Integration (5108)」を起動しておけば、本格運用の土台は揃う。
   * Slack 用の env を設定すれば、error / tool_error / Portal タイムアウト連続時に抑制付きで Slack に通知される。

### 確認用コマンド（例）

```bash
# 一括確認（推奨）
python scripts/check_orchestrator_production_ready.py
# Windows（本格運用スタート＝起動確認＋次のステップ表示）
scripts\start_orchestrator_production.ps1
scripts\check_orchestrator_production_ready.bat

# 5106 と Portal のヘルス
curl -s http://localhost:5106/health
curl -s http://localhost:5108/health

# 集計取得（Portal 経由）
curl -s http://localhost:5108/api/orchestrator/stats
```

### 統合ダッシュボードでの集計表示

**ManaOS 統合状態ダッシュボード**（`system_integration_dashboard.py`、ポート 9400）に **ask_orchestrator 集計** カードを追加済み。Portal が起動していれば、ダッシュボードの `/api/status` 取得後に Portal の `/api/orchestrator/stats` をプロキシして表示する。環境変数 `PORTAL_URL`（デフォルト `http://localhost:5108`）で Portal の URL を指定できる。

**ManaOS 統合 API（9500）** からも `GET /api/orchestrator/stats` で集計を取得できる（Portal へのプロキシ）。9500 を使っているクライアントは同じ URL で集計を叩ける。

---

## まとめ

| ポイント | 内容 |
|----------|------|
| **ツール定義が増えない** | LLM のコンテキストを汚さず、モデル差し替えが容易 |
| **クライアントが増えても壊れない** | マスコット・チャットUI・卓上端末が同じ API を叩く |
| **失敗を自然に誤魔化せる** | SKILL_NOT_FOUND → LLM に戻す → ユーザー体験は途切れない |
| **新機能はスキル追加だけ** | オーケストレータ側にファイルを置くだけでよく、クライアント改修不要 |

Unified Orchestrator の実装詳細は `unified_orchestrator.py` および `docs/棚卸し_母艦とまなOSとサーバー.md` を参照してください。
