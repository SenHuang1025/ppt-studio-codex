<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { NButton } from 'naive-ui'
import type { PreviewPageStatus } from '@/types/preview'
import { getPreviewPageStatusLabel } from '@/utils/preview'

const props = withDefaults(defineProps<{
  canGoNext: boolean
  canGoPrevious: boolean
  canRefresh: boolean
  currentPageNumber: number
  currentPageStatus: PreviewPageStatus
  currentPageTitle: string
  keyboardEnabled?: boolean
  refreshDisabledReason?: string | null
  totalPages: number
}>(), {
  keyboardEnabled: true,
  refreshDisabledReason: null
})

const emit = defineEmits<{
  next: []
  previous: []
  refresh: []
}>()

const currentStatusLabel = computed<string>(() => getPreviewPageStatusLabel(props.currentPageStatus))
const effectiveRefreshDisabledReason = computed<string>(() =>
  props.refreshDisabledReason?.trim() || '当前页尚未生成，暂时不能刷新 iframe。'
)

onMounted(() => {
  window.addEventListener('keydown', handleWindowKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
})

function handleWindowKeydown(event: KeyboardEvent): void {
  if (!props.keyboardEnabled) {
    return
  }

  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
    return
  }

  if (isEditableTarget(event.target)) {
    return
  }

  if (event.key === 'ArrowLeft' && props.canGoPrevious) {
    event.preventDefault()
    emit('previous')
  }

  if (event.key === 'ArrowRight' && props.canGoNext) {
    event.preventDefault()
    emit('next')
  }
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }

  const tagName = target.tagName.toLowerCase()
  return target.isContentEditable || tagName === 'input' || tagName === 'textarea' || tagName === 'select'
}
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,251,243,0.82)] px-4 py-3">
    <div class="flex items-center gap-2">
      <NButton secondary strong :disabled="!canGoPrevious" @click="emit('previous')">
        上一页
      </NButton>
      <NButton secondary strong :disabled="!canRefresh" @click="emit('refresh')">
        刷新当前页
      </NButton>
      <NButton secondary strong :disabled="!canGoNext" @click="emit('next')">
        下一页
      </NButton>
    </div>

    <div class="min-w-[240px] flex-1 text-right">
      <div class="flex flex-wrap items-center justify-end gap-3">
        <div class="rounded-full border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] px-4 py-1.5 text-sm font-medium text-[color:var(--app-text-primary)]">
          {{ currentPageNumber }} / {{ totalPages }}
        </div>
        <span class="max-w-[320px] truncate text-sm text-[color:var(--app-text-secondary)]">{{ currentPageTitle }}</span>
      </div>
      <div class="mt-2 flex flex-wrap items-center justify-end gap-3 text-[11px] text-[color:var(--app-text-tertiary)]">
        <span class="mono-meta">键盘 ← / →</span>
        <span>{{ currentStatusLabel }}</span>
        <span v-if="!canRefresh">{{ effectiveRefreshDisabledReason }}</span>
      </div>
    </div>
  </div>
</template>
