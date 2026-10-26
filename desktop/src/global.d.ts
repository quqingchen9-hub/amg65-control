import type { DesktopBridge } from './types'

declare global {
  interface Window {
    amg65Desktop?: DesktopBridge
  }
}

export {}
