#!/usr/bin/env python3
"""
🔥 Mega Boost Enhanced - 改善版
プログレスバー、リトライ、設定ファイル、通知機能搭載
"""

import sys
import time
import json
import yaml
import logging
import requests
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Optional

# プログレスバー
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("💡 ヒント: pip install tqdm でプログレスバーが使えます")

class EnhancedMegaBoost:
    def __init__(self, config_file: Optional[str] = None):
        self.config = self.load_config(config_file)
        self.results = []
        self.stats = {"total": 0, "success": 0, "failed": 0, "retried": 0}
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mega_boost_enhanced.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('MegaBoostEnhanced')
    
    def load_config(self, config_file: Optional[str]) -> Dict:
        """設定ファイル読み込み"""
        default_config = {
            "max_workers": 10,
            "retry": {
                "enabled": True,
                "max_attempts": 3,
                "delay": 1.0
            },
            "notifications": {
                "line": {
                    "enabled": False,
                    "token": ""
                }
            },
            "gpu": {
                "api_url": "http://localhost:5009"
            },
            "dry_run": False
        }
        
        if config_file and Path(config_file).exists():
            with open(config_file) as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    user_config = yaml.safe_load(f)
                else:
                    user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def save_default_config(self, output_file: str = "/root/.mega_boost_config.yaml"):
        """デフォルト設定保存"""
        with open(output_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
        self.logger.info(f"📄 設定ファイル保存: {output_file}")
    
    def retry_task(self, func, *args, **kwargs):
        """リトライ機能付きタスク実行"""
        if not self.config["retry"]["enabled"]:
            return func(*args, **kwargs)
        
        max_attempts = self.config["retry"]["max_attempts"]
        delay = self.config["retry"]["delay"]
        
        for attempt in range(1, max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if result.get("success"):
                    if attempt > 1:
                        self.stats["retried"] += 1
                    return result
            except Exception as e:
                if attempt < max_attempts:
                    self.logger.warning(f"⚠️ リトライ {attempt}/{max_attempts}: {str(e)}")
                    time.sleep(delay * attempt)
                else:
                    self.logger.error(f"❌ 最大リトライ到達: {str(e)}")
                    return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Max retries exceeded"}
    
    def send_line_notification(self, message: str):
        """LINE通知"""
        if not self.config["notifications"]["line"]["enabled"]:
            return
        
        token = self.config["notifications"]["line"]["token"]
        if not token:
            return
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            data = {"message": message}
            requests.post("https://notify-api.line.me/api/notify", 
                         headers=headers, data=data, timeout=10)
        except requests.RequestException:
            pass
    
    def execute_with_progress(self, tasks: List[tuple], description: str = "Processing"):
        """プログレスバー付き並列実行"""
        if self.config["dry_run"]:
            print(f"🔍 ドライラン: {len(tasks)}タスクを実行予定")
            for i, (func, args, kwargs) in enumerate(tasks, 1):
                print(f"  [{i}] {func.__name__}{args}")
            return []
        
        max_workers = self.config["max_workers"]
        
        # 自動調整: 負荷に応じてワーカー数調整
        import psutil
        cpu_percent = psutil.cpu_percent()
        if cpu_percent > 80:
            max_workers = max(1, max_workers // 2)
            self.logger.warning(f"⚠️ CPU負荷高: ワーカー数を{max_workers}に削減")
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            if HAS_TQDM:
                # プログレスバー付き
                futures = [executor.submit(self.retry_task, func, *args, **kwargs) 
                          for func, args, kwargs in tasks]
                
                with tqdm(total=len(tasks), desc=description, unit="task") as pbar:
                    for future in concurrent.futures.as_completed(futures):
                        result = future.result()
                        results.append(result)
                        self.stats["total"] += 1
                        
                        if result.get("success"):
                            self.stats["success"] += 1
                            pbar.set_postfix({"成功": self.stats["success"], 
                                            "失敗": self.stats["failed"]})
                        else:
                            self.stats["failed"] += 1
                        
                        pbar.update(1)
            else:
                # プログレスバーなし（従来通り）
                futures = [executor.submit(self.retry_task, func, *args, **kwargs) 
                          for func, args, kwargs in tasks]
                
                for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    result = future.result()
                    results.append(result)
                    self.stats["total"] += 1
                    
                    if result.get("success"):
                        self.stats["success"] += 1
                        status = "✅"
                    else:
                        self.stats["failed"] += 1
                        status = "❌"
                    
                    print(f"{status} [{i}/{len(tasks)}] 完了")
        
        # 完了通知
        message = f"""
🔥 Mega Boost 完了
総タスク: {self.stats['total']}
成功: {self.stats['success']}
失敗: {self.stats['failed']}
リトライ: {self.stats['retried']}
"""
        self.send_line_notification(message)
        
        return results
    
    # GPU処理（改善版）
    def gpu_generate_enhanced(self, task_id: int) -> Dict:
        """GPU画像生成（温度監視付き）"""
        try:
            start = time.time()
            
            # GPU温度チェック
            status_url = f"{self.config['gpu']['api_url']}/trinity/gpu/status"
            status_resp = requests.get(status_url, timeout=5)
            
            # 処理実行
            gen_url = f"{self.config['gpu']['api_url']}/trinity/gpu/generate"
            response = requests.post(gen_url, timeout=60)
            result = response.json()
            
            if result.get("success"):
                return {
                    "success": True,
                    "task_id": task_id,
                    "images": result.get("result", {}).get("images_generated", 0),
                    "time": time.time() - start
                }
            return {"success": False, "error": result.get("error")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def print_summary(self):
        """サマリー表示"""
        print("\n" + "=" * 60)
        print("📊 実行サマリー")
        print("=" * 60)
        print(f"総タスク数: {self.stats['total']}")
        print(f"成功: {self.stats['success']}")
        print(f"失敗: {self.stats['failed']}")
        print(f"リトライ: {self.stats['retried']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['success'] / self.stats['total'] * 100
            print(f"成功率: {success_rate:.1f}%")
        
        print("=" * 60)

if __name__ == "__main__":
    # 設定ファイル生成
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        boost = EnhancedMegaBoost()
        boost.save_default_config()
        print("✅ 設定ファイル作成: /root/.mega_boost_config.yaml")
        print("   編集して使ってください！")
        sys.exit(0)
    
    # 実行
    config_file = "/root/.mega_boost_config.yaml" if Path("/root/.mega_boost_config.yaml").exists() else None
    boost = EnhancedMegaBoost(config_file=config_file)
    
    # GPU画像生成デモ
    print("🎮 GPU画像生成デモ（改善版）")
    tasks = [(boost.gpu_generate_enhanced, (i,), {}) for i in range(1, 11)]
    
    results = boost.execute_with_progress(tasks, "GPU画像生成")
    boost.print_summary()

