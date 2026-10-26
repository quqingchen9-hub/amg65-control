import * as SwitchPrimitive from '@radix-ui/react-switch'
import * as SliderPrimitive from '@radix-ui/react-slider'
import {
  Check,
  FileImage,
  LoaderCircle,
  UploadCloud,
  X,
  type LucideIcon,
} from 'lucide-react'
import {
  type ButtonHTMLAttributes,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react'

export function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ')
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  icon?: LucideIcon
  busy?: boolean
}

export function Button({
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  busy = false,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cx('btn', `btn-${variant}`, `btn-${size}`, className)}
      disabled={disabled || busy}
      {...props}
    >
      {busy ? (
        <LoaderCircle size={15} className="spin" />
      ) : Icon ? (
        <Icon size={15} strokeWidth={1.8} />
      ) : null}
      <span>{children}</span>
    </button>
  )
}

export function Card({
  children,
  className,
  accent,
}: {
  children: ReactNode
  className?: string
  accent?: 'mint' | 'orange' | 'none'
}) {
  return <section className={cx('card', accent && `card-${accent}`, className)}>{children}</section>
}

export function CardHeader({
  eyebrow,
  title,
  detail,
  action,
}: {
  eyebrow?: string
  title: string
  detail?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="card-head">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
        {detail && <p className="card-detail">{detail}</p>}
      </div>
      {action && <div className="card-action">{action}</div>}
    </div>
  )
}

export function StatusPill({
  tone = 'neutral',
  children,
  pulse = false,
}: {
  tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'mint'
  children: ReactNode
  pulse?: boolean
}) {
  return (
    <span className={cx('status-pill', `status-${tone}`)}>
      <span className={cx('status-dot', pulse && 'pulse')} />
      {children}
    </span>
  )
}

export function Toggle({
  checked,
  onCheckedChange,
  disabled,
}: {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  disabled?: boolean
}) {
  return (
    <SwitchPrimitive.Root
      className="switch-root"
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
    >
      <SwitchPrimitive.Thumb className="switch-thumb" />
    </SwitchPrimitive.Root>
  )
}

export function Range({
  value,
  min,
  max,
  step,
  onValueChange,
}: {
  value: number
  min: number
  max: number
  step: number
  onValueChange: (value: number) => void
}) {
  return (
    <SliderPrimitive.Root
      className="slider-root"
      value={[value]}
      min={min}
      max={max}
      step={step}
      onValueChange={([next]) => onValueChange(next)}
    >
      <SliderPrimitive.Track className="slider-track">
        <SliderPrimitive.Range className="slider-range" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb className="slider-thumb" aria-label="帧间隔" />
    </SliderPrimitive.Root>
  )
}

function paintScreenPlaceholder(canvas: HTMLCanvasElement) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const { width, height } = canvas
  ctx.imageSmoothingEnabled = false
  ctx.fillStyle = '#050707'
  ctx.fillRect(0, 0, width, height)
  ctx.strokeStyle = 'rgba(126, 229, 196, 0.09)'
  ctx.lineWidth = 1
  for (let x = 0; x < width; x += 12) {
    ctx.beginPath()
    ctx.moveTo(x + 0.5, 0)
    ctx.lineTo(x + 0.5, height)
    ctx.stroke()
  }
  for (let y = 0; y < height; y += 12) {
    ctx.beginPath()
    ctx.moveTo(0, y + 0.5)
    ctx.lineTo(width, y + 0.5)
    ctx.stroke()
  }
  ctx.fillStyle = 'rgba(126, 229, 196, 0.65)'
  ctx.font = '600 10px "SFMono-Regular", monospace'
  ctx.textAlign = 'center'
  ctx.fillText('AMG65 · READY', width / 2, height / 2 + 4)
}

function paintStripPlaceholder(canvas: HTMLCanvasElement) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const { width, height } = canvas
  ctx.imageSmoothingEnabled = false
  ctx.fillStyle = '#040606'
  ctx.fillRect(0, 0, width, height)
  const dot = width / 63
  for (let row = 0; row < 5; row += 1) {
    for (let col = 0; col < 63; col += 1) {
      const active = (row + col) % 9 < 2
      ctx.fillStyle = active ? 'rgba(126, 229, 196, 0.55)' : 'rgba(255,255,255,0.035)'
      ctx.fillRect(col * dot + 1, row * (height / 5) + 1, dot - 2, height / 5 - 2)
    }
  }
}

export function ScreenCanvas({
  src,
  variant = 'lcd',
  className,
}: {
  src?: string
  variant?: 'lcd' | 'strip'
  className?: string
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    if (!src) {
      if (variant === 'lcd') paintScreenPlaceholder(canvas)
      else paintStripPlaceholder(canvas)
      return
    }
    const image = new Image()
    image.onload = () => {
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.imageSmoothingEnabled = false
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
    }
    image.src = src
  }, [src, variant])

  return (
    <div className={cx('screen-bezel', `screen-${variant}`, className)}>
      <canvas
        ref={canvasRef}
        width={variant === 'lcd' ? 240 : 504}
        height={variant === 'lcd' ? 135 : 40}
        className="screen-canvas"
      />
      <span className="bezel-screw screw-a" />
      <span className="bezel-screw screw-b" />
      <span className="bezel-label">{variant === 'lcd' ? 'LCD · 240×135' : 'MATRIX · 63×5'}</span>
    </div>
  )
}

export function FileDrop({
  accept,
  file,
  onFile,
  label,
  hint,
}: {
  accept: string
  file: File | null
  onFile: (file: File | null) => void
  label: string
  hint: string
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  return (
    <div
      className={cx('file-drop', dragging && 'is-dragging', file && 'has-file')}
      onClick={() => inputRef.current?.click()}
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        const next = event.dataTransfer.files?.[0]
        if (next) onFile(next)
      }}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click()
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        onChange={(event) => onFile(event.target.files?.[0] || null)}
      />
      <div className="file-drop-icon">
        {file ? <FileImage size={22} /> : <UploadCloud size={22} />}
      </div>
      <div className="file-drop-copy">
        <strong>{file ? file.name : label}</strong>
        <span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · 点击替换` : hint}</span>
      </div>
      {file ? (
        <button
          className="icon-button"
          type="button"
          aria-label="移除文件"
          onClick={(event) => {
            event.stopPropagation()
            onFile(null)
          }}
        >
          <X size={15} />
        </button>
      ) : (
        <span className="drop-action">选择文件</span>
      )}
    </div>
  )
}

export function CheckLine({ children }: { children: ReactNode }) {
  return (
    <div className="check-line">
      <span>
        <Check size={11} strokeWidth={2.4} />
      </span>
      <div>{children}</div>
    </div>
  )
}

export function Field({
  label,
  children,
  wide,
}: {
  label: string
  children: ReactNode
  wide?: boolean
}) {
  return (
    <label className={cx('field', wide && 'field-wide')}>
      <span>{label}</span>
      {children}
    </label>
  )
}

export function ColorField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <label className="color-field">
      <span>{label}</span>
      <span className="color-control">
        <input type="color" value={value} onChange={(event) => onChange(event.target.value)} />
        <code>{value.toUpperCase()}</code>
      </span>
    </label>
  )
}
