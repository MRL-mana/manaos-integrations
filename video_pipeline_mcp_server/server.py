"""
ManaOS 動画パイプライン MCPサーバー
=====================================
VS Code / Cursorのチャットから以下の操作が可能:

ツール一覧:
  - generate_narration: ナレーション原稿を生成（品質担当: dolphin-llama3）
  - generate_titles: タイトル・テロップ・ハッシュタグ生成（速度担当: dolphin-mistral）
  - analyze_image: 画像解析・ALTテキスト生成（視覚担当: llava）
  - create_promo_video: プロモーション動画を全自動生成
  - create_slideshow: シンプルなスライドショー動画を生成
  - list_models: 利用可能なローカルLLMモデル一覧
  - system_check: パイプラインの依存関係・接続状態を診断
"""

import os
import sys
import json
import asyncio
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("WARNING: mcp package not found. Install with: pip install mcp", file=sys.stderr)

try:
    import requests
except ImportError:
    requests = None

# video_pipeline モジュール
try:
    from video_pipeline import VideoPipeline, LocalLLMClient, VoicevoxTTS, MOVIEPY_AVAILABLE
except ImportError:
    VideoPipeline = None
    LocalLLMClient = None
    VoicevoxTTS = None
    MOVIEPY_AVAILABLE = False

# ========================================
# MCPサーバー定義
# ========================================

if MCP_AVAILABLE:
    server = Server("video-pipeline")
else:
    server = None

# グローバルインスタンス（遅延初期化）
_pipeline = None
_llm = None


def _get_pipeline() -> "VideoPipeline":
    global _pipeline
    if _pipeline is None and VideoPipeline is not None:
        config_path = Path(__file__).parent.parent / "video_pipeline_config.json"
        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        _pipeline = VideoPipeline(config)
    return _pipeline


def _get_llm() -> "LocalLLMClient":
    global _llm
    if _llm is None and LocalLLMClient is not None:
        _llm = LocalLLMClient()
    return _llm


# ========================================
# ツール定義
# ========================================

if MCP_AVAILABLE:

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="generate_narration",
                description=(
                    "ローカルLLM（dolphin-llama3:8b）でナレーション原稿を生成。"
                    "検閲なし・感情豊かな文章が得意。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "ナレーションのテーマ・題材",
                        },
                        "style": {
                            "type": "string",
                            "description": "文体の指定（例: エモーショナルなレビュー、冷静な解説）",
                            "default": "エモーショナルで読者の興奮を誘うレビュー",
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "最大トークン数",
                            "default": 1024,
                        },
                    },
                    "required": ["topic"],
                },
            ),
            Tool(
                name="generate_titles",
                description=(
                    "ローカルLLM（dolphin-mistral:7b）でタイトル・テロップ・ハッシュタグを高速生成。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "テーマ",
                        },
                        "narration": {
                            "type": "string",
                            "description": "ナレーション概要（任意）",
                            "default": "",
                        },
                        "num_subtitles": {
                            "type": "integer",
                            "description": "テロップの数",
                            "default": 5,
                        },
                    },
                    "required": ["topic"],
                },
            ),
            Tool(
                name="analyze_image",
                description=(
                    "ローカルLLM（llava）で画像を解析し、説明文とSEO用ALTテキストを生成。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "解析する画像ファイルの絶対パス",
                        },
                        "prompt": {
                            "type": "string",
                            "description": "解析の指示（任意）",
                            "default": "この画像の内容を日本語で詳しく説明してください。",
                        },
                    },
                    "required": ["image_path"],
                },
            ),
            Tool(
                name="create_promo_video",
                description=(
                    "画像 + LLMナレーション + VOICEVOX音声合成 → MoviePyでプロモーション動画を全自動生成。"
                    "三銃士（dolphin-llama3/dolphin-mistral/llava）がフル活用される。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "images": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "使用する画像ファイルパスのリスト",
                        },
                        "topic": {
                            "type": "string",
                            "description": "動画のテーマ（LLMでナレーション自動生成に使用）",
                        },
                        "narration_text": {
                            "type": "string",
                            "description": "ナレーション原稿（指定しない場合LLMで自動生成）",
                            "default": "",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "出力先ファイルパス（省略時は自動命名）",
                            "default": "",
                        },
                        "speaker_id": {
                            "type": "integer",
                            "description": "VOICEVOXスピーカーID",
                            "default": 3,
                        },
                    },
                    "required": ["images", "topic"],
                },
            ),
            Tool(
                name="create_slideshow",
                description=(
                    "画像からシンプルなスライドショー動画を生成（LLM不使用、高速）。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "images": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "使用する画像ファイルパスのリスト",
                        },
                        "audio_path": {
                            "type": "string",
                            "description": "BGM音声ファイルパス（任意）",
                            "default": "",
                        },
                        "duration_per_image": {
                            "type": "number",
                            "description": "1画像あたりの秒数",
                            "default": 5.0,
                        },
                        "output_path": {
                            "type": "string",
                            "description": "出力先ファイルパス",
                            "default": "",
                        },
                    },
                    "required": ["images"],
                },
            ),
            Tool(
                name="uncensored_generate",
                description=(
                    "無検閲ローカルLLMで自由にテキスト生成。"
                    "モデルを指定して直接プロンプトを送信。検閲なし。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "プロンプト（指示文）",
                        },
                        "model": {
                            "type": "string",
                            "description": "使用モデル（dolphin-llama3:8b, dolphin-mistral:7b, etc）",
                            "default": "dolphin-llama3:8b",
                        },
                        "system": {
                            "type": "string",
                            "description": "システムプロンプト（任意）",
                            "default": "",
                        },
                        "temperature": {
                            "type": "number",
                            "description": "温度パラメータ（0.0-2.0）",
                            "default": 0.8,
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "最大トークン数",
                            "default": 2048,
                        },
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(
                name="list_models",
                description="Ollamaで利用可能なローカルLLMモデル一覧を取得",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="system_check",
                description="動画パイプラインの依存関係・外部サービス接続状態を診断",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            result = await _dispatch(name, arguments)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"エラー: {e}")]


