const {
  app,
  BrowserWindow,
  Menu,
  Tray,
  dialog,
  ipcMain,
  nativeImage,
  shell,
} = require('electron')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const PORT = 8655
const API = `http://127.0.0.1:${PORT}`
const isDev = !app.isPackaged

let mainWindow = null
let tray = null
let backend = null
let backendOwned = false
let quitting = false
let logStream = null
let serviceReady = false

app.setName('AMG65 Control')
app.commandLine.appendSwitch('disable-features', 'HardwareMediaKeyHandling')

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => showWindow())
}

function resourcePath(...parts) {
  return path.join(process.resourcesPath, ...parts)
}

function logPath() {
  return path.join(app.getPath('userData'), 'backend.log')
}

function startLog() {
  fs.mkdirSync(app.getPath('userData'), { recursive: true })
  logStream = fs.createWriteStream(logPath(), { flags: 'a' })
  logStream.write(`\n\n===== ${new Date().toISOString()} =====\n`)
}

function ensureHookScript() {
  const source = isDev
    ? path.join(__dirname, '..', '..', 'tool', 'agent_hook.sh')
    : resourcePath('backend', 'agent_hook.sh')
  const target = path.join(app.getPath('userData'), 'agent_hook.sh')
  fs.mkdirSync(path.dirname(target), { recursive: true })
  fs.copyFileSync(source, target)
  fs.chmodSync(target, 0o755)
  return target
}

function backendEnvironment() {
  const env = {
    ...process.env,
    AMG65_PORT: String(PORT),
    AMG65_SETTINGS: path.join(app.getPath('userData'), 'settings.json'),
    AMG65_HOOK_SCRIPT: ensureHookScript(),
    PYTHONUNBUFFERED: '1',
  }
  if (isDev) {
    const presetDatabase = path.join(
      __dirname,
      '..',
      '..',
      'vendor',
      'db',
      'ledlayer_v2.data',
    )
    if (fs.existsSync(presetDatabase)) env.AMG65_PRESET_DB = presetDatabase
  } else {
    const presetDatabase = resourcePath('backend', 'ledlayer_v2.data')
    if (fs.existsSync(presetDatabase)) env.AMG65_PRESET_DB = presetDatabase
    env.DYLD_LIBRARY_PATH = [
      resourcePath('backend'),
      resourcePath('backend', '_internal'),
      process.env.DYLD_LIBRARY_PATH || '',
    ]
      .filter(Boolean)
      .join(':')
  }
  return env
}

async function isServiceReady(timeout = 800) {
  try {
    const response = await fetch(`${API}/api/health`, {
      signal: AbortSignal.timeout(timeout),
    })
    if (!response.ok) return false
    const data = await response.json()
    return data.service === 'amg65-panel'
  } catch {
    return false
  }
}

async function waitForService(seconds = 25) {
  const deadline = Date.now() + seconds * 1000
  while (Date.now() < deadline) {
    if (await isServiceReady(900)) return true
    await new Promise((resolve) => setTimeout(resolve, 300))
  }
  return false
}

