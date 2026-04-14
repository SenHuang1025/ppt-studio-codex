<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NButton } from 'naive-ui'
import {
  buildPreviewSlideUrl,
  ensurePreviewServerReachable,
  getPreviewBaseUrl
} from '@/services/previewService'
import type { PreviewPageStatus, SlideRendererErrorKind, SlideRendererState } from '@/types/preview'

const SLIDE_WIDTH = 1920
const SLIDE_HEIGHT = 1080
const LOAD_TIMEOUT_MS = 6000

const props = withDefaults(defineProps<{
  pageNumber: number
  pageStatus: PreviewPageStatus
  pageTitle: string
  refreshKey?: number
}>(), {
  refreshKey: 0
})

const containerRef = ref<HTMLElement | null>(null)
const stableFrameSrc = ref<string>('')
const loadingFrameSrc = ref<string>('')
const stableFramePageNumber = ref<number | null>(null)
const loadingTargetPageNumber = ref<number | null>(null)
const errorMessage = ref<string | null>(null)
const errorKind = ref<SlideRendererErrorKind | null>(null)
const rendererState = ref<SlideRendererState>('idle')
const containerWidth = ref(0)
const containerHeight = ref(0)
let resizeObserver: ResizeObserver | null = null
let loadSequence = 0
let loadTimeoutId: number | null = null

const scale = computed<number>(() => {
  if (containerWidth.value <= 0 || containerHeight.value <= 0) {
    return 1
  }

  return Math.min(containerWidth.value / SLIDE_WIDTH, containerHeight.value / SLIDE_HEIGHT)
})

const frameBoxStyle = computed<Record<string, string>>(() => ({
  height: `${Math.max(1, Math.round(SLIDE_HEIGHT * scale.value))}px`,
  width: `${Math.max(1, Math.round(SLIDE_WIDTH * scale.value))}px`
}))

const iframeStyle = computed<Record<string, string>>(() => ({
  border: '0',
  display: 'block',
  height: `${SLIDE_HEIGHT}px`,
  transform: `scale(${scale.value})`,
  transformOrigin: 'top left',
  width: `${SLIDE_WIDTH}px`
}))
const hasStableFrame = computed<boolean>(() => Boolean(stableFrameSrc.value))
const shouldShowFrame = computed<boolean>(() =>
  rendererState.value !== 'idle'
    && (Boolean(stableFrameSrc.value) || Boolean(loadingFrameSrc.value) || rendererState.value === 'error')
)
const isShowingStaleFrame = computed<boolean>(() =>
  stableFramePageNumber.value !== null && stableFramePageNumber.value !== props.pageNumber
)

const idleTitle = computed<string>(() => {
  if (props.pageStatus === 'generating') {
    return `第 ${props.pageNumber} 页正在生成`
  }

  return `第 ${props.pageNumber} 页尚未生成`
})

const idleDescription = computed<string>(() => {
  if (props.pageStatus === 'generating') {
    return '当前页代码正在生成中，完成后会自动接入 iframe 预览。'
  }

  return '请等待逐页生成完成，或切换到已经生成的页面继续浏览。'
})
const loadingDescription = computed<string>(() => {
  if (hasStableFrame.value) {
    return `正在刷新第 ${props.pageNumber} 页《${props.pageTitle}》，旧画面会保留到新画面准备完成。`
  }

  return `正在载入第 ${props.pageNumber} 页《${props.pageTitle}》。`
})
const errorTitle = computed<string>(() => {
  if (errorKind.value === 'server-unavailable') {
    return 'preview server 不可用'
  }

  return `第 ${props.pageNumber} 页预览加载失败`
})
const errorDescription = computed<string>(() => {
  const baseMessage = errorMessage.value || '预览画布暂时不可用，请稍后重试。'

  if (isShowingStaleFrame.value && stableFramePageNumber.value) {
    return `${baseMessage} 当前仍保留第 ${stableFramePageNumber.value} 页的上一次成功画面。`
  }

  return baseMessage
})
const retryLabel = computed<string>(() =>
  errorKind.value === 'server-unavailable' ? '重试连接' : '重新加载当前页'
)

watch(
  () => [props.pageNumber, props.pageStatus, props.refreshKey] as const,
  (currentValue, previousValue) => {
    const forceRefresh = previousValue ? currentValue[2] !== previousValue[2] : false
    void loadCurrentSlide(forceRefresh)
  },
  { immediate: true }
)

