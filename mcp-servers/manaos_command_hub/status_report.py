#!/usr/bin/env python3
"""
manaOS Command Hub ステータスレポート生成スクリプト

使い方:
    python3 status_report.py

出力をそのままチャットに貼り付けると、レミが状態を読み取れます。
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime

try:
    import psutil
except ImportError:
    print("❌ psutil がインストールされていません。")
    print("   pip install psutil を実行してください。")
    exit(1)

try:
    import requests
except ImportError:
    print("❌ requests がインストールされていません。")
    print("   pip install requests を実行してください。")
    exit(1)

COMMAND_HUB_URL = "http://localhost:9404/health"
BASE_DIR = Path("/root/manaos_command_hub")
LOG_DIR = BASE_DIR / "logs"
SYSTEMD_SERVICE = "manaos-command-hub"


def get_cpu_mem_disk():
    """CPU、メモリ、ディスクの使用状況を取得"""
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": cpu,
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent,
        },
    }


def get_health():
    """Command Hubのヘルスチェック"""
    try:
        r = requests.get(COMMAND_HUB_URL, timeout=3)
        r.raise_for_status()
        return {"reachable": True, "response": r.json()}
    except Exception as e:
        return {"reachable": False, "error": str(e)}


def get_systemd_status():
    """systemdサービスの状態を取得"""
    try:
        out = subprocess.check_output(
            ["systemctl", "is-active", SYSTEMD_SERVICE],
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
        return {"service": SYSTEMD_SERVICE, "active_state": out}
    except Exception as e:
        return {"service": SYSTEMD_SERVICE, "active_state": "unknown", "error": str(e)}


def tail_file(path: Path, lines: int = 20):
    """ファイルの最後N行を取得"""
    if not path.exists():
        return None
    try:
        out = subprocess.check_output(
            ["tail", "-n", str(lines), str(path)],
            stderr=subprocess.STDOUT,
            text=True,
        )
        return out
    except Exception:
        return None


def find_latest_daily_log():
    """最新の日次ログファイルを探す"""
    if not LOG_DIR.exists():
        return None
    candidates = sorted(LOG_DIR.glob("daily-*.log"))
    return candidates[-1] if candidates else None


def get_error_log_info():
    """エラーログの情報を取得"""
    error_logs = []
    if LOG_DIR.exists():
        for error_log in LOG_DIR.glob("error-*.log"):
            try:
                size = error_log.stat().st_size
                mtime = datetime.fromtimestamp(error_log.stat().st_mtime)
                error_logs.append({
                    "path": str(error_log),
                    "size_kb": round(size / 1024, 2),
                    "modified": mtime.isoformat(),
                    "tail": tail_file(error_log, 10)
                })
            except Exception:
                pass

    # 最新のエラーログを取得
    if error_logs:
        latest = max(error_logs, key=lambda x: x["modified"])
        return latest
    return None


def get_stats_info():
    """統計情報を取得"""
    stats_file = BASE_DIR / "stats.json"
    if stats_file.exists():
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
                return stats
        except Exception:
            return None
    return None


def main():
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "host": {
            "cpu_mem_disk": get_cpu_mem_disk(),
        },
        "command_hub": {
            "health": get_health(),
            "systemd": get_systemd_status(),
        },
        "logs": {},
        "stats": get_stats_info(),
    }

    latest = find_latest_daily_log()
    if latest:
        report["logs"]["latest_daily_log"] = {
            "path": str(latest),
            "tail": tail_file(latest, 20),
        }
    else:
        report["logs"]["latest_daily_log"] = None

    error_log = get_error_log_info()
    report["logs"]["latest_error_log"] = error_log

    # Markdownっぽく出力（ここをそのままチャットに貼ってOK）
    print("# manaOS Status Report")
    print(f"- generated_at: {report['generated_at']}")
    print("")

    h = report["command_hub"]["health"]
    s = report["command_hub"]["systemd"]
    print("## Command Hub")
    print(f"- systemd: {s.get('active_state')}")
    print(f"- health_reachable: {h.get('reachable')}")
    if h.get("reachable"):
        health_data = h.get("response", {})
        print(f"- status: {health_data.get('status', 'unknown')}")
        if "stats" in health_data:
            stats = health_data["stats"]
            if "today" in stats:
                today = stats["today"]
                print(f"- today_success: {today.get('success', 0)}")
                print(f"- today_failures: {today.get('failures', 0)}")
                print(f"- success_rate: {today.get('success_rate', 0)}%")
    else:
        print(f"- health_error: {h.get('error')}")
    print("")

    host = report["host"]["cpu_mem_disk"]
    print("## Host Resources")
    print(f"- CPU: {host['cpu_percent']} %")
    print(f"- Memory: {host['memory']['used_gb']} / {host['memory']['total_gb']} GB "
          f"({host['memory']['percent']} %)")
    print(f"- Disk: {host['disk']['used_gb']} / {host['disk']['total_gb']} GB "
          f"({host['disk']['percent']} %)")
    print("")

    # 統計情報
    if report["stats"]:
        print("## Statistics")
        total_commands = report["stats"].get("total_commands", 0)
        total_success = report["stats"].get("total_success", 0)
        total_failures = report["stats"].get("total_failures", 0)
        print(f"- total_commands: {total_commands}")
        print(f"- total_success: {total_success}")
        print(f"- total_failures: {total_failures}")
        if total_commands > 0:
            overall_rate = round((total_success / total_commands) * 100, 2)
            print(f"- overall_success_rate: {overall_rate}%")
        print("")

    print("## Latest Daily Log")
    if report["logs"]["latest_daily_log"] is None:
        print("- no daily log found")
    else:
        info = report["logs"]["latest_daily_log"]
        print(f"- path: {info['path']}")
        print("```")
        if info["tail"]:
            print(info["tail"].rstrip())
        else:
            print("(tail error)")
        print("```")
    print("")

    # エラーログ
    if error_log:
        print("## Latest Error Log")
        print(f"- path: {error_log['path']}")
        print(f"- size: {error_log['size_kb']} KB")
        print(f"- modified: {error_log['modified']}")
        if error_log.get("tail"):
            print("```")
            print(error_log["tail"].rstrip())
            print("```")
        print("")

    # 推奨事項
    print("## Recommendations")
    recommendations = []

    if not h.get("reachable"):
        recommendations.append("⚠️ Command Hubが応答していません。systemctl status で確認してください。")

    if s.get("active_state") != "active":
        recommendations.append("⚠️ systemdサービスがactiveではありません。")

    if host["memory"]["percent"] > 90:
        recommendations.append("⚠️ メモリ使用率が90%を超えています。")

    if host["disk"]["percent"] > 90:
        recommendations.append("⚠️ ディスク使用率が90%を超えています。")

    if error_log and error_log["size_kb"] > 100:
        recommendations.append("⚠️ エラーログが大きくなっています。確認してください。")

    if not recommendations:
        recommendations.append("✅ 特に問題は見つかりませんでした。")

    for rec in recommendations:
        print(f"- {rec}")
    print("")

    # JSON欲しいとき用（コメント外せば生JSONも見れる）
    # print()
    # print("## Raw JSON")
    # print("```json")
    # print(json.dumps(report, ensure_ascii=False, indent=2))
    # print("```")


if __name__ == "__main__":
    main()








