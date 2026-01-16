# MRL Memory System - 実装計画

## ✅ 完了した実装

1. **基本システム**
   - `mrl_memory_extractor.py`: 抽出器
   - `mrl_memory_rehearsal.py`: 復習効果
   - `mrl_memory_promoter.py`: 昇格ルール
   - `mrl_memory_system.py`: 統合システム

2. **品質改善**
   - `mrl_memory_priority_resolver.py`: RAGとFWPKMの競合解決
   - `mrl_memory_gating.py`: ゲーティング機構
   - `mrl_memory_metrics.py`: パフォーマンス測定
   - `mrl_memory_api_security.py`: APIの安全対策

3. **テスト**
   - `test_mrl_memory.py`: 最小テスト3本
   - `test_mrl_memory_integration.py`: 統合テスト
   - `benchmark_mrl_memory.py`: ベンチマーク

---

## 📋 次のステップ

### 1. 統合システムの修正（必須）

`mrl_memory_integration.py`を修正して、新しいコンポーネントを組み込む。

**修正内容**:
- `MemoryPriorityResolver`の統合
- `MemoryGating`の統合
- `MRLMemoryMetrics`の統合
- RAGメモリとの統合

### 2. APIの安全対策の適用（必須）

`mrl_memory_integration.py`のFlask APIに安全対策を適用。

**修正内容**:
- 認証デコレータの適用
- レート制限デコレータの適用
- 入力サイズチェック
- PIIマスキング

### 3. テストの実行（必須）

最小テスト3本を実行して合格条件を確認。

**実行コマンド**:
```bash
pytest test_mrl_memory.py -v
pytest test_mrl_memory_integration.py -v
python benchmark_mrl_memory.py
```

### 4. 段階的ロールアウト（推奨）

本番デプロイは段階的に行う。

**段階案**:
1. Read-onlyモード（更新なし・参照だけ）
2. Write 10%（一部リクエストだけ更新）
3. Write 100%
4. Review effectを段階投入

---

## 🎯 合格条件

### 必須の合格条件（最低ライン）

1. **再現性**: 同じ入力→同じ出力（or 許容範囲）
2. **メモリ汚染耐性**: 誤情報・ノイズが入っても回答が破綻しない
3. **崩壊防止が効く**: 特定スロットに偏り続けない
4. **劣化しない**: 長文を処理しても"前半忘れ"が減る
5. **統合が破綻しない**: RAG（長期）とFWPKM（短期）の競合で事故らない

### テスト合格目安

- **テストA（長文整合）**: ONで明確に改善（少なくとも"前半忘れ"が減る）
- **テストB（ノイズ耐性）**: 矛盾検出 or 低確度扱いに落とす（強く断言しない）
- **テストC（復習効果）**: 2回目で必要情報の再利用が増える（成功率UP or 参照率UP）

---

## ⚠️ 注意事項

### 実装の簡易性

現在の実装は簡易版（全件読み込み/書き込み）です。
本番では最適化が必要です。

### パフォーマンス

大量のエントリがある場合、検索が遅くなる可能性があります。
本番ではインデックス（SQLite等）を使うべきです。

### APIの安全対策

本番運用するなら認証、レート制限、入力サイズ制限、ログのマスキング（PII）が必要です。
