#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💬 File Secretary - Slack返信テンプレート
コマンド文言と返信テンプレートの定義
"""

from typing import Dict, List, Any, Optional


# トリガー語彙
TRIGGER_COMMANDS = {
    "done": ["終わった", "完了", "done", "おわり", "終了"],
    "skip": ["今日は放置", "放置", "skip", "あとで", "後で"],
    "status": ["Inboxどう？", "状況", "status", "一覧", "どう？"],
    "restore": ["戻して", "復元", "restore", "undo", "元に戻して"],
    "search": ["探して", "検索", "search", "find", "見つけて"]
}


def parse_command(text: str) -> Optional[str]:
    """
    コマンドを解析してタイプを返す
    
    Args:
        text: 入力テキスト
        
    Returns:
        コマンドタイプ（done/skip/status/restore/search）またはNone
    """
    text_lower = text.lower().strip()
    
    for cmd_type, keywords in TRIGGER_COMMANDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return cmd_type
    
    return None


def extract_search_query(text: str) -> Optional[str]:
    """
    「探して：◯◯」から検索クエリを抽出
    
    Args:
        text: 入力テキスト
        
    Returns:
        検索クエリまたはNone
    """
    text_lower = text.lower()
    
    # 「探して：」「検索：」などのパターンを探す
    separators = ["探して：", "探して:", "検索：", "検索:", "find:", "search:"]
    
    for sep in separators:
        if sep.lower() in text_lower:
            idx = text_lower.index(sep.lower())
            query = text[idx + len(sep):].strip()
            if query:
                return query
    
    # 「探して」だけの場合は、その後の文字列を取得
    if "探して" in text or "検索" in text:
        parts = text.split("：") if "：" in text else text.split(":")
        if len(parts) > 1:
            return parts[1].strip()
    
    return None


# 返信テンプレート関数

def template_new_files(count: int, types: Dict[str, int]) -> str:
    """
    INBOX新規ファイル検知の返信
    
    Args:
        count: 新規ファイル数
        types: タイプ別カウント（例: {"pdf": 2, "image": 1}）
        
    Returns:
        返信テキスト
    """
    type_str = " / ".join([f"{k}{v}" for k, v in types.items()])
    return f"INBOXに{count}件入ったよ（{type_str}）\n必要なら「Inboxどう？」で一覧出す"


def template_inbox_status(
    new_count: int,
    old_count: int,
    long_term_count: int,
    summary: str,
    candidates: List[Dict[str, Any]],
    action_b: str = "日報だけ把握",
    action_c: str = "最新3件だけ整理"
) -> str:
    """
    「Inboxどう？」返信
    
    Args:
        new_count: 新規ファイル数（24h以内）
        old_count: 未処理ファイル数（7日以上）
        long_term_count: 長期未処理ファイル数
        summary: ざっくりサマリ（例: "日報っぽい5、画像素材4、その他3"）
        candidates: 候補ファイルリスト
        action_b: 選択肢Bのテキスト
        action_c: 選択肢Cのテキスト
        
    Returns:
        返信テキスト
    """
    lines = [
        f"INBOX状況：新規{new_count} / 未処理{old_count}（長期{long_term_count}）",
        f"ざっくり：{summary}",
        "候補："
    ]
    
    for cand in candidates[:3]:  # 最大3件
        name = cand.get("alias_name") or cand.get("original_name", "不明")
        tags_str = "、".join(cand.get("tags", [])) if cand.get("tags") else "タグなし"
        lines.append(f"・{name}（{tags_str}）")
    
    lines.append(f"\nA 放置 / B {action_b} / C {action_c}")
    
    return "\n".join(lines)


def template_done(organized_files: List[Dict[str, Any]]) -> str:
    """
    「終わった」実行完了の返信
    
    Args:
        organized_files: 整理されたファイルリスト
        
    Returns:
        返信テキスト
    """
    lines = [f"整理したよ：{len(organized_files)}件"]
    
    for file_info in organized_files:
        alias = file_info.get("alias_name", "不明")
        original = file_info.get("original_name", "不明")
        lines.append(f"・`{alias}`（元：{original}）")
    
    lines.append("\n違ったら「戻して」でOK")
    
    return "\n".join(lines)


def template_restore(restored_files: List[Dict[str, Any]]) -> str:
    """
    「戻して」復元完了の返信
    
    Args:
        restored_files: 復元されたファイルリスト
        
    Returns:
        返信テキスト
    """
    lines = [f"復元したよ：{len(restored_files)}件"]
    
    for file_info in restored_files:
        name = file_info.get("alias_name") or file_info.get("original_name", "不明")
        lines.append(f"・{name}")
    
    lines.append("\nINBOXに戻したから、また整理できるよ")
    
    return "\n".join(lines)


def template_search(query: str, results: List[Dict[str, Any]]) -> str:
    """
    「探して：◯◯」検索結果の返信
    
    Args:
        query: 検索クエリ
        results: 検索結果リスト
        
    Returns:
        返信テキスト
    """
    lines = [f"「{query}」で{len(results)}件見つかったよ"]
    
    for result in results[:5]:  # 最大5件
        name = result.get("alias_name") or result.get("original_name", "不明")
        summary = result.get("summary", "")
        if summary:
            lines.append(f"・{name}（{summary}）")
        else:
            lines.append(f"・{name}")
    
    if len(results) > 5:
        lines.append(f"（他{len(results) - 5}件）")
    
    lines.append("\nA 詳細見る / B 整理する / C 放置")
    
    return "\n".join(lines)


def template_error(reason: str) -> str:
    """
    エラー・不明なコマンドの返信
    
    Args:
        reason: エラー理由
        
    Returns:
        返信テキスト
    """
    return f"""ごめん、{reason}
使えるコマンド：
・「Inboxどう？」：状況確認
・「終わった」：整理実行
・「戻して」：復元
・「探して：◯◯」：検索"""


def template_unknown_command() -> str:
    """不明なコマンドの返信"""
    return template_error("そのコマンドは分からなかった")


