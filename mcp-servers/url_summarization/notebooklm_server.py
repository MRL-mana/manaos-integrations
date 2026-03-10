#!/usr/bin/env python3
"""
NotebookLM風 統合サーバー
URL要約、ドキュメント管理、AI対話、音声メモ
"""

import os
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import anthropic
from typing import Dict

# モジュールインポート
from web_scraper import WebScraper
from youtube_handler import YouTubeHandler
from pdf_handler import PDFHandler
from twitter_handler import TwitterHandler
from instagram_handler import InstagramHandler
from search_integration import SearchIntegration
from info_collector import InfoCollector
from report_generator import ReportGenerator
from youtube_research import YouTubeResearch
from voice_memo import VoiceMemo
from timeline_viewer import TimelineViewer
from notification_system import NotificationSystem

# Flask設定
app = Flask(__name__)
CORS(app)

# ディレクトリ設定
WORK_DIR = Path("/root/url_summarization_system")
DATA_DIR = WORK_DIR / "data"
NOTES_DIR = DATA_DIR / "notebooks"
UPLOADS_DIR = DATA_DIR / "uploads"
AUDIO_DIR = DATA_DIR / "audio"

# ディレクトリ作成
for dir_path in [DATA_DIR, NOTES_DIR, UPLOADS_DIR, AUDIO_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ハンドラー初期化
web_scraper = WebScraper()
youtube_handler = YouTubeHandler()
pdf_handler = PDFHandler()
twitter_handler = TwitterHandler()
instagram_handler = InstagramHandler()
search_integration = SearchIntegration()
info_collector = InfoCollector()
report_generator = ReportGenerator()
youtube_research = YouTubeResearch()  # type: ignore
voice_memo = VoiceMemo()
timeline_viewer = TimelineViewer()
notification_system = NotificationSystem()

# Claude API設定
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


# ===== ノートブック管理 =====

class NotebookManager:
    """ノートブック管理"""

    def __init__(self):
        self.notebooks = {}
        self.load_notebooks()

    def load_notebooks(self):
        """ノートブック読み込み"""
        for notebook_file in NOTES_DIR.glob("*.json"):
            with open(notebook_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.notebooks[data['id']] = data

    def create_notebook(self, title: str) -> Dict:
        """ノートブック作成"""
        notebook_id = f"nb_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        notebook = {
            "id": notebook_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "sources": [],
            "notes": [],
            "summary": ""
        }
        self.notebooks[notebook_id] = notebook
        self.save_notebook(notebook_id)
        return notebook

    def save_notebook(self, notebook_id: str):
        """ノートブック保存"""
        if notebook_id in self.notebooks:
            notebook = self.notebooks[notebook_id]
            notebook['updated_at'] = datetime.now().isoformat()
            notebook_file = NOTES_DIR / f"{notebook_id}.json"
            with open(notebook_file, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, ensure_ascii=False, indent=2)

    def add_source(self, notebook_id: str, source: Dict):
        """ソース追加"""
        if notebook_id in self.notebooks:
            self.notebooks[notebook_id]['sources'].append(source)
            self.save_notebook(notebook_id)

    def add_note(self, notebook_id: str, note: Dict):
        """ノート追加"""
        if notebook_id in self.notebooks:
            self.notebooks[notebook_id]['notes'].append(note)
            self.save_notebook(notebook_id)

    def generate_summary(self, notebook_id: str) -> str:
        """サマリー生成"""
        if notebook_id not in self.notebooks:
            return ""

        notebook = self.notebooks[notebook_id]
        sources_text = "\n\n".join([
            f"【{s['title']}】\n{s.get('content', s.get('text', ''))[:500]}"
            for s in notebook['sources']
        ])

        if not sources_text:
            return "ソースがありません"

        if not claude_client:
            return "Claude APIキーが設定されていません"

        try:
            prompt = f"""以下のドキュメントを要約してください。

{sources_text}

要約のポイント:
- 主要な内容を3-5つのポイントで整理
- 重要な数値やデータがあれば含める
- 簡潔で分かりやすく"""

            response = claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            summary = response.content[0].text  # type: ignore
            notebook['summary'] = summary
            self.save_notebook(notebook_id)
            return summary

        except Exception as e:
            return f"要約生成エラー: {str(e)}"


# ノートブックマネージャー初期化
notebook_manager = NotebookManager()


# ===== API エンドポイント =====

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "NotebookLM風 統合サーバー",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/notebooks', methods=['GET'])
def list_notebooks():
    """ノートブック一覧"""
    notebooks = [
        {
            "id": nb['id'],
            "title": nb['title'],
            "created_at": nb['created_at'],
            "updated_at": nb['updated_at'],
            "source_count": len(nb['sources']),
            "note_count": len(nb['notes'])
        }
        for nb in notebook_manager.notebooks.values()
    ]
    return jsonify({"success": True, "notebooks": notebooks})


@app.route('/api/notebooks', methods=['POST'])
def create_notebook():
    """ノートブック作成"""
    data = request.json
    title = data.get('title', '新しいノートブック')
    notebook = notebook_manager.create_notebook(title)
    return jsonify({"success": True, "notebook": notebook})


@app.route('/api/notebooks/<notebook_id>', methods=['GET'])
def get_notebook(notebook_id):
    """ノートブック取得"""
    if notebook_id in notebook_manager.notebooks:
        return jsonify({
            "success": True,
            "notebook": notebook_manager.notebooks[notebook_id]
        })
    return jsonify({"success": False, "error": "ノートブックが見つかりません"}), 404


@app.route('/api/notebooks/<notebook_id>/sources', methods=['POST'])
def add_source(notebook_id):
    """ソース追加"""
    data = request.json
    source_type = data.get('type')  # web, youtube, pdf, twitter, instagram
    url = data.get('url')

    if not url:
        return jsonify({"success": False, "error": "URLが必要です"}), 400

    # ソース取得
    source = None
    if source_type == 'web':
        result = web_scraper.scrape(url)
        if result['success']:
            source = {
                "type": "web",
                "url": url,
                "title": result['title'],
                "content": result['content'],
                "meta": result['meta'],
                "added_at": datetime.now().isoformat()
            }
    elif source_type == 'youtube':
        result = youtube_handler.process(url)
        if result['success']:
            source = {
                "type": "youtube",
                "url": url,
                "title": result['video_info']['title'],
                "description": result['video_info']['description'],
                "transcript": result['transcript']['text'],
                "added_at": datetime.now().isoformat()
            }
    elif source_type == 'pdf':
        # PDFファイルアップロード処理
        return jsonify({"success": False, "error": "PDF処理は別エンドポイントを使用"}), 400
    elif source_type == 'twitter':
        result = twitter_handler.get_tweet(url)
        if result['success']:
            tweet = result['tweet']
            source = {
                "type": "twitter",
                "url": url,
                "title": f"@{tweet['user']}のツイート",
                "content": tweet['content'],
                "added_at": datetime.now().isoformat()
            }
    elif source_type == 'instagram':
        # Seleniumを使用するかどうか（デフォルト: False = requests版を使用）
        use_selenium = data.get('use_selenium', False)
        result = instagram_handler.get_post(url, use_selenium=use_selenium)
        if result['success']:
            post = result['post']
            source = {
                "type": "instagram",
                "url": url,
                "title": post.get('title', f"{post.get('username', 'Instagram')}の投稿"),
                "content": post.get('caption', post.get('description', '')),
                "image_url": post.get('image_url', ''),
                "likes": post.get('likes', '0'),
                "comments": post.get('comments', '0'),
                "added_at": datetime.now().isoformat()
            }

    if source:
        notebook_manager.add_source(notebook_id, source)
        return jsonify({"success": True, "source": source})
    else:
        return jsonify({"success": False, "error": "ソース取得失敗"}), 500


@app.route('/api/notebooks/<notebook_id>/summary', methods=['POST'])
def generate_summary(notebook_id):
    """サマリー生成"""
    summary = notebook_manager.generate_summary(notebook_id)
    return jsonify({"success": True, "summary": summary})


@app.route('/api/notebooks/<notebook_id>/chat', methods=['POST'])
def chat(notebook_id):
    """AI対話"""
    if notebook_id not in notebook_manager.notebooks:
        return jsonify({"success": False, "error": "ノートブックが見つかりません"}), 404

    data = request.json
    question = data.get('question')

    if not question:
        return jsonify({"success": False, "error": "質問が必要です"}), 400

    if not claude_client:
        return jsonify({"success": False, "error": "Claude APIキーが設定されていません"}), 500

    notebook = notebook_manager.notebooks[notebook_id]

    # コンテキスト作成
    context = f"""以下のドキュメントに基づいて質問に答えてください。

【ドキュメント】
{chr(10).join([
    f"【{s['title']}】{s.get('content', s.get('text', ''))[:1000]}"
    for s in notebook['sources']
])}

【質問】
{question}

回答は、該当するソースを引用しながら説明してください。"""

    try:
        response = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": context
            }]
        )

        answer = response.content[0].text  # type: ignore

        # ノートに追加
        notebook_manager.add_note(notebook_id, {
            "type": "chat",
            "question": question,
            "answer": answer,
            "created_at": datetime.now().isoformat()
        })

        return jsonify({"success": True, "answer": answer})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/upload/pdf', methods=['POST'])
