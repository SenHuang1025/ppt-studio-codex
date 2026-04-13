import type { SettingsResponse, SettingsUpdatePayload } from '@/types/settings'
import { apiClient } from './api'

export const settingsService = {
  clearApiKey(): Promise<void> {
    return resolveRuntime().clearApiKey()
  },

  get(): Promise<SettingsResponse> {
    return apiClient.get<SettingsResponse>('/settings')
  },

  getApiKey(): Promise<string | null> {
    return resolveRuntime().getApiKey()
  },

  saveApiKey(apiKey: string): Promise<void> {
    const runtime = resolveRuntime()
    const normalizedApiKey = apiKey.trim()

    if (!normalizedApiKey) {
      return runtime.clearApiKey()
    }

    return runtime.saveApiKey(normalizedApiKey)
  },

  update(payload: SettingsUpdatePayload): Promise<SettingsResponse> {
    return apiClient.put<SettingsResponse>('/settings', {
      body: payload
    })
  }
}

function resolveRuntime(): Window['pptStudio'] {
  if (typeof window === 'undefined' || !window.pptStudio) {
    throw new Error('PPT Studio Electron runtime is unavailable in the current context.')
  }

  return window.pptStudio
}
