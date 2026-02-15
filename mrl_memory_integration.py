#!/usr/bin/env python3
"""
MRL Memory Integration
既存システム（LLMルーティング/n8n/Slack/Obsidian）との統合
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import os
import time

from mrl_memory_system import MRLMemorySystem
from mrl_memory_priority_resolver import MemoryPriorityResolver
from mrl_memory_gating import MemoryGating
from mrl_memory_metrics import MRLMemoryMetrics
from mrl_memory_api_security import APISecurity

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# LLMルーティング統合
try:
    from llm_routing import LLMRouter
    LLM_ROUTING_AVAILABLE = True
except ImportError:
    LLM_ROUTING_AVAILABLE = False
    logger.warning("LLMルーティングが利用できません")

# RAGメモリ統合
try:
    from rag_memory_enhanced import RAGMemoryEnhanced
    RAG_MEMORY_AVAILABLE = True
except ImportError:
    RAG_MEMORY_AVAILABLE = False
    logger.warning("RAGメモリが利用できません")


def _load_dotenv(env_path: str = ".env") -> None:
    """
    最小のdotenvローダ（外部依存なし）

    - コメント行/空行は無視
    - KEY=VALUE を os.environ に反映（上書き）
    """
    try:
        p = Path(env_path)
        if not p.exists():
            return
        for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    except Exception as e:
        logger.warning(f".env読み込みに失敗しました: {e}")


# 重要: Flaskのグローバル初期化（APISecurity/Rollout等）より先に.envを読む
# 起動ディレクトリに依存しないよう、まずこのスクリプト配置ディレクトリの .env を読む
_load_dotenv(str(Path(__file__).resolve().with_name(".env")))
# 互換性のため、従来どおりカレントディレクトリの .env もあれば上書きで読む
_load_dotenv()


class MRLMemoryLLMIntegration:
    """
    LLMルーティングとの統合
    
    推論前にメモリからコンテキストを取得してLLMに渡す
    """
    
    def __init__(
        self,
        memory_system: Optional[MRLMemorySystem] = None,
        llm_router: Optional[LLMRouter] = None,
        rag_memory: Optional[RAGMemoryEnhanced] = None
    ):
        """
        初期化
        
        Args:
            memory_system: MRL Memory System
            llm_router: LLM Router
            rag_memory: RAG Memory（長期記憶）
        """
        self.memory_system = memory_system or MRLMemorySystem()
        self.llm_router = llm_router
        
        if LLM_ROUTING_AVAILABLE and llm_router is None:
            try:
                self.llm_router = LLMRouter()
            except Exception as e:
                logger.warning(f"LLMルーターの初期化エラー: {e}")
                self.llm_router = None
        
        # RAGメモリ（長期記憶）
        self.rag_memory = rag_memory
        if RAG_MEMORY_AVAILABLE and rag_memory is None:
            try:
                self.rag_memory = RAGMemoryEnhanced()
            except Exception as e:
                logger.warning(f"RAGメモリの初期化エラー: {e}")
                self.rag_memory = None
        
        # 優先度解決器
        self.priority_resolver = MemoryPriorityResolver()
        
        # ゲーティング
        self.gating = MemoryGating()
        
        # メトリクス
        self.metrics = MRLMemoryMetrics()
    
    def route_with_memory(
        self,
        task_type: str,
        prompt: str,
        source: str = "llm_routing",
        enable_memory: bool = True
    ) -> Dict[str, Any]:
        """
        メモリを活用したLLMルーティング
        
        Args:
            task_type: タスクタイプ
            prompt: プロンプト
            source: ソース
            enable_memory: メモリを使用するか
        
        Returns:
            LLMレスポンス
        """
        if not self.llm_router:
            raise ValueError("LLMルーターが利用できません")
        
        # 1. プロンプトから情報を抽出してメモリに保存
        if enable_memory:
            self.memory_system.process(
                text=prompt,
                source=source,
                enable_rehearsal=True,
                enable_promotion=False
            )
        
        # 2. メモリから関連情報を取得（RAG + FWPKM統合）
        memory_context = ""
        if enable_memory:
            # FWPKM（短期記憶）から検索
            fwpkm_results = self.memory_system.retrieve(prompt, limit=5)
            
            # RAG（長期記憶）から検索
            rag_results = []
            if self.rag_memory:
                try:
                    rag_entries = self.rag_memory.search_memories(prompt, limit=5)
                    rag_results = [
                        {
                            "key": e.entry_id,
                            "value": e.content,
                            "confidence": "high" if e.importance_score >= 0.7 else "med",
                            "timestamp": e.created_at
                        }
                        for e in rag_entries
                    ]
                except Exception as e:
                    logger.warning(f"RAG検索エラー: {e}")
            
            # 競合解決
            resolved = self.priority_resolver.resolve_conflict(
                rag_results=rag_results,
                fwpkm_results=fwpkm_results,
                query=prompt
            )
            
            # ゲーティング適用
            gated_results = []
            for result in resolved["results"]:
                gated = self.gating.gate_entry(result, resolved["results"])
                gated_results.append(gated)
            
            # 高ゲートのみ使用
            filtered_results = self.gating.filter_by_gate(gated_results, min_gate_weight=0.5)
            
            # コンテキスト構築
            memory_context = self.priority_resolver.get_context_for_llm(
                {"results": filtered_results},
                include_conflicts=True
            )
            
            # メトリクス記録
            self.metrics.record_latency(
                input_length=len(prompt),
                processing_time=0.0,  # 実際の処理時間を記録
                operation="retrieve"
            )
        
        # 3. プロンプトを拡張
        enhanced_prompt = prompt
        if memory_context:
            enhanced_prompt = f"""
{memory_context}

