import { useState } from 'react'

export default function SettingsView({ open, onClose, config, onSave }) {
  const [apiKey, setApiKey] = useState(config?.apiKey || '')
  const [refreshMs, setRefreshMs] = useState(config?.refreshMs || 30000)
  const [theme, setTheme] = useState(config?.theme || 'default')

  if (!open) return null
  return (
    <div className="modalOverlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modalCard" onClick={e => e.stopPropagation()}>
        <h2>設定</h2>
        <label>APIキー <input value={apiKey} onChange={e => setApiKey(e.target.value)} /></label>
        <label>自動更新間隔(ms) <input type="number" value={refreshMs} onChange={e => setRefreshMs(Number(e.target.value))} /></label>
        <label>テーマ <select value={theme} onChange={e => setTheme(e.target.value)}><option value="default">デフォルト</option><option value="dark">ダーク</option><option value="light">ライト</option></select></label>
        <button onClick={() => onSave({ apiKey, refreshMs, theme })}>保存</button>
        <button className="modalClose" onClick={onClose} aria-label="閉じる">✕</button>
      </div>
    </div>
  )
}
