import { useMemo, useState } from 'react'

const KIND_EMOJI = { desktop: '🖥️', laptop: '💻', mobile: '📱', server: '🗄️' }
const KIND_COLOR = { desktop: '#7CFF6B', laptop: '#6BB5FF', mobile: '#FFE66B', server: '#FF6B6B' }

function SpecBar({ label, value, max, unit }) {
  if (!value) return null
  const num = parseFloat(value)
  if (isNaN(num)) return (
    <div className="mapSpecRow">
      <span className="mapSpecLabel">{label}</span>
      <span className="mono small">{value}</span>
    </div>
  )
  const pct = Math.min(100, (num / max) * 100)
  return (
    <div className="mapSpecRow">
      <span className="mapSpecLabel">{label}</span>
      <div className="mapSpecBarWrap">
        <div className="mapSpecBarFill" style={{ width: `${pct}%` }} />
        <span className="mapSpecBarText">{value}{unit || ''}</span>
      </div>
    </div>
  )
}

function DeviceCard({ d, isPrimary }) {
  const [open, setOpen] = useState(isPrimary)
  const specs = d.specs || {}
  const features = Array.isArray(d.features) ? d.features : []
  const health = Array.isArray(d.health) ? d.health : []
  const network = d.network || {}
  const kindEmoji = KIND_EMOJI[d.kind] || '🔧'
  const accentColor = KIND_COLOR[d.kind] || 'var(--dim)'

  return (
    <div className={`mapDeviceCard${typeof d.alive === 'boolean' && !d.alive ? ' mapDeviceOffline' : ''}`}
         style={{ borderLeftColor: accentColor }}>
      <div className="mapDeviceHeader" onClick={() => setOpen(!open)}>
        <div className="mapDeviceTitle">
          <span className="mapDeviceEmoji">{kindEmoji}</span>
          <div>
            <div className="mapDeviceName">{d.name}</div>
            <div className="mapDeviceSub">{d.id} · {d.os || d.kind}</div>
          </div>
        </div>
        <div className="mapDeviceStatus">
          {typeof d.alive === 'boolean' ? (
            <span className={d.alive ? 'mapOnlineBadge' : 'mapOfflineBadge'}>
              {d.alive ? '● ONLINE' : '○ OFFLINE'}
            </span>
          ) : <span className="small">—</span>}
          <span className="mapChevron">{open ? '▲' : '▼'}</span>
        </div>
      </div>

      {/* Role */}
      {d.role && <div className="mapDeviceRole">{d.role}</div>}

      {open && (
        <div className="mapDeviceBody">
          {/* Tags */}
          {Array.isArray(d.tags) && d.tags.length > 0 && (
            <div className="mapTagRow">
              {d.tags.map(t => <span key={t} className="bestiaryTag">{t}</span>)}
            </div>
          )}

          {/* Specs - visual bars */}
          {Object.keys(specs).length > 0 && (
            <div className="mapSection">
              <div className="mapSectionTitle">📊 スペック</div>
              {specs.cpu && <div className="mapSpecRow"><span className="mapSpecLabel">CPU</span><span className="mono small">{specs.cpu}</span></div>}
              {specs.gpu && <div className="mapSpecRow"><span className="mapSpecLabel">GPU</span><span className="mono small">{specs.gpu}</span></div>}
              {specs.ram && <SpecBar label="RAM" value={specs.ram} max="128GB" unit="" />}
              {specs.storage && <div className="mapSpecRow"><span className="mapSpecLabel">Storage</span><span className="mono small">{specs.storage}</span></div>}
            </div>
          )}

          {/* Network */}
          {Object.keys(network).length > 0 && (
            <div className="mapSection">
              <div className="mapSectionTitle">🌐 ネットワーク</div>
              {network.tailscale_ip && <div className="mapSpecRow"><span className="mapSpecLabel">Tailscale</span><span className="mono small">{network.tailscale_ip}</span></div>}
              {network.local_ip && <div className="mapSpecRow"><span className="mapSpecLabel">Local</span><span className="mono small">{network.local_ip}</span></div>}
              {network.usb_ip && <div className="mapSpecRow"><span className="mapSpecLabel">USB</span><span className="mono small">{network.usb_ip}</span></div>}
            </div>
          )}

          {/* Health checks */}
          {health.length > 0 && (
            <div className="mapSection">
              <div className="mapSectionTitle">🩺 ヘルスチェック</div>
              {health.map((h, i) => (
                <div key={i} className="mapHealthRow">
                  <span className={`mapHealthDot ${h.type === 'http' ? 'mapHealthHttp' : 'mapHealthOther'}`} />
                  <span className="small">{h.label}</span>
                  <span className="mono small">{h.url || h.host || h.serial || '—'}</span>
                </div>
              ))}
            </div>
          )}

          {/* Features */}
          {features.length > 0 && (
            <div className="mapSection">
              <div className="mapSectionTitle">⚡ 機能</div>
              <div className="mapFeatures">
                {features.map((f, i) => <span key={i} className="mapFeatureChip">{f}</span>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TopologyLine({ from, to }) {
  return (
    <div className="mapTopoLine">
      <span className="mapTopoNode">{from}</span>
      <span className="mapTopoArrow">⟷</span>
      <span className="mapTopoNode">{to}</span>
    </div>
  )
}

export default function MapView({ devices }) {
  const list = useMemo(() => (Array.isArray(devices) ? devices : []), [devices])
  const aliveCount = useMemo(() => list.filter(d => d.alive).length, [list])
  const primary = list.find(d => d.kind === 'desktop')

  return (
    <div>
      <div className="panelTitle">マップ（デバイス） <span className="small">{list.length}件 / {aliveCount} online</span></div>

      {list.length === 0 ? (
        <div className="small">デバイスが未登録です（registry/devices.yaml を追加）</div>
      ) : (
        <>
          {/* Topology overview */}
          {list.length > 1 && (
            <div className="mapTopology">
              <div className="mapTopoTitle">🗺️ ネットワークトポロジー</div>
              <div className="mapTopoGraph">
                {list.map((d, i) => (
                  <div key={d.id} className="mapTopoDevice">
                    <span className="mapTopoEmoji">{KIND_EMOJI[d.kind] || '🔧'}</span>
                    <span className={`mapTopoName ${d.alive === false ? 'danger' : ''}`}>{d.name?.split('（')[0] || d.id}</span>
                  </div>
                ))}
              </div>
              <div className="mapTopoLines">
                {list.length >= 2 && primary && list.filter(d => d.id !== primary.id).map(d => (
                  <TopologyLine key={d.id} from={primary.name?.split('（')[0] || primary.id} to={d.name?.split('（')[0] || d.id} />
                ))}
              </div>
            </div>
          )}

          {/* Device cards */}
          <div className="mapDeviceGrid">
            {list.map(d => <DeviceCard key={d.id} d={d} isPrimary={d.id === primary?.id} />)}
          </div>
        </>
      )}
    </div>
  )
}
