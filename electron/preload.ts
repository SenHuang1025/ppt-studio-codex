import { contextBridge, ipcRenderer } from 'electron'
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

contextBridge.exposeInMainWorld('pptStudio', {
  platform: process.platform,
  versions: {
    chrome: process.versions.chrome,
    electron: process.versions.electron,
    node: process.versions.node
  },
  clearApiKey: (): Promise<void> => ipcRenderer.invoke(SETTINGS_CLEAR_API_KEY_CHANNEL),
  getApiKey: (): Promise<string | null> => ipcRenderer.invoke(SETTINGS_GET_API_KEY_CHANNEL),
  getPreviewBaseUrl: (): Promise<string> => ipcRenderer.invoke(PREVIEW_SERVER_GET_BASE_URL_CHANNEL),
  getPreviewSlidesDir: (): Promise<string> => ipcRenderer.invoke(PREVIEW_SERVER_GET_SLIDES_DIR_CHANNEL),
  getPreviewServerStatus: (): Promise<unknown> => ipcRenderer.invoke(PREVIEW_SERVER_GET_STATUS_CHANNEL),
  getPythonBaseUrl: (): Promise<string> => ipcRenderer.invoke(PYTHON_SIDECAR_GET_BASE_URL_CHANNEL),
  getPythonSidecarStatus: (): Promise<unknown> => ipcRenderer.invoke(PYTHON_SIDECAR_GET_STATUS_CHANNEL),
  recoverPreviewServer: (): Promise<void> => ipcRenderer.invoke(PREVIEW_SERVER_RECOVER_CHANNEL),
  recoverPythonSidecar: (): Promise<void> => ipcRenderer.invoke(PYTHON_SIDECAR_RECOVER_CHANNEL),
  saveApiKey: (apiKey: string): Promise<void> => ipcRenderer.invoke(SETTINGS_SET_API_KEY_CHANNEL, apiKey)
})
