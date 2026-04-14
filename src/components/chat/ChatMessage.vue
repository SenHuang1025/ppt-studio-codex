<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import { NButton, NTag } from 'naive-ui'
import ThinkingBubble from '@/components/chat/ThinkingBubble.vue'
import type { ChatTimelineFileAttachment, ChatTimelineItem } from '@/types/chat'
import { FILE_PARSE_STATUS_META, formatFileSize, formatUploadedFileType } from '@/utils/file'

const props = defineProps<{
  item: ChatTimelineItem
}>()

const emit = defineEmits<{
  'focus-outline': [pageNumber: number]
  'reveal-complete': [itemId: string]
  'reveal-progress': []
}>()

const markdown = new MarkdownIt({
  breaks: true,
  html: false,
  linkify: true
})

const deliberationExpanded = ref(false)
const displayedAssistantContent = ref('')
let revealTimer: number | null = null

const messageTime = computed<string>(() => formatMessageTime(props.item.createdAt))
const assistantHtml = computed<string>(() => markdown.render(displayedAssistantContent.value))
const assistantLeadLabel = computed<string>(() => (props.item.type === 'assistant_message' ? 'Agent 回复' : ''))
const outlinePreviewPages = computed(() =>
  props.item.type === 'outline_message' ? props.item.outline?.pages.slice(0, 4) ?? [] : []
)

watch(
  () => props.item.id,
  () => {
    deliberationExpanded.value = false
  }
)

watch(
  () => props.item,
  (item) => {
    stopReveal()

    if (item.type !== 'assistant_message') {
      displayedAssistantContent.value = ''
      return
    }

    if (!item.animate) {
      displayedAssistantContent.value = item.content
      return
    }

    startReveal(item.content, item.id)
  },
  { deep: true, immediate: true }
)

onBeforeUnmount(() => {
  stopReveal()
})

function stopReveal(): void {
  if (revealTimer !== null) {
    window.clearTimeout(revealTimer)
    revealTimer = null
  }
}

function startReveal(content: string, itemId: string): void {
  displayedAssistantContent.value = ''

  if (!content) {
    emit('reveal-complete', itemId)
    return
  }

  let cursor = 0
  const chunkSize = content.length > 360 ? 4 : content.length > 180 ? 2 : 1
  const delay = content.length > 360 ? 10 : 18

  const revealNextChunk = (): void => {
    cursor = Math.min(content.length, cursor + chunkSize)
    displayedAssistantContent.value = content.slice(0, cursor)
    emit('reveal-progress')

    if (cursor >= content.length) {
      revealTimer = null
      emit('reveal-complete', itemId)
      return
    }

    revealTimer = window.setTimeout(revealNextChunk, delay)
  }

  revealNextChunk()
}

function handleOutlineFocus(pageNumber: number | null): void {
  if (pageNumber === null) {
    return
  }

  emit('focus-outline', pageNumber)
}

function resolveFileStatusLabel(file: ChatTimelineFileAttachment): string {
  if (file.parseStatus === 'local') {
    return '本地消息'
  }

  return FILE_PARSE_STATUS_META[file.parseStatus].label
}

function resolveFileStatusClass(file: ChatTimelineFileAttachment): string {
  if (file.parseStatus === 'local') {
    return 'border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.72)] text-[color:var(--app-text-secondary)]'
  }

  const tone = FILE_PARSE_STATUS_META[file.parseStatus].tone
  if (tone === 'processing') {
    return 'border-[rgba(104,166,125,0.18)] bg-[rgba(104,166,125,0.12)] text-[color:var(--primary-300)]'
  }

  if (tone === 'success') {
    return 'border-[rgba(104,166,125,0.2)] bg-[rgba(104,166,125,0.14)] text-[color:var(--primary-300)]'
  }

  if (tone === 'error') {
    return 'border-[rgba(183,91,53,0.18)] bg-[rgba(183,91,53,0.12)] text-[color:#9f4b2a]'
  }

  return 'border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.72)] text-[color:var(--app-text-secondary)]'
}

