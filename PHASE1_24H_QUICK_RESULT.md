# Phase 1 24h運用 合否判定（1行出力・任意）

## 📊 24hの"合否"を1行で出す（任意の強化パッチ）

`phase1_24h_summary.py` と `phase2_stop_checker.py --go` があるから、
**最後に「合否だけを1行で出す」**と、運用がさらに気持ちよくなる。

---

## 出力例

### Go判定の場合

```
PHASE1_24H_RESULT: GO (no_5xx=0, p95_max=0.000640, missing_snapshots=0, changes=0)
```

### No-Go判定の場合

```
PHASE1_24H_RESULT: NO-GO (reason: sustained_p95_violations=3, missing_snapshots=2_consecutive)
```

---

## メリット

- **Slack通知**: 1行で完結
- **ダッシュボード表示**: 一目で分かる
- **日報への貼り付け**: 爆速

---

## 実装方法（将来の拡張）

`phase1_24h_summary.py` の最後に追加：

```python
# 合否を1行で出力
result_line = f"PHASE1_24H_RESULT: {'GO' if can_go else 'NO-GO'} "
if can_go:
    result_line += f"(no_5xx={http_5xx_total}, p95_max={p95_max:.6f}, missing_snapshots={missing_count}, changes={change_count})"
else:
    result_line += f"(reason: {', '.join(reasons[:2])})"
print(result_line)
```

---

## 注意事項

**これは本当に任意**。今のままでも十分運用できる。

実装タイミング: Phase 2開始後にチューニングでOK。今すぐ必須じゃない。

---

**作成日**: 2026-01-15  
**バージョン**: 1.0  
**ステータス**: 任意の強化パッチ（将来の拡張）
