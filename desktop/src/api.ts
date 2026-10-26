import type {
  AgentKey,
  DeviceStatus,
  HooksPayload,
  Preset,
  SitStatus,
  StripResult,
  StripStatus,
  UploadResult,
} from './types'

export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) || 'http://127.0.0.1:8655'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: 'no-store',
    ...init,
  })
  const text = await response.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`服务返回了无法解析的数据 (${response.status})`)
  }
  if (!response.ok) {
    const message =
      typeof data === 'object' && data && 'error' in data
        ? String((data as { error: unknown }).error)
        : `请求失败 (${response.status})`
    throw new Error(message)
  }
  return data as T
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export const api = {
  deviceStatus: () => request<DeviceStatus>('/api/status'),
  stripStatus: () => request<StripStatus>('/api/strip/status'),
  presets: () => request<{ presets: Preset[] }>('/api/strip/presets'),
  hooks: () => request<HooksPayload>('/api/agent/hooks'),

  uploadScreen(file: File, kind: 'gif' | 'image', fps: number, max: number) {
    const params = new URLSearchParams({
      kind,
      delay: '100',
      max: String(max),
    })
    if (kind === 'gif') params.set('fps', String(fps))
    return request<UploadResult>(`/api/upload?${params}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: file,
    })
  },

  uploadText(text: string, color: string, bg: string, size: number) {
    return postJson<UploadResult>('/api/upload?kind=text', {
      text,
      color,
      bg,
      size,
      delay: 100,
    })
  },

  uploadColor(rgb: string) {
    return postJson<UploadResult>('/api/upload?kind=color', { rgb, delay: 100 })
  },

  syncTime: () => postJson<{ ok: boolean; acks?: Array<string | null> }>('/api/time', {}),

  strip(mode: string, extra: Record<string, unknown> = {}) {
    return postJson<StripResult>('/api/strip', { mode, ...extra })
  },

  uploadStrip(file: File, kind: 'gif' | 'image') {
    return request<UploadResult>(`/api/strip/upload?kind=${kind}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: file,
    })
  },

  sit(payload: Record<string, unknown>) {
    return postJson<SitStatus & { ok: boolean }>('/api/strip/sit', payload)
  },

  agentAutostart(autostart: boolean) {
    return postJson<{ ok: boolean }>('/api/agent/settings', { autostart })
  },

  hooksAction(agent: AgentKey, action: 'install' | 'uninstall') {
    return postJson<{ ok: boolean; hooks: HooksPayload['hooks'] }>('/api/agent/hooks', {
      agent,
      action,
    })
  },
}