function resolveStatusClass(item: Extract<ChatTimelineItem, { type: 'status_message' }>): string {
  switch (item.tone) {
    case 'success':
      return 'border-[rgba(104,166,125,0.18)] bg-[rgba(104,166,125,0.12)] text-[color:var(--primary-300)]'
    case 'warning':
      return 'border-[rgba(241,143,1,0.22)] bg-[rgba(241,143,1,0.12)] text-[color:var(--accent-200)]'
    case 'error':
      return 'border-[rgba(183,91,53,0.18)] bg-[rgba(183,91,53,0.12)] text-[color:#9f4b2a]'
    case 'info':
    default:
      return 'border-[rgba(104,166,125,0.14)] bg-[rgba(255,249,239,0.72)] text-[color:var(--app-text-secondary)]'
  }
}

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
  <article v-if="item.type === 'user_message'" class="ml-auto max-w-[86%]">
    <div class="rounded-[var(--radius-xl)] border border-[rgba(241,143,1,0.18)] bg-[rgba(255,243,226,0.92)] px-4 py-3 shadow-[var(--shadow-glass-1)]">
      <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--accent-200)]">你的需求</div>
      <div class="mt-2 whitespace-pre-wrap text-sm leading-7 text-[color:var(--app-text-primary)]">
        {{ item.content }}
      </div>
      <div class="mt-3 text-right text-[11px] text-[color:var(--app-text-tertiary)]">{{ messageTime }}</div>
    </div>
  </article>

  <article v-else-if="item.type === 'assistant_message'" class="max-w-[92%]">
    <div class="rounded-[var(--radius-xl)] border border-[rgba(104,166,125,0.14)] bg-[rgba(255,249,239,0.88)] px-4 py-3 shadow-[var(--shadow-glass-1)]">
      <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">
        {{ assistantLeadLabel }}
      </div>
      <div
        v-if="item.contentFormat === 'markdown'"
        class="assistant-markdown mt-2 text-sm leading-7 text-[color:var(--app-text-primary)]"
        v-html="assistantHtml"
      />
      <div v-else class="mt-2 whitespace-pre-wrap text-sm leading-7 text-[color:var(--app-text-primary)]">
        {{ displayedAssistantContent }}
      </div>
      <div class="mt-3 text-[11px] text-[color:var(--app-text-tertiary)]">{{ messageTime }}</div>
    </div>
  </article>

  <article v-else-if="item.type === 'outline_message'" class="max-w-[96%]">
    <div class="rounded-[var(--radius-xl)] border border-[rgba(104,166,125,0.18)] bg-[rgba(255,250,243,0.94)] px-4 py-4 shadow-[var(--shadow-glass-1)]">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--primary-300)]">大纲结果</div>
          <div class="mt-2 text-base font-semibold text-[color:var(--app-text-primary)]">
            {{ item.outline?.title ?? '已生成新的演示大纲' }}
          </div>
          <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
            {{ item.summary }}
          </div>
        </div>
        <NTag v-if="item.outline" round :bordered="false" class="border border-[rgba(104,166,125,0.16)] bg-[rgba(104,166,125,0.12)] text-[color:var(--primary-300)]">
          {{ item.outline.total_pages }} 页
        </NTag>
      </div>

      <div v-if="outlinePreviewPages.length > 0" class="mt-4 grid gap-2">
        <button
          v-for="page in outlinePreviewPages"
          :key="page.page_number"
          class="flex items-center justify-between rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,248,237,0.82)] px-3 py-3 text-left transition duration-250 hover:border-[color:var(--app-border-strong)] hover:-translate-y-0.5"
          type="button"
          @click="handleOutlineFocus(page.page_number)"
        >
          <div class="min-w-0">
            <div class="text-sm font-medium text-[color:var(--app-text-primary)]">第 {{ page.page_number }} 页 · {{ page.title }}</div>
            <div class="mt-1 line-clamp-2 text-xs leading-5 text-[color:var(--app-text-secondary)]">
              {{ page.content_brief }}
            </div>
          </div>
          <span class="mono-meta shrink-0 text-[10px] text-[color:var(--app-text-tertiary)]">{{ page.type }}</span>
        </button>
      </div>

      <div class="mt-4 flex items-center justify-between gap-3">
        <div class="text-[11px] text-[color:var(--app-text-tertiary)]">{{ messageTime }}</div>
        <NButton text type="primary" @click="handleOutlineFocus(item.focusPageNumber)">
          查看右侧大纲
        </NButton>
      </div>
    </div>
  </article>

  <article v-else-if="item.type === 'file_upload'" class="max-w-[96%]">
    <div class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.86)] px-4 py-4 shadow-[var(--shadow-glass-1)]">
      <div class="flex items-center justify-between gap-3">
        <div>
          <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">文件上传</div>
          <div class="mt-2 text-base font-semibold text-[color:var(--app-text-primary)]">
            已加入 {{ item.files.length }} 个资料文件
          </div>
        </div>
        <div class="text-[11px] text-[color:var(--app-text-tertiary)]">{{ messageTime }}</div>
      </div>

      <div class="mt-4 grid gap-2">
        <div
          v-for="file in item.files"
          :key="file.id"
          class="rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,248,237,0.76)] px-3 py-3"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="truncate text-sm font-medium text-[color:var(--app-text-primary)]">{{ file.name }}</div>
              <div class="mt-1 flex flex-wrap gap-3 text-[11px] text-[color:var(--app-text-secondary)]">
                <span>{{ formatUploadedFileType(file.fileType) }}</span>
                <span>{{ formatFileSize(file.fileSize) }}</span>
              </div>
            </div>
            <span
              class="rounded-full border px-2.5 py-1 text-[11px]"
              :class="resolveFileStatusClass(file)"
            >
              {{ resolveFileStatusLabel(file) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </article>

  <article v-else-if="item.type === 'file_analysis'" class="max-w-[96%]">
    <div class="rounded-[var(--radius-xl)] border border-[rgba(104,166,125,0.14)] bg-[rgba(255,249,239,0.82)] px-4 py-4 shadow-[var(--shadow-glass-1)]">
      <div class="flex items-center justify-between gap-3">
        <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--primary-300)]">文件分析</div>
        <div class="text-[11px] text-[color:var(--app-text-tertiary)]">{{ messageTime }}</div>
      </div>
      <div class="mt-2 text-sm font-semibold text-[color:var(--app-text-primary)]">{{ item.fileName }}</div>
      <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">{{ item.summary }}</div>
    </div>
  </article>

  <article v-else-if="item.type === 'deliberation_message'" class="max-w-[96%]">
    <div class="rounded-[var(--radius-xl)] border border-[rgba(104,166,125,0.16)] bg-[rgba(255,249,239,0.84)] px-4 py-4 shadow-[var(--shadow-glass-1)]">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">思辨过程</div>
          <div class="mt-2 flex flex-wrap items-center gap-2">
            <span class="text-base font-semibold text-[color:var(--app-text-primary)]">{{ item.target }}</span>
            <NTag v-if="item.rounds !== null" round :bordered="false" class="border border-[rgba(104,166,125,0.16)] bg-[rgba(104,166,125,0.12)] text-[color:var(--primary-300)]">
              {{ item.rounds }} 轮
            </NTag>
          </div>
          <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
            {{ item.summary ?? '正在收敛 draft / critic / synthesis 结果。' }}
          </div>
        </div>

        <NButton text type="primary" @click="deliberationExpanded = !deliberationExpanded">
          {{ deliberationExpanded ? '收起' : '展开详情' }}
        </NButton>
      </div>

      <div v-if="deliberationExpanded" class="mt-4 space-y-3">
        <div
          v-for="entry in item.entries"
          :key="entry.id"
          class="rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,248,237,0.82)] px-3 py-3"
        >
          <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">{{ entry.role }}</div>
          <div class="mt-2 whitespace-pre-wrap text-sm leading-6 text-[color:var(--app-text-secondary)]">
            {{ entry.content }}
          </div>
        </div>
      </div>

      <div class="mt-4 text-[11px] text-[color:var(--app-text-tertiary)]">{{ messageTime }}</div>
    </div>
  </article>

  <article v-else-if="item.type === 'status_message'" class="mx-auto w-full max-w-[88%]">
    <div class="rounded-full border px-4 py-2 text-center text-xs leading-5" :class="resolveStatusClass(item)">
      <span class="font-medium">{{ item.label }}</span>
      <span class="mx-1.5 opacity-40">/</span>
      <span>{{ item.content }}</span>
    </div>
  </article>

  <article v-else class="max-w-[92%]">
    <ThinkingBubble :agent="item.agent" :label="item.content" />
  </article>
</template>

<style scoped>
.assistant-markdown:deep(p) {
  margin: 0;
}

.assistant-markdown:deep(p + p) {
  margin-top: 0.75rem;
}

.assistant-markdown:deep(ul),
.assistant-markdown:deep(ol) {
  margin: 0.75rem 0 0;
  padding-left: 1.2rem;
}

.assistant-markdown:deep(li + li) {
  margin-top: 0.3rem;
}

.assistant-markdown:deep(code) {
  border-radius: 999px;
  background: rgba(235, 226, 205, 0.92);
  padding: 0.14rem 0.46rem;
  color: var(--accent-200);
  font-family: var(--font-family-mono);
  font-size: 0.86em;
}

.assistant-markdown:deep(pre) {
  overflow-x: auto;
  border-radius: var(--radius-lg);
  background: rgba(248, 240, 225, 0.94);
  padding: 0.9rem 1rem;
}

.assistant-markdown:deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.assistant-markdown:deep(a) {
  color: var(--primary-300);
  text-decoration: underline;
  text-decoration-color: rgba(104, 166, 125, 0.42);
}
</style>
