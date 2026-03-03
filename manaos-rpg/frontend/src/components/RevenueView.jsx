import { useState } from 'react'
import { fetchJson } from '../api.js'
import Box from './Box.jsx'
import Sparkline from './Sparkline.jsx'

/**
 * RevenueView — 収益KPIダッシュボード
 *
 * image_generation_service の billing/quality/RL を統合表示。
 * RPGコマンド画面の「収益」タブとして機能する。
 */
export default function RevenueView() {
  const [kpi, setKpi] = useState(null)
  const [history, setHistory] = useState(null)
  const [alerts, setAlerts] = useState(null)
  const [anomaly, setAnomaly] = useState(null)
  const [tuneResult, setTuneResult] = useState(null)
  const [tuning, setTuning] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function fetchAll() {
    setLoading(true)
    setError('')
    try {
      const [kpiData, histData, alertData, anomalyData] = await Promise.all([
        fetchJson('/api/revenue/kpi'),
        fetchJson('/api/revenue/history?days=30'),
        fetchJson('/api/revenue/alert-check'),
        fetchJson('/api/revenue/anomaly?days=30'),
      ])
      setKpi(kpiData)
      setHistory(histData)
      setAlerts(alertData)
      setAnomaly(anomalyData)
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  async function runAutoTune(apply = false) {
    setTuning(true)
    try {
      const data = await fetchJson(
        `/api/revenue/auto-tune?days=30&apply=${apply}`,
        { method: 'POST' },
      )
      setTuneResult(data)
      if (apply && !data.error) {
        // 適用後は全データを再取得
        await fetchAll()
      }
    } catch (e) {
      setTuneResult({ status: 'error', error: String(e?.message || e) })
    } finally {
      setTuning(false)
    }
  }

  const billing = kpi?.billing || {}
  const quality = kpi?.quality || {}
  const rl = kpi?.rl || {}
  const health = kpi?.loop_health || {}
  const breakdown = health.breakdown || {}

  const levelColors = {
    critical: '#ef4444',
    building: '#f59e0b',
    growing: '#22c55e',
    thriving: '#06b6d4',
  }

  const levelLabels = {
    critical: '🔴 CRITICAL',
    building: '🟡 BUILDING',
    growing: '🟢 GROWING',
    thriving: '💎 THRIVING',
  }

  return (
    <div>
      <h2>💰 収益 KPI ダッシュボード</h2>
      <div style={{ marginBottom: '1rem' }}>
        <button onClick={fetchAll} disabled={loading}>
          {loading ? '読み込み中…' : '📊 全データ取得'}
        </button>
      </div>

      {error && <div className="err">{error}</div>}

      {kpi && (
        <>
          {/* Loop Health Score */}
          <Box title="ループ健全性">
            <div style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
              <span style={{
                fontSize: '3rem',
                fontWeight: 'bold',
                color: levelColors[health.level] || '#888',
              }}>
                {health.score ?? 0}
              </span>
              <span style={{ fontSize: '1.2rem', marginLeft: '0.25rem' }}>/100</span>
            </div>
            <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
              <span style={{
                padding: '0.25rem 0.75rem',
                borderRadius: '4px',
                background: levelColors[health.level] || '#888',
                color: '#000',
                fontWeight: 'bold',
              }}>
                {levelLabels[health.level] || health.level}
              </span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                {[
                  ['💰 Revenue', breakdown.revenue, 20],
                  ['👥 Users', breakdown.users, 20],
                  ['📝 Feedback', breakdown.feedback, 20],
                  ['🎯 RL Success', breakdown.rl_success, 20],
                  ['🧠 RL Learning', breakdown.rl_learning, 20],
                ].map(([label, val, max]) => (
                  <tr key={label}>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{label}</td>
                    <td style={{ padding: '0.25rem 0.5rem', width: '60%' }}>
                      <div style={{
                        background: '#333',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        height: '16px',
                      }}>
                        <div style={{
                          width: `${((val || 0) / max) * 100}%`,
                          background: (val || 0) >= max * 0.7 ? '#22c55e' : (val || 0) >= max * 0.3 ? '#f59e0b' : '#ef4444',
                          height: '100%',
                          transition: 'width 0.3s',
                        }} />
                      </div>
                    </td>
                    <td style={{ padding: '0.25rem 0.5rem', textAlign: 'right', fontFamily: 'monospace' }}>
                      {(val ?? 0).toFixed(1)}/{max}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Box>

          {/* Billing KPI */}
          <Box title="売上指標">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
              <KpiCard label="MRR" value={`¥${(billing.mrr_yen ?? 0).toLocaleString()}`} sub="月次経常収益" />
              <KpiCard label="日次売上" value={`¥${(billing.daily_sales_yen ?? 0).toFixed(2)}`} sub="本日のGPUコスト" />
              <KpiCard label="アクティブユーザー" value={billing.active_users_30d ?? 0} sub="過去30日" />
              <KpiCard label="API Key数" value={billing.active_keys ?? 0} sub="有効キー" />
            </div>
          </Box>

          {/* Quality */}
          <Box title="品質指標">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
              <KpiCard
                label="平均評価"
                value={quality.avg_rating != null ? `${quality.avg_rating.toFixed(1)} / 5.0` : '—'}
                sub="ユーザーフィードバック"
              />
              <KpiCard
                label="FB件数"
                value={quality.total_feedback ?? 0}
                sub="過去7日"
              />
            </div>
          </Box>

          {/* RL Anything */}
          <Box title="RL 学習指標">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
              <KpiCard
                label="状態"
                value={rl.enabled ? '🟢 Active' : '⚪ Inactive'}
                sub="RLAnything"
              />
              <KpiCard
                label="成功率"
                value={rl.success_rate != null ? `${(rl.success_rate * 100).toFixed(1)}%` : '—'}
                sub="タスク成功率"
              />
              <KpiCard
                label="平均スコア"
                value={rl.avg_score != null ? rl.avg_score.toFixed(3) : '—'}
                sub="品質スコア"
              />
              <KpiCard
                label="学習サイクル"
                value={rl.total_cycles ?? 0}
                sub={`スキル: ${rl.skills_count ?? 0}`}
              />
            </div>
          </Box>

          {kpi.status === 'degraded' && (
            <div className="err" style={{ marginTop: '1rem' }}>
              ⚠ image_generation_service に接続できません: {kpi.error}
            </div>
          )}
        </>
      )}

      {/* Revenue Trend Chart */}
      {history && history.days && history.days.length > 0 && (
        <Box title="📈 収益推移（日次）">
          <div style={{ marginBottom: '0.5rem' }}>
            <Sparkline
              data={history.days.map(d => d.revenue)}
              width={400}
              height={80}
              color="#22c55e"
              label="収益"
            />
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #444' }}>
                <th style={{ textAlign: 'left', padding: '4px' }}>日付</th>
                <th style={{ textAlign: 'right', padding: '4px' }}>収益</th>
                <th style={{ textAlign: 'right', padding: '4px' }}>コスト</th>
                <th style={{ textAlign: 'right', padding: '4px' }}>利益</th>
                <th style={{ textAlign: 'right', padding: '4px' }}>生成数</th>
              </tr>
            </thead>
            <tbody>
              {history.days.slice(-7).reverse().map(d => (
                <tr key={d.date} style={{ borderBottom: '1px solid #333' }}>
                  <td style={{ padding: '4px' }}>{d.date}</td>
                  <td style={{ textAlign: 'right', padding: '4px', color: '#22c55e' }}>
                    ¥{d.revenue.toLocaleString()}
                  </td>
                  <td style={{ textAlign: 'right', padding: '4px', color: '#ef4444' }}>
                    ¥{d.cost.toFixed(2)}
                  </td>
                  <td style={{ textAlign: 'right', padding: '4px',
                    color: d.profit >= 0 ? '#22c55e' : '#ef4444' }}>
                    ¥{d.profit.toLocaleString()}
                  </td>
                  <td style={{ textAlign: 'right', padding: '4px' }}>{d.products}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {history.summary && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#888' }}>
              {history.summary.period_days}日合計: 収益 ¥{(history.summary.total_revenue ?? 0).toLocaleString()}
              {' / '}コスト ¥{(history.summary.total_cost ?? 0).toFixed(2)}
              {' / '}利益率 {history.summary.margin_pct ?? 0}%
            </div>
          )}
        </Box>
      )}

      {history && history.days && history.days.length === 0 && (
        <Box title="📈 収益推移">
          <div style={{ color: '#888', textAlign: 'center', padding: '1rem' }}>
            まだデータがありません。画像生成が行われると自動的に記録されます。
          </div>
        </Box>
      )}

      {/* Alerts Panel */}
      {alerts && alerts.alerts && alerts.alerts.length > 0 && (
        <Box title="🚨 アラート">
          {alerts.alerts.map((a, i) => (
            <div key={i} style={{
              padding: '0.5rem',
              marginBottom: '0.5rem',
              borderRadius: '4px',
              background: a.severity === 'critical' ? '#4a1a1a' : '#4a3a1a',
              borderLeft: `3px solid ${a.severity === 'critical' ? '#ef4444' : '#f59e0b'}`,
            }}>
              <span style={{ fontWeight: 'bold' }}>
                {a.severity === 'critical' ? '🔴' : '🟡'} {a.dimension}
              </span>
              <span style={{ marginLeft: '0.5rem', fontSize: '0.85rem' }}>{a.message}</span>
              <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '0.25rem' }}>
                値: {(a.value ?? 0).toFixed(1)} / 閾値: {a.threshold}
              </div>
            </div>
          ))}
          {alerts.slack_notified && (
            <div style={{ fontSize: '0.75rem', color: '#06b6d4', marginTop: '0.5rem' }}>
              ✅ Slack通知を送信しました
            </div>
          )}
        </Box>
      )}

      {alerts && alerts.alerts && alerts.alerts.length === 0 && (
        <Box title="✅ アラート">
          <div style={{ color: '#22c55e', textAlign: 'center' }}>
            全次元が正常範囲内です
          </div>
        </Box>
      )}

      {/* Anomaly Detection Panel */}
      {anomaly && (
        <Box title="🔍 異常検知（AnomalyDetector）">
          {/* Trend Indicator */}
          {anomaly.trend && (
            <div style={{
              textAlign: 'center',
              marginBottom: '1rem',
              padding: '0.5rem',
              borderRadius: '6px',
              background: anomaly.trend.direction === 'up' ? '#0a2e1a'
                : anomaly.trend.direction === 'down' ? '#2e0a0a'
                : '#1a1a2e',
            }}>
              <span style={{ fontSize: '1.5rem' }}>
                {anomaly.trend.direction === 'up' ? '📈' : anomaly.trend.direction === 'down' ? '📉' : '➡️'}
              </span>
              <span style={{
                fontSize: '1.2rem',
                fontWeight: 'bold',
                marginLeft: '0.5rem',
                color: anomaly.trend.direction === 'up' ? '#22c55e'
                  : anomaly.trend.direction === 'down' ? '#ef4444'
                  : '#888',
              }}>
                {anomaly.trend.direction === 'up' ? '上昇トレンド'
                  : anomaly.trend.direction === 'down' ? '下降トレンド'
                  : anomaly.trend.direction === 'stable' ? '安定'
                  : '不明'}
              </span>
              <span style={{ marginLeft: '0.5rem', fontSize: '0.9rem', color: '#888' }}>
                ({anomaly.trend.change_pct > 0 ? '+' : ''}{anomaly.trend.change_pct?.toFixed(1)}%)
              </span>
            </div>
          )}

          {/* Anomaly Stats */}
          {anomaly.stats && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '0.5rem',
              marginBottom: '1rem',
            }}>
              <KpiCard
                label="検査データ点"
                value={anomaly.stats.data_points ?? 0}
                sub="日数"
              />
              <KpiCard
                label="異常検出"
                value={anomaly.alert_count ?? 0}
                sub={anomaly.alert_count > 0 ? '要確認' : '正常'}
              />
              <KpiCard
                label="検出手法"
                value={anomaly.stats.detectors_used ?? 0}
                sub="アクティブ"
              />
            </div>
          )}

          {/* Anomaly Alerts */}
          {anomaly.alerts && anomaly.alerts.length > 0 ? (
            anomaly.alerts.map((a, i) => (
              <div key={i} style={{
                padding: '0.5rem',
                marginBottom: '0.5rem',
                borderRadius: '4px',
                background: '#2e1a2e',
                borderLeft: '3px solid #a855f7',
              }}>
                <span style={{ fontWeight: 'bold', color: '#a855f7' }}>
                  🔮 {a.type || 'anomaly'}
                </span>
                <span style={{ marginLeft: '0.5rem', fontSize: '0.85rem' }}>
                  {a.message || a.description || JSON.stringify(a)}
                </span>
              </div>
            ))
          ) : (
            <div style={{ color: '#22c55e', textAlign: 'center', padding: '0.5rem' }}>
              異常なし — 収益パターンは正常範囲内です
            </div>
          )}

          {anomaly.status === 'degraded' && (
            <div style={{ fontSize: '0.75rem', color: '#f59e0b', marginTop: '0.5rem' }}>
              ⚠ AnomalyDetector利用不可: {anomaly.error}
            </div>
          )}
        </Box>
      )}

      {/* Auto-Tune Control Panel */}
      <Box title="🎛️ 自動チューニング（AutoTuner）">
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <button onClick={() => runAutoTune(false)} disabled={tuning}>
            {tuning ? '分析中…' : '🔍 分析のみ (Dry Run)'}
          </button>
          <button
            onClick={() => runAutoTune(true)}
            disabled={tuning}
            style={{
              background: '#a855f7',
              color: '#fff',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              cursor: tuning ? 'not-allowed' : 'pointer',
            }}
          >
            {tuning ? '適用中…' : '⚡ 分析 & 適用'}
          </button>
        </div>

        {tuneResult && !tuneResult.error && (
          <>
            {/* Strategy Badge */}
            <div style={{
              textAlign: 'center',
              marginBottom: '1rem',
              padding: '0.75rem',
              borderRadius: '6px',
              background: {
                explore: '#1a2e1a',
                exploit: '#1a1a2e',
                stabilize: '#2e2a1a',
                plateau_break: '#2e1a2e',
                maintain: '#1a2e2e',
              }[tuneResult.strategy] || '#1a1a1a',
            }}>
              <span style={{ fontSize: '1.5rem' }}>
                {{ explore: '🔍', exploit: '🎯', stabilize: '⚖️', plateau_break: '🔓', maintain: '✅' }[tuneResult.strategy] || '❓'}
              </span>
              <span style={{
                fontSize: '1.2rem',
                fontWeight: 'bold',
                marginLeft: '0.5rem',
                textTransform: 'uppercase',
              }}>
                {tuneResult.strategy}
              </span>
              {tuneResult.applied && (
                <span style={{
                  marginLeft: '0.75rem',
                  padding: '0.15rem 0.5rem',
                  borderRadius: '4px',
                  background: '#22c55e',
                  color: '#000',
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                }}>
                  APPLIED
                </span>
              )}
            </div>

            {/* Loop Health Estimate */}
            {tuneResult.loop_health && (
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '1rem',
                fontSize: '0.9rem',
              }}>
                <span>健全度:</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                  {tuneResult.loop_health.before}
                </span>
                <span style={{ color: '#a855f7' }}>→</span>
                <span style={{
                  fontFamily: 'monospace',
                  fontWeight: 'bold',
                  color: tuneResult.loop_health.estimated_after > tuneResult.loop_health.before
                    ? '#22c55e' : '#888',
                }}>
                  {tuneResult.loop_health.estimated_after}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#888' }}>
                  ({tuneResult.loop_health.estimated_after > tuneResult.loop_health.before
                    ? `+${(tuneResult.loop_health.estimated_after - tuneResult.loop_health.before).toFixed(1)}`
                    : '±0'})
                </span>
              </div>
            )}

            {/* Anomaly Summary */}
            {tuneResult.anomaly_summary && (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '0.5rem',
                marginBottom: '1rem',
              }}>
                <KpiCard
                  label="トレンド"
                  value={{ rising: '📈 上昇', falling: '📉 下降', stable: '➡️ 安定' }[tuneResult.anomaly_summary.trend_direction] || '❓'}
                  sub={`${tuneResult.anomaly_summary.change_pct?.toFixed(1) ?? 0}%`}
                />
                <KpiCard
                  label="異常数"
                  value={tuneResult.anomaly_summary.alert_count ?? 0}
                  sub="検出済み"
                />
                <KpiCard
                  label="アクション"
                  value={tuneResult.action_count ?? 0}
                  sub="提案数"
                />
              </div>
            )}

            {/* Action List */}
            {tuneResult.actions && tuneResult.actions.length > 0 ? (
              tuneResult.actions.map((a, i) => (
                <div key={i} style={{
                  padding: '0.5rem',
                  marginBottom: '0.5rem',
                  borderRadius: '4px',
                  background: '#1a1a2e',
                  borderLeft: '3px solid #a855f7',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 'bold', color: '#a855f7' }}>
                      {a.param}
                    </span>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {a.old_value?.toFixed(4)} → <span style={{ color: '#22c55e' }}>{a.new_value?.toFixed(4)}</span>
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#888', marginTop: '0.25rem' }}>
                    {a.reason}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '0.15rem' }}>
                    信頼度: {((a.confidence ?? 0) * 100).toFixed(0)}%
                  </div>
                </div>
              ))
            ) : (
              <div style={{ color: '#22c55e', textAlign: 'center', padding: '0.5rem' }}>
                調整不要 — 現在のパラメータは最適です
              </div>
            )}
          </>
        )}

        {tuneResult?.error && (
          <div style={{ color: '#ef4444', padding: '0.5rem' }}>
            ⚠ エラー: {tuneResult.error}
          </div>
        )}

        {tuneResult?.status === 'degraded' && (
          <div style={{ fontSize: '0.75rem', color: '#f59e0b', marginTop: '0.5rem' }}>
            ⚠ AutoTuner利用不可: {tuneResult.error}
          </div>
        )}
      </Box>
    </div>
  )
}


function KpiCard({ label, value, sub }) {
  return (
    <div style={{
      background: '#1a1a2e',
      border: '1px solid #333',
      borderRadius: '8px',
      padding: '1rem',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: '0.75rem', color: '#888', marginBottom: '0.25rem' }}>{label}</div>
      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', fontFamily: 'monospace' }}>{value}</div>
      {sub && <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '0.25rem' }}>{sub}</div>}
    </div>
  )
}
