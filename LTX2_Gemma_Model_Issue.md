# LTX-2 Gemmaモデルの問題

## 現在の問題

`LTXVGemmaCLIPModelLoader`が`tokenizer.model`を見つけられません。

## エラー詳細

```
ERROR: clip input is invalid: None
No files matching pattern 'tokenizer.model' found under C:\ComfyUI\models
```

## 原因

`LTXVGemmaCLIPModelLoader`は以下のロジックでファイルを探します：

1. `gemma_path`として`model-00001-of-00004.safetensors`を受け取る
2. `folder_paths.get_full_path("text_encoders", gemma_path)`でファイルパスを取得
3. `path.parents[1]`で`model_root`（`text_encoders`ディレクトリ）を取得
4. `model_root`から`tokenizer.model`を探す

しかし、`tokenizer.model`は`gemma-3-12b-it-qat-q4_0-unquantized`ディレクトリ内にある必要があります。

## 解決方法

### 方法1: Gemmaモデルを正しくダウンロード

`gemma-3-12b-it-qat-q4_0-unquantized`ディレクトリ内に以下のファイルが必要です：

- `tokenizer.model`
- `model-*.safetensors` (複数ファイル)
- `preprocessor_config.json`
- その他の設定ファイル

### 方法2: ワークフロー例の形式を使用

ワークフロー例では、`gemma_path`として`gemma-3-12b-it-qat-q4_0-unquantized/model-00001-of-00005.safetensors`という形式を使用しています。

しかし、`folder_paths.get_filename_list("text_encoders")`は、`text_encoders`ディレクトリ内のファイル名のみを返すため、この形式は受け付けられません。

### 方法3: 一時的にGemma CLIPを無効化

標準のCLIPを使用する（品質が低下する可能性があります）

## 推奨される解決方法

Gemmaモデルを完全にダウンロードし、`tokenizer.model`を`text_encoders`ディレクトリ内に配置するか、`gemma-3-12b-it-qat-q4_0-unquantized`ディレクトリ内に配置する必要があります。
