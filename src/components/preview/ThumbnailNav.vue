<script setup lang="ts">
import { computed, nextTick, watch, type ComponentPublicInstance } from 'vue'
import ThumbnailItem from './ThumbnailItem.vue'
import type { PreviewPageItem, WorkspaceGenerationProgressState } from '@/types/preview'

const props = defineProps<{
  currentPageNumber: number
  generationProgress: WorkspaceGenerationProgressState
  items: PreviewPageItem[]
}>()

const emit = defineEmits<{
  selectPage: [pageNumber: number]
}>()

const itemElementMap = new Map<number, HTMLElement>()
const generatedCount = computed<number>(() => props.generationProgress.generatedCount)
const generatingCount = computed<number>(() => props.generationProgress.generatingCount)

watch(
  [() => props.currentPageNumber, () => props.items.length],
  () => {
    void scrollCurrentItemIntoView()
  },
  { immediate: true }
)

function registerItemElement(pageNumber: number, element: Element | ComponentPublicInstance | null): void {
  const resolvedElement = element instanceof HTMLElement
    ? element
    : element && '$el' in element && element.$el instanceof HTMLElement
      ? element.$el
      : null

  if (!resolvedElement) {
    itemElementMap.delete(pageNumber)
    return
  }

  itemElementMap.set(pageNumber, resolvedElement)
}

async function scrollCurrentItemIntoView(): Promise<void> {
  await nextTick()
  itemElementMap.get(props.currentPageNumber)?.scrollIntoView({
    behavior: 'smooth',
    block: 'nearest'
  })
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="mb-4 flex items-start justify-between gap-3">
      <div>
        <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">缩略图轨道</p>
        <h2 class="m-0 text-base font-semibold">页面列表</h2>
      </div>

        <div class="rounded-full border border-[color:var(--app-border-subtle)] bg-[rgba(255,251,243,0.86)] px-3 py-1 text-right">
          <div class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">
            {{ generatedCount }} / {{ generationProgress.totalPages || items.length || 0 }} 已可预览
          </div>
          <div class="text-xs text-[color:var(--app-text-secondary)]">
            {{ generatingCount }} 页生成中
        </div>
      </div>
    </div>

    <div v-if="items.length === 0" class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4 text-sm leading-6 text-[color:var(--app-text-secondary)]">
      当前还没有可浏览的页面。
    </div>

    <div v-else class="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
      <div
        v-for="item in items"
        :key="item.pageNumber"
        :ref="(element) => registerItemElement(item.pageNumber, element)"
      >
        <ThumbnailItem
          :current-generating-page-number="generationProgress.currentGeneratingPageNumber"
          :item="item"
          :selected="currentPageNumber === item.pageNumber"
          @select="emit('selectPage', $event)"
        />
      </div>
    </div>
  </div>
</template>
