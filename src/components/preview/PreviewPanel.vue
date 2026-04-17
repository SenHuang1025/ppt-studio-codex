<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { NButton, NTag } from 'naive-ui'
import GlassPanel from '@/components/common/GlassPanel.vue'
import ExportTaskPanel from '@/components/preview/ExportTaskPanel.vue'
import FullscreenPresenter from '@/components/preview/FullscreenPresenter.vue'
import GenerationProgressBanner from '@/components/preview/GenerationProgressBanner.vue'
import PageOptimizeChat from '@/components/preview/PageOptimizeChat.vue'
import PreviewProjectChatEntry from '@/components/preview/PreviewProjectChatEntry.vue'
import QuickActions from '@/components/preview/QuickActions.vue'
import SlideControls from '@/components/preview/SlideControls.vue'
import SlideRenderer from '@/components/preview/SlideRenderer.vue'
import ThemePresetPicker from '@/components/preview/ThemePresetPicker.vue'
import ThumbnailNav from '@/components/preview/ThumbnailNav.vue'
import VersionHistoryDrawer from '@/components/preview/VersionHistoryDrawer.vue'
import type { AgentConnectionState, AgentEventLogItem, ChatTimelineItem } from '@/types/chat'
import type { ProjectExportTask } from '@/types/export'
import type { PageVersion } from '@/types/project'
import type {
  PreviewPageItem,
  PreviewRefreshRequest,
  PreviewRenderTargetKind,
  PreviewVersionSelection,
  WorkspaceGenerationProgressState
} from '@/types/preview'
import type { ThemeConfig } from '@/types/theme'
import {
  formatPreviewPageType,
  formatPreviewUpdatedAt,
  formatPreviewVersionHistoryLabel,
  getPreviewPageStatusLabel
} from '@/utils/preview'

const props = withDefaults(defineProps<{
  activeThemeId: string
  activeOptimizingPageNumber?: number | null
  applyingThemeId?: string | null
  exportStarting?: boolean
  exportTask?: ProjectExportTask | null
  fullscreenActive?: boolean
  optimizeChatConnectionState?: AgentConnectionState
  optimizeCurrentActionLabel?: string | null
  optimizeChatDebugEvents?: AgentEventLogItem[]
  optimizeChatDraft?: string
  optimizeChatError?: string | null
  optimizeChatLoaded?: boolean
  optimizeChatLoading?: boolean
  optimizePreviewRefreshRequest?: PreviewRefreshRequest | null
  optimizeConfirmingPage?: boolean
  optimizeChatSubmitting?: boolean
  optimizeChatTimelineItems?: ChatTimelineItem[]
  projectChatExpanded?: boolean
  projectChatLoaded?: boolean
  projectChatLoading?: boolean
  projectChatTimelineItems?: ChatTimelineItem[]
  currentPageNumber: number
  generationProgress: WorkspaceGenerationProgressState
  versionDrawerLoading?: boolean
  versionDrawerPageNumber?: number | null
  versionDrawerRollingBack?: boolean
  versionDrawerRollingBackVersion?: number | null
  versionDrawerSelectedVersion?: PreviewVersionSelection | null
  versionDrawerShow?: boolean
  versionDrawerVersions?: PageVersion[]
  themeError?: string | null
  themeLoading?: boolean
  themeSyncing?: boolean
  themes: ThemeConfig[]
  items: PreviewPageItem[]
}>(), {
  activeOptimizingPageNumber: null,
  applyingThemeId: null,
  exportStarting: false,
  exportTask: null,
  fullscreenActive: false,
  optimizeChatConnectionState: 'idle',
  optimizeCurrentActionLabel: null,
  optimizeChatDebugEvents: () => [],
  optimizeChatDraft: '',
  optimizeChatError: null,
  optimizeChatLoaded: false,
  optimizeChatLoading: false,
  optimizePreviewRefreshRequest: null,
  optimizeConfirmingPage: false,
  optimizeChatSubmitting: false,
  optimizeChatTimelineItems: () => [],
  projectChatExpanded: false,
  projectChatLoaded: false,
  projectChatLoading: false,
  projectChatTimelineItems: () => [],
  versionDrawerLoading: false,
  versionDrawerPageNumber: null,
  versionDrawerRollingBack: false,
  versionDrawerRollingBackVersion: null,
  versionDrawerSelectedVersion: null,
  versionDrawerShow: false,
  versionDrawerVersions: () => [],
  themeError: null,
  themeLoading: false,
  themeSyncing: false
})

