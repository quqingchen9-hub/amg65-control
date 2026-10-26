export type PageId = 'overview' | 'lcd' | 'strip' | 'agent' | 'settings'

export type AgentKey = 'claude' | 'codex'
export type AgentState = 'idle' | 'working' | 'waiting' | 'done'

export interface DeviceStatus {
  ok: boolean
  device?: string
  screen?: [number, number]
  error?: string
}

export interface AgentSession {
  state: AgentState
  cwd: string
  ago: number
}

export interface AgentStatus {
  state: AgentState
  sessions: AgentSession[]
}

export interface SitStatus {
  minutes: number
  active: boolean
  remain: number | null
  color: string
  seconds: number
}

export interface StripStatus {
  mode: string | null
  color: string
  time: string
  sit: SitStatus
  agents: Record<AgentKey, AgentStatus>
}

export interface HookInfo {
  installed: number
  total: number
  trusted: number | null
  last_event: string | null
  last_ago: number | null
}

export interface HooksPayload {
  hooks: Record<AgentKey, HookInfo>
  autostart: boolean
}

export interface Preset {
  name: string
  label: string
}

export interface UploadResult {
  ok: boolean
  frames?: number
  seconds?: number
  preview?: string
  error?: string
}

export interface StripResult extends UploadResult {
  mode?: string | null
}

export interface DesktopInfo {
  version: string
  packaged: boolean
  backendOwned: boolean
  serviceReady: boolean
  userData: string
  logPath: string
}

export interface DesktopBridge {
  platform: string
  getInfo: () => Promise<DesktopInfo>
  getLaunchAtLogin: () => Promise<boolean>
  setLaunchAtLogin: (enabled: boolean) => Promise<boolean>
  hideWindow: () => Promise<void>
  quit: () => Promise<void>
  openLogs: () => Promise<string>
}
