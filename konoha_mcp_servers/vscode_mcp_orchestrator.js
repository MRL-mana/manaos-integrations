#!/usr/bin/env node
/**
 * MCP Orchestrator - MCPサーバーの統合管理システム
 * VS Code MCP Container統合版
 */

const express = require('express');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const cors = require('cors');

class MCPOrchestrator {
    constructor() {
        this.app = express();
        this.mcpServers = new Map();
        this.port = process.env.PORT || 3001;
        this.clusterMode = process.env.CLUSTER_MODE === 'true';
        this.isMainServer = process.env.MAIN_SERVER === 'true';
        
        // ログファイル
        this.logFile = `/opt/mcp-orchestrator/mcp-orchestrator-${Date.now()}.log`;
        
        this.log('🚀 MCP Orchestrator 初期化開始');
        this.loadConfiguration();
        this.setupMiddleware();
        this.setupRoutes();
        this.startHealthMonitoring();
    }

    log(message, level = 'INFO') {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] [${level}] ${message}`;
        
        console.log(logMessage);
        
        // ファイルログ
        try {
            fs.appendFileSync(this.logFile, logMessage + '\n');
        } catch (error) {
            console.error('ログファイル書き込みエラー:', error);
        }
    }

    loadConfiguration() {
        try {
            const configPath = path.join(__dirname, '.mcp.json');
            if (fs.existsSync(configPath)) {
                const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
                this.config = config.mcpServers || {};
                this.log(`✅ MCP設定読み込み完了: ${Object.keys(this.config).length}個のサーバー`);
            } else {
                this.config = {};
                this.log('⚠️ MCP設定ファイルが見つかりません', 'WARNING');
            }
        } catch (error) {
            this.log(`❌ MCP設定読み込みエラー: ${error.message}`, 'ERROR');
            this.config = {};
        }
    }

    setupMiddleware() {
        this.app.use(cors());
        this.app.use(express.json());
        this.app.use(express.urlencoded({ extended: true }));
        
        // リクエストログ
        this.app.use((req, res, next) => {
            this.log(`${req.method} ${req.path} - ${req.ip}`);
            next();
        });
    }

    setupRoutes() {
        // ヘルスチェック
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                clusterMode: this.clusterMode,
                isMainServer: this.isMainServer,
                activeServers: this.mcpServers.size
            });
        });

        // MCPサーバー状態取得
        this.app.get('/api/mcp/status', (req, res) => {
            const status = {};
            for (const [name, server] of this.mcpServers) {
                status[name] = {
                    running: !server.killed,
                    pid: server.pid,
                    uptime: server.startTime ? Date.now() - server.startTime : 0
                };
            }
            
            res.json({
                servers: status,
                total: Object.keys(this.config).length,
                active: this.mcpServers.size,
                timestamp: new Date().toISOString()
            });
        });

        // MCPサーバー起動
        this.app.post('/api/mcp/start/:name', (req, res) => {
            const name = req.params.name;
            
            if (!this.config[name]) {
                return res.status(404).json({
                    success: false,
                    error: `サーバー設定が見つかりません: ${name}`
                });
            }

            if (this.mcpServers.has(name) && !this.mcpServers.get(name).killed) {
                return res.status(400).json({
                    success: false,
                    error: `サーバーは既に起動中です: ${name}`
                });
            }

            try {
                this.startMCPServer(name, this.config[name]);
                this.log(`✅ MCPサーバー起動完了: ${name}`);
                
                res.json({
                    success: true,
                    message: `${name} サーバーが起動しました`,
                    pid: this.mcpServers.get(name)?.pid
                });
            } catch (error) {
                this.log(`❌ MCPサーバー起動エラー ${name}: ${error.message}`, 'ERROR');
                res.status(500).json({
                    success: false,
                    error: error.message
                });
            }
        });

        // MCPサーバー停止
        this.app.post('/api/mcp/stop/:name', (req, res) => {
            const name = req.params.name;
            const server = this.mcpServers.get(name);
            
            if (!server) {
                return res.status(404).json({
                    success: false,
                    error: `サーバーが見つかりません: ${name}`
                });
            }

            try {
                server.kill('SIGTERM');
                this.mcpServers.delete(name);
                this.log(`✅ MCPサーバー停止完了: ${name}`);
                
                res.json({
                    success: true,
                    message: `${name} サーバーが停止しました`
                });
            } catch (error) {
                this.log(`❌ MCPサーバー停止エラー ${name}: ${error.message}`, 'ERROR');
                res.status(500).json({
                    success: false,
                    error: error.message
                });
            }
        });

        // 全サーバー起動
        this.app.post('/api/mcp/start-all', (req, res) => {
            const results = [];
            
            for (const [name, config] of Object.entries(this.config)) {
                try {
                    if (!this.mcpServers.has(name) || this.mcpServers.get(name).killed) {
                        this.startMCPServer(name, config);
                        results.push({ name, status: 'started' });
                    } else {
                        results.push({ name, status: 'already_running' });
                    }
                } catch (error) {
                    results.push({ name, status: 'error', error: error.message });
                }
            }
            
            this.log(`✅ 全MCPサーバー起動完了: ${results.length}個`);
            
            res.json({
                success: true,
                message: '全サーバーの起動処理が完了しました',
                results: results
            });
        });

        // 全サーバー停止
        this.app.post('/api/mcp/stop-all', (req, res) => {
            const results = [];
            
            for (const [name, server] of this.mcpServers) {
                try {
                    server.kill('SIGTERM');
                    results.push({ name, status: 'stopped' });
                } catch (error) {
                    results.push({ name, status: 'error', error: error.message });
                }
            }
            
            this.mcpServers.clear();
            this.log(`✅ 全MCPサーバー停止完了: ${results.length}個`);
            
            res.json({
                success: true,
                message: '全サーバーの停止処理が完了しました',
                results: results
            });
        });

        // ログ取得
        this.app.get('/api/mcp/logs', (req, res) => {
            try {
                const logs = fs.readFileSync(this.logFile, 'utf8');
                const lines = logs.split('\n').slice(-100); // 最新100行
                
                res.json({
                    success: true,
                    logs: lines,
                    totalLines: logs.split('\n').length
                });
            } catch (error) {
                res.status(500).json({
                    success: false,
                    error: 'ログファイルの読み込みに失敗しました'
                });
            }
        });
    }

    startMCPServer(name, config) {
        const args = config.args || [];
        const env = { ...process.env, ...config.env };
        
        this.log(`🚀 MCPサーバー起動中: ${name}`);
        this.log(`   コマンド: ${config.command} ${args.join(' ')}`);
        
        const server = spawn(config.command, args, {
            env,
            stdio: ['ignore', 'pipe', 'pipe'],
            detached: false
        });
        
        server.startTime = Date.now();
        
        // 標準出力
        server.stdout.on('data', (data) => {
            const message = data.toString().trim();
            if (message) {
                this.log(`[${name}] ${message}`);
            }
        });
        
        // 標準エラー
        server.stderr.on('data', (data) => {
            const message = data.toString().trim();
            if (message) {
                this.log(`[${name}] ${message}`, 'ERROR');
            }
        });
        
        // プロセス終了
        server.on('close', (code, signal) => {
            this.log(`[${name}] プロセス終了: code=${code}, signal=${signal}`);
            this.mcpServers.delete(name);
        });
        
        server.on('error', (error) => {
            this.log(`[${name}] プロセスエラー: ${error.message}`, 'ERROR');
            this.mcpServers.delete(name);
        });
        
        this.mcpServers.set(name, server);
        
        // 起動確認（少し待機）
        setTimeout(() => {
            if (!server.killed) {
                this.log(`✅ MCPサーバー起動確認: ${name} (PID: ${server.pid})`);
            }
        }, 2000);
        
        return server;
    }

    startHealthMonitoring() {
        // 5分ごとにヘルスチェック
        setInterval(() => {
            this.log(`💓 ヘルスチェック: 稼働中サーバー ${this.mcpServers.size}個`);
            
            // 停止したサーバーのクリーンアップ
            for (const [name, server] of this.mcpServers) {
                if (server.killed) {
                    this.log(`🧹 停止サーバーのクリーンアップ: ${name}`);
                    this.mcpServers.delete(name);
                }
            }
        }, 5 * 60 * 1000);
    }

    async start() {
        try {
            // 全MCPサーバーを起動
            this.log('🚀 全MCPサーバーを起動中...');
            
            for (const [name, config] of Object.entries(this.config)) {
                try {
                    this.startMCPServer(name, config);
                    // 起動間隔を空ける
                    await new Promise(resolve => setTimeout(resolve, 2000));
                } catch (error) {
                    this.log(`❌ MCPサーバー起動失敗 ${name}: ${error.message}`, 'ERROR');
                }
            }
            
            // Webサーバー起動
            this.app.listen(this.port, '0.0.0.0', () => {
                this.log(`🌐 MCP Orchestrator Webサーバー起動完了: http://0.0.0.0:${this.port}`);
                this.log(`📊 クラスターモード: ${this.clusterMode}`);
                this.log(`🎯 メインサーバー: ${this.isMainServer}`);
            });
            
        } catch (error) {
            this.log(`❌ MCP Orchestrator起動エラー: ${error.message}`, 'ERROR');
            process.exit(1);
        }
    }
}

// シグナルハンドリング
process.on('SIGTERM', () => {
    console.log('🛑 SIGTERM受信: MCP Orchestrator停止中...');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('🛑 SIGINT受信: MCP Orchestrator停止中...');
    process.exit(0);
});

// 起動
const orchestrator = new MCPOrchestrator();
orchestrator.start();
