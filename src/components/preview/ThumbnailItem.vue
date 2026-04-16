<script setup lang="ts">
import { computed } from 'vue'
import { NDropdown, type DropdownOption } from 'naive-ui'
import LinearProgressGlow from '@/components/common/LinearProgressGlow.vue'
import type { PreviewPageItem } from '@/types/preview'
import { formatPreviewPageType, getPreviewPageStatusLabel } from '@/utils/preview'

type ThumbnailMenuKey = 'delete' | 'duplicate' | 'history' | 'insert-after'

const props = defineProps<{
  currentGeneratingPageNumber: number | null
  item: PreviewPageItem
  selected: boolean
}>()

const emit = defineEmits<{
  deletePage: [pageNumber: number]
  duplicatePage: [pageNumber: number]
  insertPageAfter: [pageNumber: number]
  openVersionHistory: [pageNumber: number]
  select: [pageNumber: number]
}>()

const menuOptions = computed<DropdownOption[]>(() => [
  {
    disabled: !props.item.hasGeneratedCode,
    key: 'history',
    label: '查看历史版本'
  },
  {
    key: 'insert-after',
    label: '在后面插入新页'
  },
  {
    disabled: !props.item.hasGeneratedCode,
    key: 'duplicate',
    label: '复制'
  },
  {
    key: 'delete',
    label: '删除'
  }
])

const statusLabel = computed<string>(() => getPreviewPageStatusLabel(props.item.status))
const pageTypeLabel = computed<string>(() => formatPreviewPageType(props.item.pageType))
const versionLabel = computed<string>(() => (props.item.version ? `v${props.item.version}` : '等待版本'))
const messageCountLabel = computed<string>(() => `${props.item.chatMessageCount} 条对话`)
const summaryLabel = computed<string>(() => props.item.contentBrief || props.item.layout || '等待当前页内容写入')
const isCurrentGeneratingPage = computed<boolean>(() =>
  props.item.status === 'generating' && props.currentGeneratingPageNumber === props.item.pageNumber
)

const statusClass = computed<string>(() => {
  switch (props.item.status) {
    case 'confirmed':
      return 'bg-[rgba(88,151,109,0.96)]'
    case 'generated':
      return 'bg-[color:var(--primary-200)]'
    case 'generating':
      return isCurrentGeneratingPage.value
        ? 'thumbnail-generating-dot bg-[color:var(--accent-100)]'
        : 'bg-[rgba(241,143,1,0.72)]'
    default:
      return 'bg-[rgba(95,95,95,0.26)]'
  }
})

const buttonClass = computed<string>(() => {
  if (props.selected && props.item.status === 'generating') {
    return 'border-[rgba(241,143,1,0.28)] bg-[rgba(255,244,230,0.96)] text-[color:var(--accent-200)] shadow-[var(--shadow-hover)]'
  }

  if (props.selected && props.item.status === 'confirmed') {
    return 'border-[rgba(88,151,109,0.34)] bg-[rgba(240,249,243,0.98)] text-[color:var(--primary-300)] shadow-[var(--shadow-hover)]'
  }

  if (props.selected) {
    return 'border-[color:var(--app-border-strong)] bg-[color:var(--app-primary-soft)] text-[color:var(--primary-300)] shadow-[var(--shadow-hover)]'
  }

  return 'border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] hover:-translate-y-0.5 hover:border-[color:var(--app-border-strong)] hover:shadow-[var(--shadow-soft)]'
})

const previewBlockClass = computed<string>(() => {
  switch (props.item.status) {
    case 'confirmed':
      return 'border-[rgba(88,151,109,0.24)] bg-[linear-gradient(180deg,rgba(245,252,247,0.98)_0%,rgba(231,243,235,0.98)_100%)] shadow-[0_10px_24px_rgba(88,151,109,0.1)]'
    case 'generated':
      return 'border-[rgba(104,166,125,0.2)] bg-[linear-gradient(180deg,rgba(255,251,243,0.98)_0%,rgba(247,240,226,0.98)_100%)]'
    case 'generating':
      return isCurrentGeneratingPage.value
        ? 'border-[rgba(241,143,1,0.24)] bg-[linear-gradient(180deg,rgba(255,248,237,0.98)_0%,rgba(245,229,204,0.98)_100%)] shadow-[0_10px_24px_rgba(241,143,1,0.12)]'
        : 'border-[rgba(241,143,1,0.18)] bg-[linear-gradient(180deg,rgba(255,248,237,0.98)_0%,rgba(243,231,210,0.98)_100%)]'
    default:
      return 'border-[rgba(95,95,95,0.14)] bg-[rgba(255,255,255,0.52)]'
  }
})

