# SVI × Wan 2.2 カスタムノードインストール完了

## ✅ インストール完了

### インストール済みカスタムノード

1. ✅ **ComfyUI-VideoHelperSuite** - 動画処理用
   - パス: `C:\ComfyUI\custom_nodes\ComfyUI-VideoHelperSuite`
   - 状態: インストール済み

2. ✅ **ComfyUI-AnimateDiff-Evolved** - 動画生成用
   - パス: `C:\ComfyUI\custom_nodes\ComfyUI-AnimateDiff-Evolved`
   - 状態: インストール済み

3. ⚠️ **ComfyUI-Stable-Video-Diffusion** - SVI統合用
   - 状態: リポジトリが見つかりませんでした
   - 対応: ComfyUI Managerからインストールするか、標準機能として利用可能な可能性があります

---

## 📋 次のステップ

### 1. ComfyUIを起動

```powershell
cd C:\ComfyUI
python main.py --port 8188
```

### 2. ComfyUI Managerで残りのカスタムノードをインストール

1. ブラウザで `http://localhost:8188` にアクセス
2. 「Manager」ボタンをクリック
3. 「Install Missing Custom Nodes」を実行
4. または、「Custom Nodes」タブで「Stable Video Diffusion」を検索してインストール

### 3. 動作確認

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python test_svi_wan22.py
```

---

## 🎯 インストール状況

- ✅ ComfyUI: インストール済み
- ✅ ComfyUI Manager: インストール済み
- ✅ ComfyUI-VideoHelperSuite: インストール済み
- ✅ ComfyUI-AnimateDiff-Evolved: インストール済み
- ⚠️ SVI関連ノード: ComfyUI Managerからインストールが必要

---

## 📝 注意事項

SVI（Stable Video Diffusion）の機能は、ComfyUIの標準機能として組み込まれている可能性があります。または、ComfyUI Managerの「Install Missing Custom Nodes」機能を使用することで、必要なノードが自動的にインストールされる可能性があります。

ComfyUIを起動して、実際にワークフローを作成してみてください。SVI関連のノードが利用可能かどうかを確認できます。

---

*インストール日時: 2025-01-28*











