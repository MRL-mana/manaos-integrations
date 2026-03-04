from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
from github import Github
import os
from dotenv import load_dotenv
from pathlib import Path
import base64
import textwrap
import subprocess
import json
import logging
import sys
from datetime import datetime, timedelta
from collections import defaultdict
import requests

# psutil をインポート（レミ用Control APIで使用）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# ベースディレクトリを取得（スクリプトの場所を基準）
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'hub.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# エラーログ専用ハンドラー
error_log_file = LOGS_DIR / f'error-{datetime.now().strftime("%Y-%m")}.log'
error_handler = logging.FileHandler(error_log_file)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(error_handler)

# 成功・失敗カウンタ（メモリ内、再起動でリセット）
_stats = defaultdict(int)
_stats_file = LOGS_DIR / 'stats.json'

# .envファイルのパスを明示的に指定
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="manaOS Command Hub", version="1.0.0")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DEFAULT_REPO = os.getenv("GITHUB_DEFAULT_REPO", "MRL-mana/manaos-knowledge")
COMMAND_HUB_TOKEN = os.getenv("COMMAND_HUB_TOKEN")
BASE_WORKDIR = Path(os.getenv("BASE_WORKDIR", "/root")).resolve()

# ======== スキーマ定義 =========


class Meta(BaseModel):
    caller: str = "unknown"
    reason: Optional[str] = None


class GithubUpdateParams(BaseModel):
    repo: Optional[str] = None
    branch: str = "main"
    path: str
    commit_message: str = "Update from manaOS Command Hub"
    content_mode: Literal["overwrite", "append"] = "overwrite"
    new_content: Optional[str] = None
    append_text: Optional[str] = None


class GithubGetParams(BaseModel):
    repo: Optional[str] = None
    branch: str = "main"
    path: str


class FileWriteParams(BaseModel):
    relative_path: str
    content: str
    mode: Literal["overwrite", "append"] = "overwrite"


