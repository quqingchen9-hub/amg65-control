import { Clock3, ImagePlus, MonitorUp, Palette, Type } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { api } from '../api'
import {
  Button,
  Card,
  CardHeader,
  ColorField,
  Field,
  FileDrop,
  ScreenCanvas,
  StatusPill,
} from '../components'
import type { DeviceStatus } from '../types'

export default function LcdPage({ device }: { device: DeviceStatus | null }) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string>()
  const [fps, setFps] = useState(12)
  const [maxFrames, setMaxFrames] = useState(130)
  const [text, setText] = useState('HELLO')
  const [fgColor, setFgColor] = useState('#ffd66b')
  const [bgColor, setBgColor] = useState('#101416')
  const [solidColor, setSolidColor] = useState('#ff8a5b')
  const [fontSize, setFontSize] = useState(64)
  const [busy, setBusy] = useState<string | null>(null)

  async function uploadFile() {
    if (!file) {
      toast.error('请先选择图片或 GIF')
      return
    }
    const isGif = file.type === 'image/gif' || /\.gif$/i.test(file.name)
    setBusy('file')
    const toastId = toast.loading(isGif ? '正在解析并上传 GIF…' : '正在上传图片…')
    try {
      const result = await api.uploadScreen(file, isGif ? 'gif' : 'image', fps, maxFrames)
      if (result.preview) setPreview(result.preview)
      toast.success(
        `${isGif ? '动画' : '图片'}已上屏${result.frames ? ` · ${result.frames} 帧` : ''}`,
        { id: toastId },
      )
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    } finally {
      setBusy(null)
    }
  }

  async function uploadText() {
    setBusy('text')
    const toastId = toast.loading('正在渲染文字画面…')
    try {
      const result = await api.uploadText(
        text,
        fgColor.slice(1),
        bgColor.slice(1),
        fontSize,
      )
      if (result.preview) setPreview(result.preview)
      toast.success('文字已上屏', { id: toastId })
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    } finally {
      setBusy(null)
    }
  }

  async function fillColor() {
    setBusy('color')
    const toastId = toast.loading('正在填充屏幕…')
    try {
      const result = await api.uploadColor(solidColor.slice(1))
      if (result.preview) setPreview(result.preview)
      toast.success('纯色已上屏', { id: toastId })
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    } finally {
      setBusy(null)
    }
  }

  async function syncTime() {
    setBusy('time')
    const toastId = toast.loading('正在同步键盘时间…')
    try {
      const result = await api.syncTime()
      if (!result.ok) throw new Error('固件未确认校时命令')
      toast.success('时间已同步', { id: toastId })
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error), { id: toastId })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="page-stack page-enter">
      <div className="page-intro">
        <div>
          <div className="eyebrow">SMALL DISPLAY / 240 × 135</div>
          <h1>小屏 LCD 工作台</h1>
          <p>上传图片、GIF、文字或纯色。所有内容会自动裁切并编码成 RGB565。</p>
        </div>
        <StatusPill tone={device?.ok ? 'good' : 'warn'} pulse={!!device?.ok}>
          {device?.ok ? 'USB 已连接' : '等待 USB 有线连接'}
        </StatusPill>
      </div>

      <div className="lcd-layout">
        <Card className="preview-card" accent="mint">
          <CardHeader
            eyebrow="LIVE PREVIEW"
            title="屏幕预览"
            detail="上传后显示最后一帧"
            action={<span className="mono-chip">RGB565 / LE</span>}
          />
          <ScreenCanvas variant="lcd" src={preview} />
          <div className="preview-meta">
            <div>
              <span>分辨率</span>
              <strong>240 × 135</strong>
            </div>
            <div>
              <span>帧上限</span>
              <strong>130</strong>
            </div>
            <div>
              <span>编码</span>
              <strong>RGB565</strong>
            </div>
          </div>
          <div className="notice">
            <Clock3 size={15} />
            <span>大 GIF 上传需要 1–8 分钟，期间请保持 USB 连接稳定。</span>
          </div>
          <Button variant="secondary" icon={Clock3} busy={busy === 'time'} onClick={syncTime}>
            同步系统时间
          </Button>
        </Card>

        <div className="control-stack">
          <Card>
            <CardHeader
              eyebrow="MEDIA"
              title="图片 / GIF"
              detail="GIF 自动抽帧；静态图片自动缩放裁切"
              action={<ImagePlus size={18} className="muted-icon" />}
            />
            <FileDrop
              accept=".gif,.png,.jpg,.jpeg,.webp,.bmp,image/*"
              file={file}
              onFile={setFile}
              label="拖入图片或 GIF"
              hint="PNG / JPG / WebP / GIF"
            />
            <div className="form-grid form-grid-3">
              <Field label="GIF 帧率 FPS">
                <input
                  type="number"
                  min={2}
                  max={50}
                  value={fps}
                  onChange={(event) => setFps(Number(event.target.value))}
                />
              </Field>
              <Field label="最多帧数">
                <input
                  type="number"
                  min={1}
                  max={130}
                  value={maxFrames}
                  onChange={(event) => setMaxFrames(Number(event.target.value))}
                />
              </Field>
              <div className="form-submit">
                <Button
                  variant="primary"
                  icon={MonitorUp}
                  busy={busy === 'file'}
                  onClick={uploadFile}
                >
                  上传到小屏
                </Button>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader
              eyebrow="TYPE & COLOR"
              title="文字 / 纯色"
              detail="用 240 × 135 画布即时渲染"
              action={<Type size={18} className="muted-icon" />}
            />
            <div className="form-grid form-grid-2">
              <Field label="文字内容" wide>
                <input
                  type="text"
                  value={text}
                  placeholder="Hello / 你好"
                  onChange={(event) => setText(event.target.value)}
                />
              </Field>
              <Field label="字号">
                <input
                  type="number"
                  min={12}
                  max={120}
                  value={fontSize}
                  onChange={(event) => setFontSize(Number(event.target.value))}
                />
              </Field>
              <div className="form-submit">
                <Button variant="primary" icon={Type} busy={busy === 'text'} onClick={uploadText}>
                  文字上屏
                </Button>
              </div>
            </div>
            <div className="inline-fields">
              <ColorField label="文字色" value={fgColor} onChange={setFgColor} />
              <ColorField label="背景色" value={bgColor} onChange={setBgColor} />
            </div>
            <div className="section-divider" />
            <div className="inline-fields inline-fields-end">
              <ColorField label="纯色填充" value={solidColor} onChange={setSolidColor} />
              <Button variant="secondary" icon={Palette} busy={busy === 'color'} onClick={fillColor}>
                整屏填充
              </Button>
            </div>
          </Card>
        </div>
      </div>

      <Card className="keyboard-card">
        <CardHeader
          eyebrow="REFERENCE"
          title="AMG65 键位参考"
          detail="数据必须通过 USB 有线连接传输，蓝牙模式不暴露配置接口。"
        />
        <img className="keyboard-image" src="./keyboard.png" alt="LEOBOG AMG65 键位图" />
      </Card>
    </div>
  )
}
