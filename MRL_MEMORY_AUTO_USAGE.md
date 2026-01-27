# MRL Memory System 自動使用設定

## 概要

MRL Memory Systemが自動的に使用されるように設定しました。LLMルーティングや会話時に自動的にメモリを活用・保存します。

## 自動使用の設定

### 1. LLMルーティング（`route()`メソッド）

**自動実行される処理:**
- ✅ プロンプト処理前にMRL Memoryから関連コンテキストを自動取得
- ✅ 取得したコンテキストをプロンプトに自動追加
- ✅ LLMレスポンスを自動的にMRL Memoryに保存

**使用例:**
```python
from llm_routing import LLMRouter

router = LLMRouter()
result = router.route(
    task_type="conversation",
    prompt="プロジェクトXの予算は？"
)
# 自動的にMRL Memoryからコンテキストを取得し、レスポンスを保存
```

### 2. チャット（`chat()`メソッド）

**自動実行される処理:**
- ✅ 会話履歴をMRL Memoryから自動取得
- ✅ 取得した履歴をコンテキストに自動追加
- ✅ 会話全体を自動的にMRL Memoryに保存

**使用例:**
```python
from llm_routing import LLMRouter

router = LLMRouter()
result = router.chat(
    messages=[
        {"role": "user", "content": "プロジェクトXについて教えて"}
    ],
    load_history=True,  # 自動的にMRL Memoryから履歴を読み込む
    auto_save=True      # 自動的にMRL Memoryに保存
)
```

### 3. ManaOS Core API（`remember()`メソッド）

**自動実行される処理:**
- ✅ `remember()`呼び出し時に自動的にMRL Memory APIに保存

**使用例:**
```python
from manaos_core_api import ManaOSCoreAPI

api = ManaOSCoreAPI()
api.remember(
    input_data={"content": "重要な情報"},
    format_type="mrl_memory"  # または "auto"
)
# 自動的にMRL Memoryに保存される
```

## 動作確認

### 状態確認
```bash
python check_mrl_memory_status.py
```

### テスト実行
```bash
python test_mrl_memory_usage.py
```

## 設定

### 環境変数

`.env`ファイルで設定可能:

- `MRL_MEMORY_API_KEY`: APIキー（認証用）
- `MRL_MEMORY_API_URL`: API URL（デフォルト: http://localhost:5105）
- `FWPKM_WRITE_MODE`: 書き込みモード（`sampled`/`full`）
- `FWPKM_WRITE_ENABLED`: 書き込み有効化（`1`/`0`）
- `FWPKM_REVIEW_EFFECT`: 復習効果（`1`/`0`）

## 自動使用の流れ

### LLMルーティング時の流れ

```
1. route()呼び出し
   ↓
2. MRL Memoryからコンテキストを自動取得
   ↓
3. プロンプトにコンテキストを自動追加
   ↓
4. LLMで処理
   ↓
5. レスポンスをMRL Memoryに自動保存
```

### チャット時の流れ

```
1. chat()呼び出し（load_history=True, auto_save=True）
   ↓
2. MRL Memoryから会話履歴を自動取得
   ↓
3. コンテキストに履歴を自動追加
   ↓
4. LLMで処理
   ↓
5. 会話全体をMRL Memoryに自動保存
```

## 注意事項

- MRL Memory APIサーバーが起動している必要があります（ポート5105）
- 認証が必要な場合は、`.env`ファイルに`MRL_MEMORY_API_KEY`を設定してください
- エラーが発生しても処理は継続されます（ログに記録されます）

## トラブルシューティング

### メモリが保存されない
- MRL Memory APIサーバーが起動しているか確認
- `FWPKM_WRITE_ENABLED=1`が設定されているか確認
- `sampled`モードの場合、10%の確率で保存されます

### コンテキストが取得されない
- MRL Memoryにデータが保存されているか確認
- 検索クエリが適切か確認

### 認証エラー
- `.env`ファイルに`MRL_MEMORY_API_KEY`が設定されているか確認
