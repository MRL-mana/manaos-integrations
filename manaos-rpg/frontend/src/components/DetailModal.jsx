export default function DetailModal({ open, onClose, children }) {
  if (!open) return null
  return (
    <div className="modalOverlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modalCard" onClick={e => e.stopPropagation()}>
        <button className="modalClose" onClick={onClose} aria-label="閉じる">✕</button>
        {children}
      </div>
    </div>
  )
}
