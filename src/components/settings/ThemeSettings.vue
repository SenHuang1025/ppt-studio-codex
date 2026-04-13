<script setup lang="ts">
import type { SelectOption } from 'naive-ui'
import { NForm, NFormItem, NSelect } from 'naive-ui'
import type { AppTheme } from '@/types/settings'

defineProps<{
  theme: AppTheme
  themeOptions: SelectOption[]
}>()

const emit = defineEmits<{
  'update:theme': [value: AppTheme]
}>()

function updateTheme(value: string | null): void {
  if (value === null) {
    return
  }

  emit('update:theme', value as AppTheme)
}
</script>

<template>
  <div class="space-y-5">
    <div>
      <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">主题外观</p>
      <h2 class="m-0 text-2xl font-semibold">默认应用主题</h2>
      <p class="mt-3 text-sm leading-7 text-[color:var(--app-text-secondary)]">
        Phase 1 仅保留基础主题选项，用于后续主题系统落地前的默认值管理，不在本次任务中扩展完整换肤闭环。
      </p>
    </div>

    <NForm label-placement="top">
      <NFormItem label="默认主题">
        <NSelect :options="themeOptions" :value="theme" @update:value="updateTheme" />
      </NFormItem>
    </NForm>

    <div class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] p-4 text-sm leading-7 text-[color:var(--app-text-secondary)]">
      当前应用壳体保持暖色浅色纸感工作台，内容编辑区和设置表单主体继续使用高对比度实色背景，避免背景光效影响可读性。
    </div>
  </div>
</template>
