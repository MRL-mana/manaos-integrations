import React, { useState } from 'react'

export default function OutputBlock({ text, onClear }) {
  const [copied, setCopied] = useState(false)
  function handleCopy() {
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }).catch(() => {})
  }
  return (
    <div className="outputWrap">
      <pre className="output">{text}</pre>
      <div className="outputActions">
        <button className="link" onClick={handleCopy} aria-label="出力をクリップボードにコピー">{copied ? 'コピー済' : 'コピー'}</button>
        {onClear ? <button className="link" onClick={onClear} aria-label="出力をクリア">クリア</button> : null}
      </div>
    </div>
  )
}