def upload_pdf():
    """PDFアップロード"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "ファイルが必要です"}), 400

    file = request.files['file']
    notebook_id = request.form.get('notebook_id')

    if not notebook_id:
        return jsonify({"success": False, "error": "notebook_idが必要です"}), 400

    # 一時保存
    temp_path = UPLOADS_DIR / f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    file.save(temp_path)

    # PDF処理
    result = pdf_handler.process(str(temp_path))

    if result['success']:
        source = {
            "type": "pdf",
            "title": result['metadata'].get('title', 'PDFドキュメント'),
            "content": result['text'],
            "metadata": result['metadata'],
            "added_at": datetime.now().isoformat()
        }
        notebook_manager.add_source(notebook_id, source)

        # ファイル削除
        if temp_path.exists():
            temp_path.unlink()

        return jsonify({"success": True, "source": source})
    else:
        return jsonify({"success": False, "error": result['error']}), 500


@app.route('/api/search', methods=['POST'])
def search():
    """検索実行"""
    data = request.json
    query = data.get('query')
    count = data.get('count', 10)

    if not query:
        return jsonify({"success": False, "error": "検索クエリが必要です"}), 400

    result = search_integration.search_multiple(query, count)
    return jsonify(result)


@app.route('/api/collect', methods=['POST'])
def collect():
    """自動情報収集"""
    data = request.json
    query = data.get('query')
    max_results = data.get('max_results', 5)

    if not query:
        return jsonify({"success": False, "error": "検索クエリが必要です"}), 400

    result = info_collector.collect_and_summarize(query, max_results)
    return jsonify(result)


@app.route('/api/competitive', methods=['POST'])
def competitive():
    """競合分析"""
    data = request.json
    companies = data.get('companies', [])

    if not companies:
        return jsonify({"success": False, "error": "企業リストが必要です"}), 400

    result = info_collector.competitive_analysis(companies)
    return jsonify(result)


@app.route('/api/news', methods=['POST'])
def news():
    """ニュース監視"""
    data = request.json
    keywords = data.get('keywords', [])
    max_results = data.get('max_results', 5)

    if not keywords:
        return jsonify({"success": False, "error": "キーワードリストが必要です"}), 400

    result = info_collector.news_monitoring(keywords, max_results)
    return jsonify(result)


@app.route('/api/report/excel', methods=['POST'])
def generate_excel_report():
    """Excelレポート生成"""
    data = request.json

    filename = report_generator.generate_excel_report(data)

    if filename.startswith("エラー"):
        return jsonify({"success": False, "error": filename}), 500

    return jsonify({"success": True, "filepath": filename})


@app.route('/api/report/markdown', methods=['POST'])
def generate_markdown_report():
    """Markdownレポート生成"""
    data = request.json

    filename = report_generator.generate_markdown_report(data)

    if filename.startswith("エラー"):
        return jsonify({"success": False, "error": filename}), 500

    return jsonify({"success": True, "filepath": filename})


@app.route('/api/report/comparison', methods=['POST'])
def generate_comparison_report():
    """比較レポート生成"""
    data = request.json

    filename = report_generator.generate_comparison_report(data)

    if filename.startswith("エラー"):
        return jsonify({"success": False, "error": filename}), 500

    return jsonify({"success": True, "filepath": filename})


@app.route('/api/report/chart', methods=['POST'])
def generate_chart():
    """グラフ生成"""
    data = request.json
    chart_type = data.get('chart_type', 'bar')

    filepath = report_generator.generate_chart(data, chart_type)

    if filepath.startswith("エラー"):
        return jsonify({"success": False, "error": filepath}), 500

    return jsonify({"success": True, "filepath": filepath})


@app.route('/api/youtube/search', methods=['POST'])
def youtube_search():
    """YouTube検索"""
    data = request.json
    query = data.get('query')
    max_results = data.get('max_results', 5)

    if not query:
        return jsonify({"success": False, "error": "検索クエリが必要です"}), 400

    result = youtube_research.search_youtube(query, max_results)  # type: ignore
    return jsonify(result)


@app.route('/api/youtube/research', methods=['POST'])
def youtube_research():
    """YouTube研究"""
    data = request.json
    query = data.get('query')
    max_results = data.get('max_results', 3)

    if not query:
        return jsonify({"success": False, "error": "検索クエリが必要です"}), 400

    result = youtube_research.research_and_summarize(query, max_results)  # type: ignore
    return jsonify(result)


@app.route('/api/youtube/compare', methods=['POST'])
def youtube_compare():
    """動画比較"""
    data = request.json
    video_urls = data.get('video_urls', [])

    if not video_urls:
        return jsonify({"success": False, "error": "動画URLリストが必要です"}), 400

    result = youtube_research.compare_videos(video_urls)  # type: ignore
    return jsonify(result)


@app.route('/api/voice/transcribe', methods=['POST'])
def transcribe_audio():
    """音声文字起こし"""
    if 'audio' not in request.files:
        return jsonify({"success": False, "error": "音声ファイルが必要です"}), 400

    audio_file = request.files['audio']
    language = request.form.get('language', 'ja')

    # 一時保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_path = AUDIO_DIR / f"audio_{timestamp}.{audio_file.filename.split('.')[-1]}"  # type: ignore[union-attr]
    audio_file.save(temp_path)

    # 文字起こし
    result = voice_memo.transcribe_audio(str(temp_path), language)

    # ファイル削除
    if temp_path.exists():
        temp_path.unlink()

    return jsonify(result)


@app.route('/api/timeline/<notebook_id>', methods=['GET'])
def get_timeline(notebook_id):
    """タイムライン取得"""
    result = timeline_viewer.get_timeline(notebook_id)
    return jsonify(result)


@app.route('/api/timeline/<notebook_id>/statistics', methods=['GET'])
def get_statistics(notebook_id):
    """統計情報取得"""
    result = timeline_viewer.get_statistics(notebook_id)
    return jsonify(result)


@app.route('/api/timeline/<notebook_id>/search', methods=['POST'])
def search_timeline(notebook_id):
    """タイムライン検索"""
    data = request.json
    query = data.get('query')

    if not query:
        return jsonify({"success": False, "error": "検索クエリが必要です"}), 400

    result = timeline_viewer.search_timeline(notebook_id, query)
    return jsonify(result)


@app.route('/api/notify/line', methods=['POST'])
def send_line_notification():
    """LINE通知送信"""
    data = request.json
    message = data.get('message')

    if not message:
        return jsonify({"success": False, "error": "メッセージが必要です"}), 400

    result = notification_system.send_line_notification(message)
    return jsonify(result)


@app.route('/api/notify/slack', methods=['POST'])
def send_slack_notification():
    """Slack通知送信"""
    data = request.json
    message = data.get('message')
    channel = data.get('channel', '#general')

    if not message:
        return jsonify({"success": False, "error": "メッセージが必要です"}), 400

    result = notification_system.send_slack_notification(message, channel)
    return jsonify(result)


@app.route('/api/notify/alert', methods=['POST'])
def send_alert():
    """アラート送信"""
    data = request.json
    title = data.get('title')
    message = data.get('message')
    level = data.get('level', 'info')

    if not title or not message:
        return jsonify({"success": False, "error": "タイトルとメッセージが必要です"}), 400

    result = notification_system.send_alert(title, message, level)
    return jsonify(result)


@app.route('/')
def index():
    """Webインターフェース"""
    html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📚 NotebookLM風 統合システム</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { color: #667eea; margin-bottom: 30px; font-size: 2.5em; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #764ba2; margin-bottom: 20px; font-size: 1.8em; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            margin: 5px;
            transition: transform 0.2s;
        }
        .btn:hover { transform: scale(1.05); }
        .input-group {
            margin-bottom: 15px;
        }
        .input-group input, .input-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
        }
        .input-group textarea {
            min-height: 120px;
            resize: vertical;
        }
        .result {
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 NotebookLM風 統合システム</h1>

        <div class="section">
            <h2>📝 新しいノートブック作成</h2>
            <div class="input-group">
                <input type="text" id="notebookTitle" placeholder="ノートブックのタイトル">
            </div>
            <button class="btn" onclick="createNotebook()">作成</button>
        </div>

        <div class="section">
            <h2>🔗 ソース追加</h2>
            <div class="input-group">
                <select id="sourceType">
                    <option value="web">Webページ</option>
                    <option value="youtube">YouTube動画</option>
                    <option value="twitter">Twitter/X</option>
                    <option value="instagram">Instagram</option>
                </select>
            </div>
            <div class="input-group">
                <input type="text" id="sourceUrl" placeholder="URLを入力">
            </div>
            <div class="input-group">
                <input type="text" id="notebookId" placeholder="ノートブックID">
            </div>
            <button class="btn" onclick="addSource()">追加</button>
        </div>

        <div class="section">
            <h2>💬 AI対話</h2>
            <div class="input-group">
                <input type="text" id="chatNotebookId" placeholder="ノートブックID">
            </div>
            <div class="input-group">
                <textarea id="question" placeholder="質問を入力"></textarea>
            </div>
            <button class="btn" onclick="chat()">送信</button>
            <div id="chatResult" class="result" style="display:none;"></div>
        </div>

        <div class="section">
            <h2>📊 サマリー生成</h2>
            <div class="input-group">
                <input type="text" id="summaryNotebookId" placeholder="ノートブックID">
            </div>
            <button class="btn" onclick="generateSummary()">生成</button>
            <div id="summaryResult" class="result" style="display:none;"></div>
        </div>
    </div>

    <script>
        async function createNotebook() {
            const title = document.getElementById('notebookTitle').value;
            const res = await fetch('/api/notebooks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title})
            });
            const data = await res.json();
            alert('ノートブック作成: ' + data.notebook.id);
        }

        async function addSource() {
            const type = document.getElementById('sourceType').value;
            const url = document.getElementById('sourceUrl').value;
            const notebookId = document.getElementById('notebookId').value;

            const res = await fetch(`/api/notebooks/${notebookId}/sources`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({type, url})
            });
            const data = await res.json();
            alert(data.success ? '追加成功' : data.error);
        }

        async function chat() {
            const notebookId = document.getElementById('chatNotebookId').value;
            const question = document.getElementById('question').value;

            const res = await fetch(`/api/notebooks/${notebookId}/chat`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question})
            });
            const data = await res.json();

            const result = document.getElementById('chatResult');
            result.style.display = 'block';
            result.textContent = data.answer || data.error;
        }

        async function generateSummary() {
            const notebookId = document.getElementById('summaryNotebookId').value;

            const res = await fetch(`/api/notebooks/${notebookId}/summary`, {
                method: 'POST'
            });
            const data = await res.json();

            const result = document.getElementById('summaryResult');
            result.style.display = 'block';
            result.textContent = data.summary;
        }
    </script>
</body>
</html>
    """
    return render_template_string(html)


if __name__ == '__main__':
    print("=" * 60)
    print("📚 NotebookLM風 統合サーバー起動")
    print("=" * 60)
    print("API: http://0.0.0.0:5020")
    print("Web: http://localhost:5020")
    print("Ctrl+C で停止")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5023, debug=os.getenv("DEBUG", "False").lower() == "true")

