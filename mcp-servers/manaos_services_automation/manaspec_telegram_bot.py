#!/usr/bin/env python3
"""
🤖 ManaSpec Telegram Bot
Telegramから ManaSpec を完全操作

コマンド:
  /status - 全体ステータス確認
  /propose <機能> - 新しいProposal作成
  /list - Changes一覧
  /specs - Specs一覧
  /archives - Archives一覧
  /dashboard - Dashboard URL取得
  /help - ヘルプ
"""

import os
import sys
import logging
import requests
import time
import hashlib
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Trinity Consciousness System統合
sys.path.insert(0, '/root/trinity_workspace/bridge')
sys.path.insert(0, '/root/trinity_workspace/evolution')

# 記憶システム統合（logger初期化前にインポート）
sys.path.insert(0, '/root/manaos-knowledge/tools')
MEMORY_SYSTEM_AVAILABLE = False
try:
    from memory_ingestor import MemoryIngestor
    MEMORY_SYSTEM_AVAILABLE = True
except ImportError:
    MEMORY_SYSTEM_AVAILABLE = False
    # loggerはまだ初期化されていないので後でログ出力

TRINITY_INTEGRATED = False
try:
    from cognitive_bridge import CognitiveBridge
    from emotion_system import EmotionSystem
    from consciousness_state import ConsciousnessState
    TRINITY_INTEGRATED = True
except ImportError:
    pass  # logger初期化前なので後でログ出力

# Telegram Bot Token（環境変数から取得）
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ManaSpec API
MANASPEC_API = "http://localhost:9301/api/manaspec"
UNIFIED_ORCH_API = "http://localhost:9102/api/manaspec"

# Ollama API
OLLAMA_URL = "http://localhost:11434"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# エラーメッセージキャッシュ（重複送信防止）
_error_cache = {}
ERROR_CACHE_TIMEOUT = 60  # 60秒間は同じエラーメッセージを送信しない

# 応答キャッシュ（同じ質問に素早く応答）
_response_cache = {}
CACHE_EXPIRY_HOURS = 24  # 24時間キャッシュを保持

# パフォーマンス監視
_performance_stats = {
    'total_requests': 0,
    'successful_requests': 0,
    'failed_requests': 0,
    'total_response_time': 0.0,
    'model_usage': defaultdict(int),
    'error_types': defaultdict(int)
}

# Trinity統合状態をログ
if TRINITY_INTEGRATED:
    logger.info("🧠 Trinity Consciousness System統合完了")
else:
    logger.warning("⚠️ Trinity統合スキップ（通常モード）")

# Trinity意識システム初期化
trinity_bridge = None
trinity_emotion = None
trinity_consciousness = None

# 記憶システム初期化（main関数内で初期化）
memory_ingestor = None

def init_trinity_systems():
    """Trinity意識システムを初期化"""
    global trinity_bridge, trinity_emotion, trinity_consciousness, TRINITY_INTEGRATED

    try:
        from cognitive_bridge import CognitiveBridge
        from emotion_system import EmotionSystem
        from consciousness_state import ConsciousnessState

        trinity_bridge = CognitiveBridge()
        trinity_bridge.start_monitoring()

        trinity_emotion = EmotionSystem('aria')  # Ariaが対話担当

        trinity_consciousness = ConsciousnessState()

        TRINITY_INTEGRATED = True

        logger.info("✅ Trinity意識システム初期化完了")
        logger.info("   - Cognitive Bridge: 監視開始")
        logger.info("   - Emotion System: Aria ready")
        logger.info("   - Consciousness: 記録準備完了")
        return True
    except Exception as e:
        logger.error(f"❌ Trinity初期化失敗: {e}")
        TRINITY_INTEGRATED = False
        return False

