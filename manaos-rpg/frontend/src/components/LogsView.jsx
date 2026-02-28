import { useState, useMemo } from 'react'
import { fmtTs, fmtAgo, logTypeCls } from '../utils.js'

const TYPE_ICONS = {
  DOWN: '🔴', ERROR: '🔴', CRITICAL: '🔴', FATAL: '💀',
  RECOVERY: '🟢', START: '🟢', UP: '🟢', RESOLVED: '🟢',
  WARN: '🟡', WARNING: '🟡', CAUTION: '🟡', SLOW: '🟡',
  INFO: '🔵', REFRESH: '🔄', ACTION: '⚡'
}

export default function LogsView({ events, onRefresh }) {
  const list = useMemo(() => (Array.isArray(events) ? events : []), [events])
  const [logFilter, setLogFilter] = useState('')
  const [logTypeFilter, setLogTypeFilter] = useState('')

  const logTypes = useMemo(() => {
    const s = new Set()
    for (const e of list) if (e?.type) s.add(String(e.type).toUpperCase())
    return Array.from(s).sort()
  }, [list])

  /* タイプ別カウント */
  const typeCounts = useMemo(() => {
    const m = new Map()
    for (const e of list) {
      const t = String(e?.type || 'UNKNOWN').toUpperCase()
      m.set(t, (m.get(t) || 0) + 1)
    }
    return m
  }, [list])

  const filtered = useMemo(() => {
    let out = list
    if (logTypeFilter) {
      out = out.filter((e) => String(e?.type || '').toUpperCase() === logTypeFilter)
    }
    if (logFilter.trim()) {
      const q = logFilter.trim().toLowerCase()
      out = out.filter((e) => String(e?.message || '').toLowerCase().includes(q) || String(e?.type || '').toLowerCase().includes(q))
    }
    return out
  }, [list, logFilter, logTypeFilter])

  const reversed = useMemo(() => filtered.slice().reverse(), [filtered])

  return (
    <div>
      <div className="panelTitleRow">
        <span>戦闘ログ</span>
        <button className="link" onClick={onRefresh}>再読込</button>
        <span className="small">{filtered.length}/{list.length}件</span>
      </div>

      {/* タイプ別サマリー */}
      <div className="logTypeSummary">
        {logTypes.map(t => {
          const cnt = typeCounts.get(t) || 0
          const cls = logTypeCls(t)
          const active = logTypeFilter === t
          return (
            <button key={t}
                    className={`logTypeChip ${cls}${active ? ' logTypeChipActive' : ''}`}
                    onClick={() => setLogTypeFilter(active ? '' : t)}
                    title={`${t}: ${cnt}件`}>
              {TYPE_ICONS[t] || '📋'} {t} <strong>{cnt}</strong>
            </button>
          )
        })}
        {logTypeFilter && (
          <button className="logTypeChip" onClick={() => setLogTypeFilter('')}>✕ クリア</button>
        )}
      </div>

      <div className="filterBar">
        <input className="input inputFlush filterInput" value={logFilter} onChange={(e) => setLogFilter(e.target.value)} placeholder="テキストで絞り込み" aria-label="ログ検索" />
      </div>
      <div className="log">
        {filtered.length === 0 ? (
          <div className="small">{list.length === 0 ? 'events.log がまだ空です（サービスダウン等で自動追記）' : 'フィルターに一致するログがありません'}</div>
        ) : (
          reversed.map((e, idx) => {
            const t = String(e.type || '').toUpperCase()
            return (
              <div key={`${e.ts}-${e.type}-${idx}`} className={`logLine logLine${logTypeCls(e.type) === 'danger' ? 'Danger' : logTypeCls(e.type) === 'ok' ? 'Ok' : ''}`}>
                <span className="logTimestamp">
                  <span className="mono">{fmtTs(e.ts)}</span>
                  <span className="logAgo">{fmtAgo(e.ts ? e.ts * 1000 : null)}</span>
                </span>
                <span className={`logTypeBadge ${logTypeCls(e.type)}`}>
                  {TYPE_ICONS[t] || ''} {e.type}
                </span>
                <span className="logMsg">{e.message}</span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
