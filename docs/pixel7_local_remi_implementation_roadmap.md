# 🚀 Pixel 7 × ローカルレミ 実装ロードマップ

**作成日**: 2026年2月9日  
**親ドキュメント**: [コンパニオンAI構想](./pixel7_local_remi_companion_design.md)

---

## 📋 実装優先度マトリクス

| フェーズ | 期間目安 | 必須度 | 技術難易度 |
|---------|---------|--------|----------|
| フェーズ1 | 1-2日 | ★★★★★ | ⭐⭐ |
| フェーズ2 | 3-5日 | ★★★★ | ⭐⭐⭐ |
| フェーズ3 | 1週間 | ★★★ | ⭐⭐⭐⭐ |
| フェーズ4 | 2-3週間 | ★★ | ⭐⭐⭐⭐⭐ |

---

## 🟢 フェーズ1：しゃべるレミ（最優先）

### 目標
**「話しかけたら音声で返ってくる」を達成**

### ✅ 完了条件
- [ ] Pixel 7からレミと会話できる
- [ ] テキスト返答が音声で聞こえる
- [ ] LAN内でアクセス可能

### 🔧 実装タスク

#### 1. Open WebUI セットアップ（母艦）

```bash
# Docker Composeで起動
cd ~/manaos_integrations
docker-compose -f docker-compose.openwebui.yml up -d
```

**必要な作業**:
- [ ] `docker-compose.openwebui.yml` 作成
- [ ] Ollama連携設定
- [ ] ポート8080で公開（LAN内のみ）
- [ ] 初回アクセス・アカウント作成

#### 2. LAN内アクセス設定

```bash
# 母艦のIPアドレス確認
ipconfig | findstr "IPv4"

# Windowsファイアウォール設定
netsh advfirewall firewall add rule name="Open WebUI" dir=in action=allow protocol=TCP localport=8080
```

**必要な作業**:
- [ ] 母艦のローカルIP固定化（ルーター設定）
- [ ] ファイアウォールルール追加
- [ ] Pixel 7からアクセステスト

#### 3. PWA化（Pixel 7）

**手順**:
1. Pixel 7で Chrome起動
2. `http://[母艦IP]:8080` にアクセス
3. メニュー → 「ホーム画面に追加」
4. アイコン名を「レミ」に変更

**必要な作業**:
- [ ] PWAマニフェスト調整（アイコン・名前）
- [ ] Pixel 7ホーム画面配置

#### 4. 音声読み上げ実装（Pixel 7側）

**方式A: JavaScript Web Speech API（推奨）**

```javascript
// Open WebUI のカスタムCSS/JSに追加
function speakResponse(text) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'ja-JP';
  utterance.rate = 1.1; // 少し速め
  window.speechSynthesis.speak(utterance);
}

// レスポンス受信時に自動実行
document.addEventListener('新メッセージ', (e) => {
  speakResponse(e.detail.text);
});
```

**方式B: Android TTS API（ネイティブアプリ化時）**

後回し。まずは方式Aで実装。

**必要な作業**:
- [ ] Web Speech API統合コード作成
- [ ] 自動読み上げ設定
- [ ] 音声ON/OFFトグル実装

---

## 🟢 フェーズ2：状態が見える

### 目標
**「レミが何してるか」が常に分かる状態**

### ✅ 完了条件
- [ ] GPU使用率がリアルタイムで見える
- [ ] 実行中のタスクが表示される
- [ ] 学習進捗が分かる

### 🔧 実装タスク

#### 1. ステータスAPI作成（母艦）

```python
# manaos_integrations/local_remi_api.py

from fastapi import FastAPI
import psutil
import GPUtil

app = FastAPI()

@app.get("/status")
async def get_status():
    gpus = GPUtil.getGPUs()
    return {
        "gpu": {
            "usage": gpus[0].load * 100,
            "memory": gpus[0].memoryUsed,
            "temp": gpus[0].temperature
        },
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "tasks": get_running_tasks()
    }

@app.get("/tasks")
async def get_running_tasks():
    # ComfyUI、学習中タスクなどを取得
    return {
        "comfyui_queue": check_comfyui_queue(),
        "training": check_training_status(),
        "idle": is_system_idle()
    }
```

**必要な作業**:
- [ ] FastAPI サーバー実装
- [ ] GPU監視機能
- [ ] タスク検出ロジック
- [ ] ポート5000で公開

#### 2. ダッシュボードUI追加

**Open WebUI拡張 or 独立ページ**

```html
<!-- status_dashboard.html -->
<div id="remi-status">
  <div class="gpu-indicator">
    <span>GPU: <span id="gpu-usage">--</span>%</span>
    <div class="gpu-bar"></div>
  </div>
  <div class="task-list">
    <h3>実行中</h3>
    <ul id="tasks"></ul>
  </div>
</div>

<script>
setInterval(async () => {
  const status = await fetch('http://[母艦IP]:5000/status').then(r => r.json());
  document.getElementById('gpu-usage').textContent = status.gpu.usage.toFixed(1);
  // タスク表示更新
}, 2000);
</script>
```

**必要な作業**:
- [ ] リアルタイム更新UI実装
- [ ] Open WebUIへの組み込み
- [ ] レスポンシブデザイン調整

---

## 🟢 フェーズ3：ワンタップ操作

### 目標
**「指示すら面倒」を解消**

### ✅ 完了条件
- [ ] よく使う操作がボタン1タップ
- [ ] 音声コマンドで実行可能
- [ ] 実行結果が通知で届く

### 🔧 実装タスク

#### 1. クイックアクションボタン

