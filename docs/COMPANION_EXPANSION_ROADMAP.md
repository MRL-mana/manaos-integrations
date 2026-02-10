# ManaOS コンパニオン・拡張ロードマップ

## 実装済み ✅

### Pixel 7 コンパニオン
| 機能 | 説明 |
|------|------|
| PWA manifest | ホーム画面に追加で常設利用 |
| Service Worker | オフライン時ページキャッシュ |
| オフラインバッファ | 未送信メッセージをローカル保存、オンライン復帰時に送信 |
| デバイス状態 | デバイス一覧・母艦リソース取得 |
| クイックアクション | 母艦スリープ、Obsidian保存、n8nワークフロー実行 |
| 人格・system_prompt | 会話に人格プロンプトを注入 |
| Obsidian連携 | 会話をノートとして保存 |
| n8n連携 | ワークフローID指定で実行 |

### 音声
| 機能 | 説明 |
|------|------|
| ホットワード変更 | `VOICE_HOTWORD` で「レミ」以外に変更可能 |

### API
| 機能 | 説明 |
|------|------|
| llm/chat system_prompt | リクエストで system_prompt を渡せる |

---

## 今後実装候補

### コンパニオン（Pixel 7）
| 優先度 | 機能 | 概要 |
|--------|------|------|
| 高 | 通知プッシュ | Firebase Cloud Messaging で母艦→Pixel 7 にプッシュ |
| 高 | マルチモーダル | カメラ撮影画像をLLMに送信（Vision API） |
| 中 | 人格API連携 | Personality System (5123) から自動取得 |
| 中 | 学習最適化 | Learning System と連携してよく使うパターン提案 |
| 低 | n8n ワークフロー一覧 | ドロップダウンで選択して実行 |

### ハードウェア
| 優先度 | 機能 | 概要 |
|--------|------|------|
| 中 | Raspberry Pi 5 | センサー窓口・常時ノード・ダッシュボード専用機 |
| 中 | Android タブレット | Redmi Pad SE 等を常設「目・口・耳」に |
| 低 | マルチウェイクワード | 「レミ」「マナ」など複数トリガー |

### ワークフロー・自動化
| 優先度 | 機能 | 概要 |
|--------|------|------|
| 中 | n8n トリガー | コンパニオン発話をトリガーにワークフロー実行 |
| 中 | Obsidian 検索 | 会話中にノートを検索して参照 |
| 低 | カレンダー連携 | イベント作成・確認 |

### Phase2・記憶
| 優先度 | 機能 | 概要 |
|--------|------|------|
| 中 | Phase2 メモ表示 | テーマ別振り返りメモを会話に表示 |
| 低 | RAG 記憶連携 | 記憶検索結果をコンテキストに注入 |

---

## 設定・環境変数

| 変数 | 説明 | デフォルト |
|------|------|------------|
| `VOICE_HOTWORD` | 音声トリガーワード | レミ |
| `PHASE2_MEMO_INJECT` | 会話にPhase2メモを注入 | off |
| `MANAOS_CORS_ORIGINS` | CORS許可オリジン | localhost:3000,3001 |

---

## 関連ドキュメント

- [PIXEL7_INTEGRATION_GUIDE.md](guides/PIXEL7_INTEGRATION_GUIDE.md)
- [voice_operations.md](voice_operations.md)
- [scripts/voice/README.md](../scripts/voice/README.md)
