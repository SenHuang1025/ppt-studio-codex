<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { SelectOption } from 'naive-ui'
import { NButton, NSkeleton, useMessage } from 'naive-ui'
import LLMSettings from '@/components/settings/LLMSettings.vue'
import StorageSettings from '@/components/settings/StorageSettings.vue'
import ThemeSettings from '@/components/settings/ThemeSettings.vue'
import GlassPanel from '@/components/common/GlassPanel.vue'
import { settingsService } from '@/services/settingsService'
import type { AppTheme, LLMProvider, SettingsFormState, SettingsResponse } from '@/types/settings'

type SettingsSectionKey = 'llm' | 'storage' | 'theme'

interface SettingsSection {
  description: string
  key: SettingsSectionKey
  label: string
  short: string
}

const message = useMessage()
const sections: SettingsSection[] = [
  {
    description: 'Provider、模型名称、API Base URL、API Key 安全存储与 Planner 思辨增强开关',
    key: 'llm',
    label: '模型设置',
    short: '模'
  },
  {
    description: '应用壳体默认主题占位',
    key: 'theme',
    label: '默认主题',
    short: '题'
  },
  {
    description: '展示当前本地项目存储目录',
    key: 'storage',
    label: '存储路径',
    short: '存'
  }
]
const activeSection = ref<SettingsSectionKey>('llm')
const loading = ref<boolean>(true)
const saving = ref<boolean>(false)
const loadError = ref<string | null>(null)
const hasStoredApiKey = ref<boolean>(false)
const storagePath = ref<string>('')

const providerOptions: SelectOption[] = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: '自定义兼容 OpenAI', value: 'openai_compatible' }
]

const themeOptions: SelectOption[] = [
  { label: '暖纸工作台', value: 'warm-paper' },
  { label: '松绿浅色', value: 'soft-forest' }
]

const form = reactive<SettingsFormState>({
  apiBaseUrl: 'https://api.openai.com/v1',
  apiKey: '',
  defaultTheme: 'warm-paper',
  llmProvider: 'openai',
  modelName: 'gpt-5.2',
  multiAgentDeliberationEnabled: false
})

const activeSectionMeta = computed<SettingsSection>(() => {
  return sections.find((section) => section.key === activeSection.value) ?? sections[0]
})
const modelSuggestions = computed<string[]>(() => {
  switch (form.llmProvider) {
    case 'anthropic':
      return ['claude-sonnet-4-20250514', 'claude-3-7-sonnet-latest']
    case 'openai_compatible':
      return ['gpt-5.2', 'claude-sonnet-4-20250514', 'your-model-name']
    case 'openai':
    default:
      return ['gpt-5.2', 'gpt-5.1', 'gpt-4o']
  }
})

onMounted(() => {
  void loadSettings()
})

async function loadSettings(): Promise<void> {
  loading.value = true
  loadError.value = null

  try {
    const [settings, apiKey] = await Promise.all([settingsService.get(), settingsService.getApiKey()])
    applyLoadedSettings(settings, apiKey)
  } catch (error: unknown) {
    loadError.value = resolveErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function handleSave(): Promise<void> {
  saving.value = true

  try {
    const pendingApiKey = form.apiKey
    const savedSettings = await settingsService.update({
      api_base_url: form.apiBaseUrl.trim(),
      default_theme: form.defaultTheme,
      llm_provider: form.llmProvider,
      model_name: form.modelName.trim(),
      multi_agent_deliberation_enabled: form.multiAgentDeliberationEnabled
    })

    try {
      await settingsService.saveApiKey(pendingApiKey)
    } catch (error: unknown) {
      const persistedApiKey = await settingsService.getApiKey().catch(() => null)
      applyLoadedSettings(savedSettings, persistedApiKey)
      throw new Error(`非敏感设置已保存，但 API Key 安全存储失败：${resolveErrorMessage(error)}`)
    }

    const persistedApiKey = await settingsService.getApiKey()
    applyLoadedSettings(savedSettings, persistedApiKey)
    message.success('设置已保存。')
  } catch (error: unknown) {
    message.error(resolveErrorMessage(error))
  } finally {
    saving.value = false
  }
}

function applyLoadedSettings(settings: SettingsResponse, apiKey: string | null): void {
  form.llmProvider = settings.llm_provider
  form.modelName = settings.model_name
  form.apiBaseUrl = settings.api_base_url
  form.defaultTheme = settings.default_theme
  form.multiAgentDeliberationEnabled = settings.multi_agent_deliberation_enabled
  form.apiKey = apiKey ?? ''

  storagePath.value = settings.storage_path
  hasStoredApiKey.value = Boolean(apiKey && apiKey.trim())
}

function clearApiKeyInput(): void {
  form.apiKey = ''
}

function resolveErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }

  return '设置读取或保存失败，请确认 Electron 与 Python Sidecar 已就绪。'
}

