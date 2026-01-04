/**
 * Portal UI Components - Unified Portal v2用のUIコンポーネント
 * 実行ボタン・モード切替・コストメーター
 */

// モード切替コンポーネント
function createModeSwitch(currentMode = 'auto') {
    return `
        <div class="mode-switch">
            <label>モード:</label>
            <select id="mode-select" onchange="changeMode(this.value)">
                <option value="work" ${currentMode === 'work' ? 'selected' : ''}>仕事</option>
                <option value="creative" ${currentMode === 'creative' ? 'selected' : ''}>創作</option>
                <option value="fun" ${currentMode === 'fun' ? 'selected' : ''}>ムフフ</option>
                <option value="auto" ${currentMode === 'auto' ? 'selected' : ''}>自動</option>
            </select>
        </div>
    `;
}

// 実行ボタンコンポーネント
function createExecuteButton() {
    return `
        <div class="execute-panel">
            <textarea id="task-input" placeholder="タスクを入力してください..." rows="3"></textarea>
            <button id="execute-btn" onclick="executeTask()" class="execute-button">
                🚀 実行
            </button>
            <div id="execute-status" class="execute-status"></div>
        </div>
    `;
}

// コストメーターコンポーネント
function createCostMeter(costData = null) {
    const todayCost = costData?.today_cost || 0;
    const totalCost = costData?.total_cost || 0;
    const dailyLimit = 1000;
    const usagePercent = Math.min((todayCost / dailyLimit) * 100, 100);
    
    return `
        <div class="cost-meter">
            <h3>💰 コストメーター</h3>
            <div class="cost-today">
                <span>今日: ¥${todayCost.toFixed(2)}</span>
                <div class="cost-bar">
                    <div class="cost-bar-fill" style="width: ${usagePercent}%"></div>
                </div>
                <span>${usagePercent.toFixed(1)}% (上限: ¥${dailyLimit})</span>
            </div>
            <div class="cost-total">
                <span>合計: ¥${totalCost.toFixed(2)}</span>
            </div>
        </div>
    `;
}

// キュー状態コンポーネント
function createQueueStatus(queueData = null) {
    const queueSize = queueData?.queue_size || 0;
    const statusCounts = queueData?.status_counts || {};
    
    return `
        <div class="queue-status">
            <h3>📦 キュー状態</h3>
            <div class="queue-info">
                <div>待機中: ${queueSize}</div>
                <div>実行中: ${statusCounts.running || 0}</div>
                <div>完了: ${statusCounts.completed || 0}</div>
                <div>失敗: ${statusCounts.failed || 0}</div>
            </div>
        </div>
    `;
}

// 実行履歴コンポーネント
function createExecutionHistory(history = []) {
    if (history.length === 0) {
        return '<div class="execution-history">実行履歴がありません</div>';
    }
    
    const historyItems = history.slice(0, 10).map(item => `
        <div class="history-item">
            <div class="history-header">
                <span class="history-id">${item.execution_id}</span>
                <span class="history-status status-${item.status}">${item.status}</span>
            </div>
            <div class="history-content">${item.input_text.substring(0, 100)}...</div>
            <div class="history-meta">
                <span>${item.intent_type}</span>
                <span>${item.duration_seconds ? item.duration_seconds.toFixed(2) + '秒' : ''}</span>
            </div>
        </div>
    `).join('');
    
    return `
        <div class="execution-history">
            <h3>📋 実行履歴</h3>
            ${historyItems}
        </div>
    `;
}

// API呼び出し関数
const API_BASE = 'http://localhost:5108';

async function changeMode(mode) {
    try {
        const response = await fetch(`${API_BASE}/api/mode`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mode})
        });
        const data = await response.json();
        console.log('モード変更:', data);
        updateUI();
    } catch (error) {
        console.error('モード変更エラー:', error);
    }
}

async function executeTask() {
    const input = document.getElementById('task-input').value;
    if (!input.trim()) {
        alert('タスクを入力してください');
        return;
    }
    
    const statusDiv = document.getElementById('execute-status');
    statusDiv.innerHTML = '<div class="loading">実行中...</div>';
    
    try {
        const mode = document.getElementById('mode-select').value;
        const response = await fetch(`${API_BASE}/api/execute`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: input, mode})
        });
        
        const data = await response.json();
        
        if (data.error) {
            statusDiv.innerHTML = `<div class="error">エラー: ${data.error}</div>`;
        } else {
            statusDiv.innerHTML = `
                <div class="success">
                    ✅ 実行完了: ${data.execution_id}<br>
                    ステータス: ${data.status}<br>
                    時間: ${data.duration_seconds ? data.duration_seconds.toFixed(2) + '秒' : ''}
                </div>
            `;
            document.getElementById('task-input').value = '';
            updateUI();
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="error">エラー: ${error.message}</div>`;
    }
}

async function updateUI() {
    // モード取得
    try {
        const modeResponse = await fetch(`${API_BASE}/api/mode`);
        const modeData = await modeResponse.json();
        document.getElementById('mode-select').value = modeData.mode;
    } catch (error) {
        console.error('モード取得エラー:', error);
    }
    
    // コスト取得
    try {
        const costResponse = await fetch(`${API_BASE}/api/cost?days=1`);
        const costData = await costResponse.json();
        const costMeter = document.getElementById('cost-meter');
        if (costMeter) {
            costMeter.innerHTML = createCostMeter(costData);
        }
    } catch (error) {
        console.error('コスト取得エラー:', error);
    }
    
    // キュー状態取得
    try {
        const queueResponse = await fetch(`${API_BASE}/api/queue/status`);
        const queueData = await queueResponse.json();
        const queueStatus = document.getElementById('queue-status');
        if (queueStatus) {
            queueStatus.innerHTML = createQueueStatus(queueData);
        }
    } catch (error) {
        console.error('キュー状態取得エラー:', error);
    }
    
    // 実行履歴取得
    try {
        const historyResponse = await fetch(`${API_BASE}/api/history?limit=10`);
        const historyData = await historyResponse.json();
        const history = document.getElementById('execution-history');
        if (history) {
            history.innerHTML = createExecutionHistory(historyData.results || []);
        }
    } catch (error) {
        console.error('実行履歴取得エラー:', error);
    }
}

// 定期的にUIを更新
setInterval(updateUI, 5000); // 5秒ごと

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    updateUI();
});

