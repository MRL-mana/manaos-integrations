import { useState, useMemo } from 'react'
import { truncateOutput } from '../utils.js'
import { fetchJson } from '../api.js'
import OutputBlock from './OutputBlock.jsx'

const KIND_ICONS = { api: '🌐', action: '⚡', manual: '📝' }

export default function QuestsView({ quests, onRunAction, actionResult, runningAction }) {
  const list = useMemo(() => (Array.isArray(quests) ? quests : []), [quests])
  const [questLoading, setQuestLoading] = useState('')
  const [questResult, setQuestResult] = useState(null)
  const [filterText, setFilterText] = useState('')
  const [collapsed, setCollapsed] = useState(() => new Set())

  async function runApiQuest(endpoint) {
    setQuestLoading(endpoint)
    setQuestResult(null)
    try {
      const r = await fetchJson(endpoint)
      const text = JSON.stringify(r, null, 2)
      setQuestResult({ endpoint, text: truncateOutput(text), ok: true })
    } catch (e) {
      setQuestResult({ endpoint, text: `ERR: ${String(e?.message || e)}`, ok: false })
    } finally {
      setQuestLoading('')
    }
  }

  const filtered = useMemo(() => {
    if (!filterText.trim()) return list
    const q = filterText.trim().toLowerCase()
    return list.filter(qu =>
      [qu.id, qu.label, qu.kind, ...(Array.isArray(qu.tags) ? qu.tags : [])].join(' ').toLowerCase().includes(q)
    )
  }, [list, filterText])

  /* タグ別グループ化 */
  const { groups, groupOrder } = useMemo(() => {
    const map = new Map()
    for (const q of filtered) {
      const tag = (Array.isArray(q.tags) && q.tags[0]) || q.kind || 'other'
      if (!map.has(tag)) map.set(tag, [])
      map.get(tag).push(q)
    }
    return { groups: map, groupOrder: Array.from(map.keys()).sort() }
  }, [filtered])

  const toggleGroup = (tag) => {
    setCollapsed(prev => {
      const next = new Set(prev)
      next.has(tag) ? next.delete(tag) : next.add(tag)
      return next
    })
  }

  return (
    <div>
      <div className="panelTitle">クエスト（タスク） <span className="small">{filtered.length}/{list.length}件</span></div>

      {/* サマリー */}
      <div className="questSummary">
        <span className="bestiarySummaryChip" title="API">🌐 API <strong>{list.filter(q => q.kind === 'api').length}</strong></span>
        <span className="bestiarySummaryChip" title="Action">⚡ ACTION <strong>{list.filter(q => q.kind === 'action').length}</strong></span>
      </div>

      <input className="input filterInput" value={filterText}
        onChange={e => setFilterText(e.target.value)}
        placeholder="フィルター（ID/ラベル/タグ）" aria-label="クエストフィルター" />

      {/* 直近アクション結果 */}
      {actionResult ? (
        <div className={`questResultBox ${actionResult.result?.ok ? 'questResultOk' : 'questResultNg'}`}>
          <div className="questResultHead">
            <span className="mono">{actionResult.action_id}</span>
            <span className={actionResult.result?.ok ? 'ok' : 'danger'}>
              {actionResult.result?.ok ? '✓ OK' : '✗ NG'}
            </span>
          </div>
          {typeof actionResult.result?.exit_code === 'number' ? (
            <div className="small mono">exit: {actionResult.result.exit_code}</div>
          ) : null}
          {actionResult.result?.error ? (
            <div className="small danger">{actionResult.result.error}</div>
          ) : null}
        </div>
      ) : null}

      {/* グループ別表示 */}
      {filtered.length === 0 ? (
        <div className="small">条件に一致するクエストがありません</div>
      ) : (
        groupOrder.map(tag => {
          const items = groups.get(tag) || []
          const isCollapsed = collapsed.has(tag)
          return (
            <div key={tag} className="sectionBlock">
              <div className="sectionHead" role="button" aria-expanded={!isCollapsed} style={{ cursor: 'pointer' }} onClick={() => toggleGroup(tag)}>
                <span className="mono">{String(tag).toUpperCase()}</span>
                <span className="small">{items.length}件</span>
                <span style={{ fontSize: 12, opacity: 0.5 }}>{isCollapsed ? '▼' : '▲'}</span>
              </div>
              {!isCollapsed && items.map(q => (
                <div key={q.id} className="questRow">
                  <span className="questKindIcon">{KIND_ICONS[q.kind] || '📋'}</span>
                  <div className="questInfo">
                    <div className="questLabel">{q.label}</div>
                    <div className="questMeta">
                      <span className="mono small">{q.id}</span>
                      <span className="mono small">{q.endpoint ?? q.action_id ?? ''}</span>
                    </div>
                  </div>
                  <div className="questAction">
                    {q.kind === 'api' && q.endpoint ? (
                      <button className="questBtn" disabled={!!questLoading} onClick={() => runApiQuest(q.endpoint)}>
                        {questLoading === q.endpoint ? '⏳' : '▶ 実行'}
                      </button>
                    ) : q.kind === 'action' && q.action_id ? (
                      <button className="questBtn questBtnAction" disabled={!!runningAction} onClick={() => onRunAction?.(q.action_id)}>
                        {runningAction === q.action_id ? '⏳' : '⚡ 実行'}
                      </button>
                    ) : (
                      <span className="small">—</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )
        })
      )}

      {questResult ? (
        <div className="mt12">
          <div className="small">結果: <span className="mono">{questResult.endpoint}</span></div>
          <OutputBlock text={questResult.text} onClear={() => setQuestResult(null)} />
        </div>
      ) : null}
    </div>
  )
}
