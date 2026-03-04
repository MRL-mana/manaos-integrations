#!/usr/bin/env python3
"""
GTD Capture Server (port 5130)
- Pixel7 の HTTP Shortcuts からキャプチャを受け取り gtd/inbox/ に保存
- 今日の日次ログを返す morning サマリエンドポイント
- Inbox 状態確認エンドポイント
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("pip install fastapi uvicorn")
    raise

ROOT = Path(__file__).parent
GTD_INBOX   = ROOT / "gtd" / "inbox"
GTD_NA      = ROOT / "gtd" / "next-actions" / "items"
GTD_LOGS    = ROOT / "gtd" / "daily-logs"

for d in [GTD_INBOX, GTD_NA, GTD_LOGS]:
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ManaOS GTD Capture Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CaptureRequest(BaseModel):
    text: str
    type: str = "メモ"        # タスク / アイデア / URL / メモ / その他
    source: str = "pixel7"    # pixel7 / cursor / manual
    note: str = ""


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s\-ぁ-んァ-ン一-龥]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:30] or "capture"


@app.get("/health")
def health():
    return {"status": "ok", "service": "gtd-capture"}


@app.get("/api/gtd/status")
def status():
    items = [f for f in GTD_INBOX.glob("*.md") if f.name != "README.md"]
    na    = [f for f in GTD_NA.glob("*.md") if f.name != "README.md"]
    today = datetime.now().strftime("%Y-%m-%d")
    log   = GTD_LOGS / f"{today}.md"
    return {
        "inbox_count": len(items),
        "next_actions_count": len(na),
        "daily_log_exists": log.exists(),
        "daily_log_path": str(log),
        "date": today,
    }


@app.post("/api/gtd/capture")
def capture(req: CaptureRequest):
    now   = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M")
    slug  = slugify(req.text)
    fname = f"{stamp}_{slug}.md"
    path  = GTD_INBOX / fname

    content = f"""# {req.text}

- キャプチャ日時: {now.strftime('%Y-%m-%d %H:%M')}
- 種類: {req.type}
- ソース: {req.source}

## 内容
{req.text}

