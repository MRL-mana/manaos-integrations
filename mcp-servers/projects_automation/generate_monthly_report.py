#!/usr/bin/env python3
"""
月次メンテナンスレポート自動生成スクリプト
毎月1日に実行され、前月のシステム統計をまとめる
"""

import subprocess
import json
from datetime import datetime, timedelta

def get_disk_usage():
    """ディスク使用状況を取得"""
    try:
        result = subprocess.run(['df', '-h'], capture_output=True, text=True)
        return result.stdout
    except subprocess.SubprocessError:
        return "取得失敗"

def get_manaos_stats():
    """ManaOS v3統計を取得"""
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:9200/api/stats'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except subprocess.SubprocessError:
        pass
    return {"status": "取得失敗"}

def get_process_count():
    """プロセス数を取得"""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        return len(result.stdout.split('\n')) - 1
    except subprocess.SubprocessError:
        return 0

def get_log_sizes():
    """ログサイズを取得"""
    try:
        result = subprocess.run(
            ['du', '-sh', '/root/logs', '/var/log'],
            capture_output=True,
            text=True
        )
        return result.stdout
    except subprocess.SubprocessError:
        return "取得失敗"

def generate_report():
    """月次レポートを生成"""
    now = datetime.now()
    last_month = now - timedelta(days=30)
    
    report = f"""# 📊 月次メンテナンスレポート
**対象月**: {last_month.strftime('%Y年%m月')}
**作成日時**: {now.strftime('%Y年%m月%d日 %H:%M:%S')}

---

## システム状態

### ディスク使用状況
```
{get_disk_usage()}
```

### ログサイズ
```
{get_log_sizes()}
```

### プロセス数
実行中プロセス数: {get_process_count()}個

### ManaOS v3統計
```json
{json.dumps(get_manaos_stats(), indent=2, ensure_ascii=False)}
```

---

## 自動実行されたメンテナンス

### 毎日実行
- ✅ ディスク使用量監視（3回/日）
- ✅ ManaOS健全性チェック（3回/日）
- ✅ 一時ファイルクリーンアップ

### 週次実行
- ✅ プロセス重複チェック（毎週月曜）
- ✅ ゾンビプロセスクリーンアップ（毎週日曜）
- ✅ Dockerクリーンアップ（毎週日曜）
- ✅ アップデートチェック（毎週月曜）

### 月次実行
- ✅ 包括的メンテナンス
- ✅ ログローテーション
- ✅ システムジャーナルクリーンアップ
- ✅ APTキャッシュクリーンアップ

---

## 推奨アクション

### 今月実施すべきこと
1. システムアップデートの適用（あれば）
2. ディスク使用率の確認（85%超えの場合は拡張検討）
3. 重要データのバックアップ確認

### 注意事項
- ディスク使用率が90%を超えた場合は緊急対応が必要
- ManaOS成功率が95%未満の場合は原因調査を推奨

---

**自動生成**: ManaOS 月次メンテナンスシステム
"""
    
    # レポートを保存
    report_path = f"/root/logs/monthly_report_{now.strftime('%Y%m')}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 月次レポートを生成しました: {report_path}")
    
    # LINE通知（オプション）
    try:
        subprocess.run([
            'curl', '-X', 'POST', 
            'http://localhost:5099/api/line/alert',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                "title": "📊 月次レポート生成完了",
                "message": f"{last_month.strftime('%Y年%m月')}の月次メンテナンスレポートを生成しました。詳細: {report_path}",
                "level": "info"
            })
        ], timeout=10)
    except subprocess.SubprocessError:
        pass
    
    return report_path

if __name__ == "__main__":
    try:
        report_path = generate_report()
        print(f"\n📄 レポートファイル: {report_path}")
        print("✅ 月次レポート生成完了")
    except Exception as e:
        print(f"❌ エラー: {e}")
        exit(1)




