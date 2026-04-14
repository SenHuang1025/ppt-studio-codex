<script setup lang="ts">
import { computed } from 'vue'
import type { PreviewPageItem } from '@/types/preview'
import { formatPreviewPageType, getPreviewPageStatusLabel } from '@/utils/preview'

const props = defineProps<{
  item: PreviewPageItem
  selected: boolean
}>()

const emit = defineEmits<{
  select: [pageNumber: number]
}>()

const statusLabel = computed<string>(() => getPreviewPageStatusLabel(props.item.status))
const pageTypeLabel = computed<string>(() => formatPreviewPageType(props.item.pageType))
const versionLabel = computed<string>(() => (props.item.version ? `v${props.item.version}` : '等待版本'))
const summaryLabel = computed<string>(() => props.item.contentBrief || props.item.layout || '等待当前页内容写入')

const statusClass = computed<string>(() => {
  switch (props.item.status) {
    case 'generated':
      return 'bg-[color:var(--primary-200)]'
    case 'generating':
      return 'bg-[color:var(--accent-100)]'
    default:
      return 'bg-[rgba(95,95,95,0.26)]'
  }
})

const previewBlockClass = computed<string>(() => {
  switch (props.item.status) {
    case 'generated':
      return 'border-[rgba(104,166,125,0.2)] bg-[linear-gradient(180deg,rgba(255,251,243,0.98)_0%,rgba(247,240,226,0.98)_100%)]'
    case 'generating':
      return 'border-[rgba(241,143,1,0.18)] bg-[linear-gradient(180deg,rgba(255,248,237,0.98)_0%,rgba(243,231,210,0.98)_100%)]'
    default:
      return 'border-[rgba(95,95,95,0.14)] bg-[rgba(255,255,255,0.52)]'
  }
})
</script>

<template>
  <button
    class="w-full rounded-[var(--radius-xl)] border p-3 text-left transition duration-250"
    :class="
      selected
        ? 'border-[color:var(--app-border-strong)] bg-[color:var(--app-primary-soft)] text-[color:var(--primary-300)] shadow-[var(--shadow-hover)]'
        : 'border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] hover:-translate-y-0.5 hover:border-[color:var(--app-border-strong)] hover:shadow-[var(--shadow-soft)]'
    "
    type="button"
    @click="emit('select', item.pageNumber)"
  >
    <div class="mb-3 flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">第 {{ item.pageNumber }} 页</div>
        <div class="mt-2 max-h-[3rem] overflow-hidden text-sm font-semibold leading-6">{{ item.title }}</div>
        <div class="mt-2 flex flex-wrap gap-2 text-[11px] text-[color:var(--app-text-secondary)]">
          <span class="rounded-full border border-[rgba(131,53,0,0.12)] bg-[rgba(255,255,255,0.58)] px-2 py-0.5">
            {{ pageTypeLabel }}
          </span>
          <span class="rounded-full border border-[rgba(131,53,0,0.12)] bg-[rgba(255,255,255,0.58)] px-2 py-0.5">
            {{ versionLabel }}
          </span>
        </div>
      </div>

      <div class="mt-1 flex items-center gap-2">
        <span class="h-2.5 w-2.5 shrink-0 rounded-full" :class="statusClass" />
        <span class="text-xs text-[color:var(--app-text-secondary)]">{{ statusLabel }}</span>
      </div>
    </div>

    <div
      class="aspect-[16/9] rounded-[var(--radius-lg)] border px-3 py-3"
      :class="previewBlockClass"
    >
      <div class="flex h-full flex-col justify-between rounded-[calc(var(--radius-lg)-6px)] border border-dashed border-[rgba(131,53,0,0.1)] p-3">
        <div class="flex items-center justify-between gap-3">
          <div class="h-2.5 w-14 rounded-full bg-[rgba(131,53,0,0.12)]" />
          <div class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">
            {{ pageTypeLabel }}
          </div>
        </div>
        <div class="space-y-2">
          <div class="h-2 rounded-full bg-[rgba(53,53,53,0.08)]" />
          <div class="h-2 w-4/5 rounded-full bg-[rgba(53,53,53,0.08)]" />
          <div class="h-2 w-3/5 rounded-full bg-[rgba(53,53,53,0.08)]" />
        </div>
        <div class="flex items-end justify-between gap-3 text-[11px] text-[color:var(--app-text-secondary)]">
          <div class="line-clamp-2 min-w-0 leading-5">
            {{ summaryLabel }}
          </div>
          <div class="shrink-0 rounded-full border border-[rgba(131,53,0,0.12)] px-2 py-0.5">
            {{ versionLabel }}
          </div>
        </div>
      </div>
    </div>
  </button>
</template>
