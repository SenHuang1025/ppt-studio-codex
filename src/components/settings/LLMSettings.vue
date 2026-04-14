<script setup lang="ts">
import type { SelectOption } from 'naive-ui'
import { NButton, NForm, NFormItem, NInput, NSelect, NSwitch } from 'naive-ui'
import type { LLMProvider } from '@/types/settings'

defineProps<{
  apiBaseUrl: string
  apiKey: string
  hasStoredApiKey: boolean
  modelName: string
  modelSuggestions: string[]
  multiAgentDeliberationEnabled: boolean
  provider: LLMProvider
  providerOptions: SelectOption[]
}>()

const emit = defineEmits<{
  'clear-api-key': []
  'update:apiBaseUrl': [value: string]
  'update:apiKey': [value: string]
  'update:modelName': [value: string]
  'update:multiAgentDeliberationEnabled': [value: boolean]
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

      <NFormItem label="多智能体思辨模式">
        <div class="w-full rounded-[var(--radius-xl)] border border-[rgba(104,166,125,0.16)] bg-[rgba(255,248,237,0.88)] p-4 shadow-[var(--shadow-glass-1)]">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <div class="text-sm font-semibold text-[color:var(--app-text-primary)]">多智能体思辨模式</div>
                <span class="rounded-full border border-[rgba(241,143,1,0.2)] bg-[rgba(255,243,226,0.9)] px-2.5 py-0.5 text-[11px] text-[color:var(--accent-200)]">
                  默认关闭
                </span>
              </div>
              <p class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
                规划大纲时启用 Draft -> Critic -> Synthesis 的增强流程。默认关闭，当前仅作用于大纲规划。
              </p>
            </div>

            <div class="flex items-center gap-3 rounded-full border border-[color:var(--app-border-subtle)] bg-[rgba(255,252,247,0.92)] px-3 py-2">
              <span class="text-xs text-[color:var(--app-text-secondary)]">
                {{ multiAgentDeliberationEnabled ? '已开启' : '保持关闭' }}
              </span>
              <NSwitch
                :value="multiAgentDeliberationEnabled"
                @update:value="(value) => emit('update:multiAgentDeliberationEnabled', value)"
              />
            </div>
          </div>

          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <div class="rounded-[var(--radius-lg)] border border-[rgba(104,166,125,0.16)] bg-[rgba(252,248,239,0.92)] px-3 py-3">
              <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--primary-300)]">优点</div>
              <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
                更适合复杂材料、多轮补充、需要更强叙事结构的场景。
              </div>
            </div>

            <div class="rounded-[var(--radius-lg)] border border-[rgba(241,143,1,0.18)] bg-[rgba(255,244,230,0.92)] px-3 py-3">
              <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--accent-200)]">代价</div>
              <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
                响应更慢，模型调用成本更高，但通常能提升大纲结构质量。
              </div>
            </div>
          </div>
        </div>
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
