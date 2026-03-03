/**
 * ManaOS RPG — 共有ユーティリティ定数・関数
 */

export const TITLE_BASE = 'MANAOS // RPG COMMAND'

/** 共通定数: マジックナンバー排除 */
export const MAX_OUTPUT_LEN = 18000
export const AUTO_REFRESH_MS = 30000
export const ERROR_DISMISS_MS = 15000
export const EVENTS_LIMIT = 120
export const ITEMS_SHOW_LIMIT = 24
export const TICK_INTERVAL_MS = 60000

export const FALLBACK_MENU = [
  { id: 'status', label: 'ステータス', icon: '🧍' },
  { id: 'party', label: 'パーティ（サービス）', icon: '🧩' },
  { id: 'bestiary', label: '図鑑（モデル）', icon: '📚' },
  { id: 'skills', label: '魔法（スキル）', icon: '✨' },
  { id: 'quests', label: 'クエスト（タスク）', icon: '🗺' },
  { id: 'logs', label: '戦闘ログ', icon: '📜' },
  { id: 'map', label: 'マップ（デバイス）', icon: '🧭' },
  { id: 'items', label: 'アイテム（生成物）', icon: '🎒' },
  { id: 'rl', label: '強化学習(RL)', icon: '🧠' },
  { id: 'revenue', label: '収益（KPI）', icon: '💰' },
  { id: 'systems', label: 'システム（統合）', icon: '⚙️' }
]

export const DIFFICULTY_CLS = { beginner: 'ok', standard: '', advanced: 'caution', expert: 'danger' }

export const MONITOR_ROUTES = {
  comfyui_queue: { path: '/api/unified/comfyui/queue', requires: '/api/comfyui/queue' },
  comfyui_history: { path: '/api/unified/comfyui/history', requires: '/api/comfyui/history' },
  svi_queue: { path: '/api/unified/svi/queue', requires: '/api/svi/queue' },
  svi_history: { path: '/api/unified/svi/history', requires: '/api/svi/history' },
  ltx2_queue: { path: '/api/unified/ltx2/queue', requires: '/api/ltx2/queue' },
  ltx2_history: { path: '/api/unified/ltx2/history', requires: '/api/ltx2/history' },
  images_recent: { path: '/api/unified/images/recent?limit=30', requires: '/api/images/recent' },
  llm_health: { path: '/api/unified/llm/health', requires: '/api/llm/health' },
  llm_models: { path: '/api/unified/llm/models-enhanced', requires: '/api/llm/models-enhanced' },
  unified_openapi: { path: '/api/unified/openapi' },
  unified_proxy_doctor: { path: '/api/unified/proxy/doctor?limit=200&probe_timeout_s=1.5&max_total_s=8' }
}

export function pad2(n) {
  return String(n).padStart(2, '0')
}

export function fmtTs(ts) {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`
}

export function bar(pct) {
  const p = Math.max(0, Math.min(100, Number(pct || 0)))
  const filled = Math.round((p / 100) * 20)
  return `[${'#'.repeat(filled)}${'.'.repeat(20 - filled)}] ${p.toFixed(0)}%`
}

export function dangerRank(danger) {
  const d = Number(danger || 0)
  if (d >= 7) return { label: 'DANGER', cls: 'danger' }
  if (d >= 4) return { label: 'CAUTION', cls: 'caution' }
  return { label: 'OK', cls: 'ok' }
}

export function fmtAgo(tsMs, _tick) {
  if (!tsMs) return ''
  const sec = Math.floor((Date.now() - tsMs) / 1000)
  if (sec < 5) return 'たった今'
  if (sec < 60) return `${sec}秒前`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}分前`
  return `${Math.floor(min / 60)}時間前`
}

export function logTypeCls(type) {
  const t = String(type || '').toUpperCase()
  if (t === 'DOWN' || t === 'ERROR' || t === 'CRITICAL' || t === 'FATAL') return 'danger'
  if (t === 'RECOVERY' || t === 'START' || t === 'UP' || t === 'RESOLVED') return 'ok'
  if (t === 'WARN' || t === 'WARNING' || t === 'CAUTION' || t === 'SLOW') return 'caution'
  return ''
}

export function encodeRelPath(relPath) {
  const p = String(relPath || '').replace(/\\/g, '/')
  return p.split('/').map(encodeURIComponent).join('/')
}

export function fmtBytes(n) {
  const v = Number(n || 0)
  if (!Number.isFinite(v) || v <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let x = v
  let i = 0
  while (x >= 1024 && i < units.length - 1) {
    x /= 1024
    i++
  }
  return `${x.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function difficultyColor(d) { return DIFFICULTY_CLS[String(d)] || '' }

/** 長すぎる出力を安全にトランケートする */
export function truncateOutput(text) {
  return text.length > MAX_OUTPUT_LEN ? (text.slice(0, MAX_OUTPUT_LEN) + '\n... (truncated)') : text
}
