export const LLM_PROVIDER_VALUES = ['openai', 'anthropic', 'openai_compatible'] as const

export type LLMProvider = (typeof LLM_PROVIDER_VALUES)[number]

export const APP_THEME_VALUES = ['warm-paper', 'soft-forest'] as const

export type AppTheme = (typeof APP_THEME_VALUES)[number]

export interface SettingsResponse {
  llm_provider: LLMProvider
  model_name: string
  api_base_url: string
  multi_agent_deliberation_enabled: boolean
  default_theme: AppTheme
  storage_path: string
}

export interface SettingsUpdatePayload {
  llm_provider?: LLMProvider
  model_name?: string
  api_base_url?: string
  multi_agent_deliberation_enabled?: boolean
  default_theme?: AppTheme
}

export interface SettingsFormState {
  apiBaseUrl: string
  apiKey: string
  defaultTheme: AppTheme
  llmProvider: LLMProvider
  modelName: string
  multiAgentDeliberationEnabled: boolean
}
