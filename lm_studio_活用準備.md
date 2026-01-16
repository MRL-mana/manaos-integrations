# LM Studio 活用準備チェックリスト

## ✅ 完了していること

- [x] LM Studioのインストール
- [x] モデルのダウンロード（8個）
- [x] コード統合（`local_llm_helper.py`でLM Studio対応）
- [x] 環境変数設定（`USE_LM_STUDIO=1`）

## ✗ 未完了（要対応）

- [ ] **LM Studioサーバーの起動** ← **最重要**
- [ ] モデルのロード（オプション、JITロードでも可）
- [ ] バックエンドの設定（CPU版に変更が必要な場合）

## 次のステップ

### 1. LM Studioを起動

```
1. LM Studioアプリケーションを起動
2. 「Server」タブを開く
3. 「Start Server」をクリック
4. サーバーが起動するまで待つ
```

### 2. サーバー起動を確認

```powershell
python check_lm_studio_server.py
```

「✓ LM Studioサーバー: 起動中」と表示されればOKです。

### 3. 簡単なテストを実行

```powershell
python test_lm_studio_simple.py
```

「✓ 成功！」と表示されれば、LM Studioが使用可能です。

### 4. LLM修正処理を実行

```powershell
$env:USE_LM_STUDIO="1"
$env:MANA_OCR_USE_LARGE_MODEL="1"
python excel_llm_ultra_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_ULTRA.xlsx --passes 3 --verbose
```

## トラブルシューティング

### サーバーが起動しない場合

1. LM Studioを再起動
2. ポート1234が使用されていないか確認
3. ファイアウォールの設定を確認

### モデルがロードできない場合

1. バックエンドをCPU版に変更（`lm_studio_quick_fix.md`を参照）
2. LM Studioを再起動
3. モデルを再ダウンロード

## 確認コマンド

```powershell
# サーバー起動確認
python check_lm_studio_server.py

# モデルロード確認
python check_lm_studio_loaded.py

# 簡単なテスト
python test_lm_studio_simple.py

# 診断
python diagnose_lm_studio.py
```
