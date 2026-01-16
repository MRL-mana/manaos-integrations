# Phase 2 (Write 10%) 進行条件

## 🎯 Phase 2 Go条件（確定版）

Phase 1を **24〜48時間** 回して、以下が満たされればPhase 2へ。

### 必須条件（すべて満たす必要がある）

- [ ] **SECURITYログが毎回正しい**（起動のたびにOK）
  - `auth=enabled`
  - `rate_limit=enabled`
  - `max_input` が想定どおり
  - `pii_mask=enabled`

- [ ] **重大エラー（5xx）が継続発生してない**
  - ログに500エラーが連続して出ていない
  - サービスが正常に動作している

- [ ] **Read-onlyなのに書き込みが発生してない**
  - 書き込み回数/分 = 0
  - `FWPKM_WRITE_MODE=readonly`が正しく機能している

- [ ] **p95が安定**（急増なし）
  - 0.1秒以下で安定
  - 前日比2倍以上の急増がない

- [ ] **矛盾検出率が安定**（急増なし）
  - < 5%で安定
  - 前日比2倍以上の急増がない

- [ ] **ゲート遮断率が95%貼り付きじゃない**
  - 0〜80%の範囲で推移
  - 95%以上が継続していない

---

## ❌ Phase 2 No-Go条件

以下のいずれかが該当する場合、Phase 2へ進まない：

- SECURITYログが正しくない（1つでもdisabled）
- 重大エラー（5xx）が継続発生している
- Read-onlyなのに書き込みが発生している（書き込み回数/分 > 0）
- p95が急増している（前日比2倍以上）
- 矛盾検出率が急増している（前日比2倍以上）
- ゲート遮断率が95%貼り付き

---

## 📊 判定方法

### 24時間後の確認

```bash
# ダッシュボードを表示
python mrl_memory_dashboard.py

# ログを確認
tail -f /var/log/mrl-memory/error.log | grep "500"
```

### 48時間後の最終判定

```bash
# ダッシュボードを表示
python mrl_memory_dashboard.py

# Phase 2 Go条件をチェック
# （手動でチェックリストを確認）
```

---

## 🔄 Phase 2への切り替え手順

Phase 2 Go条件を満たしたら：

```bash
# Phase 2に切り替え
./rollout_commands.sh phase2

# サービス再起動（systemdの場合）
sudo systemctl restart mrl-memory

# または（PM2の場合）
pm2 restart mrl-memory --update-env

# 起動確認
python mrl_memory_dashboard.py
```

---

## 📝 チェックリスト（24時間後）

- [ ] SECURITYログが正しい
- [ ] 重大エラー（5xx）がない
- [ ] 書き込み回数/分 = 0
- [ ] p95 < 0.1秒で安定
- [ ] 矛盾検出率 < 5%で安定
- [ ] ゲート遮断率 0〜80%で推移

**すべてチェック → Phase 2へ**

---

## 📝 チェックリスト（48時間後）

- [ ] 24時間後のチェックリストがすべて満たされている
- [ ] 48時間経過しても問題がない
- [ ] 指標が安定している

**すべてチェック → Phase 2へ**

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: Phase 2進行条件確定
