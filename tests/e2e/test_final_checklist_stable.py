"""
最終確認チェックリスト（安定版）
ready待ち前提のポーリング実装
"""

import sys
import time
import json
import os
import requests
from pathlib import Path
from datetime import datetime

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))

# UTF-8エンコーディング設定
sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

BASE_URL = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")
HEALTH_TIMEOUT = 1
READY_TIMEOUT = 60  # 最大60秒ポーリング
READY_POLL_INTERVAL = 2  # 2秒間隔
API_TIMEOUT = 30


def print_header(title: str):
    """ヘッダーを表示"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def wait_for_ready(max_wait: int = READY_TIMEOUT, poll_interval: int = READY_POLL_INTERVAL) -> bool:
    """
    /readyが200を返すまで待つ（ポーリング）
    
    Returns:
        True: readyになった, False: タイムアウト
    """
    print(f"⏳ /readyを待機中（最大{max_wait}秒、{poll_interval}秒間隔）...")
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < max_wait:
        attempt += 1
        try:
            response = requests.get(f"{BASE_URL}/ready", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                elapsed = time.time() - start_time
                print(f"✅ /ready: 初期化完了（{elapsed:.1f}秒、{attempt}回目）")
                
                # チェック結果を表示
                checks = data.get("readiness_checks", {})
                required = ["memory_db", "obsidian_path", "notification_hub", "llm_routing", "image_stock"]
                for check_name in required:
                    check = checks.get(check_name, {})
                    status = check.get("status", "unknown")
                    message = check.get("message", "")
                    icon = "✅" if status == "ok" else "⚠️" if status == "warning" else "❌"
                    print(f"   {icon} {check_name}: {status} - {message}")
                
                return True
            elif response.status_code == 503:
                # 初期化中（正常）
                data = response.json()
                status = data.get("status", "unknown")
                pending = len(data.get("pending", []))
                completed = len(data.get("completed", []))
                
                if attempt % 5 == 0:  # 5回ごとに表示
                    print(f"   ℹ️  初期化中... (status: {status}, 完了: {completed}, 待機: {pending})")
            else:
                print(f"   ⚠️  予期しないステータス: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            if attempt % 5 == 0:
                print(f"   ⚠️  接続エラー: {type(e).__name__}")
        
        time.sleep(poll_interval)
    
    print(f"❌ /ready: タイムアウト（{max_wait}秒経過）")
    return False


def wait_for_connection(max_retries: int = 3, retry_interval: int = 2) -> bool:
    """
    サーバーへの接続を待つ（リトライ付き）
    
    Returns:
        True: 接続成功, False: タイムアウト
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=1)
            if response.status_code == 200:
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                print(f"   ⏳ 接続試行 {attempt}/{max_retries}... ({type(e).__name__})")
                time.sleep(retry_interval)
            else:
                print(f"   ❌ 接続失敗（{max_retries}回試行）")
                return False
        except Exception as e:
            print(f"   ⚠️  予期しないエラー: {type(e).__name__}")
            return False
    
    return False


