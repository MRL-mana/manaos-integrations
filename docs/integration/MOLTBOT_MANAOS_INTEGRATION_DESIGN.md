# Moltbot × まなOS 統合設計（分離型・安全運用）

まなOS = 司令塔 / Moltbot = 手足（限定権限）。直結せず「1本のゲート」で Plan を渡し、承認フローと監査ログで安全に運用する。

---

## 流れ（A → B → 本物）

| 段階 | やること | 判定 |
|------|----------|------|
| **A** | このはで Gateway を外部公開（Nginx/Basic/HTTPS）。母艦から 200/401/429 を取る。 | 3 点揃ったら A 完了 |
| **B** | Gateway の executor を `EXECUTOR=moltbot` に切替。list_files だけ通す。execute.jsonl 確認。 | runner `list_only` で監査が増える |
| **本物** | `MOLTBOT_DAEMON_URL` または `MOLTBOT_CLI_PATH` を設定し、`executor/moltbot.py` に本物呼び出しを実装。その後 file_move 等を解放。 | runner で実機 list / move が動く |

- A 手順: `moltbot_gateway/deploy/CHECKLIST_A_EXTERNAL.md`、取り方: `HOW_TO_GET_200_401_429.md`、一発: `check_external_200_401_429.ps1` / `.sh`
- **母艦だけでやる**（このはサーバーは使わない）: `moltbot_gateway/deploy/MOTHERSHIP_ONLY.md`。Gateway も runner も母艦で起動し、localhost で完結。
- B 手順: `moltbot_gateway/deploy/CHECKLIST_B_MOLTBOT.md`。list_files だけ: `python manaos_moltbot_runner.py list_only`
- **本格運用**: `moltbot_gateway/deploy/CHECKLIST_PRODUCTION.md`。常駐・監査ローテ・SECRET ローテ・本物切替・ロールバック・n8n 連携

---

## 1. 前提・方針

| 役割 | 担当 |
|------|------|
| 意図解釈・タスク分解・最終判断・監査ログ | まなOS |
| 実行（ブラウザ操作・ファイル整理・定型作業） | Moltbot（外付けエンジン） |
| スケジュール・通知・データ搬送 | n8n（既存） |

- Moltbot は **公式リポジトリ以外から入れない**（偽拡張・マルウェア対策）
- 実行は **段階解放**（Phase 1 → 2 → 3）
- **人間の最終承認** を「外部送信・支払い・削除・認証情報」に必ず挟む

---

## 2. Plan JSON スキーマ（まなOS → Moltbot ゲート）

まなOSが「この手順で、ここまで」だけを渡すための共通フォーマット。

```json
{
  "plan_id": "uuid",
  "version": "1.0",
  "created_at": "ISO8601",
  "source": "manaos",
  "intent": "ユーザー指示の要約（1行）",
  "risk_level": "low | medium | high",
  "requires_approval": false,
  "approval_request_id": null,
  "scope": {
    "max_steps": 10,
    "allowed_actions": ["file_read", "file_move", "browser_navigate"],
    "forbidden_actions": ["os_command", "payment", "email_send", "file_delete"],
    "allowed_paths": ["/path/to/workspace"],
    "timeout_seconds": 300
  },
  "steps": [
    {
      "step_id": "1",
      "action": "file_move",
      "params": { "src": "...", "dst": "..." },
      "condition": null,
      "rollback_hint": "元フォルダに戻す"
    }
  ],
  "metadata": {
    "user_hint": "任意のメモ",
    "phase": "1 | 2 | 3"
  }
}
```

### フィールド要点

- **risk_level**
  まなOSがタスク内容から算出。`high` のときは原則 `requires_approval: true`。
- **requires_approval**
  `true` のときはまなOSが承認依頼を出し、`approval_request_id` が付与されたあとで Plan を渡す。
- **scope**
  Moltbot に許可する操作・パス・時間を明示。過剰な権限（Excessive Agency）を防ぐ。
- **steps**
  実行順の手順だけ。Moltbot はこの配列を「ここまで」の範囲で実行し、結果を返す。

### 2.1 Plan の constraints / idempotency（運用で刺さる追記）

現場運用で二重実行・暴走を防ぐため、以下を推奨。

| フィールド | 用途 |
|------------|------|
| **idempotency_key** | 同じ命令を二重実行しない用（超重要） |
| **timeouts** | ステップ単位 or 全体のタイムアウト |
| **max_actions** | 1プランで実行できるアクション上限（暴走ストッパー） |
| **allowed_domains** / **blocked_domains** | ブラウザ系タスクの安全柵 |
| **read_only_paths** / **write_paths** | ファイル操作範囲の境界 |
| **artifacts** | 出力ファイル・スクショの保存先（後で検証が楽） |

