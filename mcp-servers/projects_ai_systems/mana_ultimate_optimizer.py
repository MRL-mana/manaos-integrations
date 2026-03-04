#!/usr/bin/env python3
"""
Mana Ultimate Optimizer
全システムを統合して自動最適化する究極のツール
"""

import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import psutil

class ManaUltimateOptimizer:
    """ManaOS統合最適化システム"""
    
    def __init__(self):
        self.root = Path("/root")
        self.logs_dir = Path("/root/logs/optimizer")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            "start_time": datetime.now(),
            "optimizations": [],
            "improvements": {}
        }
    
    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        
        with open(self.logs_dir / "optimizer.log", "a") as f:
            f.write(log_msg + "\n")
    
    def run_command(self, command: List[str], description: str) -> Dict[str, Any]:
        """コマンド実行"""
        self.log(f"実行中: {description}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            success = result.returncode == 0
            
            self.stats["optimizations"].append({
                "description": description,
                "success": success,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            self.log(f"エラー: {e}", "ERROR")
            return {"success": False, "error": str(e)}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """システム統計取得"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "process_count": len(psutil.pids()),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
    
    def optimize_backups(self) -> Dict[str, Any]:
        """バックアップ最適化"""
        self.log("=" * 60)
        self.log("🔄 バックアップ最適化開始")
        self.log("=" * 60)
        
        before_size = self._get_dir_size("/root/backups*")
        
        # スマートバックアップ実行
        result1 = self.run_command(
            ["/root/smart_backup.sh"],
            "スマートバックアップ実行"
        )
        
        # 分割バックアップ実行
        result2 = self.run_command(
            ["/root/separate_backups.sh"],
            "分割バックアップ実行"
        )
        
        # クリーンアップ実行
        result3 = self.run_command(
            ["/root/cleanup_all_backups.sh"],
            "バックアップクリーンアップ実行"
        )
        
        after_size = self._get_dir_size("/root/backups*")
        saved = before_size - after_size
        
        self.stats["improvements"]["backup"] = {
            "before_mb": before_size,
            "after_mb": after_size,
            "saved_mb": saved,
            "reduction_percent": (saved / before_size * 100) if before_size > 0 else 0
        }
        
        self.log(f"✅ バックアップ最適化完了: {saved:.1f}MB削減")
        
        return {
            "success": all([result1["success"], result2["success"], result3["success"]]),
            "saved_mb": saved
        }
    
    def optimize_logs(self) -> Dict[str, Any]:
        """ログ最適化"""
        self.log("=" * 60)
        self.log("📋 ログ最適化開始")
        self.log("=" * 60)
        
        before_size = self._get_dir_size("/root/logs")
        
        # ログ管理システム実行
        result = self.run_command(
            ["/root/log_management_system.sh"],
            "ログ管理システム実行"
        )
        
        after_size = self._get_dir_size("/root/logs")
        saved = before_size - after_size
        
        self.stats["improvements"]["logs"] = {
            "before_mb": before_size,
            "after_mb": after_size,
            "saved_mb": saved
        }
        
        self.log(f"✅ ログ最適化完了: {saved:.1f}MB削減")
        
        return {"success": result["success"], "saved_mb": saved}
    
    def optimize_documents(self) -> Dict[str, Any]:
        """ドキュメント最適化"""
        self.log("=" * 60)
        self.log("📚 ドキュメント最適化開始")
        self.log("=" * 60)
        
        before_count = self._count_files("/root", "*.md")
        
        # ドキュメント統合実行
        result = self.run_command(
            ["/root/document_consolidation.sh"],
            "ドキュメント統合実行"
        )
        
        after_count = self._count_files("/root", "*.md")
        reduced = before_count - after_count
        
        self.stats["improvements"]["documents"] = {
            "before_count": before_count,
            "after_count": after_count,
            "reduced_count": reduced
        }
        
        self.log(f"✅ ドキュメント最適化完了: {reduced}ファイル削減")
        
        return {"success": result["success"], "reduced": reduced}
    
    def run_security_audit(self) -> Dict[str, Any]:
        """セキュリティ監査"""
        self.log("=" * 60)
        self.log("🔐 セキュリティ監査開始")
        self.log("=" * 60)
        
        result = self.run_command(
            ["python3", "/root/security_monitor.py"],
            "セキュリティ監査実行"
        )
        
        self.log("✅ セキュリティ監査完了")
        
        return {"success": result["success"]}
    
    def optimize_system_resources(self) -> Dict[str, Any]:
        """システムリソース最適化"""
        self.log("=" * 60)
        self.log("⚡ システムリソース最適化開始")
        self.log("=" * 60)
        
        improvements = []
        
        # 1. 不要なキャッシュクリア
        self.log("キャッシュクリア中...")
        subprocess.run(["sync"], check=False)
        subprocess.run(
            ["sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"],
            check=False,
            stderr=subprocess.DEVNULL
        )
        improvements.append("キャッシュクリア")
        
        # 2. 孤立したPIDファイル削除
        self.log("孤立PIDファイルクリア中...")
        pid_count = 0
        for pid_file in Path("/root").rglob("*.pid"):
            try:
                with open(pid_file) as f:
                    pid = int(f.read().strip())
                if not psutil.pid_exists(pid):
                    pid_file.unlink()
                    pid_count += 1
            except IOError:
                pass
        improvements.append(f"{pid_count}個のPIDファイル削除")
        
        # 3. 一時ファイルクリア
        self.log("一時ファイルクリア中...")
        tmp_count = 0
        for tmp_file in Path("/root").rglob("*.tmp"):
            try:
                tmp_file.unlink()
                tmp_count += 1
            except IOError:
                pass
        improvements.append(f"{tmp_count}個の一時ファイル削除")
        
        # 4. Pythonキャッシュクリア
        self.log("Pythonキャッシュクリア中...")
        pyc_count = 0
        for pyc_file in Path("/root").rglob("*.pyc"):
            try:
                pyc_file.unlink()
                pyc_count += 1
            except IOError:
                pass
        for pycache in Path("/root").rglob("__pycache__"):
            try:
                subprocess.run(["rm", "-rf", str(pycache)], check=False)
                pyc_count += 1
            except IOError:
                pass
        improvements.append(f"{pyc_count}個のPythonキャッシュ削除")
        
        self.stats["improvements"]["system"] = improvements
        
        self.log(f"✅ システムリソース最適化完了: {len(improvements)}項目")
        
        return {"success": True, "improvements": improvements}
    
    def create_unified_dashboard(self) -> Dict[str, Any]:
        """統合ダッシュボード作成"""
        self.log("=" * 60)
        self.log("📊 統合ダッシュボード作成開始")
        self.log("=" * 60)
        
        dashboard_html = self.root / "mana_ultimate_dashboard.html"
        
        system_stats = self.get_system_stats()
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Ultimate Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{
            font-size: 3em;
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .stat-card h3 {{ margin-bottom: 15px; font-size: 1.2em; }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{ opacity: 0.8; font-size: 0.9em; }}
        .progress-bar {{
            width: 100%;
            height: 10px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            overflow: hidden;
            margin-top: 10px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #00f260, #0575e6);
            transition: width 0.3s ease;
        }}
        .tools-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 30px;
        }}
        .tool-button {{
            background: rgba(255,255,255,0.15);
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            color: white;
            display: block;
        }}
        .tool-button:hover {{
            background: rgba(255,255,255,0.25);
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }}
        .timestamp {{
            text-align: center;
            margin-top: 30px;
            opacity: 0.7;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Mana Ultimate Dashboard</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>💻 CPU使用率</h3>
                <div class="stat-value">{system_stats['cpu_percent']:.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {system_stats['cpu_percent']}%"></div>
                </div>
            </div>
            
            <div class="stat-card">
                <h3>🧠 メモリ使用率</h3>
                <div class="stat-value">{system_stats['memory_percent']:.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {system_stats['memory_percent']}%"></div>
                </div>
            </div>
            
            <div class="stat-card">
                <h3>💾 ディスク使用率</h3>
                <div class="stat-value">{system_stats['disk_percent']:.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {system_stats['disk_percent']}%"></div>
                </div>
            </div>
            
            <div class="stat-card">
                <h3>⚙️ 稼働プロセス数</h3>
                <div class="stat-value">{system_stats['process_count']}</div>
                <div class="stat-label">プロセス</div>
            </div>
        </div>
        
        <h2 style="margin: 30px 0 20px 0; text-align: center;">🛠️ 最適化ツール</h2>
        
        <div class="tools-grid">
            <a href="#" class="tool-button" onclick="alert('バックアップ最適化を実行します')">
                💾 バックアップ最適化
            </a>
            <a href="#" class="tool-button" onclick="alert('ログ管理を実行します')">
                📋 ログ管理
            </a>
            <a href="#" class="tool-button" onclick="alert('ドキュメント統合を実行します')">
                📚 ドキュメント統合
            </a>
            <a href="#" class="tool-button" onclick="alert('セキュリティ監査を実行します')">
                🔐 セキュリティ監査
            </a>
            <a href="http://localhost:5008" class="tool-button" target="_blank">
                🖥️ Screen Sharing
            </a>
            <a href="http://localhost:10000" class="tool-button" target="_blank">
                🎯 Command Center
            </a>
            <a href="http://localhost:3000" class="tool-button" target="_blank">
                📊 Grafana
            </a>
            <a href="http://localhost:9090" class="tool-button" target="_blank">
                📈 Prometheus
            </a>
        </div>
        
        <div class="timestamp">
            最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
        
        with open(dashboard_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        self.log(f"✅ 統合ダッシュボード作成完了: {dashboard_html}")
        
        return {"success": True, "path": str(dashboard_html)}
    
    def generate_report(self) -> str:
        """最適化レポート生成"""
        duration = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        report = f"""
{'='*70}
🎉 Mana Ultimate Optimizer - 実行レポート
{'='*70}

実行時間: {duration:.1f}秒
実行日時: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        # 改善サマリー
        if "backup" in self.stats["improvements"]:
            backup = self.stats["improvements"]["backup"]
            report += f"""
💾 バックアップ最適化:
   削減: {backup['saved_mb']:.1f}MB ({backup['reduction_percent']:.1f}%)
"""
        
        if "logs" in self.stats["improvements"]:
            logs = self.stats["improvements"]["logs"]
            report += f"""
📋 ログ最適化:
   削減: {logs['saved_mb']:.1f}MB
"""
        
        if "documents" in self.stats["improvements"]:
            docs = self.stats["improvements"]["documents"]
            report += f"""
📚 ドキュメント最適化:
   削減: {docs['reduced_count']}ファイル
"""
        
        if "system" in self.stats["improvements"]:
            system = self.stats["improvements"]["system"]
            report += """
⚡ システムリソース最適化:
"""
            for improvement in system:
                report += f"   ✅ {improvement}\n"
        
        # 実行済みタスク
        report += f"""
{'='*70}
実行タスク: {len(self.stats['optimizations'])}個
"""
        for opt in self.stats["optimizations"]:
            status = "✅" if opt["success"] else "❌"
            report += f"{status} {opt['description']}\n"
        
        report += f"""
{'='*70}
"""
        
        return report
    
    def _get_dir_size(self, path_pattern: str) -> float:
        """ディレクトリサイズ取得（MB）"""
        try:
            result = subprocess.run(
                ["du", "-sm", path_pattern],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0:
                total = sum(int(line.split()[0]) for line in result.stdout.strip().split('\n') if line)
                return total
        except subprocess.SubprocessError:
            pass
        return 0
    
    def _count_files(self, directory: str, pattern: str) -> int:
        """ファイル数カウント"""
        try:
            result = subprocess.run(
                ["find", directory, "-name", pattern, "-type", "f"],
                capture_output=True,
                text=True
            )
            return len(result.stdout.strip().split('\n')) if result.stdout else 0
        except IOError:
            return 0
    
    def run_full_optimization(self):
        """完全最適化実行"""
        self.log("=" * 70)
        self.log("🚀 Mana Ultimate Optimizer - 完全最適化開始")
        self.log("=" * 70)
        self.log("")
        
        # システム統計取得
        self.log("📊 初期システム統計:")
        initial_stats = self.get_system_stats()
        for key, value in initial_stats.items():
            self.log(f"   {key}: {value}")
        self.log("")
        
        # 各最適化実行
        self.optimize_backups()
        self.log("")
        
        self.optimize_logs()
        self.log("")
        
        self.optimize_documents()
        self.log("")
        
        self.optimize_system_resources()
        self.log("")
        
        self.run_security_audit()
        self.log("")
        
        self.create_unified_dashboard()
        self.log("")
        
        # 最終統計
        self.log("📊 最終システム統計:")
        final_stats = self.get_system_stats()
        for key, value in final_stats.items():
            self.log(f"   {key}: {value}")
        self.log("")
        
        # レポート生成
        report = self.generate_report()
        print(report)
        
        # レポート保存
        report_file = self.logs_dir / f"optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, "w") as f:
            f.write(report)
        
        self.log(f"📄 レポート保存: {report_file}")
        self.log("")
        self.log("=" * 70)
        self.log("✅ 完全最適化完了！")
        self.log("=" * 70)


def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        🚀 Mana Ultimate Optimizer v1.0                       ║
║                                                               ║
║        全システムを統合して自動最適化                            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    optimizer = ManaUltimateOptimizer()
    
    try:
        optimizer.run_full_optimization()
    except KeyboardInterrupt:
        print("\n\n⚠️  最適化が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

