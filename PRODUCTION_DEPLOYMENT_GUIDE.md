# ManaOS 統合 - 本番環境デプロイメントガイド

## 概要

このガイドは、ManaOS 統合システムを本番環境にデプロイするための包括的な手順を提供します。

## 前提条件

### システム要件

- **OS**: Windows Server 2019 以上 / Ubuntu 20.04 以上
- **Python**: 3.9 以上（推奨: 3.10+）
- **Docker**: 20.10 以上（オプション）
- **メモリ**: 8GB 以上
- **ディスク**: 50GB 以上（キャッシュとログ用）

### ネットワーク要件

- オンプレミス環境での稼働
- LAN アクセスで十分
- ファイアウォールルールの設定（ポート 9502, 9510, 5678 等を許可）

## デプロイメント前チェック

### 1. デプロイメント準備チェック実行

```bash
cd c:\Users\mana4\Desktop
python manaos_integrations/scripts/deployment_checklist.py
```

期待される結果：
```
合格: 9/10 項目
⚠️  1 項目の修正が必要です
```

### 2. 環境構築スクリプト実行

```bash
cd c:\Users\mana4\Desktop
python manaos_integrations/scripts/setup_environment.py
```

このスクリプトが実行する内容：
- Python 依存関係のインストール
- 環境ファイルの準備
- ロギングディレクトリの作成
- キャッシュディレクトリの初期化
- DatabaseService（必要に応じて）
- Docker イメージのビルド
- テストの実行

## デプロイメント手順

### ステップ 1: 環境変数の設定

```bash
# manaos_integrations ディレクトリに .env ファイルを作成
cd manaos_integrations
cp .env.example .env

# 本番環境用の設定に更新
# 以下の環境変数は特に重要：
# - FLASK_ENV=production
# - DEBUG=False
# - LOG_LEVEL=INFO
# - DATABASE_URL=<本番DB接続文字列>
```

### ステップ 2: 依存関係のインストール

```bash
# 本番環境用の最小限の依存関係
python -m pip install -r requirements.txt

# セキュリティアップデート確認
python -m pip check
```

### ステップ 3: サービス起動

#### ローカルマシンでのテスト実行

```bash
# ユニフィケーション API サーバーの起動
python unified_api_server.py

# 別のターミナルで MRL メモリを起動
python -m mrl_memory_integration

# 別のターミナルで LLM ルーティングを起動
python -m llm_routing_mcp_server
```

#### Docker での実行（推奨）

```bash
# Docker イメージのビルド
docker build -t manaos-integrations:latest .

# コンテナの実行
docker run -d \
  --name manaos-api \
  -p 9502:9502 \
  -p 9510:9510 \
  -e FLASK_ENV=production \
  -v /path/to/manaos_integrations/data:/app/data \
  manaos-integrations:latest
```

#### 複数マシンでの分散デプロイ

```bash
# X280（LLMエンジン）への api_gateway デプロイ
python x280_api_gateway.py

# Konoha（GPU マシン）への ComfyUI デプロイ
python setup_distributed_konoha.py
```

### ステップ 4: ヘルスチェック

```bash
# API が正常に起動しているか確認
curl http://localhost:9502/health

# 期待される応答
# {"status": "healthy", "services": [...]}
```

### ステップ 5: セキュリティスキャン

```bash
python scripts/security_audit.py
```

実行される検査：
- Bandit セキュリティスキャン
- Safety 依存関係チェック
- クレデンシャル検出
- ハードコード値検出

## トラブルシューティング

### テスト失敗が続く場合

```bash
# 詳細なテスト実行
python -m pytest tests/unit/ -v --tb=short

# 特定のテストのみ実行
python -m pytest tests/unit/test_sample.py -v
```

### ポートコンフリクト

```bash
# 使用中のポートを確認して、別のポートを割り当て
netstat -ano | findstr :9502

# 環境変数でポートを変更
set PORT=9505
```

### メモリ不足エラー

```bash
# メモリ使用状況を監視
python scripts/deployment_checklist.py

# キャッシュをクリア
python -m pytest --cache-clear
rm -rf manaos_integrations/.cache
```

## パフォーマンス最適化

### オンデマンド リソース管理

```bash
# CPU使用率の監視と自動最適化
python manaos_integrations/gpu_resource_manager.py

# メモリプール の初期化
python manaos_integrations/database_connection_pool.py
```

### ロギング設定

`.env` ファイルに設定：

```env
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_ROTATION=daily
LOG_RETENTION_DAYS=30
```

## バックアップとリカバリ

### 定期的なバックアップ

```bash
# データベースのバックアップ
python backup_system.py

# 設定ファイルのバックアップ
cp .env .env.backup.$(date +%Y%m%d)
```

### 障害からのリカバリ

```bash
# 最後の正常なスナップショットから復旧
python backup_recovery.py --snapshot-id=<snapshot-id>
```

## 監視とアラート

### 継続的な監視

```bash
# リアルタイムダッシュボード
python realtime_dashboard.py

# ヘルスチェックの定期実行
```

### ログ分析

```bash
# 過去24時間のエラーログ
python log_manager.py --filter=ERROR --hours=24

# パフォーマンスメトリクス分析
python performance_monitor.py
```

## セキュリティベストプラクティス

1. **環境変数の保護**
   - `.env` ファイルは `.gitignore` に含める
   - 本番環境では Secret Manager を使用

2. **API キーの管理**
   - 複雑なパスワードポリシー（16文字以上）
   - 定期的なキーローテーション（90日ごと）

3. **ネットワークセキュリティ**
   - ファイアウォール設定（許可: 必要なポートのみ）
   - VPN または限定アクセス

4. **ログ監視**
   - 不正アクセスの監視
   - エラーログの定期確認

## 本番環境チェックリスト

- [ ] デプロイメント準備チェック: 全項目パス
- [ ] 環境変数が正しく設定されている
- [ ] データベースが正常に接続できる
- [ ] 全テストが成功している
- [ ] セキュリティスキャンでエラーなし
- [ ] バックアップが定期的に実行中
- [ ] ログが適切に記録されている
- [ ] モニタリングツールが有効
- [ ] インシデント対応プランが策定
- [ ] チームトレーニングが完了

## サポートと連絡先

問題が発生した場合：

1. まずこのガイドの「トラブルシューティング」セクションを確認
2. ログファイルを確認（`logs/` ディレクトリ）
3. セキュリティスキャンを実行：`python scripts/security_audit.py`
4. サポートチームに報告（ログとエラーメッセージを添付）

---

**最終更新**: 2026年2月
**バージョン**: 1.0