class ImageJobParams(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    steps: int = 20
    sampler: str = "Euler a"
    cfg_scale: float = 7.0
    seed: int = -1


class DailyReflectionBundleParams(BaseModel):
    devqa_content: Optional[str] = None
    strategy_content: Optional[str] = None
    log_content: Optional[str] = None
    log_date: Optional[str] = None  # YYYY-MM-DD形式、省略時は今日


class DailyConsciousnessUpdateParams(BaseModel):
    devqa_content: Optional[str] = None
    strategy_content: Optional[str] = None
    log_content: Optional[str] = None
    profit_ideas: Optional[List[str]] = None  # 収益アイデアのリスト
    self_review_notes: Optional[str] = None  # 自己レビュー用のメモ
    daily_prompt_context: Optional[str] = None  # 今日のコンテキスト（体調・気分など）
    log_date: Optional[str] = None  # YYYY-MM-DD形式、省略時は今日


class WeeklyReportParams(BaseModel):
    iso_year: Optional[int] = None   # 省略時は「今日の年」
    iso_week: Optional[int] = None   # 省略時は「今日の週」
    output_path: Optional[str] = None  # 省略時: reports/weekly-YYYY-Www.md


class DailyTaskItem(BaseModel):
    title: str
    priority: Literal["S", "A", "B"] = "B"
    estimated_time: Optional[str] = None  # "30min", "1h" など
    best_time: Optional[Literal["morning",
                                "afternoon", "evening", "night"]] = None


class DailyPrompt(BaseModel):
    date: str
    top_tasks: List[DailyTaskItem]
    money_action: Optional[str] = None
    reward_action: Optional[str] = None
    text: str


class DailyPromptReadParams(BaseModel):
    date: Optional[str] = None  # "YYYY-MM-DD" / 省略時は今日


class Command(BaseModel):
    task: Literal[
        "github_update_file",
        "github_get_file",
        "file_write",
        "image_job",
        "daily_reflection_bundle",
        "daily_consciousness_update",
        "daily_prompt_read",
        "profit_ideas_analyze",
        "weekly_report_generate",
        "antigravity_status",
        "antigravity_start",
        "antigravity_workflow",
        "antigravity_connect"
    ]
    meta: Meta = Meta()
    params: Dict[str, Any] = Field(default_factory=dict)
    auth_token: str

# ======== ユーティリティ =========


def verify_auth(token: str):
    if not COMMAND_HUB_TOKEN:
        raise HTTPException(
            status_code=500, detail="Server misconfigured: no COMMAND_HUB_TOKEN")
    if token != COMMAND_HUB_TOKEN:
        logger.warning(f"Invalid auth token attempt")
        raise HTTPException(status_code=401, detail="Invalid auth token")
    logger.info("Auth verified")


def get_github_repo(full_name: Optional[str] = None):
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN is not set")
    gh = Github(GITHUB_TOKEN)
    repo_name = full_name or DEFAULT_REPO
    try:
        repo = gh.get_repo(repo_name)
        logger.info(f"GitHub repo accessed: {repo_name}")
        return repo
    except Exception as e:
        logger.error(f"GitHub repo access failed: {repo_name} - {e}")
        raise HTTPException(
            status_code=400, detail=f"Cannot access repo {repo_name}: {e}")


def ensure_safe_path(relative: str) -> Path:
    target = (BASE_WORKDIR / relative).resolve()
    if not str(target).startswith(str(BASE_WORKDIR)):
        logger.error(f"Path escape attempt: {relative}")
        raise HTTPException(
            status_code=400, detail="Path escapes BASE_WORKDIR")
    return target

# ======== タスク実装 =========


def handle_github_update(params_raw: Dict[str, Any]):
    params = GithubUpdateParams(**params_raw)
    repo = get_github_repo(params.repo)
    try:
        # ファイルが存在するか確認
        try:
            contents = repo.get_contents(params.path, ref=params.branch)
            current_text = contents.decoded_content.decode("utf-8")
            file_exists = True
        except Exception:
            # ファイルが存在しない場合は新規作成
            file_exists = False
            current_text = ""

        if params.content_mode == "overwrite":
            if not params.new_content:
                raise HTTPException(
                    status_code=400, detail="new_content is required for overwrite")
            final_text = params.new_content
        else:
            if not params.append_text:
                raise HTTPException(
                    status_code=400, detail="append_text is required for append")
            final_text = current_text + "\n" + \
                params.append_text if current_text else params.append_text

        if file_exists:
            # 既存ファイルを更新
            result = repo.update_file(
                path=params.path,
                message=params.commit_message,
                content=final_text,
                sha=contents.sha,
                branch=params.branch,
            )
            logger.info(
                f"GitHub file updated: {params.path} on {params.branch}")
        else:
            # 新規ファイルを作成
            result = repo.create_file(
                path=params.path,
                message=params.commit_message,
                content=final_text,
                branch=params.branch,
            )
            logger.info(
                f"GitHub file created: {params.path} on {params.branch}")

        return {
            "status": "ok",
            "action": "github_update_file",
            "path": params.path,
            "branch": params.branch,
            "commit_sha": result["commit"].sha,
            "created": not file_exists
        }
    except Exception as e:
        logger.error(f"GitHub update failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"GitHub update failed: {e}")


def handle_github_get(params_raw: Dict[str, Any]):
    params = GithubGetParams(**params_raw)
    repo = get_github_repo(params.repo)
    try:
        contents = repo.get_contents(params.path, ref=params.branch)
        text = contents.decoded_content.decode("utf-8")
        logger.info(
            f"GitHub file retrieved: {params.path} from {params.branch}")
        return {
            "status": "ok",
            "action": "github_get_file",
            "path": params.path,
            "branch": params.branch,
            "content": text,
        }
    except Exception as e:
        logger.error(f"GitHub get failed: {e}")
        raise HTTPException(status_code=500, detail=f"GitHub get failed: {e}")


def handle_file_write(params_raw: Dict[str, Any]):
    params = FileWriteParams(**params_raw)
    target = ensure_safe_path(params.relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if params.mode == "overwrite":
        text = params.content
    else:
        prev = ""
        if target.exists():
            prev = target.read_text(encoding="utf-8")
        text = prev + "\n" + params.content

    target.write_text(text, encoding="utf-8")
    logger.info(f"File written: {target}")
    return {
        "status": "ok",
        "action": "file_write",
        "path": str(target),
        "size": len(text)
    }


def handle_image_job(params_raw: Dict[str, Any]):
    params = ImageJobParams(**params_raw)
    # JSONLキューに書き出して、別プロセスがSD WebUI / n8nを叩く
    queue_file = ensure_safe_path("manaos_command_hub/queues/image_jobs.jsonl")
    queue_file.parent.mkdir(parents=True, exist_ok=True)

    job = {
        "prompt": params.prompt,
        "negative_prompt": params.negative_prompt,
        "steps": params.steps,
        "sampler": params.sampler,
        "cfg_scale": params.cfg_scale,
        "seed": params.seed,
        "created_at": datetime.now().isoformat(),
    }

    with open(queue_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(job, ensure_ascii=False) + "\n")

    logger.info(f"Image job queued: {queue_file}")
    return {
        "status": "ok",
        "action": "image_job",
        "queued_to": str(queue_file),
        "job_id": job.get("created_at")
    }


def handle_daily_reflection_bundle(params_raw: Dict[str, Any]):
    """daily_reflection_bundle: dev_qa + strategy + log を一括実行"""
    params = DailyReflectionBundleParams(**params_raw)
    results = []
    errors = []

    # 日付の決定
    log_date = params.log_date or datetime.now().date().isoformat()

    # 1. dev_qa.md に追記
    if params.devqa_content:
        try:
            devqa_result = handle_github_update({
                "path": "docs/guides/dev_qa.md",
                "content_mode": "append",
                "append_text": params.devqa_content,
                "commit_message": f"Daily reflection: dev_qa update ({log_date})"
            })
            results.append({"action": "dev_qa_update",
                           "status": "ok", **devqa_result})
        except Exception as e:
            errors.append(f"dev_qa update failed: {e}")
            results.append({"action": "dev_qa_update",
                           "status": "error", "error": str(e)})

    # 2. strategy.md に追記
    if params.strategy_content:
        try:
            strategy_result = handle_github_update({
                "path": "shared/strategy.md",
                "content_mode": "append",
                "append_text": params.strategy_content,
                "commit_message": f"Daily reflection: strategy update ({log_date})"
            })
            results.append({"action": "strategy_update",
                           "status": "ok", **strategy_result})
        except Exception as e:
            errors.append(f"strategy update failed: {e}")
            results.append({"action": "strategy_update",
                           "status": "error", "error": str(e)})

    # 3. ローカルログに追記
    if params.log_content:
        try:
            log_result = handle_file_write({
                "relative_path": f"logs/daily-{log_date}.log",
                "content": params.log_content,
                "mode": "append"
            })
            results.append(
                {"action": "log_write", "status": "ok", **log_result})
        except Exception as e:
            errors.append(f"log write failed: {e}")
            results.append(
                {"action": "log_write", "status": "error", "error": str(e)})

    # 結果をまとめる
    success_count = sum(1 for r in results if r.get("status") == "ok")
    total_count = len(results)

    return {
        "status": "ok" if success_count == total_count else "partial",
        "action": "daily_reflection_bundle",
        "date": log_date,
        "results": results,
        "summary": {
            "total": total_count,
            "success": success_count,
            "errors": len(errors)
        },
        "errors": errors if errors else None
    }


def generate_self_review(log_date: str) -> str:
    """週次自己レビューを生成"""
    from datetime import timedelta

    # 今週の日付範囲を計算
    date_obj = datetime.fromisoformat(log_date)
    days_since_monday = date_obj.weekday()
    week_start = date_obj - timedelta(days=days_since_monday + 6)  # 先週の月曜日
    week_end = date_obj

    # 今週のログを読み込む
    logs_dir = BASE_WORKDIR / "logs"
    success_items = []
    failure_items = []
    next_items = []

    current_date = week_start
    while current_date <= week_end:
        log_file = logs_dir / f"daily-{current_date.strftime('%Y-%m-%d')}.log"
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8")
            # 「今日やったこと」を抽出
            if "## 今日やったこと" in content:
                for line in content.split("\n"):
                    if line.strip().startswith("- "):
                        success_items.append(line.strip()[2:])
            # 「次どうするか」を抽出
            if "## 次どうするか" in content:
                for line in content.split("\n"):
                    if line.strip().startswith("- "):
                        next_items.append(line.strip()[2:])
        current_date += timedelta(days=1)

    # エラーログから失敗を抽出
    error_log_file = Path(
        f"/root/manaos_command_hub/logs/error-{date_obj.strftime('%Y-%m')}.log")
    if error_log_file.exists():
        error_content = error_log_file.read_text(encoding="utf-8")
        error_lines = [line for line in error_content.split(
            "\n") if "ERROR" in line]
        if error_lines:
            failure_items.append(f"エラーログに{len(error_lines)}件のエラーが記録されています")

    # レビューを生成
    review_lines = [
        f"# 週次自己レビュー: {week_start.strftime('%Y-%m-%d')} 〜 {week_end.strftime('%Y-%m-%d')}",
        "",
        f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 【成功したこと】",
        ""
    ]

    if success_items:
        for item in success_items[:10]:  # 最大10件
            review_lines.append(f"- {item}")
    else:
        review_lines.append("- 今週のログが見つかりませんでした")

    review_lines.extend([
        "",
        "## 【失敗／不安定】",
        ""
    ])

    if failure_items:
        for item in failure_items:
            review_lines.append(f"- {item}")
    else:
        review_lines.append("- 特に問題は見つかりませんでした")

    review_lines.extend([
        "",
        "## 【次にやるべき強化】",
        ""
    ])

    if next_items:
        unique_next = list(dict.fromkeys(next_items))  # 重複除去
        for item in unique_next[:10]:  # 最大10件
            review_lines.append(f"- {item}")
    else:
        review_lines.append("- 次のアクションは未設定です")

    review_lines.extend([
        "",
        "## 【レミの提案】",
        "",
        "- この流れはテンプレ化できる",
        "- 他人にも使わせられる",
        "- 自動化により進化速度が向上",
        ""
    ])

    return "\n".join(review_lines)


def generate_daily_prompt(log_date: str, context: Optional[str] = None) -> str:
    """daily_promptを生成（Persona）"""
    from datetime import timedelta

    date_obj = datetime.fromisoformat(log_date)
    weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
    weekday = weekday_names[date_obj.weekday()]

    # 昨日のログを読み込んでコンテキストに
    yesterday = date_obj - timedelta(days=1)
    yesterday_log = BASE_WORKDIR / "logs" / \
        f"daily-{yesterday.strftime('%Y-%m-%d')}.log"
    yesterday_context = ""
    if yesterday_log.exists():
        content = yesterday_log.read_text(encoding="utf-8")
        if "## 次どうするか" in content:
            next_section = content.split("## 次どうするか")[1].split("##")[0]
            yesterday_context = next_section.strip()[:200]  # 最初の200文字

    prompt_lines = [
        f"# 今日のmanaOSプロンプト: {log_date} ({weekday}曜日)",
        "",
        f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 📅 今日の予定",
        "",
        "- [ ] 今日のタスク1",
        "- [ ] 今日のタスク2",
        "- [ ] 今日のタスク3",
        "",
        "## 🎯 今日の目標",
        "",
        "- 目標1",
        "- 目標2",
        "",
    ]

    if context:
        prompt_lines.extend([
            "## 💭 体調・気分",
            "",
            context,
            "",
        ])

    if yesterday_context:
        prompt_lines.extend([
            "## 📝 昨日の「次どうするか」から",
            "",
            yesterday_context,
            "",
        ])

    prompt_lines.extend([
        "## 🎨 ムフフ優先度",
        "",
        "- [ ] 高（今日中にやりたい）",
        "- [ ] 中（今週中にやりたい）",
        "- [ ] 低（余裕があれば）",
        "",
        "## 💡 レミからの提案",
        "",
        "今日は以下のことを考えてみてください：",
        "",
        "- 新しいアイデア",
        "- 改善点",
        "- 楽しみたいこと",
        "",
        "---",
        "",
        "**使い方**: このプロンプトをレミに渡して、今日の計画を一緒に立てましょう。",
        ""
    ])

    return "\n".join(prompt_lines)


def handle_daily_consciousness_update(params_raw: Dict[str, Any]):
    """daily_consciousness_update: 三位一体モード（Brain + Market + Persona）"""
    from datetime import timedelta

    params = DailyConsciousnessUpdateParams(**params_raw)
    results = []
    errors = []

    # 日付の決定
    log_date = params.log_date or datetime.now().date().isoformat()
    date_obj = datetime.fromisoformat(log_date)

    # 1. dev_qa.md に追記
    if params.devqa_content:
        try:
            devqa_result = handle_github_update({
                "path": "docs/guides/dev_qa.md",
                "content_mode": "append",
                "append_text": params.devqa_content,
                "commit_message": f"Consciousness update: dev_qa ({log_date})"
            })
            results.append({"action": "dev_qa_update",
                           "status": "ok", **devqa_result})
        except Exception as e:
            errors.append(f"dev_qa update failed: {e}")
            results.append({"action": "dev_qa_update",
                           "status": "error", "error": str(e)})

    # 2. strategy.md に追記
    if params.strategy_content:
        try:
            strategy_result = handle_github_update({
                "path": "shared/strategy.md",
                "content_mode": "append",
                "append_text": params.strategy_content,
                "commit_message": f"Consciousness update: strategy ({log_date})"
            })
            results.append({"action": "strategy_update",
                           "status": "ok", **strategy_result})
        except Exception as e:
            errors.append(f"strategy update failed: {e}")
            results.append({"action": "strategy_update",
                           "status": "error", "error": str(e)})

    # 3. ローカルログに追記
    if params.log_content:
        try:
            log_result = handle_file_write({
                "relative_path": f"logs/daily-{log_date}.log",
                "content": params.log_content,
                "mode": "append"
            })
            results.append(
                {"action": "log_write", "status": "ok", **log_result})
        except Exception as e:
            errors.append(f"log write failed: {e}")
            results.append(
                {"action": "log_write", "status": "error", "error": str(e)})

    # 4. profit_ideas.md に追記（Market）- GitHub管理
    if params.profit_ideas:
        try:
            profit_content = f"\n\n## {log_date} 収益アイデア\n"
            for idea in params.profit_ideas:
                profit_content += f"- {idea}\n"
            profit_content += "\n"

            profit_result = handle_github_update({
                "path": "profit_ideas.md",
                "content_mode": "append",
                "append_text": profit_content,
                "commit_message": f"Consciousness update: profit ideas ({log_date})"
            })
            results.append({"action": "profit_ideas_update",
                           "status": "ok", **profit_result})
        except Exception as e:
            errors.append(f"profit_ideas update failed: {e}")
            results.append({"action": "profit_ideas_update",
                           "status": "error", "error": str(e)})

    # 5. self_review を生成・更新（Brain）
    try:
        # 週次レビューを生成（日曜日の場合、または手動実行時）
        if date_obj.weekday() == 6 or params.self_review_notes:  # 日曜日
            review_content = generate_self_review(log_date)
            if params.self_review_notes:
                review_content += f"\n\n## 追加メモ\n{params.self_review_notes}\n"

            # 週番号を計算
            week_num = date_obj.isocalendar()[1]
            review_result = handle_file_write({
                "relative_path": f"manaos_command_hub/summaries/self_review_2025-W{week_num:02d}.md",
                "content": review_content,
                "mode": "overwrite"
            })
            results.append({"action": "self_review_generate",
                           "status": "ok", **review_result})
    except Exception as e:
        errors.append(f"self_review generate failed: {e}")
        results.append({"action": "self_review_generate",
                       "status": "error", "error": str(e)})

    # 6. daily_prompt を生成（Persona）
    try:
        prompt_content = generate_daily_prompt(
            log_date, params.daily_prompt_context)
        prompt_result = handle_file_write({
            "relative_path": f"manaos_command_hub/prompts/daily_prompt_{log_date}.md",
            "content": prompt_content,
            "mode": "overwrite"
        })
        results.append({"action": "daily_prompt_generate",
                       "status": "ok", **prompt_result})
    except Exception as e:
        errors.append(f"daily_prompt generate failed: {e}")
        results.append({"action": "daily_prompt_generate",
                       "status": "error", "error": str(e)})

    # 結果をまとめる
    success_count = sum(1 for r in results if r.get("status") == "ok")
    total_count = len(results)

    return {
        "status": "ok" if success_count == total_count else "partial",
        "action": "daily_consciousness_update",
        "date": log_date,
        "modules": {
            "brain": any(r.get("action") == "self_review_generate" and r.get("status") == "ok" for r in results),
            "market": any(r.get("action") == "profit_ideas_update" and r.get("status") == "ok" for r in results),
            "persona": any(r.get("action") == "daily_prompt_generate" and r.get("status") == "ok" for r in results)
        },
        "results": results,
        "summary": {
            "total": total_count,
            "success": success_count,
            "errors": len(errors)
        },
        "errors": errors if errors else None
    }


def render_daily_prompt_text(prompt: DailyPrompt) -> str:
    """JSON → 人間向けテキストに変換"""
    lines: List[str] = []
    lines.append(f"# {prompt.date} のミッション")
    lines.append("")

    if prompt.top_tasks:
        for t in prompt.top_tasks:
            pri = t.priority
            title = t.title
            eta = t.estimated_time or "時間未設定"
            bt = {
                "morning": "朝",
                "afternoon": "昼",
                "evening": "夕方",
                "night": "夜",
                None: ""
            }[t.best_time]
            if bt:
                lines.append(f"【{pri}】{title}（{eta} / {bt}）")
            else:
                lines.append(f"【{pri}】{title}（{eta}）")
        lines.append("")

    if prompt.money_action:
        lines.append("💰 今日のお金になる一手")
        lines.append(f"- {prompt.money_action}")
        lines.append("")

    if prompt.reward_action:
        lines.append("🎁 今日のご褒美")
        lines.append(f"- {prompt.reward_action}")
        lines.append("")

    return "\n".join(lines)


def handle_daily_prompt_read(params_raw: Dict[str, Any]):
    """daily_prompt v2: マナ専用朝の司令塔 - JSON + 人間向けテキストの両対応"""
    from datetime import date, datetime

    params = DailyPromptReadParams(**params_raw)

    # 日付決定
    if params.date:
        try:
            target_date = date.fromisoformat(params.date)
        except Exception:
            raise HTTPException(
                status_code=400, detail="Invalid date format, expected YYYY-MM-DD")
    else:
        target_date = date.today()

    date_str = target_date.isoformat()

    # ① 既存のタスク3つを選ぶロジック（プロンプトファイルから抽出）
    prompt_file = BASE_WORKDIR / "manaos_command_hub" / \
        "prompts" / f"daily_prompt_{date_str}.md"

    raw_tasks = []
    today_goals = []

    if prompt_file.exists():
        content = prompt_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        current_section = None

        for line in lines:
            if "## 📅 今日の予定" in line:
                current_section = "tasks"
            elif "## 🎯 今日の目標" in line:
                current_section = "goals"
            elif current_section == "tasks" and line.strip().startswith("- [ ]"):
                task = line.strip().replace("- [ ]", "").strip()
                if task and task not in ["今日のタスク1", "今日のタスク2", "今日のタスク3"]:
                    raw_tasks.append(task)
            elif current_section == "goals" and line.strip().startswith("-"):
                goal = line.strip().replace("-", "").strip()
                if goal and goal not in ["目標1", "目標2"]:
                    today_goals.append(goal)

    # 昨日のログから「次どうするか」を推測
    if len(raw_tasks) < 3:
        yesterday = (target_date - timedelta(days=1)).isoformat()
        yesterday_log = BASE_WORKDIR / "logs" / f"daily-{yesterday}.log"
        if yesterday_log.exists():
            log_content = yesterday_log.read_text(encoding="utf-8")
            if "## 次どうするか" in log_content:
                next_section = log_content.split("## 次どうするか")[1].split("##")[0]
                for line in next_section.split("\n"):
                    if line.strip().startswith("- "):
                        task = line.strip()[2:]
                        if task and task not in raw_tasks:
                            raw_tasks.append(task)
                            if len(raw_tasks) >= 3:
                                break

    # デフォルトタスク
    if not raw_tasks:
        raw_tasks = [
            "今日のタスクを確認する",
            "daily_promptを更新する",
            "今日の学びを記録する"
        ]

    # ② priority / estimated_time / best_time を割り当て
    priorities = ["S", "A", "B"]
    best_times = ["morning", "afternoon", "night"]
    estimated_times = ["30min", "40min", "20min"]

    top_items: List[DailyTaskItem] = []
    for idx, title in enumerate(raw_tasks[:3]):
        pri = priorities[idx] if idx < len(priorities) else "B"
        bt = best_times[idx] if idx < len(best_times) else None
        eta = estimated_times[idx] if idx < len(estimated_times) else "30min"
        top_items.append(DailyTaskItem(
            title=title,
            priority=pri,
            estimated_time=eta,
            best_time=bt,
        ))

    # ③ お金になる一手（profit_ideas_analyze と連携）
    money_action: Optional[str] = None
    try:
        # profit_ideas_analyze を内部で呼び出し
        profit_result = handle_profit_ideas_analyze({
            "month": datetime.now().strftime("%Y-%m")
        })
        if profit_result.get("top_3") and len(profit_result["top_3"]) > 0:
            top_idea = profit_result["top_3"][0]
            idea_text = top_idea.get("idea", "")
            money_action = f"{idea_text}について、note向けアウトラインを書く"
    except Exception as e:
        logger.warning(f"Failed to get profit ideas for money_action: {e}")
        money_action = "profit_ideas の1位案について、note向けアウトラインを書く"

    # ④ ご褒美（マナ仕様）
    reward_options = [
        "今日のタスクが1つでも終わったら、ムフフ画像生成タイム15分",
        "今日のタスクが2つ終わったら、好きな動画1本見る",
        "今日のタスクが全部終わったら、高カロリー補給タイム",
        "今日のタスクが1つでも終わったら、ゲーム15分"
    ]
    reward_action = reward_options[0]  # デフォルトは最初のオプション

    # ⑤ DailyPrompt オブジェクトを作成
    prompt = DailyPrompt(
        date=date_str,
        top_tasks=top_items,
        money_action=money_action,
        reward_action=reward_action,
        text=""  # 一旦空で作って、あとで埋める
    )

    # テキストを生成
    prompt.text = render_daily_prompt_text(prompt)

    # JSON形式で返す（text も含む）
    return prompt.dict()


def handle_profit_ideas_analyze(params_raw: Dict[str, Any]):
    """profit_ideas自動分析: 今月の稼げそうTOP3を自動生成"""
    from datetime import date, datetime

    target_month = params_raw.get("month") or datetime.now().strftime("%Y-%m")

    # GitHubからprofit_ideas.mdを取得
    try:
        profit_ideas_result = handle_github_get({
            "path": "profit_ideas.md",
            "repo": "MRL-mana/manaos-knowledge",
            "branch": "main"
        })
        content = profit_ideas_result.get("content", "")
    except Exception as e:
        logger.warning(f"Failed to get profit_ideas from GitHub: {e}")
        content = ""

    # 今月のアイデアを抽出
    ideas = []
    current_date = None

    for line in content.split("\n"):
        if line.startswith("## ") and target_month in line:
            # 日付行を抽出
            date_match = line.split("## ")[1].strip()
            if date_match:
                current_date = date_match
        elif current_date and line.strip().startswith("- "):
            idea = line.strip()[2:]
            if idea:
                ideas.append({
                    "date": current_date,
                    "idea": idea
                })

    # アイデアを分析してTOP3を選ぶ（簡易版：最新順 + キーワード分析）
    # キーワードでスコアリング
    keywords_high_value = ["自動化", "テンプレ", "代行", "販売", "サービス", "パッケージ", "商材"]
    keywords_medium_value = ["改善", "効率化", "ノウハウ", "マニュアル"]

    scored_ideas = []
    for idea_item in ideas:
        score = 0
        idea_text = idea_item["idea"]

        # 高価値キーワード
        for keyword in keywords_high_value:
            if keyword in idea_text:
                score += 3

        # 中価値キーワード
        for keyword in keywords_medium_value:
            if keyword in idea_text:
                score += 1

        # 新しさボーナス（最近のアイデアほど高スコア）
        if idea_item["date"]:
            try:
                idea_date = datetime.fromisoformat(idea_item["date"]).date()
                days_ago = (date.today() - idea_date).days
                if days_ago <= 7:
                    score += 2
                elif days_ago <= 30:
                    score += 1
            except:
                pass

        scored_ideas.append({
            **idea_item,
            "score": score
        })

    # スコア順にソート
    scored_ideas.sort(key=lambda x: x["score"], reverse=True)

    # TOP3を選ぶ
    top_3 = scored_ideas[:3]

    # 分析結果を生成
    analysis = {
        "status": "ok",
        "action": "profit_ideas_analyze",
        "month": target_month,
        "total_ideas": len(ideas),
        "top_3": [
            {
                "rank": i + 1,
                "idea": item["idea"],
                "date": item["date"],
                "score": item["score"],
                "reason": f"スコア {item['score']}点（キーワード分析 + 新しさボーナス）"
            }
            for i, item in enumerate(top_3)
        ],
        "message": f"今月（{target_month}）の稼げそうTOP3：\n" + "\n".join([
            f"{i+1}. {item['idea']} (スコア: {item['score']})"
            for i, item in enumerate(top_3)
        ])
    }

    return analysis


def handle_antigravity_status(params_raw: Dict[str, Any]):
    """Antigravity IDEの状態を確認"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from commands.antigravity import antigravity_status
    result = antigravity_status()
    return {
        "status": "ok" if result["success"] else "error",
        "action": "antigravity_status",
        "output": result.get("output"),
        "error": result.get("error")
    }


def handle_antigravity_start(params_raw: Dict[str, Any]):
    """Antigravity IDEを起動"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from commands.antigravity import antigravity_start
    project_path = params_raw.get("project_path", "~")
    result = antigravity_start(project_path)
    return {
        "status": "ok" if result["success"] else "error",
        "action": "antigravity_start",
        "project_path": project_path,
        "output": result.get("output"),
        "error": result.get("error")
    }


def handle_antigravity_workflow(params_raw: Dict[str, Any]):
    """Antigravity IDEワークフローを実行"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from commands.antigravity import antigravity_workflow
    workflow_type = params_raw.get("workflow_type", "new_project")
    result = antigravity_workflow(workflow_type)
    return {
        "status": "ok" if result["success"] else "error",
        "action": "antigravity_workflow",
        "workflow_type": workflow_type,
        "output": result.get("output"),
        "error": result.get("error")
    }


def handle_antigravity_connect(params_raw: Dict[str, Any]):
    """Antigravity IDEに接続"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from commands.antigravity import antigravity_connect
    result = antigravity_connect()
    return {
        "status": "ok" if result["success"] else "error",
        "action": "antigravity_connect",
        "command": result.get("command"),
        "output": result.get("output"),
        "error": result.get("error")
    }


def handle_weekly_report_generate(params_raw: Dict[str, Any]):
    """週次レポート自動生成: 指定した週の daily log をまとめた週報 Markdown を作る"""
    from datetime import date, datetime, timedelta
    from collections import defaultdict

    params = WeeklyReportParams(**params_raw)

    # 対象週を決定（デフォルトは「今日が属するISO週」）
    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    year = params.iso_year or iso_year
    week = params.iso_week or iso_week

    # ISO週 → その週の月曜/日曜を求める
    week_start = date.fromisocalendar(year, week, 1)  # Monday
    week_end = date.fromisocalendar(year, week, 7)    # Sunday

    # 対象期間に対応する daily log を全部読む
    # daily-YYYY-MM.log (月単位) と daily-YYYY-MM-DD.log (日単位) の両方に対応
    LOG_BASE = BASE_WORKDIR / "logs"
    log_lines = []
    cur = week_start
    seen_files = set()

    while cur <= week_end:
        # 日単位のログファイルを優先的に探す
        daily_log_file = LOG_BASE / f"daily-{cur.isoformat()}.log"
        if daily_log_file.exists() and daily_log_file not in seen_files:
            seen_files.add(daily_log_file)
            with daily_log_file.open(encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if line.strip():  # 空行でない場合
                        # [YYYY-MM-DD] 形式の行があればそのまま、なければ日付を付与
                        if line.startswith("[") and "]" in line:
                            log_lines.append(line)
                        else:
                            # 日付がない場合は追加
                            log_lines.append(f"[{cur.isoformat()}] {line}")

        # 月単位のログファイルも探す（日単位がない場合のフォールバック）
        monthly_log_file = LOG_BASE / f"daily-{cur.year}-{cur.month:02d}.log"
        if monthly_log_file.exists() and monthly_log_file not in seen_files:
            seen_files.add(monthly_log_file)
            with monthly_log_file.open(encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    # 行頭が [YYYY-MM-DD] 形式なら、日付でフィルタ
                    if line.startswith("[") and "]" in line:
                        try:
                            d_str = line[1:11]  # "YYYY-MM-DD"
                            d = date.fromisoformat(d_str)
                        except Exception:
                            continue
                        if week_start <= d <= week_end:
                            log_lines.append(line)
        cur += timedelta(days=1)

    # Markdown生成
    generated_at = datetime.utcnow().isoformat() + "Z"
    report_lines = []
    report_lines.append(f"# Weekly Report {year}-W{week:02d}")
    report_lines.append(
        f"Period: {week_start.isoformat()} ～ {week_end.isoformat()}")
    report_lines.append(f"Generated at: {generated_at}")
    report_lines.append("")
    report_lines.append("## Daily Logs")
    report_lines.append("")

    if not log_lines:
        report_lines.append("_No logs found for this week._")
    else:
        # 日付ごとにグルーピング
        grouped = defaultdict(list)
        for line in log_lines:
            # "[YYYY-MM-DD] xxx" を分解
            try:
                d_str = line[1:11]
                rest = line[13:] if len(line) > 13 else ""
            except Exception:
                continue
            grouped[d_str].append(rest)

        for d_str in sorted(grouped.keys()):
            report_lines.append(f"- {d_str}")
            for item in grouped[d_str]:
                report_lines.append(f"    - {item}")
            report_lines.append("")

    # 将来の拡張用：dev_qa / strategy からの抜粋をここに追加してもOK
    report_lines.append("## Notes")
    report_lines.append(
        "- This report is generated from daily-YYYY-MM.log files.")
    report_lines.append("- dev_qa.md / strategy.md の詳細はGitHubの該当ファイルを参照。")
    report_lines.append("")

    content = "\n".join(report_lines)

    # 出力パス決定
    REPORT_BASE = BASE_WORKDIR / "manaos_command_hub" / "reports"
    REPORT_BASE.mkdir(parents=True, exist_ok=True)
    rel_path = params.output_path or f"manaos_command_hub/reports/weekly-{year}-W{week:02d}.md"

    fw_params = {
        "relative_path": rel_path,
        "content": content,
        "mode": "overwrite",
    }

    result = handle_file_write(fw_params)
    return {
        "status": "ok",
        "action": "weekly_report_generate",
        "iso_year": year,
        "iso_week": week,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "output_path": rel_path,
        "log_lines": len(log_lines),
        "file_write": result,
    }

# ======== メインエンドポイント =========


@app.get("/")
def root():
    return {
        "service": "manaOS Command Hub",
        "version": "1.0.0",
        "status": "running",
        "available_tasks": [
            "github_update_file",
            "github_get_file",
            "file_write",
            "image_job",
            "daily_reflection_bundle",
            "daily_consciousness_update",
            "daily_prompt_read",
            "profit_ideas_analyze",
            "weekly_report_generate"
        ],
        "dashboard": "/dashboard"
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """レミ用ダッシュボード - ブラウザで見れるmanaOSコックピット"""
    DASH_DIR = BASE_WORKDIR / "manaos_command_hub" / "dashboard"

    def read_file(p: str) -> str:
        f = DASH_DIR / p
        if f.exists():
            try:
                return f.read_text(encoding="utf-8")
            except Exception:
                return f"(読み込みエラー: {p})"
        return f"(まだ {p} が生成されていません)"

    today = read_file("today.md")
    status = read_file("status.md")
    money = read_file("money.md")
    weekly = read_file("weekly.md")

    # HTMLエスケープ
    def escape_html(text: str) -> str:
        return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))

    today_escaped = escape_html(today)
    status_escaped = escape_html(status)
    money_escaped = escape_html(money)
    weekly_escaped = escape_html(weekly)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>manaOS Dashboard</title>
      <style>
        * {{
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }}
        body {{
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
          background: #0b1020;
          color: #f5f5f5;
          padding: 20px;
          line-height: 1.6;
        }}
        h1 {{
          color: #ffd86b;
          margin-bottom: 10px;
          font-size: 2em;
        }}
        h2 {{
          color: #ffd86b;
          margin-bottom: 12px;
          font-size: 1.3em;
          border-bottom: 2px solid #ffd86b;
          padding-bottom: 8px;
        }}
        .header {{
          margin-bottom: 24px;
        }}
        .timestamp {{
          color: #888;
          font-size: 0.9em;
        }}
        pre {{
          background: #111827;
          padding: 16px;
          border-radius: 8px;
          white-space: pre-wrap;
          overflow-x: auto;
          font-size: 0.9em;
          line-height: 1.5;
        }}
        .grid {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 20px;
        }}
        .card {{
          border-radius: 12px;
          padding: 20px;
          background: #020617;
          box-shadow: 0 4px 12px rgba(0,0,0,0.4);
          border: 1px solid #1e293b;
        }}
        .card:hover {{
          border-color: #ffd86b;
          transition: border-color 0.3s;
        }}
        @media (max-width: 768px) {{
          .grid {{
            grid-template-columns: 1fr;
          }}
        }}
      </style>
    </head>
    <body>
      <div class="header">
        <h1>🛸 manaOS Dashboard</h1>
        <div class="timestamp">最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
      </div>
      <div class="grid">
        <div class="card">
          <h2>📋 今日のミッション</h2>
          <pre>{today_escaped}</pre>
        </div>
        <div class="card">
          <h2>💻 システム状態</h2>
          <pre>{status_escaped}</pre>
        </div>
        <div class="card">
          <h2>💰 今月の金脈 / Profit Ideas</h2>
          <pre>{money_escaped}</pre>
        </div>
        <div class="card">
          <h2>📊 最新Weekly Report</h2>
          <pre>{weekly_escaped}</pre>
        </div>
      </div>
    </body>
    </html>
    """
    return html


def load_stats():
    """統計情報を読み込む"""
    if _stats_file.exists():
        try:
            with open(_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _stats.update(data)
        except Exception as e:
            logger.warning(f"Failed to load stats: {e}")


def save_stats():
    """統計情報を保存"""
    try:
        _stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(_stats_file, 'w', encoding='utf-8') as f:
            json.dump(dict(_stats), f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save stats: {e}")


def increment_stat(key: str):
    """統計カウンタを増やす"""
    _stats[key] += 1
    save_stats()


# 起動時に統計を読み込む
load_stats()


@app.get("/health")
def health():
    """ヘルスチェック（強化版）"""
    today = datetime.now().date().isoformat()
    today_success = _stats.get(f"success_{today}", 0)
    today_failures = _stats.get(f"failure_{today}", 0)
    today_total = today_success + today_failures
    success_rate = (today_success / today_total *
                    100) if today_total > 0 else 100.0

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "stats": {
            "today": {
                "total": today_total,
                "success": today_success,
                "failures": today_failures,
                "success_rate": round(success_rate, 2)
            },
            "all_time": {
                "total": _stats.get("total_commands", 0),
                "success": _stats.get("total_success", 0),
                "failures": _stats.get("total_failures", 0)
            }
        }
    }


@app.post("/command")
def handle_command(cmd: Command):
    logger.info(f"Command received: {cmd.task} from {cmd.meta.caller}")
    increment_stat("total_commands")
    today = datetime.now().date().isoformat()

    verify_auth(cmd.auth_token)

    try:
        result = None
        if cmd.task == "github_update_file":
            result = handle_github_update(cmd.params)
        elif cmd.task == "github_get_file":
            result = handle_github_get(cmd.params)
        elif cmd.task == "file_write":
            result = handle_file_write(cmd.params)
        elif cmd.task == "image_job":
            result = handle_image_job(cmd.params)
        elif cmd.task == "daily_reflection_bundle":
            result = handle_daily_reflection_bundle(cmd.params)
        elif cmd.task == "daily_consciousness_update":
            result = handle_daily_consciousness_update(cmd.params)
        elif cmd.task == "daily_prompt_read":
            result = handle_daily_prompt_read(cmd.params)
        elif cmd.task == "profit_ideas_analyze":
            result = handle_profit_ideas_analyze(cmd.params)
        elif cmd.task == "weekly_report_generate":
            result = handle_weekly_report_generate(cmd.params)
        elif cmd.task == "antigravity_status":
            result = handle_antigravity_status(cmd.params)
        elif cmd.task == "antigravity_start":
            result = handle_antigravity_start(cmd.params)
        elif cmd.task == "antigravity_workflow":
            result = handle_antigravity_workflow(cmd.params)
        elif cmd.task == "antigravity_connect":
            result = handle_antigravity_connect(cmd.params)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown task: {cmd.task}")

        # 成功カウント
        increment_stat("total_success")
        increment_stat(f"success_{today}")
        logger.info(f"✅ Command succeeded: {cmd.task}")
        return result

    except HTTPException as e:
        # HTTP例外は失敗としてカウント
        increment_stat("total_failures")
        increment_stat(f"failure_{today}")
        logger.error(
            f"❌ Command failed: {cmd.task} - {e.detail}", exc_info=True)
        raise
    except Exception as e:
        # 予期しないエラー
        increment_stat("total_failures")
        increment_stat(f"failure_{today}")
        logger.error(
            f"❌ Command execution failed: {cmd.task} - {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Command execution failed: {e}")


# ======== Weaviate記憶検索API =========

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_CLASS_NAME = "ManaOSMemory"


class MemorySearchParams(BaseModel):
    query: str = Field(..., description="検索クエリ")
    limit: int = Field(10, ge=1, le=100, description="結果数上限")
    source: Optional[str] = Field(
        None, description="データソース（obsidian/drive/logs）")


@app.post("/api/memory/search")
def search_memory(params: MemorySearchParams):
    """記憶検索API（Weaviate）"""
    try:
        # Weaviateで検索
        search_params = {
            "class": WEAVIATE_CLASS_NAME,
            "limit": params.limit
        }

        if params.source:
            # ソースでフィルタリング
            where_filter = {
                "path": ["source"],
                "operator": "Equal",
                "valueString": params.source
            }
            search_params["where"] = where_filter

        # まず全オブジェクトを取得（簡易版、後でベクトル検索に置き換え）
        response = requests.get(
            f"{WEAVIATE_URL}/v1/objects",
            params=search_params,
            timeout=10
        )

        if response.status_code != 200:
            logger.error(
                f"Weaviate search failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500, detail="Weaviate search failed")

        objects = response.json().get("objects", [])

        # クエリでフィルタリング（簡易版、後でベクトル検索に置き換え）
        results = []
        query_lower = params.query.lower()

        for obj in objects:
            props = obj.get("properties", {})
            content = props.get("content", "").lower()

            if query_lower in content:
                results.append({
                    "id": obj.get("id"),
                    "content": props.get("content", "")[:500],  # 最初の500文字
                    "source": props.get("source"),
                    "file_path": props.get("file_path"),
                    "timestamp": props.get("timestamp"),
                    "tags": props.get("tags", [])
                })

        # 関連度順にソート（簡易版）
        results = sorted(
            results,
            key=lambda x: query_lower.count(x["content"].lower()),
            reverse=True
        )[:params.limit]

        return {
            "status": "ok",
            "query": params.query,
            "count": len(results),
            "results": results
        }

    except requests.RequestException as e:
        logger.error(f"Weaviate connection error: {e}")
        raise HTTPException(
            status_code=503, detail=f"Weaviate connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/stats")
def get_memory_stats():
    """Weaviate統計情報"""
    try:
        response = requests.get(
            f"{WEAVIATE_URL}/v1/schema/{WEAVIATE_CLASS_NAME}",
            timeout=10
        )

        if response.status_code == 200:
            # オブジェクト数を取得（簡易版）
            count_response = requests.get(
                f"{WEAVIATE_URL}/v1/objects",
                params={"class": WEAVIATE_CLASS_NAME, "limit": 1},
                timeout=10
            )

            return {
                "status": "ok",
                "class_name": WEAVIATE_CLASS_NAME,
                "weaviate_status": "active",
                "weaviate_url": WEAVIATE_URL
            }
        else:
            return {
                "status": "ok",
                "class_name": WEAVIATE_CLASS_NAME,
                "weaviate_status": "inactive",
                "error": "Class not found"
            }

    except requests.RequestException as e:
        logger.error(f"Weaviate connection error: {e}")
        return {
            "status": "error",
            "error": f"Weaviate connection error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Memory stats error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/api/memory/health")
def memory_health_check():
    """Weaviateヘルスチェック"""
    try:
        response = requests.get(
            f"{WEAVIATE_URL}/v1/.well-known/ready",
            timeout=5
        )
        if response.status_code == 200:
            return {"status": "healthy", "weaviate_url": WEAVIATE_URL}
        else:
            return {"status": "unhealthy"}, 503
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503


# ========== レミ用Control API ==========
# レミがマナOSを直接操作するためのエンドポイント

# 許可されたサービス一覧（安全な操作のみ）
ALLOWED_SERVICES = {
    "n8n": "systemctl restart n8n",
    "sd-webui": "systemctl restart sd-webui",
    "mana-intent": "systemctl restart mana-intent",
    "manaos-command-hub": "systemctl restart manaos-command-hub",
    "mana-ocr-api": "systemctl restart mana-ocr-api",
}

# n8nワークフローWebhook URL（環境変数から取得、デフォルトはlocalhost）
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
N8N_WEBHOOKS = {
    "pdf_to_excel": f"{N8N_BASE_URL}/webhook/pdf-to-excel",
    "daily_report": f"{N8N_BASE_URL}/webhook/daily-report",
    "image_generation": f"{N8N_BASE_URL}/webhook/image-generation",
}


def verify_remi_auth(auth_token: Optional[str] = Header(None, alias="X-Auth-Token")):
    """レミ用APIの認証チェック"""
    if not auth_token or auth_token != COMMAND_HUB_TOKEN:
        raise HTTPException(
            status_code=401, detail="Invalid or missing auth token")
    return auth_token


@app.get("/remi/status")
def remi_status(auth: str = Depends(verify_remi_auth)):
    """
    レミ用：マナOSの状態確認
    サービス一覧、CPU/メモリ、成功率を返す
    """
    result = {
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "system": {},
        "command_hub": {}
    }

    # 1. サービス状態確認
    for service_name in ALLOWED_SERVICES.keys():
        try:
            # systemctl is-active で状態確認
            proc = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=3
            )
            status = proc.stdout.strip()
            result["services"][service_name] = {
                "status": status,
                "active": status == "active"
            }
        except Exception as e:
            result["services"][service_name] = {
                "status": "unknown",
                "active": False,
                "error": str(e)
            }

    # 2. システムリソース（psutil使用）
    if PSUTIL_AVAILABLE:
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            result["system"] = {
                "cpu_percent": cpu,
                "memory": {
                    "total_gb": round(mem.total / (1024**3), 2),
                    "used_gb": round(mem.used / (1024**3), 2),
                    "percent": mem.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent": disk.percent
                }
            }
        except Exception as e:
            result["system"]["error"] = str(e)
    else:
        result["system"]["error"] = "psutil not available"

    # 3. Command Hubの統計
    today = datetime.now().date().isoformat()
    today_success = _stats.get(f"success_{today}", 0)
    today_failures = _stats.get(f"failure_{today}", 0)
    today_total = today_success + today_failures
    success_rate = (today_success / today_total *
                    100) if today_total > 0 else 100.0

    result["command_hub"] = {
        "status": "healthy",
        "stats": {
            "today": {
                "total": today_total,
                "success": today_success,
                "failures": today_failures,
                "success_rate": round(success_rate, 2)
            }
        }
    }

    return result


@app.post("/remi/restart/{service_name}")
def remi_restart_service(service_name: str, auth: str = Depends(verify_remi_auth)):
    """
    レミ用：安全なサービス再起動
    許可されたサービスのみ再起動可能
    """
    if service_name not in ALLOWED_SERVICES:
        raise HTTPException(
            status_code=403,
            detail=f"Service '{service_name}' is not allowed. Allowed services: {list(ALLOWED_SERVICES.keys())}"
        )

    try:
        cmd = ALLOWED_SERVICES[service_name].split()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if proc.returncode == 0:
            logger.info(f"✅ Remi restarted service: {service_name}")
            return {
                "ok": True,
                "service": service_name,
                "command": " ".join(cmd),
                "message": f"Service '{service_name}' restarted successfully"
            }
        else:
            logger.error(f"❌ Failed to restart {service_name}: {proc.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to restart service: {proc.stderr}"
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Service restart timeout")
    except Exception as e:
        logger.error(f"❌ Error restarting {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/run/{workflow}")
def remi_run_workflow(workflow: str, auth: str = Depends(verify_remi_auth)):
    """
    レミ用：n8nワークフロー実行
    許可されたワークフローのみ実行可能
    """
    if workflow not in N8N_WEBHOOKS:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow}' not found. Available workflows: {list(N8N_WEBHOOKS.keys())}"
        )

    webhook_url = N8N_WEBHOOKS[workflow]

    try:
        response = requests.post(
            webhook_url,
            json={"trigger": "remi", "timestamp": datetime.now().isoformat()},
            timeout=60
        )
        response.raise_for_status()

        logger.info(f"✅ Remi triggered workflow: {workflow}")
        return {
            "ok": True,
            "workflow": workflow,
            "webhook_url": webhook_url,
            "status_code": response.status_code,
            "message": f"Workflow '{workflow}' triggered successfully"
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to trigger workflow {workflow}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger workflow: {str(e)}"
        )


@app.get("/remi/logs/{service}")
def remi_get_logs(service: str, lines: int = 50, auth: str = Depends(verify_remi_auth)):
    """
    レミ用：ログ確認
    特定サービスのログを取得
    """
    # ログファイルのパスマッピング
    LOG_PATHS = {
        "command-hub": BASE_WORKDIR / "manaos_command_hub" / "logs" / "hub.log",
        "error": BASE_WORKDIR / "manaos_command_hub" / "logs" / f"error-{datetime.now().strftime('%Y-%m')}.log",
        "daily": BASE_WORKDIR / "manaos_command_hub" / "logs" / f"daily-{datetime.now().strftime('%Y-%m-%d')}.log",
    }

    # systemdサービスのログも取得可能
    if service.startswith("systemd:"):
        service_name = service.replace("systemd:", "")
        try:
            proc = subprocess.run(
                ["journalctl", "-u", service_name,
                    "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if proc.returncode == 0:
                return {
                    "ok": True,
                    "service": service_name,
                    "source": "systemd",
                    "lines": lines,
                    "log": proc.stdout
                }
            else:
                raise HTTPException(
                    status_code=404, detail=f"Service '{service_name}' not found in systemd")
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=504, detail="Log retrieval timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ファイルベースのログ
    if service not in LOG_PATHS:
        raise HTTPException(
            status_code=404,
            detail=f"Log source '{service}' not found. Available: {list(LOG_PATHS.keys())} or systemd:SERVICE_NAME"
        )

    log_path = LOG_PATHS[service]

    if not log_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Log file not found: {log_path}")

    try:
        # tail -n で最新N行を取得
        proc = subprocess.run(
            ["tail", "-n", str(lines), str(log_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if proc.returncode == 0:
            return {
                "ok": True,
                "service": service,
                "source": "file",
                "path": str(log_path),
                "lines": lines,
                "log": proc.stdout
            }
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to read log: {proc.stderr}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Log retrieval timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/dashboard/update")
def remi_update_dashboard(auth: str = Depends(verify_remi_auth)):
    """
    レミ用：ダッシュボード更新
    today.md, status.md を手動更新
    """
    try:
        # status.md を更新（status_report.pyを実行）
        status_script = BASE_WORKDIR / "manaos_command_hub" / "status_report.py"
        if status_script.exists():
            proc = subprocess.run(
                [sys.executable, str(status_script)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(status_script.parent)
            )
            if proc.returncode == 0:
                status_output = proc.stdout
                dash_dir = BASE_WORKDIR / "manaos_command_hub" / "dashboard"
                dash_dir.mkdir(parents=True, exist_ok=True)
                (dash_dir / "status.md").write_text(status_output, encoding="utf-8")
            else:
                logger.warning(f"status_report.py failed: {proc.stderr}")

        # today.md を更新（daily_prompt_readを実行）
        send_cmd_script = BASE_WORKDIR / "manaos_command_hub" / "send_command.py"
        cmd_file = BASE_WORKDIR / "manaos_command_hub" / \
            "commands" / "command-daily-prompt-read.json"
        if send_cmd_script.exists() and cmd_file.exists():
            proc = subprocess.run(
                [sys.executable, str(send_cmd_script), str(cmd_file)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(send_cmd_script.parent)
            )
            if proc.returncode == 0:
                try:
                    result_json = json.loads(proc.stdout)
                    text_content = result_json.get("text", "")
                    if text_content:
                        dash_dir = BASE_WORKDIR / "manaos_command_hub" / "dashboard"
                        dash_dir.mkdir(parents=True, exist_ok=True)
                        (dash_dir / "today.md").write_text(text_content, encoding="utf-8")
                except json.JSONDecodeError:
                    logger.warning("Failed to parse daily_prompt_read output")

        logger.info("✅ Remi updated dashboard")
        return {
            "ok": True,
            "message": "Dashboard updated successfully",
            "updated_files": ["status.md", "today.md"]
        }
    except Exception as e:
        logger.error(f"❌ Failed to update dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9404)
