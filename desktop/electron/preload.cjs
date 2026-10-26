const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('amg65Desktop', {
  platform: process.platform,
  getInfo: () => ipcRenderer.invoke('app:info'),
  getLaunchAtLogin: () => ipcRenderer.invoke('app:get-launch-at-login'),
  setLaunchAtLogin: (enabled) => ipcRenderer.invoke('app:set-launch-at-login', enabled),
  hideWindow: () => ipcRenderer.invoke('app:hide-window'),
  quit: () => ipcRenderer.invoke('app:quit'),
  openLogs: () => ipcRenderer.invoke('app:open-logs'),
})
