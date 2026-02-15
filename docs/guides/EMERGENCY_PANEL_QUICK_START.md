# 緊急操作パネル クイックスタートガイド

## 🚀 最短5分で始める

### Step 1: 母艦で統合APIサーバーが起動しているか確認

母艦（このはサーバー）で：

```bash
# 統合APIサーバーが起動しているか確認
curl http://127.0.0.1:9502/health

# 起動していない場合、起動
cd /root/manaos_integrations  # または適切なディレクトリ
python unified_api_server.py
```

### Step 2: X280から接続テスト（Windows）

X280でPowerShellを開いて：

```powershell
# テストスクリプトを実行
cd C:\Users\mana\Desktop\x280_setup  # またはスクリプトがある場所
.\test_emergency_panel.ps1
```

または手動で：

```powershell
# Tailscaleが起動しているか確認
Get-Process -Name "tailscale"

# ブラウザで緊急パネルを開く
Start-Process "http://100.73.247.100:9502/emergency"
```

### Step 3: Android（Pixel 7）で手動テスト

1. Pixel 7でTailscaleアプリを開く
2. 母艦（100.93.120.33）が「接続済み」になっているか確認
3. Chromeで以下を開く：
   ```
   http://100.73.247.100:9502/emergency
   ```

### Step 4: Android自動化設定（MacroDroid推奨）

1. **MacroDroidをインストール**
   - Google Play Storeで「MacroDroid」を検索してインストール

2. **マクロを作成**
   - MacroDroidを開く → 「+」ボタン
   - **トリガー**: 「USB接続」→「USBデバイス接続時」
   - **アクション1**: 「アプリ起動」→「Tailscale」
   - **アクション2**: 「待機」→「3秒」
   - **アクション3**: 「Webページを開く」→ URL: `http://100.73.247.100:9502/emergency`

3. **マクロを有効化**
   - マクロ名: 「緊急パネル起動」
   - 保存して有効化

4. **テスト**
   - USB-CハブをPixel 7に接続
   - 自動的に緊急パネルが開くことを確認

---

## 📋 チェックリスト

- [ ] 母艦の統合APIサーバーが起動中（ポート9500）
- [ ] X280から緊急パネルにアクセス可能
- [ ] Pixel 7でTailscaleが接続済み
- [ ] Pixel 7で手動で緊急パネルにアクセス可能
- [ ] MacroDroid/Taskerで自動化設定完了
- [ ] USB接続時に自動起動を確認

---

## 🔧 トラブルシューティング

### 緊急パネルが開かない

**確認事項**:
1. 母艦の統合APIサーバーが起動しているか
   ```bash
   curl http://127.0.0.1:9502/health
   ```

2. Tailscaleが接続されているか
   - Android端末: Tailscaleアプリで確認
   - X280: `Get-Process -Name "tailscale"`

3. ファイアウォール設定
   - 母艦でポート9500が開いているか確認

### MacroDroid/Taskerが動作しない

**確認事項**:
1. アプリに「アクセシビリティサービス」や「バッテリー最適化除外」の権限を付与
2. マクロ/プロファイルが有効になっているか確認
3. USB接続のトリガー条件を確認（「充電」ではなく「USB接続」を選択）

### 外部モニターに表示されない

**確認事項**:
1. USB-CハブのHDMI出力を確認
2. モニターの入力ソースを確認
3. Pixel 7の開発者オプションで「USB設定のデフォルト」を確認

---

## 📱 使用イメージ

```
[Pixel 7] 
  └─ USB-Cハブ
      ├─ HDMI → [外部モニター] ← 緊急パネル表示
      ├─ USB-A → [キーボード/マウス]
      └─ PD給電
```

**通信経路**:
```
Pixel 7 (LTE/5G) → Tailscale → 母艦 (100.93.120.33:9502)
```

**借りPC側**:
- 画面表示のみ（HDMI経由）
- 入力デバイス（USB経由）
- **ネットワークは一切使用しない**

---

## 🔒 セキュリティ

**借り物PCでの運用ルール**:
- ✅ 画面とキーボードだけ使用
- ✅ Android端末の通信のみ使用
- ❌ 借りPCのネットワークは使用しない
- ❌ 借りPCにアプリをインストールしない
- ❌ 借りPCにファイルを保存しない

---

## 📚 関連ドキュメント

- 詳細設定: `EMERGENCY_PANEL_SETUP.md`
- API仕様: `unified_api_server.py` のコメント
- サーバー設定: `OPERATIONAL_CHECKLIST.md`


