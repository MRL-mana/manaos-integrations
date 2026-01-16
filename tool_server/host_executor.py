#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ホストから直接実行するTool Server補助スクリプト
レミ先輩仕様：確実に動く手動ツール（ホストから実行）
"""

import subprocess
import json
import sys
import os

def get_docker_containers():
    """Dockerコンテナの状態を取得（ホストから直接実行）"""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=(sys.platform == "win32")
        )

        if result.returncode != 0:
            return {
                "error": "dockerコマンドの実行に失敗しました",
                "stderr": result.stderr
            }

        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    container = json.loads(line)
                    container_name = container.get("Names", "")
                    status = container.get("Status", "")

                    is_running = "Up" in status

                    containers.append({
                        "name": container_name,
                        "status": "running" if is_running else "stopped",
                        "image": container.get("Image", ""),
                        "ports": container.get("Ports", ""),
                        "status_detail": status,
                        "id": container.get("ID", "")[:12] if container.get("ID") else ""
                    })
                except json.JSONDecodeError:
                    continue

        return {
            "status": "success",
            "containers": containers,
            "count": len(containers)
        }
    except Exception as e:
        return {
            "error": f"Dockerコンテナの取得に失敗しました: {str(e)}"
        }

if __name__ == "__main__":
    result = get_docker_containers()
    print(json.dumps(result, ensure_ascii=False, indent=2))
