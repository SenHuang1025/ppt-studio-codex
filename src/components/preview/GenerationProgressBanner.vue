<script setup lang="ts">
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import LinearProgressGlow from '@/components/common/LinearProgressGlow.vue'
import type { WorkspaceGenerationProgressState } from '@/types/preview'
import { getPageGenerationStageName } from '@/utils/preview'

const props = defineProps<{
  currentPageNumber: number
  progress: WorkspaceGenerationProgressState
}>()

const stageName = computed<string | null>(() => getPageGenerationStageName(props.progress.currentGenerationStage))

const headline = computed<string>(() => `已完成 ${props.progress.generatedCount} / ${props.progress.totalPages || 0} 页`)

const summaryText = computed<string>(() => {
  if (props.progress.generationError) {
    return '本轮页面生成已中断'
  }

  if (props.progress.isGenerationCompleted) {
    return '全部页面生成完成'
  }

  if (props.progress.currentGeneratingPageNumber) {
    return `正在生成第 ${props.progress.currentGeneratingPageNumber} 页：${props.progress.currentGeneratingPageTitle || `第 ${props.progress.currentGeneratingPageNumber} 页`}`
  }

  if (props.progress.generatedCount > 0) {
    return '当前没有新的生成任务'
  }

  return '等待开始逐页生成'
})

const canvasNote = computed<string>(() => {
  if (props.progress.generationError) {
    return props.progress.generationError
  }

  if (props.progress.isGenerationActive && props.progress.currentGeneratingPageNumber === props.currentPageNumber) {
    return '当前画布正在等待这一页完成后自动接入预览。'
  }

  if (props.progress.isGenerationActive && props.progress.currentGeneratingPageNumber) {
    return `当前画布保持稳定预览，后台继续生成第 ${props.progress.currentGeneratingPageNumber} 页。`
  }

  if (props.progress.isGenerationCompleted) {
    return '全部页面已可继续浏览，后续单页优化仍留给后续阶段。'
  }

  if (props.progress.generatedCount > 0) {
    return '当前没有新的生成任务，已生成页面可以继续稳定浏览。'
  }

  return '确认大纲后，这里会持续显示整轮逐页生成进度。'
})

const latestCompletedText = computed<string | null>(() => {
  if (!props.progress.latestCompletedPageNumber) {
    return null
  }

  return `最近完成：第 ${props.progress.latestCompletedPageNumber} 页${props.progress.latestCompletedPageTitle ? ` · ${props.progress.latestCompletedPageTitle}` : ''}`
})

const progressTone = computed<'accent' | 'error' | 'primary'>(() => {
  if (props.progress.generationError) {
    return 'error'
  }

  return props.progress.isGenerationCompleted ? 'primary' : 'accent'
})
</script>

<template>
  <div class="rounded-[var(--radius-xl)] border border-[rgba(131,53,0,0.1)] bg-[rgba(255,249,239,0.92)] px-4 py-4 shadow-[var(--shadow-soft)]">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--accent-200)]">生成进度概览</div>
        <div class="mt-2 flex flex-wrap items-center gap-2">
          <h3 class="m-0 text-lg font-semibold text-[color:var(--app-text-primary)]">{{ headline }}</h3>
          <NTag
            v-if="stageName"
            round
            :bordered="false"
            class="border border-[rgba(241,143,1,0.18)] bg-[rgba(255,243,226,0.9)] text-[color:var(--accent-200)]"
          >
            {{ stageName }}
          </NTag>
          <NTag
            v-if="progress.isGenerationCompleted"
            round
            :bordered="false"
            class="border border-[rgba(104,166,125,0.16)] bg-[rgba(240,249,242,0.92)] text-[color:var(--primary-300)]"
          >
            已完成
          </NTag>
          <NTag
            v-else-if="progress.generationError"
            round
            :bordered="false"
            class="border border-[rgba(183,91,53,0.18)] bg-[rgba(255,238,231,0.92)] text-[color:#9f4b2a]"
          >
            异常
          </NTag>
        </div>
        <div class="mt-2 text-sm text-[color:var(--app-text-secondary)]">{{ summaryText }}</div>
      </div>

      <div class="rounded-full border border-[rgba(131,53,0,0.1)] bg-[rgba(255,255,255,0.62)] px-3 py-1 text-right">
        <div class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">{{ progress.generatedCount }} / {{ progress.totalPages || 0 }}</div>
        <div class="text-xs text-[color:var(--app-text-secondary)]">
          {{ progress.currentGenerationStageLabel || (progress.generationError ? '已中断' : progress.isGenerationCompleted ? '全部完成' : progress.isGenerationActive ? '持续生成中' : '静态阶段') }}
        </div>
      </div>
    </div>

    <div class="mt-4">
      <LinearProgressGlow
        :animated="progress.isGenerationActive"
        :tone="progressTone"
        :value="progress.visualProgressRatio"
      />
    </div>

    <div class="mt-3 grid gap-2 text-sm text-[color:var(--app-text-secondary)] lg:grid-cols-[minmax(0,1fr)_minmax(240px,auto)]">
      <div class="rounded-[var(--radius-lg)] border border-[rgba(131,53,0,0.08)] bg-[rgba(255,255,255,0.56)] px-3 py-2.5">
        {{ canvasNote }}
      </div>
      <div
        v-if="latestCompletedText || progress.pageGeneratorFallbackDetected"
        class="rounded-[var(--radius-lg)] border px-3 py-2.5"
        :class="progress.pageGeneratorFallbackDetected
          ? 'border-[rgba(241,143,1,0.18)] bg-[rgba(255,244,230,0.92)] text-[color:var(--accent-200)]'
          : 'border-[rgba(104,166,125,0.14)] bg-[rgba(252,248,239,0.88)] text-[color:var(--app-text-secondary)]'"
      >
        <div v-if="progress.pageGeneratorFallbackDetected">思辨失败，已回退到 Draft。</div>
        <div v-else>{{ latestCompletedText }}</div>
      </div>
    </div>
  </div>
</template>
