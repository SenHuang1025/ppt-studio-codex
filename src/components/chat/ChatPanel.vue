<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { NButton, NSkeleton, NTag } from 'naive-ui'
import ChatInput from '@/components/chat/ChatInput.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import FileCard from '@/components/chat/FileCard.vue'
import FileUploadArea from '@/components/chat/FileUploadArea.vue'
import GlassPanel from '@/components/common/GlassPanel.vue'
import type { AgentEventLogItem, AgentConnectionState, ChatTimelineItem } from '@/types/chat'
import type { UploadedFile } from '@/types/file'

const props = withDefaults(
  defineProps<{
    accept?: string
    chatError?: string | null
    chatLoaded?: boolean
    chatLoading?: boolean
    connectionState: AgentConnectionState
    debugEvents?: AgentEventLogItem[]
    deletingFileIds?: string[]
    disabled?: boolean
    draft: string
    files: UploadedFile[]
    filesError?: string | null
    filesLoading?: boolean
    projectName: string
    submitting?: boolean
    timelineItems: ChatTimelineItem[]
    uploading?: boolean
  }>(),
  {
    accept: '',
    chatError: null,
    chatLoaded: false,
    chatLoading: false,
    debugEvents: () => [],
    deletingFileIds: () => [],
    disabled: false,
    filesError: null,
    filesLoading: false,
    submitting: false,
    uploading: false
  }
)

const emit = defineEmits<{
  deleteFile: [file: UploadedFile]
  'focus-outline': [pageNumber: number]
  'message-reveal-complete': [itemId: string]
  'select-files': [files: File[]]
  submit: [value: string]
  'update:draft': [value: string]
}>()

const scrollContainerRef = ref<HTMLDivElement | null>(null)
const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null)
const debugExpanded = ref(false)

const connectionMeta = computed<{ label: string; toneClass: string }>(() => {
  switch (props.connectionState) {
    case 'connecting':
      return {
        label: '建立连接中',
        toneClass: 'border-[rgba(241,143,1,0.22)] bg-[rgba(241,143,1,0.12)] text-[color:var(--accent-200)]'
      }
    case 'streaming':
      return {
        label: '协作处理中',
        toneClass: 'border-[rgba(104,166,125,0.18)] bg-[rgba(104,166,125,0.12)] text-[color:var(--primary-300)]'
      }
    case 'completed':
      return {
        label: '本轮完成',
        toneClass: 'border-[rgba(104,166,125,0.2)] bg-[rgba(104,166,125,0.14)] text-[color:var(--primary-300)]'
      }
    case 'error':
      return {
        label: '发生错误',
        toneClass: 'border-[rgba(183,91,53,0.18)] bg-[rgba(183,91,53,0.12)] text-[color:#9f4b2a]'
      }
    case 'idle':
    default:
      return {
        label: '等待发送',
        toneClass: 'border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.72)] text-[color:var(--app-text-secondary)]'
      }
  }
})

const showMessageSkeleton = computed<boolean>(() => props.chatLoading && !props.chatLoaded && props.timelineItems.length === 0)
const showEmptyState = computed<boolean>(() => !showMessageSkeleton.value && props.timelineItems.length === 0 && !props.chatError)

watch(
  () => props.timelineItems.length,
  () => {
    void nextTick(() => scrollToBottom('smooth'))
  }
)

watch(
  () => props.connectionState,
  (state) => {
    if (state === 'connecting' || state === 'streaming') {
      void nextTick(() => scrollToBottom('smooth'))
    }
  }
)

function scrollToBottom(behavior: ScrollBehavior = 'auto'): void {
  scrollContainerRef.value?.scrollTo({
    behavior,
    top: scrollContainerRef.value.scrollHeight
  })
}

function handleRevealProgress(): void {
  scrollToBottom('auto')
}

function handleRevealComplete(itemId: string): void {
  emit('message-reveal-complete', itemId)
  scrollToBottom('auto')
}

function focusComposer(): void {
  chatInputRef.value?.focusInput()
}

defineExpose({
  focusComposer
})
</script>

