"""
秘書機能（Secretary Routines）
朝・昼・夜のルーチンを自動実行
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 標準APIをインポート
try:
    import manaos_core_api as manaos
    MANAOS_API_AVAILABLE = True
except ImportError:
    MANAOS_API_AVAILABLE = False
    logger.warning("manaOS標準APIが利用できません")


class SecretaryRoutines:
    """秘書機能（朝・昼・夜のルーチン）"""
    
    def __init__(self):
        """初期化"""
        self.tasks_storage = Path(__file__).parent / "data" / "tasks.json"
        self.schedule_storage = Path(__file__).parent / "data" / "schedule.json"
        self._ensure_storage()
    
    def _ensure_storage(self):
        """ストレージを確保"""
        self.tasks_storage.parent.mkdir(parents=True, exist_ok=True)
        self.schedule_storage.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_tasks(self) -> List[Dict[str, Any]]:
        """タスクを読み込む"""
        import json
        try:
            if self.tasks_storage.exists():
                with open(self.tasks_storage, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"タスク読み込みエラー: {e}")
        return []
    
    def _save_tasks(self, tasks: List[Dict[str, Any]]):
        """タスクを保存"""
        import json
        try:
            with open(self.tasks_storage, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"タスク保存エラー: {e}")
    
    def _load_schedule(self) -> List[Dict[str, Any]]:
        """スケジュールを読み込む"""
        import json
        try:
            if self.schedule_storage.exists():
                with open(self.schedule_storage, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"スケジュール読み込みエラー: {e}")
        return []
    
    def _get_today_schedule(self) -> List[Dict[str, Any]]:
        """今日の予定を取得"""
        schedule = self._load_schedule()
        today = datetime.now().date().isoformat()
        
        today_schedule = [
            item for item in schedule
            if item.get("date", "") == today
        ]
        
        return sorted(today_schedule, key=lambda x: x.get("time", ""))
    
    def _get_top3_tasks(self) -> List[Dict[str, Any]]:
        """最重要3タスクを取得"""
        tasks = self._load_tasks()
        
        # 未完了のタスクをフィルタ
        incomplete = [
            task for task in tasks
            if not task.get("completed", False)
        ]
        
        # 優先度でソート
        incomplete.sort(
            key=lambda x: x.get("priority", 0),
            reverse=True
        )
        
        return incomplete[:3]
    
    def _get_yesterday_log_diff(self) -> Dict[str, Any]:
        """昨日のログ差分を取得"""
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        
        # 統一記憶システムから検索
        if MANAOS_API_AVAILABLE:
            try:
                # 昨日のログを検索
                results = manaos.recall(
                    query=f"date:{yesterday}",
                    scope="all",
                    limit=50
                )
                
                # ログを分類
                log_diff = {
                    "total": len(results),
                    "conversations": 0,
                    "tasks": 0,
                    "system": 0,
                    "summary": ""
                }
                
                for result in results:
                    log_type = result.get("type", "system")
                    if log_type == "conversation":
                        log_diff["conversations"] += 1
                    elif log_type in ["action", "task"]:
                        log_diff["tasks"] += 1
                    else:
                        log_diff["system"] += 1
                
                # 要約を生成（LLMを使用）
                if results:
                    summary_prompt = f"以下のログを要約してください（1行で）:\n"
                    for result in results[:10]:
                        summary_prompt += f"- {result.get('content', '')[:100]}\n"
                    
                    try:
                        summary_result = manaos.act("llm_call", {
                            "task_type": "lightweight_conversation",  # LFM 2.5使用（高速・軽量）
                            "prompt": summary_prompt
                        })
                        log_diff["summary"] = summary_result.get("response", "")[:200]
                    except Exception:
                        log_diff["summary"] = "要約生成に失敗しました"
                
                return log_diff
            
            except Exception as e:
                logger.warning(f"ログ差分取得エラー: {e}")
        
        return {
            "total": 0,
            "conversations": 0,
            "tasks": 0,
            "system": 0,
            "summary": "ログ取得に失敗しました"
        }
    
    def _get_latest_news(self, topics: List[str] = None) -> Dict[str, Any]:
        """最新情報を検索（SearXNG使用）"""
        if not MANAOS_API_AVAILABLE:
            return {"results": [], "count": 0}
        
        # デフォルトのトピック
        if topics is None:
            topics = ["テクノロジー", "AI", "プログラミング"]
        
        all_results = []
        
        for topic in topics[:3]:  # 最大3トピック
            try:
                # Brave Search APIを優先的に使用（利用可能な場合）
                search_result = None
                try:
                    search_result = manaos.act("brave_search", {
                        "query": f"{topic} 最新情報",
                        "count": 3,
                        "search_lang": "jp",
                        "freshness": "pd"  # 過去1日
                    })
                except Exception:
                    # Brave Searchが利用できない場合はSearXNGを使用
                    search_result = manaos.act("web_search", {
                        "query": f"{topic} 最新情報",
                        "max_results": 3,
                        "language": "ja",
                        "time_range": "day"  # 過去24時間
                    })
                
                if search_result and search_result.get("results"):
                    all_results.extend(search_result["results"][:2])  # 各トピックから2件
            except Exception as e:
                logger.warning(f"最新情報検索エラー ({topic}): {e}")
        
        return {
            "results": all_results[:5],  # 最大5件
            "count": len(all_results)
        }
    
    def morning_routine(self) -> Dict[str, Any]:
        """
        朝のルーチン
        今日の予定＋最重要3タスク＋昨日のログ差分＋最新情報
        """
        logger.info("[Secretary] 朝のルーチンを開始")
        
        # 今日の予定
        schedule = self._get_today_schedule()
        
        # 最重要3タスク
        tasks = self._get_top3_tasks()
        
        # 昨日のログ差分
        log_diff = self._get_yesterday_log_diff()
        
        # 最新情報を検索
        latest_news = self._get_latest_news()
        
        # レポートを生成
        report_lines = [
            "🌅 **朝のルーチン**",
            "",
            "## 📅 今日の予定",
        ]
        
        if schedule:
            for item in schedule:
                time_str = item.get("time", "")
                title = item.get("title", "")
                report_lines.append(f"- {time_str} {title}")
        else:
            report_lines.append("- 予定なし")
        
        report_lines.extend([
            "",
            "## 🎯 最重要3タスク",
        ])
        
        for i, task in enumerate(tasks, 1):
            title = task.get("title", "タスク")
            priority = task.get("priority", 0)
            report_lines.append(f"{i}. {title} (優先度: {priority})")
        
        if not tasks:
            report_lines.append("- タスクなし")
        
        report_lines.extend([
            "",
            "## 📊 昨日のログ差分",
            f"- 総数: {log_diff['total']}件",
            f"- 会話: {log_diff['conversations']}件",
            f"- タスク: {log_diff['tasks']}件",
            f"- システム: {log_diff['system']}件",
        ])
        
        if log_diff.get("summary"):
            report_lines.extend([
                "",
                "### 要約",
                log_diff["summary"]
            ])
        
        # 最新情報セクション
        if latest_news.get("results"):
            report_lines.extend([
                "",
                "## 📰 最新情報（Web検索）",
            ])
            
            for i, item in enumerate(latest_news["results"][:3], 1):
                title = item.get("title", "")
                url = item.get("url", "")
                report_lines.append(f"{i}. {title}")
                if url:
                    report_lines.append(f"   {url}")
        
        report = "\n".join(report_lines)
        
        # 通知
        if MANAOS_API_AVAILABLE:
            try:
                manaos.emit(
                    "morning_routine",
                    {"message": report},
                    "normal"
                )
            except Exception as e:
                logger.error(f"通知送信エラー: {e}")
        
        # 記憶に保存
        if MANAOS_API_AVAILABLE:
            try:
                manaos.remember({
                    "type": "system",
                    "content": report,
                    "metadata": {
                        "routine": "morning",
                        "date": datetime.now().date().isoformat()
                    }
                }, format_type="system")
            except Exception as e:
                logger.error(f"記憶保存エラー: {e}")
        
        logger.info("[Secretary] 朝のルーチン完了")
        
        return {
            "schedule": schedule,
            "tasks": tasks,
            "log_diff": log_diff,
            "latest_news": latest_news,
            "report": report
        }
    
    def _analyze_incomplete_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        未完了タスクを自動分析（LLM使用）
        
        Returns:
            {
                "reason_category": "時間不足" | "不明確" | "依存待ち" | "気力不足" | "難しすぎ" | "その他",
                "reason_detail": "詳細な理由",
                "suggestion": "改善提案"
            }
        """
        title = task.get("title", "")
        description = task.get("description", "")
        priority = task.get("priority", 0)
        created_date = task.get("created_date", "")
        
        # 理由が既に入力されている場合は、それを分類
        existing_reason = task.get("reason", "")
        if existing_reason and existing_reason != "理由不明":
            # 既存の理由を分類
            reason_lower = existing_reason.lower()
            if "時間" in reason_lower or "time" in reason_lower or "忙" in reason_lower:
                category = "時間不足"
            elif "不明" in reason_lower or "わか" in reason_lower or "不確" in reason_lower:
                category = "不明確"
            elif "待" in reason_lower or "依存" in reason_lower or "wait" in reason_lower:
                category = "依存待ち"
            elif "気力" in reason_lower or "やる気" in reason_lower or "モチベ" in reason_lower:
                category = "気力不足"
            elif "難" in reason_lower or "複雑" in reason_lower or "hard" in reason_lower:
                category = "難しすぎ"
            else:
                category = "その他"
            
            return {
                "reason_category": category,
                "reason_detail": existing_reason,
                "suggestion": None
            }
        
        # 理由が未入力の場合は、LLMで分析
        if MANAOS_API_AVAILABLE:
            try:
                # タスク情報をまとめる
                task_info = f"""
タスク名: {title}
説明: {description}
優先度: {priority}
作成日: {created_date}
"""
                
                # LLMで分析
                analysis_prompt = f"""以下の未完了タスクを分析し、未完了の理由を1行で推測してください。

{task_info}

未完了の理由を以下のカテゴリから1つ選び、1行で説明してください：
- 時間不足: 時間が足りなかった
- 不明確: タスクの内容が不明確だった
- 依存待ち: 他のタスクやリソースを待っている
- 気力不足: やる気が出なかった
- 難しすぎ: タスクが難しすぎた
- その他: 上記以外

形式: [カテゴリ] 理由の説明

例: [時間不足] 他の緊急タスクが入って時間が取れなかった"""
                
                analysis_result = manaos.act("llm_call", {
                    "task_type": "lightweight_conversation",  # LFM 2.5使用（高速・軽量）
                    "prompt": analysis_prompt
                })
                
                analysis_text = analysis_result.get("response", "").strip()
                
                # カテゴリを抽出
                category = "その他"
                reason_detail = analysis_text
                
                if "[時間不足]" in analysis_text:
                    category = "時間不足"
                    reason_detail = analysis_text.replace("[時間不足]", "").strip()
                elif "[不明確]" in analysis_text:
                    category = "不明確"
                    reason_detail = analysis_text.replace("[不明確]", "").strip()
                elif "[依存待ち]" in analysis_text:
                    category = "依存待ち"
                    reason_detail = analysis_text.replace("[依存待ち]", "").strip()
                elif "[気力不足]" in analysis_text:
                    category = "気力不足"
                    reason_detail = analysis_text.replace("[気力不足]", "").strip()
                elif "[難しすぎ]" in analysis_text:
                    category = "難しすぎ"
                    reason_detail = analysis_text.replace("[難しすぎ]", "").strip()
                
                # 改善提案を生成（カテゴリに応じて）
                suggestion = None
                if category in ["不明確", "難しすぎ"]:
                    suggestion_prompt = f"""以下のタスクを「より小さなタスクに分割」する提案を1行でしてください。

タスク: {title}
理由: {reason_detail}

例: 「〇〇を3ステップに分割: ①調査、②設計、③実装」"""
                    
                    suggestion_result = manaos.act("llm_call", {
                        "task_type": "lightweight_conversation",  # LFM 2.5使用（高速・軽量）
                        "prompt": suggestion_prompt
                    })
                    suggestion = suggestion_result.get("response", "").strip()
                
                return {
                    "reason_category": category,
                    "reason_detail": reason_detail,
                    "suggestion": suggestion
                }
            
            except Exception as e:
                logger.warning(f"タスク分析エラー: {e}")
        
        # LLM分析に失敗した場合はデフォルト
        return {
            "reason_category": "その他",
            "reason_detail": "理由不明（分析失敗）",
            "suggestion": None
        }
    
    def _check_progress(self) -> Dict[str, Any]:
        """進捗確認（未完了タスクの自動分析付き）"""
        tasks = self._load_tasks()
        
        total = len(tasks)
        completed = len([t for t in tasks if t.get("completed", False)])
        incomplete = total - completed
        
        # 未完了タスクの理由を取得
        incomplete_tasks = [
            task for task in tasks
            if not task.get("completed", False)
        ]
        
        reasons = []
        analyzed_tasks = []
        for task in incomplete_tasks[:5]:  # 最大5件
            title = task.get("title", "")
            
            # 自動分析
            analysis = self._analyze_incomplete_task(task)
            analyzed_tasks.append({
                "title": title,
                "category": analysis["reason_category"],
                "detail": analysis["reason_detail"],
                "suggestion": analysis["suggestion"]
            })
            
            # 理由を1行で表示
            reason_line = f"- {title}: [{analysis['reason_category']}] {analysis['reason_detail']}"
            if analysis["suggestion"]:
                reason_line += f" → 提案: {analysis['suggestion']}"
            reasons.append(reason_line)
        
        return {
            "total": total,
            "completed": completed,
            "incomplete": incomplete,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "reasons": reasons,
            "analyzed_tasks": analyzed_tasks
        }
    
    def noon_routine(self) -> Dict[str, Any]:
        """
        昼のルーチン
        進捗確認＋未完了の理由を1行で
        """
        logger.info("[Secretary] 昼のルーチンを開始")
        
        # 進捗確認
        progress = self._check_progress()
        
        # レポートを生成
        report_lines = [
            "🌞 **昼のルーチン**",
            "",
            "## 📊 進捗確認",
            f"- 総タスク数: {progress['total']}件",
            f"- 完了: {progress['completed']}件",
            f"- 未完了: {progress['incomplete']}件",
            f"- 完了率: {progress['completion_rate']:.1f}%",
            "",
            "## ❌ 未完了タスクの理由（1行）",
        ]
        
        if progress['reasons']:
            report_lines.extend(progress['reasons'])
            
            # 3日以上未完了のタスクがあれば追撃通知
            from datetime import timedelta
            three_days_ago = (datetime.now() - timedelta(days=3)).date().isoformat()
            old_incomplete = [
                task for task in self._load_tasks()
                if not task.get("completed", False) and task.get("created_date", "") < three_days_ago
            ]
            
            if old_incomplete:
                report_lines.extend([
                    "",
                    "## ⚠️ 3日以上未完了のタスク",
                    f"- {len(old_incomplete)}件のタスクが3日以上未完了です",
                    "- 優先度を上げるか、タスクを再設計することを検討してください"
                ])
        else:
            report_lines.append("- 未完了タスクなし")
        
        report = "\n".join(report_lines)
        
        # 通知
        if MANAOS_API_AVAILABLE:
            try:
                manaos.emit(
                    "noon_routine",
                    {"message": report},
                    "normal"
                )
            except Exception as e:
                logger.error(f"通知送信エラー: {e}")
        
        # 記憶に保存
        if MANAOS_API_AVAILABLE:
            try:
                manaos.remember({
                    "type": "system",
                    "content": report,
                    "metadata": {
                        "routine": "noon",
                        "date": datetime.now().date().isoformat()
                    }
                }, format_type="system")
            except Exception as e:
                logger.error(f"記憶保存エラー: {e}")
        
        logger.info("[Secretary] 昼のルーチン完了")
        
        return {
            "progress": progress,
            "report": report
        }
    
    def _generate_daily_report(self) -> str:
        """日報を自動生成"""
        today = datetime.now().date().isoformat()
        
        # 今日のログを取得
        if MANAOS_API_AVAILABLE:
            try:
                results = manaos.recall(
                    query=f"date:{today}",
                    scope="all",
                    limit=100
                )
                
                # LLMで日報を生成
                report_prompt = f"以下のログから日報を生成してください:\n\n"
                for result in results[:20]:
                    report_prompt += f"- {result.get('content', '')[:200]}\n"
                
                try:
                    report_result = manaos.act("llm_call", {
                        "task_type": "lightweight_conversation",  # LFM 2.5使用（高速・軽量）
                        "prompt": report_prompt
                    })
                    return report_result.get("response", "日報生成に失敗しました")
                except Exception:
                    return "日報生成に失敗しました（LLM呼び出しエラー）"
            
            except Exception as e:
                logger.warning(f"日報生成エラー: {e}")
        
        return "日報生成に失敗しました（ログ取得エラー）"
    
    def _prepare_tomorrow(self) -> Dict[str, Any]:
        """明日の仕込み"""
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
        
        # 明日の予定を取得
        schedule = self._load_schedule()
        tomorrow_schedule = [
            item for item in schedule
            if item.get("date", "") == tomorrow
        ]
        
        # 未完了タスクを取得
        tasks = self._load_tasks()
        incomplete_tasks = [
            task for task in tasks
            if not task.get("completed", False)
        ]
        
        # 優先度の高いタスクを3件選ぶ
        incomplete_tasks.sort(
            key=lambda x: x.get("priority", 0),
            reverse=True
        )
        top_tasks = incomplete_tasks[:3]
        
        return {
            "schedule": tomorrow_schedule,
            "tasks": top_tasks
        }
    
    def evening_routine(self) -> Dict[str, Any]:
        """
        夜のルーチン
        日報自動生成＋明日の仕込み
        """
        logger.info("[Secretary] 夜のルーチンを開始")
        
        # 日報自動生成
        daily_report = self._generate_daily_report()
        
        # 明日の仕込み
        tomorrow_prep = self._prepare_tomorrow()
        
        # レポートを生成
        report_lines = [
            "🌙 **夜のルーチン**",
            "",
            "## 📝 日報",
            daily_report,
            "",
            "## 📅 明日の仕込み",
            "",
            "### 予定",
        ]
        
        if tomorrow_prep["schedule"]:
            for item in tomorrow_prep["schedule"]:
                time_str = item.get("time", "")
                title = item.get("title", "")
                report_lines.append(f"- {time_str} {title}")
        else:
            report_lines.append("- 予定なし")
        
        report_lines.extend([
            "",
            "### 優先タスク",
        ])
        
        for i, task in enumerate(tomorrow_prep["tasks"], 1):
            title = task.get("title", "タスク")
            priority = task.get("priority", 0)
            report_lines.append(f"{i}. {title} (優先度: {priority})")
        
        if not tomorrow_prep["tasks"]:
            report_lines.append("- タスクなし")
        
        report = "\n".join(report_lines)
        
        # 通知
        if MANAOS_API_AVAILABLE:
            try:
                manaos.emit(
                    "evening_routine",
                    {"message": report},
                    "normal"
                )
            except Exception as e:
                logger.error(f"通知送信エラー: {e}")
        
        # 記憶に保存
        if MANAOS_API_AVAILABLE:
            try:
                manaos.remember({
                    "type": "summary",
                    "content": report,
                    "metadata": {
                        "routine": "evening",
                        "date": datetime.now().date().isoformat()
                    }
                }, format_type="summary")
            except Exception as e:
                logger.error(f"記憶保存エラー: {e}")
        
        logger.info("[Secretary] 夜のルーチン完了")
        
        return {
            "daily_report": daily_report,
            "tomorrow_prep": tomorrow_prep,
            "report": report
        }


# 使用例
if __name__ == "__main__":
    secretary = SecretaryRoutines()
    
    # 朝のルーチン
    print("=" * 60)
    print("朝のルーチン")
    print("=" * 60)
    morning_result = secretary.morning_routine()
    print(morning_result["report"])
    
    # 昼のルーチン
    print("\n" + "=" * 60)
    print("昼のルーチン")
    print("=" * 60)
    noon_result = secretary.noon_routine()
    print(noon_result["report"])
    
    # 夜のルーチン
    print("\n" + "=" * 60)
    print("夜のルーチン")
    print("=" * 60)
    evening_result = secretary.evening_routine()
    print(evening_result["report"])






