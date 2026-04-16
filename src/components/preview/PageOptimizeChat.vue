<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { NButton, NSkeleton, NTag } from 'naive-ui'
import ChatInput from '@/components/chat/ChatInput.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import type { AgentConnectionState, AgentEventLogItem, ChatTimelineItem } from '@/types/chat'
import type { PreviewPageItem } from '@/types/preview'

const props = withDefaults(defineProps<{
  activeOptimizingPageNumber?: number | null
  connectionState: AgentConnectionState
  currentPageItem: PreviewPageItem | null
  debugEvents?: AgentEventLogItem[]
  disabled?: boolean
  draft: string
  error?: string | null
  loaded?: boolean
  loading?: boolean
  pageUpdatedAt?: string | null
  submitting?: boolean
  timelineItems: ChatTimelineItem[]
}>(), {
  activeOptimizingPageNumber: null,
  debugEvents: () => [],
  disabled: false,
  error: null,
  loaded: false,
  loading: false,
  pageUpdatedAt: null,
  submitting: false
})

const emit = defineEmits<{
  'message-reveal-complete': [itemId: string]
  submit: [value: string]
  'update:draft': [value: string]
}>()

const scrollContainerRef = ref<HTMLDivElement | null>(null)
const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null)
const debugExpanded = ref(false)

const currentPageNumber = computed<number>(() => props.currentPageItem?.pageNumber ?? 1)
const currentPageTitle = computed<string>(() => props.currentPageItem?.title ?? `第 ${currentPageNumber.value} 页`)
const isCurrentPageOptimizing = computed<boolean>(() =>
  props.activeOptimizingPageNumber === currentPageNumber.value
)
const connectionMeta = computed<{ label: string; toneClass: string }>(() => {
  if (isCurrentPageOptimizing.value) {
    return {
      label: `正在优化第 ${currentPageNumber.value} 页`,
      toneClass: 'border-[rgba(241,143,1,0.24)] bg-[rgba(255,244,230,0.94)] text-[color:var(--accent-200)]'
    }
  }

  switch (props.connectionState) {
    case 'connecting':
      return {
        label: '建立连接中',
        toneClass: 'border-[rgba(241,143,1,0.22)] bg-[rgba(241,143,1,0.12)] text-[color:var(--accent-200)]'
      }
    case 'streaming':
      return {
        label: 'Agent 处理中',
        toneClass: 'border-[rgba(104,166,125,0.18)] bg-[rgba(104,166,125,0.12)] text-[color:var(--primary-300)]'
      }
    case 'completed':
      return {
        label: '本轮优化完成',
        toneClass: 'border-[rgba(104,166,125,0.2)] bg-[rgba(104,166,125,0.14)] text-[color:var(--primary-300)]'
      }
    case 'error':
      return {
        label: '本轮优化失败',
        toneClass: 'border-[rgba(183,91,53,0.18)] bg-[rgba(183,91,53,0.12)] text-[color:#9f4b2a]'
      }
    case 'idle':
    default:
      return {
        label: '等待输入',
        toneClass: 'border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.72)] text-[color:var(--app-text-secondary)]'
      }
  }
})
const showSkeleton = computed<boolean>(() => props.loading && !props.loaded && props.timelineItems.length === 0)
const showEmptyState = computed<boolean>(() => !showSkeleton.value && props.timelineItems.length === 0 && !props.error)
const modifiedItemIds = computed<Set<string>>(() => {
  const ids = new Set<string>()

  for (const item of props.timelineItems) {
    if (
      item.type === 'assistant_message'
      && /已修改\s*✅|已修改第\s*\d+\s*页/i.test(item.content)
    ) {
      ids.add(item.id)
    }
  }

  return ids
})
const stagePills = computed<Array<{ active: boolean; label: string }>>(() => {
  const targetItem = [...props.timelineItems]
    .reverse()
    .find((item) => item.type === 'deliberation_message' && item.pageNumber === currentPageNumber.value)

  const activeRoles = new Set(
    targetItem?.type === 'deliberation_message'
      ? targetItem.entries.map((entry) => entry.role)
      : []
  )
  const summaryCompleted = Boolean(targetItem?.type === 'deliberation_message' && targetItem.summary)

  return [
    { active: activeRoles.has('draft') || Boolean(targetItem), label: '草案' },
    { active: activeRoles.has('critic'), label: '评审' },
    { active: activeRoles.has('synthesis') || summaryCompleted, label: '综合' }
  ]
})
const showStageHint = computed<boolean>(() =>
  stagePills.value.some((item) => item.active)
)
const pageMetaLabel = computed<string>(() => {
  const versionLabel = props.currentPageItem?.version ? `v${props.currentPageItem.version}` : '等待版本'
  const messageCountLabel = `${props.currentPageItem?.chatMessageCount ?? 0} 条消息`

  return `${versionLabel} · ${messageCountLabel}`
})