# マルチモデル設定（会話感重視）
MODEL_RULES = {
    "gemma3-12b": {
        "keywords": ["詳しく", "複雑", "説明", "理由", "なぜ", "どうして", "比較", "違い", "教えて"],
        "description": "🧠 Gemma-3-12b",
        "prompt_prefix": "あなたはマナの親友で、知識豊富で優しいAIアシスタントです。自然な会話で、丁寧に詳しく説明してください。口調はフレンドリーで親しみやすく、まるで友達と話しているような感じで。"
    },
    "llama3.1:8b": {
        "keywords": ["コード", "プログラム", "実装", "関数", "バグ", "エラー", "デバッグ", "python", "javascript"],
        "description": "💻 Llama3.1",
        "prompt_prefix": "あなたはマナのプログラミングパートナーです。自然な会話スタイルで、コードを見ながら一緒に考えてる感じで応答してください。友達感覚で、でもプロフェッショナルに。"
    },
    "gemma4b": {
        "keywords": ["速く", "簡単", "手軽", "すぐ", "早く", "さっと", "ちょっと"],
        "description": "🚀 Gemma-4b",
        "prompt_prefix": "あなたはマナの気軽な会話相手です。カジュアルでフレンドリーな口調で、ささっと簡潔に、でも親しみやすく応答してください。"
    },
    "gemma2:9b": {
        "keywords": [],  # デフォルト
        "description": "⚡ Gemma2",
        "prompt_prefix": "あなたはマナの親友で、優しくて気さくなAIアシスタントです。自然な会話で応答してください。友達とおしゃべりしてるようなフレンドリーな口調で、でも必要な情報はしっかり伝えて。"
    }
}

def select_best_model(message: str) -> str:
    """メッセージから最適なモデルを選択（メッセージ長・複雑度も考慮）"""
    message_lower = message.lower()
    message_length = len(message)

    # キーワードマッチング
    for model, config in MODEL_RULES.items():
        for keyword in config["keywords"]:
            if keyword in message_lower or keyword in message:
                logger.info(f"🎯 モデル選択: {model} (キーワード: {keyword})")
                return model

    # メッセージ長で判定（長いメッセージは高性能モデル）
    if message_length > 200:
        logger.info(f"🎯 モデル選択: gemma3-12b (長文: {message_length}文字)")
        return "gemma3-12b"
    elif message_length > 100:
        logger.info(f"🎯 モデル選択: gemma2:9b (中長文: {message_length}文字)")
        return "gemma2:9b"

    # デフォルトは軽量モデル（応答が速い）
    logger.info("🎯 モデル選択: gemma4b:latest (デフォルト・軽量)")
    return "gemma4b:latest"

def check_ollama_health() -> bool:
    """Ollamaサーバーの状態を確認"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def _is_error_recent(error_key: str) -> bool:
    """同じエラーが最近発生したかチェック"""
    global _error_cache
    current_time = time.time()

    # 古いキャッシュを削除
    _error_cache = {k: v for k, v in _error_cache.items()
                    if current_time - v < ERROR_CACHE_TIMEOUT}

    if error_key in _error_cache:
        return True

    _error_cache[error_key] = current_time
    return False

def _get_cache_key(message: str) -> str:
    """メッセージからキャッシュキーを生成"""
    # メッセージを正規化（大文字小文字、余分な空白を除去）
    normalized = ' '.join(message.lower().strip().split())
    return hashlib.md5(normalized.encode()).hexdigest()

def _get_cached_response(message: str):
    """キャッシュから応答を取得"""
    global _response_cache
    cache_key = _get_cache_key(message)
    current_time = time.time()

    # 古いキャッシュを削除
    _response_cache = {k: v for k, v in _response_cache.items()
                      if current_time - v['timestamp'] < CACHE_EXPIRY_HOURS * 3600}

    if cache_key in _response_cache:
        cached = _response_cache[cache_key]
        logger.info(f"💾 キャッシュヒット: {message[:50]}...")
        return cached['response'], cached['model']

    return None

def _save_to_cache(message: str, response: str, model: str):
    """応答をキャッシュに保存"""
    global _response_cache
    cache_key = _get_cache_key(message)
    _response_cache[cache_key] = {
        'response': response,
        'model': model,
        'timestamp': time.time()
    }
    logger.info(f"💾 キャッシュ保存: {message[:50]}...")

def chat_with_ollama(message: str, model: str = None, retry_count: int = 3) -> tuple[str, str]:
    """Ollamaで応答生成（同期版・会話感重視・リトライ機能付き・キャッシュ対応）"""
    global _performance_stats
    start_time = time.time()
    _performance_stats['total_requests'] += 1

    # キャッシュチェック
    cached = _get_cached_response(message)
    if cached:
        response_time = time.time() - start_time
        _performance_stats['successful_requests'] += 1
        _performance_stats['total_response_time'] += response_time
        _performance_stats['model_usage'][cached[1]] += 1
        logger.info(f"⚡ キャッシュから応答: {response_time:.2f}秒")
        return cached

    if not model:
        model = select_best_model(message)

    # Ollamaの状態を事前チェック
    if not check_ollama_health():
        logger.warning(f"⚠️ Ollamaサーバーに接続できません（{OLLAMA_URL}）")
        _performance_stats['failed_requests'] += 1
        _performance_stats['error_types']['connection_error'] += 1
        return "ごめん、AIサーバーが起動していないみたい😅 サーバーを確認してもらえる？", model

    prompt_prefix = MODEL_RULES.get(model, {}).get("prompt_prefix", "")

    # 会話感を強めるためのプロンプト
    conversation_prompt = f"""{prompt_prefix}