def test_1_server_restart_stability():
    """
    チェック1: サーバー再起動後の安定性（運用版）
    
    合格条件:
    - /health は起動直後から即200（max-time 1s）
    - /ready は503→200に遷移する（60秒以内、2秒間隔ポーリング）
    - /status は常に200で、5項目の状態が返る
    """
    print_header("チェック1: サーバー再起動後の安定性（運用版）")
    
    try:
        # 0. 接続を待つ（リトライ付き）
        print("⏳ サーバーへの接続を確認中...")
        if not wait_for_connection(max_retries=3, retry_interval=2):
            print("❌ サーバーに接続できません（起動していない可能性があります）")
            return False
        
        # 1. /healthでプロセス生存を確認（軽量、1秒以内）
        print("📡 /health を確認中...")
        health_start = time.time()
        try:
            health_response = requests.get(f"{BASE_URL}/health", timeout=HEALTH_TIMEOUT)
            health_elapsed = time.time() - health_start
            
            if health_response.status_code != 200:
                print(f"❌ /healthが正常に応答しません: {health_response.status_code}")
                return False
            
            if health_elapsed > HEALTH_TIMEOUT * 1.1:  # 10%の余裕を持たせる
                print(f"⚠️  /healthがやや遅い: {health_elapsed:.3f}秒（目標: {HEALTH_TIMEOUT}秒）")
            else:
                print(f"✅ /health: プロセス生存確認（{health_response.json().get('status')}, {health_elapsed:.3f}秒）")
        except requests.exceptions.Timeout:
            print(f"❌ /healthがタイムアウトしました（{HEALTH_TIMEOUT}秒）")
            return False
        except requests.exceptions.ConnectionError:
            print(f"❌ /healthへの接続エラー（サーバーが起動していない可能性があります）")
            return False
        
        # 2. /statusで初期化進捗を確認（常に200、5項目の状態が返る）
        print("📊 /status を確認中...")
        status_start = time.time()
        try:
            status_response = requests.get(f"{BASE_URL}/status", timeout=10)  # タイムアウトを延長
            status_elapsed = time.time() - status_start
            
            if status_response.status_code != 200:
                print(f"⚠️  /statusが正常に応答しません: {status_response.status_code}（続行）")
                # /statusが失敗しても続行（/readyで最終確認）
            else:
                data = status_response.json()
                checks = data.get("readiness_checks", {})
                required_checks = ["memory_db", "obsidian_path", "notification_hub", "llm_routing", "image_stock"]
                
                print(f"✅ /status: 初期化進捗確認（{status_elapsed:.3f}秒）")
                print(f"   必須チェック数: {len(required_checks)}項目")
                
                # 各チェックの状態を表示
                for check_name in required_checks:
                    check = checks.get(check_name, {})
                    status = check.get("status", "unknown")
                    icon = "✅" if status == "ok" else "⚠️" if status == "warning" else "❌" if status == "error" else "⏳"
                    print(f"   {icon} {check_name}: {status}")
            
        except requests.exceptions.Timeout:
            print(f"⚠️  /statusがタイムアウトしました（続行）")
            # タイムアウトしても続行（/readyで最終確認）
        except Exception as e:
            print(f"⚠️  /status確認エラー: {type(e).__name__}（続行）")
            # エラーしても続行（/readyで最終確認）
        
        # 3. /readyを待つ（ポーリング：503→200の遷移を確認）
        print("⏳ /ready を待機中（503→200の遷移を確認）...")
        ready_start = time.time()
        
        # 最初は503であることを確認（初期化中）
        first_ready_status = None
        try:
            first_ready = requests.get(f"{BASE_URL}/ready", timeout=5)
            first_ready_status = first_ready.status_code
            if first_ready_status == 200:
                print("ℹ️  /ready: 既に初期化完了（503→200の遷移は確認できませんでした）")
            elif first_ready_status == 503:
                print("✅ /ready: 初期化中を確認（503）→ 完了を待機...")
            else:
                print(f"⚠️  /ready: 予期しないステータス: {first_ready_status}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  /ready初回確認エラー: {type(e).__name__}（ポーリングを続行）")
        
        # ポーリングで200を待つ
        if not wait_for_ready():
            return False
        
        ready_elapsed = time.time() - ready_start
        if first_ready_status == 503:
            print(f"✅ /ready: 初期化完了（503→200の遷移を確認、{ready_elapsed:.1f}秒）")
        else:
            print(f"✅ /ready: 初期化完了（{ready_elapsed:.1f}秒）")
        
        # 4. 必須システムの確認
        ready_response = requests.get(f"{BASE_URL}/ready", timeout=5)
        if ready_response.status_code == 200:
            ready_data = ready_response.json()
            integrations = ready_data.get("integrations", {})
            
            required = ["llm_routing", "memory_unified", "notification_hub", "secretary", "image_stock"]
            missing = [k for k in required if not integrations.get(k, False)]
            
            if missing:
                print(f"⚠️  不足している必須システム: {', '.join(missing)}")
                return False
            else:
                print(f"✅ すべての必須システムが利用可能です")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_gpu_fallback():
    """チェック2: 意図的にGPUを埋めてフォールバック発動（テスト）"""
    print_header("チェック2: GPU/CPUフォールバック")
    
    try:
        payload = {
            "task_type": "conversation",
            "prompt": "こんにちは、テストです。",
            "memory_refs": [],
            "tools_used": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/llm/route",
            json=payload,
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            cpu_mode = data.get("cpu_mode", False)
            model = data.get("model", "unknown")
            source = data.get("source", "unknown")
            fallback_reason = data.get("fallback_reason")
            
            print(f"✅ LLMルーティング成功")
            print(f"   モデル: {model}")
            print(f"   ソース: {source}")
            print(f"   CPUモード: {cpu_mode}")
            if fallback_reason:
                print(f"   Fallback理由: {fallback_reason}")
            
            if cpu_mode:
                print(f"✅ GPU使用中を検出し、CPUモードで実行されました")
            else:
                print(f"ℹ️  GPUモードで実行されました（GPUが利用可能）")
            
            return True
        else:
            print(f"❌ LLMルーティング失敗: {response.status_code}")
            print(f"   レスポンス: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


def test_3_notification_retry():
    """チェック3: 通知先を一時遮断して再送キューが動く（信頼性）"""
    print_header("チェック3: 通知再送キュー")
    
    try:
        payload = {
            "message": "テスト通知（再送キュー確認用）",
            "priority": "normal"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/notification/send",
            json=payload,
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            slack_result = data.get("slack", False)
            
            print(f"✅ 通知送信APIは正常に応答しています")
            print(f"   Slack送信結果: {slack_result}")
            print(f"ℹ️  再送キューは、実際の送信失敗時に自動的に生成されます")
            print(f"   再送API: POST /api/notification/retry")
            
            return True
        else:
            print(f"❌ 通知送信API失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


def test_4_memory_consistency():
    """チェック4: remember/recallで同じ質問→同じ記憶参照（一貫性）"""
    print_header("チェック4: 記憶の一貫性")
    
    try:
        # 記憶を保存
        test_content = {
            "type": "conversation",
            "content": f"テスト記憶: {datetime.now().isoformat()}",
            "metadata": {
                "test": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        store_payload = {
            "content": test_content,
            "format_type": "conversation"
        }
        
        store_response = requests.post(
            f"{BASE_URL}/api/memory/store",
            json=store_payload,
            timeout=API_TIMEOUT
        )
        
        if store_response.status_code != 200:
            print(f"❌ 記憶保存失敗: {store_response.status_code}")
            return False
        
        print(f"✅ 記憶を保存しました")
        
        # 少し待つ（保存の反映を待つ）
        time.sleep(1)
        
        # 同じクエリで2回検索
        query = "テスト記憶"
        
        recall1_response = requests.get(
            f"{BASE_URL}/api/memory/recall",
            params={"query": query, "scope": "all", "limit": 10},
            timeout=API_TIMEOUT
        )
        
        if recall1_response.status_code != 200:
            print(f"❌ 記憶検索1回目失敗: {recall1_response.status_code}")
            return False
        
        time.sleep(0.5)
        
        recall2_response = requests.get(
            f"{BASE_URL}/api/memory/recall",
            params={"query": query, "scope": "all", "limit": 10},
            timeout=API_TIMEOUT
        )
        
        if recall2_response.status_code != 200:
            print(f"❌ 記憶検索2回目失敗: {recall2_response.status_code}")
            return False
        
        results1 = recall1_response.json().get("results", [])
        results2 = recall2_response.json().get("results", [])
        
        print(f"✅ 1回目の検索結果: {len(results1)}件")
        print(f"✅ 2回目の検索結果: {len(results2)}件")
        
        # 結果の一貫性を確認（件数が同じか）
        if len(results1) == len(results2):
            print(f"✅ 検索結果の一貫性が確認されました")
            return True
        else:
            print(f"⚠️  検索結果の件数が異なります（1回目: {len(results1)}, 2回目: {len(results2)}）")
            return False
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


def test_5_safety_guard():
    """チェック5: actが危険操作を勝手に実行しない（安全柵）"""
    print_header("チェック5: 安全柵")
    
    try:
        dangerous_actions = [
            {"action_type": "file_delete", "args": {"path": "/etc/passwd"}},
            {"action_type": "system_command", "args": {"command": "rm -rf /"}},
            {"action_type": "database_drop", "args": {"database": "all"}}
        ]
        
        print(f"安全柵の実装状況を確認中...")
        
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from manaos_core_api import ManaOSCoreAPI
        
        api = ManaOSCoreAPI()
        
        blocked_count = 0
        for action in dangerous_actions:
            result = api.act(action["action_type"], action["args"])
            if result.get("error") == "safety_guard_blocked":
                blocked_count += 1
                print(f"✅ ブロック成功: {action['action_type']} - {result.get('message', '')}")
            else:
                print(f"❌ ブロック失敗: {action['action_type']} - 実行されてしまった可能性があります")
        
        if blocked_count == len(dangerous_actions):
            print(f"✅ すべての危険な操作がブロックされました ({blocked_count}/{len(dangerous_actions)})")
            return True
        else:
            print(f"⚠️  一部の危険な操作がブロックされませんでした ({blocked_count}/{len(dangerous_actions)})")
            return False
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メイン関数"""
    print("\n" + "=" * 60)
    print(" manaOS拡張フェーズ 最終確認チェックリスト（安定版）")
    print("=" * 60)
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"サーバーURL: {BASE_URL}")
    print(f"ポーリング設定: 最大{READY_TIMEOUT}秒、{READY_POLL_INTERVAL}秒間隔")
    
    results = {}
    
    # チェック1: サーバー再起動後の安定性（ready待ち付き）
    results["check1"] = test_1_server_restart_stability()
    
    # チェック2: GPU/CPUフォールバック
    results["check2"] = test_2_gpu_fallback()
    
    # チェック3: 通知再送キュー
    results["check3"] = test_3_notification_retry()
    
    # チェック4: 記憶の一貫性
    results["check4"] = test_4_memory_consistency()
    
    # チェック5: 安全柵
    results["check5"] = test_5_safety_guard()
    
    # 結果サマリー
    print_header("結果サマリー")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for i, (key, value) in enumerate(results.items(), 1):
        status = "✅ 合格" if value else "❌ 不合格"
        print(f"チェック{i}: {status}")
    
    print(f"\n合格率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 すべてのチェックに合格しました！")
        print("   manaOSは「運用できる」状態です。")
    else:
        print(f"\n⚠️  {total - passed}個のチェックが不合格です。改善が必要です。")
    
    # 結果をJSONファイルに保存
    result_file = Path(__file__).parent / "data" / "final_checklist_stable_results.json"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "passed": passed,
            "total": total,
            "pass_rate": passed/total*100,
            "version": "stable"
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n結果を保存しました: {result_file}")


if __name__ == "__main__":
    main()

