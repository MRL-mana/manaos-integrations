const DEFAULT_BASE = 'http://127.0.0.1:9510'

export function getApiBase() {
  return import.meta.env.VITE_API_BASE || DEFAULT_BASE
}

export async function fetchJson(path) {
  const base = getApiBase()
  const res = await fetch(`${base}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${path}`)
  }
  return await res.json()
}
