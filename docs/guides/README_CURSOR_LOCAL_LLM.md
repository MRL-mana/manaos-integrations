# 🚀 Cursor × ローカルLLM統合システム

**マナ仕様：母艦ローカルLLM常駐前提の完全統合**

---

## 📋 概要

Cursorをフロントエンドとして、ローカルLLMを中枢として、ManaOSを実行基盤として統合するシステム。

```
Cursor = 実装・編集の司令塔
ローカルLLM = 常駐コーディング脳（補完/チャット/リファクタ/レビュー）
ManaOS = 仕事を回す実行基盤（RAG、ログ、タスク、通知、n8n、etc）
```

---

## ⚡ クイックスタート

### 1. 自動セットアップ（推奨）

```powershell
.\setup_cursor_local_llm.ps1
```

### 2. 状態確認

```powershell
.\check_llm_setup.ps1
```

### 3. テスト実行

```powershell
python test_llm_routing.py
```

---

## 📚 ドキュメント

### 基本ガイド

- **`QUICK_START_GUIDE.md`** - クイックスタートガイド（最短5分）
- **`CURSOR_LOCAL_LLM_SETUP.md`** - 詳細な接続設定手順
- **`CURSOR_LOCAL_LLM_QUICKSTART.md`** - 最短5分で接続成功

### モデル・運用

- **`CURSOR_MODEL_RECOMMENDATIONS.md`** - RTX 5080前提のモデル選定ガイド
- **`CURSOR_PROMPT_TEMPLATES.md`** - プロンプトテンプレート集

### 統合・API

- **`MANAOS_LLM_ROUTING.md`** - 難易度ルーティング設計書
- **`LLM_ROUTING_README.md`** - API使い方ガイド

### 完了レポート

- **`IMPLEMENTATION_COMPLETE.md`** - 実装完了レポート
- **`INTEGRATION_COMPLETE.md`** - 統合完了レポート
- **`FINAL_SUMMARY.md`** - 最終まとめ

---

## 🏗️ アーキテクチャ

```
┌─────────────────┐
│     Cursor      │ ← 実装・編集の司令塔
└────────┬────────┘
         │
         │ OpenAI互換API / HTTP POST
         │
┌────────▼─────────────────────────────────────┐
│   Unified API Server (Port 9500)            │
│  ┌──────────────────────────────────────┐   │
│  │  /api/llm/route-enhanced             │   │
│  │  /api/llm/analyze                     │   │
│  │  /api/llm/models-enhanced             │   │
│  └──────────┬───────────────────────────┘   │
│             │                                 │
│  ┌──────────▼───────────────────────────┐   │
│  │  Enhanced LLM Router                  │   │
│  │  ┌────────────────────────────────┐   │   │
│  │  │  Difficulty Analyzer            │   │   │
│  │  │  - プロンプト解析                │   │   │
│  │  │  - コンテキスト長チェック        │   │   │
│  │  │  - キーワード検出                │   │   │
│  │  │  - 複雑度スコア計算              │   │   │
│  │  └──────────┬─────────────────────┘   │   │
│  │             │                          │   │
│  │    ┌────────▼────────┐                 │   │
│  │    │  Routing Logic   │                 │   │
│  │    └────────┬────────┘                 │   │
│  │             │                          │   │
│  │    ┌────────┴────────┐                 │   │
│  │    │                 │                 │   │
│  │ ┌──▼──┐        ┌───▼───┐             │   │
│  │ │軽量  │        │高精度  │             │   │
│  │ │7B-14B│        │20B-32B│             │   │
│  │ └──┬──┘        └───┬───┘             │   │
│  └────┼───────────────┼──────────────────┘   │
└───────┼───────────────┼──────────────────────┘
        │               │
        │               │
┌───────▼───┐     ┌─────▼─────┐
│ LM Studio │     │ LM Studio │
│ 7B        │     │ 32B        │
└───────────┘     └────────────┘
```

---

## 🎯 機能

### 1. 難易度判定

プロンプトの難易度を自動判定：
- プロンプト長
- コンテキスト長
- キーワード検出
- コード複雑度

### 2. 自動ルーティング

難易度に応じて適切なモデルを自動選択：
- **0-10**: 軽量モデル（7B）
- **10-30**: 中量モデル（14B）
- **30以上**: 高精度モデル（32B）

### 3. フォールバック

