import { useState, useEffect, useCallback } from 'react'
import { fetchJson } from '../api.js'
import Box from './Box.jsx'

/**
 * LessonsView — AIへの教訓ダッシュボード
 *
 * lessons_recorder に蓄積された「指摘・修正パターン」を可視化する。
 * RPGコマンド画面の「教訓」タブとして機能する。
 */
export default function LessonsView() {
  const [stats, setStats]   = useState(null)
  const [items, setItems]   = useState([])
  const [query, setQuery]   = useState('')
  const [category, setCat]  = useState('')
  const [loading, setLoading] = useState(false)
  const [searching, setSearching] = useState(false)
  const [error, setError]   = useState('')

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await fetchJson('/api/lessons/stats')
      setStats(data)
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  const doSearch = useCallback(async () => {
    setSearching(true)
    setError('')
    try {
      const qs = new URLSearchParams()
      if (query)    qs.set('q', query)
      if (category) qs.set('category', category)
      qs.set('limit', '100')
      const data = await fetchJson(`/api/lessons/search?${qs}`)
      setItems(data.items || [])
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setSearching(false)
    }
  }, [query, category])

  /* 初期 — 全件取得 */
  useEffect(() => {
    doSearch()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  /* カテゴリ一覧を stats から生成 */
  const categories = stats?.by_category ? Object.keys(stats.by_category) : []

  /* カテゴリ最大値（バー幅計算用） */
  const maxCatCount = stats?.by_category
    ? Math.max(...Object.values(stats.by_category), 1)
    : 1

  const RANK_COLORS = {
    output_format:      '#7ec8e3',
    communication:      '#a8d8a8',
    code_quality:       '#ffd700',
    process:            '#ff9966',
    tool_use:           '#c9a0dc',
  }
  function catColor(cat) {
    return RANK_COLORS[cat] || '#8888aa'
  }

  return (
    <div className="lessonsRoot">
      {/* ヘッダー */}
      <div style={{ marginBottom: '1.2rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#ccc' }}>
          📖 教訓ダッシュボード
        </h2>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: '#888' }}>
          ユーザーからの指摘・修正パターンを記録したAIの成長ログ
        </p>
      </div>

      {error && (
        <div className="err" style={{ marginBottom: '0.8rem' }}>{error}</div>
      )}

      {/* 統計サマリー */}
      <Box title="📊 統計サマリー" style={{ marginBottom: '1rem' }}>
        {loading ? (
          <div className="loading">読み込み中…</div>
        ) : stats ? (
          <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            {/* 合計 */}
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#7ec8e3' }}>
                {stats.total ?? 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#888' }}>教訓 合計</div>
            </div>

            {/* カテゴリ別バー */}
            <div style={{ flex: 1, minWidth: '220px' }}>
              {categories.map((cat) => {
                const cnt = stats.by_category[cat]
                const pct = Math.round((cnt / maxCatCount) * 100)
                return (
                  <div key={cat} style={{ marginBottom: '0.4rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: '#aaa', marginBottom: '2px' }}>
                      <span>{cat}</span>
                      <span>{cnt}</span>
                    </div>
                    <div style={{ background: '#333', borderRadius: '3px', height: '8px' }}>
                      <div style={{
                        width: `${pct}%`,
                        height: '100%',
                        background: catColor(cat),
                        borderRadius: '3px',
                        transition: 'width 0.3s',
                      }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ) : (
          <div style={{ color: '#888', fontSize: '0.85rem' }}>
            {stats?.status === 'unavailable' ? 'lessons_recorder が利用できません' : 'データなし'}
          </div>
        )}
      </Box>

      {/* 繰り返し多い教訓 TOP */}
      {stats?.top_repeated?.length > 0 && (
        <Box title="🔁 繰り返し多い教訓 TOP" style={{ marginBottom: '1rem' }}>
          <ol style={{ margin: 0, paddingLeft: '1.5rem', fontSize: '0.85rem', color: '#ccc' }}>
            {stats.top_repeated.slice(0, 5).map((item, i) => (
              <li key={item.id ?? i} style={{ marginBottom: '0.4rem', lineHeight: 1.5 }}>
                <span style={{
                  display: 'inline-block',
                  background: '#cc4444',
                  color: '#fff',
                  borderRadius: '3px',
                  padding: '0 5px',
                  fontSize: '0.7rem',
                  marginRight: '6px',
                }}>×{item.count ?? 1}</span>
                {item.instruction}
              </li>
            ))}
          </ol>
        </Box>
      )}

      {/* 検索フィルター */}
      <Box title="🔍 教訓一覧" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.8rem', flexWrap: 'wrap' }}>
          <input
            className="input"
            placeholder="キーワード検索…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doSearch()}
            style={{ flex: 1, minWidth: '160px', padding: '4px 8px', background: '#2a2a3a', border: '1px solid #444', color: '#ddd', borderRadius: '4px', fontSize: '0.85rem' }}
          />
          <select
            value={category}
            onChange={e => setCat(e.target.value)}
            style={{ padding: '4px 8px', background: '#2a2a3a', border: '1px solid #444', color: '#ddd', borderRadius: '4px', fontSize: '0.85rem' }}
          >
            <option value="">全カテゴリ</option>
            {categories.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <button
            onClick={doSearch}
            disabled={searching}
            style={{ padding: '4px 12px', background: '#3a3a5a', border: '1px solid #555', color: '#ccc', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}
          >
            {searching ? '検索中…' : '検索'}
          </button>
          <button
            onClick={() => { setQuery(''); setCat('') }}
            style={{ padding: '4px 12px', background: '#2a2a3a', border: '1px solid #444', color: '#888', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}
          >
            リセット
          </button>
        </div>

        {/* テーブル */}
        {items.length === 0 ? (
          <div style={{ color: '#888', fontSize: '0.85rem' }}>教訓が見つかりません</div>
        ) : (
          <div style={{ overflowY: 'auto', maxHeight: '400px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', color: '#ccc' }}>
              <thead>
                <tr style={{ background: '#252535', borderBottom: '1px solid #444' }}>
                  <th style={{ textAlign: 'left', padding: '4px 8px', width: '80px' }}>カテゴリ</th>
                  <th style={{ textAlign: 'left', padding: '4px 8px' }}>教訓</th>
                  <th style={{ textAlign: 'right', padding: '4px 8px', width: '50px' }}>回数</th>
                  <th style={{ textAlign: 'right', padding: '4px 8px', width: '90px' }}>登録日</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => (
                  <tr key={item.id ?? i} style={{ borderBottom: '1px solid #333', ':hover': { background: '#2a2a3a' } }}>
                    <td style={{ padding: '4px 8px' }}>
                      <span style={{
                        background: catColor(item.category),
                        color: '#111',
                        borderRadius: '3px',
                        padding: '1px 5px',
                        fontSize: '0.72rem',
                        fontWeight: 'bold',
                      }}>{item.category}</span>
                    </td>
                    <td style={{ padding: '4px 8px', lineHeight: 1.5 }}>{item.instruction}</td>
                    <td style={{ padding: '4px 8px', textAlign: 'right', color: (item.count > 1 ? '#ff9966' : '#888') }}>
                      {item.count ?? 1}
                    </td>
                    <td style={{ padding: '4px 8px', textAlign: 'right', color: '#666', fontSize: '0.72rem' }}>
                      {item.created_at ? item.created_at.slice(0, 10) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Box>

      <div style={{ textAlign: 'right' }}>
        <button onClick={fetchStats} disabled={loading} style={{ background: 'none', border: '1px solid #444', color: '#888', padding: '3px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.78rem' }}>
          ↻ 統計を更新
        </button>
      </div>
    </div>
  )
}
