# ManaOS クイックリファレンス

## 🚀 1分で起動

### VSCode/Cursor起動（推奨）
```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: すべてのサービスを起動"
```

### コマンドライン
```powershell
cd C:\Users\mana4\Desktop
.\.venv\Scripts\python.exe manaos_integrations\start_vscode_cursor_services.py
```

## 🔍 ヘルスチェック

### すべてのサービス
```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: サービスヘルスチェック"
```

または

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python check_services_health.py
```

### 個別確認（PowerShell）
```powershell
# Unified API (メインエントリーポイント)
Invoke-RestMethod http://127.0.0.1:9502/health

# MRL Memory
Invoke-RestMethod http://127.0.0.1:5103/health

# Learning System
Invoke-RestMethod http://127.0.0.1:5104/health

# LLM Routing
Invoke-RestMethod http://127.0.0.1:5111/health

# OpenAI Router
Invoke-RestMethod http://127.0.0.1:5211/v1/models
```

## ⚡ サービス一覧

| サービス | ポート | URL |
|---------|--------|-----|
| Unified API | 9502 | http://127.0.0.1:9502 |
| MRL Memory | 5103 | http://127.0.0.1:5103 |
| Learning System | 5104 | http://127.0.0.1:5104 |
| LLM Routing | 5111 | http://127.0.0.1:5111 |
| OpenAI Router | 5211 | http://127.0.0.1:5211/v1 |

## 🎬 LTX-2 / LTX-2 Infinity

### LTX-2 / Infinity 統合テスト
```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python tests\integration\test_ltx2.py
python tests\integration\test_ltx2_infinity_integration.py
```

### Unified API（起動後）
```powershell
# LTX-2
Invoke-RestMethod -Method Post http://127.0.0.1:9502/api/ltx2/generate -ContentType application/json -Body '{"prompt":"a calm sea at sunset"}'

# LTX-2 Infinity（最小：segments=1）
Invoke-RestMethod -Method Post http://127.0.0.1:9502/api/ltx2-infinity/generate -ContentType application/json -Body '{"prompt":"a calm sea at sunset","segments":1}'
```

## 🧪 LoRA 学習用キャプション前処理

### 画像フォルダ → 同名 .txt を自動生成（Ollama Vision）
```powershell
cd C:\Users\mana4\Desktop\manaos_integrations

# dry-run（生成しない）
pwsh -NoProfile -ExecutionPolicy Bypass -File .\run_lora_caption_prep.ps1 -InputDir "D:\\your_dataset" -Model "llava" -DryRun

# 実行（必要なら連番リネーム）
pwsh -NoProfile -ExecutionPolicy Bypass -File .\run_lora_caption_prep.ps1 -InputDir "D:\\your_dataset" -Model "llava" -Trigger "your_token" -Ignore "clothes color, background" -Rename sequential
```

## 🖼️ ComfyUI（Qwen-Image-2512 / i2i + LM Studio 2-pass）

### モデル導入
```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
pwsh -NoProfile -ExecutionPolicy Bypass -File .\install_qwan_image_2512.ps1
```

### LM Studio サーバ起動（必要な場合）
```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
pwsh -NoProfile -ExecutionPolicy Bypass -File .\auto_start_lm_studio_server.ps1
```

### ワークフロー（記事取り込み済み）

| Variant | 用途 | ファイル | 特徴 |
|---------|------|---------|------|
| **A: i2i高品質** | Anima ロ → LM Studio (2x) → Qwen i2i | `05_wQween-2512-Real-Random2.json` | 高精度 LM Studio 2-pass 精密化 |
| **B: アニメ→リアル** | フォルダ一括バッチ → LM Studio → Qwen | `07_Qwen-2512-real-random.json` | Load Image Batch 自動ループ |
| **C: リアル→アニメ** | リアル美女フォルダ → LM Studio (2x) → Anima | `05_wAnima_preview-Random.json` | 逆方向バッチ変換、Anima-preview 出力 |
| **D: Flux→Qwen** | Flux ランダム → LM Studio → Qwen 最終 | `FLUX1_real2.json` + `Qwen-image_2512.json` | 3-stage パイプ (Flux→SD1.5→Qwen) |

#### 推奨組み合わせ
- **高品質実写女性**: Variant A or D (Qwen i2i/最終出力)
- **アニメ大量変換**: Variant B or C (バッチ処理対応)
- **フルカスタマイズ**: Variant D (Flux ランダム → トリミング → 最終化)

## 🛠️ トラブルシューティング


### サービスが応答しない
```powershell
# 30秒待ってから再チェック
Start-Sleep -Seconds 30
python check_services_health.py
```

### ポート競合確認
```powershell
netstat -ano | findstr ":9502"
netstat -ano | findstr ":5103"
netstat -ano | findstr ":5104"
netstat -ano | findstr ":5111"
netstat -ano | findstr ":5211"
```

### 強制停止して再起動
```powershell
# すべてのManaOSプロセスを停止
Get-Process python | Where-Object { $_.CommandLine -like "*manaos*" } | Stop-Process

# 再起動
.\.venv\Scripts\python.exe manaos_integrations\start_vscode_cursor_services.py
```

## 📚 詳細ドキュメント

- **起動ガイド**: [STARTUP_GUIDE.md](STARTUP_GUIDE.md)
- **設定ファイル**: 
  - Cursor: `~/.cursor/mcp.json`
  - VSCode: `~/.vscode/settings.json`

## 🆘 よくある質問

**Q: 起動に時間がかかる**  
A: 初期化に10-30秒かかります。ヘルスチェックは自動でリトライします。

**Q: 一部のサービスだけ起動したい**  
A: 個別タスクを使用:
- "ManaOS: MRLメモリを起動"
- "ManaOS: 学習システムを起動"
- "ManaOS: LLMルーティングを起動"
- "ManaOS: 統合APIを起動"

**Q: 停止方法は？**  
A: 起動ターミナルで `Ctrl+C` を押す

---

**最終更新**: 2026年2月7日
