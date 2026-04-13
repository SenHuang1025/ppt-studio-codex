import path from 'node:path'
import { app, BrowserWindow, ipcMain, shell } from 'electron'
import {
  PYTHON_SIDECAR_GET_BASE_URL_CHANNEL,
  SETTINGS_CLEAR_API_KEY_CHANNEL,
  SETTINGS_GET_API_KEY_CHANNEL,
  SETTINGS_SET_API_KEY_CHANNEL
} from './ipc/channels'
import { SecureSettingsStore } from './services/secure-settings-store'
import { PythonSidecar } from './sidecar/python-manager'

let mainWindow: BrowserWindow | null = null
let isQuitting = false
let isBootstrapped = false
let exitCode = 0

const pythonSidecar = new PythonSidecar()
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
  ipcMain.handle(PYTHON_SIDECAR_GET_BASE_URL_CHANNEL, () => pythonSidecar.getBaseUrl())
  ipcMain.handle(SETTINGS_GET_API_KEY_CHANNEL, () => secureSettingsStore.getApiKey())
  ipcMain.handle(SETTINGS_SET_API_KEY_CHANNEL, (_event, apiKey: string) => secureSettingsStore.setApiKey(apiKey))
  ipcMain.handle(SETTINGS_CLEAR_API_KEY_CHANNEL, () => secureSettingsStore.clearApiKey())
}

async function bootstrap(): Promise<void> {
  registerIpcHandlers()

  await pythonSidecar.start()
  await pythonSidecar.waitForReady()
  isBootstrapped = true
  createWindow()
}

app.whenReady().then(() => {
  void bootstrap().catch(async (error: unknown) => {
    exitCode = 1
    const message = error instanceof Error ? error.message : String(error)
    console.error(`[Main] Failed to bootstrap Electron app: ${message}`)

    try {
      await pythonSidecar.stop()
    } catch (stopError) {
      const stopMessage = stopError instanceof Error ? stopError.message : String(stopError)
      console.error(`[Main] Failed to clean up Python sidecar after bootstrap error: ${stopMessage}`)
    }

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

  void pythonSidecar
    .stop()
    .catch((error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      console.error(`[Main] Failed to stop Python sidecar during shutdown: ${message}`)
    })
    .finally(() => {
      app.exit(exitCode)
    })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
