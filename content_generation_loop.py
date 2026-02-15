#!/usr/bin/env python3
"""
📝 Content Generation Loop - 成果物自動生成ループ
日報→ブログ草稿、構成ログ→note/Zenn記事、画像生成→テンプレ商品
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
import sqlite3

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator
from _paths import OLLAMA_PORT, RAG_MEMORY_PORT

# ロガーの初期化
logger = get_service_logger("content-generation-loop")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("ContentGeneration")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("ContentGeneration")

DEFAULT_OLLAMA_URL = f"http://127.0.0.1:{OLLAMA_PORT}"
DEFAULT_RAG_MEMORY_URL = f"http://127.0.0.1:{RAG_MEMORY_PORT}"


@dataclass
class GeneratedContent:
    """生成されたコンテンツ"""
    content_id: str
    source_type: str  # "daily_report", "config_log", "image_generation"
    source_id: str
    content_type: str  # "blog_draft", "note_article", "zenn_article", "template_product"
    title: str
    content: str
    status: str  # "draft", "published", "archived"
    created_at: str
    published_at: Optional[str]
    metadata: Dict[str, Any]


class ContentGenerationLoop:
    """成果物自動生成ループ"""
    
    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model: str = "qwen2.5:14b",
        rag_memory_url: Optional[str] = None,
        db_path: Optional[Path] = None,
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            ollama_url: Ollama API URL
            model: 使用するモデル
            rag_memory_url: RAG Memory API URL
            db_path: データベースパス
            config_path: 設定ファイルのパス
        """
        self.ollama_url = os.getenv("OLLAMA_URL", ollama_url or DEFAULT_OLLAMA_URL)
        self.model = model
        self.rag_memory_url = os.getenv("RAG_MEMORY_URL", rag_memory_url or DEFAULT_RAG_MEMORY_URL)
        self.config_path = config_path or Path(__file__).parent / "content_generation_config.json"
        self.config = self._load_config()
        
        # データベース初期化
        self.db_path = db_path or Path(__file__).parent / "content_generation.db"
        self._init_database()
        
        logger.info(f"✅ Content Generation Loop初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 設定ファイルの検証
                schema = {
                    "required": [],
                    "fields": {
                        "ollama_url": {"type": str, "default": DEFAULT_OLLAMA_URL},
                        "model": {"type": str, "default": "qwen2.5:14b"},
                        "auto_generate": {"type": bool, "default": True}
                    }
                }
                
                is_valid, errors = config_validator.validate_config(config, schema, self.config_path)
                if not is_valid:
                    logger.warning(f"設定ファイル検証エラー: {errors}")
                    # エラーがあってもデフォルト設定にマージして続行
                    default_config = self._get_default_config()
                    default_config.update(config)
                    return default_config
                
                return config
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(self.config_path)},
                    user_message="設定ファイルの読み込みに失敗しました"
                )
                logger.warning(f"設定読み込みエラー: {error.message}")
        
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "ollama_url": DEFAULT_OLLAMA_URL,
            "model": "qwen2.5:14b",
            "auto_generate": True,
            "generation_rules": {
                "daily_report": {
                    "enabled": True,
                    "target": "blog_draft",
                    "template": "blog_template"
                },
                "config_log": {
                    "enabled": True,
                    "target": ["note_article", "zenn_article"],
                    "template": "tech_article_template"
                },
                "image_generation": {
                    "enabled": True,
                    "target": "template_product",
                    "min_quality_score": 0.7
                }
            }
        }
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_contents (
                content_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                content_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL,
                published_at TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON generated_contents(source_type, source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON generated_contents(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON generated_contents(created_at DESC)")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def generate_blog_from_daily_report(self, daily_report: Dict[str, Any]) -> Optional[GeneratedContent]:
        """日報からブログ草稿を生成（下書きはLFM 2.5を使用）"""
        if not self.config.get("generation_rules", {}).get("daily_report", {}).get("enabled", True):
            return None
        
        # 日報の内容を取得
        report_content = daily_report.get("content", "")
        report_date = daily_report.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        # LLMでブログ草稿を生成（下書きはLFM 2.5を使用）
        prompt = f"""以下の日報を基に、ブログ記事の草稿を作成してください。

日報（{report_date}）:
{report_content}

以下の形式でブログ記事を作成してください:
- タイトル: 興味深いタイトル
- 導入: 読者の興味を引く導入
- 本文: 日報の内容を基に、読みやすい文章に変換
- まとめ: 簡潔なまとめ

JSON形式で回答してください:
{{
    "title": "タイトル",
    "content": "本文（マークダウン形式）"
}}"""
        
        try:
            # 下書き生成はLFM 2.5を使用（高速・軽量）
            try:
                import manaos_core_api as manaos
                draft_result = manaos.act("llm_call", {
                    "task_type": "lightweight_conversation",  # LFM 2.5使用
                    "prompt": prompt
                })
                result_text = draft_result.get("response", "")
                logger.info("✅ LFM 2.5で下書き生成完了")
            except Exception as e:
                logger.warning(f"LFM 2.5呼び出し失敗、従来モデルにフォールバック: {e}")
                # フォールバック: 従来のモデルを使用
                response = httpx.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 2000
                        }
                    },
                    timeout=timeout_config.get("llm_call", 30.0)
                )
                
                if response.status_code != 200:
                    logger.error(f"ブログ生成失敗: {response.status_code}")
                    return None
                
                result_text = response.json().get("response", "")
            
            # JSONを抽出
            try:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = result_text[json_start:json_end]
                    blog_data = json.loads(json_str)
                else:
                    return None
            except json.JSONDecodeError:
                logger.warning("JSON解析失敗")
                return None
            
            # GeneratedContentを作成
            content_id = f"blog_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(report_content) % 10000}"
            
            content = GeneratedContent(
                content_id=content_id,
                source_type="daily_report",
                source_id=daily_report.get("id", ""),
                content_type="blog_draft",
                title=blog_data.get("title", f"日報から生成された記事 - {report_date}"),
                content=blog_data.get("content", ""),
                status="draft",
                created_at=datetime.now().isoformat(),
                published_at=None,
                metadata={
                    "source_date": report_date,
                    "generation_model": self.model
                }
            )
            
            # データベースに保存
            self._save_content(content)
            
            logger.info(f"✅ ブログ草稿生成完了: {content_id}")
            return content
            
        except Exception as e:
            logger.error(f"ブログ生成エラー: {e}")
            return None
    
    def generate_article_from_config_log(self, config_log: Dict[str, Any]) -> List[GeneratedContent]:
        """構成ログからnote/Zenn記事を生成（下書きはLFM 2.5を使用）"""
        if not self.config.get("generation_rules", {}).get("config_log", {}).get("enabled", True):
            return []
        
        targets = self.config.get("generation_rules", {}).get("config_log", {}).get("target", ["note_article"])
        if not isinstance(targets, list):
            targets = [targets]
        
        log_content = config_log.get("content", "")
        log_title = config_log.get("title", "構成ログ")
        
        generated_contents = []
        
        for target in targets:
            if target == "note_article":
                content = self._generate_note_article(log_title, log_content, config_log)
            elif target == "zenn_article":
                content = self._generate_zenn_article(log_title, log_content, config_log)
            else:
                continue
            
            if content:
                generated_contents.append(content)
        
        return generated_contents
    
    def _generate_note_article(self, title: str, content: str, source: Dict[str, Any]) -> Optional[GeneratedContent]:
        """note記事を生成（下書きはLFM 2.5を使用）"""
        prompt = f"""以下の技術的な構成ログを基に、note記事を作成してください。

タイトル: {title}
内容:
{content}

以下の形式でnote記事を作成してください:
- タイトル: 技術的なタイトル
- 導入: 問題や背景の説明
- 本文: 構成の詳細、実装方法、学んだこと
- まとめ: 要点のまとめ

JSON形式で回答してください:
{{
    "title": "タイトル",
    "content": "本文（マークダウン形式）"
}}"""
        
        try:
            # 下書き生成はLFM 2.5を使用（高速・軽量）
            try:
                import manaos_core_api as manaos
                draft_result = manaos.act("llm_call", {
                    "task_type": "lightweight_conversation",  # LFM 2.5使用
                    "prompt": prompt
                })
                result_text = draft_result.get("response", "")
                logger.info("✅ LFM 2.5でnote記事下書き生成完了")
            except Exception as e:
                logger.warning(f"LFM 2.5呼び出し失敗、従来モデルにフォールバック: {e}")
                # フォールバック: 従来のモデルを使用
                response = httpx.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 3000
                        }
                    },
                    timeout=timeout_config.get("llm_call", 30.0)
                )
                
                if response.status_code != 200:
                    return None
                
                result_text = response.json().get("response", "")
            
            try:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = result_text[json_start:json_end]
                    article_data = json.loads(json_str)
                else:
                    return None
            except json.JSONDecodeError:
                return None
            
            content_id = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content) % 10000}"
            
            generated = GeneratedContent(
                content_id=content_id,
                source_type="config_log",
                source_id=source.get("id", ""),
                content_type="note_article",
                title=article_data.get("title", title),
                content=article_data.get("content", ""),
                status="draft",
                created_at=datetime.now().isoformat(),
                published_at=None,
                metadata={
                    "source_title": title,
                    "generation_model": self.model
                }
            )
            
            self._save_content(generated)
            logger.info(f"✅ note記事生成完了: {content_id}")
            return generated
            
        except Exception as e:
            logger.error(f"note記事生成エラー: {e}")
            return None
    
    def _generate_zenn_article(self, title: str, content: str, source: Dict[str, Any]) -> Optional[GeneratedContent]:
        """Zenn記事を生成（下書きはLFM 2.5を使用）"""
        prompt = f"""以下の技術的な構成ログを基に、Zenn記事を作成してください。

タイトル: {title}
内容:
{content}

Zenn記事の形式で作成してください:
- タイトル: 技術的なタイトル
- 導入: 問題や背景の説明
- 本文: 構成の詳細、実装方法、学んだこと
- まとめ: 要点のまとめ

JSON形式で回答してください:
{{
    "title": "タイトル",
    "content": "本文（マークダウン形式）"
}}"""
        
        try:
            # 下書き生成はLFM 2.5を使用（高速・軽量）
            try:
                import manaos_core_api as manaos
                draft_result = manaos.act("llm_call", {
                    "task_type": "lightweight_conversation",  # LFM 2.5使用
                    "prompt": prompt
                })
                result_text = draft_result.get("response", "")
                logger.info("✅ LFM 2.5でZenn記事下書き生成完了")
            except Exception as e:
                logger.warning(f"LFM 2.5呼び出し失敗、従来モデルにフォールバック: {e}")
                # フォールバック: 従来のモデルを使用
                response = httpx.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 3000
                        }
                    },
                    timeout=timeout_config.get("llm_call", 30.0)
                )
                
                if response.status_code != 200:
                    return None
                
                result_text = response.json().get("response", "")
            
            try:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = result_text[json_start:json_end]
                    article_data = json.loads(json_str)
                else:
                    return None
            except json.JSONDecodeError:
                return None
            
            content_id = f"zenn_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content) % 10000}"
            
            generated = GeneratedContent(
                content_id=content_id,
                source_type="config_log",
                source_id=source.get("id", ""),
                content_type="zenn_article",
                title=article_data.get("title", title),
                content=article_data.get("content", ""),
                status="draft",
                created_at=datetime.now().isoformat(),
                published_at=None,
                metadata={
                    "source_title": title,
                    "generation_model": self.model
                }
            )
            
            self._save_content(generated)
            logger.info(f"✅ Zenn記事生成完了: {content_id}")
            return generated
            
        except Exception as e:
            logger.error(f"Zenn記事生成エラー: {e}")
            return None
    
    def create_template_from_image(self, image_info: Dict[str, Any]) -> Optional[GeneratedContent]:
        """画像生成物をテンプレ商品として保存"""
        if not self.config.get("generation_rules", {}).get("image_generation", {}).get("enabled", True):
            return None
        
        # 品質スコアをチェック
        quality_score = image_info.get("quality_score", 0.5)
        min_quality = self.config.get("generation_rules", {}).get("image_generation", {}).get("min_quality_score", 0.7)
        
        if quality_score < min_quality:
            logger.info(f"品質スコアが低いためスキップ: {quality_score:.2f} < {min_quality}")
            return None
        
        image_path = image_info.get("path", "")
        prompt = image_info.get("prompt", "")
        
        content_id = f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(image_path) % 10000}"
        
        # テンプレート商品情報を生成
        template_content = f"""# 画像テンプレート

**プロンプト**: {prompt}
**画像パス**: {image_path}
**品質スコア**: {quality_score:.2f}

## 使用方法
この画像はテンプレートとして使用できます。

## メタデータ
- 生成日時: {datetime.now().isoformat()}
- 品質: {quality_score:.2f}
"""
        
        content = GeneratedContent(
            content_id=content_id,
            source_type="image_generation",
            source_id=image_info.get("id", ""),
            content_type="template_product",
            title=f"画像テンプレート - {prompt[:50]}",
            content=template_content,
            status="draft",
            created_at=datetime.now().isoformat(),
            published_at=None,
            metadata={
                "image_path": image_path,
                "prompt": prompt,
                "quality_score": quality_score
            }
        )
        
        self._save_content(content)
        logger.info(f"✅ テンプレート商品作成完了: {content_id}")
        return content
    
    def _save_content(self, content: GeneratedContent):
        """コンテンツをデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO generated_contents (
                content_id, source_type, source_id, content_type,
                title, content, status, created_at, published_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            content.content_id,
            content.source_type,
            content.source_id,
            content.content_type,
            content.title,
            content.content,
            content.status,
            content.created_at,
            content.published_at,
            json.dumps(content.metadata, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def get_generated_contents(
        self,
        content_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[GeneratedContent]:
        """生成されたコンテンツを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM generated_contents WHERE 1=1"
        params = []
        
        if content_type:
            query += " AND content_type = ?"
            params.append(content_type)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        contents = []
        for row in rows:
            contents.append(GeneratedContent(
                content_id=row[0],
                source_type=row[1],
                source_id=row[2],
                content_type=row[3],
                title=row[4],
                content=row[5],
                status=row[6],
                created_at=row[7],
                published_at=row[8],
                metadata=json.loads(row[9]) if row[9] else {}
            ))
        
        return contents


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルインスタンス
generator = None

