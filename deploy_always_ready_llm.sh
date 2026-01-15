#!/bin/bash

# 🚀 常時起動LLM自動デプロイスクリプト
# Docker Compose + モデルインストール + 設定を一括実行

set -e

echo "🚀 常時起動LLMデプロイ開始..."

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 設定確認
echo -e "${YELLOW}📋 設定確認...${NC}"
if [ ! -f "docker-compose.always-ready-llm.yml" ]; then
    echo -e "${RED}❌ docker-compose.always-ready-llm.yml が見つかりません${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .envファイルが見つかりません。作成します...${NC}"
    cat > .env << EOF
N8N_USER=admin
N8N_PASSWORD=$(openssl rand -base64 32)
DOMAIN=localhost
ACME_EMAIL=admin@example.com
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(openssl rand -base64 32)
REDIS_HOST=redis
REDIS_PORT=6379
EOF
    echo -e "${GREEN}✅ .envファイルを作成しました${NC}"
fi

# Docker Compose起動
echo -e "${YELLOW}🐳 Docker Compose起動中...${NC}"
docker-compose -f docker-compose.always-ready-llm.yml up -d

# サービス起動待機
echo -e "${YELLOW}⏳ サービス起動待機中...${NC}"
sleep 10

# Ollamaヘルスチェック
echo -e "${YELLOW}🏥 Ollamaヘルスチェック...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo -e "${GREEN}✅ Ollama起動確認${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Ollama起動タイムアウト${NC}"
        exit 1
    fi
    sleep 2
done

# モデルインストール
echo -e "${YELLOW}📦 モデルインストール中...${NC}"

MODELS=(
    "llama3.2:3b"      # 軽量モデル
    "qwen2.5:14b"      # 中型モデル
    "qwen2.5:7b"       # バランス型
)

for model in "${MODELS[@]}"; do
    echo -e "${YELLOW}  インストール中: ${model}${NC}"
    docker exec ollama-always-ready ollama pull "$model" || {
        echo -e "${RED}  ❌ ${model} のインストールに失敗${NC}"
    }
done

echo -e "${GREEN}✅ モデルインストール完了${NC}"

# Redisヘルスチェック
echo -e "${YELLOW}🏥 Redisヘルスチェック...${NC}"
if docker exec redis-cache redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis起動確認${NC}"
else
    echo -e "${RED}❌ Redis起動確認失敗${NC}"
fi

# n8nヘルスチェック
echo -e "${YELLOW}🏥 n8nヘルスチェック...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:5678/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✅ n8n起動確認${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠️  n8n起動確認タイムアウト（手動確認が必要）${NC}"
    fi
    sleep 2
done

# ワークフローインポート（オプション）
if [ -f "n8n_workflows/always_ready_llm_workflow.json" ]; then
    echo -e "${YELLOW}📥 n8nワークフローインポート...${NC}"
    echo -e "${YELLOW}  手動でインポートしてください:${NC}"
    echo -e "${YELLOW}  1. http://localhost:5678 にアクセス${NC}"
    echo -e "${YELLOW}  2. ワークフロー → インポート${NC}"
    echo -e "${YELLOW}  3. n8n_workflows/always_ready_llm_workflow.json を選択${NC}"
fi

# 統合APIサーバー起動確認（オプション）
if pgrep -f "unified_api_server.py" > /dev/null; then
    echo -e "${GREEN}✅ 統合APIサーバー起動確認${NC}"
else
    echo -e "${YELLOW}⚠️  統合APIサーバーが起動していません${NC}"
    echo -e "${YELLOW}  起動: python unified_api_server.py${NC}"
fi

# 完了メッセージ
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ デプロイ完了！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📊 サービスURL:"
echo "  - Ollama: http://localhost:11434"
echo "  - n8n: http://localhost:5678"
echo "  - Redis: localhost:6379"
echo "  - Traefik Dashboard: http://localhost:8080"
echo ""
echo "🧪 テスト実行:"
echo "  python always_ready_llm_client.py"
echo ""
echo "📊 パフォーマンス監視:"
echo "  python llm_performance_monitor.py"
echo ""






