function updateProvider(value: LLMProvider): void {
  form.llmProvider = value
}

function updateTheme(value: AppTheme): void {
  form.defaultTheme = value
}
</script>

<template>
  <section class="grid min-h-[calc(100vh-3rem)] place-items-center py-6">
    <GlassPanel variant="strong" class="w-full max-w-[1180px] p-5 md:p-6">
      <div class="mb-5">
        <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">独立路由页面</p>
        <h1 class="m-0 text-3xl font-semibold">设置工作台</h1>
        <p class="mt-3 max-w-[44rem] text-sm leading-7 text-[color:var(--app-text-secondary)]">
          Settings 页面现在已经接通真实读写链路：非敏感配置走 FastAPI `/api/settings`，API Key 走 Electron `safeStorage`，存储路径先做真实展示与后续入口占位。
        </p>
      </div>

      <div class="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-3">
          <button
            v-for="section in sections"
            :key="section.key"
            class="mb-2 flex w-full items-center justify-between rounded-[var(--radius-lg)] border px-4 py-3 text-left text-sm transition duration-250"
            :class="
              activeSection === section.key
                ? 'border-[color:var(--app-primary-ring)] bg-[color:var(--app-primary-soft)] text-[color:var(--primary-300)] shadow-[var(--shadow-highlight)]'
                : 'border-transparent text-[color:var(--app-text-secondary)] hover:border-[color:var(--app-border-subtle)] hover:bg-[color:var(--surface-editor)] hover:text-[color:var(--primary-300)]'
            "
            type="button"
            @click="activeSection = section.key"
          >
            <span>{{ section.label }}</span>
            <span class="mono-meta text-[10px]">{{ section.short }}</span>
          </button>
        </aside>

        <section class="workspace-solid rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] p-6">
          <div class="mb-5 border-b border-[color:var(--app-border-subtle)] pb-5">
            <div class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">{{ activeSectionMeta.label }}</div>
            <div class="text-sm leading-7 text-[color:var(--app-text-secondary)]">
              {{ activeSectionMeta.description }}
            </div>
          </div>

          <div v-if="loading" class="space-y-4">
            <NSkeleton :sharp="false" height="18px" width="32%" />
            <NSkeleton :sharp="false" height="42px" />
            <NSkeleton :sharp="false" height="42px" />
            <NSkeleton :sharp="false" height="120px" />
          </div>

          <div v-else-if="loadError" class="space-y-4">
            <div class="rounded-[var(--radius-xl)] border border-[rgba(183,91,53,0.16)] bg-[rgba(255,248,237,0.82)] p-5">
              <div class="mono-meta mb-2 text-[10px] text-[color:#9f4b2a]">设置加载失败</div>
              <div class="text-sm leading-7 text-[color:var(--app-text-secondary)]">{{ loadError }}</div>
            </div>
            <div class="flex gap-3">
              <NButton secondary strong @click="loadSettings">重新读取</NButton>
            </div>
          </div>

          <template v-else>
            <LLMSettings
              v-if="activeSection === 'llm'"
              :api-base-url="form.apiBaseUrl"
              :api-key="form.apiKey"
              :has-stored-api-key="hasStoredApiKey"
              :model-name="form.modelName"
              :model-suggestions="modelSuggestions"
              :multi-agent-deliberation-enabled="form.multiAgentDeliberationEnabled"
              :provider="form.llmProvider"
              :provider-options="providerOptions"
              @clear-api-key="clearApiKeyInput"
              @update:api-base-url="(value) => (form.apiBaseUrl = value)"
              @update:api-key="(value) => (form.apiKey = value)"
              @update:model-name="(value) => (form.modelName = value)"
              @update:multi-agent-deliberation-enabled="(value) => (form.multiAgentDeliberationEnabled = value)"
              @update:provider="updateProvider"
            />

            <ThemeSettings
              v-else-if="activeSection === 'theme'"
              :theme="form.defaultTheme"
              :theme-options="themeOptions"
              @update:theme="updateTheme"
            />

            <StorageSettings v-else :storage-path="storagePath" />

            <div class="mt-6 flex flex-wrap gap-3">
              <NButton secondary strong :disabled="saving" @click="loadSettings">重新读取</NButton>
              <NButton type="primary" :loading="saving" @click="handleSave">保存设置</NButton>
            </div>
          </template>
        </section>
      </div>
    </GlassPanel>
  </section>
</template>
