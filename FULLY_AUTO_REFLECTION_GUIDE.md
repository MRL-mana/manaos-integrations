# 全自動反省・改善システムガイド

## 📋 概要

画像生成完了時に、**自動的に反省・改善・再生成を実行する**全自動システムです。

## 🎯 機能

### 全自動フロー

```
[画像生成完了]
    ↓
[自動評価] ← 自動実行
    ↓
[スコア < 閾値?]
    ├─ Yes → [改善提案生成] → [自動再生成] → [評価] → [比較] → [学習]
    └─ No  → [完了]
```

### 1. 自動評価

画像生成完了時に、自動的に以下の評価を実行：

- **身体崩れスコア** (anatomy_score)
- **品質スコア** (quality_score)
- **プロンプト一致度** (prompt_match_score)
- **総合スコア** (overall_score)

### 2. 自動改善提案

スコアが閾値（デフォルト: 0.7）を下回る場合、以下の改善を提案：

- **プロンプト改善**: 身体崩れ対策タグ、品質タグの追加
- **ネガティブプロンプト改善**: 身体崩れ対策の強化
- **パラメータ改善**: steps、guidance_scale、解像度などの最適化

### 3. 自動再生成

改善提案がある場合、**自動的に再生成を実行**：

- 改善されたプロンプトとパラメータで再生成
- 再生成結果も自動評価
- 元の画像と改善版を比較
- 改善が確認できたら学習データに記録

### 4. 学習機能

改善の成功・失敗から学習し、将来の改善に活用：

- 成功パターンの記録
- 失敗パターンの記録
- モデルごとの最適パラメータの学習

## 📝 使用方法

### 基本的な使い方

```python
import requests

# 画像生成をリクエスト（全自動モード）
response = requests.post("http://localhost:5559/api/generate", json={
    "prompt": "cute anime girl",
    "model": "realisian_v60.safetensors",
    "mufufu_mode": True,
    "width": 1024,
    "height": 1024
})

result = response.json()
job_id = result["job_id"]

# 少し待ってからステータスを確認
import time
time.sleep(60)  # 画像生成と評価が完了するまで待つ

status = requests.get(f"http://localhost:5559/api/job/{job_id}").json()

# 評価結果を確認
if "reflection" in status:
    evaluation = status["reflection"]["evaluation"]
    print(f"総合スコア: {evaluation['overall_score']:.2f}")
    
    # 改善版ジョブがあるか確認
    if "improved_jobs" in status:
        print(f"\n[自動改善] {len(status['improved_jobs'])}件の改善版が生成されました")
        for improved in status["improved_jobs"]:
            print(f"  ジョブID: {improved['job_id']}")
            print(f"  スコア改善: {improved['score_improvement']:+.2f}")
            print(f"  改善版スコア: {improved['improved_score']:.2f}")
```

### 改善版ジョブの確認

```python
# 改善版ジョブの詳細を確認
if "improved_jobs" in status:
    for improved in status["improved_jobs"]:
        improved_job_id = improved["job_id"]
        improved_status = requests.get(f"http://localhost:5559/api/job/{improved_job_id}").json()
        
        print(f"\n改善版ジョブ: {improved_job_id}")
        if "comparison" in improved_status:
            comp = improved_status["comparison"]
            print(f"  元のスコア: {comp['original_score']:.2f}")
            print(f"  改善版スコア: {comp['improved_score']:.2f}")
            print(f"  スコア改善: {comp['score_improvement']:+.2f}")
            print(f"  改善理由: {comp['improvement_reason']}")
```

## 🔧 設定

### 閾値の変更

デフォルトの閾値（0.7）を変更する場合：

```python
# コード内で変更
# gallery_api_server.py の threshold=0.7 を変更
```

### 最大再生成回数の変更

```python
# gallery_api_server.py の max_retries=2 を変更
```

## 📊 ジョブステータスの構造

### 元のジョブ

```json
{
  "job_id": "abc123",
  "status": "completed",
  "filename": "image.png",
  "reflection": {
    "evaluation": {
      "overall_score": 0.65,
      ...
    },
    "improvement": {
      ...
    },
    "should_regenerate": true
  },
  "improved_jobs": [
    {
      "job_id": "abc123_improved_1234567890",
      "score_improvement": 0.15,
      "improved_score": 0.80
    }
  ]
}
```

### 改善版ジョブ

```json
{
  "job_id": "abc123_improved_1234567890",
  "status": "completed",
  "filename": "image_improved.png",
  "parent_job_id": "abc123",
  "regeneration_type": "auto_improvement",
  "reflection": {
    "evaluation": {
      "overall_score": 0.80,
      ...
    }
  },
  "comparison": {
    "original_score": 0.65,
    "improved_score": 0.80,
    "score_improvement": 0.15,
    "improvement_reason": "身体崩れスコアが低い（0.60）"
  }
}
```

## 🎯 動作確認

### 自動実行の確認

1. **画像生成を実行**
   ```python
   requests.post("http://localhost:5559/api/generate", json={...})
   ```

2. **評価が自動実行される**
   - ログに「[自動反省開始]」が表示される
   - 評価結果がジョブステータスに含まれる

3. **改善提案があれば自動再生成**
   - ログに「[全自動再生成]」が表示される
   - 改善版ジョブが作成される
   - 改善版も自動評価される

4. **学習データに記録**
   - 改善成功の場合、学習データに記録される
   - 次回の改善に活用される

## ⚠️ 注意事項

1. **再生成の制限**
   - デフォルトで最大2回まで再生成（無限ループ防止）
   - 改善版の評価では自動改善は無効（再帰的改善を防止）

2. **パフォーマンス**
   - 自動再生成はバックグラウンドで実行される
   - 画像生成の完了を待つ必要がある

3. **学習データ**
   - 改善成功・失敗のパターンが蓄積される
   - データベース（`auto_improvement.db`）に保存される

## 🔄 今後の改善予定

1. **学習機能の強化**
   - 成功パターンの自動適用
   - モデルごとの最適パラメータの自動選択

2. **再生成戦略の改善**
   - 複数の改善案を試行
   - 最良の改善案を選択

3. **比較機能の強化**
   - 画像の視覚的比較
   - 改善の可視化

## 📝 まとめ

全自動反省・改善システムにより、以下のメリットがあります：

1. **完全自動化**: 画像生成から評価・改善・再生成まで自動実行
2. **継続的改善**: 学習データから継続的に改善
3. **品質向上**: 問題のある画像を自動的に検出・改善
4. **効率化**: 手動での調整が不要

**画像生成が完了すると、自動的に反省・改善・再生成が実行されます！**