ユーザーの質問: {prompt}
"""
        
        # 4. LLMで処理
        result = self.llm_router.route(
            task_type=task_type,
            prompt=enhanced_prompt
        )
        
        # 5. レスポンスもメモリに保存（オプション）
        if enable_memory and result.get("response"):
            self.memory_system.process(
                text=result.get("response", ""),
                source=f"{source}_response",
                enable_rehearsal=False,
                enable_promotion=False
            )
        
        # 6. 結果にメモリ情報を追加
        result["memory_used"] = bool(memory_context)
        result["memory_context_length"] = len(memory_context)
        
        return result


class MRLMemoryAPI:
    """
    REST API統合（n8n/Slackから呼び出し可能）
    """
    
    def __init__(self, memory_system: Optional[MRLMemorySystem] = None):
        """
        初期化
        
        Args:
            memory_system: MRL Memory System
        """
        self.memory_system = memory_system or MRLMemorySystem()
    
    def process_text(
        self,
        text: str,
        source: str = "api",
        enable_rehearsal: bool = True,
        enable_promotion: bool = False
    ) -> Dict[str, Any]:
        """
        テキストを処理（API用）
        
        Args:
            text: 入力テキスト
            source: ソース
            enable_rehearsal: 復習効果を有効にするか
            enable_promotion: 昇格チェックを有効にするか
        
        Returns:
            処理結果
        """
        return self.memory_system.process(
            text=text,
            source=source,
            enable_rehearsal=enable_rehearsal,
            enable_promotion=enable_promotion
        )
    
    def search_memory(
        self,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        メモリから検索（API用）
        
        Args:
            query: 検索クエリ
            limit: 最大取得数
        
        Returns:
            検索結果
        """
        results = self.memory_system.retrieve(query, limit)
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    
    def get_context(
        self,
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        LLMコンテキストを取得（API用）
        
        Args:
            query: 検索クエリ
            limit: 最大取得数
        
        Returns:
            コンテキスト
        """
        context = self.memory_system.get_context_for_llm(query, limit)
        return {
            "query": query,
            "context": context,
            "length": len(context)
        }
    
    def update_working_memory(self) -> Dict[str, Any]:
        """
        Working Memoryを更新（API用）
        
        Returns:
            更新結果
        """
        self.memory_system.update_working_memory()
        return {
            "status": "success",
            "message": "Working Memoryを更新しました"
        }
    
    def promote_memories(self) -> Dict[str, Any]:
        """
        メモリを昇格（API用）
        
        Returns:
            昇格結果
        """
        promoted = self.memory_system.promoter.check_and_promote()
        return {
            "status": "success",
            "promoted_count": len(promoted),
            "promoted": promoted
        }


# Flask API（n8n/Slackから呼び出し可能）
try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
    from functools import wraps
    
    app = Flask(__name__)
    CORS(app)
    
    # グローバルインスタンス
    memory_api = MRLMemoryAPI()

    # メトリクス（APIプロセス内で記録・保存）
    api_metrics = MRLMemoryMetrics()
    
    # .envファイルを再読み込み（Flask初期化時に確実に読み込む）
    _load_dotenv()
    
    # セキュリティインスタンス（グローバル）
    security = APISecurity()
    
    # セキュリティ設定をログ出力（デバッグ用）
    logger.info(f"Security initialized: require_auth={security.require_auth}, api_key={'SET' if security.api_key else 'NOT SET'}")
    
    # Rollout Manager
    try:
        from mrl_memory_rollout_manager import RolloutManager
        rollout_manager = RolloutManager()
    except ImportError:
        rollout_manager = None
        logger.warning("Rollout Managerが利用できません")
    
    def require_auth_decorator(func):
        """認証デコレータ（Flask用）"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if security.require_auth:
                # request.json はGET等で415を投げることがあるので、silent=Trueで安全に読む
                data = request.get_json(silent=True) or {}
                api_key = request.headers.get("X-API-Key") or data.get("api_key")
                
                # デバッグ用ログ（本番では削除可能）
                if not security.authenticate(api_key):
                    logger.debug(f"認証失敗: 提供されたキー={api_key[:20] if api_key else None}..., サーバー側キー={'SET' if security.api_key else 'NOT SET'}")
                    return jsonify({"error": "認証に失敗しました"}), 401
            return func(*args, **kwargs)
        return wrapper
    
    def rate_limit_decorator(func):
        """レート制限デコレータ（Flask用）"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_id = request.remote_addr or "unknown"
            if not security.check_rate_limit(client_id):
                return jsonify({"error": "レート制限を超えました"}), 429
            return func(*args, **kwargs)
        return wrapper

    def _record_api_metrics(operation: str, start_time: float, write_count: int = 0, total_results: int = 0, conflicts: int = 0, blocked: int = 0):
        """APIのメトリクスを記録して永続化（snapshotが参照できるようにする）"""
        try:
            elapsed = max(0.0, time.perf_counter() - start_time)
            # latency
            api_metrics.record_latency(input_length=0, processing_time=elapsed, operation=operation)
            # writes/min（厳密な分単位ではないが、Phase 1の0/非0判定に十分）
            api_metrics.record_write_count(int(write_count))
            # gate/conflict（現状は簡易：search結果ベース）
            if total_results > 0:
                api_metrics.record_gate_block_rate(total_entries=int(total_results), blocked_entries=int(blocked))
                api_metrics.record_conflict_detection_rate(total_results=int(total_results), conflicts=int(conflicts))
            # 保存（別プロセスのsnapshot/dashboardが読める）
            api_metrics.save_metrics()
        except Exception as e:
            logger.warning(f"メトリクス記録に失敗: {e}")
    
    @app.route('/health', methods=['GET'])
    def health():
        """ヘルスチェック"""
        return jsonify({
            "status": "healthy",
            "service": "MRL Memory API",
            "auth_required": security.require_auth,
            "api_key_configured": bool(security.api_key),
        })

    @app.route('/api/metrics', methods=['GET'])
    @require_auth_decorator
    def get_metrics():
        """現在のメトリクスを取得（Phase 1 snapshot用）"""
        try:
            latency_stats = api_metrics.get_latency_stats()
            write_stats = api_metrics.get_write_count_stats()
            gate_stats = api_metrics.get_gate_block_rate_stats()
            conflict_stats = api_metrics.get_conflict_detection_rate_stats()
            slot_stats = api_metrics.get_slot_utilization_stats()

            payload = {
                "timestamp": time.time(),
                "metrics": {
                    "e2e_p95_sec": (latency_stats.get("p95", 0) if latency_stats else 0),
                    "gate_block_rate": (gate_stats.get("current", 0) if gate_stats else 0),
                    "contradiction_rate": (conflict_stats.get("current", 0) if conflict_stats else 0),
                    "slot_usage_variance": (slot_stats.get("mean_variance", 0) if slot_stats else 0),
                    "writes_per_min": (write_stats.get("current", 0) if write_stats else 0),
                },
                "counts": {
                    "latency_samples": (latency_stats.get("count", 0) if latency_stats else 0),
                    "write_samples": (write_stats.get("count", 0) if write_stats else 0),
                    "gate_samples": (gate_stats.get("count", 0) if gate_stats else 0),
                    "conflict_samples": (conflict_stats.get("count", 0) if conflict_stats else 0),
                },
                "config": {
                    "write_mode": os.getenv("FWPKM_WRITE_MODE", "unknown"),
                    "review_effect": os.getenv("FWPKM_REVIEW_EFFECT", "0"),
                    "write_enabled": os.getenv("FWPKM_WRITE_ENABLED", "0"),
                }
            }
            return jsonify(payload)
        except Exception as e:
            logger.error(f"メトリクス取得エラー: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/memory/process', methods=['POST'])
    @require_auth_decorator
    @rate_limit_decorator
    def process_text():
        """テキストを処理"""
        start = time.perf_counter()
        try:
            data = request.get_json() or {}
            text = data.get("text", "")
            source = data.get("source", "api")
            enable_rehearsal = data.get("enable_rehearsal", True)
            enable_promotion = data.get("enable_promotion", False)
            
            if not text:
                return jsonify({"error": "text is required"}), 400
            
            # 入力サイズチェック
            if not security.check_input_size(text):
                return jsonify({"error": "入力サイズが制限を超えています"}), 413
            
            # PIIマスキング（ログ用）
            masked_text = security.mask_pii(text)
            logger.info(f"処理リクエスト: {len(text)}文字 (マスキング済み: {len(masked_text)}文字)")
            
            # Rollout Managerで書き込み制御
            if rollout_manager and not rollout_manager.is_write_enabled():
                # Read-onlyモード: 検索のみ
                results = memory_api.search_memory(text, limit=5)
                _record_api_metrics(
                    operation="process_readonly_search",
                    start_time=start,
                    write_count=0,
                    total_results=len(results.get("results", [])),
                )
                return jsonify({
                    "status": "readonly_mode",
                    "search_results": results,
                    "message": "読み取り専用モードです"
                })
            
            # 復習効果の制御
            if rollout_manager:
                enable_rehearsal = rollout_manager.is_review_effect_enabled() and enable_rehearsal
            
            # PIIマスキング（永続化直前）
            text_for_storage = security.mask_pii(text)
            
            result = memory_api.process_text(
                text=text_for_storage,  # 永続化前にマスキング
                source=source,
                enable_rehearsal=enable_rehearsal,
                enable_promotion=enable_promotion
            )

            # 書き込み量は rehearsal の処理件数で近似
            rehearsal = result.get("rehearsal", {}) if isinstance(result, dict) else {}
            write_count = int(rehearsal.get("total_processed", 1) or 1)
            _record_api_metrics(operation="process", start_time=start, write_count=write_count)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"処理エラー: {e}")
            _record_api_metrics(operation="process_error", start_time=start, write_count=0)
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/memory/search', methods=['POST'])
    @require_auth_decorator
    @rate_limit_decorator
    def search_memory():
        """メモリから検索"""
        start = time.perf_counter()
        try:
            data = request.get_json() or {}
            query = data.get("query", "")
            limit = data.get("limit", 10)
            
            if not query:
                return jsonify({"error": "query is required"}), 400
            
            result = memory_api.search_memory(query, limit)
            total = len(result.get("results", [])) if isinstance(result, dict) else 0
            _record_api_metrics(operation="search", start_time=start, write_count=0, total_results=total)
            return jsonify(result)
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            _record_api_metrics(operation="search_error", start_time=start, write_count=0)
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/memory/context', methods=['POST'])
    @require_auth_decorator
    @rate_limit_decorator
    def get_context():
        """LLMコンテキストを取得"""
        start = time.perf_counter()
        try:
            data = request.get_json() or {}
            query = data.get("query", "")
            limit = data.get("limit", 5)
            
            if not query:
                return jsonify({"error": "query is required"}), 400
            
            result = memory_api.get_context(query, limit)
            _record_api_metrics(operation="context", start_time=start, write_count=0)
            return jsonify(result)
        except Exception as e:
            logger.error(f"コンテキスト取得エラー: {e}")
            _record_api_metrics(operation="context_error", start_time=start, write_count=0)
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/memory/update_working', methods=['POST'])
    @require_auth_decorator
    @rate_limit_decorator
    def update_working_memory():
        """Working Memoryを更新"""
        try:
            result = memory_api.update_working_memory()
            return jsonify(result)
        except Exception as e:
            logger.error(f"更新エラー: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/memory/promote', methods=['POST'])
    @require_auth_decorator
    @rate_limit_decorator
    def promote_memories():
        """メモリを昇格"""
        try:
            result = memory_api.promote_memories()
            return jsonify(result)
        except Exception as e:
            logger.error(f"昇格エラー: {e}")
            return jsonify({"error": str(e)}), 500
    
    FLASK_AVAILABLE = True
    
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("Flaskが利用できません（API機能は無効）")


if __name__ == "__main__":
    # テスト
    if FLASK_AVAILABLE:
        import os
        # .envファイルを再読み込み（起動時に確実に読み込む）
        _load_dotenv()
        
        # セキュリティ設定を確認（デバッグ用）
        api_key = os.getenv("MRL_MEMORY_API_KEY") or os.getenv("API_KEY")
        require_auth = os.getenv("MRL_MEMORY_REQUIRE_AUTH") or os.getenv("REQUIRE_AUTH", "1")
        logger.info(f"API起動時設定: require_auth={require_auth}, api_key={'SET' if api_key else 'NOT SET'}")
        
        port = int(os.getenv("PORT", 5105))
        logger.info(f"🚀 MRL Memory API起動中... (ポート: {port})")
        app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
    else:
        # 直接テスト
        api = MRLMemoryAPI()
        
        # 処理テスト
        result = api.process_text("プロジェクトXの開始日は2024年2月1日です。", source="test")
        print(f"処理結果: {result}")
        
        # 検索テスト
        search_result = api.search_memory("決定", limit=5)
        print(f"検索結果: {search_result}")
