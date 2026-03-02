export default function DeviceDetail({ device }) {
  if (!device) return null
  return (
    <div>
      <h2>{device.name}</h2>
      <div>ID: <span className="mono">{device.id}</span></div>
      <div>Type: <span className="mono">{device.type}</span></div>
      <div>Status: <span className={device.alive ? 'ok' : 'danger'}>{device.alive ? 'ALIVE' : 'DOWN'}</span></div>
    </div>
  )
}
