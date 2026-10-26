import {
  ArrowUpRight,
  Bot,
  Clock3,
  Cpu,
  Keyboard,
  Monitor,
  Power,
  Radio,
  Sparkles,
  TimerReset,
  Zap,
} from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../api'
import { Button, Card, CardHeader, ScreenCanvas, StatusPill } from '../components'
import type { DeviceStatus, PageId, StripStatus } from '../types'

const modeLabels: Record<string, string> = {
  clock: '时钟',
  cpu: '系统监控',
  agent: '编程状态灯',
  live: '实时帧',
  static: '静态帧',
}

export default function Overview({
  device,
  strip,
  serviceOnline,
  onNavigate,
  onRefresh,
}: {
  device: DeviceStatus | null
  strip: StripStatus | null
  serviceOnline: boolean
  onNavigate: (page: PageId) => void
  onRefresh: () => void
}) {
  const activeMode = strip?.mode ? modeLabels[strip.mode] || strip.mode : '待机'

  async function syncTime() {
    const toastId = toast.loading('正在同步键盘时间…')
    try {
      const result = await api.syncTime()
      if (!result.ok) throw new Error('固件未确认校时命令')
      toast.success('时间已同步到键盘', { id: toastId })
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    }
  }

  async function startAgent() {
    const toastId = toast.loading('正在点亮编程状态灯…')
    try {
      await api.strip('agent')
      toast.success('编程状态灯已开启', { id: toastId })
      onRefresh()
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    }
  }

  async function stopStrip() {
    try {
      await api.strip('off')
      toast.success('长条屏已停止')
      onRefresh()
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error))
    }
  }

  return (
    <div className="page-stack page-enter">
      <section className="hero">
        <div className="hero-grid" />
        <div className="hero-glow" />
        <div className="hero-copy">
          <div className="eyebrow">
            <Radio size={12} />
            LEOBOG AMG65 / LOCAL CONTROL
          </div>
          <h1>
            把键盘的两块屏，
            <br />
            变成你的桌面仪表盘。
          </h1>
          <p>
            小屏负责表达，长条屏负责常驻。所有数据只在本地通过 USB 传输，
            不上传云端，也不依赖官方 Windows 驱动。
          </p>
          <div className="hero-actions">
            <Button variant="primary" icon={Monitor} onClick={() => onNavigate('lcd')}>
              打开小屏工作台
            </Button>
            <Button variant="ghost" icon={Sparkles} onClick={() => onNavigate('strip')}>
              配置长条屏
            </Button>
          </div>
        </div>
        <div className="hero-readout" aria-hidden="true">
          <span className="readout-label">AMG / CONTROL</span>
          <strong>AMG</strong>
          <span className="readout-sub">WIRED DESKTOP</span>
          <div className="readout-lines">
            <i />
            <i />
            <i />
            <i />
            <i />
          </div>
        </div>
      </section>

      <div className="status-strip">
        <div className="status-strip-item">
          <span className="status-strip-icon">
            <Keyboard size={17} />
          </span>
          <div>
            <span>键盘连接</span>
            <strong>{device?.ok ? 'USB 有线' : '等待连接'}</strong>
          </div>
          <StatusPill tone={device?.ok ? 'good' : 'warn'} pulse={!!device?.ok}>
            {device?.ok ? '在线' : '离线'}
          </StatusPill>
        </div>
        <div className="status-strip-divider" />
        <div className="status-strip-item">
          <span className="status-strip-icon">
            <Zap size={17} />
          </span>
          <div>
            <span>长条屏状态</span>
            <strong>{activeMode}</strong>
          </div>
          <StatusPill tone={strip?.mode ? 'mint' : 'neutral'} pulse={!!strip?.mode}>
            {strip?.mode ? '运行中' : '待机'}
          </StatusPill>
        </div>
        <div className="status-strip-divider" />
        <div className="status-strip-item">
          <span className="status-strip-icon">
            <Radio size={17} />
          </span>
          <div>
            <span>本地服务</span>
            <strong>{serviceOnline ? '127.0.0.1:8655' : '未响应'}</strong>
          </div>
          <StatusPill tone={serviceOnline ? 'good' : 'bad'}>{serviceOnline ? '正常' : '异常'}</StatusPill>
        </div>
      </div>

      <div className="dashboard-grid">
        <Card className="dashboard-screen-card" accent="mint">
          <CardHeader
            eyebrow="SMALL DISPLAY"
            title="小屏 LCD"
            detail="240 × 135 · RGB565 · 最多 130 帧"
            action={
              <button className="text-link" onClick={() => onNavigate('lcd')}>
                工作台 <ArrowUpRight size={13} />
              </button>
            }
          />
          <ScreenCanvas variant="lcd" />
          <div className="screen-footer">
            <span>图片、GIF、文字、纯色</span>
            <StatusPill tone={device?.ok ? 'good' : 'warn'}>
              {device?.ok ? '可上传' : '需有线连接'}
            </StatusPill>
          </div>
        </Card>

        <Card className="dashboard-screen-card" accent="orange">
          <CardHeader
            eyebrow="LED MATRIX"
            title="长条点阵屏"
            detail="63 × 5 · 315 LED · 实时帧不写 flash"
            action={
              <button className="text-link" onClick={() => onNavigate('strip')}>
                配置 <ArrowUpRight size={13} />
              </button>
            }
          />
          <ScreenCanvas variant="strip" />
          <div className="screen-footer">
            <span>{strip?.mode ? `${activeMode} 正在显示` : '时钟、CPU、灯效、久坐提醒'}</span>
            <StatusPill tone={strip?.mode ? 'mint' : 'neutral'} pulse={!!strip?.mode}>
              {strip?.mode ? 'LIVE' : 'IDLE'}
            </StatusPill>
          </div>
        </Card>
      </div>

      <div className="dashboard-grid dashboard-grid-lower">
        <Card>
          <CardHeader eyebrow="AGENT SIGNAL" title="编程状态灯" detail="Claude Code / Codex 双通道" />
          <div className="agent-mini-grid">
            {(['claude', 'codex'] as const).map((agent) => {
              const status = strip?.agents?.[agent]
              const state = status?.state || 'idle'
              return (
                <button
                  key={agent}
                  className={`agent-mini agent-mini-${state}`}
                  onClick={() => onNavigate('agent')}
                >
                  <span className="agent-mini-mark">{agent === 'claude' ? 'CC' : 'CX'}</span>
                  <span>
                    <strong>{agent === 'claude' ? 'Claude Code' : 'Codex'}</strong>
                    <small>{status?.sessions.length || 0} 个会话</small>
                  </span>
                  <i />
                </button>
              )
            })}
          </div>
          <div className="agent-state-legend">
            <span><i className="legend-working" />工作中</span>
            <span><i className="legend-waiting" />等待确认</span>
            <span><i className="legend-done" />已完成</span>
          </div>
        </Card>

        <Card>
          <CardHeader eyebrow="QUICK CONTROL" title="快捷操作" detail="无需进入工作台" />
          <div className="quick-grid">
            <button onClick={syncTime}>
              <Clock3 size={18} />
              <span>同步时间</span>
            </button>
            <button onClick={startAgent}>
              <Bot size={18} />
              <span>状态灯</span>
            </button>
            <button onClick={() => api.strip('clock').then(onRefresh).catch(() => undefined)}>
              <TimerReset size={18} />
              <span>显示时钟</span>
            </button>
            <button onClick={() => api.strip('cpu').then(onRefresh).catch(() => undefined)}>
              <Cpu size={18} />
              <span>系统监控</span>
            </button>
            <button onClick={stopStrip} className="quick-danger">
              <Power size={18} />
              <span>停止屏幕</span>
            </button>
          </div>
        </Card>
      </div>
    </div>
  )
}
