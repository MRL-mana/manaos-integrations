# 自動反省・改善システムガイド

## 📋 概要

生成された画像を自動的に評価し、問題があれば改善を試みるシステムです。

## 🎯 機能

### 1. 自動評価

生成された画像を以下の観点で自動評価します：

- **身体崩れスコア** (anatomy_score): 身体の正確性（0.0-1.0、1.0が最良）
- **品質スコア** (quality_score): 画像の品質（0.0-1.0）
- **プロンプト一致度** (prompt_match_score): プロンプトとの一致度（0.0-1.0）
- **総合スコア** (overall_score): 上記の重み付き平均

### 2. 自動改善

スコアが閾値（デフォルト: 0.7）を下回る場合、以下の改善を提案します：

- **プロンプト改善**: 身体崩れ対策タグ、品質タグの追加
- **ネガティブプロンプト改善**: 身体崩れ対策の強化
- **パラメータ改善**: steps、guidance_scale、解像度などの最適化

### 3. 学習機能

改善の成功・失敗から学習し、将来の改善に活用します。

## 📝 使用方法

### 自動評価（画像生成時に自動実行）

画像生成API (`/api/generate`) を使用すると、自動的に評価が実行されます：

```python
import requests

response = requests.post("http://localhost:5559/api/generate", json={
    "prompt": "cute anime girl",
    "model": "realisian_v60.safetensors",
    "mufufu_mode": True
})

result = response.json()
job_id = result["job_id"]

# ジョブステータスを確認（評価結果を含む）
status_response = requests.get(f"http://localhost:5559/api/job/{job_id}")
status = status_response.json()

if "reflection" in status:
    evaluation = status["reflection"]["evaluation"]
    print(f"総合スコア: {evaluation['overall_score']:.2f}")
    
    if status["reflection"].get("should_regenerate"):
        improvement = status["reflection"]["improvement"]
        print(f"再生成推奨: {improvement['reason']}")
        print(f"改善されたプロンプト: {improvement['improved_prompt']}")
```

### 手動評価

既存の画像を評価する場合：

```python
import requests

response = requests.post("http://localhost:5559/api/reflection/evaluate", json={
    "image_path": "C:/path/to/image.png",
    "prompt": "cute anime girl",
    "negative_prompt": "",
    "model": "realisian_v60.safetensors",
    "parameters": {
        "steps": 50,
        "guidance_scale": 7.5,
        "width": 1024,
        "height": 1024
    },
    "auto_improve": True,
    "threshold": 0.7
})

result = response.json()
print(f"総合スコア: {result['result']['evaluation']['overall_score']:.2f}")
```

### 統計情報の取得

```python
import requests

response = requests.get("http://localhost:5559/api/reflection/statistics")
stats = response.json()["statistics"]

print(f"総評価数: {stats['total_evaluations']}")
print(f"平均スコア: {stats['average_score']:.2f}")
print(f"改善提案数: {stats['total_improvements']}")
print(f"改善率: {stats['improvement_rate']:.2%}")
```

## 🔧 設定

### 評価閾値の変更

デフォルトの閾値（0.7）を変更する場合：

```python
# API呼び出し時に指定
response = requests.post("http://localhost:5559/api/reflection/evaluate", json={
    "threshold": 0.8,  # 閾値を0.8に変更
    # ...
})
```

### 自動改善の無効化

自動改善を無効にする場合：

```python
response = requests.post("http://localhost:5559/api/reflection/evaluate", json={
    "auto_improve": False,  # 自動改善を無効化
    # ...
})
```

## 📊 評価結果の構造

```json
{
  "evaluation": {
    "image_path": "path/to/image.png",
    "prompt": "cute anime girl",
    "overall_score": 0.65,
    "anatomy_score": 0.6,
    "quality_score": 0.7,
    "prompt_match_score": 0.65,
    "anatomy_issues": [
      "身体崩れ対策タグが不足している可能性",
      "解像度が低い（512x512）。身体崩れが増える可能性"
    ],
    "quality_issues": [],
    "prompt_mismatches": [],
    "improvements": [
      "身体崩れ対策タグを追加: perfect anatomy, correct anatomy",
      "解像度を1024x1024以上に上げる",
      "ステップ数を50以上に設定"
    ]
  },
  "improvement": {
    "original_prompt": "cute anime girl",
    "improved_prompt": "perfect anatomy, correct anatomy, masterpiece, best quality, ..., cute anime girl",
    "original_parameters": {
      "steps": 30,
      "width": 512,
      "height": 512
    },
    "improved_parameters": {
      "steps": 50,
      "width": 1024,
      "height": 1024,
      "guidance_scale": 7.5,
      "sampler": "dpmpp_2m",
      "scheduler": "karras"
    },
    "reason": "身体崩れスコアが低い（0.60）; 品質スコアが低い（0.70）",
    "expected_improvement": 0.35
  },
  "should_regenerate": true
}
```

## 🎯 改善提案の活用

改善提案を取得したら、以下のように再生成できます：

```python
# 改善提案を取得
improvement = status["reflection"]["improvement"]

# 改善されたパラメータで再生成
response = requests.post("http://localhost:5559/api/generate", json={
    "prompt": improvement["improved_prompt"],
    "negative_prompt": improvement["improved_negative_prompt"],
    "model": "realisian_v60.safetensors",
    "steps": improvement["improved_parameters"]["steps"],
    "guidance_scale": improvement["improved_parameters"]["guidance_scale"],
    "width": improvement["improved_parameters"]["width"],
    "height": improvement["improved_parameters"]["height"],
    "sampler": improvement["improved_parameters"]["sampler"],
    "scheduler": improvement["improved_parameters"]["scheduler"],
    "mufufu_mode": True
})
```

## 📈 データベース

評価結果と改善提案は `auto_improvement.db` に保存されます：

- `evaluations` テーブル: 評価履歴
- `improvements` テーブル: 改善履歴

## 🔄 今後の改善予定

1. **より高度な画像解析**
   - 実際の画像解析ライブラリを使用した身体崩れ検出
   - AIモデルを使用した品質評価

2. **学習機能の強化**
   - 成功パターンの自動適用
   - モデルごとの最適パラメータの学習

3. **自動再生成**
   - 改善提案に基づく自動再生成
   - 再生成結果の比較

## 📝 まとめ

自動反省・改善システムにより、以下のメリットがあります：

1. **品質の向上**: 問題のある画像を自動的に検出
2. **改善の自動化**: 手動での調整が不要
3. **学習機能**: 過去の結果から継続的に改善
4. **統計情報**: 生成品質の傾向を把握

画像生成の品質を継続的に向上させることができます。