watch(
  () => [props.timelineItems.length, currentPageNumber.value] as const,
  () => {
    void nextTick(() => scrollToBottom('smooth'))
  },
  { immediate: true }
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
  <div class="flex min-h-0 flex-1 flex-col gap-4">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">单页优化对话</p>
        <h2 class="m-0 text-xl font-semibold">{{ currentPageTitle }}</h2>
        <div class="mt-2 text-sm text-[color:var(--app-text-secondary)]">
          当前优化目标：第 {{ currentPageNumber }} 页。发送的所有指令都会自动绑定到这一页。
        </div>
        <div class="mt-2 text-xs text-[color:var(--app-text-tertiary)]">
          {{ pageMetaLabel }}
          <span v-if="pageUpdatedAt"> · 最近更新 {{ pageUpdatedAt }}</span>
        </div>
      </div>

      <NTag round :bordered="false" :class="connectionMeta.toneClass">
        {{ connectionMeta.label }}
      </NTag>
    </div>

    <div
      v-if="showStageHint"
      class="rounded-[var(--radius-xl)] border border-[rgba(241,143,1,0.18)] bg-[rgba(255,247,235,0.94)] px-4 py-3"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--accent-200)]">思辨阶段</span>
        <span
          v-for="stage in stagePills"
          :key="stage.label"
          class="rounded-full border px-2.5 py-1 text-[11px]"
          :class="stage.active
            ? 'border-[rgba(241,143,1,0.24)] bg-[rgba(255,255,255,0.8)] text-[color:var(--accent-200)]'
            : 'border-[color:var(--app-border-subtle)] bg-[rgba(255,252,247,0.7)] text-[color:var(--app-text-tertiary)]'"
        >
          {{ stage.label }}
        </span>
      </div>
      <div class="mt-2 text-xs leading-6 text-[color:var(--app-text-secondary)]">
        默认折叠详细推理，完整阶段内容可在对应消息卡片中展开查看。
      </div>
    </div>

    <div
      v-if="error"
      class="rounded-[var(--radius-xl)] border border-[rgba(183,91,53,0.16)] bg-[rgba(255,248,237,0.82)] px-4 py-3 text-sm leading-6 text-[color:#9f4b2a]"
    >
      {{ error }}
    </div>

    <div
      ref="scrollContainerRef"
      class="workspace-solid min-h-0 flex-1 space-y-4 rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4"
    >
      <div v-if="showSkeleton" class="space-y-3">
        <div
          v-for="index in 4"
          :key="index"
          class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-white p-4"
        >
          <NSkeleton :sharp="false" height="12px" width="22%" />
          <NSkeleton class="mt-3" :sharp="false" height="14px" width="72%" />
          <NSkeleton class="mt-2" :sharp="false" height="14px" width="61%" />
        </div>
      </div>

      <div
        v-else-if="showEmptyState"
        class="rounded-[var(--radius-2xl)] border border-dashed border-[color:var(--app-border-subtle)] bg-[rgba(255,251,245,0.78)] px-5 py-6"
      >
        <div class="mono-meta text-[10px] uppercase tracking-[0.18em] text-[color:var(--app-text-tertiary)]">Page Optimize</div>
        <div class="mt-3 text-lg font-semibold text-[color:var(--app-text-primary)]">
          这页还没有优化记录。
        </div>
        <div class="mt-3 text-sm leading-7 text-[color:var(--app-text-secondary)]">
          可以直接输入“把标题改成红色”“背景更简洁”“把左侧卡片对齐”等指令，Agent 会只针对当前页进行修改。
        </div>
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="item in timelineItems"
          :key="item.id"
          class="relative"
        >
          <div
            v-if="modifiedItemIds.has(item.id)"
            class="pointer-events-none absolute inset-x-3 -top-2 z-1 flex justify-end"
          >
            <span class="rounded-full border border-[rgba(104,166,125,0.22)] bg-[rgba(245,252,247,0.98)] px-2.5 py-1 text-[11px] font-medium text-[color:var(--primary-300)] shadow-[var(--shadow-soft)]">
              已修改 ✅
            </span>
          </div>

          <div
            class="rounded-[var(--radius-2xl)] transition duration-250"
            :class="modifiedItemIds.has(item.id) ? 'border border-[rgba(104,166,125,0.18)] bg-[rgba(245,252,247,0.56)] px-2 py-2' : ''"
          >
            <ChatMessage
              :item="item"
              @reveal-complete="handleRevealComplete"
              @reveal-progress="handleRevealProgress"
            />
          </div>
        </div>
      </div>
    </div>

    <section class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.74)] px-4 py-3">
      <button
        class="flex w-full items-center justify-between gap-3 border-none bg-transparent p-0 text-left"
        type="button"
        @click="debugExpanded = !debugExpanded"
      >
        <div>
          <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">开发辅助</div>
          <div class="mt-1 text-sm font-medium text-[color:var(--app-text-primary)]">页级优化事件</div>
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
          本页发送优化请求后，这里会收集 `thinking`、`page_optimizing`、`deliberation_*`、`page_updated`、`assistant_message` 和 `done`。
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

    <div class="mt-auto rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.86)] p-4">
      <ChatInput
        ref="chatInputRef"
        :disabled="disabled"
        :helper-text="`消息会发送到第 ${currentPageNumber} 页；本阶段不支持在这里上传文件。`"
        :model-value="draft"
        :placeholder="`描述你希望第 ${currentPageNumber} 页如何调整，例如：标题更突出、图表颜色更统一、把左侧留白收紧。`"
        :show-file-upload="false"
        :submit-label="isCurrentPageOptimizing ? '处理中' : '发送优化'"
        :submitting="submitting"
        @submit="emit('submit', $event)"
        @update:model-value="emit('update:draft', $event)"
      />

      <div class="mt-3 flex items-center justify-between gap-3 text-xs text-[color:var(--app-text-tertiary)]">
        <span>翻页后会自动切换到该页独立历史。</span>
        <NButton text type="primary" @click="focusComposer">
          聚焦输入框
        </NButton>
      </div>
    </div>
  </div>
</template>
