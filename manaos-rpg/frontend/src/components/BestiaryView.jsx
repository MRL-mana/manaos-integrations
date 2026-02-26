import { useState, useMemo } from 'react'

export default function BestiaryView({ models }) {
  const list = useMemo(() => (Array.isArray(models) ? models : []), [models])
  const [filterText, setFilterText] = useState('')

  const filtered = useMemo(() => {
    if (!filterText.trim()) return list
    const q = filterText.trim().toLowerCase()
    return list.filter((m) => {
      const haystack = [m?.id, m?.name, m?.type, m?.quant, ...(Array.isArray(m?.tags) ? m.tags : [])].join(' ').toLowerCase()
      return haystack.includes(q)
    })
  }, [list, filterText])

  const { byType, types } = useMemo(() => {
    const map = new Map()
    for (const m of filtered) {
      const t = String(m?.type || 'other')
      if (!map.has(t)) map.set(t, [])
      map.get(t).push(m)
    }
    const order = ['llm', 'image', 'video', 'voice', 'embedding', 'reranker', 'lora', 'other']
    const sorted = Array.from(map.keys()).sort((a, b) => {
      const ia = order.indexOf(a)
      const ib = order.indexOf(b)
      if (ia === -1 && ib === -1) return a.localeCompare(b)
      if (ia === -1) return 1
      if (ib === -1) return -1
      return ia - ib
    })
    return { byType: map, types: sorted }
  }, [filtered])

  return (
    <div>
      <div className="panelTitle">図鑑（モデル） <span className="small">{filtered.length}/{list.length}件 / {types.length}タイプ</span></div>
      <input className="input filterInput" value={filterText} onChange={(e) => setFilterText(e.target.value)} placeholder="フィルター（名前/ID/タグで絞り込み）" aria-label="モデルフィルター" />
      {list.length === 0 ? (
        <div className="small">モデルが見つかりません（Ollama / registry を確認）</div>
      ) : null}
      {types.map((t) => (
        <div key={t} className="sectionBlock">
          <div className="sectionHead">
            <span className="mono">TYPE</span>
            <span className="mono">{t.toUpperCase()}</span>
            <span className="small">{byType.get(t)?.length ?? 0}件</span>
          </div>
          <div className="table">
            <div className="tr th colsBestiary">
              <div>ID</div><div>NAME</div><div>TYPE</div><div>VER</div><div>QUANT</div><div>VRAM</div><div>TAGS</div>
            </div>
            {(byType.get(t) || []).map((m) => (
              <div key={m.id} className={`tr colsBestiary${m.loaded ? ' trLoaded' : ''}`}>
                <div className="mono">{m.id}</div>
                <div>{m.name}</div>
                <div className="mono">{m.type}</div>
                <div className="mono">{m.version ?? '—'}</div>
                <div className="mono">{m.quant ?? '—'}</div>
                <div className="mono">{m.vram_gb ?? '—'}GB</div>
                <div className="small">
                  {Array.isArray(m.tags) ? m.tags.join(', ') : '—'}
                  {typeof m.loaded === 'boolean' ? (
                    <span className={m.loaded ? 'ok' : 'small'}>{m.loaded ? ' / LOADED' : ' / idle'}</span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
      <div className="small">PATH は backend の /api/registry で参照（運用上はパス漏洩に注意）</div>
    </div>
  )
}
