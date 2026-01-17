## ManaOS Integrations（母艦）

ManaOS と外部システム（ComfyUI / n8n / Slack / Rows / Google Drive / ローカルLLM など）をつなぐ統合リポジトリです。
大きく **「統合API（運用系）」** と **「CASTLE-EX（学習/評価系）」** の2系統があります。

---

## クイックスタート（統合API）

### 1) 依存関係インストール

```bash
pip install -r requirements.txt
```

### 2) 環境変数を設定（推奨: `.env`）

- `env.example` をコピーして `.env` を作成し、必要な値を設定してください
- `.env` はローカル専用（Gitにコミットしない）

詳細は `ENVIRONMENT_VARIABLES_GUIDE.md` を参照してください。

### 3) 統合APIサーバー起動

```bash
python unified_api_server.py
```

起動後の代表エンドポイント:
- `GET /health`
- `GET /ready`
- `GET /api/integrations/status`

---

## Dockerで起動（統合サービス）

統合サービス群をまとめて起動したい場合は compose を使います。

- コア統合: `docker-compose.manaos-services.yml`
- AI系（Ollama / ComfyUI 等）: `docker-compose.ai-services.yml`
- 全部まとめ: `docker-compose.all-services.yml`（compose実装により `include` サポートが必要）

---

## 運用スクリプト

- `scripts/`: 学習・起動・一括実行の補助スクリプト（`.bat`/`.ps1`/`.py`/`.sh`）
- `docs/training/`: 学習の手順書・運用メモ
- `tools/`: スクリプトから使う共通ユーティリティ（例: LM Studioモデル選択）

### 入口コマンド（よく使うもの）

| 目的 | コマンド例 |
| --- | --- |
| 統合APIを起動 | `python unified_api_server.py` |
| CASTLE-EX パイプライン（生成→検証→スケジュール） | `python castle_ex/castle_ex_integrated.py pipeline --count 200 --output-dir ./out` |
| CASTLE-EX 評価（例） | `python castle_ex/castle_ex_evaluator.py --output evaluation.json` |
| 学習（準備チェック） | `python scripts/start_training.py` |
| 学習（自動） | `python scripts/run_training.py` |
| 学習（監視） | `python scripts/monitor_training.py --output-dir ./outputs/castle_ex_v1_0` |
| 学習（Windows入口） | `scripts/start_training.bat` / `scripts/quick_start_training.bat` |
| 学習（低メモリ/Windows） | `scripts/start_training_low_memory.bat` |
| 学習（フル/Windows） | `scripts/run_training_final.bat` |
| LM Studio結果のDriveアップロード | `python scripts/lm_studio/upload_lm_studio_results.py` |
| ComfyUI: 50枚バッチ生成 | `python scripts/comfyui/generate_50_mixed_models.py` |
| ComfyUI: 50枚バッチ生成（身体崩れ防止） | `python scripts/comfyui/generate_50_mixed_models_body_safe.py` |
| Excel OCR: 超積極修正 | `python scripts/excel/excel_llm_ultra_aggressive_corrector.py <in.xlsx> <out.xlsx> --passes 5` |

---

## CASTLE-EX（学習データ/評価）

学習データ生成・検証・スケジュール生成・評価の入口は `docs/castle-ex/CASTLE_EX_README.md` を参照してください。

最小例:

```bash
python castle_ex/castle_ex_integrated.py pipeline --count 200 --output-dir ./out
```

---

## リポジトリの“置き場”方針（推奨）

母艦が肥大化しやすいので、生成物は原則リポジトリ直下に置かず、以下に寄せます。

- `data/`（ローカルデータ、認証情報、取得物など）: Git管理外
- `out/` / `outputs/` / `snapshots/`: 実行結果の退避（Git管理外）
- `docs/`: 手順・設計

`.gitignore` 側でも、生成データ（例: `*.jsonl`）や `snapshots/` を除外する方針にしています。