## メモ
{req.note}
"""
    path.write_text(content, encoding="utf-8")

    inbox_count = len([f for f in GTD_INBOX.glob("*.md") if f.name != "README.md"])
    return {
        "status": "ok",
        "file": fname,
        "inbox_count": inbox_count,
        "message": f"✅ GTD Inbox に保存しました（残 {inbox_count} 件）",
    }


@app.get("/api/gtd/morning")
def morning_summary():
    today = datetime.now().strftime("%Y-%m-%d")
    log   = GTD_LOGS / f"{today}.md"
    if log.exists():
        text = log.read_text(encoding="utf-8")
    else:
        text = f"# {today} 日次ログ\n（まだ作成されていません）\n\n`gtd_morning_auto.ps1` を実行してください。"

    inbox_count = len([f for f in GTD_INBOX.glob("*.md") if f.name != "README.md"])
    na_count    = len([f for f in GTD_NA.glob("*.md") if f.name != "README.md"])

    # 最初の優先事項セクションだけ抽出（Pixel7 の画面サイズ考慮）
    lines   = text.split("\n")
    summary = []
    in_pri  = False
    for line in lines:
        if "## 今日の3大優先事項" in line:
            in_pri = True
            summary.append(line)
            continue
        if in_pri and line.startswith("## "):
            break
        if in_pri:
            summary.append(line)

    return {
        "date": today,
        "inbox_count": inbox_count,
        "next_actions_count": na_count,
        "priorities_text": "\n".join(summary) if summary else "（優先事項未設定）",
        "full_log_exists": log.exists(),
        "summary": f"📅 {today}\nInbox: {inbox_count}件 / Next: {na_count}件\n\n" + "\n".join(summary[:8]),
    }


@app.get("/api/gtd/morning/text", response_class=PlainTextResponse)
def morning_text():
    """Pixel7 の HTTP Shortcuts dialog 表示用プレーンテキスト"""
    data = morning_summary()
    return data["summary"]


@app.get("/api/gtd/inbox/list")
def inbox_list():
    items = sorted(
        [f for f in GTD_INBOX.glob("*.md") if f.name != "README.md"],
        key=lambda f: f.name,
    )
    return {
        "count": len(items),
        "items": [f.name for f in items[-20:]],  # 最新20件
    }


@app.get("/capture", response_class=PlainTextResponse)
def capture_form():
    """Pixel7 ブラウザ用モバイルキャプチャフォーム"""
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📝 GTD Capture</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: sans-serif; background: #0d1117; color: #e6edf3; padding: 16px; }
h1 { font-size: 20px; margin-bottom: 16px; color: #58a6ff; }
textarea, select, input { width: 100%; padding: 12px; margin-bottom: 12px;
  background: #161b22; color: #e6edf3; border: 1px solid #30363d;
  border-radius: 8px; font-size: 16px; }
textarea { height: 100px; resize: vertical; }
button { width: 100%; padding: 14px; background: #238636; color: #fff;
  border: none; border-radius: 8px; font-size: 18px; font-weight: bold; cursor: pointer; }
button:active { background: #2ea043; }
#result { margin-top: 12px; padding: 12px; border-radius: 8px;
  background: #161b22; border: 1px solid #30363d; display: none; }
.ok { border-color: #238636 !important; color: #3fb950; }
.err { border-color: #da3633 !important; color: #ff7b72; }
</style>
</head>
<body>
<h1>📝 GTD Capture</h1>
<form id="f">
<textarea id="text" placeholder="気になること・タスク・アイデア..." required></textarea>
<select id="type">
  <option value="メモ">📌 メモ</option>
  <option value="タスク">✅ タスク</option>
  <option value="アイデア">💡 アイデア</option>
  <option value="URL">🔗 URL</option>
  <option value="その他">📦 その他</option>
</select>
<textarea id="note" placeholder="補足メモ（省略可）" style="height:60px"></textarea>
<button type="submit">📥 Inbox に保存</button>
</form>
<div id="result"></div>
<script>
document.getElementById('f').onsubmit = async (e) => {
  e.preventDefault();
  const btn = document.querySelector('button');
  btn.textContent = '送信中...'; btn.disabled = true;
  const res = await fetch('/api/gtd/capture', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      text: document.getElementById('text').value,
      type: document.getElementById('type').value,
      source: 'pixel7_browser',
      note: document.getElementById('note').value
    })
  });
  const d = await res.json();
  const el = document.getElementById('result');
  el.style.display = 'block';
  if (res.ok) {
    el.className = 'ok'; el.textContent = d.message;
    document.getElementById('text').value = '';
    document.getElementById('note').value = '';
  } else {
    el.className = 'err'; el.textContent = '❌ エラー: ' + JSON.stringify(d);
  }
  btn.textContent = '📥 Inbox に保存'; btn.disabled = false;
};
</script>
</body>
</html>"""
    return PlainTextResponse(html, media_type="text/html")


