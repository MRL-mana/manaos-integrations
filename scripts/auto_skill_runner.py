#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills自動実行スクリプト
AIにYAML生成を依頼し、自動的に処理を実行する
"""

import os
import sys
import json
import yaml
import subprocess
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

project_root = Path(__file__).parent.parent
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

# プロジェクトルートをパスに追加
sys.path.insert(0, str(project_root))

# LLM統合を試行
LLM_AVAILABLE = False
try:
    from local_llm_helper import chat as ollama_chat
    LLM_AVAILABLE = True
    LLM_TYPE = "ollama"
except ImportError:
    try:
        # unified_api_server経由を試行
        LLM_TYPE = "api"
    except Exception:
        LLM_TYPE = None

# Skillsマッピング（全14個のSkillsに対応）
SKILLS_MAP = {
    "daily_ops": {
        "script": "apply_skill_daily_ops.py",
        "prompt_template": "今日の日報をYAML形式で出力してください。daily_ops Skillのフォーマットに従ってください。日付は{date}です。"
    },
    "git_ops": {
        "script": "apply_skill_git_ops.py",
        "prompt_template": "Gitの状態を確認するYAMLを出力してください。git_ops Skillのフォーマットに従ってください。"
    },
    "log_analysis": {
        "script": "apply_skill_log_analysis.py",
        "prompt_template": "ログファイルを分析するYAMLを出力してください。log_analysis Skillのフォーマットに従ってください。ログファイルパス: {log_file}"
    },
    "file_organize": {
        "script": "apply_skill_file_organize.py",
        "prompt_template": "ファイル整理のYAMLを出力してください。file_organize Skillのフォーマットに従ってください。"
    },
    "data_transform": {
        "script": "apply_skill_data_transform.py",
        "prompt_template": "データ変換のYAMLを出力してください。data_transform Skillのフォーマットに従ってください。"
    },
    "notion_ops": {
        "script": "apply_skill_notion_ops.py",
        "prompt_template": "Notion操作のYAMLを出力してください。notion_ops Skillのフォーマットに従ってください。"
    },
    "server_monitor": {
        "script": "apply_skill_server_monitor.py",
        "prompt_template": "サーバー監視のYAMLを出力してください。server_monitor Skillのフォーマットに従ってください。"
    },
    "database_ops": {
        "script": "apply_skill_database_ops.py",
        "prompt_template": "データベース操作のYAMLを出力してください。database_ops Skillのフォーマットに従ってください。"
    },
    "rows_ops": {
        "script": "apply_skill_rows_ops.py",
        "prompt_template": "Rows操作のYAMLを出力してください。rows_ops Skillのフォーマットに従ってください。"
    },
    "email_ops": {
        "script": "apply_skill_email_ops.py",
        "prompt_template": "メール送信のYAMLを出力してください。email_ops Skillのフォーマットに従ってください。"
    },
    "calendar_ops": {
        "script": "apply_skill_calendar_ops.py",
        "prompt_template": "カレンダー操作のYAMLを出力してください。calendar_ops Skillのフォーマットに従ってください。"
    },
    "db_backup": {
        "script": "apply_skill_db_backup.py",
        "prompt_template": "データベースバックアップのYAMLを出力してください。db_backup Skillのフォーマットに従ってください。"
    },
    "n8n_workflow": {
        "script": "apply_skill_n8n_workflow.py",
        "prompt_template": "n8nワークフロー操作のYAMLを出力してください。n8n_workflow Skillのフォーマットに従ってください。"
    },
    "drive_backup": {
        "script": "apply_skill_drive_backup.py",
        "prompt_template": "Google DriveバックアップのYAMLを出力してください。drive_backup Skillのフォーマットに従ってください。"
    }
}


def extract_yaml_from_response(response_text: str) -> Optional[str]:
    """レスポンスからYAMLを抽出"""
    # ```yaml と ``` で囲まれた部分を抽出
    yaml_pattern = r'```yaml\s*\n(.*?)\n```'
    match = re.search(yaml_pattern, response_text, re.DOTALL)
    if match:
        return match.group(1)
    
    # ``` のみで囲まれた部分を抽出
    code_pattern = r'```\s*\n(.*?)\n```'
    match = re.search(code_pattern, response_text, re.DOTALL)
    if match:
        content = match.group(1)
        # YAMLっぽいかチェック（kind: で始まるなど）
        if 'kind:' in content:
            return content
    
    # YAMLっぽい部分を直接抽出
    if 'kind:' in response_text:
        lines = response_text.split('\n')
        yaml_lines = []
        in_yaml = False
        for line in lines:
            if 'kind:' in line:
                in_yaml = True
            if in_yaml:
                yaml_lines.append(line)
                # 空行が2つ続いたら終了
                if line.strip() == '' and len(yaml_lines) > 1 and yaml_lines[-2].strip() == '':
                    break
        
        if yaml_lines:
            return '\n'.join(yaml_lines)
    
    return None


def call_llm_api(prompt: str) -> Optional[str]:
    """LLM APIを呼び出してYAMLを生成"""
    # 方法1: local_llm_helper経由（Ollama）
    if LLM_AVAILABLE and LLM_TYPE == "ollama":
        try:
            print("🤖 Ollama経由でLLMを呼び出し中...")
            response = ollama_chat(
                model="qwen3:4b",
                message=prompt,
                timeout=120
            )
            
            if "error" in response:
                print(f"⚠️  Ollamaエラー: {response.get('error')}")
                return None
            
            return response.get("message", {}).get("content", "")
        except Exception as e:
            print(f"⚠️  Ollama呼び出しエラー: {e}")
    
    # 方法2: unified_api_server経由
    try:
        print("🤖 unified_api_server経由でLLMを呼び出し中...")
        api_url = os.getenv("UNIFIED_API_SERVER_URL", "http://127.0.0.1:9510")
        response = requests.post(
            f"{api_url}/api/lfm25/chat",
            json={
                "message": prompt,
                "task_type": "conversation"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "")
        else:
            print(f"⚠️  APIエラー: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  API呼び出しエラー: {e}")
    
    return None


def generate_yaml_with_ai(skill_name: str, **kwargs) -> Optional[Path]:
    """
    AIにYAML生成を依頼（完全自動版：LLM API統合）
    """
    if skill_name not in SKILLS_MAP:
        print(f"❌ 不明なSkill: {skill_name}")
        return None
    
    skill_info = SKILLS_MAP[skill_name]
    
    # テンプレートからプロンプトを生成
    prompt = skill_info["prompt_template"].format(**kwargs)
    
    # Skillsファイルの内容をプロンプトに追加（より正確なYAML生成のため）
    skill_file = project_root / "skills" / f"{skill_name}_skill.mdc"
    if skill_file.exists():
        with open(skill_file, 'r', encoding='utf-8') as f:
            skill_content = f.read()
            # YAMLフォーマット部分を抽出
            if "```yaml" in skill_content:
                yaml_example = skill_content.split("```yaml")[1].split("```")[0]
                prompt += f"\n\n以下のフォーマットに従ってください：\n```yaml{yaml_example}```"
    
    print(f"📝 AIにYAML生成を依頼: {skill_name}")
    print(f"   プロンプト: {prompt[:200]}...")
    
    # LLM APIを呼び出し
    response_text = call_llm_api(prompt)
    
    if not response_text:
        print("⚠️  LLM API呼び出しに失敗。テンプレートベースで生成します。")
        yaml_content = generate_sample_yaml(skill_name, **kwargs)
    else:
        # レスポンスからYAMLを抽出
        yaml_content = extract_yaml_from_response(response_text)
        
        if not yaml_content:
            print("⚠️  YAML抽出に失敗。テンプレートベースで生成します。")
            yaml_content = generate_sample_yaml(skill_name, **kwargs)
        else:
            print("✅ LLMからYAMLを取得しました")
    
    if not yaml_content:
        return None
    
    # YAMLファイルを保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    yaml_file = ARTIFACTS_DIR / f"{skill_name}_{timestamp}.yaml"
    
    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    
    print(f"✅ YAMLファイルを生成: {yaml_file}")
    return yaml_file


def generate_sample_yaml(skill_name: str, **kwargs) -> Optional[str]:
    """サンプルYAMLを生成（実際の実装ではLLM APIから取得）"""
    if skill_name == "daily_ops":
        date = kwargs.get("date", datetime.now().strftime("%Y-%m-%d"))
        return f"""kind: daily_ops