def init_generator():
    """ジェネレーターを初期化"""
    global generator
    if generator is None:
        generator = ContentGenerationLoop()
    return generator

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Content Generation Loop"})

@app.route('/api/generate/blog', methods=['POST'])
def generate_blog_endpoint():
    """ブログ生成エンドポイント"""
    data = request.get_json() or {}
    daily_report = data.get("daily_report", {})
    
    if not daily_report:
        return jsonify({"error": "daily_report is required"}), 400
    
    generator = init_generator()
    content = generator.generate_blog_from_daily_report(daily_report)
    
    if not content:
        return jsonify({"error": "生成に失敗しました"}), 500
    
    return jsonify(asdict(content))

@app.route('/api/generate/article', methods=['POST'])
def generate_article_endpoint():
    """記事生成エンドポイント"""
    data = request.get_json() or {}
    config_log = data.get("config_log", {})
    
    if not config_log:
        return jsonify({"error": "config_log is required"}), 400
    
    generator = init_generator()
    contents = generator.generate_article_from_config_log(config_log)
    
    return jsonify({
        "results": [asdict(c) for c in contents],
        "count": len(contents)
    })

@app.route('/api/create/template', methods=['POST'])
def create_template_endpoint():
    """テンプレート作成エンドポイント"""
    data = request.get_json() or {}
    image_info = data.get("image_info", {})
    
    if not image_info:
        return jsonify({"error": "image_info is required"}), 400
    
    generator = init_generator()
    content = generator.create_template_from_image(image_info)
    
    if not content:
        return jsonify({"error": "テンプレート作成に失敗しました"}), 500
    
    return jsonify(asdict(content))

@app.route('/api/contents', methods=['GET'])
def get_contents_endpoint():
    """生成コンテンツ取得エンドポイント"""
    content_type = request.args.get("content_type")
    status = request.args.get("status")
    limit = request.args.get("limit", 20, type=int)
    
    generator = init_generator()
    contents = generator.get_generated_contents(content_type, status, limit)
    
    return jsonify({
        "results": [asdict(c) for c in contents],
        "count": len(contents)
    })


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5109))
    logger.info(f"📝 Content Generation Loop起動中... (ポート: {port})")
    init_generator()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

