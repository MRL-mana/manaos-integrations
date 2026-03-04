#!/usr/bin/env python3
"""
全問題修正実行スクリプト
シェルが使えない場合でもPythonで直接実行
"""

import subprocess
import os
import sys
import time
from datetime import datetime

def run_command(cmd, description):
    """コマンドを実行して結果を返す"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"実行コマンド: {cmd}")
        print(f"終了コード: {result.returncode}")
        
        if result.stdout:
            print(f"\n出力:\n{result.stdout}")
        
        if result.stderr:
            print(f"\nエラー出力:\n{result.stderr}")
        
        return result.returncode == 0
    
    except subprocess.TimeoutExpired:
        print("⚠️ タイムアウト")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    print("🚀 全問題修正実行開始")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = {}
    
    # 1. スクリプトに実行権限付与
    print("\n📝 ステップ1: スクリプトに実行権限を付与")
    scripts = [
        "/root/disk_usage_monitor.sh",
        "/root/check_duplicate_processes.sh",
        "/root/cleanup_zombie_processes.sh",
        "/root/fix_x280_ssh_permissions.sh"
    ]
    
    for script in scripts:
        if os.path.exists(script):
            os.chmod(script, 0o755)
            print(f"✅ {script} - 実行権限付与")
        else:
            print(f"⚠️ {script} - ファイルが見つかりません")
    
    # 2. ディスク使用量チェック
    print("\n💾 ステップ2: ディスク使用量確認")
    results['disk_check'] = run_command(
        "df -h / /mnt/storage500 2>/dev/null",
        "ディスク使用状況の確認"
    )
    
    # 3. ゾンビプロセスチェック
    print("\n🧹 ステップ3: ゾンビプロセス検出")
    results['zombie_check'] = run_command(
        "ps aux | grep defunct | grep -v grep || echo 'ゾンビプロセスなし'",
        "ゾンビプロセスの検出"
    )
    
    # 4. ゾンビプロセスクリーンアップ
    print("\n🧹 ステップ4: ゾンビプロセスクリーンアップ")
    zombie_pids = subprocess.run(
        "ps aux | grep defunct | grep -v grep | awk '{print $2}'",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if zombie_pids.stdout.strip():
        for pid in zombie_pids.stdout.strip().split('\n'):
            if pid:
                # 親プロセスを取得
                ppid_result = subprocess.run(
                    f"ps -o ppid= -p {pid} 2>/dev/null",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                ppid = ppid_result.stdout.strip()
                
                if ppid:
                    print(f"ゾンビPID: {pid}, 親PID: {ppid}")
                    # HUPシグナル送信
                    subprocess.run(f"kill -HUP {ppid} 2>/dev/null", shell=True)
                    print(f"  → 親プロセス {ppid} にHUPシグナル送信")
                    time.sleep(1)
        results['zombie_cleanup'] = True
    else:
        print("✅ ゾンビプロセスは見つかりませんでした")
        results['zombie_cleanup'] = True
    
    # 5. プロセス重複チェック
    print("\n🔍 ステップ5: プロセス重複チェック")
    results['process_check'] = run_command(
        "ps aux | grep python | grep -v grep | awk '{print $11, $12}' | sort | uniq -c | sort -rn | head -10",
        "重複Pythonプロセスの検出"
    )
    
    # 6. Dockerコンテナ状態確認
    print("\n🐳 ステップ6: Dockerコンテナ状態確認")
    results['docker_check'] = run_command(
        "docker ps --format 'table {{.Names}}\t{{.Status}}'",
        "Dockerコンテナの状態"
    )
    
    # 7. ManaOS v3サービス状態確認
    print("\n🤖 ステップ7: ManaOS v3サービス確認")
    manaos_services = [
        ("mana-orchestrator", 9200),
        ("mana-intention", 9201),
        ("mana-policy", 9202),
        ("mana-actuator", 9203),
        ("mana-ingestor", 9204),
        ("mana-insight", 9205)
    ]
    
    for service, port in manaos_services:
        result = subprocess.run(
            f"docker ps --filter name={service} --format '{{{{.Status}}}}'",
            shell=True,
            capture_output=True,
            text=True
        )
        status = result.stdout.strip()
        if "Up" in status:
            print(f"✅ {service} (port {port}): 稼働中")
        else:
            print(f"⚠️ {service} (port {port}): 停止中")
    
    # 8. systemdサービス状態確認
    print("\n⚙️ ステップ8: systemdサービス確認")
    results['systemd_check'] = run_command(
        "systemctl --failed --no-pager",
        "失敗したsystemdサービスの確認"
    )
    
    # 9. ログファイルサイズ確認
    print("\n📊 ステップ9: ログファイルサイズ確認")
    results['log_check'] = run_command(
        "du -sh /root/logs /var/log 2>/dev/null",
        "ログファイルサイズの確認"
    )
    
    # 10. メモリ使用状況確認
    print("\n💻 ステップ10: メモリ使用状況確認")
    results['memory_check'] = run_command(
        "free -h",
        "メモリ使用状況の確認"
    )
    
    # 結果サマリー
    print("\n" + "="*60)
    print("📊 実行結果サマリー")
    print("="*60)
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for task, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"{status} - {task}")
    
    print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    # cron設定の推奨
    print("\n" + "="*60)
    print("📅 自動化の推奨設定（cron）")
    print("="*60)
    print("""
以下をcrontabに追加してください（crontab -e）:

# ディスク監視（毎日3回）
0 9,15,21 * * * /root/disk_usage_monitor.sh >> /root/logs/disk_monitor.log 2>&1

# プロセスチェック（毎週月曜）
0 9 * * 1 /root/check_duplicate_processes.sh >> /root/logs/process_check.log 2>&1

# ゾンビクリーンアップ（毎週日曜）
0 22 * * 0 /root/cleanup_zombie_processes.sh >> /root/logs/zombie_cleanup.log 2>&1
""")
    
    print("\n✅ 全問題修正実行完了！")
    print(f"完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return success_count == total_count

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




