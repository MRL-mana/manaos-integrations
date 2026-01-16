#!/usr/bin/env node

/**
 * MCP API Keys Setup Script
 * インタラクティブにAPIキーを設定するスクリプト
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const question = (query) => new Promise((resolve) => rl.question(query, resolve));

async function setupAPIKeys() {
  console.log('🔑 MCP API Keys Setup');
  console.log('====================\n');
  
  const envPath = path.join(__dirname, '.env');
  let envContent = '';
  
  // 既存の.envファイルがあるかチェック
  if (fs.existsSync(envPath)) {
    envContent = fs.readFileSync(envPath, 'utf8');
    console.log('📁 Existing .env file found. Updating...\n');
  } else {
    console.log('📁 Creating new .env file...\n');
  }
  
  const keys = [
    {
      name: 'FIGMA_ACCESS_TOKEN',
      description: 'Figma Access Token (for design-to-code conversion)',
      required: false
    },
    {
      name: 'POSTGRES_CONNECTION_STRING',
      description: 'PostgreSQL Connection String (for database operations)',
      required: false
    },
    {
      name: 'GITHUB_PERSONAL_ACCESS_TOKEN',
      description: 'GitHub Personal Access Token (for repository operations)',
      required: false
    },
    {
      name: 'NOTION_API_KEY',
      description: 'Notion API Key (for note-taking and documentation)',
      required: false
    },
    {
      name: 'STRIPE_SECRET_KEY',
      description: 'Stripe Secret Key (for payment processing)',
      required: false
    },
    {
      name: 'BRAVE_API_KEY',
      description: 'Brave Search API Key (for web search)',
      required: false
    },
    {
      name: 'CONTEXT7_API_KEY',
      description: 'Context7 API Key (for documentation search)',
      required: false
    },
    {
      name: 'SERENA_API_KEY',
      description: 'Serena API Key (for codebase search)',
      required: false
    }
  ];
  
  let newEnvContent = '';
  
  for (const key of keys) {
    const currentValue = getEnvValue(envContent, key.name);
    const prompt = currentValue 
      ? `Enter ${key.description} (current: ${maskValue(currentValue)}) [Enter to keep current]: `
      : `Enter ${key.description}${key.required ? ' (required)' : ' (optional)'}: `;
    
    const input = await question(prompt);
    
    if (input.trim()) {
      newEnvContent += `${key.name}=${input.trim()}\n`;
    } else if (currentValue) {
      newEnvContent += `${key.name}=${currentValue}\n`;
    } else if (!key.required) {
      newEnvContent += `# ${key.name}=your_${key.name.toLowerCase()}_here\n`;
    }
  }
  
  // .envファイルを保存
  fs.writeFileSync(envPath, newEnvContent);
  
  console.log('\n✅ API Keys configuration saved to .env file!');
  console.log('\n📋 Next steps:');
  console.log('1. Review your .env file');
  console.log('2. Run: node update-mcp-config.js');
  console.log('3. Test: node test-mcp-servers.js');
  
  rl.close();
}

function getEnvValue(content, keyName) {
  const regex = new RegExp(`^${keyName}=(.+)$`, 'm');
  const match = content.match(regex);
  return match ? match[1] : null;
}

function maskValue(value) {
  if (value.length <= 8) return '*'.repeat(value.length);
  return value.substring(0, 4) + '*'.repeat(value.length - 8) + value.substring(value.length - 4);
}

setupAPIKeys().catch(console.error);
