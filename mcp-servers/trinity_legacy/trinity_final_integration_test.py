#!/usr/bin/env python3
"""
🧪 Trinity Final Integration Test
全システム統合テスト - 最終確認

すべてのシステムが完璧に連携しているか確認！
"""

import asyncio
import sys
import requests

# カラー
class C:
    G = '\033[92m'  # Green
    R = '\033[91m'  # Red
    Y = '\033[93m'  # Yellow
    B = '\033[94m'  # Blue
    M = '\033[95m'  # Magenta
    E = '\033[0m'   # End

def print_header(text):
    print(f"\n{C.M}{'='*60}{C.E}")
    print(f"{C.M}{text:^60}{C.E}")
    print(f"{C.M}{'='*60}{C.E}\n")

def print_test(name, status, message=""):
    symbol = "✅" if status else "❌"
    color = C.G if status else C.R
    print(f"{symbol} {color}{name:40}{C.E} {message}")

async def main():
    results = {"passed": 0, "failed": 0, "skipped": 0}
    
    print_header("🚀 TRINITY FINAL INTEGRATION TEST 🚀")
    
    # ============================================================
    # Test 1: Core Systems
    # ============================================================
    print(f"{C.B}Test Suite 1: Core Systems{C.E}\n")
    
    # Obsidian
    try:
        from trinity_obsidian_connector import obsidian
        task = obsidian.add_task("最終統合テスト", priority="高")
        assert task.exists()
        print_test("Obsidian Connector", True, "→ Task created")
        results["passed"] += 1
    except Exception as e:
        print_test("Obsidian Connector", False, str(e))
        results["failed"] += 1
    
    # Notification
    try:
        from trinity_notification_system import notification_system, NotificationPriority
        result = await notification_system.send_notification(
            "統合テスト", "全システムチェック中", NotificationPriority.NORMAL
        )
        print_test("Notification System", result['success'], "→ Ntfy OK")
        results["passed"] += 1
    except Exception as e:
        print_test("Notification System", False, str(e))
        results["failed"] += 1
    
    # Voice System
    try:
        from trinity_voice_system import TrinityVoiceSystem
        voice = TrinityVoiceSystem()
        stats = voice.get_stats()
        print_test("Voice System", True, f"→ Model: {stats['model']}")
        results["passed"] += 1
    except Exception as e:
        print_test("Voice System", False, str(e))
        results["failed"] += 1
    
    # Master System
    try:
        from trinity_master_system import trinity_master
        result = await trinity_master.process_command("ステータス")
        print_test("Master System", result['success'], "→ Command OK")
        results["passed"] += 1
    except Exception as e:
        print_test("Master System", False, str(e))
        results["failed"] += 1
    
    print()
    
    # ============================================================
    # Test 2: New Systems
    # ============================================================
    print(f"{C.B}Test Suite 2: New Systems{C.E}\n")
    
    # GDrive Backup
    try:
        from trinity_gdrive_backup import TrinityGDriveBackup
        backup = TrinityGDriveBackup()
        stats = backup.get_stats()
        print_test("GDrive Backup", True, f"→ {stats['stored_backups']} backups")
        results["passed"] += 1
    except Exception as e:
        print_test("GDrive Backup", False, str(e))
        results["failed"] += 1
    
    # Health Monitor
    try:
        from trinity_health_monitor import TrinityHealthMonitor
        monitor = TrinityHealthMonitor()
        health = await monitor.check_all_services()
        print_test("Health Monitor", True, f"→ {health['health_percentage']:.0f}% health")
        results["passed"] += 1
    except Exception as e:
        print_test("Health Monitor", False, str(e))
        results["failed"] += 1
    
    # Smart Scheduler
    try:
        from trinity_smart_scheduler import TrinitySmartScheduler
        scheduler = TrinitySmartScheduler()
        events = await scheduler.check_upcoming_events()
        print_test("Smart Scheduler", True, f"→ {len(events)} events")
        results["passed"] += 1
    except Exception as e:
        print_test("Smart Scheduler", False, str(e))
        results["failed"] += 1
    
    # Slack Integration
    try:
        from trinity_slack_integration import TrinitySlackIntegration
        slack = TrinitySlackIntegration()
        stats = slack.get_stats()
        print_test("Slack Integration", True, "→ Ready")
        results["passed"] += 1
    except Exception as e:
        print_test("Slack Integration", False, str(e))
        results["failed"] += 1
    
    print()
    
    # ============================================================
    # Test 3: API Endpoints
    # ============================================================
    print(f"{C.B}Test Suite 3: API Endpoints{C.E}\n")
    
    api_tests = [
        ("GET /api/status", "http://localhost:5555/api/status"),
        ("POST /api/notification/test", "http://localhost:5555/api/notification/test")
    ]
    
    for test_name, url in api_tests:
        try:
            if "POST" in test_name:
                response = requests.post(url, timeout=5)
            else:
                response = requests.get(url, timeout=5)
            
            success = response.status_code == 200
            print_test(test_name, success, f"→ {response.status_code}")
            if success:
                results["passed"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            print_test(test_name, False, str(e))
            results["failed"] += 1
    
    print()
    
    # ============================================================
    # Test 4: File Integrity
    # ============================================================
    print(f"{C.B}Test Suite 4: File Integrity{C.E}\n")
    
    import os
    critical_files = [
        "/root/trinity_mobile_server.py",
        "/root/trinity_master_system.py",
        "/root/trinity_telegram_bot.py",
        "/root/trinity_notification_system.py",
        "/root/trinity_voice_system.py",
        "/root/trinity_obsidian_connector.py",
        "/root/trinity_gdrive_backup.py",
        "/root/trinity_health_monitor.py",
        "/root/trinity_smart_scheduler.py",
        "/root/trinity_slack_integration.py",
        "/root/trinity_ultimate_launcher.py",
        "/root/trinity_mobile_pwa.html",
        "/root/trinity_realtime_dashboard.html"
    ]
    
    missing = [f for f in critical_files if not os.path.exists(f)]
    
    if not missing:
        print_test("All Files Exist", True, f"→ {len(critical_files)} files")
        results["passed"] += 1
    else:
        print_test("All Files Exist", False, f"→ Missing: {len(missing)}")
        results["failed"] += 1
    
    print()
    
    # ============================================================
    # Final Results
    # ============================================================
    print_header("📊 FINAL RESULTS")
    
    total = results['passed'] + results['failed'] + results['skipped']
    success_rate = (results['passed'] / total * 100) if total > 0 else 0
    
    print(f"{C.G}✅ Passed:  {results['passed']:2d}{C.E}")
    print(f"{C.R}❌ Failed:  {results['failed']:2d}{C.E}")
    print(f"{C.Y}⏭️  Skipped: {results['skipped']:2d}{C.E}")
    print(f"\n📈 Success Rate: {C.G if success_rate == 100 else C.Y}{success_rate:.1f}%{C.E}")
    
    print()
    
    if results['failed'] == 0:
        print(f"{C.G}╔══════════════════════════════════════════════════╗{C.E}")
        print(f"{C.G}║  🎉 ALL TESTS PASSED! TRINITY IS PERFECT! 🎉  ║{C.E}")
        print(f"{C.G}╚══════════════════════════════════════════════════╝{C.E}\n")
        return 0
    else:
        print(f"{C.Y}⚠️  Some tests failed. Check details above.{C.E}\n")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

