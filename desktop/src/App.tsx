import {
  Bot,
  ChevronRight,
  CircleAlert,
  Gauge,
  Keyboard,
  LayoutDashboard,
  Monitor,
  PanelTop,
  Settings2,
  Sparkles,
  WifiOff,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import { API_BASE, api } from './api'
import { StatusPill, cx } from './components'
import AgentPage from './pages/AgentPage'
import LcdPage from './pages/LcdPage'
import Overview from './pages/Overview'
import SettingsPage from './pages/SettingsPage'
import StripPage from './pages/StripPage'
import type {
  DesktopInfo,
  DeviceStatus,
  HooksPayload,
  PageId,
  Preset,
  StripStatus,
} from './types'

const pages: Array<{
  id: PageId
  label: string
  caption: string
  icon: typeof LayoutDashboard
  title: string
  subtitle: string
}> = [
  {
    id: 'overview',
    label: '总览',
    caption: 'Overview',
    icon: LayoutDashboard,
    title: '控制台总览',
    subtitle: '两块屏幕与本地服务的实时状态',
  },
  {
    id: 'lcd',
    label: '小屏 LCD',
    caption: '240 × 135',
    icon: Monitor,
    title: '小屏 LCD',
    subtitle: '图片、GIF、文字与纯色',
  },
  {
    id: 'strip',
    label: '长条屏',
    caption: '63 × 5',
    icon: PanelTop,
    title: '长条点阵屏',
    subtitle: '实时内容、官方灯效与久坐提醒',
  },
  {
    id: 'agent',
    label: '状态灯',
    caption: 'Claude + Codex',
    icon: Bot,
    title: '编程状态灯',
    subtitle: 'Claude Code / Codex 双通道状态',
  },
  {
    id: 'settings',
    label: '设置',
    caption: 'Preferences',
    icon: Settings2,
    title: '设置与关于',
    subtitle: '启动项、常驻行为与运行环境',
  },
]

function useDesktopState() {
  const [info, setInfo] = useState<DesktopInfo | null>(null)
  const [launchAtLogin, setLaunchAtLogin] = useState(false)

  useEffect(() => {
    const bridge = window.amg65Desktop
    if (!bridge) return
    bridge.getInfo().then(setInfo).catch(() => undefined)
    bridge.getLaunchAtLogin().then(setLaunchAtLogin).catch(() => undefined)
  }, [])

  async function changeLaunchAtLogin(enabled: boolean) {
    const bridge = window.amg65Desktop
    if (!bridge) throw new Error('仅桌面应用支持登录项设置')
    const actual = await bridge.setLaunchAtLogin(enabled)
    setLaunchAtLogin(actual)
  }

  return { info, launchAtLogin, changeLaunchAtLogin }
}

export default function App() {
  const [page, setPage] = useState<PageId>('overview')
  const [device, setDevice] = useState<DeviceStatus | null>(null)
  const [strip, setStrip] = useState<StripStatus | null>(null)
  const [hooks, setHooks] = useState<HooksPayload | null>(null)
  const [presets, setPresets] = useState<Preset[]>([])
  const [serviceOnline, setServiceOnline] = useState(false)
  const [refreshTick, setRefreshTick] = useState(0)
  const contentRef = useRef<HTMLDivElement>(null)
  const { info, launchAtLogin, changeLaunchAtLogin } = useDesktopState()

  const activePage = useMemo(() => pages.find((item) => item.id === page) || pages[0], [page])

  useEffect(() => {
    let alive = true
    let timer: number | undefined

    async function poll() {
      try {
        const next = await api.deviceStatus()
        if (!alive) return
        setDevice(next)
        setServiceOnline(true)
      } catch (error) {
        if (!alive) return
        setServiceOnline(false)
        setDevice({
          ok: false,
          error: error instanceof Error ? error.message : '本地服务未响应',
        })
      } finally {
        if (alive) timer = window.setTimeout(poll, 4500)
      }
    }

    poll()
    return () => {
      alive = false
      if (timer) window.clearTimeout(timer)
    }
  }, [refreshTick])

  useEffect(() => {
    let alive = true
    let timer: number | undefined

    async function poll() {
      try {
        const next = await api.stripStatus()
        if (!alive) return
        setStrip(next)
        setServiceOnline(true)
      } catch {
        if (!alive) return
        setServiceOnline(false)
      } finally {
        if (alive) timer = window.setTimeout(poll, 1000)
      }
    }

    poll()
    return () => {
      alive = false
      if (timer) window.clearTimeout(timer)
    }
  }, [refreshTick])

  useEffect(() => {
    let alive = true
    let timer: number | undefined

    async function poll() {
      try {
        const next = await api.hooks()
        if (alive) setHooks(next)
      } catch {
        // The device poll already surfaces service availability.
      } finally {
        if (alive) timer = window.setTimeout(poll, 3000)
      }
    }

    poll()
    return () => {
      alive = false
      if (timer) window.clearTimeout(timer)
    }
  }, [refreshTick])

  useEffect(() => {
    api
      .presets()
      .then((result) => setPresets(result.presets))
      .catch(() => setPresets([]))
  }, [])

  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }, [page])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === ',') {
        event.preventDefault()
        setPage('settings')
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  function refresh() {
    setRefreshTick((value) => value + 1)
  }

  async function refreshHooks() {
    try {
      setHooks(await api.hooks())
    } catch {
      toast.error('无法刷新钩子状态')
    }
  }

  return (
    <div className="app-shell">
      <div className="window-drag" />
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <span>AMG</span>
            <i />
          </div>
          <div>
            <strong>AMG CONTROL</strong>
            <span>CONTROL</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <nav className="nav-list">
          {pages.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                className={cx('nav-item', page === item.id && 'is-active')}
                onClick={() => setPage(item.id)}
              >
                <span className="nav-icon"><Icon size={17} strokeWidth={1.75} /></span>
                <span className="nav-copy">
                  <strong>{item.label}</strong>
                  <small>{item.caption}</small>
                </span>
                <ChevronRight className="nav-arrow" size={14} />
              </button>
            )
          })}
        </nav>

        <div className="sidebar-spacer" />
        <div className="sidebar-signal">
          <div className="sidebar-signal-top">
            <span className={cx('signal-orb', device?.ok && 'is-online')}>
              <Keyboard size={17} />
            </span>
            <StatusPill tone={device?.ok ? 'good' : 'warn'} pulse={!!device?.ok}>
              {device?.ok ? 'CONNECTED' : 'WAITING'}
            </StatusPill>
          </div>
          <strong>{device?.ok ? 'LEOBOG AMG65' : '等待 USB 连接'}</strong>
          <span>{device?.ok ? '配置通道已就绪' : '请使用有线模式'}</span>
        </div>
        <div className="sidebar-foot">
          <span>v{info?.version || '1.1.0'}</span>
          <span>{window.amg65Desktop ? 'MENU BAR APP' : 'BROWSER PREVIEW'}</span>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-title">
            <span className="topbar-kicker">{activePage.caption}</span>
            <h2>{activePage.title}</h2>
          </div>
          <div className="topbar-actions">
            <span className="topbar-subtitle">{activePage.subtitle}</span>
            <StatusPill
              tone={device?.ok ? 'good' : serviceOnline ? 'warn' : 'bad'}
              pulse={!!device?.ok}
            >
              {device?.ok ? '键盘在线' : serviceOnline ? '等待键盘' : '服务离线'}
            </StatusPill>
          </div>
        </header>

        <div className="content-scroll" ref={contentRef}>
          {!serviceOnline && (
            <div className="offline-banner">
              <span><WifiOff size={17} /></span>
              <div>
                <strong>本地服务未响应</strong>
                <p>
                  请从菜单栏重新打开应用。如果问题持续，查看后端日志。
                  <code>{API_BASE}</code>
                </p>
              </div>
              <button onClick={() => window.amg65Desktop?.openLogs()}>打开日志</button>
            </div>
          )}

          {page === 'overview' && (
            <Overview
              device={device}
              strip={strip}
              serviceOnline={serviceOnline}
              onNavigate={setPage}
              onRefresh={refresh}
            />
          )}
          {page === 'lcd' && <LcdPage device={device} />}
          {page === 'strip' && (
            <StripPage status={strip} presets={presets} onRefresh={refresh} />
          )}
          {page === 'agent' && (
            <AgentPage
              strip={strip}
              hooks={hooks}
              autostart={hooks?.autostart ?? false}
              onRefresh={refresh}
              onRefreshHooks={refreshHooks}
            />
          )}
          {page === 'settings' && (
            <SettingsPage
              info={info}
              device={device}
              serviceOnline={serviceOnline}
              launchAtLogin={launchAtLogin}
              onLaunchAtLogin={changeLaunchAtLogin}
            />
          )}
        </div>

        <footer className="app-footer">
          <span><Gauge size={13} /> 本地控制 · 无云端</span>
          <span><Sparkles size={13} /> 关闭窗口后仍在菜单栏运行</span>
          {!serviceOnline && <span className="footer-warning"><CircleAlert size={13} /> 服务离线</span>}
        </footer>
      </main>
    </div>
  )
}
