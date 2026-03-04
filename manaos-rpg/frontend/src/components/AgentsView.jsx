import { useState, useEffect, useCallback } from 'react'
import { fetchJson } from '../api.js'
import Box from './Box.jsx'

/**
 * AgentsView — Claudeエージェントのランク＆品質ダッシュボード
 *
 * agent_tracker に蓄積された使用回数・ランク・品質スコアを可視化する。
 * RPGコマンド画面の「エージェント」タブとして機能する。
 */

const RANK_ORDER = ['N-S', 'N-A', 'N-B', 'N-C', 'N']
const RANK_STYLE = {
  'N-S': { bg: '#ffd700', color: '#111', label: 'N-S ★★★★★' },
  'N-A': { bg: '#c0a0ff', color: '#111', label: 'N-A ★★★★' },
  'N-B': { bg: '#7ec8e3', color: '#111', label: 'N-B ★★★' },
  'N-C': { bg: '#a8d8a8', color: '#111', label: 'N-C ★★' },
  'N':   { bg: '#555',    color: '#ddd', label: 'N ★' },
}

function RankBadge({ rank }) {
  const style = RANK_STYLE[rank] || RANK_STYLE['N']
  return (
    <span style={{
      background: style.bg,
      color: style.color,
      borderRadius: '4px',
      padding: '2px 7px',
      fontSize: '0.72rem',
      fontWeight: 'bold',
      whiteSpace: 'nowrap',
    }}>
      {rank || 'N'}
    </span>
  )
}

function ScoreBar({ score, max = 100 }) {
  const pct = Math.min(100, Math.round((score / max) * 100))
  const color = pct >= 80 ? '#a8d8a8' : pct >= 50 ? '#ffd700' : '#ff6666'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <div style={{ background: '#333', borderRadius: '3px', height: '8px', flex: 1 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '3px', transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontSize: '0.75rem', color, minWidth: '34px', textAlign: 'right' }}>{score}/{max}</span>
    </div>
  )
}

