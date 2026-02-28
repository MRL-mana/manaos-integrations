import { useMemo, useState } from 'react'

function DeviceCard({ d }) {
  const [open, setOpen] = useState(false)
  const specs = d.specs || {}
  const features = Array.isArray(d.features) ? d.features : []
  const health = Array.isArray(d.health) ? d.health : []
  const kindEmoji = d.kind === 'desktop' ? '🖥️' : d.kind === 'laptop' ? '💻' : d.kind === 'mobile' ? '📱' : '🔧'

  return (
    <div className={`deviceCard${typeof d.alive === 'boolean' && !d.alive ? ' trDanger' : ''}`}
         style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '12px 16px', marginBottom: 10, background: 'var(--bg-card, #1a1a2e)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
           onClick={() => setOpen(!open)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 24 }}>{kindEmoji}</span>
          <div>
            <div style={{ fontWeight: 'bold', fontSize: 16 }}>{d.name}</div>
            <div className="small mono" style={{ opacity: 0.7 }}>{d.id} · {d.os || d.kind} · {d.role || '—'}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {typeof d.alive === 'boolean' ? (
            <span className={d.alive ? 'ok' : 'danger'} style={{ fontWeight: 'bold' }}>
              {d.alive ? '● ONLINE' : '○ OFFLINE'}
            </span>
          ) : <span className="small">—</span>}
          <span style={{ fontSize: 12, opacity: 0.5 }}>{open ? '▲' : '▼'}</span>
        </div>
      </div>

      {open && (
        <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
          {/* Tags */}
          <div style={{ marginBottom: 8 }}>
            {Array.isArray(d.tags) && d.tags.map(t => (
              <span key={t} style={{ display: 'inline-block', background: 'var(--accent, #333)', borderRadius: 4, padding: '2px 8px', marginRight: 4, marginBottom: 4, fontSize: 11 }}>{t}</span>
            ))}
          </div>

          {/* Specs */}
          {Object.keys(specs).length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 'bold', fontSize: 12, marginBottom: 4 }}>📊 スペック</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '2px 12px', fontSize: 13 }}>
                {specs.cpu && <><span className="small">CPU</span><span className="mono">{specs.cpu}</span></>}
                {specs.gpu && <><span className="small">GPU</span><span className="mono">{specs.gpu}</span></>}
                {specs.ram && <><span className="small">RAM</span><span className="mono">{specs.ram}</span></>}
                {specs.storage && <><span className="small">Storage</span><span className="mono">{specs.storage}</span></>}
              </div>
            </div>
          )}

          {/* Health checks */}
          {health.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 'bold', fontSize: 12, marginBottom: 4 }}>🩺 ヘルスチェック</div>
              {health.map((h, i) => (
                <div key={i} className="small mono" style={{ marginLeft: 8 }}>
                  [{h.type}] {h.label}: {h.url || h.host || h.serial || '—'}
                </div>
              ))}
            </div>
          )}

          {/* Features */}
          {features.length > 0 && (
            <div>
              <div style={{ fontWeight: 'bold', fontSize: 12, marginBottom: 4 }}>⚡ 機能</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {features.map((f, i) => (
                  <span key={i} style={{ display: 'inline-block', background: '#2a2a4a', borderRadius: 4, padding: '2px 8px', fontSize: 11 }}>{f}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function MapView({ devices }) {
  const list = useMemo(() => (Array.isArray(devices) ? devices : []), [devices])
  const aliveDevices = useMemo(() => list.filter((d) => d.alive), [list])
  return (
    <div>
      <div className="panelTitle">マップ（デバイス） <span className="small">{list.length}件{list.length > 0 ? ` / ${aliveDevices.length} online` : ''}</span></div>
      {list.length === 0 ? (
        <div className="small">デバイスが未登録です（registry/devices.yaml を追加）</div>
      ) : (
        <div>
          {list.map((d) => <DeviceCard key={d.id} d={d} />)}
        </div>
      )}
    </div>
  )
}