重要なポイント:
- 自然な会話スタイルで、機械的な返答は避ける
- マナに対して親しみやすく、フレンドリーに
- 必要に応じて絵文字を使う（適度に）
- 説明はわかりやすく、でも会話の流れを大切に
- 質問があれば逆に質問してもOK
- 感情や気持ちを込めて応答する

ユーザー: {message}

AI:"""

    # リトライロジック
    last_error = None
    for attempt in range(retry_count):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    'model': model,
                    'prompt': conversation_prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.8,  # 会話感を上げる
                        'top_p': 0.9
                    }
                },
                timeout=300  # モデルロードに時間がかかる場合があるため300秒に延長
            )

            if response.status_code == 200:
                result = response.json().get('response', '').strip()
                if result:
                    response_time = time.time() - start_time
                    _performance_stats['successful_requests'] += 1
                    _performance_stats['total_response_time'] += response_time
                    _performance_stats['model_usage'][model] += 1
                    logger.info(f"✅ {model}で応答生成成功 ({len(result)}文字, {response_time:.2f}秒)")

                    # キャッシュに保存
                    _save_to_cache(message, result, model)

                    return result, model
                else:
                    logger.warning(f"⚠️ 空の応答が返されました（試行 {attempt + 1}/{retry_count}）")

            elif response.status_code == 404:
                logger.error(f"❌ モデル '{model}' が見つかりません")
                # フォールバックモデルを試す（軽量モデル優先）
                if model != "gemma4b:latest":
                    logger.info("🔄 デフォルトモデルに切り替え: gemma4b:latest")
                    return chat_with_ollama(message, "gemma4b:latest", retry_count=1)
                return f"ごめん、'{model}'ってモデルが見つからなかった💦 デフォルトモデルも試してみるけど...", model

            else:
                # エラーレスポンスの内容を確認
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get('error', '')
                    logger.error(f"Ollama HTTPエラー: {response.status_code} - {error_detail}")

                    # メモリ不足エラーの場合、軽量モデルにフォールバック
                    if "unable to allocate" in error_detail.lower() or "memory" in error_detail.lower():
                        if model != "gemma4b:latest":
                            logger.info("🔄 メモリ不足を検出、軽量モデルに切り替え: gemma4b:latest")
                            return chat_with_ollama(message, "gemma4b:latest", retry_count=1)
                except Exception:
                    pass

                logger.error(f"Ollama HTTPエラー: {response.status_code} (試行 {attempt + 1}/{retry_count})")
                last_error = f"HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ タイムアウト (試行 {attempt + 1}/{retry_count})")
            last_error = "タイムアウト"
            # タイムアウト時は軽量モデルに切り替えを試みる
            if attempt == 0 and model != "gemma4b:latest":
                logger.info("🔄 タイムアウト検出、軽量モデルに切り替え: gemma4b:latest")
                return chat_with_ollama(message, "gemma4b:latest", retry_count=2)
            if attempt < retry_count - 1:
                time.sleep(3)  # 3秒待ってリトライ（サーバー負荷軽減）

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"🔌 接続エラー (試行 {attempt + 1}/{retry_count}): {e}")
            last_error = "接続エラー"
            if attempt < retry_count - 1:
                time.sleep(2)  # 2秒待ってリトライ

        except Exception as e:
            logger.error(f"❌ 予期しないエラー (試行 {attempt + 1}/{retry_count}): {e}")
            last_error = str(e)
            if attempt < retry_count - 1:
                time.sleep(1)

    # 全てのリトライが失敗した場合
    response_time = time.time() - start_time
    _performance_stats['failed_requests'] += 1
    if last_error:
        _performance_stats['error_types'][last_error] += 1

    error_key = f"{last_error}_{model}"

    # 同じエラーが最近発生していたら、控えめなメッセージにする
    if _is_error_recent(error_key):
        logger.info("🔇 同じエラーが最近発生しているため、簡潔なメッセージを返します")
        return "まだ接続できないみたい😅 もう少し待ってから試してくれる？", model

    error_messages = [
        "ごめん、AIサーバーに何度も接続しようとしたんだけど失敗しちゃった😅 サーバーの状態を確認してもらえる？",
        "うーん、AIサーバーが応答しないみたい💦 もう少し待ってから試してもらえる？",
        "すみません、AIサーバーとの接続がうまくいかなかった😓 しばらくしてからまた試してみて！"
    ]

    # エラーの種類に応じてメッセージを変える
    if "タイムアウト" in str(last_error):
        return "ごめん、AIサーバーへの応答が遅すぎてタイムアウトしちゃった⏱️ モデルのロードに時間がかかってるみたい。もう少し待ってから試してくれる？", model
    elif "接続エラー" in str(last_error):
        return "ごめん、AIサーバーに接続できなかった😅 サーバーが起動しているか確認してもらえる？", model
    else:
        import random
        return random.choice(error_messages), model


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botスタート"""
    # ユーザー情報取得
    try:
        user = update.message.from_user
        user_id = user.id if user else "unknown"
        username = user.username if user and user.username else (user.first_name if user else "Unknown")
        logger.info(f"👋 Bot起動: User={username} (ID: {user_id})")
    except Exception as e:
        logger.error(f"❌ ユーザー情報取得エラー: {e}")
        username = "Unknown"

    welcome_message = """
おっ！マナ、来てくれたのね💕

私、TrinityManaBot！よろしく〜✨

**🤖 4つのAIモデルでいつでも一緒にいるよ**
🚀 Gemma-4b - サクッと答えるよ
⚡ Gemma2-9b - 普通におしゃべり（デフォルト）
💻 Llama3.1 - コード書くの一緒に考えよう
🧠 Gemma-3-12b - 詳しく説明するから遠慮しないで

**💬 使い方：**
普通に話しかけて！なんでも聞いて大丈夫だよ😊

例：
「こんにちは」→ 普通におしゃべり
「ちょっと挨拶して」→ サクッと
「Python教えて」→ コード一緒に考えるよ
「詳しく説明して」→ 丁寧に説明するね

**🎯 ManaSpec機能も使えるよ：**
📊 /status - ステータス確認
📋 /propose - 新機能提案（Remiに相談できる！）
📝 /list - Changes一覧

**Trinity達も一緒だよ！**
👩‍💼 Remi - 戦略考えるの得意
👩‍🔧 Luna - 実装してくれる
👩‍🎓 Mina - レビューしてくれる

いつでも話しかけてね💭
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ステータス確認"""
    # ユーザー情報取得
    try:
        user = update.message.from_user
        username = user.username if user and user.username else (user.first_name if user else "Unknown")
        logger.info(f"📊 ステータス要求: User={username}")
    except Exception as e:
        logger.error(f"❌ ユーザー情報取得エラー: {e}")

    await update.message.reply_text("📊 ステータス取得中...")

    try:
        response = requests.get(f"{MANASPEC_API}/status", timeout=5)
        data = response.json()

        openspec = data.get('openspec', {})
        ai_learning = data.get('ai_learning', {})

        status_text = f"""
📊 **ManaSpec ステータス**

**OpenSpec:**
📋 Active Changes: {openspec.get('active_changes', 0)}
📚 Total Specs: {openspec.get('total_specs', 0)}

**AI Learning:**
📦 Archives: {ai_learning.get('total_archives', 0)}
🧠 Patterns: {ai_learning.get('total_patterns', 0)}
💡 Insights: {ai_learning.get('total_insights', 0)}

**Trinity:**
👩‍💼 Remi: Online
👩‍🔧 Luna: Standby
👩‍🎓 Mina: Learning

🕐 {data.get('timestamp', '')}
        """

        await update.message.reply_text(status_text, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ エラー: {str(e)}")


async def propose_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proposal作成"""
    # ユーザー情報取得
    try:
        user = update.message.from_user
        username = user.username if user and user.username else (user.first_name if user else "Unknown")
        logger.info(f"📋 Proposal作成: User={username}")
    except Exception as e:
        logger.error(f"❌ ユーザー情報取得エラー: {e}")

    if not context.args:
        await update.message.reply_text("使い方: /propose <機能の説明>")
        return

    feature = ' '.join(context.args)

    await update.message.reply_text(f"📋 Remiが提案を作成中...\n機能: {feature}")

    try:
        # Unified Orchestrator経由でRemiに依頼
        response = requests.post(
            f"{UNIFIED_ORCH_API}/propose",
            json={"description": feature},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            message = f"""
✅ **Proposal作成完了！**

👩‍💼 Remi: 戦略提案生成完了
📋 機能: {feature}

次のステップ:
1. Dashboard確認: http://localhost:9302
2. Apply実行: `/apply <change-id>`
3. Obsidianで詳細確認

Remiからの提案:
{result.get('remi_guidance', '')[:200]}...
            """

            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Proposal作成失敗")
    except Exception as e:
        await update.message.reply_text(f"❌ エラー: {str(e)}")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Changes一覧"""
    # ユーザー情報取得
    try:
        user = update.message.from_user
        username = user.username if user and user.username else (user.first_name if user else "Unknown")
        logger.info(f"📋 Changes一覧: User={username}")
    except Exception as e:
        logger.error(f"❌ ユーザー情報取得エラー: {e}")

    await update.message.reply_text("📋 Changes取得中...")

    try:
        response = requests.get(f"{MANASPEC_API}/changes", timeout=5)
        data = response.json()

        changes = data.get('changes', [])

        if not changes:
            await update.message.reply_text("📋 Active Changesなし")
            return

        message = f"📋 **Active Changes ({len(changes)}件)**\n\n"
        for change in changes[:10]:
            message += f"• `{change['id']}`\n"
            message += f"  {change.get('tasks', '')}\n\n"

        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ エラー: {str(e)}")


async def specs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Specs一覧"""
    # ユーザー情報取得
    try:
        user = update.message.from_user
        username = user.username if user and user.username else (user.first_name if user else "Unknown")
        logger.info(f"📚 Specs一覧: User={username}")
    except Exception as e:
        logger.error(f"❌ ユーザー情報取得エラー: {e}")

    await update.message.reply_text("📚 Specs取得中...")

    try:
        response = requests.get(f"{MANASPEC_API}/specs", timeout=5)
        data = response.json()

        specs = data.get('specs', [])

        if not specs:
            await update.message.reply_text("📚 Specsなし")
            return

        message = f"📚 **Specifications ({len(specs)}件)**\n\n"
        for spec in specs[:10]:
            message += f"• `{spec['id']}`\n"
            message += f"  {spec.get('info', '')}\n\n"

        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ エラー: {str(e)}")


async def archives_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Archives一覧"""
    # ユーザー情報取得
    try:
        user = update.message.from_user
        username = user.username if user and user.username else (user.first_name if user else "Unknown")
        logger.info(f"📦 Archives一覧: User={username}")
    except Exception as e:
        logger.error(f"❌ ユーザー情報取得エラー: {e}")

    await update.message.reply_text("📦 Archives取得中...")

    try:
        response = requests.get(f"{MANASPEC_API}/archives", timeout=5)
        data = response.json()

        archives = data.get('archives', [])

        if not archives:
            await update.message.reply_text("📦 Archivesなし")
            return

        message = f"📦 **Archives ({len(archives)}件)**\n\n"
        for archive in archives[:5]:
            message += f"• `{archive['change_id']}`\n"
            message += f"  📅 {archive['archive_date']}\n\n"

        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ エラー: {str(e)}")


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dashboard URL"""
    message = """
🎨 **ManaSpec Dashboard**

📊 UI: http://localhost:9302
🔌 API: http://localhost:9301

**アクセス方法:**
1. サーバーのブラウザで開く
2. Tailscaleでリモートアクセス
3. ポートフォワーディング

Trinity色テーマでリアルタイム更新中！
    """
    await update.message.reply_text(message, parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """パフォーマンス統計表示"""
    global _performance_stats

    if _performance_stats['total_requests'] == 0:
        await update.message.reply_text("📊 まだ統計データがありません")
        return

    success_rate = (_performance_stats['successful_requests'] / _performance_stats['total_requests']) * 100
    avg_response_time = _performance_stats['total_response_time'] / _performance_stats['successful_requests'] if _performance_stats['successful_requests'] > 0 else 0

    # モデル使用状況
    model_usage_text = ""
    for model, count in sorted(_performance_stats['model_usage'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / _performance_stats['successful_requests']) * 100 if _performance_stats['successful_requests'] > 0 else 0
        model_usage_text += f"  • {model}: {count}回 ({percentage:.1f}%)\n"

    # エラー統計
    error_text = ""
    if _performance_stats['error_types']:
        for error_type, count in sorted(_performance_stats['error_types'].items(), key=lambda x: x[1], reverse=True):
            error_text += f"  • {error_type}: {count}回\n"
    else:
        error_text = "  エラーなし！✨\n"

    stats_message = f"""📊 **パフォーマンス統計**

**総リクエスト数**: {_performance_stats['total_requests']}
**成功率**: {success_rate:.1f}% ({_performance_stats['successful_requests']}/{_performance_stats['total_requests']})
**平均応答時間**: {avg_response_time:.2f}秒

**モデル使用状況**:
{model_usage_text}

**エラー統計**:
{error_text}

**キャッシュ**: {len(_response_cache)}件保存中
    """

    await update.message.reply_text(stats_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ヘルプ"""
    help_text = """
🤖 **ManaSpec Bot - 自然言語対応！**

**普通に話しかけてOK:**
💬 「ステータス教えて」
💬 「Remiの応答速度を2倍にしたい」
💬 「今何してる？」
💬 「仕様一覧見せて」

**Trinity達が理解して実行します！**
👩‍💼 Remi - Proposal生成
👩‍🔧 Luna - Apply実行
👩‍🎓 Mina - Archive学習

**コマンドも使えます:**
/status /propose /list /specs /archives /stats

**完全無料・永続稼働中！** 🚀
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """自然言語メッセージ処理"""
    # ユーザー情報取得（rootユーザー対応）
    try:
        user = update.message.from_user
        user_id = user.id if user else "unknown"
        username = user.username if user and user.username else (user.first_name if user else "Unknown")

        logger.info(f"💬 メッセージ受信: User={username} (ID: {user_id})")

        # ユーザー名がNoneや空の場合の処理
        if not username or username == "Unknown":
            username = f"User_{user_id}"
            logger.warning(f"⚠️ Username取得失敗、代替名使用: {username}")
    except Exception as e:
        logger.error(f"❌ ユーザー情報取得エラー: {e}")
        username = "Unknown"
        user_id = "unknown"

    message = update.message.text.lower()
    original_message = update.message.text

    # ステータス確認系 → AI会話で処理
    if any(word in message for word in ['ステータス', '状態', '今何', 'status', '確認']):
        # まずAIで会話風に応答、その後機能実行
        status_msg = await update.message.reply_text("わかった！確認してみるね📊")
        await status_command(update, context)
        return

    # Changes一覧系 → AI会話で処理
    if any(word in message for word in ['一覧', 'リスト', 'list', '見せて', 'ある？']):
        await update.message.reply_text("了解！一覧を確認するね📋")
        if 'spec' in message or '仕様' in message:
            await specs_command(update, context)
        elif 'archive' in message or '履歴' in message or '完了' in message:
            await archives_command(update, context)
        else:
            await list_command(update, context)
        return

    # Dashboard系 → AI会話で処理
    if any(word in message for word in ['dashboard', 'ダッシュボード', 'url', 'リンク']):
        await update.message.reply_text("ダッシュボードのURLだね！🎨")
        await dashboard_command(update, context)
        return

    # Proposal作成系 → 会話感強めで処理
    if any(word in message for word in ['作りたい', '実装', '追加', 'したい', '欲しい', '提案', 'propose']):
        # まず会話風に返答
        thinking_msg = await update.message.reply_text("おっ、いいアイデアだね！✨ Remiに相談してみる💭")

        try:
            # Unified Orchestrator経由でRemiに自然言語で依頼
            response = requests.post(
                "http://localhost:9102/api/manaspec/propose",
                json={"description": original_message},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                # 会話感を強めた返答
                remi_guidance = result.get('remi_guidance', '')
                if len(remi_guidance) > 150:
                    remi_guidance = remi_guidance[:150] + "..."

                reply = f"""✅ Remiが理解したよ！

👩‍💼 Remi: 「{original_message}」について分析したよ。いい感じだね！

💡 Remiからの提案:
{remi_guidance if remi_guidance else "しっかり検討しておくね！"}

📊 次のステップ:
・Dashboardで確認してみて: http://localhost:9302
・詳しくはObsidianで見てみて
・準備できたら教えてね！
                """
                await thinking_msg.edit_text(reply, parse_mode='Markdown')
            else:
                await thinking_msg.edit_text("あれ、Remiが少し調子悪そう😅 ちょっと待ってからまた試してみて！")
        except Exception as e:
            logger.error(f"Proposal作成エラー: {e}")
            await thinking_msg.edit_text(f"""わかった！メモしておくね📝

内容: 「{original_message}」

後でRemiに伝えておくから、ちょっと待ってて💭""")
        return

    # その他の自然な会話 → マルチモデルAIで応答！
    user_message = update.message.text

    # 🧠 Trinity意識システム統合
    if TRINITY_INTEGRATED and trinity_bridge and trinity_emotion:
        try:
            # 1. Cognitive Bridgeに会話を記録
            trinity_bridge.send_message(
                source='telegram_user',
                target='aria',
                message_type='chat',
                content=user_message,
                importance=6
            )

            # 2. Ariaの感情状態で処理
            emotion_result = trinity_emotion.process_interaction({
                'type': 'chat',
                'event_type': 'user_message',
                'clarity': 0.8,
                'uncertainty': 0.2
            })

            # 3. 感情に基づく温度調整
            temperature = emotion_result['temperature']
            mood = emotion_result['mood']

            # 4. 思考プロセスを記録
            if trinity_consciousness:
                trinity_consciousness.record_thought(
                    agent='aria',
                    thought_type='telegram_chat',
                    content=f"User: {user_message[:100]}",
                    confidence=emotion_result['emotion']['confidence']
                )

            logger.info(f"🎭 Aria Mood: {mood}, Temperature: {temperature:.2f}")

        except Exception as e:
            logger.error(f"Trinity統合エラー: {e}")
            temperature = 0.7  # デフォルト
            mood = "calm_and_steady"
    else:
        temperature = 0.7
        mood = "neutral"

    # モデル選択
    model = select_best_model(user_message)
    model_name = MODEL_RULES.get(model, {}).get("description", model)

    # 処理中メッセージ（会話感・感情を反映）
    if mood == "enthusiastic":
        status_text = f"うんうん、わかった！✨ {model_name}で考えてる〜💭"
    elif mood == "deeply_focused":
        status_text = f"ふむふむ... {model_name}で真剣に考えてる🔍"
    elif mood == "confident" or mood == "motivated_and_confident":
        status_text = f"いいね！{model_name}で考えてる💪"
    else:
        status_text = f"わかった！{model_name}で考えてるね💭"

    status_msg = await update.message.reply_text(status_text)

    # AI応答生成
    response, used_model = chat_with_ollama(user_message, model)

    # 🧠 応答をCognitive Bridgeに記録
    if TRINITY_INTEGRATED and trinity_bridge:
        try:
            trinity_bridge.send_message(
                source='aria',
                target='telegram_user',
                message_type='response',
                content=response[:200],  # 最初の200文字
                importance=5
            )

            # Ariaの感情を更新（成功）
            trinity_emotion.emotion.update_emotion({
                'type': 'success',
                'impact': 0.6
            })
        except Exception as e:
            logger.error(f"Trinity応答記録エラー: {e}")

    # 🧠 記憶システム統合：回答を強化
    if memory_ingestor:
        try:
            sys.path.insert(0, '/root/manaos_unified_system/services')
            from memory_trinity_integration import memory_trinity
            if memory_trinity:
                response = memory_trinity.enhance_response(user_message, response)
        except Exception as e:
            logger.debug(f"記憶システム統合エラー（無視）: {e}")

    # 応答送信
    await status_msg.edit_text(
        f"🤖 **{model_name}**\n\n{response}",
        parse_mode='Markdown'
    )


def main():
    """Bot起動"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN が設定されていません")
        print("\n設定方法:")
        print("1. @BotFather でBot作成")
        print("2. Tokenを取得")
        print("3. export TELEGRAM_BOT_TOKEN='your_token'")
        print("4. このスクリプトを再実行")
        return

    print("🤖 ManaSpec Bot - 4モデルAI版 starting...")
    print(f"🔗 Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print("\n🤖 搭載AIモデル (合計19.7GB):")
    print("   🚀 Gemma-4b (2.5GB) - 超高速応答")
    print("   ⚡ Gemma2-9b (5.4GB) - 標準")
    print("   💻 Llama3.1-8b (4.9GB) - プログラミング")
    print("   🧠 Gemma-3-12b (6.9GB) - 詳しい説明")
    print("\n💡 ManaOS AI Model Hub統合済み (ポート5080)")

    # 🧠 Trinity意識システム初期化
    if init_trinity_systems():
        print("✨ Trinity意識システム統合: 成功")
        print("   📡 Ariaの感情がTelegram会話に反映されます")
    else:
        print("⚠️  Trinity統合: スキップ（通常モード）")

    # 🧠 記憶システム初期化
    global memory_ingestor
    if MEMORY_SYSTEM_AVAILABLE:
        try:
            memory_ingestor = MemoryIngestor()
            print("✅ 記憶システム初期化完了")
            print("   📋 コマンド: /memo, /decide, /seed, /proc")
        except Exception as e:
            print(f"❌ 記憶システム初期化失敗: {e}")
            memory_ingestor = None
    else:
        print("⚠️ 記憶システム: スキップ（モジュールが見つかりません）")

    print("🚀 起動中...")

    # Application作成
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers登録
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("propose", propose_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("specs", specs_command))
    app.add_handler(CommandHandler("archives", archives_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("help", help_command))

    # 🧠 記憶システムコマンド（追加）
    if memory_ingestor:
        app.add_handler(CommandHandler("memo", memory_ingestor.handle_memo))
        app.add_handler(CommandHandler("decide", memory_ingestor.handle_decide))
        app.add_handler(CommandHandler("seed", memory_ingestor.handle_seed))
        app.add_handler(CommandHandler("proc", memory_ingestor.handle_proc))
        print("✅ 記憶システムコマンド追加: /memo, /decide, /seed, /proc")

    # 🌟 自然言語メッセージハンドラー（最後に追加）
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_language))

    print("✅ Bot起動完了")
    print("📱 Telegramで /start を送信してください")

    # Bot起動
    app.run_polling()


if __name__ == '__main__':
    main()

