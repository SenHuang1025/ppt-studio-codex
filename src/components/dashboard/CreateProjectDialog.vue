<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NInput, NModal } from 'naive-ui'

type ProjectDialogMode = 'create' | 'rename'

const props = withDefaults(
  defineProps<{
    initialName?: string
    mode?: ProjectDialogMode
    pending: boolean
    show: boolean
  }>(),
  {
    initialName: '',
    mode: 'create'
  }
)

const emit = defineEmits<{
  submit: [name: string]
  'update:show': [value: boolean]
}>()

const draftName = ref<string>('')

const dialogTitle = computed<string>(() => (props.mode === 'rename' ? '重命名项目' : '新建项目'))
const dialogDescription = computed<string>(() =>
  props.mode === 'rename'
    ? '更新项目名称后，会直接保留当前项目状态并刷新卡片信息。'
    : '从一个明确的标题开始，马上进入对话工作区继续规划这份演示稿。'
)
const submitLabel = computed<string>(() => (props.mode === 'rename' ? '保存名称' : '创建并进入工作区'))
const validationMessage = computed<string | null>(() => {
  if (!draftName.value.trim()) {
    return '请输入项目名称。'
  }

  return null
})

watch(
  () => [props.initialName, props.show] as const,
  ([initialName, show]) => {
    if (!show) {
      draftName.value = ''
      return
    }

    draftName.value = initialName.trim()
  },
  { immediate: true }
)

function handleShowChange(value: boolean): void {
  if (props.pending) {
    return
  }

  emit('update:show', value)
}

function handleClose(): void {
  handleShowChange(false)
}

function handleSubmit(): void {
  const normalizedName = draftName.value.trim()

  if (!normalizedName || props.pending) {
    return
  }

  emit('submit', normalizedName)
}
</script>

<template>
  <NModal :mask-closable="!pending" :show="show" @update:show="handleShowChange">
    <div class="mx-auto my-0 mt-[12vh] w-[min(92vw,560px)] rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] p-6 shadow-[var(--shadow-canvas)]">
      <div class="mb-5">
        <p class="mono-meta mb-3 text-[color:var(--app-text-tertiary)]">项目入口</p>
        <h2 class="m-0 text-2xl font-semibold">{{ dialogTitle }}</h2>
        <p class="mt-3 text-sm leading-7 text-[color:var(--app-text-secondary)]">
          {{ dialogDescription }}
        </p>
      </div>

      <div class="space-y-3">
        <div class="text-sm font-medium text-[color:var(--app-text-primary)]">项目名称</div>
        <NInput
          v-model:value="draftName"
          autofocus
          clearable
          maxlength="255"
          placeholder="例如：品牌焕新提案 / 年度经营复盘 / 产品发布叙事"
          size="large"
          @keydown.enter.prevent="handleSubmit"
        />
        <div
          class="min-h-[1.5rem] text-sm"
          :class="validationMessage ? 'text-[#b75b35]' : 'text-[color:var(--app-text-tertiary)]'"
        >
          {{ validationMessage ?? '名称会同步用于项目列表和后续工作区标题。' }}
        </div>
      </div>

      <div class="mt-6 flex flex-wrap justify-end gap-3">
        <NButton secondary strong :disabled="pending" @click="handleClose">取消</NButton>
        <NButton
          type="primary"
          :disabled="Boolean(validationMessage)"
          :loading="pending"
          @click="handleSubmit"
        >
          {{ submitLabel }}
        </NButton>
      </div>
    </div>
  </NModal>
</template>
