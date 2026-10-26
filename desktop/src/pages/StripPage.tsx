import {
  CircleStop,
  Clock3,
  Cpu,
  HeartPulse,
  ImagePlus,
  Palette,
  Play,
  Rainbow,
  Sparkles,
  Type,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { api } from '../api'
import {
  Button,
  Card,
  CardHeader,
  ColorField,
  Field,
  FileDrop,
  Range,
  ScreenCanvas,
  StatusPill,
} from '../components'
import type { Preset, StripStatus } from '../types'

const modeNames: Record<string, string> = {
  clock: '时钟',
  cpu: 'CPU / 内存',
  agent: '编程状态灯',
  live: '实时帧',
  static: '静态帧',
}

export default function StripPage({
  status,
  presets,
  onRefresh,
}: {
  status: StripStatus | null
  presets: Preset[]
  onRefresh: () => void
}) {
  const [preview, setPreview] = useState<string>()
  const [color, setColor] = useState('#78e6c7')
  const [text, setText] = useState('HELLO')
  const [file, setFile] = useState<File | null>(null)
  const [delay, setDelay] = useState(80)
  const [sitMinutes, setSitMinutes] = useState(0)
  const [sitColor, setSitColor] = useState('#ff3452')
  const [busy, setBusy] = useState<string | null>(null)

  useEffect(() => {
    if (status?.sit) {
      setSitMinutes(status.sit.minutes)
      setSitColor(status.sit.color)
    }
  }, [status?.sit?.minutes, status?.sit?.color])

  async function run(key: string, task: () => Promise<void>, loading: string) {
    setBusy(key)
    const toastId = toast.loading(loading)
    try {
      await task()
      toast.success('已发送到长条屏', { id: toastId })
      onRefresh()
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    } finally {
      setBusy(null)
    }
  }

  function startClock() {
    return run(
      'clock',
      async () => {
        await api.strip('clock', { color: color.slice(1) })
      },
      '正在启动时钟…',
    )
  }

  function startCpu() {
    return run(
      'cpu',
      async () => {
        await api.strip('cpu', { color: color.slice(1) })
      },
      '正在启动系统监控…',
    )
  }

  function startAgent() {
    return run(
      'agent',
      async () => {
        await api.strip('agent', { color: color.slice(1) })
      },
      '正在启动编程状态灯…',
    )
  }

  function stop() {
    return run(
      'off',
      async () => {
        await api.strip('off')
      },
      '正在停止长条屏…',
    )
  }

  function uploadText() {
    return run(
      'text',
      async () => {
        const result = await api.strip('text', {
          text,
          color: color.slice(1),
        })
        if (result.preview) setPreview(result.preview)
      },
      '正在渲染点阵文字…',
    )
  }

  function uploadColor() {
    return run(
      'color',
      async () => {
        const result = await api.strip('color', { color: color.slice(1) })
        if (result.preview) setPreview(result.preview)
      },
      '正在填充长条屏…',
    )
  }

  function uploadRainbow() {
    return run(
      'rainbow',
      async () => {
        const result = await api.strip('rainbow')
        if (result.preview) setPreview(result.preview)
      },
      '正在上传彩虹动画…',
    )
  }

  function uploadPreset(preset: Preset) {
    return run(
      `preset-${preset.name}`,
      async () => {
        const result = await api.strip('preset', { name: preset.name, delay })
        if (result.preview) setPreview(result.preview)
      },
      `正在上传「${preset.label}」…`,
    )
  }

  function uploadFile() {
    if (!file) {
      toast.error('请先选择图片或 GIF')
      return
    }
    const isGif = file.type === 'image/gif' || /\.gif$/i.test(file.name)
    return run(
      'file',
      async () => {
        const result = await api.uploadStrip(file, isGif ? 'gif' : 'image')
        if (result.preview) setPreview(result.preview)
      },
      isGif ? '正在上传 GIF 动画…' : '正在上传图片…',
    )
  }

  async function updateSit(minutes: number) {
    setSitMinutes(minutes)
    const toastId = toast.loading(minutes ? '正在设置久坐提醒…' : '正在关闭久坐提醒…')
    try {
      await api.sit({ minutes, color: sitColor.slice(1) })
      toast.success(minutes ? `已设置为每 ${minutes} 分钟提醒` : '久坐提醒已关闭', {
        id: toastId,
      })
      onRefresh()
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    }
  }

  async function testSit() {
    const toastId = toast.loading('正在播放久坐提醒…')
    try {
      await api.sit({ action: 'test', seconds: 10, color: sitColor.slice(1) })
      toast.success('提醒已显示 10 秒', { id: toastId })
      onRefresh()
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    }
  }

  async function dismissSit() {
    try {
      await api.sit({ action: 'dismiss' })
      toast.success('已关闭本次提醒')
      onRefresh()
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error))
    }
  }

  const mode = status?.mode ? modeNames[status.mode] || status.mode : '待机'

  return (
    <div className="page-stack page-enter">
      <div className="page-intro">
        <div>
          <div className="eyebrow">LED MATRIX / 63 × 5 / 315 LED</div>
          <h1>长条屏控制台</h1>
          <p>实时内容每秒补发，不写 flash；图片和官方灯效上传一次即可常驻。</p>
        </div>
        <StatusPill tone={status?.mode ? 'mint' : 'neutral'} pulse={!!status?.mode}>
          {status?.mode ? `${mode}运行中` : '当前待机'}
        </StatusPill>
      </div>

      <div className="strip-hero-grid">
        <Card accent="orange" className="strip-preview-card">
          <CardHeader
            eyebrow="MATRIX PREVIEW"
            title="点阵预览"
            detail="逻辑灯序已按硬件灯位重排"
            action={<span className="mono-chip">04 33 / 04 35</span>}
          />
          <ScreenCanvas variant="strip" src={preview} />
          <div className="preview-meta">
            <div>
              <span>当前模式</span>
              <strong>{mode}</strong>
            </div>
            <div>
              <span>实时帧</span>
              <strong>1.0 s</strong>
            </div>
            <div>
              <span>灯珠</span>
              <strong>315</strong>
            </div>
          </div>
          <div className="matrix-guide">
            <div>
              <code>04 33</code>
              <strong>常驻写入</strong>
              <span>图片 / 官方灯效</span>
            </div>
            <div>
              <code>04 35</code>
              <strong>实时补发</strong>
              <span>时钟 / CPU / 状态灯</span>
            </div>
            <div>
              <code>04 F0</code>
              <strong>断电保留</strong>
              <span>仅静态写入时使用</span>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader
            eyebrow="REALTIME"
            title="实时内容"
            detail="不写 flash，停止后约 2.5 秒回到槽 7"
            action={<span className={status?.mode ? 'live-indicator is-live' : 'live-indicator'} />}
          />
          <ColorField label="主色" value={color} onChange={setColor} />
          <div className="action-grid action-grid-2">
            <Button variant="primary" icon={Clock3} busy={busy === 'clock'} onClick={startClock}>
              显示时钟
            </Button>
            <Button variant="primary" icon={Cpu} busy={busy === 'cpu'} onClick={startCpu}>
              CPU / 内存
            </Button>
            <Button variant="secondary" icon={Sparkles} busy={busy === 'agent'} onClick={startAgent}>
              编程状态灯
            </Button>
            <Button variant="ghost" icon={CircleStop} busy={busy === 'off'} onClick={stop}>
              停止长条屏
            </Button>
          </div>
          <div className="section-divider" />
          <div className="form-grid form-grid-2">
            <Field label="点阵文字" wide>
              <input
                type="text"
                value={text}
                maxLength={8}
                onChange={(event) => setText(event.target.value)}
              />
            </Field>
            <div className="form-submit">
              <Button variant="secondary" icon={Type} busy={busy === 'text'} onClick={uploadText}>
                文字上屏
              </Button>
            </div>
          </div>
          <div className="inline-actions">
            <Button variant="ghost" icon={Palette} busy={busy === 'color'} onClick={uploadColor}>
              纯色填充
            </Button>
            <Button variant="ghost" icon={Rainbow} busy={busy === 'rainbow'} onClick={uploadRainbow}>
              彩虹动画
            </Button>
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader
          eyebrow="OFFICIAL PRESETS"
          title="官方预制灯效"
          detail="从官方驱动素材转换，上传后写入灯效槽 6，断电保留"
          action={
            <div className="delay-control">
              <span>帧间隔</span>
              <Range value={delay} min={30} max={200} step={10} onValueChange={setDelay} />
              <code>{delay} ms</code>
            </div>
          }
        />
        {presets.length ? (
          <div className="preset-grid">
            {presets.map((preset) => (
              <button
                key={preset.name}
                className="preset-card"
                disabled={busy === `preset-${preset.name}`}
                onClick={() => uploadPreset(preset)}
              >
                <span className="preset-image">
                  <span className="preset-glyph">
                    {preset.label.slice(0, 1)}
                  </span>
                  {busy === `preset-${preset.name}` ? (
                    <span className="preset-busy">
                      <Play size={18} />
                    </span>
                  ) : (
                    <span className="preset-play">
                      <Play size={14} fill="currentColor" />
                    </span>
                  )}
                </span>
                <span className="preset-copy">
                  <strong>{preset.label}</strong>
                  <small>04 33 常驻</small>
                </span>
              </button>
            ))}
          </div>
        ) : (
          <div className="preset-unavailable">
            官方预制灯效需要本机驱动中的 <code>ledlayer_v2.data</code>，设置
            <code> AMG65_PRESET_DB </code>后重启服务即可启用。
          </div>
        )}
      </Card>

      <div className="strip-bottom-grid">
        <Card>
          <CardHeader
            eyebrow="SIT REMINDER"
            title="久坐提醒"
            detail="到点后 9 颗心闪烁 60 秒"
            action={<HeartPulse size={18} className="muted-icon" />}
          />
          <div className="sit-status-line">
            <span className={status?.sit?.active ? 'sit-heart is-active' : 'sit-heart'}>
              <HeartPulse size={16} />
            </span>
            <div>
              <strong>
                {status?.sit?.active
                  ? '提醒正在显示'
                  : status?.sit?.minutes
                    ? `每 ${status.sit.minutes} 分钟`
                    : '提醒已关闭'}
              </strong>
              <span>
                {status?.sit?.active
                  ? '长条屏正在闪烁心形'
                  : status?.sit?.remain != null
                    ? `下次提醒还有 ${Math.floor(status.sit.remain / 60)} 分 ${String(status.sit.remain % 60).padStart(2, '0')} 秒`
                    : '计时由本地服务负责'}
              </span>
            </div>
          </div>
          <div className="sit-controls">
            <Field label="提醒间隔">
              <select
                value={sitMinutes}
                onChange={(event) => updateSit(Number(event.target.value))}
              >
                <option value={0}>关闭</option>
                <option value={30}>30 分钟</option>
                <option value={45}>45 分钟</option>
                <option value={60}>60 分钟</option>
                <option value={90}>90 分钟</option>
              </select>
            </Field>
            <ColorField label="心形颜色" value={sitColor} onChange={setSitColor} />
            <Button variant="primary" icon={HeartPulse} onClick={testSit}>
              试一下
            </Button>
            <Button variant="ghost" onClick={dismissSit}>
              知道了
            </Button>
          </div>
        </Card>

        <Card>
          <CardHeader
            eyebrow="IMAGE → MATRIX"
            title="图片 / GIF 上屏"
            detail="自动缩放到 63 × 5 点阵"
            action={<ImagePlus size={18} className="muted-icon" />}
          />
          <FileDrop
            accept=".gif,.png,.jpg,.jpeg,.webp,.bmp,image/*"
            file={file}
            onFile={setFile}
            label="拖入图片或 GIF"
            hint="GIF 自动抽帧，最多 100 帧"
          />
          <Button variant="primary" icon={ImagePlus} busy={busy === 'file'} onClick={uploadFile}>
            上传到长条屏
          </Button>
          <p className="footnote">
            上传会占用槽 6 并写入 flash。静态内容只需上传一次，不要高频重复上传。
          </p>
        </Card>
      </div>
    </div>
  )
}