`moltbot_integration.schema.PlanConstraints` にまとめてあり、`Plan.constraints` で渡す。

---

## 3. 承認フロー（人間の最終承認を挟むポイント）

### 3.1 承認必須アクション（まなOS側で判定）

| カテゴリ | 例 | 承認前の扱い |
|----------|-----|----------------|
| 外部送信 | メール送信、DM、投稿 | Plan に含めず「承認依頼」のみ |
| 支払い・購入 | 決済、カート操作 | 同上 |
| 破壊操作 | ファイル削除、上書き一括 | 同上 |
| 認証・秘密 | パスワード入力、APIキー参照 | 同上 |

まなOSはこれらのアクションを Plan の `steps` に載せず、**承認依頼**（Slack / Obsidian / 専用API）を出す。承認後に「承認済み 1 ステップ」だけを Plan として Moltbot に渡すか、またはまなOSが別経路で実行する。

### 3.2 承認リクエストの形（既存パターンに合わせる）

既存の `oh_my_opencode` 承認と揃える。

```json
{
  "approval_request_id": "uuid",
  "plan_id": "uuid",
  "reason": "メール送信のため承認が必要です",
  "action_summary": "〇〇さんにレポートを送信",
  "risk_level": "medium",
  "created_at": "ISO8601",
  "expires_at": "ISO8601",
  "approved_plan_snippet": null,
  "proposed_patch": null,
  "user_notes": null,
  "resubmit_plan_id": null
}
```

- 承認後: `approved_plan_snippet` に「実行してよい 1 ステップ」を入れ、Moltbot 用の短い Plan にするか、まなOS側で実行。

#### 差し戻し前提（会話で修正できるUI）

「この部分だけ直して再提出して」に対応するため、以下を推奨。

| フィールド | 用途 |
|------------|------|
| **proposed_patch** | Plan の差分案（人間が修正案を渡す） |
| **user_notes** | 人間からの追加制約 |
| **resubmit_plan_id** | 差し替え先 Plan ID（再提出用） |

Slack 承認を「はい/いいえ」だけにしないと、運用が詰まない。

### 3.3 承認ポイントの実装方針

- まなOSが Plan を組み立てる段階で `requires_approval` と `allowed_actions` / `forbidden_actions` を設定。
- `risk_level` は「承認必須アクションを含むか」「範囲が広いか」などで算出。
- 承認は既存の Slack / Obsidian / キュー（例: `IntrinsicTodoQueue` の APPROVED）と連携し、**承認済みだけ**を Moltbot ゲートに流す。

---

## 4. ログ設計（監査・証跡・巻き戻し）

### 4.1 残すもの

- **Plan**（まなOSがゲートに投げた JSON）
- **Execute**（Moltbot が実際に実行したステップと結果の要約）
- **Result**（成功/失敗、所要時間、エラー有無）

これらを **Git でコミット** する（Moltbot の Git 記憶文化と相性が良い）。

### 4.2 ログレコード形式（3層構成・事故分析・テンプレ化に強い）

後で分析や商品化（テンプレ化）を考えると、次の形式に固定するのがおすすめ。

```
moltbot_audit/
  YYYY-MM-DD/
    {plan_id}/
      plan.json        # 入力（投げた Plan）
      decision.json    # 承認判定・理由・リスク根拠
      execute.json     # 実行サマリ（従来互換）
      execute.jsonl    # 時系列イベント（1行=1イベント）
      result.json      # 出力（success, error, finished_at）
      artifacts/       # スクショ・生成物の保存先
      commit_message.txt
```

- 事故分析が早い
- 成功パターンをテンプレ化しやすい
- 「運用ログ」がそのままプロダクト資産になる

### 4.3 コミットメッセージ例

```
moltbot: execute plan_id=xxx risk=low steps=3 success
```

- 事故時の巻き戻し・「誰がいつ何をさせたか」の証跡として利用。

---

## 5. まなOS → Moltbot ゲート（1本化）

- Moltbot の **gateway/daemon** にだけ接続する。
- まなOSは **Plan JSON を POST** し、**実行結果（Execute / Result）を JSON で受け取る**。
- ゲートの URL は設定で切り替え（このは / 専用機 / 母艦）。

### 5.1 ゲート API 最小仕様

| メソッド | パス | 概要 |
|----------|------|------|
| POST | /moltbot/plan | Plan JSON を送り、実行を開始 |
| GET | /moltbot/plan/{plan_id}/result | 実行結果の取得（ポーリング） |
| POST | /moltbot/plan/{plan_id}/cancel | 実行キャンセル |

#### Plan 署名（HMAC）