# ========================================
# ツール実装
# ========================================


async def _dispatch(name: str, args: dict) -> str:
    if name == "generate_narration":
        return await _generate_narration(args)
    elif name == "generate_titles":
        return await _generate_titles(args)
    elif name == "analyze_image":
        return await _analyze_image(args)
    elif name == "create_promo_video":
        return await _create_promo_video(args)
    elif name == "create_slideshow":
        return await _create_slideshow(args)
    elif name == "uncensored_generate":
        return await _uncensored_generate(args)
    elif name == "list_models":
        return await _list_models()
    elif name == "system_check":
        return await _system_check()
    else:
        return f"不明なツール: {name}"


async def _generate_narration(args: dict) -> str:
    pipeline = _get_pipeline()
    if not pipeline:
        return "エラー: VideoPipelineが初期化できません"

    topic = args["topic"]
    style = args.get("style", "エモーショナルで読者の興奮を誘うレビュー")
    max_tokens = args.get("max_tokens", 1024)

    loop = asyncio.get_event_loop()
    narration = await loop.run_in_executor(
        None, lambda: pipeline.generate_narration(topic, style, max_tokens)
    )
    return json.dumps(
        {"status": "success", "topic": topic, "narration": narration, "model": "dolphin-llama3:8b"},
        ensure_ascii=False,
        indent=2,
    )


async def _generate_titles(args: dict) -> str:
    pipeline = _get_pipeline()
    if not pipeline:
        return "エラー: VideoPipelineが初期化できません"

    topic = args["topic"]
    narration = args.get("narration", "")
    num = args.get("num_subtitles", 5)

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(
        None, lambda: pipeline.generate_title_and_subtitles(topic, narration, num)
    )
    return json.dumps(
        {"status": "success", "model": "dolphin-mistral:7b", **data},
        ensure_ascii=False,
        indent=2,
    )


async def _analyze_image(args: dict) -> str:
    pipeline = _get_pipeline()
    if not pipeline:
        return "エラー: VideoPipelineが初期化できません"

    image_path = args["image_path"]
    prompt = args.get("prompt", "この画像の内容を日本語で詳しく説明してください。")

    if not os.path.exists(image_path):
        return f"エラー: 画像が見つかりません: {image_path}"

    loop = asyncio.get_event_loop()
    llm = _get_llm()
    description = await loop.run_in_executor(
        None, lambda: llm.analyze_image(image_path, prompt)
    )

    alt_text = description.split("。")[0] + "。" if "。" in description else description[:80]
    return json.dumps(
        {
            "status": "success",
            "model": "llava:latest",
            "image_path": image_path,
            "description": description,
            "alt_text": alt_text,
        },
        ensure_ascii=False,
        indent=2,
    )


