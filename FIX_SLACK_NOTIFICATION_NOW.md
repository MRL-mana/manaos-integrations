# 🔧 Slack通知が届かない問題の即座修正

## 🎯 問題の原因

Browse AIから送られてくるデータの形式が想定と異なる可能性が高いです。

**現在のロボット**: 「トレンドリポジトリリスト」
**データ形式**: 配列形式（9個のリポジトリ）

---

## ✅ 即座に試せる修正

### Step 1: n8nを起動

```powershell
# n8nを起動（ポート5678）
cd manaos_integrations
pwsh -File start_n8n_port5678.ps1
```

または、手動で起動:
```powershell
npx n8n
```

---

### Step 2: n8nのワークフローを確認

1. **http://localhost:5678 を開く**
2. **Browse AI統合ワークフローを開く**
3. **右上のトグルスイッチがONになっているか確認**

---

### Step 3: データ形式を確認

1. **「Browse AI Webhook」ノードをクリック**
2. **「Execute step」をクリック**
3. **出力データを確認**:
   - `body`の中身を確認
   - `extractedData`の構造を確認

**想定されるデータ形式**:
```json
{
  "robot": {
    "name": "トレンドリポジトリリスト"
  },
  "extractedData": {
    "トレンドリポジトリ": [
      {
        "リポジトリ": "...",
        "説明": "...",
        "星の数": "...",
        "フォーク数": "..."
      }
    ]
  }
}
```

---

### Step 4: 重要度スコアの計算を修正

現在のコードは`extractedData.stars`を探していますが、実際のデータは`extractedData.トレンドリポジトリ[0].星の数`のような形式になっている可能性があります。

**修正方法**:
1. **「データ整形・重要度判定」ノードを開く**
2. **コードを修正**:

```javascript
const input = $input.first().json.body || $input.first().json;
const robotName = input.robot?.name || input.robotName || 'unknown';
const url = input.capturedAt?.url || input.url || '';
const extractedData = input.extractedData || input.data || {};
const timestamp = input.capturedAt?.timestamp || new Date().toISOString();

let score = 0;

// トレンドリポジトリの場合
if (robotName.includes('Trending') || robotName.includes('トレンド')) {
  // 配列形式のデータを確認
  const trendingRepos = extractedData['トレンドリポジトリ'] || extractedData.trendingRepos || [];
  if (trendingRepos.length > 0) {
    score += 10; // データが取得できれば通知
  }
  // 星の数を確認（配列の最初の要素から）
  if (trendingRepos.length > 0 && trendingRepos[0]['星の数']) {
    score += 5;
  }
}

// セール情報の場合
if (robotName.includes('Sale') || robotName.includes('セール')) {
  if (extractedData.salePrice || extractedData.discount) score += 10;
  if (extractedData.price && extractedData.originalPrice) score += 8;
}

// 競合サイトの場合
if (robotName.includes('Competitor') || robotName.includes('競合')) {
  if (extractedData.changes || extractedData.diff) score += 8;
  score += 5;
}

let message = `🔍 **${robotName}** から新しい情報を検出\n\n`;

if (robotName.includes('Trending') || robotName.includes('トレンド')) {
  message += `📈 **トレンド情報**\n`;
  const trendingRepos = extractedData['トレンドリポジトリ'] || extractedData.trendingRepos || [];
  if (trendingRepos.length > 0) {
    const firstRepo = trendingRepos[0];
    if (firstRepo['リポジトリ']) message += `リポジトリ: ${firstRepo['リポジトリ']}\n`;
    if (firstRepo['星の数']) message += `⭐ ${firstRepo['星の数']} stars\n`;
    if (firstRepo['プログラミング']) message += `言語: ${firstRepo['プログラミング']}\n`;
  }
  message += `取得数: ${trendingRepos.length}件\n`;
} else if (robotName.includes('Sale')) {
  message += `💰 **セール情報**\n`;
  if (extractedData.name) message += `商品: ${extractedData.name}\n`;
  if (extractedData.price) message += `価格: ${extractedData.price}\n`;
  if (extractedData.discount) message += `割引: ${extractedData.discount}\n`;
  if (extractedData.link) message += `リンク: ${extractedData.link}\n`;
} else if (robotName.includes('Competitor')) {
  message += `🕵️ **競合サイト変更**\n`;
  message += `URL: ${url}\n`;
  if (extractedData.changes) message += `変更内容: ${JSON.stringify(extractedData.changes)}\n`;
}

message += `\n重要度スコア: ${score}/20`;

return [{
  json: {
    robotName,
    url,
    extractedData,
    timestamp,
    importance: score,
    message,
    shouldNotify: score >= 5 // または true にしてすべて通知
  }
}];
```

---

### Step 5: 一時的にすべての通知を送る（テスト用）

**修正方法**:
1. **「通知判定」ノードを開く**
2. **条件を変更**:
   ```
   {{ true }}
   ```
   （常にtrueにして、すべての通知を送る）

これで、重要度スコアに関係なく、すべての通知がSlackに送られます。

---

### Step 6: Browse AIから再実行

1. **Browse AIでロボットを再実行**
2. **n8nの実行履歴を確認**
3. **Slackに通知が届いたか確認**

---

## 🧪 テスト手順

### テスト1: n8nで手動実行

1. **n8nのワークフローを開く**
2. **「Browse AI Webhook」ノードをクリック**
3. **「Execute step」をクリック**
4. **各ノードの出力を確認**

---

### テスト2: Browse AIから再実行

1. **Browse AIでロボットを再実行**
2. **n8nの実行履歴を確認**
3. **Slackに通知が届いたか確認**

---

## 💡 よくある問題と解決策

### 問題1: n8nが起動していない

**解決策**: n8nを起動する

---

### 問題2: ワークフローが有効化されていない

**解決策**: ワークフローの右上のトグルスイッチをONにする

---

### 問題3: データ形式が想定と異なる

**解決策**: 実際のデータ形式を確認して、コードを修正する

---

### 問題4: 重要度スコアが5未満

**解決策**: 一時的に`shouldNotify: true`にして、すべての通知を送る

---

## 🚀 次のステップ

1. **n8nを起動**
2. **ワークフローを確認**
3. **データ形式を確認**
4. **必要に応じてコードを修正**
5. **Browse AIから再実行**

---

**まずはn8nを起動して、ワークフローを確認してください！** 🔍

