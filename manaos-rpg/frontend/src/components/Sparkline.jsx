import React from 'react'

/** SVG スパークライン — values 配列をインライン折れ線チャートで描画 */
export default function Sparkline({ values = [], width = 300, height = 40, color = '#4ade80', strokeWidth = 1.5 }) {
  if (!values || values.length < 2) return null
  const nums = values.map(Number).filter(Number.isFinite)
  if (nums.length < 2) return null
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const range = max - min || 1
  const padY = 2
  const points = nums.map((v, i) => {
    const x = (i / (nums.length - 1)) * width
    const y = height - padY - ((v - min) / range) * (height - padY * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return (
    <svg width={width} height={height} style={{ display: 'block', background: 'rgba(0,0,0,0.15)', borderRadius: 4 }}>
      <polyline fill="none" stroke={color} strokeWidth={strokeWidth} points={points} />
      <circle cx={(nums.length - 1) / (nums.length - 1) * width} cy={height - padY - ((nums[nums.length - 1] - min) / range) * (height - padY * 2)} r="2.5" fill={color} />
    </svg>
  )
}
