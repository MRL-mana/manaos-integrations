import { useState } from 'react'

const DEFAULT_ITEMS = [
  { id: 'cpu', label: 'CPU' },
  { id: 'ram', label: 'RAM' },
  { id: 'disk', label: 'DISK' },
  { id: 'gpu', label: 'GPU' },
  { id: 'network', label: 'NETWORK' },
  { id: 'services', label: 'サービス' },
  { id: 'stats', label: '統計' },
  { id: 'actions', label: '次の一手' }
]

export default function DashboardConfig({ open, config, onChange, onClose }) {
  const [items, setItems] = useState(config?.items || DEFAULT_ITEMS)
  const [visible, setVisible] = useState(config?.visible || DEFAULT_ITEMS.map(i => i.id))

  function handleToggle(id) {
    setVisible(v => v.includes(id) ? v.filter(x => x !== id) : [...v, id])
  }
  function handleMove(from, to) {
    const arr = [...items]
    const item = arr.splice(from, 1)[0]
    arr.splice(to, 0, item)
    setItems(arr)
  }
  function handleSave() {
    onChange && onChange({ items, visible })
    onClose && onClose()
  }
  if (!open) return null
  return (
    <div className="modalOverlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modalCard" onClick={e => e.stopPropagation()}>
        <h2>ダッシュボード表示項目設定</h2>
        <ul>
          {items.map((item, i) => (
            <li key={item.id}>
              <input type="checkbox" checked={visible.includes(item.id)} onChange={() => handleToggle(item.id)} />
              {item.label}
              {i > 0 && <button onClick={() => handleMove(i, i-1)}>↑</button>}
              {i < items.length-1 && <button onClick={() => handleMove(i, i+1)}>↓</button>}
            </li>
          ))}
        </ul>
        <button onClick={handleSave}>保存</button>
        <button className="modalClose" onClick={onClose} aria-label="閉じる">✕</button>
      </div>
    </div>
  )
}
