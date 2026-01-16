#!/usr/bin/env node

/**
 * MCP Configuration Updater
 * .envファイルからAPIキーを読み込んで.mcp.jsonを更新するスクリプト
 */

const fs = require('fs');
const path = require('path');

function loadEnvFile() {
  const envPath = path.join(__dirname, '.env');
  
  if (!fs.existsSync(envPath)) {
    console.log('❌ .env file not found. Please run: node setup-mcp-keys.js');
    process.exit(1);
  }
  
  const envContent = fs.readFileSync(envPath, 'utf8');
  const env = {};
  
  envContent.split('\n').forEach(line => {
    const [key, ...valueParts] = line.split('=');
    if (key && valueParts.length > 0) {
      const value = valueParts.join('=').trim();
      if (!value.startsWith('your_') && !value.startsWith('#') && value !== '') {
        env[key.trim()] = value;
      }
    }
  });
  
  return env;
}

function updateMCPConfig(env) {
  const mcpConfigPath = path.join(__dirname, '.mcp.json');
  const mcpConfig = JSON.parse(fs.readFileSync(mcpConfigPath, 'utf8'));
  
  // 環境変数を更新
  Object.keys(mcpConfig.mcpServers).forEach(serverName => {
    const server = mcpConfig.mcpServers[serverName];
    if (server.env) {
      Object.keys(server.env).forEach(envKey => {
        if (env[envKey]) {
          server.env[envKey] = env[envKey];
          console.log(`✅ Updated ${serverName}: ${envKey}`);
        } else {
          console.log(`⚠️  Missing ${serverName}: ${envKey}`);
        }
      });
    }
  });
  
  // 設定ファイルを保存
  fs.writeFileSync(mcpConfigPath, JSON.stringify(mcpConfig, null, 2));
  console.log('\n✅ MCP configuration updated!');
}

function main() {
  console.log('🔄 Updating MCP Configuration...\n');
  
  try {
    const env = loadEnvFile();
    updateMCPConfig(env);
    
    console.log('\n📋 Configuration Summary:');
    console.log('========================');
    
    Object.keys(env).forEach(key => {
      const maskedValue = env[key].length > 8 
        ? env[key].substring(0, 4) + '*'.repeat(env[key].length - 8) + env[key].substring(env[key].length - 4)
        : '*'.repeat(env[key].length);
      console.log(`${key}: ${maskedValue}`);
    });
    
    console.log('\n🚀 Ready to use MCP servers!');
    
  } catch (error) {
    console.error('❌ Error updating configuration:', error.message);
    process.exit(1);
  }
}

main();
