#!/usr/bin/env python3
"""
Antigravity IDE コマンド
Command HubからAntigravity IDEを操作するコマンド
"""

import subprocess
import json
from pathlib import Path


def antigravity_status():
    """Antigravity IDEの状態を確認"""
    try:
        result = subprocess.run(
            ["/root/scripts/x280_antigravity_status.sh"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return {
            "success": True,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def antigravity_start(project_path="~"):
    """Antigravity IDEを起動"""
    try:
        result = subprocess.run(
            ["/root/scripts/x280_antigravity_start.sh", project_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": True,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def antigravity_workflow(workflow_type="new_project"):
    """Antigravity IDEワークフローを実行"""
    try:
        result = subprocess.run(
            ["/root/scripts/antigravity_workflow_examples.sh"],
            input=workflow_type,
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "success": True,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def antigravity_connect():
    """Antigravity IDEに接続"""
    try:
        result = subprocess.run(
            ["ssh", "x280-vscode", "echo 'Connected'"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "command": "ssh x280-vscode"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# コマンド定義
COMMANDS = {
    "antigravity-status": {
        "function": antigravity_status,
        "description": "Antigravity IDEの状態を確認",
        "usage": "antigravity-status"
    },
    "antigravity-start": {
        "function": lambda **kwargs: antigravity_start(kwargs.get("project_path", "~")),
        "description": "Antigravity IDEを起動",
        "usage": "antigravity-start [project_path]"
    },
    "antigravity-workflow": {
        "function": lambda **kwargs: antigravity_workflow(kwargs.get("workflow_type", "new_project")),
        "description": "Antigravity IDEワークフローを実行",
        "usage": "antigravity-workflow [workflow_type]"
    },
    "antigravity-connect": {
        "function": antigravity_connect,
        "description": "Antigravity IDEに接続",
        "usage": "antigravity-connect"
    }
}



"""
Antigravity IDE コマンド
Command HubからAntigravity IDEを操作するコマンド
"""

import subprocess
import json
from pathlib import Path


def antigravity_status():
    """Antigravity IDEの状態を確認"""
    try:
        result = subprocess.run(
            ["/root/scripts/x280_antigravity_status.sh"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return {
            "success": True,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def antigravity_start(project_path="~"):
    """Antigravity IDEを起動"""
    try:
        result = subprocess.run(
            ["/root/scripts/x280_antigravity_start.sh", project_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": True,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def antigravity_workflow(workflow_type="new_project"):
    """Antigravity IDEワークフローを実行"""
    try:
        result = subprocess.run(
            ["/root/scripts/antigravity_workflow_examples.sh"],
            input=workflow_type,
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "success": True,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def antigravity_connect():
    """Antigravity IDEに接続"""
    try:
        result = subprocess.run(
            ["ssh", "x280-vscode", "echo 'Connected'"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "command": "ssh x280-vscode"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# コマンド定義
COMMANDS = {
    "antigravity-status": {
        "function": antigravity_status,
        "description": "Antigravity IDEの状態を確認",
        "usage": "antigravity-status"
    },
    "antigravity-start": {
        "function": lambda **kwargs: antigravity_start(kwargs.get("project_path", "~")),
        "description": "Antigravity IDEを起動",
        "usage": "antigravity-start [project_path]"
    },
    "antigravity-workflow": {
        "function": lambda **kwargs: antigravity_workflow(kwargs.get("workflow_type", "new_project")),
        "description": "Antigravity IDEワークフローを実行",
        "usage": "antigravity-workflow [workflow_type]"
    },
    "antigravity-connect": {
        "function": antigravity_connect,
        "description": "Antigravity IDEに接続",
        "usage": "antigravity-connect"
    }
}