async def _create_promo_video(args: dict) -> str:
    pipeline = _get_pipeline()
    if not pipeline:
        return "エラー: VideoPipelineが初期化できません"
    if not MOVIEPY_AVAILABLE:
        return "エラー: MoviePyが未インストールです。pip install moviepy"

    images = args["images"]
    topic = args["topic"]
    narration = args.get("narration_text", "") or None
    output = args.get("output_path", "") or None
    speaker_id = args.get("speaker_id", None)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: pipeline.create_promo_video(
            images=images,
            narration_text=narration,
            topic=topic,
            output_path=output,
            speaker_id=speaker_id,
            with_llm=True,
        ),
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


async def _create_slideshow(args: dict) -> str:
    pipeline = _get_pipeline()
    if not pipeline:
        return "エラー: VideoPipelineが初期化できません"

    images = args["images"]
    audio = args.get("audio_path", "") or None
    duration = args.get("duration_per_image", 5.0)
    output = args.get("output_path", "") or None

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: pipeline.create_simple_slideshow(images, audio, output, duration),
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


async def _uncensored_generate(args: dict) -> str:
    llm = _get_llm()
    if not llm:
        return "エラー: LocalLLMClientが初期化できません"

    prompt = args["prompt"]
    model = args.get("model", "dolphin-llama3:8b")
    system = args.get("system", "")
    temperature = args.get("temperature", 0.8)
    max_tokens = args.get("max_tokens", 2048)

    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(
        None,
        lambda: llm.generate(prompt, model, system, temperature, max_tokens),
    )
    return json.dumps(
        {"status": "success", "model": model, "response": text},
        ensure_ascii=False,
        indent=2,
    )


async def _list_models() -> str:
    try:
        loop = asyncio.get_event_loop()

        def _fetch():
            r = requests.get("http://localhost:11434/api/tags", timeout=5)
            return r.json().get("models", [])

        models = await loop.run_in_executor(None, _fetch)
        model_list = []
        for m in models:
            name = m.get("name", "")
            size_gb = round(m.get("size", 0) / 1e9, 1)
            role = ""
            if "dolphin-llama3" in name:
                role = "品質担当 (Quality)"
            elif "dolphin-mistral" in name:
                role = "速度担当 (Speed)"
            elif "llava" in name:
                role = "視覚担当 (Vision)"
            model_list.append({"name": name, "size_gb": size_gb, "role": role})

        return json.dumps(
            {"status": "success", "count": len(model_list), "models": model_list},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


async def _system_check() -> str:
    checks = {}

    # MoviePy
    checks["moviepy"] = MOVIEPY_AVAILABLE

    # Pillow
    try:
        from PIL import Image

        checks["pillow"] = True
    except ImportError:
        checks["pillow"] = False

    # Ollama
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        checks["ollama"] = {"connected": True, "models": models}
    except Exception:
        checks["ollama"] = {"connected": False, "models": []}

    # VOICEVOX
    try:
        r = requests.get("http://127.0.0.1:50021/version", timeout=3)
        checks["voicevox"] = {"connected": True, "version": r.text.strip('"')}
    except Exception:
        checks["voicevox"] = {"connected": False}

    # VideoPipeline
    checks["video_pipeline"] = VideoPipeline is not None

    return json.dumps(
        {"status": "success", "checks": checks},
        ensure_ascii=False,
        indent=2,
    )


# ========================================
# ヘルスチェックHTTPサーバー
# ========================================

HEALTH_PORT = int(os.getenv("VIDEO_PIPELINE_HEALTH_PORT", "5112"))


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            body = json.dumps(
                {
                    "status": "healthy",
                    "service": "video-pipeline-mcp",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            self.wfile.write(body.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # ログ抑制


def _start_health_server(port: int):
    httpd = HTTPServer(("127.0.0.1", port), HealthCheckHandler)
    httpd.serve_forever()


# ========================================
# メインエントリーポイント
# ========================================


async def main():
    # ヘルスチェックサーバーを起動（MCPが無くても生存確認できるようにする）
    health_thread = threading.Thread(
        target=_start_health_server, args=(HEALTH_PORT,), daemon=True
    )
    health_thread.start()
    print(f"ヘルスチェック: http://127.0.0.1:{HEALTH_PORT}/health", file=sys.stderr)

    if not MCP_AVAILABLE:
        print(
            "WARNING: mcp パッケージが見つかりません。MCP機能は無効ですが /health は稼働します。\n"
            "         対処: pip install mcp",
            file=sys.stderr,
        )
        # そのままプロセスを維持（ヘルスチェック用途）
        while True:
            await asyncio.sleep(3600)

    # MCPサーバーを起動（stdio通信）
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
