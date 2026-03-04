#!/usr/bin/env python3
"""
Mana Smart Log Analyzer
スマートログ分析システム - エラー自動検出・異常パターン検知
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaSmartLogAnalyzer:
    def __init__(self):
        self.log_dir = "/root/logs"
        self.db_path = "/root/mana_log_analysis.db"
        
        # エラーパターン
        self.error_patterns = {
            "critical": [
                r'CRITICAL',
                r'FATAL',
                r'Traceback \(most recent call last\)',
                r'Exception:',
                r'Error:',
                r'Failed to',
                r'Connection refused',
                r'Cannot connect',
                r'Out of memory'
            ],
            "error": [
                r'ERROR',
                r'error',
                r'failed',
                r'failure',
                r'exception',
                r'timeout',
                r'refused',
                r'denied'
            ],
            "warning": [
                r'WARNING',
                r'WARN',
                r'deprecated',
                r'slow',
                r'retry'
            ]
        }
        
        # 異常パターン
        self.anomaly_patterns = {
            "memory_leak": r'memory.*(?:leak|grow|increase)',
            "high_cpu": r'cpu.*(?:high|100%|spike)',
            "disk_full": r'disk.*(?:full|space|quota)',
            "connection_issue": r'connection.*(?:timeout|refused|reset|closed)',
            "auth_failure": r'auth.*(?:fail|denied|invalid|incorrect)',
            "permission_denied": r'permission.*denied'
        }
        
        self.init_database()
        logger.info("📊 Mana Smart Log Analyzer 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ログエントリテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS log_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_file TEXT,
                line_number INTEGER,
                timestamp TEXT,
                level TEXT,
                message TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 異常検出テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anomaly_type TEXT,
                severity TEXT,
                description TEXT,
                log_file TEXT,
                occurrences INTEGER DEFAULT 1,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 統計テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS log_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                log_file TEXT,
                total_lines INTEGER,
                error_count INTEGER,
                warning_count INTEGER,
                critical_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def parse_log_line(self, line: str) -> Dict[str, Any]:
        """ログ行を解析"""
        try:
            # タイムスタンプ抽出
            timestamp_match = re.search(
                r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', 
                line
            )
            timestamp = timestamp_match.group(1) if timestamp_match else None
            
            # レベル抽出
            level = "INFO"
            for lvl in ["CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG"]:
                if lvl in line.upper():
                    level = lvl if lvl != "WARN" else "WARNING"
                    break
            
            return {
                "timestamp": timestamp,
                "level": level,
                "message": line.strip(),
                "raw": line
            }
            
        except Exception as e:
            logger.error(f"ログ解析エラー: {e}")
            return {"level": "UNKNOWN", "message": line, "raw": line}
    
    def categorize_error(self, message: str) -> Tuple[str, str]:
        """エラーをカテゴリ分類"""
        message_lower = message.lower()
        
        # CRITICALチェック
        for pattern in self.error_patterns["critical"]:
            if re.search(pattern, message, re.I):
                return ("error", "critical")
        
        # ERRORチェック
        for pattern in self.error_patterns["error"]:
            if re.search(pattern, message_lower):
                return ("error", "error")
        
        # WARNINGチェック
        for pattern in self.error_patterns["warning"]:
            if re.search(pattern, message, re.I):
                return ("warning", "warning")
        
        return ("info", "info")
    
    def detect_anomalies(self, log_file: str) -> List[Dict[str, Any]]:
        """異常パターン検出"""
        anomalies = []
        
        try:
            if not os.path.exists(log_file):
                return []
            
            with open(log_file, 'r', errors='ignore') as f:
                content = f.read()
            
            for anomaly_type, pattern in self.anomaly_patterns.items():
                matches = re.findall(pattern, content, re.I)
                if matches:
                    anomalies.append({
                        "type": anomaly_type,
                        "severity": "high" if len(matches) > 5 else "medium",
                        "occurrences": len(matches),
                        "log_file": os.path.basename(log_file),
                        "description": f"{anomaly_type} detected {len(matches)} times"
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"異常検出エラー ({log_file}): {e}")
            return []
    
    def analyze_log_file(self, log_file: str, lines_limit: int = 1000) -> Dict[str, Any]:
        """ログファイルを分析"""
        logger.info(f"📄 分析中: {log_file}")
        
        try:
            if not os.path.exists(log_file):
                return {"error": "File not found"}
            
            with open(log_file, 'r', errors='ignore') as f:
                lines = f.readlines()
            
            # 最新N行のみ分析
            lines = lines[-lines_limit:]
            
            stats = {
                "file": os.path.basename(log_file),
                "total_lines": len(lines),
                "errors": [],
                "warnings": [],
                "critical": [],
                "error_count": 0,
                "warning_count": 0,
                "critical_count": 0,
                "anomalies": []
            }
            
            # 各行を分析
            for i, line in enumerate(lines, 1):
                parsed = self.parse_log_line(line)
                category, severity = self.categorize_error(parsed["message"])
                
                if severity == "critical":
                    stats["critical"].append({
                        "line": i,
                        "message": parsed["message"][:200]
                    })
                    stats["critical_count"] += 1
                elif severity == "error":
                    stats["errors"].append({
                        "line": i,
                        "message": parsed["message"][:200]
                    })
                    stats["error_count"] += 1
                elif severity == "warning":
                    stats["warnings"].append({
                        "line": i,
                        "message": parsed["message"][:200]
                    })
                    stats["warning_count"] += 1
            
            # 異常検出
            stats["anomalies"] = self.detect_anomalies(log_file)
            
            # データベースに保存
            self._save_stats(stats)
            
            logger.info(f"✅ 分析完了: {stats['error_count']}エラー, {stats['warning_count']}警告")
            
            return stats
            
        except Exception as e:
            logger.error(f"ログ分析エラー ({log_file}): {e}")
            return {"error": str(e)}
    
    def analyze_all_logs(self) -> Dict[str, Any]:
        """全ログファイルを分析"""
        logger.info("📊 全ログファイルを分析中...")
        
        if not os.path.exists(self.log_dir):
            return {"error": "Log directory not found"}
        
        log_files = [
            os.path.join(self.log_dir, f) 
            for f in os.listdir(self.log_dir) 
            if f.endswith('.log')
        ]
        
        results = {}
        total_errors = 0
        total_warnings = 0
        total_critical = 0
        all_anomalies = []
        
        for log_file in log_files:
            result = self.analyze_log_file(log_file)
            if "error" not in result:
                results[os.path.basename(log_file)] = result
                total_errors += result.get("error_count", 0)
                total_warnings += result.get("warning_count", 0)
                total_critical += result.get("critical_count", 0)
                all_anomalies.extend(result.get("anomalies", []))
        
        summary = {
            "total_files": len(results),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "total_critical": total_critical,
            "anomalies": all_anomalies,
            "files": results,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ 全分析完了: {len(results)}ファイル")
        
        return summary
    
    def get_error_trends(self, days: int = 7) -> Dict[str, Any]:
        """エラートレンド分析"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute('''
                SELECT date, SUM(error_count), SUM(warning_count), SUM(critical_count)
                FROM log_stats
                WHERE created_at >= ?
                GROUP BY date
                ORDER BY date
            ''', (since,))
            
            trends = []
            for row in cursor.fetchall():
                trends.append({
                    "date": row[0],
                    "errors": row[1],
                    "warnings": row[2],
                    "critical": row[3]
                })
            
            conn.close()
            
            return {
                "period_days": days,
                "trends": trends
            }
            
        except Exception as e:
            logger.error(f"トレンド分析エラー: {e}")
            return {}
    
    def get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """頻出エラーTOP N"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT message, COUNT(*) as count, log_file
                FROM log_entries
                WHERE level IN ('ERROR', 'CRITICAL')
                GROUP BY message
                ORDER BY count DESC
                LIMIT ?
            ''', (limit,))
            
            errors = []
            for row in cursor.fetchall():
                errors.append({
                    "message": row[0][:200],
                    "count": row[1],
                    "log_file": row[2]
                })
            
            conn.close()
            
            return errors
            
        except Exception as e:
            logger.error(f"頻出エラー取得エラー: {e}")
            return []
    
    def _save_stats(self, stats: Dict[str, Any]):
        """統計をデータベースに保存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute('''
                INSERT INTO log_stats (date, log_file, total_lines, error_count, warning_count, critical_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                today,
                stats["file"],
                stats["total_lines"],
                stats["error_count"],
                stats["warning_count"],
                stats["critical_count"]
            ))
            
            # 異常を保存
            for anomaly in stats.get("anomalies", []):
                cursor.execute('''
                    INSERT INTO anomalies (anomaly_type, severity, description, log_file, occurrences, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    anomaly["type"],
                    anomaly["severity"],
                    anomaly["description"],
                    anomaly["log_file"],
                    anomaly["occurrences"],
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"統計保存エラー: {e}")
    
    def generate_report(self) -> Dict[str, Any]:
        """分析レポート生成"""
        logger.info("📋 レポート生成中...")
        
        summary = self.analyze_all_logs()
        trends = self.get_error_trends(7)
        top_errors = self.get_top_errors(10)
        
        report = {
            "summary": summary,
            "trends": trends,
            "top_errors": top_errors,
            "generated_at": datetime.now().isoformat()
        }
        
        # レポートをファイルに保存
        report_file = f"/root/logs/log_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ レポート保存: {report_file}")
        
        return report

def main():
    analyzer = ManaSmartLogAnalyzer()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "analyze":
            result = analyzer.analyze_all_logs()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "report":
            report = analyzer.generate_report()
            print(json.dumps(report, indent=2, ensure_ascii=False))
        
        elif command == "trends":
            trends = analyzer.get_error_trends(7)
            print(json.dumps(trends, indent=2, ensure_ascii=False))
        
        elif command == "top":
            errors = analyzer.get_top_errors(10)
            print(json.dumps(errors, indent=2, ensure_ascii=False))
        
        elif command == "file":
            if len(sys.argv) > 2:
                log_file = sys.argv[2]
                result = analyzer.analyze_log_file(log_file)
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print("Usage: mana_smart_log_analyzer.py file <log_file_path>")
        
        else:
            print("Usage: mana_smart_log_analyzer.py [analyze|report|trends|top|file]")
    else:
        # デフォルトは全ログ分析
        result = analyzer.analyze_all_logs()
        print("\n=== ログ分析サマリー ===")
        print(f"ファイル数: {result['total_files']}")
        print(f"Critical: {result['total_critical']}")
        print(f"Error: {result['total_errors']}")
        print(f"Warning: {result['total_warnings']}")
        print(f"異常検出: {len(result['anomalies'])}")

if __name__ == "__main__":
    main()

