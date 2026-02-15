#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 Runbook生成スクリプト
本番運用の取説を1枚にまとめる
"""

import os
from pathlib import Path
from datetime import datetime

def generate_runbook(
    vault_path: str = os.getenv(
        "OBSIDIAN_VAULT_PATH",
        str(Path.home() / "Documents" / "Obsidian Vault"),
    ),
    runbook_relpath: str = r"ManaOS\System\Runbook_System3.md",
) -> str:
    """Generate System 3 Runbook"""

    VAULT = Path(vault_path)
    RUNBOOK_MD = VAULT / runbook_relpath

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = f"""# System 3 Runbook - 本番運用手順書

**最終更新**: {now}
**対象**: System 3 AI運用チーム

---

## 📋 サービス一覧

### Core Services

| サービス名 | ポート | 起動スクリプト | Health URL |
|-----------|--------|---------------|------------|
| Intrinsic Score API | 5130 | `intrinsic_score_api.py` | `http://127.0.0.1:5130/api/score` |
| Task Queue | 5104 | `task_queue_system.py` | `http://127.0.0.1:5104/health` |
| Unified Orchestrator | 5106 | `unified_orchestrator.py` | `http://127.0.0.1:5106/health` |
| Unified API Server | 9510 | `unified_api_server.py` | `http://127.0.0.1:9510/health` |

### Status & Monitoring

| サービス名 | ポート | 起動スクリプト | Health URL |
|-----------|--------|---------------|------------|
| System Status API | 5112 | `system_status_api.py` | `http://127.0.0.1:5112/api/health` |
| SSOT Generator | - | `ssot_generator.py` | - |

### Integration Services

| サービス名 | ポート | 起動スクリプト | Health URL |
|-----------|--------|---------------|------------|
| Slack Integration | 5114 | `slack_integration.py` | `http://127.0.0.1:5114/api/health` |
| Portal Integration | 5108 | `portal_integration_api.py` | `http://127.0.0.1:5108/api/health` |

---

## 🚨 緊急復旧手順

### ケース1: 全部落ちた（全サービス停止）

**3ステップで復旧**:

1. **状態確認**
   ```powershell
   # 全ポート確認
    netstat -ano | findstr "5130 5104 5106 9510 5112"

   # プロセス確認
   Get-Process python | Where-Object {{$_.Path -like "*manaos*"}}
   ```

2. **一括起動**
   ```powershell
   cd C:\\Users\\mana4\\Desktop\\manaos_integrations
   .\\start_all_services_unified.ps1
   ```

3. **動作確認**
   ```powershell
   # Health check
   Invoke-RestMethod http://127.0.0.1:5130/api/score
   Invoke-RestMethod http://127.0.0.1:5104/health
   Invoke-RestMethod http://127.0.0.1:5106/health
    Invoke-RestMethod http://127.0.0.1:9510/health
   ```

**所要時間**: 約5分

---

### ケース2: 1個だけ死んだ（個別サービス停止）

**切り分け手順**:

#### Intrinsic Score API (5130) が死んだ

```powershell
# 1. ポート確認
netstat -ano | findstr "5130"

# 2. プロセス確認
Get-Process python | Where-Object {{$_.CommandLine -like "*intrinsic_score*"}}

# 3. 再起動
cd C:\\Users\\mana4\\Desktop\\manaos_integrations
python intrinsic_score_api.py

# 4. 確認
Invoke-RestMethod http://127.0.0.1:5130/api/health
```

#### Task Queue (5104) が死んだ

```powershell
# 1. ポート確認
netstat -ano | findstr "5104"

# 2. 再起動
cd C:\\Users\\mana4\\Desktop\\manaos_integrations
python task_queue_system.py

# 3. 確認
Invoke-RestMethod http://127.0.0.1:5104/health
```

#### Unified Orchestrator (5106) が死んだ

```powershell
# 1. ポート確認
netstat -ano | findstr "5106"

# 2. 再起動
cd C:\\Users\\mana4\\Desktop\\manaos_integrations
python unified_orchestrator.py

# 3. 確認
Invoke-RestMethod http://127.0.0.1:5106/api/health
```

#### Unified API Server (9510) が死んだ

```powershell
# 1. ポート確認
netstat -ano | findstr "9510"

# 2. 再起動
cd C:\\Users\\mana4\\Desktop\\manaos_integrations
python unified_api_server.py

# 3. 確認
Invoke-RestMethod http://127.0.0.1:9510/health
```

---

## 📁 ログ場所

### 日次ログ

- **場所**: `C:\\Users\\mana4\\Documents\\Obsidian Vault\\ManaOS\\System\\Daily\\`
- **ファイル名**: `System3_Daily_YYYY-MM-DD.md`
- **用途**: 日次スコア・アクティビティ記録
- **保持期間**: 30日（推奨）

### 週次レビュー

- **場所**: `C:\\Users\\mana4\\Documents\\Obsidian Vault\\ManaOS\\System\\Playbook_Review\\`
- **ファイル名**: `Playbook_Review_YYYY-MM-DD.md`
- **用途**: 週次スコア変化・改善アクション
- **保持期間**: 12週（推奨）

### エラーログ

- **場所**: `C:\\Users\\mana4\\Desktop\\manaos_integrations\\logs\\`
- **ファイル名**: `*_error.log`, `*.log`
- **用途**: サービスエラー・クラッシュ記録
- **保持期間**: 7日（推奨）

### メトリクス

