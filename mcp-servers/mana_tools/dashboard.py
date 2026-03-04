#!/usr/bin/env python3
"""
ManaOS ポリシーシステム ダッシュボード
キュー状態、競合件数、ポリシー違反を可視化
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.policy.action_queue import ActionQueue
from datetime import datetime, timedelta
import json

def generate_dashboard_html():
    """ダッシュボードHTMLを生成"""

    # データを取得
    queue = ActionQueue()
    queue_status = queue.get_queue_status()

    # 観測ログから統計を取得
    observability_log = Path("/root/logs/policy_observability.log")
    conflicts = 0
    rejections = 0
    rollbacks = 0

    if observability_log.exists():
        cutoff = datetime.now() - timedelta(hours=24)
        with open(observability_log, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                    if entry_time > cutoff:
                        conflicts += entry.get("conflicts", 0)
                        rejections += entry.get("violations", 0)
                        rollbacks += entry.get("rollbacks", 0)
                except IOError:
                    pass

    # PAUSE_AUTOフラグ状態
    pause_flag = Path("/root/infra/flags/PAUSE_AUTO")
    is_paused = pause_flag.exists()

    # HTML生成
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ManaOS ポリシーシステム ダッシュボード</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: white;
            text-align: center;
            margin-bottom: 30px;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .card h2 {{
            margin-top: 0;
            color: #333;
            font-size: 18px;
        }}
        .stat {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .status {{
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }}
        .status.ok {{
            background: #d4edda;
            color: #155724;
        }}
        .status.warning {{
            background: #fff3cd;
            color: #856404;
        }}
        .status.error {{
            background: #f8d7da;
            color: #721c24;
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 ManaOS ポリシーシステム ダッシュボード</h1>

        <div class="dashboard">
            <div class="card">
                <h2>📊 アクションキュー</h2>
                <div class="stat">{queue_status['pending']}</div>
                <p>待機中</p>
                <div class="stat" style="font-size: 24px;">{queue_status['processing']}</div>
                <p>処理中</p>
                <div class="stat" style="font-size: 24px; color: #dc3545;">{queue_status['failed']}</div>
                <p>失敗</p>
            </div>

            <div class="card">
                <h2>🔒 リソースロック</h2>
                <div class="stat">{queue_status['locks']}</div>
                <p>有効なロック</p>
            </div>

            <div class="card">
                <h2>⚠️  過去24時間の統計</h2>
                <div class="stat" style="color: #ffc107;">{conflicts}</div>
                <p>競合検出</p>
                <div class="stat" style="font-size: 24px; color: #dc3545;">{rejections}</div>
                <p>却下</p>
                <div class="stat" style="font-size: 24px; color: #dc3545;">{rollbacks}</div>
                <p>ロールバック</p>
            </div>

            <div class="card">
                <h2>🛡️  システム状態</h2>
                <div class="status {'error' if is_paused else 'ok'}">
                    {'⚠️  PAUSE_AUTOフラグ有効（自動アクション停止中）' if is_paused else '✅ システム正常動作中'}
                </div>
                <p style="margin-top: 10px; color: #666;">
                    最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </div>

        <div class="footer">
            <p>ManaOS Policy System Dashboard</p>
            <p>自動更新: ページをリロードしてください</p>
        </div>
    </div>

    <script>
        // 30秒ごとに自動リロード
        setTimeout(function() {{
            location.reload();
        }}, 30000);
    </script>
</body>
</html>
"""

    return html

def main():
    """ダッシュボードを生成"""
    html = generate_dashboard_html()

    # ダッシュボードファイルを保存
    dashboard_file = Path("/root/dashboards/policy_dashboard.html")
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    dashboard_file.write_text(html, encoding='utf-8')

    print("✅ ダッシュボードを生成しました")
    print(f"📊 ファイル: {dashboard_file}")
    print(f"🌐 ブラウザで開く: file://{dashboard_file}")

    # 簡単なHTTPサーバーを起動するオプション
    print("\n💡 ローカルサーバーで確認:")
    print("   cd /root/dashboards && python3 -m http.server 8080")
    print("   ブラウザで http://localhost:8080/policy_dashboard.html を開く")

if __name__ == "__main__":
    main()



