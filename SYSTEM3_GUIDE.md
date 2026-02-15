# ManaOS 自律運用システム (System3)

## 📋 概要

ManaOSの**System3レベル**自律運用を実現するコンポーネントです。サービスの自動監視、異常検知、復旧計画を提供します。

## 🤖 機能

### 1. 自動ヘルスチェック
- 全サービス（4つ）を定期的に監視
- デフォルト: 60秒間隔
- HTTPエンドポイント `/health` を使用

### 2. 異常検知
- サービスの応答失敗を自動検出
- 統計情報の収集:
  - 総チェック回数
  - 異常検知回数
  - サービス別の異常率

### 3. レポート機能
- 監視結果をリアルタイムでログ出力
- 停止時に統計サマリーを表示
- サービス別の稼働率を計算

### 4. 自動復旧（計画）
現在は**手動対応モード**で運用:
- 異常検知時に対処方法を表示
- 将来的に自動復旧ロジックを追加予定

## 🚀 使用方法

### 統合モード（推奨）

サービス起動と同時に自律監視を開始:

```powershell
# VSCode/Cursorタスク
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: すべてのサービスを起動"
```

または

```powershell
# コマンドライン
cd C:\Users\mana4\Desktop
.\.venv\Scripts\python.exe manaos_integrations\start_vscode_cursor_services.py
```

**自動的に以下が実行されます:**
1. 4つのサービスを起動
2. 初期化完了を待機（5秒）
3. ヘルスチェック実行（リトライ付き）
4. 自律監視システム起動
5. 60秒ごとに継続監視

### 単体モード

自律監視のみを実行:

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python autonomous_operations.py
```

## 📊 統計情報

監視中に `Ctrl+C` で停止すると、以下の統計が表示されます:

```
============================================================
📊 自律運用システム統計
============================================================
稼働時間: 300秒
総チェック回数: 5
異常検知回数: 0
最終チェック: 2026-02-07T18:04:38

--- サービス別統計 ---
MRL Memory:
  チェック回数: 5
  異常回数: 0
  異常率: 0.0%
  最終状態: healthy

Learning System:
  チェック回数: 5
  異常回数: 0
  異常率: 0.0%
  最終状態: healthy
...
============================================================
```

## ⚙️ 設定

### チェック間隔の変更

`start_vscode_cursor_services.py`:

```python
autonomous = AutonomousOperations(
    check_interval=60,  # 秒単位で指定
    enable_auto_recovery=False
)
```

### 自動復旧の有効化（将来機能）

```python
autonomous = AutonomousOperations(
    check_interval=60,
    enable_auto_recovery=True  # 注意: 実装完了後に有効化
)
```

## 🔄 System3レベルとは

**System3**は、ManaOSの3層アーキテクチャにおける「自律層」:

- **System1**: 基本サービス（MRL Memory, Learning System, LLM Routing, Unified API）
- **System2**: 統合・オーケストレーション（Unified API, start_vscode_cursor_services.py）
- **System3**: 自律・自己管理（autonomous_operations.py, self_*_system.py）

### System3の責務

1. **監視**: サービスの継続的なヘルスチェック
2. **診断**: 異常の検出と原因分析
3. **復旧**: 自動または手動での復旧手順
4. **最適化**: パフォーマンス監視と改善提案
5. **学習**: 過去の障害パターンから学習

## 🛡️ 安全機能

### 現在の安全設計

- **手動対応モード**: 自動復旧は無効（enable_auto_recovery=False）
- **デーモンスレッド**: メインプロセス終了時に自動停止
- **例外処理**: エラーが発生しても監視を継続
- **タイムアウト**: ヘルスチェックは5秒でタイムアウト

### 将来の安全機能

- **復旧レート制限**: 短期間に何度も再起動しない
- **エスカレーション**: 自動復旧失敗時に人間に通知
- **ロールバック**: 復旧失敗時に前の状態に戻す

## 📈 運用メトリクス

### 正常運用の目安

- **異常率**: < 5%
- **平均応答時間**: < 1秒
- **連続成功**: > 95%

### アラート条件

- 3回連続でヘルスチェック失敗
- 異常率が10%を超える
- サービスの起動失敗

## 🔧 トラブルシューティング

### 自律監視が起動しない

```powershell
# 依存関係を確認
python -c "import requests; print('✅ requests available')"

# 手動で起動テスト
cd C:\Users\mana4\Desktop\manaos_integrations
python autonomous_operations.py
```

### ヘルスチェックが失敗し続ける

1. **サービスの実行確認**:
   ```powershell
   Get-Process python | Where-Object { $_.CommandLine -like "*manaos*" }
   ```

2. **ポート確認**:
   ```powershell
   netstat -ano | findstr ":9510 :5103 :5104 :5111"
   ```

3. **手動ヘルスチェック**:
   ```powershell
   Invoke-RestMethod http://127.0.0.1:9510/health
   ```

## 📁 関連ファイル

- **自律運用**: `manaos_integrations/autonomous_operations.py`
- **サービス起動**: `manaos_integrations/start_vscode_cursor_services.py`
- **ヘルスチェック**: `manaos_integrations/check_services_health.py`
- **自己診断**: `manaos_integrations/self_diagnosis_system.py`
- **サービス監視**: `manaos_integrations/service_monitor.py`

---

**最終更新**: 2026年2月7日  
**バージョン**: 1.0.0  
**System3レベル**: 監視・検知（復旧は計画中）

