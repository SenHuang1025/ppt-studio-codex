<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NButton } from 'naive-ui'
import {
  buildPreviewSlideUrl,
  buildPreviewVersionUrl,
  ensurePreviewServerReachable,
  getPreviewBaseUrl
} from '@/services/previewService'
import type {
  IframeScrollSnapshot,
  PreviewPageStatus,
  SlideRendererErrorKind,
  SlideRendererState
} from '@/types/preview'

const SLIDE_WIDTH = 1920
const SLIDE_HEIGHT = 1080
const LOAD_TIMEOUT_MS = 6000
const SCROLL_SNAPSHOT_TIMEOUT_MS = 180
const MAX_AUTO_RETRY_COUNT = 2
const PREVIEW_IFRAME_MESSAGE_SOURCE = 'ppt-studio-preview-frame'
const PREVIEW_IFRAME_MESSAGE_TARGET = 'ppt-studio-host'

const props = withDefaults(defineProps<{
  currentGenerationStageLabel?: string | null
  generationActive?: boolean
  generationActivePageNumber?: number | null
  presenter?: boolean
  pageNumber: number
  pageStatus: PreviewPageStatus
  pageTitle: string
  previewOverrideCode?: string | null
  refreshToken?: string
}>(), {
  currentGenerationStageLabel: null,
  generationActive: false,
  generationActivePageNumber: null,
  presenter: false,
  previewOverrideCode: null,
  refreshToken: '0'
})

interface RenderFrameSlot {
  key: string
  pageNumber: number
  src: string
}

interface HostFrameMessageEnvelope {
  id?: string
  payload?: unknown
  source?: string
  type?: string
}

const containerRef = ref<HTMLElement | null>(null)
const stableFrameRef = ref<HTMLIFrameElement | null>(null)
const loadingFrameRef = ref<HTMLIFrameElement | null>(null)
const stableFrame = ref<RenderFrameSlot | null>(null)
const loadingFrame = ref<RenderFrameSlot | null>(null)
const errorMessage = ref<string | null>(null)
const errorKind = ref<SlideRendererErrorKind | null>(null)
const rendererState = ref<SlideRendererState>('idle')
const containerWidth = ref(0)
const containerHeight = ref(0)
let resizeObserver: ResizeObserver | null = null
let loadSequence = 0
let loadTimeoutId: number | null = null
let frameSequence = 0
let scrollRequestSequence = 0
let autoRetryCount = 0
let autoRetryTimerId: number | null = null
const pendingScrollResolvers = new Map<string, (snapshot: IframeScrollSnapshot | null) => void>()

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
const hasStableFrame = computed<boolean>(() => stableFrame.value !== null)
const shouldShowFrame = computed<boolean>(() =>
  rendererState.value !== 'idle'
    && (stableFrame.value !== null || loadingFrame.value !== null || rendererState.value === 'error')
)
const isShowingStaleFrame = computed<boolean>(() =>
  stableFrame.value !== null && stableFrame.value.pageNumber !== props.pageNumber
)

const idleTitle = computed<string>(() => {
  if (props.pageStatus === 'generating') {
    return `第 ${props.pageNumber} 页正在生成`
  }

  return `第 ${props.pageNumber} 页尚未生成`
})