date: {date}
title: "日報"
tags: ["ops", "manaos"]
summary: "今日の作業内容"
tasks:
  - title: "タスク1"
    status: todo
    priority: high
notify:
  slack: false
  obsidian: true
idempotency_key: "daily_ops_{date}"
"""
    elif skill_name == "git_ops":
        return """kind: git_ops
action: status
repository_path: "."
idempotency_key: "git_status_auto"
"""
    elif skill_name == "log_analysis":
        log_file = kwargs.get("log_file", "logs/app.log")
        return f"""kind: log_analysis
action: analyze
log_file: "{log_file}"
analysis_type: "error_summary"
output_format: "markdown"
output_path: "reports/log_analysis_auto.md"
notify:
  slack: false
idempotency_key: "log_analysis_auto"
"""
    return None


def execute_skill(skill_name: str, yaml_file: Path) -> bool:
    """Skillスクリプトを実行"""
    if skill_name not in SKILLS_MAP:
        print(f"❌ 不明なSkill: {skill_name}")
        return False
    
    script_name = SKILLS_MAP[skill_name]["script"]
    script_path = project_root / "scripts" / script_name
    
    if not script_path.exists():
        print(f"❌ スクリプトが見つかりません: {script_path}")
        return False
    
    try:
        print(f"🚀 Skillを実行: {skill_name}")
        result = subprocess.run(
            [sys.executable, str(script_path), str(yaml_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Skill実行成功: {skill_name}")
            print(result.stdout)
            return True
        else:
            print(f"❌ Skill実行失敗: {skill_name}")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Skill実行エラー: {e}")
        return False


def auto_run_skill(skill_name: str, **kwargs) -> bool:
    """Skillを自動実行（YAML生成→処理実行）"""
    print(f"\n🤖 自動実行開始: {skill_name}")
    
    # 1. AIにYAML生成を依頼
    yaml_file = generate_yaml_with_ai(skill_name, **kwargs)
    if not yaml_file:
        print(f"❌ YAML生成に失敗: {skill_name}")
        return False
    
    # 2. Skillスクリプトを実行
    success = execute_skill(skill_name, yaml_file)
    
    if success:
        print(f"✅ 自動実行完了: {skill_name}")
    else:
        print(f"❌ 自動実行失敗: {skill_name}")
    
    return success


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法: python auto_skill_runner.py <skill_name> [args...]")
        print("\n利用可能なSkills:")
        for skill_name in SKILLS_MAP.keys():
            print(f"  - {skill_name}")
        sys.exit(1)
    
    skill_name = sys.argv[1]
    kwargs = {}
    
    # 追加引数を解析
    for i in range(2, len(sys.argv), 2):
        if i + 1 < len(sys.argv):
            key = sys.argv[i].lstrip("-")
            value = sys.argv[i + 1]
            kwargs[key] = value
    
    success = auto_run_skill(skill_name, **kwargs)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
