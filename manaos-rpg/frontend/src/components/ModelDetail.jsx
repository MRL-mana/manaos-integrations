export default function ModelDetail({ model }) {
  if (!model) return null
  return (
    <div>
      <h2>{model.name}</h2>
      <div>ID: <span className="mono">{model.id}</span></div>
      <div>Type: <span className="mono">{model.type}</span></div>
      <div>Runtime: <span className="mono">{model.runtime}</span></div>
      <div>VRAM: <span className="mono">{model.vram_gb ?? '—'}GB</span></div>
      {/* タグ/バージョン/詳細など追加可 */}
    </div>
  )
}
