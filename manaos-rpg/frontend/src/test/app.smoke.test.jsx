import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

describe('App smoke', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(async (url) => {
      const u = String(url)

      if (u.includes('/api/snapshot')) {
        return jsonResponse({
          ts: 1735689600,
          danger: 1,
          host: {
            cpu: { percent: 10 },
            mem: { percent: 20, used_gb: 8, total_gb: 32 },
            disk: { free_gb: 100, total_gb: 256 },
            host: { hostname: 'test-host', os: 'windows', disk_root: 'C:' },
            gpu: { nvidia: [], apps: [] },
            net: { bytes_sent: 1000, bytes_recv: 2000 }
          },
          services: [],
          menu: [
            { id: 'status', label: 'ステータス', icon: '🧍' },
            { id: 'party', label: 'パーティ（サービス）', icon: '🧩' },
            { id: 'bestiary', label: '図鑑（モデル）', icon: '📚' },
            { id: 'skills', label: '魔法（スキル）', icon: '✨' },
            { id: 'quests', label: 'クエスト（タスク）', icon: '🗺' },
            { id: 'logs', label: '戦闘ログ', icon: '📜' },
            { id: 'map', label: 'マップ（デバイス）', icon: '🧭' },
            { id: 'items', label: 'アイテム（生成物）', icon: '🎒' },
            { id: 'rl', label: '強化学習(RL)', icon: '🧠' },
            { id: 'systems', label: 'システム（統合）', icon: '⚙️' }
          ],
          next_actions: [],
          next_action_hints: [],
          actions_enabled: false,
          models: [],
          quests: [],
          devices: [],
          items: { roots: [], recent: [] },
          skills: [],
          prompts: { ollama: [], image: [], video: [] },
          rl_anything: { enabled: false },
          unified: { integrations: { ok: false }, proxy: { rules: [], write_enabled: false } }
        })
      }

      if (u.includes('/api/events')) {
        return jsonResponse({ events: [] })
      }

      if (u.includes('/api/state')) {
        return jsonResponse({ ts: 1735689600, danger: 0, services: [] })
      }

      return jsonResponse({}, 404)
    }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders header and loads snapshot', async () => {
    render(<App />)

    expect(screen.getByText('MANAOS // RPG COMMAND')).toBeInTheDocument()

    await waitFor(() => {
      expect(fetch).toHaveBeenCalled()
    })

    expect(screen.getByText(/API:/)).toBeInTheDocument()
    expect(screen.getByText(/サービス:/)).toBeInTheDocument()
  })
})
