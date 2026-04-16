<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NModal, NPopover, NTag } from 'naive-ui'
import type { PreviewPageItem } from '@/types/preview'

interface QuickActionOption {
  description: string
  key: string
  label: string
  prompt: string
}

const COLOR_SCHEME_OPTIONS: QuickActionOption[] = [
  {
    key: 'warm-earth',
    label: '暖杏土棕',
    description: '偏自然纸感，适合汇报与策略页。',
    prompt: '将这一页的主色调改为暖杏与土棕，整体更自然、更有纸感。'
  },
  {
    key: 'forest-sage',
    label: '松针鼠尾草',
    description: '沉稳偏专业，适合数据和流程页。',
    prompt: '将这一页的主色调改为松针绿与鼠尾草绿，保持专业和克制。'
  },
  {
    key: 'sunset-copper',
    label: '夕照铜橙',
    description: '更有层次和视觉焦点，适合亮点展示。',
    prompt: '将这一页的主色调改为夕照铜橙，强化层次与视觉焦点。'
  },
  {
    key: 'ink-stone',
    label: '墨灰砂石',
    description: '低彩高对比，适合严肃信息表达。',
    prompt: '将这一页的主色调改为墨灰与砂石色，保持高对比和冷静表达。'
  }
]

const LAYOUT_OPTIONS: QuickActionOption[] = [
  {
    key: 'left-right',
    label: '左右分栏',
    description: '更适合一侧文字、一侧图表或图片。',
    prompt: '将这一页改为左右分栏布局，信息分区更清晰，保持内容层级稳定。'
  },
  {
    key: 'top-bottom',
    label: '上下分栏',
    description: '更适合标题摘要在上、内容在下。',
    prompt: '将这一页改为上下分栏布局，上方聚焦标题摘要，下方承载主要内容。'
  },
  {
    key: 'grid',
    label: '网格',
    description: '更适合卡片型并列信息。',
    prompt: '将这一页改为网格布局，让卡片与信息块排列更整齐均衡。'
  },
  {
    key: 'centered',
    label: '居中',
    description: '更适合单核心观点或主视觉场景。',
    prompt: '将这一页改为居中布局，突出核心信息，减少分散元素。'
  }
]

const ANIMATION_OPTIONS: QuickActionOption[] = [
  {
    key: 'fade',
    label: '淡入',
    description: '克制柔和，适合大多数汇报场景。',
    prompt: '将这一页的动效调整为淡入风格，过渡更柔和克制。'
  },
  {
    key: 'bounce',
    label: '弹跳',
    description: '更有节奏感，适合亮点或年轻化页面。',
    prompt: '将这一页的动效调整为轻微弹跳风格，但避免夸张和影响专业感。'
  },
  {
    key: 'slide',
    label: '滑动',
    description: '更强调结构推进，适合流程或时间线。',
    prompt: '将这一页的动效调整为滑动风格，突出信息进入的方向感。'
  },
  {
    key: 'none',
    label: '无',
    description: '移除多余动画，保持静态稳定。',
    prompt: '移除这一页中不必要的动画效果，保持静态、清晰、稳定。'
  }
]

const props = withDefaults(defineProps<{
  busy?: boolean
  currentPageItem: PreviewPageItem | null
  currentPageNumber: number
  currentActionLabel?: string | null
  disabled?: boolean
  confirming?: boolean
}>(), {
  busy: false,
  currentActionLabel: null,
  disabled: false,
  confirming: false
})

const emit = defineEmits<{
  confirmPage: []
  quickPrompt: [payload: { actionLabel: string; prompt: string }]
  regeneratePage: []
}>()

const colorPopoverVisible = ref(false)
const layoutPopoverVisible = ref(false)
const animationPopoverVisible = ref(false)
const regenerateConfirmVisible = ref(false)

const pageTitle = computed<string>(() => props.currentPageItem?.title ?? `第 ${props.currentPageNumber} 页`)
const disabledReason = computed<string>(() => {
  if (props.busy) {
    return props.currentActionLabel?.trim()
      ? `当前正在执行「${props.currentActionLabel.trim()}」。`
      : '当前页操作处理中，请稍候。'
  }

  if (props.disabled) {
    return '当前页尚未生成，暂时不能执行快捷操作。'
  }

  return ''
})
const isConfirmed = computed<boolean>(() => props.currentPageItem?.generatedPage?.status === 'confirmed')

function handlePresetSelect(option: QuickActionOption, categoryLabel: string): void {
  if (props.disabled || props.busy) {
    return
  }

  if (categoryLabel === '换配色') {
    colorPopoverVisible.value = false
  } else if (categoryLabel === '换布局') {
    layoutPopoverVisible.value = false
  } else if (categoryLabel === '换动画') {
    animationPopoverVisible.value = false
  }

  emit('quickPrompt', {
    actionLabel: `${categoryLabel} · ${option.label}`,
    prompt: option.prompt
  })
}

function handleRegenerate(): void {
  if (props.disabled || props.busy) {
    return
  }

  regenerateConfirmVisible.value = true
}

function handleRegenerateConfirm(): void {
  regenerateConfirmVisible.value = false
  emit('regeneratePage')
}

function handleConfirmPage(): void {
  if (props.disabled || props.busy || isConfirmed.value) {
    return
  }

  emit('confirmPage')
}
</script>

