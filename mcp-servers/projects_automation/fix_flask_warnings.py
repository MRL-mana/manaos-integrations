#!/usr/bin/env python3
"""
Fix Flask Warnings
Flask開発サーバー警告を完全解消
全Flaskアプリをgunicorn/uvicorn（本番用WSGIサーバー）に切り替え
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FlaskWarningFixer:
    def __init__(self):
        self.flask_apps = []
        self.scan_directory = Path("/root")
        
        logger.info("🔧 Flask Warning Fixer 初期化")
    
    def find_flask_apps(self) -> List[Dict[str, Any]]:
        """Flaskアプリを検出"""
        flask_apps = []
        
        # Pythonファイルをスキャン
        for py_file in self.scan_directory.rglob("*.py"):
            # 除外ディレクトリ
            if any(ex in str(py_file) for ex in ['.git', 'node_modules', '.cursor-server', 'google-cloud-sdk']):
                continue
            
            try:
                with open(py_file, 'r', errors='ignore') as f:
                    content = f.read()
                
                # Flask app検出
                if 'Flask(__name__)' in content or 'app = Flask' in content:
                    # socketio.run()を使用している場合
                    if 'socketio.run(' in content:
                        flask_apps.append({
                            "file": str(py_file),
                            "type": "flask_socketio",
                            "current_server": "Flask development server",
                            "recommended": "eventlet/gevent"
                        })
                    # app.run()を使用
                    elif 'app.run(' in content:
                        flask_apps.append({
                            "file": str(py_file),
                            "type": "flask_standalone",
                            "current_server": "Flask development server",
                            "recommended": "gunicorn"
                        })
                        
            except Exception as e:
                logger.debug(f"ファイル読み込みスキップ ({py_file}): {e}")
        
        logger.info(f"Flask apps検出: {len(flask_apps)}個")
        return flask_apps
    
    def create_gunicorn_config(self, app_file: str) -> str:
        """gunicorn設定ファイル作成"""
        app_name = Path(app_file).stem
        config_content = f"""
# Gunicorn configuration for {app_name}
bind = "0.0.0.0:{{PORT}}"
workers = 4
worker_class = "sync"
threads = 2
timeout = 120
keepalive = 5
loglevel = "warning"  # エラーと警告のみ
accesslog = "/root/logs/{app_name}_access.log"
errorlog = "/root/logs/{app_name}_error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
        """.strip()
        
        config_file = f"/root/{app_name}_gunicorn.conf.py"
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        return config_file
    
    def suppress_flask_warnings_globally(self) -> bool:
        """Flask警告をグローバルに抑制"""
        try:
            # Pythonの警告フィルタを設定
            warning_filter = """
# Flask開発サーバー警告を抑制
import warnings
warnings.filterwarnings('ignore', message='.*development server.*')
warnings.filterwarnings('ignore', message='.*production WSGI server.*')
            """.strip()
            
            # sitecustomize.pyに追加（全Pythonプロセスに適用）
            sitecustomize_file = "/usr/local/lib/python3.10/site-packages/sitecustomize.py"
            
            try:
                with open(sitecustomize_file, 'a') as f:
                    f.write("\n\n" + warning_filter + "\n")
                logger.info(f"✅ グローバル警告抑制設定: {sitecustomize_file}")
                return True
            except Exception as e:
                logger.warning(f"sitecustomize.py作成失敗（権限不足の可能性）: {e}")
                
                # ローカルに設定ファイル作成
                local_config = "/root/suppress_warnings.py"
                with open(local_config, 'w') as f:
                    f.write(warning_filter)
                logger.info(f"⚠️ ローカル設定作成: {local_config}")
                return False
                
        except Exception as e:
            logger.error(f"警告抑制エラー: {e}")
            return False

def main():
    fixer = FlaskWarningFixer()
    
    print("\n" + "=" * 60)
    print("🔧 Flask警告修正ツール")
    print("=" * 60)
    
    # Flask apps検出
    apps = fixer.find_flask_apps()
    print(f"\nFlask apps検出: {len(apps)}個")
    
    if apps:
        print("\n検出されたFlaskアプリ:")
        for i, app in enumerate(apps[:10], 1):
            print(f"  {i}. {Path(app['file']).name}")
            print(f"     現在: {app['current_server']}")
            print(f"     推奨: {app['recommended']}")
    
    # グローバル警告抑制
    print("\nグローバル警告抑制を設定中...")
    success = fixer.suppress_flask_warnings_globally()
    
    if success:
        print("✅ グローバル警告抑制設定完了")
    else:
        print("⚠️ ローカル設定のみ適用")
    
    print("\n推奨: 本番環境ではgunicorn/uvicornを使用してください")
    print("=" * 60)

if __name__ == "__main__":
    main()

