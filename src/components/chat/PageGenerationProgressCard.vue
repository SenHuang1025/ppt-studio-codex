<script setup lang="ts">
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import LinearProgressGlow from '@/components/common/LinearProgressGlow.vue'
import type { PageGenerationProgressChatTimelineItem } from '@/types/chat'
import { getPageGenerationStageName } from '@/utils/preview'

const props = defineProps<{
  item: PageGenerationProgressChatTimelineItem
}>()

const progress = computed(() => props.item.progress)

const statusLabel = computed<string>(() => {
  if (progress.value.generationError) {
    return '生成异常'
  }

  if (progress.value.isGenerationCompleted) {
    return '批量生成完成'
  }

  if (progress.value.isGenerationActive) {
    return '正在逐页生成'
  }

  return '等待继续生成'
})

const statusToneClass = computed<string>(() => {
  if (progress.value.generationError) {
    return 'border-[rgba(183,91,53,0.18)] bg-[rgba(255,238,231,0.92)] text-[color:#9f4b2a]'
  }

  if (progress.value.isGenerationCompleted) {
    return 'border-[rgba(104,166,125,0.18)] bg-[rgba(240,249,242,0.92)] text-[color:var(--primary-300)]'
  }

  return 'border-[rgba(241,143,1,0.18)] bg-[rgba(255,243,226,0.92)] text-[color:var(--accent-200)]'
})

const headline = computed<string>(() => {
  if (progress.value.generationError) {
    return progress.value.totalPages > 0
      ? `生成在 ${progress.value.generatedCount} / ${progress.value.totalPages} 页时中断`
      : '页面生成启动失败'
  }

  if (progress.value.isGenerationCompleted) {
    return `已完成 ${progress.value.generatedCount} / ${progress.value.totalPages} 页生成`
  }

  if (progress.value.currentGeneratingPageNumber && progress.value.totalPages > 0) {
    return `正在生成第 ${progress.value.currentGeneratingPageNumber} / ${progress.value.totalPages} 页：${progress.value.currentGeneratingPageTitle || `第 ${progress.value.currentGeneratingPageNumber} 页`}`
  }

  if (progress.value.isGenerationActive && progress.value.totalPages > 0) {
    return `正在准备生成 ${progress.value.totalPages} 页内容`
  }

  if (progress.value.generatedCount > 0 && progress.value.totalPages > 0) {
    return `已完成 ${progress.value.generatedCount} / ${progress.value.totalPages} 页，等待继续生成`
  }

  return '等待开始页面生成'
})

const stageName = computed<string | null>(() => getPageGenerationStageName(progress.value.currentGenerationStage))
const stageLabel = computed<string | null>(() => progress.value.currentGenerationStageLabel)
const latestCompletedText = computed<string | null>(() => {
  if (!progress.value.latestCompletedPageNumber) {
    return null
  }

  return `最近完成：第 ${progress.value.latestCompletedPageNumber} 页${progress.value.latestCompletedPageTitle ? ` · ${progress.value.latestCompletedPageTitle}` : ''}`
})

const progressTone = computed<'accent' | 'error' | 'primary'>(() => {
  if (progress.value.generationError) {
    return 'error'
  }

  return progress.value.isGenerationCompleted ? 'primary' : 'accent'
})

const messageTime = computed<string>(() => formatMessageTime(props.item.createdAt))

function formatMessageTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}
</script>

<template>
  <article class="max-w-[96%]">
    <div class="rounded-[var(--radius-xl)] border border-[rgba(241,143,1,0.16)] bg-[rgba(255,249,239,0.9)] px-4 py-4 shadow-[var(--shadow-glass-1)]">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--accent-200)]">页面生成进度</div>
          <div class="mt-2 text-base font-semibold text-[color:var(--app-text-primary)]">
            {{ headline }}
          </div>
        </div>

        <NTag round :bordered="false" :class="statusToneClass">
          {{ statusLabel }}
        </NTag>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-[color:var(--app-text-secondary)]">
        <span>{{ progress.generatedCount }} / {{ progress.totalPages || 0 }} 已完成</span>
        <span v-if="progress.generatingCount > 0">{{ progress.generatingCount }} 页生成中</span>
        <span v-if="progress.pendingCount > 0">{{ progress.pendingCount }} 页待生成</span>
        <span v-if="stageLabel">{{ stageLabel }}</span>
      </div>

      <div class="mt-3">
        <LinearProgressGlow
          :animated="progress.isGenerationActive"
          :tone="progressTone"
          :value="progress.visualProgressRatio"
        />
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2">
        <NTag
          v-if="stageName"
          round
          :bordered="false"
          class="border border-[rgba(241,143,1,0.14)] bg-[rgba(255,243,226,0.9)] text-[color:var(--accent-200)]"
        >
          当前阶段 · {{ stageName }}
        </NTag>
        <NTag
          v-if="progress.isGenerationCompleted"
          round
          :bordered="false"
          class="border border-[rgba(104,166,125,0.16)] bg-[rgba(240,249,242,0.92)] text-[color:var(--primary-300)]"
        >
          全部页面已可预览
        </NTag>
      </div>

      <div
        v-if="latestCompletedText"
        class="mt-3 rounded-[var(--radius-lg)] border border-[rgba(104,166,125,0.14)] bg-[rgba(252,248,239,0.88)] px-3 py-2.5 text-sm text-[color:var(--app-text-secondary)]"
      >
        {{ latestCompletedText }}
      </div>

      <div
        v-if="progress.pageGeneratorFallbackDetected"
        class="mt-3 rounded-[var(--radius-lg)] border border-[rgba(241,143,1,0.18)] bg-[rgba(255,244,230,0.92)] px-3 py-2.5 text-sm text-[color:var(--accent-200)]"
      >
        思辨失败，已回退到 Draft。
      </div>

      <div
        v-if="progress.generationError"
        class="mt-3 rounded-[var(--radius-lg)] border border-[rgba(183,91,53,0.18)] bg-[rgba(255,238,231,0.92)] px-3 py-2.5 text-sm leading-6 text-[color:#9f4b2a]"
      >
        {{ progress.generationError }}
      </div>

      <div class="mt-4 text-[11px] text-[color:var(--app-text-tertiary)]">{{ messageTime }}</div>
    </div>
  </article>
</template>