隔離運用では改ざん・中間者対策が肝。最小でも以下を推奨。

- まなOS側: `X-Plan-Signature: hmac_sha256(secret, plan_json_bytes)` を付与（`MOLTBOT_GATEWAY_SECRET` と同一 secret）
- Gateway 側: 署名検証が通った Plan だけ受理

`moltbot_integration.gateway` の `MoltbotGatewayClient` は、`MOLTBOT_GATEWAY_SECRET` が設定されていれば自動でヘッダを付与する。

#### イベントストリーム（オプション）

実行中の進捗をストリームで返す API（例: `GET /moltbot/plan/{plan_id}/events` で Server-Sent Events）を用意すると、長時間タスクの監視が楽。必須ではない。

※ 実際の Moltbot の API に合わせてパス・ペイロードは調整する。

---

## 6. 導入 Phase と scope の対応

| Phase | 内容 | allowed_actions 例 | 承認 |
|-------|------|--------------------|------|
| 1 | ファイル整理・定型操作のみ | file_read, file_move, file_copy | 不要（送信なし） |
| 2 | Slack 通知・レポート作成 | + slack_send, report_generate | 送信は承認あり |
| 3 | 予約・交渉・メール返信 | + email_send, browser_submit | ホワイトリスト＋監査必須 |

まなOSの `scope.allowed_actions` / `forbidden_actions` と `metadata.phase` で Phase を明示し、Moltbot 側でも同じポリシーをチェックする（二重チェック）。

---

## 7. セキュリティ（設計で押さえる点）

- **秘密情報**: API キー等はホーム直下に置かず、実行ユーザーを分け、可能ならコンテナ/VM で隔離。
- **入力フィルタ**: まなOSが Moltbot に渡す前に、外部コンテンツの「命令文っぽい部分」除去・隠し命令検出・送信先ドメイン制限を行う。
- **監査**: 上記ログを Git で必ず残し、定期的にレビュー可能にする。

---

## 8. 次のステップ

1. **このは or 専用機で Moltbot を立てる**（推奨: 母艦は聖域にしない）
2. **まなOS側に「Moltbot ゲート用クライアント」を実装**（Plan 送信・Result 取得・ログ書き込み）→ 済
3. **承認フローを既存の Slack / Obsidian / IntrinsicTodoQueue と接続**
4. **Phase 1 の scope だけで試運転**（ファイル整理のみ許可し、送信系は一切許可しない）

以上が、まなOSに Moltbot を「分離して取り込む」ための現実的な設計のまとめ。

---

## 8.1 このは側 Gateway 最小実装（貼って動く）

リポジトリ内の **`moltbot_gateway/gateway_app.py`** で、このは側の Gateway を立てられる。

- **署名検証**: `X-Plan-Signature` が来たら検証（SECRET 設定時）。未設定ならスキップ（ローカル試行用）。
- **Plan 保存**: `MOLTBOT_GATEWAY_DATA_DIR/plans/{plan_id}.json`
- **実行**: いったん **モック**で、dry_run なら「分類結果だけ」、dry_run=False なら「実行した体」で返す。
- **Cancel**: 状態を `cancelled` に。
- **Result**: GET で保存した result.json をそのまま返す。

### このは側での起動（最小）

```bash
cd moltbot_gateway
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install fastapi uvicorn
export MOLTBOT_GATEWAY_SECRET="あなたのsecret"
export MOLTBOT_GATEWAY_DATA_DIR="/var/lib/moltbot_gateway"   # ローカルなら ./moltbot_gateway_data
uvicorn gateway_app:app --host 0.0.0.0 --port 8088
```

リポジトリルートから: `uvicorn moltbot_gateway.gateway_app:app --host 0.0.0.0 --port 8088`

### まなOS側 .env（runner が最後まで通る）

```env
MOLTBOT_GATEWAY_URL=http://<このはのIP or ドメイン>:8088
MOLTBOT_GATEWAY_SECRET=あなたのsecret
```

runner 成功時は `moltbot_audit/YYYY-MM-DD/{plan_id}/` に **3層ログ＋commit_message.txt** が出力される。

---

## 8.2 device_orchestrator_config.json 雛形

まなOSの司令塔で「外付け手足」として扱う場合の追記例。

```json
{
  "device_id": "moltbot-konoha",
  "device_name": "Moltbot Gateway (Konoha)",
  "device_type": "moltbot_gateway",
  "device_location": "このはサーバー（Gateway 最小実装）",
  "api_endpoint": "http://<konoha-host>:8088",
  "capabilities": ["file_organize_phase1"]
}
```

capabilities を Phase2/3 で増やせば、**権限解放が台帳管理**できる。既存の `device_orchestrator_config.json` に上記エントリを追加済み（api_endpoint は環境に合わせて書き換え）。

