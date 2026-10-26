import {
  Bot,
  CircleCheck,
  CircleHelp,
  Code2,
  LoaderCircle,
  ShieldCheck,
  TerminalSquare,
  Unplug,
  Zap,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { api } from '../api'
import { Button, Card, CardHeader, StatusPill, Toggle } from '../components'
import type { AgentKey, AgentState, HooksPayload, StripStatus } from '../types'

const stateLabels: Record<AgentState, string> = {
  idle: '空闲',
  working: '工作中',
  waiting: '等你操作',
  done: '已完成',
}

const stateHints: Record<AgentState, string> = {
  idle: '没有正在运行的会话',
  working: '黄色流水灯',
  waiting: '红色闪烁灯',
  done: '绿色常亮',
}

const agentMeta = {
  claude: {
    short: 'CC',
    name: 'Claude Code',
    detail: '~/.claude/settings.json',
    icon: Code2,
  },
  codex: {
    short: 'CX',
    name: 'Codex',
    detail: '~/.codex/hooks.json',
    icon: TerminalSquare,
  },
}

function ago(seconds: number | null) {
  if (seconds == null) return '还没收到事件'
  if (seconds < 60) return `${seconds} 秒前`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  return `${Math.floor(seconds / 3600)} 小时前`
}

export default function AgentPage({
  strip,
  hooks,
  autostart,
  onRefresh,
  onRefreshHooks,
}: {
  strip: StripStatus | null
  hooks: HooksPayload | null
  autostart: boolean
  onRefresh: () => void
  onRefreshHooks: () => void
}) {
  const [busy, setBusy] = useState<string | null>(null)
  const [localAutostart, setLocalAutostart] = useState(autostart)

  async function startAgent() {
    setBusy('start')
    const toastId = toast.loading('正在开启状态灯…')
    try {
      await api.strip('agent')
      toast.success('编程状态灯已开启', { id: toastId })
      onRefresh()
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    } finally {
      setBusy(null)
    }
  }

  async function stopAgent() {
    setBusy('stop')
    try {
      await api.strip('off')
      toast.success('状态灯已停止')
      onRefresh()
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error))
    } finally {
      setBusy(null)
    }
  }

  async function toggleHooks(agent: AgentKey) {
    const info = hooks?.hooks?.[agent]
    if (!info) return
    const action = info.installed ? 'uninstall' : 'install'
    if (
      action === 'uninstall' &&
      !window.confirm(`卸载 ${agentMeta[agent].name} 的状态灯钩子？`)
    ) {
      return
    }
    setBusy(`hook-${agent}`)
    const toastId = toast.loading(action === 'install' ? '正在安装钩子…' : '正在卸载钩子…')
    try {
      await api.hooksAction(agent, action)
      toast.success(action === 'install' ? '钩子已安装' : '钩子已卸载', { id: toastId })
      onRefreshHooks()
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    } finally {
      setBusy(null)
    }
  }

  async function setAutostart(enabled: boolean) {
    setLocalAutostart(enabled)
    try {
      await api.agentAutostart(enabled)
      toast.success(enabled ? '服务启动时将自动开启状态灯' : '已关闭自动开启')
      onRefreshHooks()
    } catch (error) {
      setLocalAutostart(!enabled)
      toast.error(String(error instanceof Error ? error.message : error))
    }
  }

  return (
    <div className="page-stack page-enter">
      <div className="page-intro">
        <div>
          <div className="eyebrow">AGENT SIGNAL / CLAUDE CODE + CODEX</div>
          <h1>编程状态灯</h1>
          <p>把两个 Agent 的工作状态投射到长条屏左右两侧，不需要切换窗口。</p>
        </div>
        <div className="intro-actions">
          <StatusPill tone={strip?.mode === 'agent' ? 'mint' : 'neutral'} pulse={strip?.mode === 'agent'}>
            {strip?.mode === 'agent' ? '状态灯运行中' : '状态灯未开启'}
          </StatusPill>
          <Button variant="primary" icon={Zap} busy={busy === 'start'} onClick={startAgent}>
            开启
          </Button>
          <Button variant="ghost" onClick={stopAgent} busy={busy === 'stop'}>
            停止
          </Button>
        </div>
      </div>

      <div className="agent-page-grid">
        {(['claude', 'codex'] as AgentKey[]).map((key) => {
          const meta = agentMeta[key]
          const status = strip?.agents?.[key]
          const state = status?.state || 'idle'
          const hook = hooks?.hooks?.[key]
          const Icon = meta.icon
          const installed = hook ? hook.installed >= hook.total : false
          const partial = hook ? hook.installed > 0 && hook.installed < hook.total : false
          return (
            <Card key={key} className={`agent-page-card agent-page-${state}`} accent="none">
              <div className="agent-card-top">
                <div className="agent-identity">
                  <span className={`agent-emblem agent-emblem-${state}`}>
                    <Icon size={22} />
                  </span>
                  <div>
                    <span className="agent-short">{meta.short}</span>
                    <h2>{meta.name}</h2>
                  </div>
                </div>
                <span className={`agent-state-badge agent-state-${state}`}>
                  <i />
                  {stateLabels[state]}
                </span>
              </div>

              <div className="agent-big-state">
                <span>{stateLabels[state]}</span>
                <strong>{status?.sessions.length || 0}</strong>
                <small>个活跃会话</small>
              </div>

              <div className="agent-wave" aria-hidden="true">
                {Array.from({ length: 24 }).map((_, index) => (
                  <i key={index} style={{ animationDelay: `${index * 38}ms` }} />
                ))}
              </div>

              <div className="agent-meta-grid">
                <div>
                  <span>状态含义</span>
                  <strong>{stateHints[state]}</strong>
                </div>
                <div>
                  <span>最近事件</span>
                  <strong>{hook?.last_event || '暂无'}</strong>
                </div>
                <div>
                  <span>时间</span>
                  <strong>{ago(hook?.last_ago ?? null)}</strong>
                </div>
              </div>

              <div className="hook-row">
                <div className="hook-info">
                  {hook?.installed ? (
                    <CircleCheck size={17} className="hook-ok" />
                  ) : (
                    <Unplug size={17} className="muted-icon" />
                  )}
                  <div>
                    <strong>
                      {installed
                        ? '钩子已安装'
                        : partial
                          ? `部分安装 ${hook?.installed}/${hook?.total}`
                          : '钩子未安装'}
                    </strong>
                    <span>{meta.detail}</span>
                  </div>
                </div>
                <Button
                  variant={hook?.installed ? 'ghost' : 'secondary'}
                  size="sm"
                  busy={busy === `hook-${key}`}
                  onClick={() => toggleHooks(key)}
                >
                  {hook?.installed ? '卸载' : '安装钩子'}
                </Button>
              </div>

              {key === 'codex' && hook && hook.trusted != null && hook.trusted < hook.total && (
                <div className="trust-note">
                  <ShieldCheck size={15} />
                  <span>
                    已安装 {hook.installed}/{hook.total}，Codex 已信任 {hook.trusted}/{hook.total}。
                    新钩子需要在 Codex 里执行 <code>/hooks</code> 并选择 Trust all。
                  </span>
                </div>
              )}
            </Card>
          )
        })}
      </div>

      <div className="agent-bottom-grid">
        <Card>
          <CardHeader
            eyebrow="BEHAVIOR"
            title="常驻行为"
            detail="本地服务启动后自动点亮状态灯"
            action={<Bot size={18} className="muted-icon" />}
          />
          <div className="setting-line">
            <div>
              <strong>服务启动时自动开启</strong>
              <span>桌面应用常驻或重启后端后，自动切到编程状态灯。</span>
            </div>
            <Toggle checked={localAutostart} onCheckedChange={setAutostart} />
          </div>
          <div className="section-divider" />
          <div className="legend-grid">
            <div><i className="legend-working" /><strong>黄色流水</strong><span>Agent 正在工作</span></div>
            <div><i className="legend-waiting" /><strong>红色闪烁</strong><span>等待权限确认</span></div>
            <div><i className="legend-done" /><strong>绿色常亮</strong><span>本轮任务完成</span></div>
          </div>
        </Card>

        <Card>
          <CardHeader
            eyebrow="HOW IT WORKS"
            title="工作方式"
            detail="钩子只转发事件，不阻塞 Agent"
            action={<CircleHelp size={18} className="muted-icon" />}
          />
          <div className="how-list">
            <div>
              <span>01</span>
              <p>安装钩子后，Agent 会把事件 JSON 转发到本地 8655 端口。</p>
            </div>
            <div>
              <span>02</span>
              <p>服务按会话计算最紧急状态，左右各占 31 列灯珠。</p>
            </div>
            <div>
              <span>03</span>
              <p>实时帧每 0.25 秒补发一次，不写 flash，不损伤键盘存储。</p>
            </div>
          </div>
          <div className="notice">
            <LoaderCircle size={15} />
            <span>如果钩子没有触发，请确认服务正在运行，并重新信任 Codex hooks。</span>
          </div>
        </Card>
      </div>
    </div>
  )
}
