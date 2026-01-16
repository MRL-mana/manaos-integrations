# MRL Memory System - Phase 1開始準備完了

## ✅ 準備完了項目

### 1. デプロイ前の最終チェック ✅
- `phase1_preflight_check.py`: 環境変数のチェック

### 2. 疎通確認スクリプト ✅
- `phase1_connectivity_test.py`: 4つのテスト

### 3. メトリクススナップショット取得 ✅
- `phase1_metrics_snapshot.py`: JSON形式でスナップショットを取得
- `phase1_warmup.py`: Warm-up用スクリプト（オプション）

### 4. Go/No-Go判定スクリプト ✅
- `phase1_decision_maker.py`: JSONスナップショットから自動判定

### 5. 健康診断スクリプト ✅
- `phase1_health_check.py`: 永続化ストアの行数チェックとTTLマネージャの動作確認

### 6. 判定表・ガイド ✅
- `PHASE1_GO_NOGO_DECISION_TABLE.md`: 詳細な判定基準
- `PHASE1_SNAPSHOT_TEMPLATE.md`: スナップショット共有テンプレート
- `PHASE1_ROUTINE.md`: 運用ルーチン
- `PHASE1_START_NOW.md`: 起動手順
- `PHASE1_FINAL_CHECKLIST.md`: 最終チェックリスト

### 7. Phase 2進行条件 ✅
- `PHASE2_GO_CONDITIONS.md`: Phase 2 Go条件（確定版）

---

## 🎯 次のアクション（最短）

Phase 1を起動したら、以下を共有してください：

### 方法1（最強）

- `phase1_metrics_snapshot_baseline.json` の中身ぜんぶ
- （余裕があれば）`phase1_metrics_snapshot_warmup.json` の中身ぜんぶ

### 方法2（最短）

- `phase1_decision_maker.py` の判定1行
- `phase1_health_check.py` の要点
- SECURITYログ1行

---

## ⚠️ 絶対確認項目

### Read-onlyなのに書き込みしてないか

- [ ] `writes_per_min == 0` ✅
- [ ] health_checkで永続化行数増加なし ✅

**ここがズレてたら、他が全部良くても設定ミスで即修正**

---

## 📋 Phase 1起動手順（最短）

### 1. Preflight

```bash
python phase1_preflight_check.py
```

### 2. 起動

```bash
python mrl_memory_integration.py
```

### 3. 疎通確認

```bash
python phase1_connectivity_test.py
```

### 4. Baselineスナップショット取得

```bash
python phase1_metrics_snapshot.py phase1_metrics_snapshot_baseline.json
```

### 5. Warm-up（推奨・オプション）

```bash
python phase1_warmup.py 20
python phase1_metrics_snapshot.py phase1_metrics_snapshot_warmup.json
```

### 6. 健康診断

```bash
python phase1_health_check.py
```

### 7. 自動判定

```bash
python phase1_decision_maker.py phase1_metrics_snapshot_baseline.json
```

---

## 🎯 判定結果

共有された情報に基づいて、以下を即座に判定します：

- **Go / 設定ミス / 止めるべき** の確定
- もし止めるなら「どこ直すか」1〜3点に絞って提示
- Phase 2へ進むための条件を最終確定

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: Phase 1開始準備完了