async function ensureBackend() {
  if (await isServiceReady()) {
    backendOwned = false
    serviceReady = true
    return
  }

  startLog()
  let command
  let args
  let cwd

  if (isDev) {
    command = process.env.AMG65_PYTHON || 'python3'
    args = [path.join(__dirname, '..', '..', 'panel', 'server.py'), String(PORT)]
    cwd = path.join(__dirname, '..', '..')
  } else {
    const dir = resourcePath('backend')
    command = path.join(dir, 'amg65-backend')
    args = [String(PORT)]
    cwd = dir
  }

  backend = spawn(command, args, {
    cwd,
    env: backendEnvironment(),
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  backendOwned = true
  backend.stdout.pipe(logStream, { end: false })
  backend.stderr.pipe(logStream, { end: false })
  backend.on('exit', (code, signal) => {
    logStream?.write(`\nbackend exited code=${code} signal=${signal}\n`)
    backend = null
    serviceReady = false
  })
  backend.on('error', (error) => {
    logStream?.write(`\nbackend spawn error: ${error.stack || error}\n`)
    backend = null
    serviceReady = false
  })

  serviceReady = await waitForService()
  if (!serviceReady) {
    throw new Error(
      `本地服务未能启动。请查看日志：${logPath()}`,
    )
  }
}

function trayIcon() {
  const iconPath = isDev
    ? path.join(__dirname, '..', 'build', 'trayTemplate.png')
    : resourcePath('trayTemplate.png')
  const image = nativeImage.createFromPath(iconPath)
  image.setTemplateImage(true)
  return image
}

async function stripAction(mode) {
  try {
    await fetch(`${API}/api/strip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    })
  } catch {
    // The window has its own connection state. The tray action is best effort.
  }
}

function rebuildTrayMenu() {
  if (!tray) return
  const launchAtLogin = app.getLoginItemSettings().openAtLogin
  const menu = Menu.buildFromTemplate([
    {
      label: '打开 AMG65 Control',
      click: () => showWindow(),
    },
    { type: 'separator' },
    {
      label: '开启编程状态灯',
      click: () => stripAction('agent'),
    },
    {
      label: '停止长条屏',
      click: () => stripAction('off'),
    },
    { type: 'separator' },
    {
      label: '登录时自动启动',
      type: 'checkbox',
      checked: launchAtLogin,
      click: (item) => setLaunchAtLogin(item.checked),
    },
    {
      label: '打开后端日志',
      click: () => shell.openPath(logPath()),
    },
    { type: 'separator' },
    {
      label: '退出 AMG65 Control',
      accelerator: 'Command+Q',
      click: () => {
        quitting = true
        app.quit()
      },
    },
  ])
  tray.setContextMenu(menu)
}

function createTray() {
  tray = new Tray(trayIcon())
  tray.setToolTip('AMG65 Control')
  tray.on('click', () => showWindow())
  rebuildTrayMenu()
}

function setLaunchAtLogin(enabled) {
  app.setLoginItemSettings({
    openAtLogin: Boolean(enabled),
    openAsHidden: true,
    args: ['--hidden'],
  })
  rebuildTrayMenu()
  return app.getLoginItemSettings().openAtLogin
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 1080,
    minHeight: 700,
    show: false,
    backgroundColor: '#f5f5f7',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 20, y: 21 },
    vibrancy: 'under-window',
    visualEffectState: 'active',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  mainWindow.once('ready-to-show', () => {
    if (!process.argv.includes('--hidden')) mainWindow.show()
  })
  mainWindow.on('close', (event) => {
    if (!quitting) {
      event.preventDefault()
      mainWindow.hide()
    }
  })
  mainWindow.on('closed', () => {
    mainWindow = null
  })
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://') || url.startsWith('http://')) shell.openExternal(url)
    return { action: 'deny' }
  })
}

function showWindow() {
  if (!mainWindow) createWindow()
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.show()
  mainWindow.focus()
}

function buildMenu() {
  Menu.setApplicationMenu(
    Menu.buildFromTemplate([
      {
        label: 'AMG65 Control',
        submenu: [
          { role: 'about' },
          { type: 'separator' },
          { role: 'hide' },
          { role: 'hideOthers' },
          { role: 'unhide' },
          { type: 'separator' },
          {
            label: '退出',
            accelerator: 'Command+Q',
            click: () => {
              quitting = true
              app.quit()
            },
          },
        ],
      },
      { role: 'editMenu' },
      { role: 'windowMenu' },
    ]),
  )
}

ipcMain.handle('app:info', () => ({
  version: app.getVersion(),
  packaged: app.isPackaged,
  backendOwned,
  serviceReady,
  userData: app.getPath('userData'),
  logPath: logPath(),
}))
ipcMain.handle('app:get-launch-at-login', () => app.getLoginItemSettings().openAtLogin)
ipcMain.handle('app:set-launch-at-login', (_event, enabled) => setLaunchAtLogin(enabled))
ipcMain.handle('app:hide-window', () => mainWindow?.hide())
ipcMain.handle('app:quit', () => {
  quitting = true
  app.quit()
})
ipcMain.handle('app:open-logs', () => shell.openPath(logPath()))

app.on('before-quit', () => {
  quitting = true
  if (backend && backendOwned) {
    backend.kill('SIGTERM')
    backend = null
  }
  logStream?.end()
})

app.on('window-all-closed', () => {
  // The menu-bar app intentionally stays alive with no visible windows.
})

app.on('activate', () => showWindow())

app.whenReady().then(async () => {
  app.dock?.hide()
  buildMenu()
  createTray()
  try {
    await ensureBackend()
    createWindow()
  } catch (error) {
    dialog.showErrorBox('AMG65 Control 启动失败', String(error?.message || error))
    app.quit()
  }
})
