import { useState, useMemo } from 'react'
import { fmtTs, logTypeCls } from '../utils.js'

export default function LogsView({ events, onRefresh }) {
  const list = Array.isArray(events) ? events : []
  const [logFilter, setLogFilter] = useState('')
  const [logTypeFilter, setLogTypeFilter] = useState('')

  const logTypes = useMemo(() => {
    const s = new Set()
    for (const e of list) if (e?.type) s.add(String(e.type).toUpperCase())
    return Array.from(s).sort()
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
      <div className="filterBar">
        <input className="input inputFlush filterInput" value={logFilter} onChange={(e) => setLogFilter(e.target.value)} placeholder="テキストで絞り込み" aria-label="ログ検索" />
        <select value={logTypeFilter} onChange={(e) => setLogTypeFilter(e.target.value)} aria-label="ログタイプフィルター">
          <option value="">全タイプ</option>
          {logTypes.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div className="log">
        {filtered.length === 0 ? (
          <div className="small">{list.length === 0 ? 'events.log がまだ空です（サービスダウン等で自動追記）' : 'フィルターに一致するログがありません'}</div>
        ) : (
          reversed.map((e, idx) => (
            <div key={`${e.ts}-${e.type}-${idx}`} className="logLine">
              <span className="mono">{fmtTs(e.ts)}</span>
              <span className={`mono ${logTypeCls(e.type)}`}>[{e.type}]</span>
              <span>{e.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
