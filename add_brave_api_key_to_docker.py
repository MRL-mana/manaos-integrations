#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker設定ファイルにBrave Search APIキーを追加するスクリプト
"""

import subprocess
import yaml
import json
import os
from pathlib import Path

def get_brave_api_key():
    """このはサーバー側からBrave Search APIキーを取得"""
    print("[1] Brave Search APIキーを取得中...")
    print("-" * 70)
    
    # まず.envファイルから確認
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("BRAVE_API_KEY="):
                    api_key = line.split('=', 1)[1].strip()
                    print(f"  [OK] .envファイルから取得しました")
                    print(f"  APIキー: {api_key[:10]}...")
                    return api_key
    
    # このはサーバー側から取得を試みる
    try:
        result = subprocess.run(
            ["ssh", "konoha", "env | grep BRAVE_API_KEY"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if 'BRAVE_API_KEY=' in line:
                    api_key = line.split('=', 1)[1]
                    print(f"  [OK] このはサーバー側から取得しました")
                    print(f"  APIキー: {api_key[:10]}...")
                    return api_key
    except Exception as e:
        print(f"  [WARN] SSH接続に失敗しました: {e}")
    
    print("  [WARN] APIキーが見つかりませんでした")
    api_key = input("Brave Search APIキーを入力してください: ").strip()
    return api_key

def update_docker_compose(file_path: Path, api_key: str):
    """docker-compose.ymlファイルを更新"""
    print(f"\n[2] {file_path.name} を更新中...")
    print("-" * 70)
    
    if not file_path.exists():
        print(f"  [WARN] ファイルが存在しません: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compose = yaml.safe_load(f)
        
        updated = False
        
        if 'services' in compose:
            for service_name, service_config in compose['services'].items():
                # 環境変数セクションを確認
                if 'environment' not in service_config:
                    service_config['environment'] = []
                
                env_list = service_config['environment']
                
                # 既存のBRAVE_API_KEYを確認
                brave_key_found = False
                if isinstance(env_list, list):
                    for i, env_item in enumerate(env_list):
                        if isinstance(env_item, str) and env_item.startswith('BRAVE_API_KEY='):
                            env_list[i] = f'BRAVE_API_KEY={api_key}'
                            brave_key_found = True
                            updated = True
                            break
                        elif isinstance(env_item, dict) and 'BRAVE_API_KEY' in env_item:
                            env_item['BRAVE_API_KEY'] = api_key
                            brave_key_found = True
                            updated = True
                            break
                    
                    if not brave_key_found:
                        env_list.append(f'BRAVE_API_KEY={api_key}')
                        updated = True
                elif isinstance(env_list, dict):
                    env_list['BRAVE_API_KEY'] = api_key
                    updated = True
                
                if updated:
                    print(f"  [OK] {service_name} サービスにBRAVE_API_KEYを追加しました")
        
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(compose, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"  [OK] {file_path.name} を保存しました")
            return True
        else:
            print(f"  [INFO] {file_path.name} は既に更新済みです")
            return False
            
    except Exception as e:
        print(f"  [ERROR] ファイルの更新に失敗しました: {e}")
        return False

def update_dockerfile(file_path: Path, api_key: str):
    """DockerfileにENVを追加（必要に応じて）"""
    print(f"\n[3] {file_path.name} を確認中...")
    print("-" * 70)
    
    if not file_path.exists():
        print(f"  [INFO] ファイルが存在しません: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'BRAVE_API_KEY' in content:
            print(f"  [INFO] {file_path.name} には既にBRAVE_API_KEYが含まれています")
            return False
        
        # ENVセクションの後に追加
        if 'ENV' in content:
            # 最後のENV行の後に追加
            lines = content.split('\n')
            last_env_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('ENV '):
                    last_env_idx = i
            
            if last_env_idx >= 0:
                # 最後のENV行の後に追加
                lines.insert(last_env_idx + 1, f'ENV BRAVE_API_KEY={api_key}')
                content = '\n'.join(lines)
            else:
                # ENVセクションが見つからない場合は最後に追加
                content += f'\nENV BRAVE_API_KEY={api_key}\n'
        else:
            # ENVセクションがない場合は最後に追加
            content += f'\nENV BRAVE_API_KEY={api_key}\n'
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  [OK] {file_path.name} にENV BRAVE_API_KEYを追加しました")
        return True
        
    except Exception as e:
        print(f"  [ERROR] ファイルの更新に失敗しました: {e}")
        return False

def create_env_file_for_docker(api_key: str):
    """Docker用の.envファイルを作成"""
    print("\n[4] Docker用の.envファイルを作成中...")
    print("-" * 70)
    
    script_dir = Path(__file__).parent
    
    # docker-compose.ymlがあるディレクトリを探す
    docker_dirs = [
        script_dir / "konoha_mcp_servers" / "manaos_unified_system_mcp",
        script_dir,
    ]
    
    for docker_dir in docker_dirs:
        env_file = docker_dir / ".env.docker"
        compose_file = docker_dir / "docker-compose.yml"
        
        if compose_file.exists():
            env_content = ""
            if env_file.exists():
                env_content = env_file.read_text(encoding='utf-8')
            
            if "BRAVE_API_KEY=" not in env_content:
                if env_content and not env_content.endswith('\n'):
                    env_content += '\n'
                env_content += f"BRAVE_API_KEY={api_key}\n"
                env_file.write_text(env_content, encoding='utf-8')
                print(f"  [OK] {env_file} を作成/更新しました")
            else:
                # 既存の値を更新
                lines = env_content.split('\n')
                new_lines = []
                for line in lines:
                    if line.startswith("BRAVE_API_KEY="):
                        new_lines.append(f"BRAVE_API_KEY={api_key}")
                    else:
                        new_lines.append(line)
                env_file.write_text('\n'.join(new_lines), encoding='utf-8')
                print(f"  [OK] {env_file} を更新しました")

def main():
    """メイン処理"""
    print("=" * 70)
    print("Docker設定にBrave Search APIキーを追加")
    print("=" * 70)
    
    # APIキーを取得
    api_key = get_brave_api_key()
    
    if not api_key:
        print("[ERROR] APIキーが入力されていません")
        return
    
    script_dir = Path(__file__).parent
    
    # docker-compose.ymlファイルを探して更新
    docker_compose_files = [
        script_dir / "konoha_mcp_servers" / "manaos_unified_system_mcp" / "docker-compose.yml",
        script_dir / "docker-compose.always-ready-llm.yml",
        script_dir / "docker-compose.searxng.yml",
    ]
    
    updated_files = []
    for compose_file in docker_compose_files:
        if compose_file.exists():
            if update_docker_compose(compose_file, api_key):
                updated_files.append(compose_file.name)
    
    # Dockerfileを更新（オプション）
    dockerfile_files = [
        script_dir / "konoha_mcp_servers" / "manaos_unified_system_mcp" / "Dockerfile",
        script_dir / "Dockerfile",
    ]
    
    for dockerfile in dockerfile_files:
        if dockerfile.exists():
            update_dockerfile(dockerfile, api_key)
    
    # Docker用の.envファイルを作成
    create_env_file_for_docker(api_key)
    
    print()
    print("=" * 70)
    print("完了")
    print("=" * 70)
    print()
    
    if updated_files:
        print("[更新されたファイル]")
        for file_name in updated_files:
            print(f"  - {file_name}")
        print()
        print("[次のステップ]")
        print("1. Dockerコンテナを再起動してください:")
        print("   docker-compose down")
        print("   docker-compose up -d")
        print("2. 環境変数が正しく設定されているか確認してください:")
        print("   docker-compose exec <service_name> env | grep BRAVE_API_KEY")
    else:
        print("[INFO] 更新が必要なファイルはありませんでした")
    print()

if __name__ == "__main__":
    main()



