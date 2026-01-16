#!/usr/bin/env node
/**
 * AI Learning System MCP Server
 * パターン認識・学習・知識ベース管理
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// データディレクトリ
const DATA_DIR = path.join(__dirname, '../data');
const PATTERNS_FILE = path.join(DATA_DIR, 'learned_patterns.json');
const KNOWLEDGE_FILE = path.join(DATA_DIR, 'knowledge_base.json');
const LOGS_FILE = path.join(DATA_DIR, 'learning_logs.json');

// データ構造の初期化
async function ensureDataFiles() {
  await fs.mkdir(DATA_DIR, { recursive: true });
  
  const files = {
    [PATTERNS_FILE]: { patterns: [], lastUpdated: new Date().toISOString() },
    [KNOWLEDGE_FILE]: { entries: [], categories: {} },
    [LOGS_FILE]: { logs: [] }
  };
  
  for (const [file, defaultData] of Object.entries(files)) {
    try {
      await fs.access(file);
    } catch {
      await fs.writeFile(file, JSON.stringify(defaultData, null, 2));
    }
  }
}

// パターン学習
async function learnPattern(data) {
  const patterns = JSON.parse(await fs.readFile(PATTERNS_FILE, 'utf-8'));
  
  const newPattern = {
    id: `pattern_${Date.now()}`,
    timestamp: new Date().toISOString(),
    type: data.type || 'general',
    pattern: data.pattern,
    context: data.context || {},
    frequency: 1,
    confidence: data.confidence || 0.8
  };
  
  // 類似パターンをチェック
  const similarIndex = patterns.patterns.findIndex(p => 
    p.pattern === data.pattern && p.type === data.type
  );
  
  if (similarIndex >= 0) {
    // 既存パターンの頻度を更新
    patterns.patterns[similarIndex].frequency++;
    patterns.patterns[similarIndex].confidence = Math.min(
      1.0,
      patterns.patterns[similarIndex].confidence + 0.05
    );
    patterns.patterns[similarIndex].lastSeen = new Date().toISOString();
  } else {
    patterns.patterns.push(newPattern);
  }
  
  patterns.lastUpdated = new Date().toISOString();
  await fs.writeFile(PATTERNS_FILE, JSON.stringify(patterns, null, 2));
  
  // ログに記録
  await logLearning('pattern_learned', newPattern);
  
  return {
    success: true,
    pattern: similarIndex >= 0 ? patterns.patterns[similarIndex] : newPattern,
    action: similarIndex >= 0 ? 'updated' : 'created'
  };
}

// パターン検索
async function searchPatterns(query) {
  const patterns = JSON.parse(await fs.readFile(PATTERNS_FILE, 'utf-8'));
  
  const results = patterns.patterns.filter(p => {
    if (query.type && p.type !== query.type) return false;
    if (query.minConfidence && p.confidence < query.minConfidence) return false;
    if (query.pattern && !p.pattern.includes(query.pattern)) return false;
    return true;
  });
  
  // 頻度と信頼度でソート
  results.sort((a, b) => {
    const scoreA = a.frequency * a.confidence;
    const scoreB = b.frequency * b.confidence;
    return scoreB - scoreA;
  });
  
  return {
    total: results.length,
    patterns: results.slice(0, query.limit || 10)
  };
}

// ナレッジベース追加
async function addKnowledge(data) {
  const knowledge = JSON.parse(await fs.readFile(KNOWLEDGE_FILE, 'utf-8'));
  
  const entry = {
    id: `knowledge_${Date.now()}`,
    timestamp: new Date().toISOString(),
    title: data.title,
    content: data.content,
    category: data.category || 'general',
    tags: data.tags || [],
    metadata: data.metadata || {}
  };
  
  knowledge.entries.push(entry);
  
  // カテゴリ統計を更新
  if (!knowledge.categories[entry.category]) {
    knowledge.categories[entry.category] = 0;
  }
  knowledge.categories[entry.category]++;
  
  await fs.writeFile(KNOWLEDGE_FILE, JSON.stringify(knowledge, null, 2));
  await logLearning('knowledge_added', entry);
  
  return { success: true, entry };
}

// ナレッジ検索
async function searchKnowledge(query) {
  const knowledge = JSON.parse(await fs.readFile(KNOWLEDGE_FILE, 'utf-8'));
  
  const results = knowledge.entries.filter(entry => {
    if (query.category && entry.category !== query.category) return false;
    if (query.tags && !query.tags.some(tag => entry.tags.includes(tag))) return false;
    if (query.search) {
      const searchLower = query.search.toLowerCase();
      const titleMatch = entry.title.toLowerCase().includes(searchLower);
      const contentMatch = entry.content.toLowerCase().includes(searchLower);
      if (!titleMatch && !contentMatch) return false;
    }
    return true;
  });
  
  return {
    total: results.length,
    entries: results.slice(0, query.limit || 10),
    categories: knowledge.categories
  };
}

// 学習統計
async function getStats() {
  const patterns = JSON.parse(await fs.readFile(PATTERNS_FILE, 'utf-8'));
  const knowledge = JSON.parse(await fs.readFile(KNOWLEDGE_FILE, 'utf-8'));
  const logs = JSON.parse(await fs.readFile(LOGS_FILE, 'utf-8'));
  
  return {
    patterns: {
      total: patterns.patterns.length,
      byType: patterns.patterns.reduce((acc, p) => {
        acc[p.type] = (acc[p.type] || 0) + 1;
        return acc;
      }, {}),
      avgConfidence: patterns.patterns.reduce((sum, p) => sum + p.confidence, 0) / patterns.patterns.length || 0
    },
    knowledge: {
      total: knowledge.entries.length,
      categories: knowledge.categories
    },
    logs: {
      total: logs.logs.length,
      recentActivity: logs.logs.slice(-10)
    },
    lastUpdated: patterns.lastUpdated
  };
}

// ログ記録
async function logLearning(action, data) {
  const logs = JSON.parse(await fs.readFile(LOGS_FILE, 'utf-8'));
  
  logs.logs.push({
    timestamp: new Date().toISOString(),
    action,
    data
  });
  
  // 最新1000件のみ保持
  if (logs.logs.length > 1000) {
    logs.logs = logs.logs.slice(-1000);
  }
  
  await fs.writeFile(LOGS_FILE, JSON.stringify(logs, null, 2));
}

// MCPサーバー
class AILearningMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'ai-learning-system',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // ツール一覧
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'ai_learn_pattern',
          description: 'コードパターンや使用パターンを学習',
          inputSchema: {
            type: 'object',
            properties: {
              pattern: {
                type: 'string',
                description: '学習するパターン'
              },
              type: {
                type: 'string',
                description: 'パターンタイプ (code, workflow, error, api)',
                enum: ['code', 'workflow', 'error', 'api', 'general']
              },
              context: {
                type: 'object',
                description: '追加のコンテキスト情報'
              },
              confidence: {
                type: 'number',
                description: '信頼度 (0.0-1.0)'
              }
            },
            required: ['pattern']
          }
        },
        {
          name: 'ai_search_patterns',
          description: '学習済みパターンを検索',
          inputSchema: {
            type: 'object',
            properties: {
              type: {
                type: 'string',
                description: 'パターンタイプでフィルタ'
              },
              pattern: {
                type: 'string',
                description: 'パターン文字列で検索'
              },
              minConfidence: {
                type: 'number',
                description: '最小信頼度'
              },
              limit: {
                type: 'number',
                description: '結果の最大数'
              }
            }
          }
        },
        {
          name: 'ai_add_knowledge',
          description: 'ナレッジベースに知見を追加',
          inputSchema: {
            type: 'object',
            properties: {
              title: {
                type: 'string',
                description: 'タイトル'
              },
              content: {
                type: 'string',
                description: '内容'
              },
              category: {
                type: 'string',
                description: 'カテゴリ'
              },
              tags: {
                type: 'array',
                items: { type: 'string' },
                description: 'タグ'
              },
              metadata: {
                type: 'object',
                description: 'メタデータ'
              }
            },
            required: ['title', 'content']
          }
        },
        {
          name: 'ai_search_knowledge',
          description: 'ナレッジベースから検索',
          inputSchema: {
            type: 'object',
            properties: {
              search: {
                type: 'string',
                description: '検索クエリ'
              },
              category: {
                type: 'string',
                description: 'カテゴリでフィルタ'
              },
              tags: {
                type: 'array',
                items: { type: 'string' },
                description: 'タグでフィルタ'
              },
              limit: {
                type: 'number',
                description: '結果の最大数'
              }
            }
          }
        },
        {
          name: 'ai_get_stats',
          description: '学習統計を取得',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        }
      ]
    }));

    // ツール実行
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        const { name, arguments: args } = request.params;

        switch (name) {
          case 'ai_learn_pattern':
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(await learnPattern(args || {}), null, 2)
                }
              ]
            };

          case 'ai_search_patterns':
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(await searchPatterns(args || {}), null, 2)
                }
              ]
            };

          case 'ai_add_knowledge':
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(await addKnowledge(args || {}), null, 2)
                }
              ]
            };

          case 'ai_search_knowledge':
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(await searchKnowledge(args || {}), null, 2)
                }
              ]
            };

          case 'ai_get_stats':
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(await getStats(), null, 2)
                }
              ]
            };

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`
            }
          ],
          isError: true
        };
      }
    });
  }

  async run() {
    await ensureDataFiles();
    
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    
    console.error('AI Learning System MCP Server running on stdio');
  }
}

const server = new AILearningMCPServer();
server.run().catch(console.error);