export default function AgentsView() {
  const [agentList, setAgentList]   = useState([])
  const [parking, setParking]       = useState([])
  const [audit, setAudit]           = useState([])
  const [stats, setStats]           = useState(null)
  const [loading, setLoading]       = useState(false)
  const [tab, setTab]               = useState('list')   // 'list' | 'audit' | 'parking'
  const [rankFilter, setRankFilter] = useState('')
  const [error, setError]           = useState('')

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [listData, statsData] = await Promise.all([
        fetchJson('/api/agents/list'),
        fetchJson('/api/agents/stats'),
      ])
      setAgentList(listData.items || [])
      setStats(statsData)
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchParking = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchJson('/api/agents/parking')
      setParking(data.items || [])
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchAudit = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchJson('/api/agents/audit')
      setAudit(data.items || [])
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (tab === 'parking' && parking.length === 0) fetchParking()
    if (tab === 'audit'   && audit.length === 0)   fetchAudit()
  }, [tab]) // eslint-disable-line react-hooks/exhaustive-deps

  /* ランク別集計 */
  const rankSummary = RANK_ORDER.map((r) => ({
    rank: r,
    count: agentList.filter((a) => a.rank === r).length,
  }))

  /* フィルター済みリスト */
  const filtered = rankFilter
    ? agentList.filter((a) => a.rank === rankFilter)
    : agentList

  /* 最終使用日フォーマット */
  function fmtDate(d) {
    if (!d) return '未使用'
    return String(d).slice(0, 10)
  }

  return (
    <div className="agentsRoot">
      {/* ヘッダー */}
      <div style={{ marginBottom: '1.2rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#ccc' }}>
          🤖 エージェント追跡
        </h2>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: '#888' }}>
          Claude Code エージェントの使用回数・ランク・品質スコアを一覧化
        </p>
      </div>

      {error && (
        <div className="err" style={{ marginBottom: '0.8rem' }}>{error}</div>
      )}

      {/* ランク内訳 */}
      {agentList.length > 0 && (
        <Box title="🏆 ランク内訳" style={{ marginBottom: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap' }}>
            {rankSummary.map(({ rank, count }) => {
              const s = RANK_STYLE[rank]
              return (
                <button
                  key={rank}
                  onClick={() => setRankFilter(rankFilter === rank ? '' : rank)}
                  style={{
                    background: rankFilter === rank ? s.bg : '#2a2a3a',
                    color: rankFilter === rank ? s.color : '#bbb',
                    border: `2px solid ${s.bg}`,
                    borderRadius: '6px',
                    padding: '6px 14px',
                    cursor: 'pointer',
                    fontSize: '0.82rem',
                    fontWeight: 'bold',
                  }}
                >
                  {rank} <span style={{ opacity: 0.8 }}>({count})</span>
                </button>
              )
            })}
            {(stats?.total ?? agentList.length) > 0 && (
              <div style={{ marginLeft: 'auto', fontSize: '0.78rem', color: '#888', alignSelf: 'center' }}>
                合計 {agentList.length} エージェント
              </div>
            )}
          </div>
        </Box>
      )}

      {/* サブタブ */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '0.8rem', borderBottom: '1px solid #333', paddingBottom: '4px' }}>
        {[
          { id: 'list',    label: '📋 一覧' },
          { id: 'audit',   label: '🔬 品質監査' },
          { id: 'parking', label: '🅿  未使用' },
        ].map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              background: tab === id ? '#3a3a5a' : 'none',
              border: tab === id ? '1px solid #555' : '1px solid transparent',
              color: tab === id ? '#ccc' : '#888',
              padding: '4px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.82rem',
            }}
          >
            {label}
          </button>
        ))}
        <div style={{ marginLeft: 'auto' }}>
          <button
            onClick={() => { fetchAll(); if (tab === 'audit') fetchAudit(); if (tab === 'parking') fetchParking() }}
            disabled={loading}
            style={{ background: 'none', border: '1px solid #444', color: '#888', padding: '3px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.78rem' }}
          >
            {loading ? '更新中…' : '↻ 更新'}
          </button>
        </div>
      </div>

      {/* ─── 一覧タブ ─── */}
      {tab === 'list' && (
        <Box title={`エージェント一覧${rankFilter ? ` [${rankFilter}]` : ''}`}>
          {filtered.length === 0 ? (
            <div style={{ color: '#888', fontSize: '0.85rem' }}>
              {agentList.length === 0
                ? (stats?.status === 'unavailable' ? 'agent_tracker が利用できません' : 'データなし')
                : 'このランクのエージェントはいません'}
            </div>
          ) : (
            <div style={{ overflowY: 'auto', maxHeight: '450px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', color: '#ccc' }}>
                <thead>
                  <tr style={{ background: '#252535', borderBottom: '1px solid #444' }}>
                    <th style={{ textAlign: 'left', padding: '4px 8px' }}>エージェント名</th>
                    <th style={{ textAlign: 'center', padding: '4px 8px', width: '70px' }}>ランク</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', width: '60px' }}>使用数</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', width: '95px' }}>最終使用</th>
                    <th style={{ textAlign: 'left', padding: '4px 8px' }}>直近タスク</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered
                    .sort((a, b) => {
                      const ri = (r) => RANK_ORDER.indexOf(r)
                      if (ri(a.rank) !== ri(b.rank)) return ri(a.rank) - ri(b.rank)
                      return (b.total_uses ?? 0) - (a.total_uses ?? 0)
                    })
                    .map((agent, i) => (
                      <tr key={agent.name ?? i} style={{ borderBottom: '1px solid #333' }}>
                        <td style={{ padding: '5px 8px', fontFamily: 'monospace', fontSize: '0.8rem' }}>{agent.name}</td>
                        <td style={{ padding: '5px 8px', textAlign: 'center' }}><RankBadge rank={agent.rank} /></td>
                        <td style={{ padding: '5px 8px', textAlign: 'right', color: agent.total_uses > 0 ? '#7ec8e3' : '#666' }}>{agent.total_uses ?? 0}</td>
                        <td style={{ padding: '5px 8px', textAlign: 'right', color: '#666', fontSize: '0.75rem' }}>{fmtDate(agent.last_used)}</td>
                        <td style={{ padding: '5px 8px', color: '#888', fontSize: '0.78rem', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {agent.last_task || '—'}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </Box>
      )}

      {/* ─── 品質監査タブ ─── */}
      {tab === 'audit' && (
        <Box title="🔬 品質スコア（100点満点）">
          {audit.length === 0 ? (
            <div style={{ color: '#888', fontSize: '0.85rem' }}>
              {loading ? '監査中…' : 'エージェントが見つかりません（.claude/agents/ を確認してください）'}
            </div>
          ) : (
            <div style={{ overflowY: 'auto', maxHeight: '450px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', color: '#ccc' }}>
                <thead>
                  <tr style={{ background: '#252535', borderBottom: '1px solid #444' }}>
                    <th style={{ textAlign: 'left', padding: '4px 8px' }}>エージェント名</th>
                    <th style={{ textAlign: 'left', padding: '4px 8px', width: '200px' }}>品質スコア</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.map((item, i) => (
                    <tr key={item.name ?? i} style={{ borderBottom: '1px solid #333' }}>
                      <td style={{ padding: '5px 8px', fontFamily: 'monospace', fontSize: '0.8rem' }}>{item.name}</td>
                      <td style={{ padding: '5px 8px' }}>
                        <ScoreBar score={item.score} max={item.max_score ?? 100} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Box>
      )}

      {/* ─── 未使用パーキングタブ ─── */}
      {tab === 'parking' && (
        <Box title="🅿 パーキング候補（30日未使用）">
          {parking.length === 0 ? (
            <div style={{ color: '#a8d8a8', fontSize: '0.85rem' }}>
              {loading ? '確認中…' : '✓ 未使用エージェントはありません'}
            </div>
          ) : (
            <div>
              <div style={{ fontSize: '0.82rem', color: '#ff9966', marginBottom: '0.6rem' }}>
                ⚠ {parking.length} 件のエージェントが30日以上未使用です
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', color: '#ccc' }}>
                <thead>
                  <tr style={{ background: '#252535', borderBottom: '1px solid #444' }}>
                    <th style={{ textAlign: 'left', padding: '4px 8px' }}>エージェント名</th>
                    <th style={{ textAlign: 'center', padding: '4px 8px', width: '70px' }}>ランク</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', width: '60px' }}>使用数</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', width: '95px' }}>最終使用</th>
                  </tr>
                </thead>
                <tbody>
                  {parking.map((agent, i) => (
                    <tr key={agent.name ?? i} style={{ borderBottom: '1px solid #333' }}>
                      <td style={{ padding: '5px 8px', fontFamily: 'monospace', fontSize: '0.8rem' }}>{agent.name}</td>
                      <td style={{ padding: '5px 8px', textAlign: 'center' }}><RankBadge rank={agent.rank} /></td>
                      <td style={{ padding: '5px 8px', textAlign: 'right', color: '#666' }}>{agent.total_uses ?? 0}</td>
                      <td style={{ padding: '5px 8px', textAlign: 'right', color: '#888', fontSize: '0.75rem' }}>{fmtDate(agent.last_used)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Box>
      )}
    </div>
  )
}
