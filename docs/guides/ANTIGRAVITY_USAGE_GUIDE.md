# 🛠️ Antigravity × ManaOS 使い方ガイド

**最終更新**: 2026-01-06  
**目的**: Antigravityの起動方法とManaOS統合

---

## 🎯 Antigravityの位置づけ

> **Antigravity = 知識加工工場**  
> **Cursorより軽い。ローカルLLMより速い。ManaOSより"即席"。**

**役割**: まとめ・再構築・軽作業専用  
**起動タイミング**: **必要なときだけ起動**（常時起動不要）

---

## 🚀 起動方法

### 方法1: Webアプリとして起動（推奨）

1. **Antigravityを開く**
   - ブラウザでAntigravityのURLにアクセス
   - または、デスクトップアプリを起動

2. **必要なときだけ起動**
   - MOC再構築が必要なとき
   - 記事化が必要なとき
   - YAML一括編集が必要なとき

3. **作業完了後は閉じる**
   - 常時起動不要
   - リソースを節約

---

### 方法2: コマンドラインから起動（オプション）

```bash
# Antigravityがコマンドライン対応している場合
antigravity start
```

---

## 📋 使い方フロー

### STEP 1: 作業が必要になったら起動

```
【アウトプット時】
関連ノートを複数選択
  ↓
Antigravityを起動（このタイミング）
  ↓
プロンプトを選択
  ↓
ノートを貼り付け
  ↓
実行
  ↓
結果をObsidianに保存
  ↓
Antigravityを閉じる
```

---

### STEP 2: プロンプトを選択

`antigravity_prompts.md` から適切なプロンプトを選択：

- **MOC再構築**: 基本MOC作成 or テーマ別MOC作成
- **記事化**: 学習ログ → 記事化 or 振り返り → 記事化
- **YAML編集**: タグの追加 or メタデータの追加

---

### STEP 3: ノートを貼り付け

1. **Obsidianでノートを選択**
   - 関連するノートを複数選択
   - 内容をコピー

2. **Antigravityに貼り付け**
   - プロンプトの「【ノート】」セクションに貼り付け
   - 実行

---

### STEP 4: 結果を保存

```python
from manaos_obsidian_integration import ObsidianNotebookLMAntigravityIntegration

integration = ObsidianNotebookLMAntigravityIntegration()

# MOCとして保存
integration.save_antigravity_result(
    content="再構築されたMOC内容",
    title="テーマ名",
    output_type="moc"
)

# 記事として保存
integration.save_antigravity_result(
    content="再構築された記事内容",
    title="記事タイトル",
    output_type="article"
)
```

---

## ⚡ 起動タイミングの判断基準

### ✅ 起動すべきとき

- **MOCを作りたいとき**
  - 関連ノートが5個以上たまった
  - テーマが明確になってきた

- **記事化したいとき**
  - 学習ログが一定量たまった
  - 振り返りをまとめたい
  - 思考メモを整理したい

- **YAML編集したいとき**
  - 複数ノートのタグを一括追加
  - メタデータを一括編集

### ❌ 起動不要なとき

- **毎日の記録時**（Obsidianで十分）
- **週次分析時**（NotebookLMで十分）
- **常時監視**（ManaOSが担当）

---

## 🔧 ManaOS統合

### 自動化ワークフロー（n8n）

Antigravityは**手動起動**が基本ですが、以下の場合は自動化も可能：

```json
{
  "name": "Antigravity自動実行（月次）",
  "trigger": "毎月1日",
  "action": [
    "関連ノートを自動選択",
    "Antigravity APIに送信（または手動実行）",
    "結果をObsidianに保存",
    "ManaOSの記憶システムに登録"
  ]
}
```

**注意**: Antigravity APIが利用可能な場合のみ自動化可能

---

## 📊 リソース使用量

### Antigravity vs 他のツール

| ツール | 常時起動 | リソース使用量 | 起動タイミング |
|--------|---------|--------------|--------------|
| **Antigravity** | ❌ 不要 | 低（必要なときだけ） | アウトプット時 |
| **NotebookLM** | ❌ 不要 | 中（週1回） | 週次分析時 |
| **Obsidian** | ✅ 推奨 | 低（常時起動OK） | 常時 |
| **ManaOS** | ✅ 必須 | 中（常時起動） | 常時 |
| **ローカルLLM** | ✅ 推奨 | 高（常時起動） | 常時 |

---

## 🎯 推奨設定

### 起動方法

1. **Antigravityは必要なときだけ起動**
   - デスクトップショートカットを作成
   - または、ブラウザのブックマークに追加

2. **Obsidianから直接起動（オプション）**
   - Obsidianのコマンドパレットから起動
   - または、プラグインで統合

---

## 📝 実践例

### 例1: MOCを作りたいとき

```
1. Obsidianで関連ノートを5個選択
2. Antigravityを起動
3. 「MOC再構築（基本）」プロンプトを選択
4. ノートを貼り付け
5. 実行
6. 結果を MOCs/テーマ名-MOC.md に保存
7. Antigravityを閉じる
```

### 例2: 記事化したいとき

```
1. 学習ログが10個以上たまった
2. Antigravityを起動
3. 「学習ログ → 記事化」プロンプトを選択
4. ノートを貼り付け
5. 実行
6. 結果を Articles/YYYY-MM-DD-記事名.md に保存
7. Antigravityを閉じる
```

---

## 🔄 完全フロー（再掲）

```
【毎日】
Obsidianで記録（常時起動OK）
  ↓
Daily/YYYY-MM-DD.md

【週1回】
NotebookLMで分析（必要なときだけ起動）
  ↓
Review/YYYY-MM-DD-notebooklm-result.md

【アウトプット時】
Antigravityで再構築（必要なときだけ起動）
  ↓
MOCs/テーマ名-MOC.md
または
Articles/YYYY-MM-DD-記事名.md

【常時】
ManaOSが記憶・統合（常時起動）
  ↓
自動化・収益化
```

---

## 🎯 まとめ

### ✅ Antigravityの起動方針

- **必要なときだけ起動**
- **作業完了後は閉じる**
- **常時起動不要**

### 📌 起動タイミング

- MOCを作りたいとき
- 記事化したいとき
- YAML一括編集したいとき

### 🔧 統合方法

- **手動起動**が基本
- **n8n自動化**はオプション（API利用可能な場合）
- **ManaOS統合**で結果を自動保存

---

**Antigravityは「知識加工工場」。必要なときだけ起動して、作業完了後は閉じる。**

**全部使う。役割を混ぜない。完璧を目指さない。**

---




