const idleDescription = computed<string>(() => {
  if (props.pageStatus === 'generating') {
    return props.currentGenerationStageLabel
      ? `当前页处于${props.currentGenerationStageLabel}，完成后会自动接入 iframe 预览。`
      : '当前页代码正在生成中，完成后会自动接入 iframe 预览。'
  }

  if (props.generationActive && props.generationActivePageNumber && props.generationActivePageNumber !== props.pageNumber) {
    return `后台正在生成第 ${props.generationActivePageNumber} 页，你可以先浏览已完成页面，轮到当前页后会自动接入预览。`
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

  if (isShowingStaleFrame.value && stableFrame.value) {
    return `${baseMessage} 当前仍保留第 ${stableFrame.value.pageNumber} 页的上一次成功画面。`
  }

  return baseMessage
})
const retryLabel = computed<string>(() =>
  errorKind.value === 'server-unavailable' ? '重试连接' : '重新加载当前页'
)

watch(
  () => [props.pageNumber, props.pageStatus, props.previewOverrideCode, props.refreshToken] as const,
  (currentValue, previousValue) => {
    const forceRefresh = previousValue
      ? currentValue[2] !== previousValue[2] || currentValue[3] !== previousValue[3]
      : false
    void loadCurrentSlide(forceRefresh)
  },
  { immediate: true }
)

onMounted(() => {
  if (!containerRef.value) {
    return
  }

  window.addEventListener('message', handleIframeMessage)
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
  window.removeEventListener('message', handleIframeMessage)
  resizeObserver?.disconnect()
  resizeObserver = null
  clearLoadTimeout()
  clearAutoRetryTimer()
  resolvePendingScrollRequests()
})

async function handleLoadingFrameLoad(): Promise<void> {
  if (rendererState.value !== 'loading' || !loadingFrame.value) {
    return
  }

  clearLoadTimeout()
  const snapshot = await readStableFrameScrollSnapshot()
  const nextStableFrame = loadingFrame.value
  stableFrame.value = nextStableFrame
  loadingFrame.value = null
  errorKind.value = null
  errorMessage.value = null
  rendererState.value = 'ready'
  await nextTick()
  await restoreFrameScrollSnapshot(stableFrameRef.value, snapshot)
}

function handleRetry(): void {
  autoRetryCount = 0
  void loadCurrentSlide(true)
}

async function loadCurrentSlide(forceRefresh: boolean): Promise<void> {
  loadSequence += 1
  const currentLoadId = loadSequence
  clearLoadTimeout()
  clearAutoRetryTimer()
  errorMessage.value = null
  errorKind.value = null

  if (props.pageStatus !== 'generated' && props.pageStatus !== 'confirmed') {
    stableFrame.value = null
    loadingFrame.value = null
    rendererState.value = 'idle'
    return
  }

  rendererState.value = 'loading'

  try {
    const baseUrl = await getPreviewBaseUrl(forceRefresh)
    await ensurePreviewServerReachable(baseUrl)
    const slideUrl = props.previewOverrideCode
      ? buildPreviewVersionUrl(baseUrl, props.pageNumber)
      : buildPreviewSlideUrl(baseUrl, props.pageNumber)

    if (currentLoadId !== loadSequence) {
      return
    }

    loadingFrame.value = {
      key: `preview-frame-${++frameSequence}`,
      pageNumber: props.pageNumber,
      src: `${slideUrl}${slideUrl.includes('?') ? '&' : '?'}ts=${Date.now()}`
    }
    loadTimeoutId = window.setTimeout(() => {
      if (currentLoadId !== loadSequence || rendererState.value !== 'loading') {
        return
      }

      loadingFrame.value = null
      errorKind.value = 'slide-load-failed'
      rendererState.value = 'error'
      errorMessage.value = '预览加载超时，请刷新当前页，或确认 preview server 仍在运行。'
      scheduleAutoRetry()
    }, LOAD_TIMEOUT_MS)
  } catch (error: unknown) {
    if (currentLoadId !== loadSequence) {
      return
    }

    loadingFrame.value = null
    errorKind.value = 'server-unavailable'
    rendererState.value = 'error'
    errorMessage.value = resolvePreviewError(error, errorKind.value)
    scheduleAutoRetry()
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

function scheduleAutoRetry(): void {
  if (autoRetryCount >= MAX_AUTO_RETRY_COUNT) {
    return
  }

  autoRetryCount += 1
  autoRetryTimerId = window.setTimeout(() => {
    autoRetryTimerId = null
    void loadCurrentSlide(true)
  }, 900 * autoRetryCount)
}

function clearAutoRetryTimer(): void {
  if (autoRetryTimerId === null) {
    return
  }

  window.clearTimeout(autoRetryTimerId)
  autoRetryTimerId = null
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

function handleIframeMessage(event: MessageEvent<unknown>): void {
  const data = event.data as HostFrameMessageEnvelope | null

  if (!data || data.source !== PREVIEW_IFRAME_MESSAGE_SOURCE || typeof data.type !== 'string') {
    return
  }

  if (data.type !== 'preview-scroll-snapshot' || typeof data.id !== 'string') {
    return
  }

  const resolve = pendingScrollResolvers.get(data.id)
  if (!resolve) {
    return
  }

  pendingScrollResolvers.delete(data.id)
  resolve(isIframeScrollSnapshot(data.payload) ? data.payload : null)
}

async function readStableFrameScrollSnapshot(): Promise<IframeScrollSnapshot | null> {
  return requestFrameScrollSnapshot(stableFrameRef.value)
}

async function requestFrameScrollSnapshot(frame: HTMLIFrameElement | null): Promise<IframeScrollSnapshot | null> {
  if (!frame?.contentWindow) {
    return null
  }

  const requestId = `preview-scroll-${++scrollRequestSequence}`

  return await new Promise<IframeScrollSnapshot | null>((resolve) => {
    const timeoutId = window.setTimeout(() => {
      pendingScrollResolvers.delete(requestId)
      resolve(null)
    }, SCROLL_SNAPSHOT_TIMEOUT_MS)

    pendingScrollResolvers.set(requestId, (snapshot) => {
      window.clearTimeout(timeoutId)
      resolve(snapshot)
    })

    frame.contentWindow?.postMessage(
      {
        id: requestId,
        source: PREVIEW_IFRAME_MESSAGE_TARGET,
        type: 'request-preview-scroll-snapshot'
      },
      '*'
    )
  })
}

async function restoreFrameScrollSnapshot(
  frame: HTMLIFrameElement | null,
  snapshot: IframeScrollSnapshot | null
): Promise<void> {
  if (!frame?.contentWindow || !snapshot) {
    return
  }

  await waitForAnimationFrame()
  frame.contentWindow.postMessage(
    {
      payload: snapshot,
      source: PREVIEW_IFRAME_MESSAGE_TARGET,
      type: 'restore-preview-scroll-snapshot'
    },
    '*'
  )
}

function waitForAnimationFrame(): Promise<void> {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => resolve())
  })
}

function resolvePendingScrollRequests(): void {
  for (const resolve of pendingScrollResolvers.values()) {
    resolve(null)
  }

  pendingScrollResolvers.clear()
}

function isIframeScrollSnapshot(value: unknown): value is IframeScrollSnapshot {
  if (!value || typeof value !== 'object') {
    return false
  }

  const candidate = value as Record<string, unknown>
  const windowSnapshot = candidate.window
  const elements = candidate.elements

  return Array.isArray(elements)
    && typeof windowSnapshot === 'object'
    && windowSnapshot !== null
    && typeof (windowSnapshot as Record<string, unknown>).left === 'number'
    && typeof (windowSnapshot as Record<string, unknown>).top === 'number'
}
</script>

<template>
  <div
    class="grid flex-1 place-items-center"
    :class="presenter
      ? 'h-full min-h-0 bg-black p-0'
      : 'rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-preview-stage)] p-5 md:p-8'"
  >
    <div
      ref="containerRef"
      class="relative h-full w-full overflow-hidden"
      :class="presenter
        ? 'min-h-0 bg-black'
        : 'min-h-[360px] rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-canvas)]'"
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

      <div
        v-else-if="shouldShowFrame"
        class="absolute inset-0 flex items-center justify-center"
        :class="presenter ? 'p-0' : 'p-5'"
      >
        <div
          class="relative overflow-hidden bg-white"
          :class="presenter ? '' : 'rounded-[28px] shadow-[var(--shadow-canvas)]'"
          :style="frameBoxStyle"
        >
          <iframe
            v-if="stableFrame"
            ref="stableFrameRef"
            :key="stableFrame.key"
            :src="stableFrame.src"
            sandbox="allow-scripts allow-same-origin"
            title="PPT slide preview"
            :style="iframeStyle"
          />
          <iframe
            v-if="loadingFrame"
            ref="loadingFrameRef"
            :key="loadingFrame.key"
            :src="loadingFrame.src"
            sandbox="allow-scripts allow-same-origin"
            title="PPT slide preview loading"
            class="absolute inset-0"
            :class="hasStableFrame ? 'pointer-events-none opacity-0' : ''"
            :style="iframeStyle"
            @load="void handleLoadingFrameLoad()"
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