エラー時に自動的に軽量モデルに切り替え

### 4. LM Studio/Ollama両対応

環境に応じて選択可能

---

## 📋 APIエンドポイント

### 統合APIサーバー（ポート9500）

- **POST `/api/llm/route-enhanced`** - 拡張LLMルーティング
- **POST `/api/llm/analyze`** - 難易度分析
- **GET `/api/llm/models-enhanced`** - モデル一覧

### 拡張LLMルーティングAPI（ポート9501）

- **POST `/api/llm/route`** - LLMリクエストをルーティング
- **POST `/api/llm/analyze`** - 難易度分析
- **GET `/api/llm/models`** - モデル一覧
- **GET `/api/llm/health`** - ヘルスチェック

---

## 🚀 使い方

### Pythonから使用

```python
import requests

# 難易度分析
response = requests.post(
    "http://localhost:9500/api/llm/analyze",
    json={
        "prompt": "この関数のタイポを修正して",
        "context": {
            "code_context": "def hello():\n    print('helo')"
        }
    }
)
print(response.json())

# ルーティング実行
response = requests.post(
    "http://localhost:9500/api/llm/route-enhanced",
    json={
        "prompt": "この関数のタイポを修正して",
        "context": {
            "code_context": "def hello():\n    print('helo')"
        },
        "preferences": {
            "prefer_speed": True
        }
    }
)
print(response.json())
```

### 使用例スクリプト

```powershell
python example_usage.py
```

---

## 🎯 マナ推奨構成

### 構成1：シンプル（推奨）

**常駐**: `Qwen2.5-Coder-7B-Instruct`（Q4量子化）
- VRAM: ~4GB
- 速度: ⚡⚡⚡（超高速）
- 用途: コード補完・軽量チャット

**高精度**: `Qwen2.5-Coder-32B-Instruct`（Q8量子化）
- VRAM: ~20GB
- 速度: ⚡（中速）
- 用途: 複雑なコード生成・設計

---

## 📝 ファイル構成

### ドキュメント

- `QUICK_START_GUIDE.md` - クイックスタートガイド
- `CURSOR_LOCAL_LLM_SETUP.md` - 詳細な接続設定手順
- `CURSOR_MODEL_RECOMMENDATIONS.md` - モデル選定ガイド
- `CURSOR_PROMPT_TEMPLATES.md` - プロンプトテンプレート集
- `MANAOS_LLM_ROUTING.md` - 統合設計書
- `LLM_ROUTING_README.md` - API使い方ガイド

### 実装コード

- `llm_difficulty_analyzer.py` - 難易度判定エンジン
- `llm_router_enhanced.py` - ルーティングロジック
- `manaos_llm_routing_api.py` - Flask APIサーバー（スタンドアロン）
- `unified_api_server.py` - 統合APIサーバー（拡張済み）

### 設定・テスト

- `cursor_llm_routing_config.json` - 設定ファイル
- `test_llm_routing.py` - 統合テスト
- `example_usage.py` - 使用例
- `setup_cursor_local_llm.ps1` - 自動セットアップスクリプト
- `check_llm_setup.ps1` - 状態確認スクリプト
- `start_llm_routing_api.ps1` - APIサーバー起動スクリプト

---

## 🚨 トラブルシューティング

### 接続できない場合

1. **状態確認**
   ```powershell
   .\check_llm_setup.ps1
   ```

2. **LM Studioのサーバーが起動しているか確認**
   - 「Server」タブで「Server is running」が表示されているか

3. **Firewallを確認**
   - Windows Firewallで `localhost:1234` が許可されているか

### 遅い場合

1. **モデルサイズを確認**
   - 7Bモデルを使用しているか（32Bは重い）

2. **量子化レベルを確認**
   - Q4量子化を使用しているか（FP16は重い）

### 応答が薄い場合

1. **モデルを確認**
   - Coder系モデルを使用しているか（汎用モデルはコード弱い）

2. **プロンプトを確認**
   - プロンプトテンプレートを使用しているか

---

## 🔗 関連リンク

- [LM Studio](https://lmstudio.ai/)
- [Ollama](https://ollama.ai/)
- [Cursor](https://cursor.sh/)

---

## 📄 ライセンス

このプロジェクトはManaOS統合システムの一部です。

---

**これで"Cursor = 実装・編集の司令塔"が完成！🔥**



