const emit = defineEmits<{
  applyTheme: [theme: ThemeConfig]
  deletePage: [pageNumber: number]
  downloadExportArtifact: []
  duplicatePage: [pageNumber: number]
  enterFullscreen: []
  exitFullscreen: []
  fullscreenError: [message: string]
  insertPageAfter: [pageNumber: number]
  nextPage: []
  openChatMode: []
  optimizeConfirmPage: []
  optimizeMessageRevealComplete: [itemId: string]
  projectMessageRevealComplete: [itemId: string]
  optimizeQuickPrompt: [payload: { actionLabel: string; prompt: string }]
  optimizeRegeneratePage: []
  optimizeSubmit: [value: string]
  previewPageVersion: [version: PageVersion]
  previousPage: []
  reorderPages: [pageNumbers: number[]]
  rollbackPageVersion: [version: PageVersion]
  retryTheme: []
  selectPage: [pageNumber: number]
  showPageVersionHistory: [pageNumber: number]
  startExportPdf: []
  'update:projectChatExpanded': [value: boolean]
  'update:versionDrawerShow': [value: boolean]
  'update:optimizeChatDraft': [value: string]
}>()

const rendererManualRefreshTick = ref(0)
const fullscreenPresenterRef = ref<InstanceType<typeof FullscreenPresenter> | null>(null)
const pageOptimizeChatRef = ref<InstanceType<typeof PageOptimizeChat> | null>(null)
const currentPageItem = computed<PreviewPageItem | null>(() =>
  props.items.find((item) => item.pageNumber === props.currentPageNumber) ?? props.items[0] ?? null
)
const totalPages = computed<number>(() => props.items.length)
const canGoPrevious = computed<boolean>(() => props.currentPageNumber > 1)
const canGoNext = computed<boolean>(() => props.currentPageNumber < totalPages.value)
const currentPageStatusLabel = computed<string>(() =>
  getPreviewPageStatusLabel(currentPageItem.value?.status ?? 'pending')
)
const currentPageStatusTagType = computed<'default' | 'success' | 'warning'>(() => {
  switch (currentPageItem.value?.status) {
    case 'confirmed':
      return 'success'
    case 'generated':
      return 'success'
    case 'generating':
      return 'warning'
    default:
      return 'default'
  }
})
const currentPageTitle = computed<string>(() =>
  currentPageItem.value?.title ?? `第 ${props.currentPageNumber} 页`
)
const currentPageTypeLabel = computed<string>(() => formatPreviewPageType(currentPageItem.value?.pageType))
const currentPageVersionLabel = computed<string>(() =>
  currentPageItem.value?.version ? `v${currentPageItem.value.version}` : '等待版本'
)
const currentPageUpdatedLabel = computed<string>(() => formatPreviewUpdatedAt(currentPageItem.value?.updatedAt))
const currentPageLayoutLabel = computed<string>(() => currentPageItem.value?.layout || '等待大纲布局')
const currentPageContentBrief = computed<string>(() =>
  currentPageItem.value?.contentBrief || '当前页摘要会在 outline 与 generated page 信息稳定后持续补齐。'
)
const currentPreviewVersionLabel = computed<string | null>(() =>
  formatPreviewVersionHistoryLabel(
    props.versionDrawerSelectedVersion?.pageNumber === (currentPageItem.value?.pageNumber ?? props.currentPageNumber)
      ? props.versionDrawerSelectedVersion
      : null
  )
)
const currentPageHasGeneratedCode = computed<boolean>(() => Boolean(currentPageItem.value?.hasGeneratedCode))
const canEnterFullscreen = computed<boolean>(() => totalPages.value > 0)
const canExportPdf = computed<boolean>(() => {
  if (props.exportStarting) {
    return false
  }

  if (props.exportTask && ['pending', 'running'].includes(props.exportTask.status)) {
    return false
  }

  if (props.generationProgress.isGenerationActive || props.items.length === 0) {
    return false
  }

  return props.items.every((item) => item.hasGeneratedCode)
})
const exportDisabledReason = computed<string>(() => {
  if (props.exportStarting) {
    return '正在提交导出任务。'
  }

  if (props.exportTask && ['pending', 'running'].includes(props.exportTask.status)) {
    return '当前已有导出任务在执行。'
  }

  if (props.items.length === 0) {
    return '当前项目还没有可导出的页面。'
  }

  if (props.generationProgress.isGenerationActive) {
    return '页面仍在生成中，全部完成后才能导出 PDF。'
  }

  if (props.items.some((item) => !item.hasGeneratedCode)) {
    return '仍有页面未生成完成，暂时不能导出 PDF。'
  }

  return ''
})
const canRefreshCurrentPage = computed<boolean>(() =>
  Boolean(currentRendererOverrideCode.value)
    || currentPageItem.value?.status === 'generated'
    || currentPageItem.value?.status === 'confirmed'
)
const refreshDisabledReason = computed<string>(() => {
  if (currentRendererOverrideCode.value) {
    return ''
  }

  switch (currentPageItem.value?.status) {
    case 'generating':
      return '当前页还在生成中，完成后才能刷新 iframe。'
    case 'confirmed':
      return ''
    case 'generated':
      return ''
    default:
      return '当前页尚未生成，暂时没有可刷新的预览画面。'
  }
})
const pageInfoRows = computed<Array<{ label: string; value: string }>>(() => [
  { label: '页码', value: `第 ${currentPageItem.value?.pageNumber ?? props.currentPageNumber} 页` },
  { label: '状态', value: currentPageStatusLabel.value },
  { label: '页面类型', value: currentPageTypeLabel.value },
  { label: '版本', value: currentPageVersionLabel.value },
  { label: '最后更新时间', value: currentPageUpdatedLabel.value },
  { label: 'Vue SFC', value: currentPageHasGeneratedCode.value ? '已生成' : '尚未写入' }
])
const currentRendererOverrideCode = computed<string | null>(() =>
  props.versionDrawerSelectedVersion?.pageNumber === (currentPageItem.value?.pageNumber ?? props.currentPageNumber)
    ? props.versionDrawerSelectedVersion.vueCode
    : null
)
const currentRendererTargetKind = computed<PreviewRenderTargetKind>(() =>
  currentRendererOverrideCode.value ? 'version' : 'live'
)
const currentRendererSignature = computed<string>(() => {
  const pageNumber = currentPageItem.value?.pageNumber ?? props.currentPageNumber

  if (currentRendererTargetKind.value === 'version' && props.versionDrawerSelectedVersion) {
    return [
      'version',
      pageNumber,
      props.versionDrawerSelectedVersion.sourceVersion,
      props.versionDrawerSelectedVersion.previewToken
    ].join(':')
  }

  const refreshRequest = props.optimizePreviewRefreshRequest
  const requestedVersion = refreshRequest?.pageNumber === pageNumber ? refreshRequest.version : null

  return [
    'live',
    pageNumber,
    currentPageItem.value?.status ?? 'pending',
    currentPageItem.value?.generatedPage?.id ?? 'page-slot',
    requestedVersion ?? currentPageItem.value?.version ?? 0
  ].join(':')
})
const currentRendererAutoRefreshSequence = computed<number>(() => {
  const pageNumber = currentPageItem.value?.pageNumber ?? props.currentPageNumber
  if (currentRendererTargetKind.value !== 'live') {
    return 0
  }

  return props.optimizePreviewRefreshRequest?.pageNumber === pageNumber
    ? props.optimizePreviewRefreshRequest.sequence
    : 0
})
const rendererRefreshToken = computed<string>(() =>
  [
    currentRendererSignature.value,
    `auto:${currentRendererAutoRefreshSequence.value}`,
    `manual:${rendererManualRefreshTick.value}`
  ].join('|')
)

