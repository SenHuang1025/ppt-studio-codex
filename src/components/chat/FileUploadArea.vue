<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton } from 'naive-ui'

const props = withDefaults(
  defineProps<{
    accept?: string
    disabled?: boolean
    uploading?: boolean
  }>(),
  {
    accept: '',
    disabled: false,
    uploading: false
  }
)

const emit = defineEmits<{
  'select-files': [files: File[]]
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const dragDepth = ref(0)
const isDragActive = computed<boolean>(() => dragDepth.value > 0)

function openFilePicker(): void {
  if (props.disabled || props.uploading) {
    return
  }

  fileInputRef.value?.click()
}

function handleInputChange(event: Event): void {
  const input = event.target as HTMLInputElement | null
  const files = input?.files ? Array.from(input.files) : []

  if (files.length > 0) {
    emit('select-files', files)
  }

  if (input) {
    input.value = ''
  }
}

function handleDragEnter(): void {
  if (props.disabled || props.uploading) {
    return
  }

  dragDepth.value += 1
}

function handleDragOver(event: DragEvent): void {
  if (props.disabled || props.uploading) {
    return
  }

  event.dataTransfer!.dropEffect = 'copy'
}

function handleDragLeave(): void {
  if (props.disabled || props.uploading) {
    return
  }

  dragDepth.value = Math.max(0, dragDepth.value - 1)
}

function handleDrop(event: DragEvent): void {
  dragDepth.value = 0

  if (props.disabled || props.uploading) {
    return
  }

  const files = event.dataTransfer?.files ? Array.from(event.dataTransfer.files) : []
  if (files.length > 0) {
    emit('select-files', files)
  }
}
</script>

<template>
  <div
    class="rounded-[var(--radius-xl)] border border-dashed p-5 transition duration-250"
    :class="
      isDragActive
        ? 'border-[color:var(--app-border-strong)] bg-[color:var(--app-primary-soft)] shadow-[var(--shadow-highlight)]'
        : 'border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.54)]'
    "
    @click="openFilePicker"
    @dragenter.prevent="handleDragEnter"
    @dragleave.prevent="handleDragLeave"
    @dragover.prevent="handleDragOver"
    @drop.prevent="handleDrop"
  >
    <input
      ref="fileInputRef"
      :accept="accept"
      class="hidden"
      multiple
      type="file"
      @change="handleInputChange"
    />

    <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div class="space-y-2">
        <div class="mono-meta text-[color:var(--app-text-tertiary)]">拖拽上传区</div>
        <div class="text-base font-semibold">把资料拖到这里，或点击选择文件</div>
        <div class="text-sm leading-6 text-[color:var(--app-text-secondary)]">
          上传后文件会写入当前项目的 `uploads/` 目录，并在数据库中登记为 `pending`。
        </div>
      </div>

      <div class="flex shrink-0 flex-col items-start gap-2 md:items-end">
        <NButton secondary strong :disabled="disabled" :loading="uploading" @click.stop="openFilePicker">
          选择文件
        </NButton>
        <div class="text-xs text-[color:var(--app-text-tertiary)]">单文件 50MB，支持 11 种格式</div>
      </div>
    </div>
  </div>
</template>
