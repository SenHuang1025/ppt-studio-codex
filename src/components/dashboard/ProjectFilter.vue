<script setup lang="ts">
import { PROJECT_FILTER_OPTIONS } from '@/stores/projectStore'
import type { ProjectFilterValue } from '@/stores/projectStore'

defineProps<{
  loading: boolean
  modelValue: ProjectFilterValue
  total: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ProjectFilterValue]
}>()

function updateFilter(value: ProjectFilterValue): void {
  emit('update:modelValue', value)
}
</script>

<template>
  <section class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
    <div>
      <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">最近项目</p>
      <div class="text-sm text-[color:var(--app-text-secondary)]">
        {{ loading ? '正在同步项目列表…' : `当前显示 ${total} 个项目` }}
      </div>
    </div>

    <div class="flex flex-wrap gap-2 rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-2 shadow-[var(--shadow-glass-1)]">
      <button
        v-for="option in PROJECT_FILTER_OPTIONS"
        :key="option.value"
        class="flex items-center gap-2 rounded-[var(--radius-lg)] border px-4 py-2 text-sm transition duration-250"
        :class="
          option.value === modelValue
            ? 'border-[color:var(--app-primary-ring)] bg-[color:var(--app-primary-soft)] text-[color:var(--primary-300)] shadow-[var(--shadow-highlight)]'
            : 'border-transparent text-[color:var(--app-text-secondary)] hover:border-[color:var(--app-border-subtle)] hover:bg-[color:var(--surface-editor)] hover:text-[color:var(--primary-300)]'
        "
        type="button"
        @click="updateFilter(option.value)"
      >
        <span>{{ option.label }}</span>
        <span v-if="loading && option.value === modelValue" class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">
          sync
        </span>
      </button>
    </div>
  </section>
</template>