onMounted(() => {
  if (!containerRef.value) {
    return
  }

  updateContainerSize(containerRef.value)
  resizeObserver = new ResizeObserver((entries) => {
    const entry = entries[0]
    if (!entry) {
      return
    }

    updateContainerSize(entry.target as HTMLElement)
  })
  resizeObserver.observe(containerRef.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  clearLoadTimeout()
})

function handleLoadingFrameLoad(): void {
  if (rendererState.value !== 'loading' || !loadingFrameSrc.value) {
    return
  }

  clearLoadTimeout()
  stableFrameSrc.value = loadingFrameSrc.value
  stableFramePageNumber.value = loadingTargetPageNumber.value
  loadingFrameSrc.value = ''
  loadingTargetPageNumber.value = null
  errorKind.value = null
  errorMessage.value = null
  rendererState.value = 'ready'
}

function handleRetry(): void {
  void loadCurrentSlide(true)
}

async function loadCurrentSlide(forceRefresh: boolean): Promise<void> {
  loadSequence += 1
  const currentLoadId = loadSequence
  clearLoadTimeout()
  errorMessage.value = null
  errorKind.value = null

  if (props.pageStatus !== 'generated') {
    stableFrameSrc.value = ''
    stableFramePageNumber.value = null
    loadingFrameSrc.value = ''
    loadingTargetPageNumber.value = null
    rendererState.value = 'idle'
    return
  }

  rendererState.value = 'loading'

  try {
    const baseUrl = await getPreviewBaseUrl(forceRefresh)
    await ensurePreviewServerReachable(baseUrl)
    const slideUrl = buildPreviewSlideUrl(baseUrl, props.pageNumber)

    if (currentLoadId !== loadSequence) {
      return
    }

    loadingTargetPageNumber.value = props.pageNumber
    loadingFrameSrc.value = `${slideUrl}${slideUrl.includes('?') ? '&' : '?'}ts=${Date.now()}`
    loadTimeoutId = window.setTimeout(() => {
      if (currentLoadId !== loadSequence || rendererState.value !== 'loading') {
        return
      }

      loadingFrameSrc.value = ''
      loadingTargetPageNumber.value = null
      errorKind.value = 'slide-load-failed'
      rendererState.value = 'error'
      errorMessage.value = '预览加载超时，请刷新当前页，或确认 preview server 仍在运行。'
    }, LOAD_TIMEOUT_MS)
  } catch (error: unknown) {
    if (currentLoadId !== loadSequence) {
      return
    }

    loadingFrameSrc.value = ''
    loadingTargetPageNumber.value = null
    errorKind.value = 'server-unavailable'
    rendererState.value = 'error'
    errorMessage.value = resolvePreviewError(error, errorKind.value)
  }
}

function updateContainerSize(element: HTMLElement): void {
  const { height, width } = element.getBoundingClientRect()
  containerWidth.value = width
  containerHeight.value = height
}

function clearLoadTimeout(): void {
  if (loadTimeoutId === null) {
    return
  }

  window.clearTimeout(loadTimeoutId)
  loadTimeoutId = null
}

function resolvePreviewError(error: unknown, kind: SlideRendererErrorKind | null): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }

  if (kind === 'server-unavailable') {
    return '无法连接到 preview server，请确认 Electron 侧边车服务已经启动。'
  }

  return '当前页预览暂时不可用，请稍后重试。'
}
</script>

<template>
  <div class="grid flex-1 place-items-center rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-preview-stage)] p-5 md:p-8">
    <div
      ref="containerRef"
      class="relative h-full min-h-[360px] w-full overflow-hidden rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-canvas)]"
    >
      <div
        v-if="rendererState === 'idle'"
        class="absolute inset-0 grid place-items-center px-6"
      >
        <div class="max-w-[480px] text-center">
          <div class="mono-meta mb-3 text-[color:var(--app-text-tertiary)]">Preview Pending</div>
          <h3 class="m-0 text-2xl font-semibold">{{ idleTitle }}</h3>
          <p class="mt-4 text-sm leading-7 text-[color:var(--app-text-secondary)]">
            {{ idleDescription }}
          </p>
        </div>
      </div>

      <div v-else-if="shouldShowFrame" class="absolute inset-0 flex items-center justify-center p-5">
        <div
          class="relative overflow-hidden rounded-[28px] bg-white shadow-[var(--shadow-canvas)]"
          :style="frameBoxStyle"
        >
          <iframe
            v-if="stableFrameSrc"
            :key="stableFrameSrc"
            :src="stableFrameSrc"
            sandbox="allow-scripts allow-same-origin"
            title="PPT slide preview"
            :style="iframeStyle"
          />
          <iframe
            v-if="loadingFrameSrc"
            :key="loadingFrameSrc"
            :src="loadingFrameSrc"
            sandbox="allow-scripts allow-same-origin"
            title="PPT slide preview loading"
            class="absolute inset-0"
            :class="hasStableFrame ? 'pointer-events-none opacity-0' : ''"
            :style="iframeStyle"
            @load="handleLoadingFrameLoad"
          />

          <div
            v-if="rendererState === 'loading' && !hasStableFrame"
            class="absolute inset-0 grid place-items-center bg-[rgba(255,253,248,0.9)]"
          >
            <div class="text-center">
              <div class="mono-meta mb-3 text-[color:var(--app-text-tertiary)]">Loading Slide</div>
              <div class="text-sm text-[color:var(--app-text-secondary)]">
                {{ loadingDescription }}
              </div>
            </div>
          </div>

          <div
            v-else-if="rendererState === 'loading'"
            class="absolute inset-x-5 top-5 flex justify-center"
          >
            <div class="max-w-[580px] rounded-full border border-[rgba(131,53,0,0.1)] bg-[rgba(255,253,248,0.92)] px-4 py-2 text-center text-sm text-[color:var(--app-text-secondary)] shadow-[var(--shadow-soft)]">
              {{ loadingDescription }}
            </div>
          </div>

          <div
            v-if="rendererState === 'error'"
            class="absolute inset-0 grid place-items-center bg-[rgba(255,253,248,0.86)] px-6"
          >
            <div class="max-w-[560px] text-center">
              <div class="mono-meta mb-3 text-[color:#9f4b2a]">Preview Error</div>
              <h3 class="m-0 text-2xl font-semibold">{{ errorTitle }}</h3>
              <p class="mt-4 text-sm leading-7 text-[color:var(--app-text-secondary)]">
                {{ errorDescription }}
              </p>
              <NButton class="mt-5" secondary strong @click="handleRetry">
                {{ retryLabel }}
              </NButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
