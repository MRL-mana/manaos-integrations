#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像評価Web UI起動スクリプト（ポート9601版）"""

import sys
import os
from pathlib import Path

# Cursor/ログ収集側がUTF-8前提のことが多いので、WindowsでもUTF-8で出す
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 評価UIファイルを確認
evaluation_web_file = Path(__file__).parent / "image_evaluation_web.py"

if not evaluation_web_file.exists():
    print("[WARNING] image_evaluation_web.py が見つかりません")
    print("評価UIファイルを再作成します...")

    # 簡易版の評価UIを作成
    from flask import Flask, render_template_string, jsonify, request, send_from_directory
    import json
    from datetime import datetime

    app = Flask(__name__)

    COMFYUI_OUTPUT_DIR = Path("C:/ComfyUI/output")
    EVALUATION_DB = Path("C:/ComfyUI/input/mana_favorites/evaluation.json")

    # 評価データを読み込み
    evaluations = {}
    if EVALUATION_DB.exists():
        try:
            with open(EVALUATION_DB, "r", encoding="utf-8") as f:
                evaluations = json.load(f)
        except:
            pass

    @app.route("/")
    def index():
        return render_template_string(
            """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>画像評価</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #333; }
        .stats { background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .controls { background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        .controls select, .controls input { padding: 8px; border: 2px solid #ddd; border-radius: 5px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .image-card { background: white; border-radius: 5px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .image-card img { width: 100%; height: auto; border-radius: 5px; cursor: pointer; }
        .score-buttons { display: flex; gap: 5px; margin: 10px 0; }
        .score-btn { flex: 1; padding: 10px; border: 2px solid #ddd; border-radius: 5px; cursor: pointer; background: white; }
        .score-btn.active { background: #667eea; color: white; border-color: #667eea; }
        .comment-input { width: 100%; padding: 8px; border: 2px solid #ddd; border-radius: 5px; margin-top: 5px; }
        .save-btn { width: 100%; padding: 10px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px; display: none; }
        .evaluated-badge { display: inline-block; padding: 5px 10px; background: #4CAF50; color: white; border-radius: 3px; font-size: 12px; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>画像評価</h1>
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
            <button onclick="loadImages(true)" style="padding: 8px 15px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer;">更新</button>
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

        async function loadImages(reset = true) {
            try {
                const filter = document.getElementById('filter-status').value;
                const sort = document.getElementById('sort-order').value;
                const limit = parseInt(document.getElementById('page-limit').value || '100', 10);
                if (reset) pageOffset = 0;

                const url = `/api/images?filter=${encodeURIComponent(filter)}&sort=${encodeURIComponent(sort)}&limit=${limit}&offset=${pageOffset}`;
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const payload = await response.json();

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
                card.setAttribute('data-image-full-path', img.path); // 完全パスも保存

                // 既存の評価済みスコアをcurrentScoreに設定
                if (img.evaluated && img.score) {
                    currentScore[img.path] = img.score;
                }

                card.innerHTML = `
                    <img src="/images/${encodeURIComponent(img.name)}" alt="${img.name}" onclick="openModal('${img.name}')" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22300%22 height=%22300%22%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22%3E画像読み込みエラー%3C/text%3E%3C/svg%3E'">
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
                    </div>
                `;
                grid.appendChild(card);
            });
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
            console.log('setScore called:', imagePath, score);
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
            window.open(`/images/${encodeURIComponent(imgName)}`, '_blank');
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

    @app.route("/api/images")
    def get_images():
        if not COMFYUI_OUTPUT_DIR.exists():
            return jsonify({"total": 0, "items": [], "stats": {}})

        # クエリパラメータを取得
        filter_status = request.args.get("filter", "all")  # all, evaluated, unevaluated, high-score
        sort_order = request.args.get("sort", "newest")  # newest, oldest, score-high, score-low
        limit = int(request.args.get("limit", 200))
        offset = int(request.args.get("offset", 0))

        all_items = []
        for img_file in COMFYUI_OUTPUT_DIR.glob("ComfyUI_*.png"):
            try:
                img_path = str(img_file)
                eval_data = evaluations.get(img_path)
                evaluated = eval_data is not None
                score = eval_data.get("score") if evaluated else None
                comment = eval_data.get("comment", "") if evaluated else ""

                all_items.append(
                    {
                        "name": img_file.name,
                        "path": img_path,
                        "mtime": img_file.stat().st_mtime,
                        "evaluated": evaluated,
                        "score": score,
                        "comment": comment,
                    }
                )
            except Exception as e:
                print(f"画像読み込みエラー: {img_file.name} - {e}")
                continue

        total = len(all_items)

        # 統計を計算
        evaluated_count = sum(1 for x in all_items if x["evaluated"])
        high_score_count = sum(
            1 for x in all_items if x["evaluated"] and x["score"] is not None and x["score"] <= 2
        )

        # フィルタリング
        if filter_status == "evaluated":
            all_items = [x for x in all_items if x["evaluated"]]
        elif filter_status == "unevaluated":
            all_items = [x for x in all_items if not x["evaluated"]]
        elif filter_status == "high-score":
            all_items = [
                x
                for x in all_items
                if x["evaluated"] and x["score"] is not None and x["score"] <= 2
            ]

        # ソート
        if sort_order == "newest":
            all_items.sort(key=lambda x: x["mtime"], reverse=True)
        elif sort_order == "oldest":
            all_items.sort(key=lambda x: x["mtime"])
        elif sort_order == "score-high":
            all_items.sort(
                key=lambda x: (x["score"] if x["score"] is not None else 999, x["mtime"])
            )
        elif sort_order == "score-low":
            all_items.sort(
                key=lambda x: (-(x["score"] if x["score"] is not None else -1), x["mtime"]),
                reverse=False,
            )

        # ページネーション
        filtered_total = len(all_items)
        items = all_items[offset : offset + limit]

        # mtimeを削除（クライアントには不要）
        for item in items:
            item.pop("mtime", None)

        return jsonify(
            {
                "total": total,
                "filtered_total": filtered_total,
                "items": items,
                "stats": {
                    "total": total,
                    "evaluated": evaluated_count,
                    "unevaluated": total - evaluated_count,
                    "high_score": high_score_count,
                },
            }
        )

    @app.route("/api/evaluate", methods=["POST"])
    def evaluate():
        data = request.json
        img_path = data.get("image_path")
        score = data.get("score")
        comment = data.get("comment", "").strip()

        if not img_path or not score:
            return jsonify({"success": False, "error": "画像パスとスコアが必要です"})

        evaluations[img_path] = {
            "score": score,
            "comment": comment,
            "evaluated_at": datetime.now().isoformat(),
        }

        try:
            EVALUATION_DB.parent.mkdir(parents=True, exist_ok=True)
            with open(EVALUATION_DB, "w", encoding="utf-8") as f:
                json.dump(evaluations, f, ensure_ascii=False, indent=2)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    @app.route("/images/<path:filename>")
    def serve_image(filename):
        return send_from_directory(str(COMFYUI_OUTPUT_DIR), filename)

    if __name__ == "__main__":
        import socket

        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except:
                return "localhost"

        local_ip = get_local_ip()
        PORT = 9601  # 別のポートを使用

        print("=" * 60)
        print("画像評価Webサーバー起動（ポート9601）")
        print("=" * 60)
        print(f"ローカルアクセス: http://localhost:{PORT}")
        print(f"外部アクセス（同一Wi-Fi）: http://{local_ip}:{PORT}")
        print(f"Pixel 7からアクセス: http://{local_ip}:{PORT}")
        print("=" * 60)
        print()

        app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

else:
    # 既存の評価UIファイルを実行
    print("既存の評価UIを起動します...")
    exec(open(evaluation_web_file).read())