const progressTone = computed<'accent' | 'muted' | 'primary'>(() => {
  switch (props.item.status) {
    case 'confirmed':
      return 'primary'
    case 'generated':
      return 'primary'
    case 'generating':
      return 'accent'
    default:
      return 'muted'
  }
})

const progressValue = computed<number>(() => {
  switch (props.item.status) {
    case 'confirmed':
      return 1
    case 'generated':
      return 1
    case 'generating':
      return 0.48
    default:
      return 0.08
  }
})

function handleMenuSelect(key: string | number): void {
  switch (key as ThumbnailMenuKey) {
    case 'delete':
      emit('deletePage', props.item.pageNumber)
      return
    case 'duplicate':
      emit('duplicatePage', props.item.pageNumber)
      return
    case 'history':
      emit('openVersionHistory', props.item.pageNumber)
      return
    case 'insert-after':
      emit('insertPageAfter', props.item.pageNumber)
      return
  }
}
</script>

<template>
  <div
    class="w-full rounded-[var(--radius-xl)] border p-3 text-left transition duration-250"
    :class="buttonClass"
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

      <div class="mt-1 flex items-start gap-2">
        <div class="flex items-center gap-2 pt-1">
          <span class="h-2.5 w-2.5 shrink-0 rounded-full" :class="statusClass" />
          <span class="text-xs text-[color:var(--app-text-secondary)]">{{ statusLabel }}</span>
        </div>
        <NDropdown
          :options="menuOptions"
          placement="bottom-end"
          trigger="click"
          @select="handleMenuSelect"
        >
          <button
            data-thumbnail-drag-ignore="true"
            class="flex h-7 w-7 items-center justify-center rounded-full border border-[rgba(131,53,0,0.12)] bg-[rgba(255,255,255,0.68)] text-xs text-[color:var(--app-text-secondary)] transition duration-200 hover:border-[rgba(131,53,0,0.24)] hover:text-[color:var(--primary-300)]"
            type="button"
            @click.stop
          >
            ···
          </button>
        </NDropdown>
      </div>
    </div>

    <button
      class="relative aspect-[16/9] overflow-hidden rounded-[var(--radius-lg)] border px-3 py-3"
      :class="previewBlockClass"
      type="button"
      @click="emit('select', item.pageNumber)"
    >
      <div v-if="item.status === 'generating'" class="thumbnail-generating-sheen absolute inset-y-0 left-[-32%] w-1/3" />
      <div class="absolute inset-x-3 top-3">
        <LinearProgressGlow
          :animated="item.status === 'generating'"
          :tone="progressTone"
          :value="progressValue"
        />
      </div>
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
          <div class="shrink-0 text-right">
            <div class="rounded-full border border-[rgba(131,53,0,0.12)] px-2 py-0.5">
              {{ versionLabel }}
            </div>
            <div class="mt-1 text-[10px] text-[color:var(--app-text-tertiary)]">
              {{ messageCountLabel }}
            </div>
          </div>
        </div>
      </div>
    </button>
  </div>
</template>

<style scoped>
.thumbnail-generating-dot {
  animation: thumbnail-generating-pulse 1.8s ease-in-out infinite;
}

.thumbnail-generating-sheen {
  animation: thumbnail-generating-sheen 1.9s ease-in-out infinite;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0), rgba(255, 247, 231, 0.7), rgba(255, 255, 255, 0));
  opacity: 0.7;
  transform: translateX(-135%);
}

@keyframes thumbnail-generating-pulse {
  0%,
  100% {
    opacity: 0.72;
    transform: scale(0.96);
  }

  50% {
    opacity: 1;
    transform: scale(1.08);
  }
}

@keyframes thumbnail-generating-sheen {
  0% {
    opacity: 0;
    transform: translateX(-135%);
  }

  20% {
    opacity: 0.7;
  }

  100% {
    opacity: 0;
    transform: translateX(540%);
  }
}
</style>