<template>
  <GlassPanel variant="strong" class="flex min-h-0 flex-col gap-5 p-5">
    <div class="flex items-center justify-between gap-3">
      <div>
        <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">AI 协作区</p>
        <h2 class="m-0 text-xl font-semibold">对话工作台</h2>
        <div class="mt-2 text-sm text-[color:var(--app-text-secondary)]">
          结合资料与对话，共同完成 {{ projectName }} 的结构规划。
        </div>
      </div>

      <NTag round :bordered="false" :class="connectionMeta.toneClass">
        {{ connectionMeta.label }}
      </NTag>
    </div>

    <div ref="scrollContainerRef" class="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
      <div
        v-if="chatError"
        class="rounded-[var(--radius-xl)] border border-[rgba(183,91,53,0.16)] bg-[rgba(255,248,237,0.82)] px-4 py-3 text-sm leading-6 text-[color:#9f4b2a]"
      >
        {{ chatError }}
      </div>

      <div v-if="showMessageSkeleton" class="space-y-3">
        <div
          v-for="index in 4"
          :key="index"
          class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.76)] p-4"
        >
          <NSkeleton :sharp="false" height="12px" width="24%" />
          <NSkeleton class="mt-3" :sharp="false" height="14px" width="76%" />
          <NSkeleton class="mt-2" :sharp="false" height="14px" width="68%" />
        </div>
      </div>

      <div
        v-else-if="showEmptyState"
        class="rounded-[var(--radius-2xl)] border border-dashed border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.62)] px-5 py-6"
      >
        <div class="mono-meta text-[10px] uppercase tracking-[0.18em] text-[color:var(--app-text-tertiary)]">Chat Mode</div>
        <div class="mt-3 text-xl font-semibold text-[color:var(--app-text-primary)]">先上传资料，再描述你想做的演示。</div>
        <div class="mt-3 text-sm leading-7 text-[color:var(--app-text-secondary)]">
          可以先拖入表格、文档、PDF 或图片，然后在下方输入区说明受众、目标、页数倾向和你想强调的信息，左侧会持续记录协作过程，右侧会实时整理大纲。
        </div>
      </div>

      <div v-else class="space-y-4">
        <ChatMessage
          v-for="item in timelineItems"
          :key="item.id"
          :item="item"
          @focus-outline="emit('focus-outline', $event)"
          @reveal-complete="handleRevealComplete"
          @reveal-progress="handleRevealProgress"
        />
      </div>
    </div>

    <div class="mt-auto space-y-4">
      <section class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.74)] px-4 py-3">
        <button
          class="flex w-full items-center justify-between gap-3 border-none bg-transparent p-0 text-left"
          type="button"
          @click="debugExpanded = !debugExpanded"
        >
          <div>
            <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">开发辅助</div>
            <div class="mt-1 text-sm font-medium text-[color:var(--app-text-primary)]">实时事件日志</div>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-[11px] text-[color:var(--app-text-tertiary)]">{{ debugEvents.length }} 条</span>
            <span class="text-sm text-[color:var(--app-text-secondary)]">{{ debugExpanded ? '收起' : '展开' }}</span>
          </div>
        </button>

        <div v-if="debugExpanded" class="mt-3 space-y-2">
          <div
            v-if="debugEvents.length === 0"
            class="rounded-[var(--radius-lg)] border border-dashed border-[color:var(--app-border-subtle)] px-3 py-3 text-xs leading-6 text-[color:var(--app-text-secondary)]"
          >
            发送一轮真实请求后，这里会收集 `thinking`、`file_parsed`、`outline`、`deliberation_*`、`page_*`、`assistant_message` 和 `done`。
          </div>

          <div
            v-for="event in debugEvents"
            :key="event.id"
            class="rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,248,237,0.72)] px-3 py-3"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="text-xs font-medium text-[color:var(--app-text-primary)]">{{ event.event }}</div>
              <div class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">{{ event.received_at }}</div>
            </div>
            <div class="mt-1 text-xs leading-5 text-[color:var(--app-text-secondary)]">{{ event.summary }}</div>
          </div>
        </div>
      </section>

      <FileUploadArea
        :accept="accept"
        :disabled="disabled || submitting"
        :uploading="uploading"
        @select-files="emit('select-files', $event)"
      />

      <section class="space-y-3">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">项目资料</div>
            <div class="mt-1 text-sm font-medium text-[color:var(--app-text-primary)]">已上传文件</div>
          </div>
          <NTag round :bordered="false" class="border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.72)] text-[color:var(--app-text-secondary)]">
            {{ files.length }} 个
          </NTag>
        </div>

        <div
          v-if="filesError"
          class="rounded-[var(--radius-xl)] border border-[rgba(183,91,53,0.16)] bg-[rgba(255,248,237,0.82)] px-4 py-3 text-sm leading-6 text-[color:#9f4b2a]"
        >
          {{ filesError }}
        </div>

        <div v-else-if="filesLoading" class="space-y-3">
          <div
            v-for="index in 2"
            :key="index"
            class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.76)] p-4"
          >
            <NSkeleton :sharp="false" height="16px" width="58%" />
            <NSkeleton class="mt-3" :sharp="false" height="14px" width="34%" />
          </div>
        </div>

        <div
          v-else-if="files.length === 0"
          class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.58)] px-4 py-4 text-sm leading-6 text-[color:var(--app-text-secondary)]"
        >
          当前还没有项目资料。上传后会先进入对话时间线，再在这里保留完整文件清单，便于继续增删与复查。
        </div>

        <div v-else class="max-h-[220px] space-y-3 overflow-y-auto pr-1">
          <FileCard
            v-for="file in files"
            :key="file.id"
            :deleting="deletingFileIds.includes(file.id)"
            :file="file"
            @delete="emit('deleteFile', $event)"
          />
        </div>
      </section>

      <ChatInput
        ref="chatInputRef"
        :accept="accept"
        :disabled="disabled"
        :model-value="draft"
        :submitting="submitting"
        :uploading="uploading"
        @select-files="emit('select-files', $event)"
        @submit="emit('submit', $event)"
        @update:model-value="emit('update:draft', $event)"
      />
    </div>
  </GlassPanel>
</template>
