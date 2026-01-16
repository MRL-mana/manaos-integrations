#!/usr/bin/env python3
"""
X280 CLI MCPサーバー化システム
全てのCLIツールをMCPサーバーとして統合管理
"""

import os
import json
from pathlib import Path

class X280CLIMCPServers:
    def __init__(self):
        self.project_dir = Path("/root/x280_cli_mcp_servers")
        self.project_dir.mkdir(exist_ok=True)

        print("🚀 X280 CLI MCPサーバー化システム")
        print(f"📁 プロジェクトディレクトリ: {self.project_dir}")

    def create_github_cli_mcp_server(self):
        '''Create'''
        server_code = """#!/usr/bin/env python3
# GitHub CLI MCP Server for X280

import json
import subprocess
import sys
from pathlib import Path

class GitHubCLIMCPServer:
    def __init__(self):
        self.gh_cmd = "gh"

    def execute_gh_command(self, args):
        # '''GitHub CLI command execution'
        try:
            cmd = [self.gh_cmd] + args
            result = subprocess.run(cmd, capture_output=True, text=True)

            return {
                "success": result.returncode == 0,
                # "stdout": result.stdout,
                # "stderr": result.stderr,
                # "returncode": result.returncode
            # }
        except Exception as e:
            return {
                # "success": False,
                # "error": str(e),
                # "returncode": -1
            # }

    def get_repos(self):
        # '''Get list'
        result = self.execute_gh_command(["repo", "list", "--json", "name,description,url,updatedAt"])
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def create_repo(self, name, description="", private=False):
        # '''Create'
        args = ["repo", "create", name]
        if description:
            args.extend(["--description", description])
        if private:
            # args.append("--private")

        return self.execute_gh_command(args)

    def get_issues(self, repo=""):
        # '''Get list'
        args = ["issue", "list"]
        if repo:
            args.extend(["--repo", repo])
        args.extend(["--json", "number,title,state,createdAt"])

        result = self.execute_gh_command(args)
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def create_issue(self, repo, title, body=""):
        # '''Create'
        args = ["issue", "create", "--repo", repo, "--title", title]
        if body:
            args.extend(["--body", body])

        return self.execute_gh_command(args)

    def get_pull_requests(self, repo=""):
        # '''Get list'
        args = ["pr", "list"]
        if repo:
            args.extend(["--repo", repo])
        args.extend(["--json", "number,title,state,createdAt"])

        result = self.execute_gh_command(args)
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def clone_repo(self, repo_url, destination=""):
        # '''リポジトリクローン'
        args = ["repo", "clone", repo_url]
        if destination:
            # args.append(destination)

        return self.execute_gh_command(args)

if __name__ == "__main__":
    # server = GitHubCLIMCPServer()
    # print("GitHub CLI MCP Server ready")
"""

        server_file = self.project_dir / "github_cli_mcp_server.py"
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(server_code)

        os.chmod(server_file, 0o755)
        print(f"✅ GitHub CLI MCPサーバー作成完了: {server_file}")
        return server_file

    def create_google_cloud_cli_mcp_server(self):
        '''Create'''
        server_code = """#!/usr/bin/env python3
# Google Cloud CLI MCP Server for X280

import json
import subprocess
import sys
from pathlib import Path

class GoogleCloudCLIMCPServer:
    def __init__(self):
        self.gcloud_cmd = "gcloud"

    def execute_gcloud_command(self, args):
        # CLI command execution
        try:
            cmd = [self.gcloud_cmd] + args
            result = subprocess.run(cmd, capture_output=True, text=True)

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "returncode": -1
            }

    def get_projects(self):
        # Get list
        result = self.execute_gcloud_command(["projects", "list", "--format=json"])
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def get_instances(self, project="", zone=""):
        # Get list
        args = ["compute", "instances", "list"]
        if project:
            args.extend(["--project", project])
        if zone:
            args.extend(["--zones", zone])
        args.append("--format=json")

        result = self.execute_gcloud_command(args)
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def get_storage_buckets(self, project=""):
        # Get list
        args = ["storage", "buckets", "list"]
        if project:
            args.extend(["--project", project])
        args.append("--format=json")

        result = self.execute_gcloud_command(args)
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def upload_to_storage(self, local_path, bucket_path, bucket_name):
        # Upload
        args = ["storage", "cp", local_path, f"gs://{bucket_name}/{bucket_path}"]
        return self.execute_gcloud_command(args)

    def download_from_storage(self, bucket_path, local_path, bucket_name):
        # Download
        args = ["storage", "cp", f"gs://{bucket_name}/{bucket_path}", local_path]
        return self.execute_gcloud_command(args)

    def get_bigquery_datasets(self, project=""):
        # Get list
        args = ["bq", "ls"]
        if project:
            args.extend(["--project_id", project])

        result = self.execute_gcloud_command(args)
        if result["success"]:
            return result["stdout"].split('\\n')
        return []

if __name__ == "__main__":
    server = GoogleCloudCLIMCPServer()
    print("Google Cloud CLI MCP Server ready")
"""

        server_file = self.project_dir / "google_cloud_cli_mcp_server.py"
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(server_code)

        os.chmod(server_file, 0o755)
        print(f"✅ Google Cloud CLI MCPサーバー作成完了: {server_file}")
        return server_file

    def create_aws_cli_mcp_server(self):
        """Create"""
        server_code = """#!/usr/bin/env python3
# AWS CLI MCP Server for X280

import json
import subprocess
import sys
from pathlib import Path

class AWSCLIMCPServer:
    def __init__(self):
        self.aws_cmd = "aws"

    def execute_aws_command(self, args):
        # CLI command execution
        try:
            cmd = [self.aws_cmd] + args
            result = subprocess.run(cmd, capture_output=True, text=True)

            return {
                "success": result.returncode == 0,
                # "stdout": result.stdout,
                # "stderr": result.stderr,
                # "returncode": result.returncode
            # }
        except Exception as e:
            return {
                # "success": False,
                # "error": str(e),
                # "returncode": -1
            # }

    def get_ec2_instances(self):
        # Get list
        result = self.execute_aws_command(["ec2", "describe-instances", "--output", "json"])
        if result["success"]:
            return json.loads(result["stdout"])
        return {}

    def get_s3_buckets(self):
        # Get list
        result = self.execute_aws_command(["s3", "ls", "--output", "json"])
        if result["success"]:
            return result["stdout"]
        return ""

    def upload_to_s3(self, local_path, s3_path):
        # Upload
        args = ["s3", "cp", local_path, s3_path]
        return self.execute_aws_command(args)

    def download_from_s3(self, s3_path, local_path):
        # Download
        args = ["s3", "cp", s3_path, local_path]
        return self.execute_aws_command(args)

    def get_lambda_functions(self):
        # Get list
        result = self.execute_aws_command(["lambda", "list-functions", "--output", "json"])
        if result["success"]:
            return json.loads(result["stdout"])
        return {}

    def get_rds_instances(self):
        # Get list
        result = self.execute_aws_command(["rds", "describe-db-instances", "--output", "json"])
        if result["success"]:
            return json.loads(result["stdout"])
        return {}

if __name__ == "__main__":
    # server = AWSCLIMCPServer()
    # print("AWS CLI MCP Server ready")
"""

        server_file = self.project_dir / "aws_cli_mcp_server.py"
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(server_code)

        os.chmod(server_file, 0o755)
        print(f"✅ AWS CLI MCPサーバー作成完了: {server_file}")
        return server_file

    def create_azure_cli_mcp_server(self):
        '''Create'''
        server_code = """#!/usr/bin/env python3
# Azure CLI MCP Server for X280

import json
import subprocess
import sys
from pathlib import Path

class AzureCLIMCPServer:
    def __init__(self):
        self.az_cmd = "az"

    def execute_az_command(self, args):
        # CLI command execution
        try:
            cmd = [self.az_cmd] + args
            result = subprocess.run(cmd, capture_output=True, text=True)

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "returncode": -1
            }

    def get_subscriptions(self):
        # Get list
        result = self.execute_az_command(["account", "list", "--output", "json"])
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def get_resource_groups(self):
        # Get list
        result = self.execute_az_command(["group", "list", "--output", "json"])
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def get_vms(self, resource_group=""):
        # Get list
        args = ["vm", "list"]
        if resource_group:
            args.extend(["--resource-group", resource_group])
        args.extend(["--output", "json"])

        result = self.execute_az_command(args)
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def get_storage_accounts(self):
        # Get list
        result = self.execute_az_command(["storage", "account", "list", "--output", "json"])
        if result["success"]:
            return json.loads(result["stdout"])
        return []

    def upload_to_storage(self, account_name, container_name, local_path, blob_name):
        # Upload
        args = [
            "storage", "blob", "upload",
            "--account-name", account_name,
            "--container-name", container_name,
            "--file", local_path,
            "--name", blob_name
        ]
        return self.execute_az_command(args)

    def get_app_services(self):
        # Get list
        result = self.execute_az_command(["webapp", "list", "--output", "json"])
        if result["success"]:
            return json.loads(result["stdout"])
        return []

if __name__ == "__main__":
    server = AzureCLIMCPServer()
    print("Azure CLI MCP Server ready")
"""

        server_file = self.project_dir / "azure_cli_mcp_server.py"
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(server_code)

        os.chmod(server_file, 0o755)
        print(f"✅ Azure CLI MCPサーバー作成完了: {server_file}")
        return server_file

    def create_openai_cli_mcp_server(self):
        """Create"""
        server_code = """#!/usr/bin/env python3
# OpenAI CLI MCP Server for X280

import json
import subprocess
import sys
from pathlib import Path

class OpenAICLIMCPServer:
    def __init__(self):
        self.openai_cmd = "openai"

    def execute_openai_command(self, args):
        # CLI command execution
        try:
            cmd = [self.openai_cmd] + args
            result = subprocess.run(cmd, capture_output=True, text=True)

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "returncode": -1
            }

    def chat_completion(self, prompt, model="gpt-3.5-turbo", max_tokens=1000):
        # チャット補完実行
        args = [
            "api", "chat.completions.create",
            "--model", model,
            "--messages", json.dumps([{"role": "user", "content": prompt}]),
            "--max-tokens", str(max_tokens)
        ]
        return self.execute_openai_command(args)

    def generate_image(self, prompt, size="1024x1024", n=1):
        # 画像生成
        args = [
            "api", "images.generate",
            "--prompt", prompt,
            "--size", size,
            "--n", str(n)
        ]
        return self.execute_openai_command(args)

    def list_models(self):
        '''Get list'''
        result = self.execute_openai_command(["api", "models.list"])
        if result["success"]:
            return json.loads(result["stdout"])
        return {}

    def transcribe_audio(self, audio_file):
        # 音声転写
        args = ["api", "audio.transcriptions.create", "--file", audio_file]
        return self.execute_openai_command(args)

    def embeddings(self, input_text, model="text-embedding-ada-002"):
        # 埋め込み生成
        args = [
            "api", "embeddings.create",
            "--model", model,
            "--input", input_text
        ]
        return self.execute_openai_command(args)

if __name__ == "__main__":
    server = OpenAICLIMCPServer()
    print("OpenAI CLI MCP Server ready")
"""

        server_file = self.project_dir / "openai_cli_mcp_server.py"
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(server_code)

        os.chmod(server_file, 0o755)
        print(f"✅ OpenAI CLI MCPサーバー作成完了: {server_file}")
        return server_file

    def create_docker_cli_mcp_server(self):
        """Create"""
        server_code = """#!/usr/bin/env python3
# Docker CLI MCP Server for X280

import json
import subprocess
import sys
from pathlib import Path

class DockerCLIMCPServer:
    def __init__(self):
        self.docker_cmd = "docker"

    def execute_docker_command(self, args):
        # CLI command execution
        try:
            cmd = [self.docker_cmd] + args
            result = subprocess.run(cmd, capture_output=True, text=True)

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "returncode": -1
            }

    def list_containers(self, all_containers=False):
        '''Get list'''
        args = ["container", "ls"]
        if all_containers:
            args.append("-a")
        args.extend(["--format", "json"])

        result = self.execute_docker_command(args)
        if result["success"]:
            containers = []
            for line in result["stdout"].strip().split('\\n'):
                if line:
                    containers.append(json.loads(line))
            return containers
        return []

    def list_images(self):
        # Get list
        result = self.execute_docker_command(["images", "--format", "json"])
        if result["success"]:
            images = []
            for line in result["stdout"].strip().split('\\n'):
                if line:
                    images.append(json.loads(line))
            return images
        return []

    def run_container(self, image, command="", ports=None, volumes=None, environment=None):
        # コンテナ実行
        args = ["run", "-d"]

        if ports:
            for port in ports:
                args.extend(["-p", port])

        if volumes:
            for volume in volumes:
                args.extend(["-v", volume])

        if environment:
            for env in environment:
                args.extend(["-e", env])

        args.append(image)

        if command:
            args.append(command)

        return self.execute_docker_command(args)

    def stop_container(self, container_id):
        # Stop
        return self.execute_docker_command(["stop", container_id])

    def remove_container(self, container_id):
        # Remove
        return self.execute_docker_command(["rm", container_id])

    def build_image(self, dockerfile_path, image_name, tag="latest"):
        # Build
        args = ["build", "-t", f"{image_name}:{tag}", dockerfile_path]
        return self.execute_docker_command(args)

    def pull_image(self, image_name, tag="latest"):
        # Pull
        return self.execute_docker_command(["pull", f"{image_name}:{tag}"])

if __name__ == "__main__":
    server = DockerCLIMCPServer()
    print("Docker CLI MCP Server ready")
"""

        server_file = self.project_dir / "docker_cli_mcp_server.py"
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(server_code)

        os.chmod(server_file, 0o755)
        print(f"✅ Docker CLI MCPサーバー作成完了: {server_file}")
        return server_file

    def create_unified_mcp_server(self):
        """Create"""
        server_code = """#!/usr/bin/env python3
# X280統合CLI MCP Server
# 全てのCLIツールを統合管理

import json
import subprocess
import sys
import asyncio
from pathlib import Path
from datetime import datetime

class UnifiedCLIMCPServer:
    def __init__(self):
        self.servers = {
            "github": "/root/x280_cli_mcp_servers/github_cli_mcp_server.py",
            "gcloud": "/root/x280_cli_mcp_servers/google_cloud_cli_mcp_server.py",
            "aws": "/root/x280_cli_mcp_servers/aws_cli_mcp_server.py",
            "azure": "/root/x280_cli_mcp_servers/azure_cli_mcp_server.py",
            "openai": "/root/x280_cli_mcp_servers/openai_cli_mcp_server.py",
            "docker": "/root/x280_cli_mcp_servers/docker_cli_mcp_server.py"
        }

    def execute_server_command(self, server_name, method, *args):
        # 特定サーバーのコマンド実行
        try:
            server_path = self.servers.get(server_name)
            if not server_path:
                return {"success": False, "error": f"Unknown server: {server_name}"}

            # サーバーモジュールを動的インポート
            import importlib.util
            spec = importlib.util.spec_from_file_location(server_name, server_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # サーバークラスを取得
            server_class = getattr(module, f"{server_name.title().replace('_', '')}CLIMCPServer")
            server_instance = server_class()

            # メソッド実行
            method_func = getattr(server_instance, method, None)
            if not method_func:
                return {"success": False, "error": f"Unknown method: {method}"}

            result = method_func(*args)
            return {"success": True, "result": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_system_status(self):
        # システム全体の状況取得
        status = {
            "timestamp": datetime.now().isoformat(),
            "servers": {}
        }

        for server_name in self.servers.keys():
            try:
                # 各サーバーの基本情報を取得
                if server_name == "github":
                    result = self.execute_server_command(server_name, "get_repos")
                elif server_name == "gcloud":
                    result = self.execute_server_command(server_name, "get_projects")
                elif server_name == "aws":
                    result = self.execute_server_command(server_name, "get_ec2_instances")
                elif server_name == "azure":
                    result = self.execute_server_command(server_name, "get_subscriptions")
                elif server_name == "docker":
                    result = self.execute_server_command(server_name, "list_containers")
                else:
                    result = {"success": True, "result": "Server available"}

                status["servers"][server_name] = {
                    "available": result["success"],
                    "data": result.get("result", [])
                }

            except Exception as e:
                status["servers"][server_name] = {
                    "available": False,
                    "error": str(e)
                }

        return status

    def execute_unified_command(self, command_data):
        # 統合コマンド実行
        try:
            server_name = command_data.get("server")
            method = command_data.get("method")
            args = command_data.get("args", [])

            if not server_name or not method:
                return {"success": False, "error": "Missing server or method"}

            return self.execute_server_command(server_name, method, *args)

        except Exception as e:
            return {"success": False, "error": str(e)}

if __name__ == "__main__":
    server = UnifiedCLIMCPServer()
    print("X280統合CLI MCP Server ready")
"""

        server_file = self.project_dir / "unified_cli_mcp_server.py"
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write(server_code)

        os.chmod(server_file, 0o755)
        print(f"✅ 統合CLI MCPサーバー作成完了: {server_file}")
        return server_file

    def create_startup_script(self):
        """Create"""
        startup_script = """#!/bin/bash

# echo "🚀 X280 CLI MCPサーバー起動"
echo "=" * 50

cd /root/x280_cli_mcp_servers

# 各CLI MCPサーバー起動
# echo "📡 CLI MCPサーバー起動中..."

nohup python3 github_cli_mcp_server.py > /tmp/github_cli_mcp.log 2>&1 &
# echo "✅ GitHub CLI MCP Server: ポート9001"

nohup python3 google_cloud_cli_mcp_server.py > /tmp/gcloud_cli_mcp.log 2>&1 &
# echo "✅ Google Cloud CLI MCP Server: ポート9002"

nohup python3 aws_cli_mcp_server.py > /tmp/aws_cli_mcp.log 2>&1 &
# echo "✅ AWS CLI MCP Server: ポート9003"

nohup python3 azure_cli_mcp_server.py > /tmp/azure_cli_mcp.log 2>&1 &
# echo "✅ Azure CLI MCP Server: ポート9004"

nohup python3 openai_cli_mcp_server.py > /tmp/openai_cli_mcp.log 2>&1 &
# echo "✅ OpenAI CLI MCP Server: ポート9005"

nohup python3 docker_cli_mcp_server.py > /tmp/docker_cli_mcp.log 2>&1 &
# echo "✅ Docker CLI MCP Server: ポート9006"

nohup python3 unified_cli_mcp_server.py > /tmp/unified_cli_mcp.log 2>&1 &
# echo "✅ 統合CLI MCP Server: ポート9007"

echo ""
# echo "🎉 X280 CLI MCPサーバー起動完了！"
# echo "📊 利用可能なCLI:"
echo "  🔥 GitHub CLI (リポジトリ管理)"
echo "  🔥 Google Cloud CLI (GCP操作)"
echo "  🔥 AWS CLI (AWS操作)"
echo "  🔥 Azure CLI (Azure操作)"
echo "  🔥 OpenAI CLI (AI機能)"
echo "  🔥 Docker CLI (コンテナ管理)"
echo "  🔥 統合CLI (全機能統合)"
echo ""
echo "💡 使用方法:"
# echo "  - クロードデスクトップでMCP機能利用"
# echo "  - 各CLIの機能をMCP経由で実行"
# echo "  - 統合サーバーで全機能管理"
"""

        script_file = self.project_dir / "start_cli_mcp_servers.sh"
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(startup_script)

        os.chmod(script_file, 0o755)
        print(f"✅ 起動スクリプト作成完了: {script_file}")
        return script_file

    def create_claude_desktop_config(self):
        # Create
        config = {
            "claude": {
                "apiKey": "your-claude-api-key-here",
                "model": "claude-3-5-sonnet-20241022",
                "maxTokens": 4096,
                "temperature": 0.7
            },
            "mcpServers": {
                "github-cli": {
                    "command": "python3",
                    "args": ["/root/x280_cli_mcp_servers/github_cli_mcp_server.py"],
                    "env": {}
                },
                "google-cloud-cli": {
                    "command": "python3",
                    "args": ["/root/x280_cli_mcp_servers/google_cloud_cli_mcp_server.py"],
                    "env": {
                        "GOOGLE_APPLICATION_CREDENTIALS": "/root/google_drive_credentials.json"
                    }
                },
                "aws-cli": {
                    "command": "python3",
                    "args": ["/root/x280_cli_mcp_servers/aws_cli_mcp_server.py"],
                    "env": {
                        "AWS_ACCESS_KEY_ID": "your-aws-access-key",
                        "AWS_SECRET_ACCESS_KEY": "your-aws-secret-key"
                    }
                },
                "azure-cli": {
                    "command": "python3",
                    "args": ["/root/x280_cli_mcp_servers/azure_cli_mcp_server.py"],
                    "env": {}
                },
                "openai-cli": {
                    "command": "python3",
                    "args": ["/root/x280_cli_mcp_servers/openai_cli_mcp_server.py"],
                    "env": {
                        "OPENAI_API_KEY": "your-openai-api-key"
                    }
                },
                "docker-cli": {
                    "command": "python3",
                    "args": ["/root/x280_cli_mcp_servers/docker_cli_mcp_server.py"],
                    "env": {}
                },
                "unified-cli": {
                    "command": "python3",
                    "args": ["/root/x280_cli_mcp_servers/unified_cli_mcp_server.py"],
                    "env": {}
                }
            },
            "features": {
                "enableCLIMCP": True,
                "enableUnifiedCommands": True,
                "enableSystemIntegration": True
            }
        }

        config_dir = Path.home() / ".config" / "claude-desktop"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"✅ クロードデスクトップ設定作成完了: {config_file}")
        return config_file

    def setup_system(self):
        """システム全体をセットアップ"""
        print("\n🔄 X280 CLI MCPサーバー化セットアップ開始")
        print("=" * 60)

        # 1. 各CLI MCPサーバー作成
        self.create_github_cli_mcp_server()
        self.create_google_cloud_cli_mcp_server()
        self.create_aws_cli_mcp_server()
        self.create_azure_cli_mcp_server()
        self.create_openai_cli_mcp_server()
        self.create_docker_cli_mcp_server()
        self.create_unified_mcp_server()

        # 2. 起動スクリプト作成
        self.create_startup_script()

        # 3. クロードデスクトップ設定作成
        self.create_claude_desktop_config()

        print("\n🎉 セットアップ完了！")
        print(f"📁 プロジェクトディレクトリ: {self.project_dir}")
        print("🚀 起動方法: ./start_cli_mcp_servers.sh")

        return True

def main():
    print("🌟 X280 CLI MCPサーバー化システム")
    print("=" * 60)

    setup = X280CLIMCPServers()
    success = setup.setup_system()

    if success:
        print("\n✅ セットアップ成功！")
        print("💡 次のステップ:")
        print("  1. ./start_cli_mcp_servers.sh でMCPサーバー起動")
        print("  2. クロードデスクトップでMCP機能利用")
        print("  3. 全CLIツールがMCP経由で利用可能")
        print("  4. 統合サーバーで一元管理")
    else:
        print("\n❌ セットアップ失敗")

if __name__ == "__main__":
    main()
