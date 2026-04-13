<script setup lang="ts">
import type { SelectOption } from 'naive-ui'
import { NButton, NForm, NFormItem, NInput, NSelect } from 'naive-ui'
import type { LLMProvider } from '@/types/settings'

defineProps<{
  apiBaseUrl: string
  apiKey: string
  hasStoredApiKey: boolean
  modelName: string
  modelSuggestions: string[]
  provider: LLMProvider
  providerOptions: SelectOption[]
}>()

const emit = defineEmits<{
  'clear-api-key': []
  'update:apiBaseUrl': [value: string]
  'update:apiKey': [value: string]
  'update:modelName': [value: string]
  'update:provider': [value: LLMProvider]
}>()

function updateProvider(value: string | null): void {
  if (value === null) {
    return
  }

  emit('update:provider', value as LLMProvider)
}
</script>

<template>
  <div class="space-y-5">
    <div>
      <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">模型设置</p>
      <h2 class="m-0 text-2xl font-semibold">LLM Provider 与 API 访问配置</h2>
      <p class="mt-3 text-sm leading-7 text-[color:var(--app-text-secondary)]">
        当前阶段只保存 Provider、模型名、Base URL 等非敏感设置。API Key 会单独通过 Electron `safeStorage` 加密保存，不进入后端 SQLite。
      </p>
    </div>

    <NForm label-placement="top">
      <div class="grid gap-4 md:grid-cols-2">
        <NFormItem label="模型提供商">
          <NSelect :options="providerOptions" :value="provider" @update:value="updateProvider" />
        </NFormItem>
        <NFormItem label="模型名称">
          <NInput
            :value="modelName"
            placeholder="例如 gpt-5.2"
            @update:value="(value) => emit('update:modelName', value)"
          />
        </NFormItem>
      </div>

      <div class="mb-4 flex flex-wrap gap-2">
        <button
          v-for="suggestion in modelSuggestions"
          :key="suggestion"
          class="rounded-full border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] px-3 py-1 text-xs text-[color:var(--app-text-secondary)] transition duration-250 hover:border-[color:var(--app-border-strong)] hover:text-[color:var(--primary-300)]"
          type="button"
          @click="emit('update:modelName', suggestion)"
        >
          {{ suggestion }}
        </button>
      </div>

      <NFormItem label="API Base URL">
        <NInput
          :value="apiBaseUrl"
          placeholder="https://api.openai.com/v1"
          @update:value="(value) => emit('update:apiBaseUrl', value)"
        />
      </NFormItem>

      <NFormItem label="API Key">
        <NInput
          :value="apiKey"
          placeholder="保存后会通过 Electron safeStorage 加密写入本机"
          show-password-on="click"
          type="password"
          @update:value="(value) => emit('update:apiKey', value)"
        />
      </NFormItem>
    </NForm>

    <div class="flex flex-wrap items-start justify-between gap-3 rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] p-4">
      <div class="text-sm leading-6 text-[color:var(--app-text-secondary)]">
        <div class="font-medium text-[color:var(--app-text-primary)]">安全存储状态</div>
        <div class="mt-1">
          {{ hasStoredApiKey ? '已从本地安全存储读取 API Key，可直接修改后保存。' : '当前尚未保存 API Key，保存后将通过 Electron safeStorage 加密持久化。' }}
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <NButton quaternary size="small" @click="$emit('clear-api-key')">清空 API Key</NButton>
        <NButton secondary strong disabled size="small">测试连接（后续）</NButton>
      </div>
    </div>
  </div>
</template>
