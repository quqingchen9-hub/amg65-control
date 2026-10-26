import {
  Cable,
  Check,
  ExternalLink,
  FileText,
  HardDrive,
  Info,
  Keyboard,
  LogIn,
  Menu,
  Power,
  ShieldCheck,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { API_BASE } from '../api'
import { Button, Card, CardHeader, StatusPill, Toggle } from '../components'
import type { DesktopInfo, DeviceStatus } from '../types'

export default function SettingsPage({
  info,
  device,
  serviceOnline,
  launchAtLogin,
  onLaunchAtLogin,
}: {
  info: DesktopInfo | null
  device: DeviceStatus | null
  serviceOnline: boolean
  launchAtLogin: boolean
  onLaunchAtLogin: (enabled: boolean) => Promise<void>
}) {
  const [busy, setBusy] = useState(false)
  const bridge = window.amg65Desktop

  async function changeLaunchAtLogin(enabled: boolean) {
    setBusy(true)
    try {
      await onLaunchAtLogin(enabled)
      toast.success(enabled ? '已加入登录项' : '已从登录项移除')
    } catch (error) {
      toast.error(String(error instanceof Error ? error.message : error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-stack page-enter">
      <div className="page-intro">
        <div>
          <div className="eyebrow">APPLICATION / PREFERENCES</div>
          <h1>设置与关于</h1>
          <p>桌面壳负责常驻、托盘和开机启动；USB 协议仍由本地 Python 服务处理。</p>
        </div>
        <StatusPill tone={serviceOnline ? 'good' : 'bad'} pulse={serviceOnline}>
          {serviceOnline ? '本地服务正常' : '本地服务异常'}
        </StatusPill>
      </div>

      <div className="settings-grid">
        <Card>
          <CardHeader
            eyebrow="STARTUP & RESIDENCY"
            title="启动与常驻"
            detail="像 Magpie 一样待在菜单栏，而不是占用 Dock"
            action={<Menu size={18} className="muted-icon" />}
          />
          <div className="setting-line">
            <div className="setting-icon"><LogIn size={18} /></div>
            <div>
              <strong>登录时自动启动</strong>
              <span>开机后静默启动，不主动弹出控制台。</span>
            </div>
            <Toggle
              checked={launchAtLogin}
              onCheckedChange={changeLaunchAtLogin}
              disabled={!bridge || busy}
            />
          </div>
          <div className="setting-line">
            <div className="setting-icon"><Menu size={18} /></div>
            <div>
              <strong>关闭窗口后继续运行</strong>
              <span>点击窗口关闭按钮只会隐藏窗口，本地服务和长条屏常驻。</span>
            </div>
            <span className="locked-pill"><Check size={12} /> 始终开启</span>
          </div>
          <div className="setting-line">
            <div className="setting-icon"><Power size={18} /></div>
            <div>
              <strong>菜单栏快捷操作</strong>
              <span>托盘菜单可直接打开控制台、开启状态灯或停止长条屏。</span>
            </div>
            <span className="muted-text">可用</span>
          </div>
          {!bridge && (
            <div className="notice notice-warn">
              <Info size={15} />
              <span>当前在浏览器预览中运行，登录项与托盘控制只在桌面应用内可用。</span>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader
            eyebrow="CONNECTION"
            title="连接状态"
            detail="配置通道必须通过 USB 有线连接"
            action={<Cable size={18} className="muted-icon" />}
          />
          <div className="info-list">
            <div>
              <span>键盘</span>
              <strong className={device?.ok ? 'text-good' : 'text-warn'}>
                {device?.ok ? 'LEOBOG AMG65 · 在线' : device?.error || '等待连接'}
              </strong>
            </div>
            <div>
              <span>本地 API</span>
              <code>{API_BASE}</code>
            </div>
            <div>
              <span>小屏分辨率</span>
              <strong>240 × 135 / RGB565</strong>
            </div>
            <div>
              <span>长条屏</span>
              <strong>63 × 5 / 315 LED</strong>
            </div>
          </div>
          <div className="notice">
            <Keyboard size={15} />
            <span>蓝牙模式下键盘不会暴露 0x0C45:0x800A 配置接口，请切换为 USB 有线。</span>
          </div>
        </Card>

        <Card>
          <CardHeader
            eyebrow="RUNTIME"
            title="运行环境"
            detail="打包后的服务与前端均在本机运行"
            action={<HardDrive size={18} className="muted-icon" />}
          />
          <div className="info-list">
            <div>
              <span>应用版本</span>
              <strong>{info?.version || '1.1.0'}</strong>
            </div>
            <div>
              <span>运行模式</span>
              <strong>{info?.packaged ? '打包应用' : '开发模式'}</strong>
            </div>
            <div>
              <span>后端进程</span>
              <strong>{info?.backendOwned ? '由桌面应用托管' : '复用已有服务'}</strong>
            </div>
            <div>
              <span>数据目录</span>
              <code className="path-code">{info?.userData || '~/Library/Application Support/AMG65 Control'}</code>
            </div>
          </div>
          <div className="button-row">
            <Button
              variant="secondary"
              icon={FileText}
              disabled={!bridge}
              onClick={() => bridge?.openLogs()}
            >
              打开后端日志
            </Button>
            <Button
              variant="ghost"
              icon={ExternalLink}
              disabled={!bridge}
              onClick={() => bridge?.hideWindow()}
            >
              隐藏到菜单栏
            </Button>
          </div>
        </Card>

        <Card className="about-card">
          <CardHeader
            eyebrow="ABOUT"
            title="AMG65 Control"
            detail="A local-first hardware console for macOS"
            action={<ShieldCheck size={18} className="muted-icon" />}
          />
          <div className="about-mark">
            <span>AMG</span>
            <strong>CONTROL</strong>
            <i />
          </div>
          <p className="about-copy">
            官方只有 Windows 驱动。本项目通过逆向 DeviceDriver.exe 1.0.3.3
            还原 USB 协议，在 macOS 上实现小屏与长条屏的完整控制。
          </p>
          <div className="about-facts">
            <span>本地传输</span>
            <span>不依赖云端</span>
            <span>菜单栏常驻</span>
            <span>开机自启动</span>
          </div>
        </Card>
      </div>
    </div>
  )
}
