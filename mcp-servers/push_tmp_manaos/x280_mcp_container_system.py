#!/usr/bin/env python3
"""
X280 MCPサーバー・コンテナ統合システム
PDF-Excel変換システムのMCP化とコンテナ化
"""

import os
import json
import docker
import yaml
from pathlib import Path

class X280MCPContainerSystem:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.project_dir = Path("/root/x280_mcp_project")
        self.project_dir.mkdir(exist_ok=True)
        
        print("🚀 X280 MCPサーバー・コンテナ統合システム")
        print(f"📁 プロジェクトディレクトリ: {self.project_dir}")
    
    def create_docker_compose(self):
        """Docker Compose設定を作成"""
        compose_config = {
            'version': '3.8',
            'services': {
                'pdf-excel-converter': {
                    'build': {
                        'context': '.',
                        'dockerfile': 'Dockerfile.pdf-converter'
                    },
                    'ports': ['8080:8080'],
                    'volumes': [
                        './data:/app/data',
                        './output:/app/output'
                    ],
                    'environment': [
                        'PYTHONPATH=/app',
                        'LOG_LEVEL=INFO'
                    ],
                    'restart': 'unless-stopped'
                },
                'google-drive-integration': {
                    'build': {
                        'context': '.',
                        'dockerfile': 'Dockerfile.google-drive'
                    },
                    'ports': ['8081:8081'],
                    'volumes': [
                        './credentials:/app/credentials',
                        './data:/app/data'
                    ],
                    'environment': [
                        'GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/credentials.json'
                    ],
                    'restart': 'unless-stopped',
                    'depends_on': ['pdf-excel-converter']
                },
                'mcp-server': {
                    'build': {
                        'context': '.',
                        'dockerfile': 'Dockerfile.mcp-server'
                    },
                    'ports': ['8082:8082'],
                    'volumes': [
                        './mcp_config:/app/config',
                        './data:/app/data'
                    ],
                    'environment': [
                        'MCP_SERVER_PORT=8082',
                        'MCP_LOG_LEVEL=INFO'
                    ],
                    'restart': 'unless-stopped',
                    'depends_on': ['pdf-excel-converter', 'google-drive-integration']
                },
                'monitoring-dashboard': {
                    'build': {
                        'context': '.',
                        'dockerfile': 'Dockerfile.monitoring'
                    },
                    'ports': ['8083:8083'],
                    'volumes': [
                        './monitoring_data:/app/data'
                    ],
                    'environment': [
                        'DASHBOARD_PORT=8083'
                    ],
                    'restart': 'unless-stopped'
                },
                'nginx-proxy': {
                    'image': 'nginx:alpine',
                    'ports': ['80:80', '443:443'],
                    'volumes': [
                        './nginx.conf:/etc/nginx/nginx.conf',
                        './ssl:/etc/nginx/ssl'
                    ],
                    'depends_on': [
                        'pdf-excel-converter',
                        'google-drive-integration',
                        'mcp-server',
                        'monitoring-dashboard'
                    ],
                    'restart': 'unless-stopped'
                }
            },
            'networks': {
                'x280-network': {
                    'driver': 'bridge'
                }
            },
            'volumes': {
                'data': {},
                'output': {},
                'credentials': {},
                'monitoring_data': {}
            }
        }
        
        compose_file = self.project_dir / 'docker-compose.yml'
        with open(compose_file, 'w', encoding='utf-8') as f:
            yaml.dump(compose_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ Docker Compose設定作成完了: {compose_file}")
        return compose_file
    
    def create_pdf_converter_dockerfile(self):
        """PDF変換システム用Dockerfile"""
        dockerfile_content = """
FROM python:3.10-slim

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \\
    tesseract-ocr \\
    tesseract-ocr-jpn \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    libsm6 \\
    libxext6 \\
    libxrender-dev \\
    libgomp1 \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pythonパッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルのコピー
COPY pdf_excel_converter.py .
COPY final_production_converter.py .
COPY advanced_ocr_enhancer.py .
COPY intelligent_table_recognizer.py .

# ポート公開
EXPOSE 8080

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://127.0.0.1:8080/health || exit 1

# アプリケーション起動
CMD ["python", "pdf_excel_converter.py"]
"""
        
        dockerfile_path = self.project_dir / 'Dockerfile.pdf-converter'
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        
        print(f"✅ PDF変換システムDockerfile作成完了: {dockerfile_path}")
        return dockerfile_path
    
    def create_google_drive_dockerfile(self):
        """Google Drive統合用Dockerfile"""
        dockerfile_content = """
FROM python:3.10-slim

WORKDIR /app

# Pythonパッケージのインストール
COPY requirements-google-drive.txt .
RUN pip install --no-cache-dir -r requirements-google-drive.txt

# アプリケーションファイルのコピー
COPY google_drive_integration.py .
COPY google_drive_credentials.json .

# ポート公開
EXPOSE 8081

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://127.0.0.1:8081/health || exit 1

# アプリケーション起動
CMD ["python", "google_drive_integration.py"]
"""
        
        dockerfile_path = self.project_dir / 'Dockerfile.google-drive'
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        
        print(f"✅ Google Drive統合Dockerfile作成完了: {dockerfile_path}")
        return dockerfile_path
    
    def create_mcp_server_dockerfile(self):
        """MCPサーバー用Dockerfile"""
        dockerfile_content = """
FROM node:18-slim

WORKDIR /app

# Node.jsパッケージのインストール
COPY package.json package-lock.json ./
RUN npm ci --only=production

# アプリケーションファイルのコピー
COPY mcp-server.js .
COPY mcp-config.json .

# ポート公開
EXPOSE 8082

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://127.0.0.1:8082/health || exit 1

# アプリケーション起動
CMD ["node", "mcp-server.js"]
"""
        
        dockerfile_path = self.project_dir / 'Dockerfile.mcp-server'
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        
        print(f"✅ MCPサーバーDockerfile作成完了: {dockerfile_path}")
        return dockerfile_path
    
    def create_requirements_files(self):
        """必要なrequirements.txtファイルを作成"""
        # PDF変換システム用
        pdf_requirements = """
fastapi==0.104.1
uvicorn==0.24.0
pandas==2.1.3
openpyxl==3.1.2
PyMuPDF==1.23.8
pdfplumber==0.10.3
camelot-py[cv]==0.10.1
Pillow==10.1.0
pytesseract==0.3.10
opencv-python==4.8.1.78
numpy==1.24.3
requests==2.31.0
aiofiles==23.2.1
websockets==12.0
"""
        
        # Google Drive統合用
        google_drive_requirements = """
google-api-python-client==2.108.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.1.0
fastapi==0.104.1
uvicorn==0.24.0
requests==2.31.0
"""
        
        pdf_req_file = self.project_dir / 'requirements.txt'
        google_req_file = self.project_dir / 'requirements-google-drive.txt'
        
        with open(pdf_req_file, 'w', encoding='utf-8') as f:
            f.write(pdf_requirements)
        
        with open(google_req_file, 'w', encoding='utf-8') as f:
            f.write(google_drive_requirements)
        
        print("✅ Requirementsファイル作成完了")
        return pdf_req_file, google_req_file
    
    def create_nginx_config(self):
        """Nginx設定ファイルを作成"""
        nginx_config = """
events {
    worker_connections 1024;
}

http {
    upstream pdf_converter {
        server pdf-excel-converter:8080;
    }
    
    upstream google_drive {
        server google-drive-integration:8081;
    }
    
    upstream mcp_server {
        server mcp-server:8082;
    }
    
    upstream monitoring {
        server monitoring-dashboard:8083;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        location / {
            proxy_pass http://pdf_converter;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location /google-drive/ {
            proxy_pass http://google_drive/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location /mcp/ {
            proxy_pass http://mcp_server/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location /monitoring/ {
            proxy_pass http://monitoring/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
"""
        
        nginx_file = self.project_dir / 'nginx.conf'
        with open(nginx_file, 'w', encoding='utf-8') as f:
            f.write(nginx_config)
        
        print(f"✅ Nginx設定作成完了: {nginx_file}")
        return nginx_file
    
    def create_mcp_server_js(self):
        """MCPサーバーJavaScriptファイルを作成"""
        mcp_server_content = """
const express = require('express');
const cors = require('cors');
const axios = require('axios');

const app = express();
const PORT = process.env.MCP_SERVER_PORT || 8082;

app.use(cors());
app.use(express.json());

// サービス接続設定
const services = {
    pdfConverter: 'http://pdf-excel-converter:8080',
    googleDrive: 'http://google-drive-integration:8081',
    monitoring: 'http://monitoring-dashboard:8083'
};

// ヘルスチェック
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// PDF変換API
app.post('/api/convert-pdf', async (req, res) => {
    try {
        const response = await axios.post(`${services.pdfConverter}/convert`, req.body);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Google Drive統合API
app.get('/api/google-drive/files', async (req, res) => {
    try {
        const response = await axios.get(`${services.googleDrive}/files`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 監視データAPI
app.get('/api/monitoring/stats', async (req, res) => {
    try {
        const response = await axios.get(`${services.monitoring}/stats`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// MCP統合API
app.post('/api/mcp/execute', async (req, res) => {
    try {
        const { service, action, params } = req.body;
        
        let response;
        switch (service) {
            case 'pdf':
                response = await axios.post(`${services.pdfConverter}/${action}`, params);
                break;
            case 'google-drive':
                response = await axios.post(`${services.googleDrive}/${action}`, params);
                break;
            default:
                throw new Error(`Unknown service: ${service}`);
        }
        
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(PORT, () => {
    console.log(`🚀 X280 MCP Server running on port ${PORT}`);
    console.log(`📊 Services: ${Object.keys(services).join(', ')}`);
});
"""
        
        mcp_file = self.project_dir / 'mcp-server.js'
        with open(mcp_file, 'w', encoding='utf-8') as f:
            f.write(mcp_server_content)
        
        print(f"✅ MCPサーバー作成完了: {mcp_file}")
        return mcp_file
    
    def create_package_json(self):
        """package.jsonファイルを作成"""
        package_json = {
            "name": "x280-mcp-server",
            "version": "1.0.0",
            "description": "X280 MCP統合サーバー",
            "main": "mcp-server.js",
            "scripts": {
                "start": "node mcp-server.js",
                "dev": "nodemon mcp-server.js"
            },
            "dependencies": {
                "express": "^4.18.2",
                "cors": "^2.8.5",
                "axios": "^1.6.0"
            },
            "devDependencies": {
                "nodemon": "^3.0.1"
            }
        }
        
        package_file = self.project_dir / 'package.json'
        with open(package_file, 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2, ensure_ascii=False)
        
        print(f"✅ package.json作成完了: {package_file}")
        return package_file
    
    def create_startup_script(self):
        """起動スクリプトを作成"""
        startup_script = """#!/bin/bash

echo "🚀 X280 MCP・コンテナ統合システム起動"
echo "=" * 60

# ディレクトリ確認
cd /root/x280_mcp_project

# Docker Composeでサービス起動
echo "📦 コンテナ起動中..."
docker-compose up -d

# サービス起動確認
echo "🔍 サービス起動確認中..."
sleep 10

# ヘルスチェック
echo "✅ ヘルスチェック実行中..."
curl -f http://127.0.0.1:8080/health && echo "PDF変換システム: OK"
curl -f http://127.0.0.1:8081/health && echo "Google Drive統合: OK"
curl -f http://127.0.0.1:8082/health && echo "MCPサーバー: OK"
curl -f http://127.0.0.1:8083/health && echo "監視ダッシュボード: OK"

echo ""
echo "🎉 X280 MCP・コンテナ統合システム起動完了！"
echo "🌐 アクセスURL:"
echo "  - PDF変換: http://127.0.0.1:8080"
echo "  - Google Drive: http://127.0.0.1:8081"
echo "  - MCPサーバー: http://127.0.0.1:8082"
echo "  - 監視ダッシュボード: http://127.0.0.1:8083"
echo "  - 統合プロキシ: http://localhost"
"""
        
        script_file = self.project_dir / 'start_system.sh'
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(startup_script)
        
        # 実行権限を付与
        os.chmod(script_file, 0o755)
        
        print(f"✅ 起動スクリプト作成完了: {script_file}")
        return script_file
    
    def setup_system(self):
        """システム全体をセットアップ"""
        print("\n🔄 X280 MCP・コンテナ統合システムセットアップ開始")
        print("=" * 60)
        
        # 1. Docker Compose設定作成
        self.create_docker_compose()
        
        # 2. Dockerfile作成
        self.create_pdf_converter_dockerfile()
        self.create_google_drive_dockerfile()
        self.create_mcp_server_dockerfile()
        
        # 3. Requirementsファイル作成
        self.create_requirements_files()
        
        # 4. Nginx設定作成
        self.create_nginx_config()
        
        # 5. MCPサーバー作成
        self.create_mcp_server_js()
        self.create_package_json()
        
        # 6. 起動スクリプト作成
        self.create_startup_script()
        
        print("\n🎉 セットアップ完了！")
        print(f"📁 プロジェクトディレクトリ: {self.project_dir}")
        print("🚀 起動方法: ./start_system.sh")
        
        return True

def main():
    print("🌟 X280 MCPサーバー・コンテナ統合システム")
    print("=" * 60)
    
    system = X280MCPContainerSystem()
    success = system.setup_system()
    
    if success:
        print("\n✅ セットアップ成功！")
        print("💡 次のステップ:")
        print("  1. ./start_system.sh でシステム起動")
        print("  2. http://localhost で統合ダッシュボードアクセス")
        print("  3. 各サービスがコンテナで独立稼働")
        print("  4. MCPサーバーで全機能統合管理")
    else:
        print("\n❌ セットアップ失敗")

if __name__ == "__main__":
    main()