---

## 8.3 本番事故らない運用（Phase1 やらかし防止）

Phase1 で事故るのはだいたいここ。

- `dry_run` を外したまま運用開始
- `write_paths` 制限がない
- 分類ルールが雑で誤移動

### Phase1 推奨 Constraints（テンプレ）

- **dry_run=True をデフォルト**（runner の Phase1 は最初 dry_run）
- **write_paths** は `~/Downloads` と移動先だけ（`PlanConstraints.phase1_safe()` で固定）
- **max_actions** は 50 程度（`PlanConstraints.phase1_safe()` で 50）

`moltbot_integration.schema.PlanConstraints.phase1_safe()` で上記をまとめており、`manaos_moltbot_runner.py` の Phase1 プランに組み込み済み。

---

## 8.4 統一APIから Moltbot を呼ぶ（まなOS本体連携）

まなOS統一API（例: 9502）経由で Plan を送信できる。n8n・Open WebUI・他サービスから HTTP で呼べる。

| メソッド | パス | 概要 |
|----------|------|------|
| POST | /api/moltbot/plan | Plan 送信。body: 完全な plan JSON、または `intent`=list_only/read_only & `path` & `user_hint` |
| GET | /api/moltbot/plan/{plan_id}/result | 実行結果取得 |
| POST | /api/moltbot/plan/{plan_id}/cancel | キャンセル |
| GET | /api/moltbot/health | Gateway 死活プロキシ |
| POST | /api/secretary/file-organize | 秘書経由でファイル整理 Plan 送信（学習・記憶と連携） |

- 統一API の .env に `MOLTBOT_GATEWAY_URL`（例: http://127.0.0.1:8088）と `MOLTBOT_GATEWAY_SECRET` を設定する。
- 疎通確認: リポジトリルートで `.\moltbot_gateway\deploy\check_unified_api_moltbot.ps1`（統一API 9502 と Moltbot Gateway 8088 が起動していること）。
- 自律・秘書からプログラムで送る場合は `PersonalityAutonomySecretaryIntegration.submit_file_organize_plan(user_hint, path, intent)` を使うと学習記録も残る。

---

## 9. 最小インターフェースの使い方（貼れる形）

リポジトリ内の `moltbot_integration/` に以下を用意した。

- **Plan JSON スキーマ** … `Plan`, `PlanStep`, `PlanScope`, `PlanConstraints`, `PlanMetadata`, `ApprovalRequest`, `AuditRecord`
- **承認必須判定** … `action_requires_approval`, `plan_requires_approval`
- **ゲートクライアント** … `MoltbotGatewayClient`（`submit_plan`, `get_result`, `cancel_plan`, `write_audit`）、`sign_plan_body`, `PLAN_SIGNATURE_HEADER`
- **Phase1 安全 scope** … `PlanScope.file_organize()`（ファイル整理オンリー・送信・削除なし）
- **貼って使えるランナー** … ルートの `manaos_moltbot_runner.py`（dry_run → 実行 → 監査ログが残る流れの最小例）

### 使用例

```python
from moltbot_integration import (
    Plan, PlanStep, PlanScope, PlanMetadata, RiskLevel,
    plan_requires_approval, MoltbotGatewayClient, AuditRecord,
)

# Phase 1 用 scope（ファイル整理のみ）
scope = PlanScope(
    max_steps=5,
    allowed_actions=["file_read", "file_move", "file_copy"],
    forbidden_actions=["file_delete", "os_command", "email_send"],
    allowed_paths=["/path/to/workspace"],
    timeout_seconds=300,
)
steps = [
    PlanStep(step_id="1", action="file_move", params={"src": "...", "dst": "..."}),
]
plan = Plan(
    intent="Downloads を整理",
    risk_level=RiskLevel.LOW,
    requires_approval=plan_requires_approval(RiskLevel.LOW, steps),
    scope=scope,
    steps=steps,
    metadata=PlanMetadata(phase="1"),
)

# 承認不要ならゲートに送信
if not plan.requires_approval:
    client = MoltbotGatewayClient()  # MOLTBOT_GATEWAY_URL を .env に設定
    out = client.submit_plan(plan)
    if out.get("ok"):
        # 結果取得・監査ログ書き出し（AuditRecord を組み立てて write_audit）
        pass
else:
    # 承認依頼を Slack / Obsidian 等に出す（既存 oh_my_opencode パターンに合わせる）
    pass
```

- 監査ログは `client.write_audit(record)` で `moltbot_audit/YYYY-MM-DD/{plan_id}/` に出力。Git でコミットするかは運用方針に合わせる。
