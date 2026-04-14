<script setup lang="ts">
import { computed, ref } from 'vue'
import { NInput, NTag } from 'naive-ui'
import GlassPanel from '@/components/common/GlassPanel.vue'
import GenerationProgressBanner from '@/components/preview/GenerationProgressBanner.vue'
import SlideControls from '@/components/preview/SlideControls.vue'
import SlideRenderer from '@/components/preview/SlideRenderer.vue'
import ThemePresetPicker from '@/components/preview/ThemePresetPicker.vue'
import ThumbnailNav from '@/components/preview/ThumbnailNav.vue'
import type { PreviewPageItem, WorkspaceGenerationProgressState } from '@/types/preview'
import type { ThemeConfig } from '@/types/theme'
import { formatPreviewPageType, formatPreviewUpdatedAt, getPreviewPageStatusLabel } from '@/utils/preview'

const props = withDefaults(defineProps<{
  activeThemeId: string
  applyingThemeId?: string | null
  currentPageNumber: number
  generationProgress: WorkspaceGenerationProgressState
  themeError?: string | null
  themeLoading?: boolean
  themeSyncing?: boolean
  themes: ThemeConfig[]
  items: PreviewPageItem[]
}>(), {
  applyingThemeId: null,
  themeError: null,
  themeLoading: false,
  themeSyncing: false
})

const emit = defineEmits<{
  applyTheme: [theme: ThemeConfig]
  nextPage: []
  previousPage: []
  retryTheme: []
  selectPage: [pageNumber: number]
}>()

const rendererRefreshKey = ref(0)
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
const currentPageHasGeneratedCode = computed<boolean>(() => Boolean(currentPageItem.value?.hasGeneratedCode))
const canRefreshCurrentPage = computed<boolean>(() => currentPageItem.value?.status === 'generated')
const refreshDisabledReason = computed<string>(() => {
  switch (currentPageItem.value?.status) {
    case 'generating':
      return '当前页还在生成中，完成后才能刷新 iframe。'
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

function requestCurrentPageRefresh(): void {
  if (!canRefreshCurrentPage.value) {
    return
  }

  rendererRefreshKey.value += 1
}
</script>

<template>
  <div class="grid min-h-[780px] gap-6 xl:grid-cols-[220px_minmax(0,1fr)_360px]">
    <GlassPanel class="flex min-h-0 flex-col gap-4 p-4">
      <ThumbnailNav
        :current-page-number="currentPageNumber"
        :generation-progress="generationProgress"
        :items="items"
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
          <NTag round :bordered="false" :type="currentPageStatusTagType">
            {{ currentPageStatusLabel }}
          </NTag>
          <NTag round :bordered="false" type="default">
            {{ currentPageTypeLabel }}
          </NTag>
          <NTag round :bordered="false" type="default">
            {{ currentPageVersionLabel }}
          </NTag>
        </div>
      </div>

      <GenerationProgressBanner
        :current-page-number="currentPageItem?.pageNumber ?? currentPageNumber"
        :progress="generationProgress"
      />

      <SlideRenderer
        :current-generation-stage-label="generationProgress.currentGenerationStageLabel"
        :generation-active="generationProgress.isGenerationActive"
        :generation-active-page-number="generationProgress.currentGeneratingPageNumber"
        :page-number="currentPageItem?.pageNumber ?? currentPageNumber"
        :page-status="currentPageItem?.status ?? 'pending'"
        :page-title="currentPageItem?.title ?? `第 ${currentPageNumber} 页`"
        :refresh-key="rendererRefreshKey"
      />

      <SlideControls
        :can-go-next="canGoNext"
        :can-go-previous="canGoPrevious"
        :can-refresh="canRefreshCurrentPage"
        :current-page-number="currentPageItem?.pageNumber ?? currentPageNumber"
        :current-page-status="currentPageItem?.status ?? 'pending'"
        :current-page-title="currentPageTitle"
        :refresh-disabled-reason="refreshDisabledReason"
        :total-pages="Math.max(totalPages, 1)"
        @next="emit('nextPage')"
        @previous="emit('previousPage')"
        @refresh="requestCurrentPageRefresh"
      />
    </section>

    <GlassPanel variant="strong" class="flex min-h-0 flex-col gap-5 p-5">
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

      <div>
        <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">单页优化区</p>
        <h2 class="m-0 text-xl font-semibold">{{ currentPageTitle }}</h2>
        <div class="mt-2 text-sm text-[color:var(--app-text-secondary)]">
          当前聚焦第 {{ currentPageItem?.pageNumber ?? currentPageNumber }} 页，右侧已展示这页的真实 outline / generated 信息。
        </div>
      </div>

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

      <div class="grid gap-3">
        <button
          class="cursor-not-allowed rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,255,255,0.48)] px-4 py-3 text-left opacity-70"
          disabled
          type="button"
        >
          <div class="text-sm text-[color:var(--app-text-primary)]">调整版式平衡</div>
          <div class="mt-1 text-xs text-[color:var(--app-text-secondary)]">Phase 4 接入真实单页优化后开放。</div>
        </button>
        <button
          class="cursor-not-allowed rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,255,255,0.48)] px-4 py-3 text-left opacity-70"
          disabled
          type="button"
        >
          <div class="text-sm text-[color:var(--app-text-primary)]">替换配色强调</div>
          <div class="mt-1 text-xs text-[color:var(--app-text-secondary)]">当前仅展示入口，不执行真实页面改写。</div>
        </button>
        <button
          class="cursor-not-allowed rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,255,255,0.48)] px-4 py-3 text-left opacity-70"
          disabled
          type="button"
        >
          <div class="text-sm text-[color:var(--app-text-primary)]">查看版本历史</div>
          <div class="mt-1 text-xs text-[color:var(--app-text-secondary)]">本阶段只显示版本号，历史抽屉留给后续阶段。</div>
        </button>
      </div>

      <div class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4 text-sm leading-6 text-[color:var(--app-text-secondary)]">
        本阶段重点是把预览浏览与生成反馈补稳：真实页信息可读、翻页可持续、刷新可控。单页优化对话和版本抽屉仍留给后续阶段。
      </div>

      <NInput
        disabled
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 5 }"
        placeholder="单页优化对话将在后续阶段接入；当前输入框仅保留布局与信息层次。"
        size="large"
      />
    </GlassPanel>
  </div>
</template>
