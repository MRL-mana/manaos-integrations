import { useMemo, useState } from 'react'

/** タグの優先表示順 */
const TAG_ORDER = [
  'always_on', 'core', 'ai', 'chat', 'monitoring', 'automation', 'mcp',
  'secretary', 'slack', 'blueprint', 'docker', 'infra', 'training',
  'generation', 'searxng', 'video', 'voice', 'image'
]

function tagPriority(tag) {
  const i = TAG_ORDER.indexOf(tag)
  return i >= 0 ? i : 999
}

/** 最優先タグでグループ化（複合タグの場合は先頭タグ） */
function primaryTag(tags) {
  if (!Array.isArray(tags) || tags.length === 0) return 'other'
  const sorted = [...tags].sort((a, b) => tagPriority(a) - tagPriority(b))
  return sorted[0]
}

/** 復旧ヒント（always_on で DOWN の時に表示） */
const RECOVERY_HINTS = {
  docker_desktop: 'Docker Desktop を起動',
  open_webui: 'Docker → open-webui コンテナ確認',
  grafana: 'Docker → grafana コンテナ確認',
  prometheus: 'Docker → prometheus コンテナ確認',
  cadvisor: 'Docker → cadvisor コンテナ確認',
  mrl_memory: 'Docker → mrl-memory コンテナ確認',
  tool_server: 'Docker → tool-server コンテナ確認',
  ollama: 'ollama serve を起動',
  n8n: 'n8n を起動',
  rpg_backend: 'cd manaos-rpg && python -m backend',
  rpg_frontend: 'cd manaos-rpg/frontend && npm run dev',
  unified_api_server: 'cd unified_api && python -m server',
}

function ServiceRow({ s }) {
  const hint = !s.alive && RECOVERY_HINTS[s.id]
  return (
    <div className={`partyRow${s.alive ? '' : ' partyRowDead'}`}>
      <div className="partyStatus">
        <span className={s.alive ? 'partyDot partyDotAlive' : 'partyDot partyDotDead'} />
      </div>
      <div className="partyMain">
        <div className="partyName">{s.name}</div>
        <div className="partyMeta">
          <span className="mono">{s.id}</span>
          <span className="mono">{s.kind}</span>
          {s.port ? <span className="mono">:{s.port}</span> : null}
        </div>
        {hint && <div className="partyHint">💡 {hint}</div>}
      </div>
      <div className="partyDetail">
        <span className="mono small">{s.alive_by || '—'}</span>
        {typeof s.http_status === 'number' ? <span className="mono small"> {s.http_status}</span> : null}
        {typeof s.docker_health === 'string' ? (
          <span className={s.docker_health === 'unhealthy' ? 'danger small' : 'small'}> {s.docker_health}</span>
        ) : null}
        {typeof s.restart_count === 'number' && s.restart_count > 0 ? (
          <span className={s.restart_count >= 5 ? 'danger small' : 'caution small'}> ↻{s.restart_count}</span>
        ) : null}
        {Array.isArray(s.deps_down) && s.deps_down.length > 0 ? (
          <span className="danger small"> deps↓{s.deps_down.length}</span>
        ) : null}
        {s.degraded ? <span className="caution small"> DEGRADED</span> : null}
      </div>
    </div>
  )
}

export default function PartyView({ services }) {
  const list = useMemo(() => (Array.isArray(services) ? services : []), [services])
  const [filterText, setFilterText] = useState('')
  const [showMode, setShowMode] = useState('all') // 'all' | 'alive' | 'down'
  const [collapsed, setCollapsed] = useState(() => new Set())

  const aliveCount = useMemo(() => list.filter(s => s.alive).length, [list])
  const downCount = list.length - aliveCount
  const alivePercent = list.length > 0 ? Math.round((aliveCount / list.length) * 100) : 0

  /** フィルター適用 */
  const filtered = useMemo(() => {
    let result = list
    if (showMode === 'alive') result = result.filter(s => s.alive)
    if (showMode === 'down') result = result.filter(s => !s.alive)
    if (filterText.trim()) {
      const q = filterText.trim().toLowerCase()
      result = result.filter(s => {
        const hay = [s.id, s.name, s.kind, ...(Array.isArray(s.tags) ? s.tags : [])].join(' ').toLowerCase()
        return hay.includes(q)
      })
    }
    return result
  }, [list, filterText, showMode])

  /** タグ別グループ化 */
  const { groups, groupOrder } = useMemo(() => {
    const map = new Map()
    for (const s of filtered) {
      const tag = primaryTag(s.tags)
      if (!map.has(tag)) map.set(tag, [])
      map.get(tag).push(s)
    }
    // 各グループ内: dead first, then alive
    for (const arr of map.values()) {
      arr.sort((a, b) => {
        if (a.alive === b.alive) return (a.name || '').localeCompare(b.name || '')
        return a.alive ? 1 : -1
      })
    }
    const order = Array.from(map.keys()).sort((a, b) => tagPriority(a) - tagPriority(b))
    return { groups: map, groupOrder: order }
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
      <div className="panelTitle">パーティ（サービス） <span className="small">{filtered.length}/{list.length}件</span></div>

      {/* ─── サマリーバー ─── */}
      <div className="partySummary">
        <div className="partySummaryBar">
          <div className="partySummaryAlive" style={{ width: `${alivePercent}%` }} />
        </div>
        <div className="partySummaryText">
          <span className="ok">{aliveCount} alive</span>
          <span className="danger">{downCount} down</span>
          <span className="small">{alivePercent}%</span>
        </div>
      </div>

      {/* ─── フィルターバー ─── */}
      <div className="filterBar">
        <input
          className="input filterInput inputFlush"
          value={filterText}
          onChange={e => setFilterText(e.target.value)}
          placeholder="フィルター（ID/名前/タグ）"
          aria-label="サービスフィルター"
        />
        <button className={`link${showMode === 'all' ? ' partyFilterActive' : ''}`} onClick={() => setShowMode('all')}>ALL</button>
        <button className={`link${showMode === 'alive' ? ' partyFilterActive' : ''}`} onClick={() => setShowMode('alive')}>ALIVE</button>
        <button className={`link${showMode === 'down' ? ' partyFilterActive' : ''}`} onClick={() => setShowMode('down')}>DOWN</button>
      </div>

      {list.length === 0 ? (
        <div className="small">サービスが未登録です（registry/services.yaml を追加）</div>
      ) : filtered.length === 0 ? (
        <div className="small">条件に一致するサービスがありません</div>
      ) : (
        <div>
          {groupOrder.map(tag => {
            const items = groups.get(tag) || []
            const groupAlive = items.filter(s => s.alive).length
            const isCollapsed = collapsed.has(tag)
            return (
              <div key={tag} className="sectionBlock">
                <div className="sectionHead" style={{ cursor: 'pointer' }} onClick={() => toggleGroup(tag)}>
                  <span className="mono">{tag.toUpperCase()}</span>
                  <span>
                    <span className="ok">{groupAlive}</span>
                    <span className="small"> / </span>
                    <span className={items.length - groupAlive > 0 ? 'danger' : 'small'}>{items.length}</span>
                  </span>
                  <span style={{ fontSize: 12, opacity: 0.5 }}>{isCollapsed ? '▼' : '▲'}</span>
                </div>
                {!isCollapsed && (
                  <div className="partyGroup">
                    {items.map(s => <ServiceRow key={s.id} s={s} />)}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
