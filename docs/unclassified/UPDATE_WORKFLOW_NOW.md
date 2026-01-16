# 🔧 ワークフロー更新手順

## 🎯 修正内容

Browse AIから送られてくるデータ形式に対応するように、ワークフローのコードを修正しました。

**主な変更点**:
1. **トレンドリポジトリの配列形式に対応**
   - `extractedData['トレンドリポジトリ']`を確認
   - 日本語フィールド名（「星の数」「フォーク数」など）に対応
2. **重要度スコアの計算を改善**
   - データが取得できれば10点
   - 100スター以上で追加5点
3. **フォールバック処理を追加**
   - 配列形式でない場合も対応

---

## ✅ 更新手順

### Step 1: n8nを開く

1. **http://localhost:5678 を開く**
2. **Browse AI統合ワークフローを開く**

---

### Step 2: ワークフローを更新

**方法A: 新しいワークフローをインポート（推奨）**

1. **n8nの左メニューから「Workflows」をクリック**
2. **「Import from File」をクリック**
3. **`browse_ai_manaos_integration_fixed.json`を選択**
4. **インポート**

---

**方法B: 既存のワークフローを手動で更新**

1. **「データ整形・重要度判定」ノードを開く**
2. **コードを以下のように置き換え**:

```javascript
const input = $input.first().json.body || $input.first().json;
const robotName = input.robot?.name || input.robotName || 'unknown';
const url = input.capturedAt?.url || input.url || '';
const extractedData = input.extractedData || input.data || {};
const timestamp = input.capturedAt?.timestamp || new Date().toISOString();

let score = 0;
let message = `🔍 **${robotName}** から新しい情報を検出\n\n`;

// トレンドリポジトリの場合
if (robotName.includes('Trending') || robotName.includes('トレンド')) {
  // 配列形式のデータを確認
  const trendingRepos = extractedData['トレンドリポジトリ'] || extractedData.trendingRepos || extractedData.trending || [];
  
  if (trendingRepos.length > 0) {
    score += 10; // データが取得できれば通知
    
    // 最初のリポジトリの情報を取得
    const firstRepo = trendingRepos[0];
    const starCount = firstRepo['星の数'] || firstRepo.stars || firstRepo.starCount || '0';
    
    message += `📈 **トレンド情報**\n`;
    message += `取得数: ${trendingRepos.length}件\n`;
    
    if (firstRepo['リポジトリ']) message += `リポジトリ: ${firstRepo['リポジトリ']}\n`;
    if (firstRepo['説明']) message += `説明: ${firstRepo['説明']}\n`;
    if (starCount) message += `⭐ ${starCount} stars\n`;
    if (firstRepo['プログラミング']) message += `言語: ${firstRepo['プログラミング']}\n`;
    if (firstRepo['フォーク数']) message += `フォーク: ${firstRepo['フォーク数']}\n`;
    
    if (starCount && parseInt(starCount) > 100) score += 5; // 100スター以上で追加ポイント
  } else {
    // 配列形式でない場合のフォールバック
    if (extractedData.stars || extractedData.starCount) score += 5;
    if (extractedData.trending) score += 5;
    
    message += `📈 **トレンド情報**\n`;
    if (extractedData.name) message += `リポジトリ: ${extractedData.name}\n`;
    if (extractedData.stars) message += `⭐ ${extractedData.stars} stars\n`;
    if (extractedData.language) message += `言語: ${extractedData.language}\n`;
  }
}
// セール情報の場合
else if (robotName.includes('Sale') || robotName.includes('セール')) {
  if (extractedData.salePrice || extractedData.discount) score += 10;
  if (extractedData.price && extractedData.originalPrice) score += 8;
  
  message += `💰 **セール情報**\n`;
  if (extractedData.name) message += `商品: ${extractedData.name}\n`;
  if (extractedData.price) message += `価格: ${extractedData.price}\n`;
  if (extractedData.discount) message += `割引: ${extractedData.discount}\n`;
  if (extractedData.link) message += `リンク: ${extractedData.link}\n`;
}
// 競合サイトの場合
else if (robotName.includes('Competitor') || robotName.includes('競合')) {
  if (extractedData.changes || extractedData.diff) score += 8;
  score += 5;
  
  message += `🕵️ **競合サイト変更**\n`;
  message += `URL: ${url}\n`;
  if (extractedData.changes) message += `変更内容: ${JSON.stringify(extractedData.changes)}\n`;
}
// その他の場合
else {
  // データが存在すれば通知
  if (Object.keys(extractedData).length > 0) {
    score += 5;
  }
  message += `📊 **データ取得**\n`;
  message += `URL: ${url}\n`;
  message += `データ: ${JSON.stringify(extractedData).substring(0, 200)}...\n`;
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
    shouldNotify: score >= 5 // 5点以上で通知（トレンドの場合は常に通知）
  }
}];
```

3. **「Save」をクリック**

---

### Step 3: ワークフローを有効化

1. **ワークフローの右上のトグルスイッチをONにする**

---

### Step 4: Browse AIから再実行

1. **Browse AIでロボットを再実行**
2. **n8nの実行履歴を確認**
3. **Slackに通知が届いたか確認**

---

## 🧪 テスト手順

### テスト1: n8nで手動実行

1. **「Browse AI Webhook」ノードをクリック**
2. **「Execute step」をクリック**
3. **各ノードの出力を確認**:
   - データ整形ノード: `importance`が10以上になっているか
   - `shouldNotify`が`true`になっているか

---

### テスト2: Browse AIから再実行

1. **Browse AIでロボットを再実行**
2. **n8nの実行履歴を確認**
3. **Slackに通知が届いたか確認**

---

## 💡 まだ通知が届かない場合

### 一時的にすべての通知を送る（テスト用）

1. **「通知判定」ノードを開く**
2. **条件を変更**:
   ```
   {{ true }}
   ```
   （常にtrueにして、すべての通知を送る）

---

## 🚀 次のステップ

1. **ワークフローを更新**
2. **ワークフローを有効化**
3. **Browse AIから再実行**
4. **Slackに通知が届いたか確認**

---

**ワークフローを更新して、Browse AIから再実行してください！** 🔧

