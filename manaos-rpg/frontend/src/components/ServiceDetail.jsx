export default function ServiceDetail({ service }) {
  if (!service) return null
  return (
    <div>
      <h2>{service.name}</h2>
      <div>ID: <span className="mono">{service.id}</span></div>
      <div>Kind: <span className="mono">{service.kind}</span></div>
      <div>Port: <span className="mono">{service.port ?? '—'}</span></div>
      <div>Status: <span className={service.alive ? 'ok' : 'danger'}>{service.alive ? 'ALIVE' : 'DOWN'}</span></div>
      {/* 依存/ヒント/詳細など追加可 */}
    </div>
  )
}
