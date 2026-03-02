"""
ManaOS Image Generation Service
================================
画像生成パイプラインの責務分離サービス。

既存 Unified API の /api/comfyui/* を段階的にこちらに移行し、
品質評価・課金・自律改善ループを統合する。

アーキテクチャ:
  router.py           — FastAPI エンドポイント (/api/v1/images/*)
  service.py          — ビジネスロジック（生成→スコア→改善→保存）
  pipeline.py         — ComfyUI ワークフロー実行 (direct + proxy)
  scorer.py           — 品質評価（5指標: CLIP/美的/技術/破綻/商用）
  prompt_enhancer.py  — プロンプト自動強化 (翻訳/スタイル/品質タグ)
  rl_bridge.py        — RLAnything 評価ループ接続
  revenue_tracker.py  — 収益 DB 書き込み
  billing.py          — 課金・使用量管理 (SQLite)
  queue.py            — ジョブキュー管理 (SQLite + async worker)
  api_auth.py         — API Key 認証 + レート制限
  metrics.py          — Prometheus-style メトリクス収集
  models.py           — Pydantic スキーマ（API I/O 契約）
  batch_generator.py  — バッチ生成 (1→N→ベスト選択) + A/B比較
  feedback.py         — ユーザーフィードバック/評価 (SQLite)
  customer_memory.py  — 顧客嗜好記憶 (MRL Memory連携)
  gpu_monitor.py      — GPU使用率モニタリング (nvidia-smi)
  landing_page.html   — ランディングページ

Created: 2026-03-02
"""

__version__ = "0.4.0"  # Batch + Feedback + Customer Memory + GPU Monitor + Landing Page
