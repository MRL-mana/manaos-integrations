# Stable Diffusion プロンプト生成機能のManaOS統合

## 概要

OllamaのUncensored Llama3モデルを使用したStable Diffusion用プロンプト生成機能をManaOSに統合しました。

## 統合内容

### 追加されたアクションタイプ

- `generate_sd_prompt`: Stable Diffusion用プロンプト生成
- `sd_prompt`: 短縮形（エイリアス）

### 使用方法

#### Python APIから使用

```python
from manaos_core_api import ManaOSCoreAPI

api = ManaOSCoreAPI()

# 基本的な使用
result = api.act("generate_sd_prompt", {
    "prompt": "マナごのみのムフフ画像生成"
})

if result.get("success"):
    generated_prompt = result["prompt"]
    print(f"生成されたプロンプト: {generated_prompt}")
else:
    print(f"エラー: {result.get('error')}")
```

#### オプション

```python
result = api.act("generate_sd_prompt", {
    "prompt": "美しい夕日と海",
    "model": "llama3-uncensored",  # デフォルト: llama3-uncensored
    "temperature": 0.9  # デフォルト: 0.9
})
```

### パラメータ

- `prompt` (必須): 日本語の説明
- `description` (オプション): `prompt`のエイリアス
- `model` (オプション): 使用するOllamaモデル名（デフォルト: `llama3-uncensored`）
- `temperature` (オプション): 温度パラメータ（0.0-1.0、デフォルト: 0.9）

### レスポンス

```python
{
    "success": True,
    "prompt": "生成された英語のプロンプト",
    "japanese_description": "元の日本語の説明",
    "model": "使用されたモデル名",
    "temperature": 0.9
}
```

エラーの場合:

```python
{
    "error": "エラーメッセージ"
}
```

## 統合された機能

1. **ManaOS API統合**: `manaos_core_api.py`の`act`メソッドに統合
2. **自動保存**: 重要なアクションとして記憶システムに自動保存
3. **ログ記録**: アクション履歴に記録

## 前提条件

- Ollamaがインストールされていること
- `llama3-uncensored`モデル（または他のUncensored Llama3モデル）がインストールされていること
- Ollamaサービスが起動していること（デフォルト: `http://localhost:11434`）

## 環境変数

- `OLLAMA_URL`: Ollama APIのURL（デフォルト: `http://localhost:11434`）

## 使用例

### 例1: 基本的な使用

```python
from manaos_core_api import ManaOSCoreAPI

api = ManaOSCoreAPI()
result = api.act("generate_sd_prompt", {
    "prompt": "猫がベッドで寝ている"
})

print(result["prompt"])
```

### 例2: カスタムモデルを使用

```python
result = api.act("generate_sd_prompt", {
    "prompt": "美しい夕日と海",
    "model": "gurubot/llama3-guru-uncensored:latest",
    "temperature": 0.8
})
```

### 例3: エラーハンドリング

```python
result = api.act("generate_sd_prompt", {
    "prompt": "マナごのみのムフフ画像生成"
})

if result.get("success"):
    generated_prompt = result["prompt"]
    # プロンプトを使用
    print(f"生成されたプロンプト: {generated_prompt}")
else:
    error = result.get("error", "Unknown error")
    print(f"エラー: {error}")
```

## 統合のメリット

1. **統一されたAPI**: ManaOSの標準APIを通じてアクセス可能
2. **自動保存**: 生成されたプロンプトが自動的に記憶システムに保存
3. **ログ記録**: すべてのアクションが履歴に記録
4. **エラーハンドリング**: 統一されたエラーハンドリング
5. **他の機能との統合**: 他のManaOS機能と組み合わせて使用可能

## 関連ファイル

- `manaos_core_api.py`: メインAPI（統合場所）
- `sd-prompt.sh`: Linux/WSL用のスタンドアロンスクリプト
- `sd-prompt.ps1`: Windows用のスタンドアロンスクリプト
- `Modelfile.llama3-uncensored`: カスタムモデル設定ファイル

## 注意事項

**※重要※** Uncensoredモデルは、コンテンツフィルタリングが無効化されたモデルです。通常のモデルよりも不適切な内容が生成される可能性があります。利用は自己責任でお願いします。
