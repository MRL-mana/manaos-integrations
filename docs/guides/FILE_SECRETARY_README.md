# File Secretary システム

**「もう一人のマナ」のファイル秘書機能**

Slackで会話しながら、INBOXに入れたファイルを自動的に把握・整理するシステムです。

---

## ✨ 特徴

- ✅ **ぶち込み前提**: 保存先を考えなくていい
- ✅ **急かさない**: マナが「終わった」と言うまで何もしない
- ✅ **削除しない**: ファイルは動かさず、メタデータで管理
- ✅ **戻せる**: いつでも復元可能

---

## 🚀 クイックスタート

### Windows環境

```powershell
.\file_secretary_quick_start.ps1
```

### Linux/Mac環境

```bash
chmod +x file_secretary_quick_start.sh
./file_secretary_quick_start.sh
```

---

## 💬 Slackコマンド

- `Inboxどう？` - INBOX状況確認
- `終わった` - ファイル整理実行
- `戻して` - ファイル復元
- `探して：◯◯` - ファイル検索

---

## 📁 ディレクトリ構造

```
manaos_integrations/
├── file_secretary_*.py          # コア実装（11ファイル）
├── file_secretary_*.sh/.ps1     # 起動スクリプト
├── file_secretary.db            # SQLiteデータベース
├── 00_INBOX/                    # INBOXディレクトリ
├── ocr_texts/                   # OCRテキスト保存先
└── FILE_SECRETARY_*.md          # ドキュメント
```

---

## 📚 ドキュメント

- `FILE_SECRETARY_OPERATION_GUIDE.md` - 運用ガイド（**まずこれを読む**）
- `FILE_SECRETARY_DESIGN.md` - 実装設計書
- `FILE_SECRETARY_SETUP.md` - セットアップガイド
- `FILE_SECRETARY_COMPLETE.md` - 完全実装完了ドキュメント

---

## 🎯 完成条件

- ✅ Slackで会話できる
- ✅ INBOXに入れたファイルを把握できる
- ✅ 「終わった」で整理が走る
- ✅ 勝手に削除しない / 急かさない / 戻せる

**すべて達成！** 🎉

---

## 📊 実装状況

- **Phase1（基本機能）**: ✅ 100%動作確認済み
- **Phase2（拡張機能）**: ✅ 実装完了（OCR動作確認済み）
- **Phase3（事務・販促）**: ✅ 実装完了

---

## 🔧 トラブルシューティング

詳細は `FILE_SECRETARY_OPERATION_GUIDE.md` を参照してください。

---

**File Secretary - 「もう一人のマナ」のファイル秘書機能**






















