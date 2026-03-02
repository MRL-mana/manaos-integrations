import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from '../App.jsx'

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

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
        services: [
          {
            id: 'unified_api_server',
            name: 'Unified API Server',
            kind: 'api',
            alive: true,
            port: 9502,
            tags: ['always_on', 'ai'],
            alive_by: 'http',
            http_status: 200
          },
          {
            id: 'open_webui',
            name: 'Open WebUI',
            kind: 'web',
            alive: false,
            port: 3001,
            tags: ['always_on', 'chat'],
            alive_by: 'http',
            http_status: 503
          }
        ],
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
        models: [
          {
            id: 'llama3:8b',
            name: 'Llama3 8B',
            type: 'llm',
            runtime: 'ollama',
            vram_gb: 8,
            loaded: true,
            tags: ['chat']
          }
        ],
        quests: [
          {
            id: 'q-health-check',
            label: 'Health Check API',
            kind: 'api',
            endpoint: '/api/health/check',
            tags: ['ops']
          },
          {
            id: 'q-restart-openwebui',
            label: 'Restart OpenWebUI',
            kind: 'action',
            action_id: 'restart_openwebui',
            tags: ['recovery']
          }
        ],
        devices: [
          {
            id: 'main-desktop',
            name: 'Main Desktop',
            kind: 'desktop',
            os: 'Windows',
            alive: true,
            role: 'mother-ship',
            tags: ['primary'],
            specs: { cpu: 'Ryzen 9', ram: '64', storage: '2TB NVMe' },
            network: { local_ip: '192.168.3.10' },
            features: ['docker', 'ollama']
          },
          {
            id: 'pixel7',
            name: 'Pixel7',
            kind: 'mobile',
            os: 'Android',
            alive: true,
            role: 'remote',
            tags: ['android', 'adb'],
            network: { tailscale_ip: '100.99.0.7' },
            features: ['scrcpy', 'termux']
          }
        ],
        items: {
          roots: [{ id: 'gallery', label: 'Gallery' }],
          recent: [
            {
              root_id: 'gallery',
              rel_path: 'notes/sample.txt',
              name: 'sample.txt',
              kind: 'text',
              mtime: 1735689600,
              size_bytes: 1234
            }
          ]
        },
        skills: [
          {
            id: 'comm',
            label: 'Communication',
            items: [
              {
                id: 'notify',
                label: '通知送信',
                action_id: 'notify_send',
                integration_key: 'openwebui'
              }
            ]
          }
        ],
        prompts: {
          ollama: [{ id: 'quick-summary', label: 'Quick Summary', prompt: '要約して' }],
          image: [],
          video: []
        },
        rl_anything: { enabled: false },
        unified: {
          base: 'http://127.0.0.1:5105',
          services: [
            { id: 'unified_api_server', name: 'Unified API Server', deps: ['open_webui'] },
            { id: 'open_webui', name: 'Open WebUI', deps: [] }
          ],
          integrations: {
            ok: true,
            data: {
              health: { service: 'unified-api', status: 'healthy', mcp_available: true },
              openapi: { title: 'Unified API', version: '1.0.0', paths_count: 120, paths_sample: ['/api/health', '/api/memory/recall'] },
              openwebui: { name: 'Open WebUI', available: true, reason: '' }
            }
          },
          proxy: { rules: [], write_enabled: false },
          mrl_memory: {
            ok: true,
            base: 'http://127.0.0.1:5110',
            health: { service: 'mrl-memory', status: 'healthy', auth_required: false },
            metrics: { config: { write_mode: 'readonly', write_enabled: false } }
          }
        }
      })
    }

    if (u.includes('/api/ollama/tags')) {
      return jsonResponse({ data: { models: [{ name: 'llama3:8b' }] } })
    }

    if (u.includes('/api/events')) {
      return jsonResponse({
        events: [
          { ts: 1735689600, type: 'DOWN', message: 'open_webui is down' },
          { ts: 1735689660, type: 'RECOVERY', message: 'open_webui recovered' }
        ]
      })
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

test('renders header and basic status meta', async () => {
  render(<App />)

  expect(screen.getByText('MANAOS // RPG COMMAND')).toBeInTheDocument()

  await waitFor(() => {
    expect(fetch).toHaveBeenCalled()
  })

  expect(screen.getByText(/API:/)).toBeInTheDocument()
  expect(screen.getByText(/サービス:/)).toBeInTheDocument()
})

test('opens and closes bestiary model detail modal', async () => {
  render(<App />)

  const bestiaryTab = await screen.findByRole('tab', { name: /図鑑（モデル）/ })
  fireEvent.click(bestiaryTab)

  const card = await screen.findByText('Llama3 8B')
  fireEvent.click(card)

  expect(await screen.findByText('ID:')).toBeInTheDocument()
  expect(screen.getByText('Runtime:')).toBeInTheDocument()
  expect(screen.getByText('VRAM:')).toBeInTheDocument()

  fireEvent.click(screen.getByLabelText('閉じる'))

  await waitFor(() => {
    expect(screen.queryByText('ID:')).not.toBeInTheDocument()
  })
})

test('renders party tab with service rows and status summary', async () => {
  render(<App />)

  const partyTab = await screen.findByRole('tab', { name: /パーティ（サービス）/ })
  fireEvent.click(partyTab)

  expect(await screen.findByText(/2件/)).toBeInTheDocument()
  expect(screen.getByText('Unified API Server')).toBeInTheDocument()
  expect(screen.getByText('Open WebUI')).toBeInTheDocument()
  expect(screen.getByText(/1 alive/)).toBeInTheDocument()
})

test('renders map tab with topology and device cards', async () => {
  render(<App />)

  const mapTab = await screen.findByRole('tab', { name: /マップ（デバイス）/ })
  fireEvent.click(mapTab)

  expect(await screen.findByText(/ネットワークトポロジー/)).toBeInTheDocument()
  expect(screen.getAllByText('Main Desktop').length).toBeGreaterThan(0)
  expect(screen.getAllByText('Pixel7').length).toBeGreaterThan(0)
  expect(screen.getByText(/2件\s*\/\s*2 online/)).toBeInTheDocument()
})

test('renders skills tab with cheatsheet and unified status', async () => {
  render(<App />)

  const skillsTab = await screen.findByRole('tab', { name: /魔法（スキル）/ })
  fireEvent.click(skillsTab)

  expect(await screen.findByText('生成ツール早見表')).toBeInTheDocument()
  expect(screen.getByText(/Unified integrations\/status:/)).toBeInTheDocument()
  expect(screen.getAllByText('通知送信').length).toBeGreaterThan(0)
})

test('renders systems tab overview cards', async () => {
  render(<App />)

  const systemsTab = await screen.findByRole('tab', { name: /システム（統合）/ })
  fireEvent.click(systemsTab)

  expect(screen.getAllByText('システム（統合）').length).toBeGreaterThan(0)
  expect(screen.getAllByText('Unified API').length).toBeGreaterThan(0)
  expect(screen.getByText('MRL Memory')).toBeInTheDocument()
  expect(screen.getAllByText(/available/).length).toBeGreaterThan(0)
})

test('renders quests tab with quest rows', async () => {
  render(<App />)

  const questsTab = await screen.findByRole('tab', { name: /クエスト（タスク）/ })
  fireEvent.click(questsTab)

  expect(screen.getAllByText('Health Check API').length).toBeGreaterThan(0)
  expect(screen.getAllByText('Restart OpenWebUI').length).toBeGreaterThan(0)
  expect(screen.getByText(/成功率/)).toBeInTheDocument()
})

test('renders logs tab with event entries', async () => {
  render(<App />)

  const logsTab = await screen.findByRole('tab', { name: /戦闘ログ/ })
  fireEvent.click(logsTab)

  expect(screen.getAllByText('戦闘ログ').length).toBeGreaterThan(0)
  expect(await screen.findByText('open_webui is down')).toBeInTheDocument()
  expect(screen.getByText('open_webui recovered')).toBeInTheDocument()
})

test('renders items tab with recent artifact', async () => {
  render(<App />)

  const itemsTab = await screen.findByRole('tab', { name: /アイテム（生成物）/ })
  fireEvent.click(itemsTab)

  expect(screen.getAllByText('アイテム（生成物）').length).toBeGreaterThan(0)
  expect(await screen.findByText('Gallery')).toBeInTheDocument()
  expect(screen.getByText('sample.txt')).toBeInTheDocument()
})

test('renders rl tab with disabled message when RL is off', async () => {
  render(<App />)

  const rlTab = await screen.findByRole('tab', { name: /強化学習\(RL\)/ })
  fireEvent.click(rlTab)

  expect(await screen.findByText(/RLAnything が無効または未初期化/)).toBeInTheDocument()
})
