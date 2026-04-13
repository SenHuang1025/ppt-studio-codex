<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NTag } from 'naive-ui'
import type { UploadedFile } from '@/types/file'
import { FILE_PARSE_STATUS_META, formatFileSize, formatUploadedFileType } from '@/utils/file'

const props = withDefaults(
  defineProps<{
    deleting?: boolean
    file: UploadedFile
  }>(),
  {
    deleting: false
  }
)

const emit = defineEmits<{
  delete: [file: UploadedFile]
}>()

const fileTypeLabel = computed<string>(() => formatUploadedFileType(props.file.file_type))
const statusMeta = computed(() => FILE_PARSE_STATUS_META[props.file.parse_status])
const statusClass = computed<string>(() => {
  switch (statusMeta.value.tone) {
    case 'processing':
      return 'border-[rgba(104,166,125,0.18)] bg-[rgba(104,166,125,0.16)] text-[color:var(--primary-300)]'
    case 'success':
      return 'border-[rgba(104,166,125,0.2)] bg-[rgba(104,166,125,0.12)] text-[color:var(--primary-300)]'
    case 'error':
      return 'border-[rgba(183,91,53,0.16)] bg-[rgba(183,91,53,0.12)] text-[color:#9f4b2a]'
    case 'neutral':
    default:
      return 'border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] text-[color:var(--app-text-secondary)]'
  }
})
</script>

<template>
  <article class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4">
    <div class="flex items-start justify-between gap-3">
      <div class="flex min-w-0 items-start gap-3">
        <div
          class="flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] text-[11px] font-semibold tracking-[0.08em] text-[color:var(--primary-300)]"
        >
          {{ fileTypeLabel }}
        </div>

        <div class="min-w-0">
          <div class="truncate text-sm font-semibold">{{ file.original_name }}</div>
          <div class="mt-1 flex flex-wrap gap-3 text-xs text-[color:var(--app-text-secondary)]">
            <span>{{ formatFileSize(file.file_size) }}</span>
            <span>类型 {{ file.file_type }}</span>
          </div>
        </div>
      </div>

      <NButton text size="small" :loading="deleting" @click="emit('delete', file)">删除</NButton>
    </div>

    <div class="mt-3 flex items-center justify-between gap-3">
      <NTag round size="small" :bordered="false" :class="statusClass">
        {{ statusMeta.label }}
      </NTag>
      <div class="text-xs text-[color:var(--app-text-tertiary)]">后续解析流程会直接复用这条记录</div>
    </div>
  </article>
</template>
