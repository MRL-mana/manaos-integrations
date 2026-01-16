# MRL Memory System - ロールアウトログ

## Phase 1: Read-onlyモード

### 開始日時
- **開始**: YYYY-MM-DD HH:MM:SS
- **終了**: YYYY-MM-DD HH:MM:SS（予定）
- **期間**: 1〜2日

### 切り替え手順
```bash
# 実行したコマンド
export FWPKM_ENABLED=1
export FWPKM_WRITE_MODE=readonly
export FWPKM_WRITE_ENABLED=0
export FWPKM_REVIEW_EFFECT=0
```

### 起動確認

#### SECURITYログ
```
SECURITY: auth=enabled, rate_limit=enabled, max_input=200000, pii_mask=enabled
```

**確認**: ✅ / ❌

#### 疎通確認結果
- 認証なし → 401: ✅ / ❌
- 認証あり → 200: ✅ / ❌
- MAX_INPUT超過 → 413/400: ✅ / ❌
- レート超過 → 429: ✅ / ❌

### 指標の推移

#### 初期値（開始時）
```
E2E p95: X.XXX秒
ゲート遮断率: XX%
矛盾検出率: XX%
スロット使用率: XX%
書き込み回数/分: X（Read-onlyなので基本0）
```

#### 24時間後
```
E2E p95: X.XXX秒
ゲート遮断率: XX%
矛盾検出率: XX%
スロット使用率: XX%
書き込み回数/分: X
```

#### 48時間後（終了時）
```
E2E p95: X.XXX秒
ゲート遮断率: XX%
矛盾検出率: XX%
スロット使用率: XX%
書き込み回数/分: X
```

### 異常・インシデント

#### 発生した問題
- **日時**: YYYY-MM-DD HH:MM:SS
- **内容**: 
- **対応**: 
- **結果**: 

### 判定

#### 合格ライン（✅）
- [ ] E2E p95が普段の2倍以内で安定
- [ ] ゲート遮断率が0〜80%の範囲で変動
- [ ] 矛盾検出率が低い or 安定（急増しない）
- [ ] スロット使用率に極端な偏りなし
- [ ] Write Amp / 書き込み回数が基本ゼロ

#### 即停止ライン（🛑）
- [ ] p95が急に跳ねる（前日比2倍以上が続く）
- [ ] ゲート遮断率が常時95%超え
- [ ] 矛盾検出率が急増

### Phase 2へのGo条件
- [ ] SECURITYログが継続して正しい
- [ ] 指標が安定している
- [ ] 重大な例外（500）が出ていない
- [ ] 参照経由で回答が破綻していない

### 判定結果
- **Go**: ✅ / ❌
- **理由**: 

---

## Phase 2: Write 10%

### 開始日時
- **開始**: YYYY-MM-DD HH:MM:SS
- **終了**: YYYY-MM-DD HH:MM:SS（予定）
- **期間**: 1〜3日

### 切り替え手順
```bash
# 実行したコマンド
export FWPKM_ENABLED=1
export FWPKM_WRITE_MODE=sampled
export FWPKM_WRITE_SAMPLE_RATE=0.1
export FWPKM_WRITE_ENABLED=1
export FWPKM_REVIEW_EFFECT=0
```

### 指標の推移
（Phase 1と同様の形式で記録）

### 異常・インシデント
（発生した問題を記録）

### 判定結果
- **Go**: ✅ / ❌
- **理由**: 

---

## Phase 3: Write 100%

### 開始日時
- **開始**: YYYY-MM-DD HH:MM:SS
- **終了**: YYYY-MM-DD HH:MM:SS（予定）
- **期間**: 数日

### 切り替え手順
```bash
# 実行したコマンド
export FWPKM_ENABLED=1
export FWPKM_WRITE_MODE=full
export FWPKM_WRITE_ENABLED=1
export FWPKM_REVIEW_EFFECT=0
```

### 指標の推移
（Phase 1と同様の形式で記録）

### 異常・インシデント
（発生した問題を記録）

### 判定結果
- **Go**: ✅ / ❌
- **理由**: 

---

## Phase 4: Review effect ON

### 開始日時
- **開始**: YYYY-MM-DD HH:MM:SS
- **終了**: YYYY-MM-DD HH:MM:SS（予定）

### 切り替え手順
```bash
# 実行したコマンド
export FWPKM_ENABLED=1
export FWPKM_WRITE_MODE=full
export FWPKM_WRITE_ENABLED=1
export FWPKM_REVIEW_EFFECT=1
```

### 指標の推移
（Phase 1と同様の形式で記録）

### 異常・インシデント
（発生した問題を記録）

### 判定結果
- **Go**: ✅ / ❌
- **理由**: 

---

## 総合評価

### ロールアウト完了日
- **完了**: YYYY-MM-DD HH:MM:SS

### 最終ステータス
- **全Phase完了**: ✅ / ❌
- **本番運用開始**: ✅ / ❌

### 学んだこと・改善点
- 
- 
- 

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: ロールアウト進行中