**UI設計**:
```
+-----------------------+
| [画像生成]  [学習開始] |
| [GPU確認]  [ログ確認] |
| [生成停止]  [再起動]  |
+-----------------------+
```

**API実装**:
```python
@app.post("/actions/{action_name}")
async def execute_action(action_name: str, params: dict):
    actions = {
        "generate_image": start_comfyui_generation,
        "start_training": start_lora_training,
        "check_gpu": get_gpu_status,
        "stop_all": stop_all_tasks
    }
    
    if action_name not in actions:
        raise HTTPException(404)
    
    result = await actions[action_name](params)
    return {"status": "success", "result": result}
```

**必要な作業**:
- [ ] アクションホワイトリスト定義
- [ ] 各アクション実装
- [ ] UIボタン配置
- [ ] 実行ログ記録

#### 2. 音声コマンド対応

```javascript
// 音声認識 → アクション実行
const recognition = new webkitSpeechRecognition();
recognition.lang = 'ja-JP';
recognition.continuous = true;

recognition.onresult = (event) => {
  const command = event.results[event.results.length - 1][0].transcript;
  
  if (command.includes('画像生成')) {
    executeAction('generate_image');
  } else if (command.includes('GPU確認')) {
    executeAction('check_gpu');
  }
};
```

**必要な作業**:
- [ ] 音声認識統合
- [ ] コマンドマッピング定義
- [ ] 認識精度テスト

---

## 🟢 フェーズ4：完全コンパニオン

### 目標
**「レミが常にそこにいる感覚」**

### ✅ 完了条件
- [ ] キャラクター音声（VOICEVOX）
- [ ] Androidウィジェット化
- [ ] プッシュ通知
- [ ] 自発的な提案機能

### 🔧 実装タスク

#### 1. VOICEVOX統合

```python
# voice_service.py
import requests
import base64

def generate_voice(text: str, speaker_id: int = 1):
    # VOICEVOX API呼び出し
    query = requests.post(
        'http://localhost:50021/audio_query',
        params={'text': text, 'speaker': speaker_id}
    ).json()
    
    audio = requests.post(
        'http://localhost:50021/synthesis',
        params={'speaker': speaker_id},
        json=query
    ).content
    
    return base64.b64encode(audio).decode()
```

**必要な作業**:
- [ ] VOICEVOX Docker化
- [ ] 音声生成API実装
- [ ] キャラクター調整
- [ ] Pixel 7での再生テスト

#### 2. Androidウィジェット

**技術選択**:
- **簡易版**: PWAショートカット（今すぐ可能）
- **本格版**: Flutter/React Native（時間かかる）

**必要な作業**:
- [ ] ウィジェット設計
- [ ] 実装（後回し推奨）

#### 3. プッシュ通知

```python
# notification_service.py
from firebase_admin import messaging

def notify_pixel(title: str, body: str):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token='[Pixel 7のFCMトークン]'
    )
    messaging.send(message)

# 使用例
notify_pixel(
    title="GPU空いたよ",
    body="画像生成できます"
)
```

**必要な作業**:
- [ ] Firebase設定
- [ ] プッシュ通知実装
- [ ] 通知トリガー設計

---

## 🔒 セキュリティ実装（全フェーズ共通）

### 必須対策

#### 1. APIトークン認証

```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/status")
async def get_status(token: str = Security(security)):
    if token.credentials != os.getenv("REMI_API_TOKEN"):
        raise HTTPException(403, "Invalid token")
    # ...
```

**必要な作業**:
- [ ] トークン生成・管理
- [ ] 全エンドポイントに認証追加
- [ ] トークンローテーション機能

#### 2. ホワイトリスト方式

```python
ALLOWED_COMMANDS = [
    "comfyui_generate",
    "check_gpu",
    "list_models",
    "get_logs"
]

@app.post("/run/{command}")
async def run_command(command: str):
    if command not in ALLOWED_COMMANDS:
        raise HTTPException(403, "Command not allowed")
    # ...
```

#### 3. ログ記録

```python
import logging

logging.basicConfig(
    filename='remi_api_audit.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

@app.middleware("http")
async def log_requests(request, call_next):
    logging.info(f"{request.client.host} - {request.method} {request.url.path}")
    response = await call_next(request)
    return response
```

---

## 📦 必要な技術スタック

### 母艦（Windows）
- Python 3.11+
- FastAPI
- Docker Desktop
- Open WebUI
- Ollama
- VOICEVOX（フェーズ4）

### Pixel 7（Android）
- Chrome（PWA対応）
- Firebase Cloud Messaging（フェーズ4）

### ネットワーク
- Tailscale（外出先アクセス用・オプション）
- ローカルIP固定設定

---

## 🎯 今日やるべきこと（最優先）

### ステップ1: 環境確認
```powershell
# Docker起動確認
docker --version
docker ps

# Ollama起動確認
ollama list
```

### ステップ2: Open WebUI起動
```bash
docker run -d -p 8080:8080 -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main
```

### ステップ3: Pixel 7からアクセス
1. 母艦のIPアドレス確認: `ipconfig`
2. Pixel 7で `http://[IP]:8080` を開く
3. PWA化（ホーム画面追加）

---

## 📝 次回以降の課題

- [ ] Tailscale設定（外出先アクセス）
- [ ] 音声コマンドのカスタマイズ
- [ ] 自発的な提案機能（AI判断）
- [ ] バッテリー最適化
- [ ] オフライン対応

---

**このロードマップは進捗に応じて更新されます。**  
**迷ったら「フェーズ1完成」を最優先。**
