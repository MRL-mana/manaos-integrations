# 本格運用チェックリスト（母艦だけでやる前提）

常駐化・監査ローテ・SECRET ローテ・本物接続の切り替え・ロールバック・n8n 連携まで、本格運用でやることを固定する。

**今すぐ本番運用を始める** → **`PRODUCTION_START.md`** に従って上から順に実行する。

---

## ✅ 1. Gateway を常駐させる（母艦）

- [ ] **タスクスケジューラ**で「ログオン時」に Gateway を起動する（`deploy/register_gateway_autostart.ps1` を実行して登録）
- [ ] または **手動で常駐**: 必要時に `uvicorn moltbot_gateway.gateway_app:app --host 127.0.0.1 --port 8088` をバックグラウンドで起動
- [ ] 起動確認: `Invoke-WebRequest -Uri http://127.0.0.1:8088/moltbot/health -UseBasicParsing` が 200

---

## ✅ 2. 監査ローテ（moltbot_audit の整理）

- [ ] **30 日以上前**の監査をアーカイブ or 削除する（月 1 回などで実行）
- [ ] 実行: `python moltbot_gateway/deploy/rotate_audit.py`（または リポジトリルートで `.\moltbot_gateway\deploy\rotate_audit.ps1`）
- [ ] 設定: 保持日数は環境変数 `MOLTBOT_AUDIT_KEEP_DAYS`（デフォルト 30）。削除する場合は `MOLTBOT_AUDIT_DELETE=1`

---

## ✅ 3. SECRET ローテ（年 1 回推奨）

- [ ] `MOLTBOT_GATEWAY_SECRET` を変更（.env と Gateway 起動時の環境変数を同じ値に）
- [ ] Gateway を再起動
- [ ] まなOS runner の .env を同じ SECRET に更新
- [ ] （将来）401 Invalid signature を検知したら Slack 通知する運用を検討

---

## ✅ 4. 本物 Moltbot 接続への切り替え

- [ ] `EXECUTOR=moltbot` に設定
- [ ] `MOLTBOT_DAEMON_URL` または `MOLTBOT_CLI_PATH` を設定（本物 daemon/CLI の URL またはパス）
- [ ] 最初は **list_files / file_read のみ**許可。`list_only` runner で成功確認
- [ ] 問題なければ `ALLOWED_ACTIONS_MOLTBOT` に move_files 等を追加して解放

---

## ✅ 5. ロールバック（障害時）

- [ ] **EXECUTOR=mock に戻す**: Gateway の環境変数を `EXECUTOR=mock` にし、再起動。まなOS 側は変更不要
- [ ] **Gateway が落ちた場合**: runner は submit で失敗する。監査は「plan 送信前」までしか残らない。再起動後は再実行でよい
- [ ] **本物 daemon が応答しない場合**: executor 側でタイムアウト・リトライを入れるか、EXECUTOR=mock に切り戻す

---

## ✅ 6. n8n から Plan を投げる（オプション）

- [ ] n8n の HTTP Request ノードで `POST {{MOLTBOT_GATEWAY_URL}}/moltbot/plan` に body = Plan JSON を送る
- [ ] ヘッダ: `Content-Type: application/json`, `X-Plan-Signature`: HMAC-SHA256(secret, body), `X-Plan-Id`: plan_id
- [ ] 結果取得: `GET {{MOLTBOT_GATEWAY_URL}}/moltbot/plan/{{plan_id}}/result` をポーリング
- [ ] サンプル: `deploy/n8n_plan_request_example.json` を参照（必要なら作成）

---

## 運用で「絶対やる」2 つ（再掲）

- [ ] **監査ログ**を「監査と同じ日付」で追えるようにする（moltbot_audit の日付フォルダ）
- [ ] **SECRET ローテ**を年 1 回やる（漏れていなくても）

---

## 関連ドキュメント

- 母艦だけ: `MOTHERSHIP_ONLY.md`
- A（外部公開）: `CHECKLIST_A_EXTERNAL.md`
- B（本物接続）: `CHECKLIST_B_MOLTBOT.md`
