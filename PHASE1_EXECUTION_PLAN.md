# Phase 1 (Read-only) 実行プラン

## 🎯 目的

Phase 1は「効果」ではなく「安全」を確認するフェーズです。
- メモリ参照を混ぜても回答を壊さないことを確認
- セキュリティ設定が正しく機能することを確認
- 指標が安定することを確認

**期間**: 24〜48時間

---

## 📋 実行手順

### Step 0: デプロイ前の最終チェック（5分）

```bash
# チェックスクリプトを実行
python phase1_preflight_check.py
```

**すべてのチェックがパスすることを確認**

### Step 1: 起動してSECURITYログを確認

```bash
# 起動
python mrl_memory_integration.py
```

**確認すべきログ（超重要）**:
```
SECURITY: auth=enabled, rate_limit=enabled, max_input=200000, pii_mask=enabled
✅ Rollout Manager初期化: enabled=True, write_mode=readonly, ...
```

**これが出ない = 本番は未適用** → 設定を確認してください。

### Step 2: 疎通確認（4つのテスト）

```bash
# 疎通確認スクリプトを実行
python phase1_connectivity_test.py
```

**確認項目**:
- [ ] 認証なしで叩く → 401
- [ ] 認証ありで叩く → 200
- [ ] MAX_INPUT超過で叩く → 413/400
- [ ] レート超過で叩く → 429

**すべてパスしたら Phase 1の土台OK** ✅

### Step 3: ダッシュボードで初期値を確認

```bash
# ダッシュボードを表示
python mrl_memory_dashboard.py
```

**記録すべき値（`MRL_MEMORY_ROLLOUT_LOG.md`に記録）**:
- E2E p95: X.XXX秒
- ゲート遮断率: XX%
- 矛盾検出率: XX%
- スロット使用率: XX%
- 書き込み回数/分: X（Read-onlyなので基本0）

---

## 📊 Phase 1で見るべき6指標の合格ライン

### ✅ 合格（目安）

- **E2E p95**: 普段の2倍以内で安定
- **ゲート遮断率**: 0〜80%の範囲で変動（常時100%は死んでる）
- **矛盾検出率**: 低い or 安定（急増しない）
- **スロット使用率**: 極端な偏りなし（特定スロットに集中しない）
- **Write Amp / 書き込み回数**: Read-onlyなら基本ゼロ（ゼロじゃないなら設定ミス）

### 🛑 即停止ライン

- ❌ p95が急に跳ねる（前日比2倍以上が続く）
- ❌ ゲート遮断率が常時95%超え（意味がない）
- ❌ 矛盾検出率が急増（入力のノイズ源 or 解析バグの可能性）

---

## 📝 ログ記録（24時間ごと）

### 毎日の確認

```bash
# ダッシュボードを表示して記録
python mrl_memory_dashboard.py
```

**`MRL_MEMORY_ROLLOUT_LOG.md`に以下を記録**:
- 日時
- 各指標の値
- 異常があれば内容と対応

---

## 🚀 Phase 2へのGo条件

Phase 1を24〜48時間回して、以下を満たしたら **Write 10%** に進めます：

- [ ] SECURITYログが継続して正しい
- [ ] 指標が安定している
- [ ] 重大な例外（500）が出ていない
- [ ] 参照経由で回答が破綻していない（ユーザー/運用側の体感でもOK）

---

## 🔄 切り替え手順（Phase 2へ）

```bash
# Phase 2に切り替え
./rollout_commands.sh phase2

# サービス再起動（systemdの場合）
sudo systemctl restart mrl-memory

# または（PM2の場合）
pm2 restart mrl-memory --update-env
```

---

## 📋 チェックリスト

### 起動前

- [ ] `.env`ファイルが設定されている
- [ ] `REQUIRE_AUTH=1`が設定されている
- [ ] `API_KEY`が強力なキーに設定されている
- [ ] `RATE_LIMIT_PER_MIN`が適切に設定されている
- [ ] `MAX_INPUT_CHARS`が適切に設定されている
- [ ] `FWPKM_WRITE_MODE=readonly`
- [ ] `FWPKM_REVIEW_EFFECT=0`
- [ ] `FWPKM_ENABLED=1`
- [ ] `FWPKM_WRITE_ENABLED=0`

### 起動時

- [ ] 起動ログに`SECURITY: auth=enabled, ...`が表示される
- [ ] ヘルスチェックが正常（`curl http://localhost:5105/health`）

### 疎通確認

- [ ] 認証なし → 401
- [ ] 認証あり → 200
- [ ] MAX_INPUT超過 → 413/400
- [ ] レート超過 → 429

### ロールアウト中（毎日）

- [ ] ダッシュボードで指標を確認
- [ ] ログに異常がないか確認
- [ ] 停止ラインに達していないか確認
- [ ] `MRL_MEMORY_ROLLOUT_LOG.md`に記録

---

## 🆘 トラブルシューティング

### SECURITYログが出ない

→ `.env`ファイルが正しく読み込まれていない可能性
→ 環境変数を直接確認: `echo $REQUIRE_AUTH`（Linux/Mac）または `echo %REQUIRE_AUTH%`（Windows）

### 疎通確認が失敗する

→ APIサーバーが起動しているか確認: `curl http://localhost:5105/health`
→ 認証キーが正しいか確認: `.env`ファイルの`API_KEY`

### 指標が異常

→ 停止ラインに達したら即座に停止: `export FWPKM_WRITE_ENABLED=0`
→ ログを確認: `tail -f /var/log/mrl-memory/error.log`

---

## 📊 次の返信で共有してほしい情報

Phase 1を起動したら、以下を共有してください：

1. **起動時のSECURITYログ1行**
   ```
   SECURITY: auth=enabled, rate_limit=enabled, max_input=200000, pii_mask=enabled
   ```

2. **ダッシュボードの初期値**
   ```
   E2E p95: X.XXX秒
   ゲート遮断率: XX%
   矛盾検出率: XX%
   スロット使用率: XX%
   書き込み回数/分: X
   ```

これがあれば「Goか、設定ミスか、止めるべきか」を一発で判定できます。

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: Phase 1開始準備完了
