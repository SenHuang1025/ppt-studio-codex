import path from 'node:path'
import { app, BrowserWindow, ipcMain, shell } from 'electron'
import {
  PREVIEW_SERVER_GET_BASE_URL_CHANNEL,
  PREVIEW_SERVER_GET_SLIDES_DIR_CHANNEL,
  PREVIEW_SERVER_GET_STATUS_CHANNEL,
  PREVIEW_SERVER_RECOVER_CHANNEL,
  PYTHON_SIDECAR_GET_BASE_URL_CHANNEL,
  PYTHON_SIDECAR_GET_STATUS_CHANNEL,
  PYTHON_SIDECAR_RECOVER_CHANNEL,
  SETTINGS_CLEAR_API_KEY_CHANNEL,
  SETTINGS_GET_API_KEY_CHANNEL,
  SETTINGS_SET_API_KEY_CHANNEL
} from './ipc/channels'
import { SecureSettingsStore } from './services/secure-settings-store'
import { PythonSidecar } from './sidecar/python-manager'
import { PreviewServerManager } from './sidecar/preview-server-manager'

let mainWindow: BrowserWindow | null = null
let isQuitting = false
let isBootstrapped = false
let exitCode = 0

const previewServerManager = new PreviewServerManager()
const pythonSidecar = new PythonSidecar({
  extraEnv: {
    PPT_STUDIO_PREVIEW_BASE_URL: previewServerManager.getBaseUrl(),
    PPT_STUDIO_PREVIEW_SLIDES_DIR: previewServerManager.getSlidesDir(),
    PPT_STUDIO_PREVIEW_THEME_FILE: previewServerManager.getThemeFile()
  }
})
const secureSettingsStore = new SecureSettingsStore()

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 960,
    minWidth: 1280,
    minHeight: 820,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: '#09090B',
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url)
    return { action: 'deny' }
  })

  const devServerUrl = process.env.ELECTRON_RENDERER_URL

  if (devServerUrl) {
    void mainWindow.loadURL(devServerUrl)
  } else {
    void mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
  }
}

function registerIpcHandlers(): void {
  ipcMain.handle(PREVIEW_SERVER_GET_BASE_URL_CHANNEL, () => previewServerManager.getBaseUrl())
  ipcMain.handle(PREVIEW_SERVER_GET_SLIDES_DIR_CHANNEL, () => previewServerManager.getSlidesDir())
  ipcMain.handle(PREVIEW_SERVER_GET_STATUS_CHANNEL, () => previewServerManager.getStatus())
  ipcMain.handle(PREVIEW_SERVER_RECOVER_CHANNEL, () => previewServerManager.recover())
  ipcMain.handle(PYTHON_SIDECAR_GET_BASE_URL_CHANNEL, () => pythonSidecar.getBaseUrl())
  ipcMain.handle(PYTHON_SIDECAR_GET_STATUS_CHANNEL, () => pythonSidecar.getStatus())
  ipcMain.handle(PYTHON_SIDECAR_RECOVER_CHANNEL, () => pythonSidecar.recover())
  ipcMain.handle(SETTINGS_GET_API_KEY_CHANNEL, () => secureSettingsStore.getApiKey())
  ipcMain.handle(SETTINGS_SET_API_KEY_CHANNEL, (_event, apiKey: string) => secureSettingsStore.setApiKey(apiKey))
  ipcMain.handle(SETTINGS_CLEAR_API_KEY_CHANNEL, () => secureSettingsStore.clearApiKey())
}

async function stopSidecars(): Promise<void> {
  const results = await Promise.allSettled([previewServerManager.stop(), pythonSidecar.stop()])

  results.forEach((result, index) => {
    if (result.status === 'rejected') {
      const sidecarName = index === 0 ? 'preview server' : 'Python sidecar'
      const message = result.reason instanceof Error ? result.reason.message : String(result.reason)
      console.error(`[Main] Failed to stop ${sidecarName}: ${message}`)
    }
  })
}

async function bootstrap(): Promise<void> {
  registerIpcHandlers()

  await Promise.all([previewServerManager.start(), pythonSidecar.start()])
  await Promise.all([previewServerManager.waitForReady(), pythonSidecar.waitForReady()])
  isBootstrapped = true
  createWindow()
}

app.whenReady().then(() => {
  void bootstrap().catch(async (error: unknown) => {
    exitCode = 1
    const message = error instanceof Error ? error.message : String(error)
    console.error(`[Main] Failed to bootstrap Electron app: ${message}`)

    await stopSidecars()
    app.quit()
  })

  app.on('activate', () => {
    if (isBootstrapped && BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('before-quit', (event) => {
  if (isQuitting) {
    return
  }

  isQuitting = true
  event.preventDefault()

  void stopSidecars().finally(() => {
    app.exit(exitCode)
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