- **場所**: `C:\\Users\\mana4\\Desktop\\manaos_integrations\\`
- **ファイル名**: `manaos_status.json`, `*.jsonl`
- **用途**: システム状態・スコア履歴
- **保持期間**: 30日（推奨）

---

## 🔧 よくある事故と対処法

### 1. Encoding Error（文字化け）

**症状**:
- `SyntaxError: invalid character`
- `UnicodeDecodeError`

**原因**:
- ファイルエンコーディング不一致
- 日本語文字の破損

**対処法**:
```powershell
# 1. ファイルをUTF-8で再保存
python -c "with open('create_system3_status.py', 'r', encoding='utf-8', errors='replace') as f: content = f.read(); open('create_system3_status.py', 'w', encoding='utf-8', newline='').write(content)"

# 2. 問題行を確認
python -m py_compile create_system3_status.py

# 3. 該当行を修正
```

**予防策**:
- ファイル先頭に `# -*- coding: utf-8 -*-` を追加
- エディタのエンコーディング設定をUTF-8に統一

---

### 2. Port Already in Use（ポート競合）

**症状**:
- `OSError: [WinError 10048] 通常、各ソケット アドレス (プロトコル/ネットワーク アドレス/ポート) は一度に使用できるのは 1 つだけです`
- `Address already in use`

**原因**:
- 既存プロセスがポートを使用中
- 前回起動が正常終了していない

**対処法**:
```powershell
# 1. ポート使用プロセスを確認
netstat -ano | findstr "5130"

# 2. プロセスIDを取得して終了
taskkill /PID <PID> /F

# 3. サービスを再起動
python <service_script>.py
```

**予防策**:
- サービス起動前にポートチェック
- 正常終了ハンドラーを実装

---

### 3. Task Scheduler Error（タスクスケジューラエラー）

**症状**:
- `System3_Status_Update` タスクが実行されない
- タスクが「準備完了」のまま実行されない

**原因**:
- Pythonパスの問題
- 作業ディレクトリの不一致
- 権限不足

**対処法**:
```powershell
# 1. タスク状態確認
Get-ScheduledTask -TaskName "System3_Status_Update"

# 2. 手動実行テスト
python C:\\Users\\mana4\\Desktop\\manaos_integrations\\create_system3_status.py

# 3. タスク再登録
powershell -ExecutionPolicy Bypass -File schedule_system3_status.ps1

# 4. 実行履歴確認
Get-ScheduledTaskInfo -TaskName "System3_Status_Update"
```

**予防策**:
- タスク作成時にフルパスを使用
- 実行権限を確認

---

### 4. API Connection Error（API接続エラー）

**症状**:
- `Connection refused`
- `Timeout`
- `N/A` が表示される

**原因**:
- サービスが起動していない
- ポート番号の不一致
- ファイアウォール設定

**対処法**:
```powershell
# 1. サービス状態確認
   Invoke-RestMethod http://127.0.0.1:5130/api/score -ErrorAction SilentlyContinue
   Invoke-RestMethod http://127.0.0.1:5104/health -ErrorAction SilentlyContinue

# 2. サービス起動
cd C:\\Users\\mana4\\Desktop\\manaos_integrations
python intrinsic_score_api.py
python task_queue_system.py

# 3. 接続確認
python create_system3_status.py
```

**予防策**:
- エラーハンドリングを実装（既に実装済み）
- フォールバック値を設定

---

### 5. File Not Found（ファイル不存在）

**症状**:
- `FileNotFoundError`
- `System3_Status.md` が生成されない

**原因**:
- Obsidian Vaultパスの不一致
- ディレクトリが存在しない

**対処法**:
```powershell
# 1. パス確認
Test-Path "C:\\Users\\mana4\\Documents\\Obsidian Vault\\ManaOS\\System"

# 2. ディレクトリ作成
New-Item -ItemType Directory -Path "C:\\Users\\mana4\\Documents\\Obsidian Vault\\ManaOS\\System" -Force

# 3. 再実行
python create_system3_status.py
```

**予防策**:
- ディレクトリ自動作成を実装（既に実装済み）

---

## 🔄 定期メンテナンス

### 日次（自動）

- **System3_Status.md更新**: 毎日23:00（タスクスケジューラ）
- **日次ログ生成**: 自動

### 週次（手動推奨）

- **週次レビュー確認**: 毎週月曜
- **ログローテーション**: 30日超のログをアーカイブ
- **メトリクス確認**: スコア推移・ToDoメトリクス確認

### 月次（手動推奨）

- **バックアップ**: Obsidian Vault全体をバックアップ
- **ログクリーンアップ**: 7日超のエラーログを削除
- **パフォーマンス確認**: スコア・メトリクスの傾向確認

---

## 📞 緊急連絡先

- **システム管理者**: Mana
- **ログ確認場所**: `C:\\Users\\mana4\\Desktop\\manaos_integrations\\logs\\`
- **設定ファイル**: `C:\\Users\\mana4\\Desktop\\manaos_integrations\\`

---

## 📝 変更履歴

- **2026-01-04**: Runbook初版作成（Phase B完了時点）

---

**重要**: このRunbookは運用開始時に必ず確認し、実際の運用で更新を継続してください。

"""

    RUNBOOK_MD.parent.mkdir(parents=True, exist_ok=True)
    RUNBOOK_MD.write_text(content, encoding="utf-8", newline="\n")

    return str(RUNBOOK_MD)

if __name__ == "__main__":
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    path = generate_runbook()
    print(f"OK Runbook generated: {path}")
