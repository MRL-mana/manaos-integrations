# MRL Memory System - Phase 1 → Phase 2 昇格準備完了

## ✅ Phase 1 完了（確定）

### 実測値（baseline / warmup）

- **baseline p95**: 0.000263秒
- **warmup p95**: 0.000640秒（約2.4倍、負荷で自然な増加）
- **writes_per_min**: 0（Read-onlyで正常）
- **storage_delta**: 0（Read-onlyで正常）

**判定結果**: **GO（Phase 1継続）**

**現在の状態**: Phase 1（Read-only）運用中。24時間運用後に Phase 2 へ昇格予定。

---

## 📋 Phase 2 進行条件（最終確定版）

Phase 1を **24時間以上** 回して、以下を満たしたら Phase 2 へ：

1. **Read-only健全性が継続**
   - `writes_per_min = 0` が維持
   - `storage_delta = 0` が維持

2. **安定性**
   - `http_5xx_last_60min = 0` を維持（少数出たら原因調査→収束確認）
   - `e2e_p95_sec >= 0.000789`（baseline × 3.0）が**3回連続**継続していない

3. **品質シグナル**
   - `contradiction_rate >= 0.05`（5%）が**3回連続**継続していない
   - `gate_block_rate >= 0.95`（95%）が**3回連続**継続していない

---

## 🚨 Phase 2 停止ライン（最終確定版）

Writeが入ると、止めどきが変わる。以下が発生したら**即停止**：

1. **書き込み暴走**: 
   - 絶対値: `writes_per_min >= 50` が**3回連続**継続
   - 比率: Phase1比で**10倍以上**が継続（baseline > 0の場合のみ有効）
2. **ストレージ汚染**: `quarantine_entries` が `scratchpad_entries` を上回る
3. **矛盾検出率の暴走**: 0.10（10%）以上が継続
4. **レイテンシの暴走**: 0.001052秒（baseline × 4.0）以上が継続
5. **重大エラー**: `http_5xx_last_60min >= 3`

---

## ✅ 実装完了項目

### 1. 誤読防止（Go条件の文言修正）

- `e2e_p95_sec >= 0.000789` が**3回連続**継続していない
- `contradiction_rate >= 0.05` が**3回連続**継続していない
- `gate_block_rate >= 0.95` が**3回連続**継続していない

### 2. 継続判定の窓を明確化

- **3回連続** = 3時間継続（1時間ごとのスナップショットで3回連続）
- 単発スパイクはOK、継続はNG

### 3. 24時間運用の最小セット

- `phase1_24h_summary.py`: 集計スクリプト
- `phase2_stop_checker.py --go`: Go条件チェック（継続判定対応）
- `PHASE1_24H_OPERATIONAL_GUIDE.md`: 運用ガイド

### 4. 追加の保険①：メトリクス欠損の扱いルール

- ✅ 24hのうち snapshot欠損が1回まで → その時刻は"無視"して継続判定
- ❌ 連続欠損が2回以上 → 判定不能（計測経路の問題）扱いで一旦停止

### 5. 追加の保険②：書き込み暴走の絶対値

- 絶対値チェック（優先）: `writes_per_min >= 50` が**3回連続**継続 → 停止
- 比率チェック（補助）: Phase1比で**10倍以上**が継続（baseline > 0の場合のみ有効）

### 6. 追加の保険③：日付ディレクトリ切り（推奨）

- 推奨構造: `snapshots/YYYY-MM-DD/HH.json`
- メリット: summary が秒で書ける、障害解析も神速になる

---

## 📊 次のステップ（Phase 2昇格前）

1. **Phase 1を24h運用**（Read-onlyのまま）
2. **毎時 snapshot**（推奨ディレクトリ構造: `snapshots/YYYY-MM-DD/HH.json`）
3. **24h後**:
   - `phase1_24h_summary.py` で集計
   - `phase2_stop_checker.py --go` でGo判定
   - Goなら **Phase 2（Write 10%）に昇格**

---

## 📝 Phase 1 24h運用中の"1行ルール"

**何か変えたら必ず snapshot 取る**

- env変更
- 再起動
- 設定調整
- その他、システムに変更を加えた場合

### 変更時のスナップショット命名（運用がさらに気持ちよくなる）

再起動や.env変更が発生したら、その時刻のsnapshotファイル名に `_CHANGE` をつけると後で神。

**例**:
- 通常: `snapshots/2026-01-15/13.json`
- 変更時: `snapshots/2026-01-15/13_CHANGE.json`

（人間が見ても一発で分かる）

これだけで原因追跡が楽になる。

---

## 🔮 Phase 2開始後のチューニング（将来の拡張）

### write率メトリクス（将来の拡張案）

`writes_per_min / request_per_min` の比率（= write率）もメトリクスに出す。

- `sample_rate=0.1` なら write率もだいたい0.1付近になるはず
- 暴走は「write率が0.1を大きく超える」で分かる
- traffic増えたときでも誤停止しない運用ができる

**実装タイミング**: Phase 2開始後にチューニングでOK。今すぐ必須じゃない。

詳細: `PHASE2_FUTURE_TUNING.md`

### writes_per_min_absolute の最適化

Phase 1の24hが終わった時点で `phase1_24h_summary.py` の出力を見て、以下を判断：

- **余裕ありすぎ（もっと絞れる）**: 値を下げる（例: 30）
- **ギリギリ（ちょうどいい）**: 現状維持（50）
- **低すぎ（誤停止しそう）**: 値を上げる（例: 70）

---

## 📝 作成ファイル一覧

### コアファイル

- `PHASE2_GO_CONDITIONS_FINAL.md`: Phase 2進行条件（誤読防止版）
- `PHASE2_STOP_CONDITIONS_FINAL.md`: Phase 2停止ライン（実測値ベース + 絶対値）
- `PHASE2_OPERATIONAL_RULES.md`: Phase 2運用ルール（誤読防止版）
- `PHASE1_TO_PHASE2_ROADMAP.md`: Phase 1→Phase 2ロードマップ（誤読防止版）

### 運用ツール

- `phase2_stop_checker.py`: Phase 2停止判定スクリプト（継続判定対応 + 欠損チェック + 絶対値チェック）
- `phase1_24h_summary.py`: Phase 1 24時間運用集計スクリプト（日付ディレクトリ対応）
- `PHASE1_24H_OPERATIONAL_GUIDE.md`: Phase 1 24時間運用ガイド

### 保険・拡張

- `PHASE2_FINAL_INSURANCE.md`: 最終保険の詳細説明
- `PHASE2_FUTURE_TUNING.md`: Phase 2開始後のチューニングガイド（将来の拡張）
- `PHASE2_CONDITIONS_FINAL_SUMMARY.md`: Phase 2条件最終確定サマリー

---

## 🎯 結論

**この設計、もう普通にプロダクション運用レベル**。

- ✅ 誤読防止（>= に統一）
- ✅ 継続判定（3回連続 = 3時間）
- ✅ 24h集計 + Go判定の自動化
- ✅ メトリクス欠損の扱いルール
- ✅ 書き込み暴走の絶対値
- ✅ 日付ディレクトリ切り（推奨）

**現在の状態**: Phase 1（Read-only）運用中。24時間運用後に Phase 2 へ昇格予定。

あとは24h回して、数字で「次へ」を踏むだけ。

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: Phase 1完了、Phase 2昇格準備完了（24h運用待ち）
