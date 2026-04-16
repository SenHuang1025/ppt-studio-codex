<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { NButton, NSkeleton, NTag } from 'naive-ui'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import type { ChatTimelineItem } from '@/types/chat'

const props = withDefaults(defineProps<{
  currentPageNumber: number
  expanded?: boolean
  loaded?: boolean
  loading?: boolean
  timelineItems?: ChatTimelineItem[]
}>(), {
  expanded: false,
  loaded: false,
  loading: false,
  timelineItems: () => []
})

const emit = defineEmits<{
  backToChat: []
  focusPage: [pageNumber: number]
  'message-reveal-complete': [itemId: string]
  toggle: [value: boolean]
}>()

const scrollContainerRef = ref<HTMLDivElement | null>(null)

const itemCountLabel = computed<string>(() => `${props.timelineItems.length} 条`)
const latestItems = computed<ChatTimelineItem[]>(() =>
  props.timelineItems.slice(Math.max(0, props.timelineItems.length - 6))
)
const showSkeleton = computed<boolean>(() => props.loading && !props.loaded && props.timelineItems.length === 0)
const showEmptyState = computed<boolean>(() => !showSkeleton.value && props.timelineItems.length === 0)

watch(
  () => [props.expanded, latestItems.value.length] as const,
  ([expanded]) => {
    if (!expanded) {
      return
    }

    void nextTick(() => {
      scrollContainerRef.value?.scrollTo({
        behavior: 'smooth',
        top: scrollContainerRef.value?.scrollHeight ?? 0
      })
    })
  }
)
</script>

<template>
  <section class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.84)]">
    <button
      class="flex w-full items-center justify-between gap-3 border-none bg-transparent px-4 py-4 text-left"
      type="button"
      @click="emit('toggle', !expanded)"
    >
      <div class="min-w-0">
        <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">项目级对话</div>
        <div class="mt-1 text-sm font-medium text-[color:var(--app-text-primary)]">
          预览中也能查看完整项目会话
        </div>
        <div class="mt-1 text-xs leading-5 text-[color:var(--app-text-secondary)]">
          当前第 {{ currentPageNumber }} 页，展开后可快速回看项目历史，再回到对话模式继续协作。
        </div>
      </div>

      <div class="flex items-center gap-3">
        <NTag round :bordered="false" class="border border-[color:var(--app-border-subtle)] bg-white/70 text-[color:var(--app-text-secondary)]">
          {{ itemCountLabel }}
        </NTag>
        <span class="text-sm text-[color:var(--app-text-secondary)]">{{ expanded ? '收起' : '展开' }}</span>
      </div>
    </button>

    <div v-if="expanded" class="border-t border-[color:var(--app-border-subtle)] px-4 pb-4 pt-4">
      <div class="mb-3 flex items-center justify-between gap-3">
        <div class="text-xs text-[color:var(--app-text-tertiary)]">这里展示项目级完整历史中的最近片段，包含页级优化同步记录。</div>
        <NButton tertiary strong size="small" @click="emit('backToChat')">回到对话模式</NButton>
      </div>

      <div
        ref="scrollContainerRef"
        class="workspace-solid max-h-[320px] space-y-4 overflow-y-auto rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4"
      >
        <div v-if="showSkeleton" class="space-y-3">
          <div
            v-for="index in 3"
            :key="index"
            class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-white p-4"
          >
            <NSkeleton :sharp="false" height="12px" width="24%" />
            <NSkeleton class="mt-3" :sharp="false" height="14px" width="74%" />
            <NSkeleton class="mt-2" :sharp="false" height="14px" width="62%" />
          </div>
        </div>

        <div
          v-else-if="showEmptyState"
          class="rounded-[var(--radius-xl)] border border-dashed border-[color:var(--app-border-subtle)] bg-[rgba(255,251,245,0.78)] px-4 py-5 text-sm leading-6 text-[color:var(--app-text-secondary)]"
        >
          当前项目级对话还没有历史消息。
        </div>

        <ChatMessage
          v-for="item in latestItems"
          :key="item.id"
          :item="item"
          @focus-outline="emit('focusPage', $event)"
          @reveal-complete="emit('message-reveal-complete', $event)"
        />
      </div>
    </div>
  </section>
</template>
