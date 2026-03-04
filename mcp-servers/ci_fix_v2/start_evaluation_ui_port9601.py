#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像評価Web UI起動スクリプト（ポート9601版）"""

import sys
import os
from pathlib import Path

# Cursor/ログ収集側がUTF-8前提のことが多いので、WindowsでもUTF-8で出す
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    import io

    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 起動ログ（デバッグ用：eval_ui_debug.log に追記）
_debug_log = Path(__file__).parent / "eval_ui_debug.log"
try:
    _prev = (_debug_log.read_text() + "\n") if _debug_log.exists() else ""
    _debug_log.write_text(
        _prev + f"[{__import__('datetime').datetime.now().isoformat()}] script started\n",
        encoding="utf-8",
    )
except Exception:
    pass

# 評価UIファイルを確認
evaluation_web_file = Path(__file__).parent / "image_evaluation_web.py"

if not evaluation_web_file.exists():
    print("[WARNING] image_evaluation_web.py が見つかりません")
    print("評価UIファイルを再作成します...")

    # 簡易版の評価UIを作成
    from flask import (
        Flask,
        render_template_string,
        jsonify,
        request,
        send_from_directory,
        send_file,
    )
    import json
    from datetime import datetime
    import time
    import mimetypes
    import threading

    try:
        from PIL import Image, ImageOps
    except Exception as e:
        try:
            _p = (_debug_log.read_text() + "\n") if _debug_log.exists() else ""
            _debug_log.write_text(
                _p
                + f"[{__import__('datetime').datetime.now().isoformat()}] PIL import failed: {e!r}\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        raise

    app = Flask(__name__)

    COMFYUI_OUTPUT_DIR = Path(os.getenv("COMFYUI_OUTPUT_DIR", "C:/ComfyUI/output"))
    COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    # generate_50 と同じベースでメタデータを参照（COMFYUI_BASE または OUTPUT の親）
    _comfyui_base = os.getenv("COMFYUI_BASE") or os.getenv("COMFYUI_PATH")
    if _comfyui_base:
        _base = Path(_comfyui_base)
    else:
        _base = COMFYUI_OUTPUT_DIR.parent
    EVALUATION_DB = _base / "input/mana_favorites/evaluation.json"
    GENERATION_METADATA_DB = _base / "input/mana_favorites/generation_metadata.json"
    # メタデータなし画像用：手動で入力したモデル・LoRAを保存（編集で追加可能）
    IMAGE_METADATA_OVERRIDE_DB = _base / "input/mana_favorites/image_metadata_override.json"

    # 評価データを読み込み
    evaluations = {}
    if EVALUATION_DB.exists():
        try:
            with open(EVALUATION_DB, "r", encoding="utf-8") as f:
                evaluations = json.load(f)
        except Exception:
            pass

    # 生成メタデータを読み込み（モデル・LoRA・プロンプト表示用）
    generation_metadata = {}
    path_to_meta = {}  # 画像パス or ファイル名 -> { model, loras, prompt, negative_prompt }
    # メタデータ（generation_metadata.json）はサイズが大きくなりやすいので、API呼び出し毎の再構築を避ける
    _META_CACHE = {"mtime": None, "path_to_meta": {}, "filename_to_meta": {}, "models": []}
    _OVERRIDE_CACHE = {"mtime": None, "override": {}}

    def _load_metadata_override():
        """手動メタ（メタデータなし画像用）を読み込み。キー: パス or ファイル名 -> { model, loras, prompt, negative_prompt }"""
        out = {}
        if not IMAGE_METADATA_OVERRIDE_DB.exists():
            return out
        try:
            mtime = IMAGE_METADATA_OVERRIDE_DB.stat().st_mtime
            if _OVERRIDE_CACHE.get("mtime") == mtime and _OVERRIDE_CACHE.get("override"):
                return _OVERRIDE_CACHE["override"]
            with open(IMAGE_METADATA_OVERRIDE_DB, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if isinstance(v, dict) and k:
                        out[str(k)] = {
                            "model": v.get("model", ""),
                            "loras": v.get("loras") if isinstance(v.get("loras"), list) else [],
                            "prompt": v.get("prompt", ""),
                            "negative_prompt": v.get("negative_prompt", ""),
                            "profile": v.get("profile", "safe"),
                        }
            _OVERRIDE_CACHE["mtime"] = mtime
            _OVERRIDE_CACHE["override"] = out
        except Exception:
            pass
        return out

    # ファイルスキャン（outputの画像一覧）はI/O負荷が高いので、短時間キャッシュする
    _FILES_CACHE = {"ts": 0.0, "base": None, "max_scan": None, "files": []}
    _FILES_CACHE_TTL_SEC = 2.0
    # スキャン対象パターン（必要なら環境変数で拡張）
    # 例: MANAOS_IMAGE_PATTERNS="ComfyUI_*.png;ComfyUI_*.jpg;ComfyUI_*.webp"
    IMAGE_PATTERNS = [
        p.strip()
        for p in os.getenv("MANAOS_IMAGE_PATTERNS", "ComfyUI_*.png").split(";")
        if p.strip()
    ]
    if GENERATION_METADATA_DB.exists():
        try:
            with open(GENERATION_METADATA_DB, "r", encoding="utf-8") as f:
                generation_metadata = json.load(f)
            for _pid, gen in generation_metadata.items():
                if not isinstance(gen, dict):
                    continue
                model = gen.get("model", "")
                loras = gen.get("loras", [])
                prompt = gen.get("prompt", "")
                negative_prompt = gen.get("negative_prompt", "")
                profile = gen.get("profile", "safe")  # safe=通常世界, lab=闇の実験室
                meta = {
                    "model": model,
                    "loras": loras,
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "profile": profile,
                }
                for p in gen.get("output_paths") or []:
                    path_to_meta[str(p).replace("/", os.sep)] = meta
                for fname in gen.get("output_filenames") or []:
                    base = os.path.basename(fname) if "/" in fname or "\\" in fname else fname
                    path_to_meta[base] = meta
                full = str(COMFYUI_OUTPUT_DIR).rstrip(os.sep) + os.sep
                for p in gen.get("output_paths") or []:
                    path_to_meta[
                        full + (os.path.basename(p) if "/" in str(p) or "\\" in str(p) else str(p))
                    ] = meta
        except Exception:
            pass

    try:
        _p = (_debug_log.read_text() + "\n") if _debug_log.exists() else ""
        _debug_log.write_text(
            _p
            + f"[{__import__('datetime').datetime.now().isoformat()}] generation_metadata loaded (keys={len(generation_metadata)})\n",
            encoding="utf-8",
        )
    except Exception:
        pass

    # メタデータから使用モデル一覧（フィルタ用）
    available_models = sorted(set(m.get("model") for m in path_to_meta.values() if m.get("model")))
    try:
        _p = (_debug_log.read_text() + "\n") if _debug_log.exists() else ""
        _debug_log.write_text(
            _p
            + f"[{__import__('datetime').datetime.now().isoformat()}] available_models done (count={len(available_models)})\n",
            encoding="utf-8",
        )
    except Exception:
        pass
    # ComfyUI履歴からの補完は重いのでデフォルト無効（必要なら true に）
    REFRESH_FROM_COMFYUI_HISTORY = (
        os.getenv("MANAOS_REFRESH_FROM_COMFYUI_HISTORY", "false").lower() == "true"
    )

    # サムネイル設定（B: 評価UI側で不足分だけ生成）
    THUMBS_DIRNAME = os.getenv("MANAOS_THUMBS_DIRNAME", ".thumbs").strip() or ".thumbs"
    THUMB_SIZE = int(os.getenv("MANAOS_THUMB_SIZE", "512"))  # 長辺最大
    THUMB_QUALITY = int(os.getenv("MANAOS_THUMB_QUALITY", "82"))
    _THUMB_LOCKS = {}
    _THUMB_LOCKS_GUARD = threading.Lock()

    @app.errorhandler(500)
    def handle_500(err):
        import traceback

        traceback.print_exc()
        return (
            jsonify(
                {
                    "error": str(err),
                    "total": 0,
                    "items": [],
                    "models": [],
                    "stats": {"total": 0, "evaluated": 0, "unevaluated": 0, "high_score": 0},
                }
            ),
            500,
        )

    @app.route("/favicon.ico")
    def favicon():
        from flask import Response

        # 1x1 透明 PNG（68バイト）を返して 404 を防ぐ
        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        import base64

        return Response(
            base64.b64decode(png_b64),
            status=200,
            mimetype="image/png",
        )

    @app.route("/")
    def index():
        return render_template_string(
            """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>画像評価</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🖼</text></svg>">
    <style>
        :root { --bg: #f5f5f5; --card-bg: white; --text: #333; --border: #ddd; --accent: #667eea; }
        [data-theme="dark"] { --bg: #1a1a2e; --card-bg: #16213e; --text: #e4e4e7; --border: #3f3f46; --accent: #818cf8; }
        body { font-family: Arial, sans-serif; margin: 20px; background: var(--bg); color: var(--text); transition: background .2s, color .2s; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: var(--text); }
        .stats { background: var(--card-bg); padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .controls { background: var(--card-bg); padding: 15px; border-radius: 5px; margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        .controls select, .controls input { padding: 8px; border: 2px solid var(--border); border-radius: 5px; background: var(--card-bg); color: var(--text); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .image-card { background: var(--card-bg); border-radius: 5px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .image-card img { width: 100%; height: auto; border-radius: 5px; cursor: pointer; }
        .score-buttons { display: flex; gap: 5px; margin: 10px 0; }
        .score-btn { flex: 1; padding: 10px; border: 2px solid var(--border); border-radius: 5px; cursor: pointer; background: var(--card-bg); color: var(--text); }
        .score-btn.active { background: var(--accent); color: white; border-color: var(--accent); }
        .comment-input { width: 100%; padding: 8px; border: 2px solid var(--border); border-radius: 5px; margin-top: 5px; background: var(--card-bg); color: var(--text); }
        .save-btn { width: 100%; padding: 10px; background: var(--accent); color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px; display: none; }
        .evaluated-badge { display: inline-block; padding: 5px 10px; background: #4CAF50; color: white; border-radius: 3px; font-size: 12px; margin-top: 5px; }
        .detail-btn { margin-top: 8px; padding: 6px 12px; background: #555; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 12px; }
        .detail-btn:hover { background: #333; }
        .per-image-info { margin-top: 6px; padding: 6px 8px; background: var(--bg); border-radius: 4px; font-size: 11px; color: var(--text); border-left: 3px solid var(--accent); }
        .per-image-info .info-title { font-weight: bold; color: #667eea; margin-bottom: 2px; }
        .profile-badge { font-size: 10px; background: #9e9e9e; color: #fff; padding: 1px 5px; border-radius: 3px; margin-left: 4px; }
        .profile-badge.profile-lab { background: #5c6bc0; }
        .per-image-info .info-model, .per-image-info .info-lora {
            color: #555; margin-top: 2px;
            max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .per-image-info .info-lora { color: #666; }
        .per-image-info-no-meta { border-left-color: #9e9e9e !important; }
        .per-image-info-no-meta .info-title { color: #757575; }
        .detail-panel { margin-top: 10px; padding: 10px; background: var(--bg); border-radius: 5px; font-size: 11px; text-align: left; max-height: 280px; overflow-y: auto; border: 1px solid var(--border); }
        .detail-panel .panel-title { font-weight: bold; color: #333; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #ddd; }
        .detail-panel .meta-label { font-weight: bold; color: #667eea; margin-top: 8px; }
        .detail-panel .meta-label:first-of-type { margin-top: 0; }
        .detail-panel pre { white-space: pre-wrap; word-break: break-word; margin: 4px 0 0 0; }
        .card-checkbox { margin-bottom: 8px; }
        .edit-meta-form { margin-top: 8px; padding: 10px; background: #f0f0f0; border-radius: 5px; }
        .edit-meta-form input, .edit-meta-form textarea { width: 100%; padding: 6px; margin: 4px 0; box-sizing: border-box; }
        .edit-meta-form button { margin-right: 8px; margin-top: 4px; }
        @media (max-width: 600px) {
            .grid { grid-template-columns: 1fr; }
            .controls { flex-direction: column; align-items: stretch; }
            body { margin: 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>画像評価</h1>
        <p style="font-size:12px;color:#888;margin-top:-8px;">カードをクリック → 1〜4キーでスコア、Ctrl+Enterで保存</p>
        <div class="stats" id="stats">読み込み中...</div>
        <div class="controls">
            <label>フィルタ:
                <select id="filter-status" onchange="loadImages(true)">
                    <option value="all">すべて</option>
                    <option value="unevaluated">未評価のみ</option>
                    <option value="evaluated">評価済み</option>
                    <option value="high-score">高評価のみ</option>
                </select>
            </label>
            <label>プロファイル:
                <select id="profile-filter" onchange="loadImages(true)">
                    <option value="all">すべて</option>
                    <option value="safe_only">通常のみ</option>
                    <option value="lab_only">実験室のみ</option>
                </select>
            </label>
            <label>使用モデル:
                <select id="model-filter" onchange="loadImages(true)">
                    <option value="">すべて</option>
                </select>
            </label>
            <label>並び順:
                <select id="sort-order" onchange="loadImages(true)">
                    <option value="newest">新着順</option>
                    <option value="oldest">古い順</option>
                    <option value="score-high">評価高い順</option>
                    <option value="score-low">評価低い順</option>
                </select>
            </label>
            <label>表示件数:
                <select id="page-limit" onchange="loadImages(true)">
                    <option value="50">50件</option>
                    <option value="100" selected>100件</option>
                    <option value="200">200件</option>
                    <option value="500">500件</option>
                </select>
            </label>
            <button onclick="loadImages(true)" style="padding: 8px 15px; background: var(--accent); color: white; border: none; border-radius: 5px; cursor: pointer;">更新</button>
            <button id="darkModeBtn" onclick="toggleDarkMode()" style="padding: 8px 12px; border: 2px solid var(--border); border-radius: 5px; cursor: pointer; background: var(--card-bg); color: var(--text);">🌙 ダーク</button>
            <span style="margin-left: 15px;">一括:</span>
            <select id="batch-score" style="width: auto;">
                <option value="">スコア選択</option>
                <option value="1">1 最高</option>
                <option value="2">2 高</option>
                <option value="3">3 普通</option>
                <option value="4">4 低</option>
            </select>
            <button id="batch-evaluate-btn" onclick="batchEvaluate()" style="padding: 8px 12px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">一括評価</button>
            <button id="batch-delete-btn" onclick="batchDelete()" style="padding: 8px 12px; background: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer;">一括削除</button>
        </div>
        <div class="grid" id="imageGrid"></div>
        <div id="loadMoreContainer" style="text-align: center; margin-top: 20px; display: none;">
            <button id="loadMoreBtn" onclick="loadImages(false)" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer;">もっと読み込む</button>
        </div>
    </div>
    <script>
        let currentScore = {};
        let imagesData = [];
        let pageOffset = 0;
        let totalAvailable = 0;
        let activeCardPath = null;

        function toggleDarkMode() {
            const html = document.documentElement;
            const isDark = html.getAttribute('data-theme') === 'dark';
            html.setAttribute('data-theme', isDark ? '' : 'dark');
            document.getElementById('darkModeBtn').textContent = isDark ? '🌙 ダーク' : '☀️ ライト';
            try { localStorage.setItem('evalUI-theme', isDark ? '' : 'dark'); } catch(_) {}
        }
        (function() {
            try {
                const t = localStorage.getItem('evalUI-theme');
                if (t === 'dark') { document.documentElement.setAttribute('data-theme', 'dark'); document.getElementById('darkModeBtn').textContent = '☀️ ライト'; }
            } catch(_) {}
        })();

        document.addEventListener('keydown', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
            if (e.key >= '1' && e.key <= '4') {
                const score = parseInt(e.key);
                const path = activeCardPath || (imagesData[0] && imagesData[0].path);
                if (path) {
                    const cards = document.querySelectorAll('.image-card');
                    for (const card of cards) {
                        if (card.getAttribute('data-image-full-path') === path) {
                            const btns = card.querySelectorAll('.score-btn');
                            if (btns[score - 1]) setScore(path, score, btns[score - 1]);
                            break;
                        }
                    }
                }
            }
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                const path = activeCardPath || (imagesData[0] && imagesData[0].path);
                if (path) saveEvaluation(path, true);
            }
        });

        // "/images/<path:filename>" に渡すための安全なURLパス化
        // - サブフォルダ (例: "lab/ComfyUI_....png") の "/" は維持
        // - 各セグメントのみ encodeURIComponent する
        function encodePathForUrl(p) {
            // NOTE: Python の文字列エスケープを経由するため、正規表現 /\\/g を出力するには \\\\ が必要
            const s = String(p || '').replace(/\\\\/g, '/').replace(/^\/+/, '');
            if (!s) return '';
            return s.split('/').map(seg => encodeURIComponent(seg)).join('/');
        }

        function handleThumbError(imgEl, encodedNameForUrl) {
            // まずフル解像度にフォールバック → それも失敗したらプレースホルダ
            try {
                if (!imgEl || !encodedNameForUrl) return;
                const triedFull = imgEl.getAttribute('data-tried-full');
                if (!triedFull) {
                    imgEl.setAttribute('data-tried-full', '1');
                    imgEl.src = '/images/' + encodedNameForUrl;
                    return;
                }
            } catch (e) {}
            imgEl.onerror = null;
            imgEl.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22300%22 height=%22300%22%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22%3E画像読み込みエラー%3C/text%3E%3C/svg%3E';
        }

        async function loadImages(reset = true) {
            const statsEl = document.getElementById('stats');
            const gridEl = document.getElementById('imageGrid');
            try {
                statsEl.innerHTML = '読み込み中...';
                if (reset) gridEl.innerHTML = '<div style="padding:40px;text-align:center;color:#666;">読み込み中...</div>';

                const filter = document.getElementById('filter-status').value;
                const profileFilter = (document.getElementById('profile-filter') && document.getElementById('profile-filter').value) || 'all';
                const modelFilter = (document.getElementById('model-filter') && document.getElementById('model-filter').value) || '';
                const sort = document.getElementById('sort-order').value;
                const limit = parseInt(document.getElementById('page-limit').value || '100', 10);
                if (reset) pageOffset = 0;

                let url = `/api/images?filter=${encodeURIComponent(filter)}&profile_filter=${encodeURIComponent(profileFilter)}&sort=${encodeURIComponent(sort)}&limit=${limit}&offset=${pageOffset}`;
                if (modelFilter) url += '&model_filter=' + encodeURIComponent(modelFilter);
                const response = await fetch(url);
                let payload = {};
                try {
                    payload = await response.json();
                } catch (_) {}
                if (!response.ok) {
                    const msg = payload.error
                        ? payload.error + ' (HTTP ' + response.status + ')'
                        : 'HTTP error! status: ' + response.status;
                    throw new Error(msg);
                }

                const items = Array.isArray(payload) ? payload : (payload.items || []);
                const stats = Array.isArray(payload) ? null : (payload.stats || null);
                totalAvailable = Array.isArray(payload) ? items.length : (payload.filtered_total || payload.total || 0);

                if (reset) {
                    imagesData = items;
                } else {
                    imagesData = imagesData.concat(items);
                }

                if (stats) updateStatsFromStats(stats);
                else updateStatsFromLocal();
                if (payload.models && Array.isArray(payload.models)) {
                    const sel = document.getElementById('model-filter');
                    if (sel) {
                        const current = sel.value;
                        const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                        const label = m => (m.length > 32 ? m.slice(0, 29) + '...' : m);
                        sel.innerHTML = '<option value="">すべて</option>' + payload.models.map(m => '<option value="' + esc(m) + '">' + esc(label(m)) + '</option>').join('');
                        if (payload.models.indexOf(current) >= 0) sel.value = current;
                    }
                }
                displayImages();

                pageOffset = imagesData.length;
                updateLoadMoreButton();
            } catch (error) {
                console.error('画像読み込みエラー:', error);
                document.getElementById('stats').innerHTML = '<strong style="color: red;">エラー: 画像を読み込めませんでした - ' + error.message + '</strong>';
            }
        }

        function updateStatsFromStats(stats) {
            document.getElementById('stats').innerHTML = `
                <strong>統計:</strong> 総数: ${stats.total}件 | 評価済み: ${stats.evaluated}件 | 未評価: ${stats.unevaluated}件 | 高評価: ${stats.high_score}件
            `;
        }

        function updateStatsFromLocal() {
            const total = imagesData.length;
            const evaluated = imagesData.filter(img => img.evaluated).length;
            const highScore = imagesData.filter(img => img.evaluated && img.score <= 2).length;
            document.getElementById('stats').innerHTML = `
                <strong>統計:</strong> 表示中: ${total}件 | 評価済み: ${evaluated}件 | 高評価: ${highScore}件
            `;
        }

        function updateLoadMoreButton() {
            const container = document.getElementById('loadMoreContainer');
            const btn = document.getElementById('loadMoreBtn');
            if (imagesData.length < totalAvailable) {
                container.style.display = 'block';
                btn.textContent = `もっと読み込む (残り${totalAvailable - imagesData.length}件)`;
            } else {
                container.style.display = 'none';
            }
        }

        function updateStats() {
            const total = imagesData.length;
            const evaluated = imagesData.filter(img => img.evaluated).length;
            const highScore = imagesData.filter(img => img.evaluated && img.score <= 2).length;
            document.getElementById('stats').innerHTML = `
                <strong>統計:</strong> 総数: ${total}件 | 評価済み: ${evaluated}件 | 高評価: ${highScore}件
            `;
        }

        function displayImages() {
            const grid = document.getElementById('imageGrid');
            grid.innerHTML = '';

            if (imagesData.length === 0) {
                grid.innerHTML = '<p>画像が見つかりませんでした</p>';
                return;
            }

            imagesData.forEach(img => {
                const card = document.createElement('div');
                card.className = 'image-card';
                const imgId = img.path.replace(/[^a-zA-Z0-9]/g, '_');
                card.setAttribute('data-image-path', imgId);
                card.setAttribute('data-image-full-path', img.path);

                // 既存の評価済みスコアをcurrentScoreに設定
                if (img.evaluated && img.score) {
                    currentScore[img.path] = img.score;
                }

                const meta = img.meta || {};
                const hasMeta = meta && (meta.model || (Array.isArray(meta.loras) && meta.loras.length) || meta.profile || meta.prompt);
                const modelStr = (meta.model || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                const lorasArr = Array.isArray(meta.loras) ? meta.loras : [];
                const loraStr = lorasArr.map(l => typeof l === 'object' && l != null ? (l.name || l) + (l.strength != null ? ' @ ' + l.strength : '') : String(l)).join(', ').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                const profileLabel = (meta.profile === 'lab') ? '実験室' : (meta.profile ? '通常' : '');
                const profileBadgeClass = (meta.profile === 'lab') ? 'profile-badge profile-lab' : 'profile-badge';
                const nameRaw = String(img.name || '');
                const nameEscHtml = nameRaw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                const nameForUrl = encodePathForUrl(nameRaw);
                const perImageInfoHtml = hasMeta ? `
                    <div class="per-image-info" title="この画像の生成情報">
                        <div class="info-title">この画像${profileLabel ? ' <span class="' + profileBadgeClass + '">' + profileLabel + '</span>' : ''}</div>
                        ${modelStr ? `<div class="info-model" title="${(meta.model || '').replace(/"/g, '&quot;')}">モデル: ${modelStr}</div>` : ''}
                        ${loraStr ? `<div class="info-lora" title="${(lorasArr.map(l => typeof l === 'object' && l != null ? (l.name || l) + (l.strength != null ? ' @ ' + l.strength : '') : String(l)).join(', ')).replace(/"/g, '&quot;')}">LoRA: ${loraStr}</div>` : ''}
                    </div>` : `
                    <div class="per-image-info per-image-info-no-meta" title="編集でモデル・LoRAを登録できます">
                        <div class="info-title">メタデータなし</div>
                        <div class="info-model">編集でモデル・LoRAを登録できます</div>
                    </div>`;

                card.addEventListener('click', function() { activeCardPath = img.path; });
                card.innerHTML = `
                    <div class="card-checkbox"><input type="checkbox" class="img-select-cb" data-path="${(img.path || '').replace(/"/g, '&quot;')}" id="cb_${imgId}"></div>
                    <img src="/thumbs/${nameForUrl}" alt="${nameEscHtml}" loading="lazy" decoding="async" onclick="openModal(${JSON.stringify(nameRaw)})" onerror="handleThumbError(this, '${nameForUrl}')">
                    ${perImageInfoHtml}
                    <div style="margin-top: 10px;">
                        <div class="score-buttons">
                            ${[1,2,3,4].map(score => `
                                <button class="score-btn ${(img.evaluated && img.score === score) ? 'active' : ''}"
                                        onclick="setScore('${img.path}', ${score}, this)">
                                    ${score}<br><small>${score === 1 ? '最高' : score === 2 ? '高' : score === 3 ? '普通' : '低'}</small>
                                </button>
                            `).join('')}
                        </div>
                        <textarea class="comment-input" id="comment_${imgId}"
                                  placeholder="コメント（オプション）"
                                  oninput="toggleSaveButton('${imgId}', this.value)"
                                  onkeydown="if(event.key==='Enter' && event.ctrlKey) { const imgPath = '${img.path.replace(/'/g, "\\'")}'; saveEvaluation(imgPath, true); }">${(img.comment || '').trim()}</textarea>
                        <button class="save-btn" id="save_${imgId}"
                                onclick="const imgPath = '${img.path.replace(/'/g, "\\'")}'; saveEvaluation(imgPath, true)"
                                style="display: ${(img.comment || '').trim() ? 'block' : 'none'}">保存</button>
                        ${img.evaluated ? `<div class="evaluated-badge">評価済み: ${img.score}点</div>` : ''}
                        <button class="detail-btn" onclick="toggleDetail('${imgId}', this)">詳細</button><button class="detail-btn" onclick="openEditMeta('${imgId}')" style="background:#2196F3;">編集</button><div class="detail-panel" id="detail_${imgId}" style="display:none;" data-meta="${encodeURIComponent(JSON.stringify(img.meta || {}))}"></div>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function toggleDetail(id, btn) {
            const el = document.getElementById('detail_' + id);
            if (!el) return;
            if (el.style.display === 'none') {
                if (!el.innerHTML) {
                    try {
                        const meta = JSON.parse(decodeURIComponent(el.getAttribute('data-meta') || '{}'));
                        const esc = s => (s == null ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                        const lorasStr = Array.isArray(meta.loras) ? meta.loras.map(l => typeof l === 'object' && l != null ? (l.name || l) + (l.strength != null ? ' @ ' + l.strength : '') : l).join(', ') : '';
                        el.innerHTML = '<div class="panel-title">この画像の生成情報</div><div class="meta-label">モデル</div><pre>' + esc(meta.model) + '</pre><div class="meta-label">LoRA</div><pre>' + esc(lorasStr) + '</pre><div class="meta-label">プロンプト</div><pre>' + esc(meta.prompt) + '</pre><div class="meta-label">ネガティブ</div><pre>' + esc(meta.negative_prompt) + '</pre>';
                    } catch (e) { el.innerHTML = '詳細の読み込みに失敗しました'; }
                }
                el.style.display = 'block';
                btn.textContent = '閉じる';
            } else {
                el.style.display = 'none';
                btn.textContent = '詳細';
            }
        }

        // ファイル名を抽出する関数
        function extractFileName(path) {
            // C:ComfyUIoutputComfyUI_04535_.png → ComfyUI_04535_.png
            // パターン: ComfyUI_数字_.png を探す
            const match = path.match(/ComfyUI_\d+_\.png$/);
            if (match) {
                return match[0];
            }
            // フォールバック: 最後の部分を取得
            return path.split(/[\\/:]/).pop();
        }

        // パスを比較する関数（ファイル名で比較）
        function pathsMatch(path1, path2) {
            const name1 = extractFileName(path1).toLowerCase();
            const name2 = extractFileName(path2).toLowerCase();
            return name1 === name2;
        }

        async function setScore(imagePath, score, buttonElement) {
            activeCardPath = imagePath;
            // ファイル名を抽出して、元のパス（img.path）を探す
            const fileName = extractFileName(imagePath);
            console.log('抽出されたファイル名:', fileName);

            // imagesDataから完全なパスを探す
            const matchedImg = imagesData.find(img => {
                const imgFileName = extractFileName(img.path);
                return imgFileName.toLowerCase() === fileName.toLowerCase();
            });

            if (matchedImg) {
                console.log('マッチした完全パス:', matchedImg.path);
                imagePath = matchedImg.path; // 完全なパスを使用
            }

            currentScore[imagePath] = score;
            const buttons = buttonElement.parentElement.querySelectorAll('.score-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            buttonElement.classList.add('active');

            const commentId = 'comment_' + imagePath.replace(/[^a-zA-Z0-9]/g, '_');
            const commentEl = document.getElementById(commentId);
            const hasComment = commentEl && commentEl.value.trim().length > 0;

            console.log('hasComment:', hasComment);

            if (!hasComment) {
                console.log('自動保存を実行します');
                await saveEvaluation(imagePath, false);
            } else {
                console.log('保存ボタンを表示します');
                const saveBtn = document.getElementById('save_' + imagePath.replace(/[^a-zA-Z0-9]/g, '_'));
                if (saveBtn) {
                    saveBtn.style.display = 'block';
                    console.log('保存ボタン表示完了');
                } else {
                    console.error('保存ボタンが見つかりません');
                }
            }
        }

        async function saveEvaluation(imagePath, showErrorAlert) {
            console.log('saveEvaluation called:', imagePath, 'showErrorAlert:', showErrorAlert);

            // ファイル名を抽出して、元のパス（img.path）を探す
            const fileName = extractFileName(imagePath);
            console.log('抽出されたファイル名:', fileName);

            // imagesDataから完全なパスを探す
            const matchedImg = imagesData.find(img => {
                const imgFileName = extractFileName(img.path);
                return imgFileName.toLowerCase() === fileName.toLowerCase();
            });

            if (matchedImg) {
                console.log('マッチした完全パス:', matchedImg.path);
                imagePath = matchedImg.path; // 完全なパスを使用
            }

            const score = currentScore[imagePath];
            console.log('currentScore for imagePath:', score);

            if (!score) {
                console.warn('スコアが設定されていません');
                if (showErrorAlert) alert('評価を選択してください');
                return;
            }

            // コメントを取得（複数の方法で試す）
            let comment = '';
            const imgId = imagePath.replace(/[^a-zA-Z0-9]/g, '_');
            const commentId = 'comment_' + imgId;
            let commentEl = document.getElementById(commentId);

            // 方法1: 正規化されたIDで検索
            if (!commentEl) {
                // 方法2: ファイル名から検索
                const fileName = extractFileName(imagePath);
                const allTextareas = document.querySelectorAll('textarea.comment-input');
                for (let ta of allTextareas) {
                    const taId = ta.id;
                    if (taId && taId.includes(fileName.replace(/[^a-zA-Z0-9]/g, '_'))) {
                        commentEl = ta;
                        console.log('コメント欄をファイル名で発見:', taId);
                        break;
                    }
                }
            }

            if (commentEl) {
                comment = commentEl.value.trim();
                console.log('コメント取得成功:', comment.length, '文字');
            } else {
                console.warn('コメント欄が見つかりません:', commentId);
            }

            console.log('評価データ:', {image_path: imagePath, score: score, comment: comment, comment_length: comment.length});

            try {
                console.log('APIリクエスト送信中...');
                const response = await fetch('/api/evaluate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({image_path: imagePath, score: score, comment: comment})
                });

                console.log('APIレスポンス:', response.status, response.statusText);

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('HTTPエラー:', response.status, errorText);
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                console.log('API結果:', result);

                if (result.success) {
                    console.log('評価保存成功！UIを更新します');

                    // 評価済みバッジを即座に更新（視覚的フィードバック）
                    console.log('カードを検索中 - imagePath:', imagePath);

                    // 複数の方法でカードを探す
                    let card = null;

                    // 方法1: data-image-full-pathで検索（ファイル名で比較）
                    const allCards = document.querySelectorAll('.image-card');
                    for (let c of allCards) {
                        const fullPath = c.getAttribute('data-image-full-path');
                        if (fullPath && pathsMatch(imagePath, fullPath)) {
                            card = c;
                            console.log('方法1でカード発見: data-image-full-path（正規化比較）');
                            break;
                        }
                    }

                    // 方法2: data-image-pathで検索（フォールバック）
                    if (!card) {
                        const imgId = imagePath.replace(/[^a-zA-Z0-9]/g, '_');
                        card = document.querySelector(`[data-image-path="${imgId}"]`);
                        if (card) {
                            console.log('方法2でカード発見: data-image-path');
                        }
                    }

                    // 方法3: 画像名で検索（最終フォールバック）
                    if (!card) {
                        const imgName = imagePath.split(/[\\/]/).pop();
                        for (let c of allCards) {
                            const img = c.querySelector('img');
                            if (img && (img.alt === imgName || img.src.includes(encodeURIComponent(imgName)))) {
                                card = c;
                                console.log('方法3でカード発見: 画像名', imgName);
                                break;
                            }
                        }
                    }

                    if (card) {
                        console.log('カード発見！バッジを更新します');
                        // 既存のバッジを探すか、新規作成
                        let badge = card.querySelector('.evaluated-badge');
                        if (!badge) {
                            badge = document.createElement('div');
                            badge.className = 'evaluated-badge';
                            // スコアボタンの親要素の後に追加
                            const scoreButtons = card.querySelector('.score-buttons');
                            if (scoreButtons && scoreButtons.parentNode) {
                                scoreButtons.parentNode.insertBefore(badge, scoreButtons.nextSibling);
                            } else {
                                // フォールバック: カードの最後に追加
                                card.appendChild(badge);
                            }
                        }
                        badge.textContent = '評価済み: ' + score + '点';
                        badge.style.display = 'inline-block';
                        console.log('バッジ更新完了');

                        // コメント欄をクリアして保存ボタンを非表示（コメントがない場合のみ）
                        if (!comment) {
                            if (commentEl) {
                                commentEl.value = '';
                                console.log('コメント欄をクリアしました');
                            }
                            const saveBtnId = 'save_' + imgId;
                            const saveBtn = document.getElementById(saveBtnId);
                            if (saveBtn) {
                                saveBtn.style.display = 'none';
                                console.log('保存ボタンを非表示にしました');
                            } else {
                                console.warn('保存ボタンが見つかりません:', saveBtnId);
                            }
                        } else {
                            // コメントがある場合は保存ボタンを表示
                            const saveBtnId = 'save_' + imgId;
                            const saveBtn = document.getElementById(saveBtnId);
                            if (saveBtn) {
                                saveBtn.style.display = 'block';
                                console.log('保存ボタンを表示しました（コメントあり）');
                            }
                        }

                        // 画像データを更新（再読み込みせずに）
                        const imgIndex = imagesData.findIndex(img => img.path === imagePath);
                        if (imgIndex >= 0) {
                            imagesData[imgIndex].evaluated = true;
                            imagesData[imgIndex].score = score;
                            imagesData[imgIndex].comment = comment;
                            console.log('画像データ更新完了');
                        }
                    } else {
                        console.warn('カードが見つかりません。全カードを確認します...');
                        const allCards = document.querySelectorAll('.image-card');
                        console.log('総カード数:', allCards.length);
                        // 最初の3つのカードのdata属性を確認
                        for (let i = 0; i < Math.min(3, allCards.length); i++) {
                            const c = allCards[i];
                            console.log(`カード${i}:`, c.getAttribute('data-image-path'), c.getAttribute('data-image-full-path'));
                        }
                    }

                    // 統計を更新（ページ全体を再読み込みしない）
                    const statsResp = await fetch('/api/images?filter=all&limit=1&offset=0');
                    if (statsResp.ok) {
                        const statsData = await statsResp.json();
                        if (statsData.stats) {
                            updateStatsFromStats(statsData.stats);
                        }
                    }

                    console.log('評価完了！');
                } else {
                    console.error('評価保存失敗:', result.error);
                    if (showErrorAlert) alert('エラー: ' + (result.error || '評価の保存に失敗しました'));
                }
            } catch (error) {
                console.error('評価保存エラー:', error);
                if (showErrorAlert) alert('評価の保存に失敗しました: ' + error.message);
            }
        }

        function openModal(imgName) {
            window.open(`/images/${encodePathForUrl(imgName)}`, '_blank');
        }

        function getSelectedPaths() {
            const cbs = document.querySelectorAll('.img-select-cb:checked');
            return Array.from(cbs).map(cb => cb.getAttribute('data-path')).filter(Boolean);
        }

        async function batchEvaluate() {
            const paths = getSelectedPaths();
            const score = document.getElementById('batch-score').value;
            if (!paths.length) { alert('画像を選択してください'); return; }
            if (!score) { alert('一括評価のスコアを選択してください'); return; }
            const items = paths.map(p => ({ image_path: p, score: parseInt(score, 10), comment: '' }));
            try {
                const r = await fetch('/api/batch-evaluate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ items }) });
                const res = await r.json();
                if (res.success) { alert('一括評価しました: ' + res.updated + '件'); loadImages(true); }
                else alert('エラー: ' + (res.error || ''));
            } catch (e) { alert('エラー: ' + e.message); }
        }

        async function batchDelete() {
            const paths = getSelectedPaths();
            if (!paths.length) { alert('画像を選択してください'); return; }
            if (!confirm('選択した ' + paths.length + ' 件の画像を削除します。よろしいですか？')) return;
            try {
                const r = await fetch('/api/batch-delete', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ image_paths: paths }) });
                const res = await r.json();
                if (res.success) { alert('削除しました: ' + res.deleted + '件'); loadImages(true); }
                else alert('エラー: ' + (res.error || ''));
            } catch (e) { alert('エラー: ' + e.message); }
        }

        function openEditMeta(imgId) {
            const card = document.querySelector('[data-image-path="' + imgId + '"]');
            const path = card ? card.getAttribute('data-image-full-path') : '';
            const img = imagesData.find(i => (i.path || '').replace(/[^a-zA-Z0-9]/g, '_') === imgId);
            const meta = (img && img.meta) ? img.meta : {};
            const model = meta.model || '';
            const loras = meta.loras || [];
            const lorasStr = Array.isArray(loras) ? loras.map(l => typeof l === 'object' && l != null ? (l.name || l) + (l.strength != null ? ' @ ' + l.strength : '') : l).join(', ') : '';
            const prompt = meta.prompt || '';
            const neg = meta.negative_prompt || '';
            const pathAttr = ((img && img.path) ? img.path : path || '').replace(/"/g, '&quot;').replace(/</g, '&lt;');
            const html = '<div class="edit-meta-form" data-image-path="' + pathAttr + '"><label>モデル</label><input type="text" id="edit-model" value="' + (model.replace(/"/g, '&quot;').replace(/</g, '&lt;')) + '"><label>LoRA (name @ strength をカンマ区切り)</label><input type="text" id="edit-loras" value="' + (lorasStr.replace(/"/g, '&quot;').replace(/</g, '&lt;')) + '"><label>プロンプト</label><textarea id="edit-prompt" rows="4">' + (prompt.replace(/</g, '&lt;').replace(/&/g, '&amp;')) + '</textarea><label>ネガティブ</label><textarea id="edit-neg" rows="2">' + (neg.replace(/</g, '&lt;').replace(/&/g, '&amp;')) + '</textarea><button onclick="saveEditMeta(this)">保存</button><button onclick="this.closest(&quot;.edit-meta-form&quot;).parentElement.remove()">キャンセル</button></div>';
            const wrap = document.createElement('div');
            wrap.id = 'edit-meta-wrap-' + imgId;
            wrap.innerHTML = html;
            const panel = document.getElementById('detail_' + imgId);
            if (panel) {
                const oldEdit = panel.querySelector('.edit-meta-form');
                if (oldEdit) oldEdit.remove();
                panel.appendChild(wrap.firstElementChild);
                panel.style.display = 'block';
            } else {
                const cardInner = card ? card.querySelector('.score-buttons') : null;
                if (cardInner && cardInner.parentNode) cardInner.parentNode.insertBefore(wrap.firstElementChild, cardInner.nextSibling);
            }
        }

        async function saveEditMeta(btn) {
            const form = btn && btn.closest ? btn.closest('.edit-meta-form') : null;
            const imagePath = form ? form.getAttribute('data-image-path') : '';
            const model = document.getElementById('edit-model') ? document.getElementById('edit-model').value : '';
            const lorasStr = document.getElementById('edit-loras') ? document.getElementById('edit-loras').value : '';
            const loras = lorasStr.split(',').map(s => s.trim()).filter(Boolean).map(s => {
                const at = s.indexOf(' @ ');
                if (at >= 0) return { name: s.slice(0, at).trim(), strength: parseFloat(s.slice(at + 3)) || 0.7 };
                return { name: s, strength: 0.7 };
            });
            const prompt = document.getElementById('edit-prompt') ? document.getElementById('edit-prompt').value : '';
            const negative_prompt = document.getElementById('edit-neg') ? document.getElementById('edit-neg').value : '';
            if (!imagePath) { alert('画像パスが取得できません'); return; }
            try {
                const r = await fetch('/api/metadata', { method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ image_path: imagePath, model, loras, prompt, negative_prompt }) });
                const res = await r.json();
                if (res.success) { alert('メタデータを保存しました'); loadImages(true); }
                else alert('エラー: ' + (res.error || ''));
            } catch (e) { alert('エラー: ' + e.message); }
        }

        function toggleSaveButton(imgId, commentValue) {
            console.log('toggleSaveButton called:', imgId, 'commentValue length:', commentValue.trim().length);
            const saveBtn = document.getElementById('save_' + imgId);
            if (saveBtn) {
                const shouldShow = commentValue.trim().length > 0;
                saveBtn.style.display = shouldShow ? 'block' : 'none';
                console.log('保存ボタンの表示状態:', shouldShow ? '表示' : '非表示');
            } else {
                console.error('保存ボタンが見つかりません: save_' + imgId);
            }
        }

        loadImages();
    </script>
</body>
</html>
        """
        )

    def _get_output_from_comfyui_history(prompt_id):
        """ComfyUI /history/{prompt_id} から出力ファイル名を取得（空なら []）。HTTP/JSONエラーはログ出力。"""
        import urllib.request
        import urllib.error

        try:
            req = urllib.request.Request(
                f"{COMFYUI_URL}/history/{prompt_id}",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                raw = r.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"[WARN] ComfyUI履歴JSONパースエラー prompt_id={prompt_id}: {e}", flush=True)
                return [], []
            item = data.get(prompt_id) if isinstance(data, dict) else None
            if not isinstance(item, dict):
                return [], []
            outputs = item.get("outputs", {}) or {}
            filenames, paths = [], []
            for out in outputs.values() if isinstance(outputs, dict) else []:
                if not isinstance(out, dict):
                    continue
                for img in out.get("images", []) or []:
                    if not isinstance(img, dict):
                        continue
                    if img.get("type") and img.get("type") != "output":
                        continue
                    fn = img.get("filename")
                    if not fn:
                        continue
                    sub = (img.get("subfolder") or "").strip()
                    filenames.append(fn if not sub else f"{sub}/{fn}")
                    paths.append(
                        str(COMFYUI_OUTPUT_DIR / sub / fn) if sub else str(COMFYUI_OUTPUT_DIR / fn)
                    )
            return filenames, paths
        except urllib.error.HTTPError as e:
            print(f"[WARN] ComfyUI履歴 HTTP {e.code} prompt_id={prompt_id}: {e.reason}", flush=True)
            return [], []
        except urllib.error.URLError as e:
            print(f"[WARN] ComfyUI履歴 URLエラー prompt_id={prompt_id}: {e.reason}", flush=True)
            return [], []
        except OSError as e:
            print(f"[WARN] ComfyUI履歴 接続エラー prompt_id={prompt_id}: {e}", flush=True)
            return [], []
        except Exception as e:
            print(f"[WARN] ComfyUI履歴 取得エラー prompt_id={prompt_id}: {e}", flush=True)
            return [], []

    def _norm(path_str):
        """パスを正規化（スラッシュ統一・比較用）"""
        if not path_str:
            return ""
        return os.path.normpath(str(path_str).replace("/", os.sep))

    def _build_path_to_meta():
        """generation_metadata.json から path_to_meta を組み立て。空の出力はComfyUI履歴から補完。"""
        p2m = {}
        if not GENERATION_METADATA_DB.exists():
            return p2m
        try:
            with open(GENERATION_METADATA_DB, "r", encoding="utf-8") as f:
                gen_meta = json.load(f)
            dirty = False
            for _pid, gen in gen_meta.items():
                if not isinstance(gen, dict):
                    continue
                ofns = gen.get("output_filenames") or []
                opaths = gen.get("output_paths") or []
                # 単数形のみのエントリ（他ツール出力）にも対応
                if not ofns and gen.get("output_filename"):
                    ofns = [gen.get("output_filename")]
                if not opaths and gen.get("output_path"):
                    opaths = [gen.get("output_path")]
                pid = (gen.get("prompt_id") or "").strip()
                # NOTE: ここでComfyUIのhistoryへ問い合わせると /api/images が極端に遅くなるためデフォルト無効
                if REFRESH_FROM_COMFYUI_HISTORY and pid and not ofns:
                    fns, path_list = _get_output_from_comfyui_history(pid)
                    if fns and path_list:
                        gen["output_filenames"] = fns
                        gen["output_paths"] = path_list
                        ofns, opaths = fns, path_list
                        dirty = True
                meta = {
                    "model": gen.get("model", ""),
                    "loras": gen.get("loras", []),
                    "prompt": gen.get("prompt", ""),
                    "negative_prompt": gen.get("negative_prompt", ""),
                    "profile": gen.get("profile", "safe"),
                }
                out_dir_str = str(COMFYUI_OUTPUT_DIR)
                full = _norm(out_dir_str.rstrip(os.sep) + os.sep)
                for p in opaths:
                    key = _norm(p)
                    p2m[key] = meta
                    # パス区切り違いでもヒットするよう両方登録
                    p2m[key.replace("\\", "/")] = meta
                    p2m[key.replace("/", "\\")] = meta
                    base = os.path.basename(key)
                    p2m[base] = meta
                    try:
                        rel = os.path.relpath(key, out_dir_str)
                        if rel != base:
                            p2m[rel] = meta
                            p2m[rel.replace("\\", "/")] = meta
                            p2m[rel.replace("/", "\\")] = meta
                        # lab サブフォルダ: lab\filename / lab/filename も登録
                        if "lab" in rel.lower():
                            p2m["lab/" + base] = meta
                            p2m["lab\\" + base] = meta
                    except ValueError:
                        pass
                    p2m[full + base] = meta
                    # lab 内のファイルは full + "lab" + sep + base も登録
                    if "lab" in key.lower() and ("lab" + os.sep in key or "lab/" in key):
                        p2m[_norm(full + "lab" + os.sep + base)] = meta
                for fname in ofns:
                    base = os.path.basename(fname) if "/" in fname or "\\" in fname else fname
                    p2m[base] = meta
                    p2m[fname] = meta
                    p2m[fname.replace("\\", "/")] = meta
                    p2m[fname.replace("/", "\\")] = meta
                    if "lab" in fname.lower():
                        p2m["lab/" + base] = meta
                        p2m["lab\\" + base] = meta
            if dirty:
                try:
                    GENERATION_METADATA_DB.parent.mkdir(parents=True, exist_ok=True)
                    with open(GENERATION_METADATA_DB, "w", encoding="utf-8") as f:
                        json.dump(gen_meta, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
        except Exception:
            pass
        return p2m

    def _build_filename_to_meta():
        """ファイル名 -> メタのマップを1回だけJSONを読んで構築（重い _find_meta_by_filename の代わり）"""
        f2m = {}
        if not GENERATION_METADATA_DB.exists():
            return f2m
        try:
            with open(GENERATION_METADATA_DB, "r", encoding="utf-8") as f:
                gen_meta = json.load(f)
            for _pid, gen in gen_meta.items():
                if not isinstance(gen, dict):
                    continue
                meta = {
                    "model": gen.get("model", ""),
                    "loras": gen.get("loras", []),
                    "prompt": gen.get("prompt", ""),
                    "negative_prompt": gen.get("negative_prompt", ""),
                    "profile": gen.get("profile", "safe"),
                }
                for p in gen.get("output_paths") or []:
                    f2m[os.path.basename(p) if "/" in str(p) or "\\" in str(p) else str(p)] = meta
                if gen.get("output_path"):
                    f2m[os.path.basename(gen.get("output_path", ""))] = meta
                for fname in gen.get("output_filenames") or []:
                    fn = os.path.basename(fname) if "/" in fname or "\\" in fname else fname
                    f2m[fn] = meta
                if gen.get("output_filename"):
                    f2m[gen.get("output_filename") or ""] = meta
        except Exception:
            pass
        return f2m

    def _get_cached_meta_maps():
        """generation_metadata.json 由来の各種マップをmtimeベースでキャッシュして返す。"""
        if not GENERATION_METADATA_DB.exists():
            _META_CACHE["mtime"] = None
            _META_CACHE["path_to_meta"] = {}
            _META_CACHE["filename_to_meta"] = {}
            _META_CACHE["models"] = []
            return (
                _META_CACHE["path_to_meta"],
                _META_CACHE["filename_to_meta"],
                _META_CACHE["models"],
            )

        try:
            mtime = GENERATION_METADATA_DB.stat().st_mtime
        except Exception:
            mtime = None

        if _META_CACHE.get("mtime") == mtime and _META_CACHE.get("path_to_meta"):
            return (
                _META_CACHE["path_to_meta"],
                _META_CACHE["filename_to_meta"],
                _META_CACHE["models"],
            )

        path_to_meta_local = _build_path_to_meta()
        filename_to_meta_local = _build_filename_to_meta()
        models_local = sorted(
            set(m.get("model") for m in path_to_meta_local.values() if m.get("model"))
            | set(m.get("model") for m in filename_to_meta_local.values() if m.get("model"))
        )
        _META_CACHE["mtime"] = mtime
        _META_CACHE["path_to_meta"] = path_to_meta_local
        _META_CACHE["filename_to_meta"] = filename_to_meta_local
        _META_CACHE["models"] = models_local
        return path_to_meta_local, filename_to_meta_local, models_local

    def _scan_latest_files(max_scan: int):
        """output直下＆output/lab から画像をスキャンして新着順に返す（短時間キャッシュ付き）。"""
        base = str(COMFYUI_OUTPUT_DIR.resolve())
        now = time.time()
        if (
            _FILES_CACHE.get("base") == base
            and _FILES_CACHE.get("max_scan") == max_scan
            and (now - float(_FILES_CACHE.get("ts") or 0.0)) < _FILES_CACHE_TTL_SEC
        ):
            return list(_FILES_CACHE.get("files") or [])

        all_files = []
        for pat in IMAGE_PATTERNS:
            all_files.extend(COMFYUI_OUTPUT_DIR.glob(pat))
        lab_dir = COMFYUI_OUTPUT_DIR / "lab"
        if lab_dir.exists():
            for pat in IMAGE_PATTERNS:
                all_files.extend(lab_dir.glob(pat))

        # mtime でソート（新着順）
        all_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        all_files = all_files[:max_scan]

        _FILES_CACHE["ts"] = now
        _FILES_CACHE["base"] = base
        _FILES_CACHE["max_scan"] = max_scan
        _FILES_CACHE["files"] = list(all_files)
        return all_files

    @app.route("/api/images")
    def get_images():
        try:
            if not COMFYUI_OUTPUT_DIR.exists() or not COMFYUI_OUTPUT_DIR.is_dir():
                return jsonify(
                    {
                        "total": 0,
                        "items": [],
                        "models": [],
                        "stats": {"total": 0, "evaluated": 0, "unevaluated": 0, "high_score": 0},
                    }
                )

            # generation_metadata.json はサイズが大きくなりやすいので、mtimeベースでキャッシュして高速化
            path_to_meta, filename_to_meta, available_models = _get_cached_meta_maps()
            metadata_override = _load_metadata_override()
            # 手動メタのモデル名をフィルタ用に追加
            override_models = sorted(
                set(m.get("model") for m in metadata_override.values() if m.get("model"))
            )
            available_models = sorted(set(available_models) | set(override_models))

            # クエリパラメータを取得（不正値はデフォルトにフォールバック）
            filter_status = request.args.get(
                "filter", "all"
            )  # all, evaluated, unevaluated, high-score
            profile_filter = request.args.get("profile_filter", "all")  # all, safe_only, lab_only
            model_filter = request.args.get("model_filter", "")  # 使用モデルで絞り込み
            sort_order = request.args.get("sort", "newest")  # newest, oldest, score-high, score-low
            try:
                limit = int(request.args.get("limit") or 200)
            except (TypeError, ValueError):
                limit = 200
            try:
                offset = int(request.args.get("offset") or 0)
            except (TypeError, ValueError):
                offset = 0

            # output 直下と lab のみスキャン。最新 MAX_SCAN 件に制限
            MAX_SCAN = 10000
            all_files = _scan_latest_files(MAX_SCAN)

            # 全ファイルから item を組み立て（フィルタ・ソートのため）
            all_items = []
            for img_file in all_files:
                try:
                    img_path = str(img_file)
                    img_path_norm = _norm(img_path)
                    try:
                        name_for_url = img_file.relative_to(COMFYUI_OUTPUT_DIR).as_posix()
                    except ValueError:
                        name_for_url = img_file.name
                    # 評価データ取得: パス表記ゆれ（/ と \）に対応
                    eval_data = (
                        evaluations.get(img_path)
                        or evaluations.get(img_path_norm)
                        or evaluations.get(img_path.replace("\\", "/"))
                        or evaluations.get(img_path.replace("/", "\\"))
                    )
                    evaluated = eval_data is not None
                    score = eval_data.get("score") if evaluated else None
                    comment = eval_data.get("comment", "") if evaluated else ""

                    # メタデータ紐付け: 複数のキーで検索（フルパス、正規化パス、ファイル名、相対パス、パス区切り違い）
                    basename = img_file.name
                    name_for_url_basename = (
                        name_for_url.split("/")[-1] if "/" in name_for_url else name_for_url
                    )
                    meta = (
                        path_to_meta.get(img_path)
                        or path_to_meta.get(img_path_norm)
                        or path_to_meta.get(img_path.replace("\\", "/"))
                        or path_to_meta.get(img_path.replace("/", "\\"))
                        or path_to_meta.get(basename)
                        or path_to_meta.get(name_for_url)
                        or path_to_meta.get(name_for_url.replace("/", "\\"))
                        or path_to_meta.get(name_for_url_basename)
                        or path_to_meta.get("lab/" + basename)
                        or path_to_meta.get("lab\\" + basename)
                        or filename_to_meta.get(basename)
                        or filename_to_meta.get(name_for_url_basename)
                        or metadata_override.get(img_path)
                        or metadata_override.get(img_path_norm)
                        or metadata_override.get(basename)
                        or metadata_override.get(name_for_url_basename)
                    )
                    meta_profile = (meta or {}).get("profile", "")
                    meta_model = (meta or {}).get("model", "")

                    all_items.append(
                        {
                            "name": name_for_url,
                            "path": img_path,
                            "mtime": img_file.stat().st_mtime,
                            "evaluated": evaluated,
                            "score": score,
                            "comment": comment,
                            "meta": meta,
                            "_profile": meta_profile,
                            "_model": meta_model,
                        }
                    )
                except Exception as e:
                    print(f"画像読み込みエラー: {img_file} - {e}")
                    continue

            # フィルタ適用
            if filter_status == "unevaluated":
                all_items = [x for x in all_items if not x["evaluated"]]
            elif filter_status == "evaluated":
                all_items = [x for x in all_items if x["evaluated"]]
            elif filter_status == "high-score":
                all_items = [
                    x
                    for x in all_items
                    if x["evaluated"] and x["score"] is not None and x["score"] <= 2
                ]

            if profile_filter == "safe_only":
                all_items = [x for x in all_items if x.get("_profile") != "lab"]
            elif profile_filter == "lab_only":
                all_items = [x for x in all_items if x.get("_profile") == "lab"]

            if model_filter:
                model_filter_lower = model_filter.lower()
                all_items = [
                    x for x in all_items if (x.get("_model") or "").lower() == model_filter_lower
                ]

            # ソート適用
            if sort_order == "oldest":
                all_items.sort(key=lambda x: x["mtime"])
            elif sort_order == "score-high":
                # 高評価順（スコア1,2,3,4）、未評価は末尾
                def _score_sort_key(x):
                    if not x["evaluated"] or x["score"] is None:
                        return (1, 999)
                    return (0, x["score"])

                all_items.sort(key=_score_sort_key)
            elif sort_order == "score-low":
                # 低評価順（スコア4,3,2,1）、未評価は末尾
                def _score_sort_key_low(x):
                    if not x["evaluated"] or x["score"] is None:
                        return (1, -1)
                    return (0, -x["score"])

                all_items.sort(key=_score_sort_key_low)
            else:
                # newest（デフォルト）: mtime 降順
                all_items.sort(key=lambda x: x["mtime"], reverse=True)

            filtered_total = len(all_items)

            # ページネーション: offset, limit でスライス
            items = all_items[offset : offset + limit]

            # 統計はフィルタ適用後の全件ベース
            evaluated_count = sum(1 for x in all_items if x["evaluated"])
            high_score_count = sum(
                1
                for x in all_items
                if x["evaluated"] and x["score"] is not None and x["score"] <= 2
            )

            # 内部キーを削除（クライアントには不要）
            for item in items:
                item.pop("mtime", None)
                item.pop("_profile", None)
                item.pop("_model", None)

            return jsonify(
                {
                    "total": filtered_total,
                    "filtered_total": filtered_total,
                    "items": items,
                    "models": available_models,
                    "stats": {
                        "total": filtered_total,
                        "evaluated": evaluated_count,
                        "unevaluated": filtered_total - evaluated_count,
                        "high_score": high_score_count,
                    },
                }
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            return (
                jsonify(
                    {
                        "total": 0,
                        "items": [],
                        "models": [],
                        "stats": {"total": 0, "evaluated": 0, "unevaluated": 0, "high_score": 0},
                        "error": str(e),
                    }
                ),
                500,
            )

    @app.route("/api/evaluate", methods=["POST"])
    def evaluate():
        data = request.json
        img_path = data.get("image_path")
        score = data.get("score")
        comment = data.get("comment", "").strip()

        if not img_path or not score:
            return jsonify({"success": False, "error": "画像パスとスコアが必要です"})

        # 保存キーを正規化して一貫性を保つ（読み出し時の複数キー検索と合わせる）
        key = _norm(img_path)
        evaluations[key] = {
            "score": score,
            "comment": comment,
            "evaluated_at": datetime.now().isoformat(),
        }
        # 旧キー（表記ゆれ）を削除して重複を防ぐ
        for old_key in [img_path, img_path.replace("\\", "/"), img_path.replace("/", "\\")]:
            if old_key != key and old_key in evaluations:
                del evaluations[old_key]

        try:
            EVALUATION_DB.parent.mkdir(parents=True, exist_ok=True)
            with open(EVALUATION_DB, "w", encoding="utf-8") as f:
                json.dump(evaluations, f, ensure_ascii=False, indent=2)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    @app.route("/api/batch-evaluate", methods=["POST"])
    def batch_evaluate():
        """複数画像を一括評価。body: { "items": [ { "image_path": "...", "score": 1, "comment": "" } ] }"""
        data = request.json or {}
        items = data.get("items") or []
        if not items:
            return jsonify({"success": False, "error": "items が必要です", "updated": 0})
        updated = 0
        for it in items:
            img_path = it.get("image_path")
            score = it.get("score")
            comment = (it.get("comment") or "").strip()
            if not img_path or not score:
                continue
            key = _norm(img_path)
            evaluations[key] = {
                "score": score,
                "comment": comment,
                "evaluated_at": datetime.now().isoformat(),
            }
            updated += 1
        try:
            EVALUATION_DB.parent.mkdir(parents=True, exist_ok=True)
            with open(EVALUATION_DB, "w", encoding="utf-8") as f:
                json.dump(evaluations, f, ensure_ascii=False, indent=2)
            return jsonify({"success": True, "updated": updated})
        except Exception as e:
            return jsonify({"success": False, "error": str(e), "updated": updated})

    @app.route("/api/batch-delete", methods=["POST"])
    def batch_delete():
        """選択した画像を削除（ファイル削除＋評価データから除去）。body: { "image_paths": ["..."] }"""
        data = request.json or {}
        paths = data.get("image_paths") or []
        if not paths:
            return jsonify({"success": False, "error": "image_paths が必要です", "deleted": 0})
        deleted = 0
        output_root = COMFYUI_OUTPUT_DIR.resolve()
        for img_path in paths:
            p = Path(img_path)
            if not p.is_absolute():
                # 相対の場合は output 直下または lab 等サブフォルダを探す
                cand = output_root / img_path
                if not cand.exists():
                    cand = output_root / p.name
                p = cand if cand.exists() else None
            else:
                p = p.resolve() if p.exists() else None
                if p:
                    try:
                        p.relative_to(output_root)  # 出力フォルダ外は削除しない
                    except ValueError:
                        p = None
            if p and p.exists():
                try:
                    p.unlink()
                    deleted += 1
                except Exception:
                    pass
            evaluations.pop(img_path, None)
            if p:
                evaluations.pop(str(p), None)
        try:
            EVALUATION_DB.parent.mkdir(parents=True, exist_ok=True)
            with open(EVALUATION_DB, "w", encoding="utf-8") as f:
                json.dump(evaluations, f, ensure_ascii=False, indent=2)
            return jsonify({"success": True, "deleted": deleted})
        except Exception as e:
            return jsonify({"success": False, "error": str(e), "deleted": deleted})

    def _find_prompt_id_by_image_path(img_path):
        """generation_metadata から image_path に一致する prompt_id を返す"""
        if not GENERATION_METADATA_DB.exists():
            return None
        try:
            with open(GENERATION_METADATA_DB, "r", encoding="utf-8") as f:
                gen_meta = json.load(f)
        except Exception:
            return None
        img_name = Path(img_path).name if img_path else ""
        for pid, gen in gen_meta.items():
            if not isinstance(gen, dict):
                continue
            for op in gen.get("output_paths") or []:
                if op == img_path or Path(op).name == img_name:
                    return pid
            for of in gen.get("output_filenames") or []:
                if of == img_name or of.endswith(img_name):
                    return pid
        return None

    @app.route("/api/metadata", methods=["PATCH"])
    def patch_metadata():
        """画像に紐づくメタデータを更新。body: { "image_path": "...", "model": "", "loras": [], "prompt": "", "negative_prompt": "" }
        生成メタに無い画像（メタデータなし）は手動メタとして image_metadata_override.json に保存し、表示に反映する。"""
        data = request.json or {}
        img_path = data.get("image_path")
        if not img_path:
            return jsonify({"success": False, "error": "image_path が必要です"})
        pid = _find_prompt_id_by_image_path(img_path)
        if pid:
            # 既存の generation_metadata に存在する場合は従来どおり更新
            gen_meta = {}
            if GENERATION_METADATA_DB.exists():
                try:
                    with open(GENERATION_METADATA_DB, "r", encoding="utf-8") as f:
                        gen_meta = json.load(f)
                except Exception:
                    pass
            entry = gen_meta.get(pid)
            if isinstance(entry, dict):
                if "model" in data:
                    entry["model"] = data["model"]
                if "loras" in data:
                    entry["loras"] = data["loras"]
                if "prompt" in data:
                    entry["prompt"] = data["prompt"]
                if "negative_prompt" in data:
                    entry["negative_prompt"] = data["negative_prompt"]
                try:
                    GENERATION_METADATA_DB.parent.mkdir(parents=True, exist_ok=True)
                    with open(GENERATION_METADATA_DB, "w", encoding="utf-8") as f:
                        json.dump(gen_meta, f, ensure_ascii=False, indent=2)
                    return jsonify({"success": True})
                except Exception as e:
                    return jsonify({"success": False, "error": str(e)})
        # メタデータなし画像 → 手動メタとしてオーバーライドに保存（編集でモデル等を表示できるようにする）
        entry = {
            "model": data.get("model", ""),
            "loras": data.get("loras") if isinstance(data.get("loras"), list) else [],
            "prompt": data.get("prompt", ""),
            "negative_prompt": data.get("negative_prompt", ""),
            "profile": data.get("profile", "safe"),
        }
        override = {}
        if IMAGE_METADATA_OVERRIDE_DB.exists():
            try:
                with open(IMAGE_METADATA_OVERRIDE_DB, "r", encoding="utf-8") as f:
                    override = json.load(f)
            except Exception:
                pass
        if not isinstance(override, dict):
            override = {}
        key_norm = _norm(img_path)
        basename = os.path.basename(img_path) if "/" in img_path or "\\" in img_path else img_path
        override[key_norm] = entry
        override[basename] = entry
        override[key_norm.replace("\\", "/")] = entry
        override[key_norm.replace("/", "\\")] = entry
        if "lab" in key_norm.lower():
            override["lab/" + basename] = entry
            override["lab\\" + basename] = entry
        try:
            IMAGE_METADATA_OVERRIDE_DB.parent.mkdir(parents=True, exist_ok=True)
            with open(IMAGE_METADATA_OVERRIDE_DB, "w", encoding="utf-8") as f:
                json.dump(override, f, ensure_ascii=False, indent=2)
            _OVERRIDE_CACHE["mtime"] = None  # 次回読み込みで再読み込み
            return jsonify({"success": True, "saved_as": "override"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    @app.route("/images/<path:filename>")
    def serve_image(filename):
        from flask import abort
        from urllib.parse import unquote

        # Flask/Werkzeug が %2F をスラッシュとしてデコードしない環境があるため、
        # 明示的に unquote してサブフォルダパスを復元する（例: "lab%2FComfyUI_...png" -> "lab/ComfyUI_...png"）
        filename = unquote(str(filename or ""))

        # 先頭のスラッシュ除去・パス正規化
        filename = filename.lstrip("/").replace("\\", "/")
        if ".." in filename:
            abort(404)
        base = COMFYUI_OUTPUT_DIR.resolve()
        # Path で結合して実ファイルパスを取得（Windows で確実に動く）
        target = (base / filename).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            abort(404)
        if not target.is_file():
            abort(404)
        mime, _enc = mimetypes.guess_type(str(target))
        # 画像は基本不変なのでキャッシュを許可（再表示が体感で軽くなる）
        return send_file(
            str(target),
            mimetype=(mime or "application/octet-stream"),
            max_age=86400,
        )

    @app.route("/thumbs/<path:filename>")
    def serve_thumb(filename):
        """サムネイル配信。無ければ生成して返す（既存分の後追い=B）。"""
        from flask import abort
        from urllib.parse import unquote

        # %2F を含む場合もあるので明示的に unquote
        filename = unquote(str(filename or ""))
        filename = filename.lstrip("/").replace("\\", "/")
        if ".." in filename:
            abort(404)

        base = COMFYUI_OUTPUT_DIR.resolve()
        src = (base / filename).resolve()
        try:
            src.relative_to(base)
        except ValueError:
            abort(404)
        if not src.is_file():
            abort(404)

        thumbs_root = (base / THUMBS_DIRNAME).resolve()
        # thumbs 配下にミラーして .jpg で保存
        rel = Path(filename)
        thumb_rel = rel.with_suffix(".jpg")
        thumb = (thumbs_root / thumb_rel).resolve()
        try:
            thumb.relative_to(thumbs_root)
        except ValueError:
            abort(404)

        # 既にサムネがあり、元より新しければそのまま返す
        try:
            if thumb.is_file() and thumb.stat().st_mtime >= src.stat().st_mtime:
                return send_file(str(thumb), mimetype="image/jpeg", max_age=86400)
        except Exception:
            pass

        # 生成（同時生成を避ける）
        key = str(thumb)
        with _THUMB_LOCKS_GUARD:
            lock = _THUMB_LOCKS.get(key)
            if lock is None:
                lock = threading.Lock()
                _THUMB_LOCKS[key] = lock

        with lock:
            try:
                # もう誰かが作っていたら再利用
                if thumb.is_file() and thumb.stat().st_mtime >= src.stat().st_mtime:
                    return send_file(str(thumb), mimetype="image/jpeg", max_age=86400)
            except Exception:
                pass

            try:
                thumb.parent.mkdir(parents=True, exist_ok=True)
                with Image.open(str(src)) as im:
                    im = ImageOps.exif_transpose(im)
                    # JPEG保存のためRGB化
                    if im.mode in ("RGBA", "LA"):
                        bg = Image.new("RGB", im.size, (255, 255, 255))
                        bg.paste(im, mask=im.split()[-1])
                        im = bg
                    elif im.mode != "RGB":
                        im = im.convert("RGB")

                    im.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)
                    im.save(
                        str(thumb),
                        format="JPEG",
                        quality=THUMB_QUALITY,
                        optimize=True,
                        progressive=True,
                    )
            except Exception:
                # サムネ生成に失敗したら元画像へフォールバック
                return send_file(
                    str(src),
                    mimetype=(mimetypes.guess_type(str(src))[0] or "application/octet-stream"),
                    max_age=86400,
                )

        return send_file(str(thumb), mimetype="image/jpeg", max_age=86400)

    def _fill_pending_filenames_on_startup():
        """起動時に output_filenames が空のエントリを ComfyUI 履歴から補完（1回だけ）。"""
        if not GENERATION_METADATA_DB.exists():
            return
        try:
            with open(GENERATION_METADATA_DB, "r", encoding="utf-8") as f:
                gen_meta = json.load(f)
            dirty = False
            filled_count = 0
            for _pid, gen in gen_meta.items():
                if not isinstance(gen, dict):
                    continue
                ofns = gen.get("output_filenames") or []
                pid = (gen.get("prompt_id") or "").strip()
                status = gen.get("status", "")
                # output_filenames が空で prompt_id があるエントリを補完
                if pid and (not ofns or status == "pending_filename_fetch"):
                    fns, path_list = _get_output_from_comfyui_history(pid)
                    if fns and path_list:
                        gen["output_filenames"] = fns
                        gen["output_paths"] = path_list
                        if "status" in gen:
                            del gen["status"]
                        dirty = True
                        filled_count += 1
            if dirty:
                GENERATION_METADATA_DB.parent.mkdir(parents=True, exist_ok=True)
                with open(GENERATION_METADATA_DB, "w", encoding="utf-8") as f:
                    json.dump(gen_meta, f, ensure_ascii=False, indent=2)
                print(f"✅ 未取得ファイル名を補完しました: {filled_count}件")
        except Exception as e:
            print(f"[WARN] 起動時のファイル名補完でエラー: {e}")

    if __name__ == "__main__":
        import socket

        # ファイル名補完は起動をブロックしないようバックグラウンドで実行（UIを先に開く）
        def _run_fill_in_background():
            try:
                import urllib.request

                req = urllib.request.Request(f"{COMFYUI_URL}/system_stats", method="GET")
                urllib.request.urlopen(req, timeout=3)
                _fill_pending_filenames_on_startup()
            except Exception:
                print("[INFO] ComfyUI未接続のため、ファイル名補完はスキップ")

        t = threading.Thread(target=_run_fill_in_background, daemon=True)
        t.start()

        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                return "localhost"

        local_ip = get_local_ip()
        PORT = 9601  # 別のポートを使用

        print("=" * 60)
        print("画像評価Webサーバー起動（ポート9601）")
        print("=" * 60)
        print(f"ローカルアクセス: http://127.0.0.1:{PORT}")
        print(f"外部アクセス（同一Wi-Fi）: http://{local_ip}:{PORT}")
        print(f"Pixel 7からアクセス: http://{local_ip}:{PORT}")
        print("=" * 60)
        print()

        try:
            _p = (_debug_log.read_text() + "\n") if _debug_log.exists() else ""
            _debug_log.write_text(
                _p
                + f"[{__import__('datetime').datetime.now().isoformat()}] calling app.run(port={PORT})\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

else:
    # 既存の評価UIファイルを実行
    print("既存の評価UIを起動します...")
    exec(open(evaluation_web_file).read())