<template>
  <section class="rounded-[var(--radius-2xl)] border border-[rgba(131,53,0,0.12)] bg-[linear-gradient(180deg,rgba(255,250,243,0.96)_0%,rgba(250,241,228,0.94)_100%)] p-4 shadow-[var(--shadow-soft)]">
    <div class="flex items-start justify-between gap-3">
      <div>
        <div class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">快捷操作栏</div>
        <h3 class="mt-2 text-base font-semibold text-[color:var(--app-text-primary)]">第 {{ currentPageNumber }} 页快速调整</h3>
        <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          对 {{ pageTitle }} 使用预设优化指令，复用当前页对话链路。
        </div>
      </div>

      <NTag
        round
        :bordered="false"
        :type="isConfirmed ? 'success' : 'default'"
      >
        {{ isConfirmed ? '已确认' : '待确认' }}
      </NTag>
    </div>

    <div
      v-if="disabledReason"
      class="mt-4 rounded-[var(--radius-lg)] border border-[rgba(131,53,0,0.12)] bg-[rgba(255,255,255,0.78)] px-3 py-2.5 text-xs leading-6 text-[color:var(--app-text-secondary)]"
    >
      {{ disabledReason }}
    </div>

    <div class="mt-4 grid gap-3 sm:grid-cols-2">
      <NPopover v-model:show="colorPopoverVisible" trigger="click" placement="bottom-start" :disabled="disabled || busy">
        <template #trigger>
          <NButton strong secondary :disabled="disabled || busy">
            换配色
          </NButton>
        </template>
        <div class="w-[280px] space-y-2">
          <button
            v-for="option in COLOR_SCHEME_OPTIONS"
            :key="option.key"
            class="w-full rounded-[16px] border border-[rgba(131,53,0,0.12)] bg-white px-3 py-3 text-left transition duration-200 hover:border-[rgba(131,53,0,0.24)] hover:bg-[rgba(255,248,240,0.94)]"
            type="button"
            @click="handlePresetSelect(option, '换配色')"
          >
            <div class="text-sm font-medium text-[color:var(--app-text-primary)]">{{ option.label }}</div>
            <div class="mt-1 text-xs leading-5 text-[color:var(--app-text-secondary)]">{{ option.description }}</div>
          </button>
        </div>
      </NPopover>

      <NPopover v-model:show="layoutPopoverVisible" trigger="click" placement="bottom-start" :disabled="disabled || busy">
        <template #trigger>
          <NButton strong secondary :disabled="disabled || busy">
            换布局
          </NButton>
        </template>
        <div class="w-[280px] space-y-2">
          <button
            v-for="option in LAYOUT_OPTIONS"
            :key="option.key"
            class="w-full rounded-[16px] border border-[rgba(131,53,0,0.12)] bg-white px-3 py-3 text-left transition duration-200 hover:border-[rgba(131,53,0,0.24)] hover:bg-[rgba(255,248,240,0.94)]"
            type="button"
            @click="handlePresetSelect(option, '换布局')"
          >
            <div class="text-sm font-medium text-[color:var(--app-text-primary)]">{{ option.label }}</div>
            <div class="mt-1 text-xs leading-5 text-[color:var(--app-text-secondary)]">{{ option.description }}</div>
          </button>
        </div>
      </NPopover>

      <NPopover v-model:show="animationPopoverVisible" trigger="click" placement="bottom-start" :disabled="disabled || busy">
        <template #trigger>
          <NButton strong secondary :disabled="disabled || busy">
            换动画
          </NButton>
        </template>
        <div class="w-[280px] space-y-2">
          <button
            v-for="option in ANIMATION_OPTIONS"
            :key="option.key"
            class="w-full rounded-[16px] border border-[rgba(131,53,0,0.12)] bg-white px-3 py-3 text-left transition duration-200 hover:border-[rgba(131,53,0,0.24)] hover:bg-[rgba(255,248,240,0.94)]"
            type="button"
            @click="handlePresetSelect(option, '换动画')"
          >
            <div class="text-sm font-medium text-[color:var(--app-text-primary)]">{{ option.label }}</div>
            <div class="mt-1 text-xs leading-5 text-[color:var(--app-text-secondary)]">{{ option.description }}</div>
          </button>
        </div>
      </NPopover>

      <NButton strong tertiary :disabled="disabled || busy" @click="handleRegenerate">
        重新生成
      </NButton>
    </div>

    <div class="mt-3 grid gap-3 sm:grid-cols-[1fr_auto]">
      <div class="rounded-[var(--radius-lg)] border border-[rgba(104,166,125,0.14)] bg-[rgba(255,255,255,0.7)] px-3 py-2.5 text-xs leading-6 text-[color:var(--app-text-secondary)]">
        “确认本页”只标记当前页为 `confirmed`，不展开更多页面状态体系。
      </div>
      <NButton
        type="success"
        strong
        :disabled="disabled || busy || isConfirmed"
        :loading="confirming"
        @click="handleConfirmPage"
      >
        {{ isConfirmed ? '已确认' : '确认本页' }}
      </NButton>
    </div>

    <NModal
      v-model:show="regenerateConfirmVisible"
      preset="dialog"
      title="重新生成当前页"
      positive-text="确认重生成"
      negative-text="取消"
      @positive-click="handleRegenerateConfirm"
    >
      <div class="text-sm leading-7 text-[color:var(--app-text-secondary)]">
        这会重新生成第 {{ currentPageNumber }} 页《{{ pageTitle }}》，并覆盖当前预览代码。该操作只针对当前页，不会展开到 4.5 的版本回滚 UI。
      </div>
    </NModal>
  </section>
</template>
