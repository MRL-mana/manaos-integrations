// PM2設定ファイル
module.exports = {
  apps: [{
    name: 'mrl-memory',
    script: 'mrl_memory_integration.py',
    interpreter: 'python3',
    env: {
      // 環境変数は .env ファイルから読み込む
      NODE_ENV: 'production'
    },
    env_file: '.env',
    instances: 1,
    exec_mode: 'fork',
    watch: false,
    max_memory_restart: '500M',
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s'
  }]
};
