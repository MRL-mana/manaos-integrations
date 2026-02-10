# ComfyUI が起動しないとき

## 症状: ImportError / ValueError で起動しない

### 1. huggingface-hub のバージョン

```
ImportError: huggingface-hub>=1.3.0,<2.0 is required ... but found huggingface-hub==0.36.0
```

**対処:**

```bash
pip install "huggingface-hub>=1.3.0,<2.0"
```

### 2. transformers の BACKENDS_MAPPING / tensorflow_text

```
ValueError: Backend should be defined in the BACKENDS_MAPPING. Offending backend: tensorflow_text
```

**対処:** transformers を ComfyUI と相性の良いバージョンに合わせ、tokenizers も合わせる。

```bash
pip install "transformers>=4.50.3,<4.52" "tokenizers>=0.21,<0.22"
```

### 3. tokenizers のバージョン

```
ImportError: tokenizers>=0.21,<0.22 is required ... but found tokenizers==0.13.3
```

**対処:**

```bash
pip install "tokenizers>=0.21,<0.22"
```

---

## まとめ（一括で直す場合）

ComfyUI が起動しないとき、次を順に試す。

```bash
pip install "huggingface-hub>=1.3.0,<2.0"
pip install "transformers>=4.50.3,<4.52" "tokenizers>=0.21,<0.22"
```

その後、**`start_comfyui_no_tqdm.bat`** で ComfyUI を起動する。

---

## カスタムノードの読み込み失敗について

- **ComfyUI-LTXVideo** の `No module named 'comfy.ldm.lightricks.vae.audio_vae'` などは、そのノード側の非対応です。本体の起動には影響しません。
- **ComfyUI-KJNodes** の LTXV ノードの AttributeError も、ノードの互換性の問題です。画像生成（generate_50）は通常のノードだけで動作します。

起動ログに **「To see the GUI go to: http://127.0.0.1:8188」** が出ていれば、ComfyUI は起動しています。ブラウザで http://localhost:8188 を開いてください。
