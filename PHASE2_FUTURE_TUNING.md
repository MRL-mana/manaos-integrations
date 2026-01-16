# Phase 2 開始後のチューニング（将来の拡張）

## 📊 write率メトリクス（将来の拡張案）

### 提案内容

`writes_per_min / request_per_min` の比率（= write率）もメトリクスに出す。

### メリット

- `sample_rate=0.1` なら write率もだいたい0.1付近になるはず
- 暴走は「write率が0.1を大きく超える」で分かる
- traffic増えたときでも誤停止しない運用ができる

### 実装タイミング

**Phase 2開始後にチューニングでOK**。今すぐ必須じゃない。

### 実装イメージ

```python
# メトリクスに追加
write_rate = writes_per_min / request_per_min if request_per_min > 0 else 0

# 停止条件に追加（将来）
if write_rate > 0.15:  # sample_rate=0.1の1.5倍以上
    # 暴走判定
```

---

## 📋 writes_per_min_absolute の最適化

### 現在の値

- `writes_per_min_absolute = 50`（暫定値）

### 最適化方法

Phase 1の24hが終わった時点で `phase1_24h_summary.py` の出力を見て、以下を判断：

- **余裕ありすぎ（もっと絞れる）**: 値を下げる（例: 30）
- **ギリギリ（ちょうどいい）**: 現状維持（50）
- **低すぎ（誤停止しそう）**: 値を上げる（例: 70）

### 判断基準（チューニングロジック）

Phase 2想定の traffic を仮定（request/min）:
- `sample_rate=0.1` なら期待write/min ≒ request/min × 0.1
- 実際の write/min 上振れが「どれくらい出るか」で閾値調整

**将来の拡張**: summary に `request/min`（またはAPI hit数）があると最強だけど、今は無くても調整できる。

---

## 📝 Phase 2開始後の監視項目

1. **write率**: `writes_per_min / request_per_min`
2. **writes_per_min_absolute**: 実際のtrafficに合わせて調整
3. **quarantine比率**: `quarantine_entries / scratchpad_entries`
4. **矛盾検出率の推移**: 急増していないか

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: Phase 2開始後のチューニングガイド（将来の拡張）
