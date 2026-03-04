#!/usr/bin/env python3
# X280 GUI API Server - Complete Version
from flask import Flask, request, jsonify, send_file
import pyautogui
import tempfile
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Use temp directory to avoid permission issues
TEMP_DIR = Path(tempfile.gettempdir()) / "x280_gui"
TEMP_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR = TEMP_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "screen": list(pyautogui.size()), "screen_size": list(pyautogui.size())})

@app.route("/screenshot", methods=["POST", "GET"])
def screenshot():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ss_{timestamp}.png"
    filepath = SCREENSHOTS_DIR / filename
    
    ss = pyautogui.screenshot()
    ss.save(filepath)
    
    return jsonify({
        "success": True,
        "filename": filename,
        "filepath": str(filepath)
    })

@app.route("/screenshot/download/<filename>")
def download_screenshot(filename):
    filepath = SCREENSHOTS_DIR / filename
    if filepath.exists():
        return send_file(str(filepath), mimetype="image/png")
    return jsonify({"error": "File not found"}), 404

@app.route("/screenshot/latest")
def get_latest():
    screenshots = sorted(SCREENSHOTS_DIR.glob("ss_*.png"), key=os.path.getmtime, reverse=True)
    if screenshots:
        return send_file(str(screenshots[0]), mimetype="image/png")
    return jsonify({"error": "No screenshots"}), 404

@app.route("/mouse/click", methods=["POST"])
def click():
    d = request.json or {}
    if d.get("x") and d.get("y"):
        pyautogui.click(int(d["x"]), int(d["y"]))
    else:
        pyautogui.click()
    return jsonify({"success": True})

@app.route("/keyboard/type", methods=["POST"])
def kbtype():
    pyautogui.write(request.json.get("text", ""), interval=request.json.get("interval", 0.05))
    return jsonify({"success": True})

@app.route("/keyboard/press", methods=["POST"])
def kbpress():
    pyautogui.press(request.json.get("key"))
    return jsonify({"success": True})

@app.route("/keyboard/hotkey", methods=["POST"])
def hotkey():
    pyautogui.hotkey(*request.json.get("keys", []))
    return jsonify({"success": True})

@app.route("/screen/info")
def screen_info():
    pos = pyautogui.position()
    size = pyautogui.size()
    return jsonify({
        "success": True,
        "screen_width": size[0],
        "screen_height": size[1],
        "mouse_x": pos[0],
        "mouse_y": pos[1]
    })

if __name__ == "__main__":
    print("=" * 50)
    print("X280 GUI Server READY on :5009")
    print(f"Screen: {pyautogui.size()}")
    print(f"Screenshots: {SCREENSHOTS_DIR}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5009, debug=os.getenv("DEBUG", "False").lower() == "true")