onMounted(() => {
  window.addEventListener('keydown', handleWindowKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
  if (props.fullscreenActive) {
    emit('exitFullscreen')
  }
})

function handleWindowKeydown(event: KeyboardEvent): void {
  if (event.defaultPrevented || event.key !== 'F5' || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
    return
  }

  event.preventDefault()

  if (!props.fullscreenActive && canEnterFullscreen.value) {
    requestFullscreen()
  }
}

function requestCurrentPageRefresh(): void {
  if (!canRefreshCurrentPage.value) {
    return
  }

  rendererManualRefreshTick.value += 1
}

function focusOptimizeComposer(): void {
  pageOptimizeChatRef.value?.focusComposer()
}

function requestFullscreen(): void {
  if (!canEnterFullscreen.value) {
    return
  }

  emit('enterFullscreen')
  void fullscreenPresenterRef.value?.enterFullscreen()
}

defineExpose({
  focusOptimizeComposer
})
</script>

<template>
  <div class="grid min-h-[780px] gap-6 xl:grid-cols-[220px_minmax(0,1fr)_360px]">
    <GlassPanel class="flex min-h-0 flex-col gap-4 p-4">
      <ThumbnailNav
        :current-page-number="currentPageNumber"
        :generation-progress="generationProgress"
        :items="items"
        @delete-page="emit('deletePage', $event)"
        @duplicate-page="emit('duplicatePage', $event)"
        @insert-page-after="emit('insertPageAfter', $event)"
        @open-version-history="emit('showPageVersionHistory', $event)"
        @reorder-pages="emit('reorderPages', $event)"
        @select-page="emit('selectPage', $event)"
      />
    </GlassPanel>

    <section class="workspace-solid flex min-h-0 flex-col gap-5 rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] p-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">稳定画布</p>
          <h2 class="m-0 text-xl font-semibold">第 {{ currentPageItem?.pageNumber ?? currentPageNumber }} 页 · {{ currentPageTitle }}</h2>
          <div class="mt-2 text-sm text-[color:var(--app-text-secondary)]">
            {{ currentPageContentBrief }}
          </div>
        </div>

        <div class="flex items-center gap-2">
          <NButton secondary strong :disabled="!canEnterFullscreen" @click="requestFullscreen">
            全屏
          </NButton>
          <NTag round :bordered="false" :type="currentPageStatusTagType">
            {{ currentPageStatusLabel }}
          </NTag>
          <NTag round :bordered="false" type="default">
            {{ currentPageTypeLabel }}
          </NTag>
          <NTag round :bordered="false" type="default">
            {{ currentPageVersionLabel }}
          </NTag>
          <NTag v-if="currentPreviewVersionLabel" round :bordered="false" type="warning">
            {{ currentPreviewVersionLabel }}
          </NTag>
        </div>
      </div>

      <GenerationProgressBanner
        :current-page-number="currentPageItem?.pageNumber ?? currentPageNumber"
        :progress="generationProgress"
      />

      <ExportTaskPanel
        :disabled="!canExportPdf"
        :disabled-reason="exportDisabledReason"
        :starting="exportStarting"
        :task="exportTask"
        @download-artifact="emit('downloadExportArtifact')"
        @start-pdf="emit('startExportPdf')"
      />

      <SlideRenderer
        :current-generation-stage-label="generationProgress.currentGenerationStageLabel"
        :generation-active="generationProgress.isGenerationActive"
        :generation-active-page-number="generationProgress.currentGeneratingPageNumber"
        :page-number="currentPageItem?.pageNumber ?? currentPageNumber"
        :page-status="currentPageItem?.status ?? 'pending'"
        :page-title="currentPageItem?.title ?? `第 ${currentPageNumber} 页`"
        :preview-override-code="currentRendererOverrideCode"
        :refresh-token="rendererRefreshToken"
      />

      <SlideControls
        :can-go-next="canGoNext"
        :can-go-previous="canGoPrevious"
        :can-refresh="canRefreshCurrentPage"
        :current-page-number="currentPageItem?.pageNumber ?? currentPageNumber"
        :current-page-status="currentPageItem?.status ?? 'pending'"
        :current-page-title="currentPageTitle"
        :keyboard-enabled="!fullscreenActive"
        :refresh-disabled-reason="refreshDisabledReason"
        :total-pages="Math.max(totalPages, 1)"
        @next="emit('nextPage')"
        @previous="emit('previousPage')"
        @refresh="requestCurrentPageRefresh"
      />
    </section>

    <GlassPanel variant="strong" class="flex min-h-0 flex-col gap-5 p-5">
      <QuickActions
        :busy="optimizeChatSubmitting || optimizeConfirmingPage"
        :confirming="optimizeConfirmingPage"
        :current-action-label="optimizeCurrentActionLabel"
        :current-page-item="currentPageItem"
        :current-page-number="currentPageNumber"
        :disabled="!currentPageHasGeneratedCode"
        @confirm-page="emit('optimizeConfirmPage')"
        @quick-prompt="emit('optimizeQuickPrompt', $event)"
        @regenerate-page="emit('optimizeRegeneratePage')"
      />

      <ThemePresetPicker
        :active-theme-id="activeThemeId"
        :applying-theme-id="applyingThemeId"
        :error="themeError"
        :loading="themeLoading"
        :syncing="themeSyncing"
        :themes="themes"
        @apply="emit('applyTheme', $event)"
        @retry="emit('retryTheme')"
      />

      <PreviewProjectChatEntry
        :current-page-number="currentPageNumber"
        :expanded="projectChatExpanded"
        :loaded="projectChatLoaded"
        :loading="projectChatLoading"
        :timeline-items="projectChatTimelineItems"
        @back-to-chat="emit('openChatMode')"
        @focus-page="emit('selectPage', $event)"
        @message-reveal-complete="emit('projectMessageRevealComplete', $event)"
        @toggle="emit('update:projectChatExpanded', $event)"
      />

      <div class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4">
        <div class="mono-meta mb-3 text-[color:var(--app-text-tertiary)]">当前页信息</div>
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
          <div
            v-for="row in pageInfoRows"
            :key="row.label"
            class="rounded-[var(--radius-lg)] border border-[rgba(131,53,0,0.08)] bg-[rgba(255,255,255,0.62)] px-3 py-2.5"
          >
            <div class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">{{ row.label }}</div>
            <div class="mt-1 text-sm font-medium text-[color:var(--app-text-primary)]">{{ row.value }}</div>
          </div>
        </div>
        <div class="mt-4 space-y-3 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          <div>
            <div class="mono-meta mb-1 text-[10px] text-[color:var(--app-text-tertiary)]">Layout</div>
            <div>{{ currentPageLayoutLabel }}</div>
          </div>
          <div>
            <div class="mono-meta mb-1 text-[10px] text-[color:var(--app-text-tertiary)]">Content Brief</div>
            <div>{{ currentPageContentBrief }}</div>
          </div>
        </div>
      </div>

      <PageOptimizeChat
        ref="pageOptimizeChatRef"
        :active-optimizing-page-number="activeOptimizingPageNumber"
        :connection-state="optimizeChatConnectionState"
        :current-page-item="currentPageItem"
        :debug-events="optimizeChatDebugEvents"
        :disabled="!currentPageHasGeneratedCode"
        :draft="optimizeChatDraft"
        :error="optimizeChatError"
        :loaded="optimizeChatLoaded"
        :loading="optimizeChatLoading"
        :page-updated-at="currentPageUpdatedLabel"
        :submitting="optimizeChatSubmitting"
        :timeline-items="optimizeChatTimelineItems"
        @message-reveal-complete="emit('optimizeMessageRevealComplete', $event)"
        @submit="emit('optimizeSubmit', $event)"
        @update:draft="emit('update:optimizeChatDraft', $event)"
      />
    </GlassPanel>

    <VersionHistoryDrawer
      :loading="versionDrawerLoading"
      :page-number="versionDrawerPageNumber ?? currentPageNumber"
      :rolling-back="versionDrawerRollingBack"
      :rolling-back-version="versionDrawerRollingBackVersion"
      :selected-version="versionDrawerSelectedVersion ?? null"
      :show="versionDrawerShow"
      :versions="versionDrawerVersions"
      @close="emit('update:versionDrawerShow', false)"
      @preview-version="emit('previewPageVersion', $event)"
      @rollback-version="emit('rollbackPageVersion', $event)"
      @update:show="emit('update:versionDrawerShow', $event)"
    />

    <FullscreenPresenter
      ref="fullscreenPresenterRef"
      :active="fullscreenActive"
      :can-go-next="canGoNext"
      :can-go-previous="canGoPrevious"
      :current-generation-stage-label="generationProgress.currentGenerationStageLabel"
      :generation-active="generationProgress.isGenerationActive"
      :generation-active-page-number="generationProgress.currentGeneratingPageNumber"
      :page-number="currentPageItem?.pageNumber ?? currentPageNumber"
      :page-status="currentPageItem?.status ?? 'pending'"
      :page-title="currentPageItem?.title ?? `第 ${currentPageNumber} 页`"
      :preview-override-code="currentRendererOverrideCode"
      :refresh-token="rendererRefreshToken"
      :total-pages="Math.max(totalPages, 1)"
      @close="emit('exitFullscreen')"
      @fullscreen-error="emit('fullscreenError', $event)"
      @next-page="emit('nextPage')"
      @previous-page="emit('previousPage')"
    />
  </div>
</template>
