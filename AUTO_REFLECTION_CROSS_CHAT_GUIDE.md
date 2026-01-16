# 自動反省・改善システムのクロスチャット対応ガイド

## 📋 概要

自動反省・改善システムは、**どのチャット（Cursorの別セッション）から画像生成を実行しても、自動的に動作します**。

## ✅ 動作確認

### システムの動作フロー

```
[別チャットで画像生成]
    ↓
[gallery_api_server.py の /api/generate エンドポイント]
    ↓
[画像生成完了]
    ↓
[自動反省・改善システムが自動実行]
    ↓
[評価結果をデータベースに保存]
    ↓
[ジョブステータスに評価結果を含める]
```

### 動作する条件

1. **Gallery APIサーバーが起動している**
   - `gallery_api_server.py`が実行されている必要があります
   - ポート5559でリッスンしている必要があります

2. **自動反省・改善システムが利用可能**
   - `auto_reflection_improvement.py`がインポート可能
   - データベース（`auto_improvement.db`）が作成可能

3. **画像生成APIを使用**
   - `/api/generate`エンドポイントを使用している必要があります

## 🔍 動作確認方法

### 1. APIサーバーの起動確認

```python
import requests

try:
    response = requests.get("http://localhost:5559/api/images", timeout=5)
    if response.status_code == 200:
        print("[OK] Gallery APIサーバーが起動しています")
    else:
        print(f"[WARN] APIサーバーが応答していますが、エラー: {response.status_code}")
except:
    print("[ERROR] Gallery APIサーバーが起動していません")
    print("gallery_api_server.py を起動してください")
```

### 2. 別チャットから画像生成を実行

```python
import requests

# 別チャットから画像生成
response = requests.post("http://localhost:5559/api/generate", json={
    "prompt": "cute anime girl",
    "model": "realisian_v60.safetensors",
    "mufufu_mode": True,
    "width": 1024,
    "height": 1024
})

result = response.json()
job_id = result["job_id"]
print(f"ジョブID: {job_id}")

# 少し待ってからステータスを確認
import time
time.sleep(30)  # 画像生成が完了するまで待つ

status_response = requests.get(f"http://localhost:5559/api/job/{job_id}")
status = status_response.json()

# 評価結果を確認
if "reflection" in status:
    evaluation = status["reflection"]["evaluation"]
    print(f"✅ 自動反省が実行されました！")
    print(f"総合スコア: {evaluation['overall_score']:.2f}")
    
    if status["reflection"].get("should_regenerate"):
        print(f"⚠️ 再生成推奨: {status['reflection']['improvement']['reason']}")
else:
    print("⚠️ 評価結果が見つかりません（まだ生成中、またはエラー）")
```

### 3. 統計情報で確認

```python
import requests

# 統計情報を取得
response = requests.get("http://localhost:5559/api/reflection/statistics")
stats = response.json()["statistics"]

print(f"総評価数: {stats['total_evaluations']}")
print(f"平均スコア: {stats['average_score']:.2f}")
print(f"改善提案数: {stats['total_improvements']}")
```

## 📊 データベースの共有

自動反省・改善システムは、**同じデータベースファイル（`auto_improvement.db`）を使用**します。

- すべてのチャットセッションから同じデータベースにアクセス
- 評価履歴が蓄積される
- 統計情報が共有される

## 🔧 トラブルシューティング

### 問題: 評価が実行されない

**確認事項:**
1. Gallery APIサーバーが起動しているか
2. `auto_reflection_improvement.py`がインポート可能か
3. ログにエラーがないか

**解決方法:**
```python
# gallery_api_server.py のログを確認
# 以下のメッセージが表示されているか確認:
# "✅ 自動反省・改善システムを読み込みました"
# "[自動反省開始] ..."
```

### 問題: 評価結果がジョブステータスに含まれない

**確認事項:**
1. 画像生成が正常に完了したか
2. ジョブステータスを確認するタイミング（生成完了後）

**解決方法:**
```python
# ジョブステータスを確認する前に、生成が完了するまで待つ
import time

job_id = "..."  # ジョブID
max_wait = 300  # 最大5分待つ

for i in range(max_wait // 5):
    status = requests.get(f"http://localhost:5559/api/job/{job_id}").json()
    
    if status.get("status") == "completed":
        if "reflection" in status:
            print("✅ 評価結果が見つかりました")
            break
    
    time.sleep(5)
```

## 📝 まとめ

**自動反省・改善システムは、どのチャットから画像生成を実行しても動作します。**

- ✅ APIサーバー経由で画像生成を実行すれば、自動的に評価が実行される
- ✅ 評価結果はデータベースに保存され、すべてのチャットセッションから参照可能
- ✅ 統計情報も共有される

**重要なポイント:**
- Gallery APIサーバー（`gallery_api_server.py`）が起動している必要がある
- `/api/generate`エンドポイントを使用する必要がある
- 画像生成が完了すると、自動的に評価が実行される
