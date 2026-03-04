#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メール送信処理スクリプト
YAML形式のメール送信設定を読み込み、メールを送信
"""

import os
import sys
import json
import yaml
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_email_ops_history.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_history() -> Dict[str, Any]:
    """処理履歴を読み込む"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  履歴ファイルの読み込みエラー: {e}")
    return {"processed": []}


def save_history(history: Dict[str, Any]):
    """処理履歴を保存"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_already_processed(
    idempotency_key: str, history: Dict[str, Any]
) -> bool:
    """既に処理済みかチェック"""
    processed_keys = [
        item.get("idempotency_key")
        for item in history.get("processed", [])
    ]
    return idempotency_key in processed_keys


def mark_as_processed(
    idempotency_key: str, history: Dict[str, Any], result: Dict[str, Any]
):
    """処理済みとしてマーク"""
    if "processed" not in history:
        history["processed"] = []

    history["processed"].append({
        "idempotency_key": idempotency_key,
        "processed_at": datetime.now().isoformat(),
        "result": result
    })


def send_email(data: Dict[str, Any]) -> Dict[str, Any]:
    """メールを送信"""
    to_email = data.get("to")
    if not to_email:
        return {"success": False, "error": "toが指定されていません"}
    
    subject = data.get("subject", "")
    body = data.get("body", "")
    from_email = data.get("from") or EMAIL_FROM
    cc = data.get("cc", [])
    bcc = data.get("bcc", [])
    attachments = data.get("attachments", [])
    
    try:
        # メッセージ作成
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        if cc:
            msg['Cc'] = ', '.join(cc)
        msg['Subject'] = subject
        
        # 本文
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 添付ファイル
        for attachment_path in attachments:
            file_path = Path(attachment_path)
            if not file_path.exists():
                print(f"⚠️  添付ファイルが見つかりません: {attachment_path}")
                continue
            
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {file_path.name}'
                )
                msg.attach(part)
        
        # 送信先リスト
        recipients = [to_email]
        if cc:
            recipients.extend(cc)
        if bcc:
            recipients.extend(bcc)
        
        # SMTPサーバーに接続して送信
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg, from_addr=from_email, to_addrs=recipients)
        
        return {
            "success": True,
            "to": to_email,
            "subject": subject
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_batch_email(data: Dict[str, Any]) -> Dict[str, Any]:
    """バッチメールを送信"""
    to_emails = data.get("to", [])
    if not to_emails or not isinstance(to_emails, list):
        return {"success": False, "error": "toがリスト形式で指定されていません"}
    
    subject_template = data.get("subject", "")
    body_template = data.get("body", "")
    template_variables = data.get("template_variables", {})
    
    results = {
        "success_count": 0,
        "failed_count": 0,
        "errors": []
    }
    
    for to_email in to_emails:
        # テンプレート変数を適用
        subject = subject_template
        body = body_template
        
        if to_email in template_variables:
            vars_dict = template_variables[to_email]
            for key, value in vars_dict.items():
                subject = subject.replace(f"{{{key}}}", str(value))
                body = body.replace(f"{{{key}}}", str(value))
        
        # メール送信
        email_data = {
            **data,
            "to": to_email,
            "subject": subject,
            "body": body
        }
        result = send_email(email_data)
        
        if result.get("success"):
            results["success_count"] += 1
        else:
            results["failed_count"] += 1
            results["errors"].append({
                "to": to_email,
                "error": result.get("error", "不明なエラー")
            })
    
    return {
        "success": results["success_count"] > 0,
        "results": results
    }


def send_slack_notification(action: str, result: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "send": "メール送信",
            "batch_send": "バッチメール送信"
        }
        action_name = action_names.get(action, action)
        
        message = f"📧 *メール送信: {action_name}*\n\n"
        
        if result.get("success"):
            message += f"✅ 成功\n"
            if "to" in result:
                message += f"送信先: {result['to']}\n"
            if "subject" in result:
                message += f"件名: {result['subject']}\n"
            if "results" in result:
                results = result["results"]
                message += f"成功: {results.get('success_count', 0)}件\n"
                message += f"失敗: {results.get('failed_count', 0)}件\n"
        else:
            message += f"❌ 失敗: {result.get('error', '不明なエラー')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS Email Ops",
            "icon_emoji": ":email:"
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Slack通知送信完了")
            return True
        else:
            print(f"❌ Slack通知送信失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Slack通知送信エラー: {e}")
        return False


def process_yaml_file(yaml_file: Path) -> bool:
    """YAMLファイルを処理"""
    print(f"\n📁 処理開始: {yaml_file}")
    
    # YAML読み込み
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ YAMLファイル読み込みエラー: {e}")
        return False
    
    # バリデーション
    if data.get("kind") != "email_ops":
        print("⚠️  kindが'email_ops'ではありません。スキップします。")
        return False
    
    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
        return False
    
    # 履歴チェック
    history = load_history()
    if is_already_processed(idempotency_key, history):
        print(f"⏭️  既に処理済みです: {idempotency_key}")
        return True
    
    # 処理実行
    action = data.get("action")
    result = {"success": False, "error": "不明なアクション"}
    
    try:
        if action == "send":
            result = send_email(data)
        elif action == "batch_send":
            result = send_batch_email(data)
        else:
            result = {"success": False, "error": f"不明なアクション: {action}"}
    except Exception as e:
        result = {"success": False, "error": str(e)}
        print(f"❌ 処理エラー: {e}")
    
    # Slack通知
    if data.get("notify", {}).get("slack", False):
        send_slack_notification(action, result)
    else:
        print("⏭️  Slack通知はスキップされます")
    
    # 履歴に記録
    mark_as_processed(idempotency_key, history, result)
    save_history(history)
    
    if result.get("success"):
        print(f"✅ 処理完了: {yaml_file}")
        return True
    else:
        print(f"❌ 処理失敗: {yaml_file} - {result.get('error', '')}")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_email_ops.py "
            "<yaml_file> [yaml_file2 ...]"
        )
        sys.exit(1)
    
    yaml_files = [Path(f) for f in sys.argv[1:]]
    
    success_count = 0
    for yaml_file in yaml_files:
        if not yaml_file.exists():
            print(f"❌ ファイルが見つかりません: {yaml_file}")
            continue
        
        if process_yaml_file(yaml_file):
            success_count += 1
    
    print(f"\n🎉 処理完了: {success_count}/{len(yaml_files)} ファイル")
    
    if success_count < len(yaml_files):
        sys.exit(1)


if __name__ == "__main__":
    main()
