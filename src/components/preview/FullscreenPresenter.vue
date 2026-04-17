<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import SlideRenderer from '@/components/preview/SlideRenderer.vue'
import type { PreviewPageStatus } from '@/types/preview'

const props = withDefaults(defineProps<{
  active: boolean
  canGoNext: boolean
  canGoPrevious: boolean
  currentGenerationStageLabel?: string | null
  generationActive?: boolean
  generationActivePageNumber?: number | null
  pageNumber: number
  pageStatus: PreviewPageStatus
  pageTitle: string
  previewOverrideCode?: string | null
  refreshToken?: string
  totalPages: number
}>(), {
  currentGenerationStageLabel: null,
  generationActive: false,
  generationActivePageNumber: null,
  previewOverrideCode: null,
  refreshToken: '0'
})

const emit = defineEmits<{
  close: []
  fullscreenError: [message: string]
  nextPage: []
  previousPage: []
}>()

const presenterRef = ref<HTMLElement | null>(null)
let fullscreenRequest: Promise<void> | null = null

const pageIndicatorLabel = computed<string>(() => `${props.pageNumber} / ${Math.max(props.totalPages, 1)}`)

watch(
  () => props.active,
  (active) => {
    if (active) {
      void nextTick(() => {
        if (props.active && !isPresenterFullscreen() && fullscreenRequest === null) {
          void enterFullscreen()
        }
      })
      return
    }

    void exitOwnedFullscreen()
  }
)

onMounted(() => {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  window.addEventListener('keydown', handleWindowKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  window.removeEventListener('keydown', handleWindowKeydown)
  void exitOwnedFullscreen()
})

async function enterFullscreen(): Promise<void> {
  const presenterElement = presenterRef.value
  if (!presenterElement) {
    return
  }

  if (!presenterElement.requestFullscreen) {
    emit('fullscreenError', '当前运行环境不支持 Fullscreen API。')
    emit('close')
    return
  }

  if (isPresenterFullscreen()) {
    return
  }

  try {
    fullscreenRequest = presenterElement.requestFullscreen()
    await fullscreenRequest
  } catch (error: unknown) {
    emit('fullscreenError', resolveFullscreenError(error))
    emit('close')
  } finally {
    fullscreenRequest = null
  }
}

async function exitOwnedFullscreen(): Promise<void> {
  if (!isPresenterFullscreen() || !document.exitFullscreen) {
    return
  }

  await document.exitFullscreen().catch(() => undefined)
}

function handleFullscreenChange(): void {
  if (props.active && !isPresenterFullscreen()) {
    emit('close')
  }
}

function handleWindowKeydown(event: KeyboardEvent): void {
  if (!props.active || event.defaultPrevented) {
    return
  }

  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
    void exitOwnedFullscreen()
    return
  }

  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
    return
  }

  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    requestPreviousPage()
    return
  }

  if (event.key === 'ArrowRight') {
    event.preventDefault()
    requestNextPage()
  }
}

function handlePreviousZoneClick(): void {
  requestPreviousPage()
}

function handleNextZoneClick(): void {
  requestNextPage()
}

function requestPreviousPage(): void {
  if (!props.canGoPrevious) {
    return
  }

  emit('previousPage')
}

function requestNextPage(): void {
  if (!props.canGoNext) {
    return
  }

  emit('nextPage')
}

function isPresenterFullscreen(): boolean {
  return document.fullscreenElement === presenterRef.value
}

function resolveFullscreenError(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }

  return '进入全屏演示失败，请确认当前窗口允许使用 Fullscreen API。'
}

defineExpose({
  enterFullscreen
})
</script>

<template>
  <div
    ref="presenterRef"
    class="fixed inset-0 z-[1000] bg-black text-white transition-opacity duration-150"
    :class="active ? 'visible opacity-100 pointer-events-auto' : 'invisible opacity-0 pointer-events-none'"
    aria-label="全屏演示模式"
  >
    <SlideRenderer
      v-if="active"
      class="h-full min-h-0"
      :current-generation-stage-label="currentGenerationStageLabel"
      :generation-active="generationActive"
      :generation-active-page-number="generationActivePageNumber"
      :page-number="pageNumber"
      :page-status="pageStatus"
      :page-title="pageTitle"
      presenter
      :preview-override-code="previewOverrideCode"
      :refresh-token="refreshToken"
    />

    <button
      v-if="active"
      aria-label="上一页"
      class="absolute inset-y-0 left-0 z-[2] w-[30%] cursor-w-resize border-0 bg-transparent p-0"
      :class="canGoPrevious ? '' : 'cursor-default'"
      type="button"
      @click="handlePreviousZoneClick"
    />
    <button
      v-if="active"
      aria-label="下一页"
      class="absolute inset-y-0 right-0 z-[2] w-[70%] cursor-e-resize border-0 bg-transparent p-0"
      :class="canGoNext ? '' : 'cursor-default'"
      type="button"
      @click="handleNextZoneClick"
    />

    <div
      v-if="active"
      class="pointer-events-none absolute inset-x-0 bottom-5 z-[3] flex justify-center px-4"
    >
      <div class="rounded-full border border-white/16 bg-black/56 px-3 py-1.5 text-xs font-medium text-white/86 shadow-[0_10px_34px_rgba(0,0,0,0.28)]">
        {{ pageIndicatorLabel }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.fixed:fullscreen {
  height: 100vh;
  width: 100vw;
}
</style>
