import { contextBridge, ipcRenderer } from 'electron'
import {
  PYTHON_SIDECAR_GET_BASE_URL_CHANNEL,
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
  getPythonBaseUrl: (): Promise<string> => ipcRenderer.invoke(PYTHON_SIDECAR_GET_BASE_URL_CHANNEL),
  saveApiKey: (apiKey: string): Promise<void> => ipcRenderer.invoke(SETTINGS_SET_API_KEY_CHANNEL, apiKey)
})
