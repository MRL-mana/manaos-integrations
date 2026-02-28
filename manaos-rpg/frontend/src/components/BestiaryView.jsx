import { useState, useMemo } from 'react'

const TYPE_ORDER = ['llm', 'vision', 'image', 'video', 'voice', 'embedding', 'reranker', 'lora', 'other']
const TYPE_ICONS = { llm: '🧠', vision: '👁', image: '🎨', video: '🎬', voice: '🔊', embedding: '📐', reranker: '🔀', lora: '🧬', other: '❓' }
const VRAM_MAX = 48 // VRAM bar reference max (GB)

function VramBar({ gb }) {
  if (typeof gb !== 'number' || gb <= 0) return <span className="mono small">—</span>
  const pct = Math.min(100, (gb / VRAM_MAX) * 100)
  const cls = gb >= 40 ? 'danger' : gb >= 16 ? 'caution' : 'ok'
  return (
    <div className="vramBarWrap" title={`${gb}GB`}>
      <div className={`vramBarFill vramBar${cls.charAt(0).toUpperCase() + cls.slice(1)}`} style={{ width: `${pct}%` }} />
      <span className="vramBarLabel">{gb}GB</span>
    </div>
  )
}

function RuntimeBadge({ runtime }) {
  if (!runtime) return null
  const cls = runtime === 'ollama' ? 'badgeOllama' : runtime === 'comfyui' ? 'badgeComfy' : 'badgeOther'
  return <span className={`runtimeBadge ${cls}`}>{runtime}</span>
}

export default function BestiaryView({ models }) {
  const list = useMemo(() => (Array.isArray(models) ? models : []), [models])
  const [filterText, setFilterText] = useState('')
  const [collapsed, setCollapsed] = useState(() => new Set())

  const filtered = useMemo(() => {
    if (!filterText.trim()) return list
    const q = filterText.trim().toLowerCase()
    return list.filter((m) => {
      const haystack = [m?.id, m?.name, m?.type, m?.runtime, m?.quant, ...(Array.isArray(m?.tags) ? m.tags : [])].join(' ').toLowerCase()
      return haystack.includes(q)
    })
  }, [list, filterText])

  /* タイプ別グループ化 */
  const { byType, types } = useMemo(() => {
    const map = new Map()
    for (const m of filtered) {
      const t = String(m?.type || 'other')
      if (!map.has(t)) map.set(t, [])
      map.get(t).push(m)
    }
    const sorted = Array.from(map.keys()).sort((a, b) => {
      const ia = TYPE_ORDER.indexOf(a)
      const ib = TYPE_ORDER.indexOf(b)
      if (ia === -1 && ib === -1) return a.localeCompare(b)
      if (ia === -1) return 1
      if (ib === -1) return -1
      return ia - ib
    })
    return { byType: map, types: sorted }
  }, [filtered])

  /* VRAM合計 */
  const totalVram = useMemo(() =>
    list.reduce((sum, m) => sum + (typeof m?.vram_gb === 'number' ? m.vram_gb : 0), 0), [list])

  const toggleGroup = (t) => {
    setCollapsed(prev => {
      const next = new Set(prev)
      next.has(t) ? next.delete(t) : next.add(t)
      return next
    })
  }

  return (
    <div>
      <div className="panelTitle">図鑑（モデル） <span className="small">{filtered.length}/{list.length}件 / {types.length}タイプ</span></div>

      {/* ─── タイプ別サマリー ─── */}
      <div className="bestiarySummary">
        {TYPE_ORDER.filter(t => byType.has(t)).map(t => (
          <span key={t} className="bestiarySummaryChip" title={t}>
            {TYPE_ICONS[t] || '❓'} {t.toUpperCase()} <strong>{byType.get(t)?.length || 0}</strong>
          </span>
        ))}
        <span className="bestiarySummaryChip" title="総VRAM">💾 {totalVram}GB</span>
      </div>

      <input className="input filterInput" value={filterText} onChange={(e) => setFilterText(e.target.value)} placeholder="フィルター（名前/ID/タグ/ランタイムで絞り込み）" aria-label="モデルフィルター" />

      {list.length === 0 ? (
        <div className="small">モデルが見つかりません（Ollama / registry を確認）</div>
      ) : null}

      {types.map((t) => {
        const items = byType.get(t) || []
        const isCollapsed = collapsed.has(t)
        return (
          <div key={t} className="sectionBlock">
            <div className="sectionHead" style={{ cursor: 'pointer' }} onClick={() => toggleGroup(t)}>
              <span>{TYPE_ICONS[t] || '❓'}</span>
              <span className="mono">{t.toUpperCase()}</span>
              <span className="small">{items.length}件</span>
              <span style={{ fontSize: 12, opacity: 0.5 }}>{isCollapsed ? '▼' : '▲'}</span>
            </div>
            {!isCollapsed && (
              <div className="bestiaryCards">
                {items.map((m) => (
                  <div key={m.id} className={`bestiaryCard${m.loaded ? ' bestiaryCardLoaded' : ''}`}>
                    <div className="bestiaryCardHead">
                      <span className="bestiaryCardName">{m.name}</span>
                      <RuntimeBadge runtime={m.runtime} />
                      {typeof m.loaded === 'boolean' ? (
                        <span className={m.loaded ? 'bestiaryLoadedBadge' : 'bestiaryIdleBadge'}>
                          {m.loaded ? '● LOADED' : '○ idle'}
                        </span>
                      ) : null}
                    </div>
                    <div className="bestiaryCardBody">
                      <div className="bestiaryCardMeta">
                        <span className="mono small">{m.id}</span>
                        {m.version ? <span className="mono small">v{m.version}</span> : null}
                        {m.quant ? <span className="mono small">{m.quant}</span> : null}
                      </div>
                      <VramBar gb={m.vram_gb} />
                      {Array.isArray(m.tags) && m.tags.length > 0 ? (
                        <div className="bestiaryTags">
                          {m.tags.map(tag => <span key={tag} className="bestiaryTag">{tag}</span>)}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
