import { apiClient } from './api'
import type { ThemeListResponse } from '@/types/theme'

export const themeService = {
  list(): Promise<ThemeListResponse> {
    return apiClient.get<ThemeListResponse>('/themes')
  }
}
