<script setup lang="ts">
import { computed, nextTick, ref, watch, type ComponentPublicInstance } from 'vue'
import ThumbnailItem from './ThumbnailItem.vue'
import type { PreviewPageItem, WorkspaceGenerationProgressState } from '@/types/preview'

const props = defineProps<{
  currentPageNumber: number
  generationProgress: WorkspaceGenerationProgressState
  items: PreviewPageItem[]
}>()

const emit = defineEmits<{
  deletePage: [pageNumber: number]
  duplicatePage: [pageNumber: number]
  insertPageAfter: [pageNumber: number]
  openVersionHistory: [pageNumber: number]
  reorderPages: [pageNumbers: number[]]
  selectPage: [pageNumber: number]
}>()

const itemElementMap = new Map<number, HTMLElement>()
const generatedCount = computed<number>(() => props.generationProgress.generatedCount)
const generatingCount = computed<number>(() => props.generationProgress.generatingCount)
const draggingPageNumber = ref<number | null>(null)
const dragOverPageNumber = ref<number | null>(null)

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

function handleDragStart(event: DragEvent, pageNumber: number): void {
  if (event.target instanceof HTMLElement && event.target.closest('[data-thumbnail-drag-ignore="true"]')) {
    event.preventDefault()
    return
  }

  draggingPageNumber.value = pageNumber
  dragOverPageNumber.value = null
  event.dataTransfer?.setData('text/plain', String(pageNumber))
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function handleDragOver(event: DragEvent, pageNumber: number): void {
  if (draggingPageNumber.value === null || draggingPageNumber.value === pageNumber) {
    return
  }

  event.preventDefault()
  dragOverPageNumber.value = pageNumber
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function handleDrop(event: DragEvent, targetPageNumber: number): void {
  event.preventDefault()
  const sourcePageNumber = resolveDraggedPageNumber(event)
  clearDragState()

  if (sourcePageNumber === null || sourcePageNumber === targetPageNumber) {
    return
  }

  const orderedPageNumbers = props.items.map((item) => item.pageNumber)
  const sourceIndex = orderedPageNumbers.indexOf(sourcePageNumber)
  const targetIndex = orderedPageNumbers.indexOf(targetPageNumber)

  if (sourceIndex < 0 || targetIndex < 0) {
    return
  }

  const [movedPageNumber] = orderedPageNumbers.splice(sourceIndex, 1)
  orderedPageNumbers.splice(targetIndex, 0, movedPageNumber)
  emit('reorderPages', orderedPageNumbers)
}

function clearDragState(): void {
  draggingPageNumber.value = null
  dragOverPageNumber.value = null
}

function resolveDraggedPageNumber(event: DragEvent): number | null {
  const rawValue = event.dataTransfer?.getData('text/plain') || String(draggingPageNumber.value ?? '')
  const parsed = Number.parseInt(rawValue, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
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
        draggable="true"
        class="rounded-[var(--radius-xl)] transition duration-200"
        :class="dragOverPageNumber === item.pageNumber
          ? 'translate-y-0.5 ring-2 ring-[rgba(104,166,125,0.42)]'
          : ''"
        @dragenter="handleDragOver($event, item.pageNumber)"
        @dragend="clearDragState"
        @dragover="handleDragOver($event, item.pageNumber)"
        @dragstart="handleDragStart($event, item.pageNumber)"
        @drop="handleDrop($event, item.pageNumber)"
      >
        <ThumbnailItem
          :current-generating-page-number="generationProgress.currentGeneratingPageNumber"
          :item="item"
          :selected="currentPageNumber === item.pageNumber"
          @delete-page="emit('deletePage', $event)"
          @duplicate-page="emit('duplicatePage', $event)"
          @insert-page-after="emit('insertPageAfter', $event)"
          @open-version-history="emit('openVersionHistory', $event)"
          @select="emit('selectPage', $event)"
        />
      </div>
    </div>
  </div>
</template>