@app.get("/morning", response_class=PlainTextResponse)
def morning_page():
    """Pixel7 ブラウザ用モーニングサマリページ"""
    data = morning_summary()
    inbox_warn = ""
    if data["inbox_count"] >= 10:
        inbox_warn = f'<p style="color:#ff7b72">⚠️ Inbox が {data["inbox_count"]} 件溜まっています</p>'
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>🌅 GTD Morning</title>
<style>
body {{ font-family: sans-serif; background: #0d1117; color: #e6edf3; padding: 16px; }}
h1 {{ color: #f0a500; font-size: 20px; margin-bottom: 12px; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 12px; }}
.label {{ color: #8b949e; font-size: 12px; margin-bottom: 4px; }}
pre {{ white-space: pre-wrap; font-family: inherit; font-size: 15px; }}
.badge {{ display: inline-block; background: #238636; color: #fff;
  padding: 2px 8px; border-radius: 12px; font-size: 13px; margin: 2px; }}
.badge.warn {{ background: #b08800; }}
a {{ color: #58a6ff; text-decoration: none; display: block; margin-top: 8px; }}
</style>
</head>
<body>
<h1>🌅 {data["date"]} Morning</h1>
<div class="card">
  <div class="label">統計</div>
  <span class="badge {'warn' if data['inbox_count'] > 0 else ''}">📥 Inbox: {data['inbox_count']}件</span>
  <span class="badge">✅ Next: {data['next_actions_count']}件</span>
  {inbox_warn}
</div>
<div class="card">
  <div class="label">今日の優先事項</div>
  <pre>{data['priorities_text']}</pre>
</div>
<a href="/capture">📝 GTD Capture を開く</a>
<a href="/inbox-list">📋 Inbox 一覧を見る</a>
</body>
</html>"""
    return PlainTextResponse(html, media_type="text/html")


@app.get("/inbox-list", response_class=PlainTextResponse)
def inbox_list_page():
    """Pixel7 ブラウザ用 Inbox 一覧ページ"""
    items = sorted(
        [f for f in GTD_INBOX.glob("*.md") if f.name != "README.md"],
        key=lambda f: f.name, reverse=True
    )
    rows = "".join(
        f'<li style="padding:8px 0;border-bottom:1px solid #30363d">{f.name[:-3]}</li>'
        for f in items[:30]
    ) or '<li style="color:#8b949e">（空です）</li>'
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📋 GTD Inbox</title>
<style>
body {{ font-family: sans-serif; background: #0d1117; color: #e6edf3; padding: 16px; }}
h1 {{ color: #58a6ff; font-size: 20px; margin-bottom: 12px; }}
ul {{ list-style: none; padding: 0; font-size: 14px; }}
a {{ color: #58a6ff; text-decoration: none; display: block; margin-top: 12px; }}
</style>
</head>
<body>
<h1>📋 Inbox（{len(items)}件）</h1>
<ul>{rows}</ul>
<a href="/morning">← Morning に戻る</a>
<a href="/capture">📝 新規キャプチャ</a>
</body>
</html>"""
    return PlainTextResponse(html, media_type="text/html")


@app.get("/download/gtd-shortcuts")
def download_shortcuts():
    """HTTP Shortcuts インポート用 JSON ファイルを配信"""
    f = ROOT / "gtd_pixel7_shortcuts.json"
    if not f.exists():
        raise HTTPException(404, "gtd_pixel7_shortcuts.json not found")
    return FileResponse(str(f), media_type="application/json",
                        filename="gtd_pixel7_shortcuts.json")


@app.get("/import/shortcuts", response_class=PlainTextResponse)
def import_shortcuts_guide():
    """Pixel7 ブラウザでアクセス → HTTP Shortcuts が自動でインポートダイアログを出す"""
    base_url = "http://100.73.247.100:5130"
    dl_url   = f"{base_url}/download/gtd-shortcuts"
    import_url = f"http-shortcuts://import?url={dl_url}"
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GTD Shortcuts Import</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: sans-serif; background: #0d1117; color: #e6edf3; padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }}
h2 {{ color: #58a6ff; margin-bottom: 16px; font-size: 22px; text-align: center; }}
p {{ color: #8b949e; margin-bottom: 24px; text-align: center; font-size: 15px; }}
.btn {{ display: block; width: 100%; max-width: 340px; padding: 20px; background: #238636;
  color: #fff; text-decoration: none; border-radius: 12px; font-size: 22px;
  font-weight: bold; text-align: center; margin-bottom: 16px; }}
.btn-dl {{ display: block; width: 100%; max-width: 340px; padding: 14px;
  background: #161b22; color: #58a6ff; text-decoration: none; border-radius: 12px;
  font-size: 15px; text-align: center; border: 1px solid #30363d; }}
.hint {{ font-size: 12px; color: #6e7681; margin-top: 16px; text-align: center; }}
</style>
</head>
<body>
<h2>📋 GTD Shortcuts インポート</h2>
<p>下のボタンをタップしてください</p>
<a href="{import_url}" class="btn">📥 HTTP Shortcuts で開く</a>
<a href="{dl_url}" class="btn-dl" download="gtd_pixel7_shortcuts.json">⬇️ JSONを直接ダウンロード</a>
<p class="hint">「JSONを直接ダウンロード」後は<br>HTTP Shortcuts → メニュー → Import/Export → Import from File</p>
</body>
</html>"""
    return PlainTextResponse(html, media_type="text/html")


if __name__ == "__main__":
    port = int(os.environ.get("GTD_CAPTURE_PORT", "5130"))
    print(f"GTD Capture Server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
