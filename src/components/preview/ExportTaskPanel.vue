<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NProgress, NTag } from 'naive-ui'
import type { ProjectExportTask } from '@/types/export'

const props = withDefaults(defineProps<{
  disabled?: boolean
  disabledReason?: string | null
  starting?: boolean
  task?: ProjectExportTask | null
}>(), {
  disabled: false,
  disabledReason: null,
  starting: false,
  task: null
})

const emit = defineEmits<{
  downloadArtifact: []
  startPdf: []
}>()

const isRunning = computed<boolean>(() =>
  props.task?.status === 'pending' || props.task?.status === 'running'
)
const canDownload = computed<boolean>(() =>
  props.task?.status === 'completed' && Boolean(props.task.download_url)
)
const progressPercentage = computed<number>(() => Math.round((props.task?.progress ?? 0) * 100))
const statusTagType = computed<'default' | 'warning' | 'success' | 'error'>(() => {
  switch (props.task?.status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'pending':
    case 'running':
      return 'warning'
    default:
      return 'default'
  }
})
const exportHint = computed<string>(() => {
  if (props.task?.status === 'failed') {
    return props.task.error || '导出任务失败，请检查 Python 后端的导出依赖。'
  }

  if (props.task?.status === 'completed') {
    return props.task.artifact_name
      ? `导出完成，可下载 ${props.task.artifact_name}。`
      : '导出完成，可直接下载 PDF。'
  }

  if (isRunning.value && props.task) {
    if (props.task.current_page_number && props.task.total_pages > 0) {
      return `正在处理第 ${props.task.current_page_number} 页，共 ${props.task.total_pages} 页。`
    }

    return props.task.stage
  }

  return props.disabledReason?.trim() || '导出会按 1920x1080 视口逐页截图，再合并成 PDF。'
})
const artifactMeta = computed<string>(() => {
  if (!props.task?.artifact_size_bytes) {
    return ''
  }

  return formatFileSize(props.task.artifact_size_bytes)
})

function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <section class="rounded-[var(--radius-xl)] border border-[rgba(131,53,0,0.12)] bg-[rgba(255,251,243,0.84)] p-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">导出</div>
        <h3 class="mt-2 text-base font-semibold text-[color:var(--app-text-primary)]">导出当前项目 PDF</h3>
        <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          {{ exportHint }}
        </div>
      </div>

      <NTag round :bordered="false" :type="statusTagType">
        {{ task?.status === 'completed'
          ? '已完成'
          : task?.status === 'failed'
            ? '失败'
            : isRunning
              ? '导出中'
              : '待开始' }}
      </NTag>
    </div>

    <div v-if="task" class="mt-4 space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-3 text-xs text-[color:var(--app-text-tertiary)]">
        <span>{{ task.stage }}</span>
        <span v-if="task.total_pages > 0">{{ task.completed_pages }} / {{ task.total_pages }}</span>
        <span v-if="artifactMeta">{{ artifactMeta }}</span>
      </div>
      <NProgress
        type="line"
        rail-color="rgba(131,53,0,0.1)"
        :show-indicator="false"
        :percentage="progressPercentage"
        :status="task.status === 'failed' ? 'error' : task.status === 'completed' ? 'success' : 'default'"
      />
    </div>

    <div class="mt-4 flex flex-wrap gap-3">
      <NButton
        strong
        secondary
        :disabled="disabled || isRunning"
        :loading="starting"
        @click="emit('startPdf')"
      >
        导出 PDF
      </NButton>
      <NButton
        v-if="canDownload"
        strong
        type="success"
        @click="emit('downloadArtifact')"
      >
        下载文件
      </NButton>
    </div>
  </section>
</template>
