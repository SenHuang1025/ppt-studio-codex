<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NInput } from 'naive-ui'

const props = withDefaults(
  defineProps<{
    accept?: string
    disabled?: boolean
    modelValue: string
    submitting?: boolean
    uploading?: boolean
  }>(),
  {
    accept: '',
    disabled: false,
    submitting: false,
    uploading: false
  }
)

const emit = defineEmits<{
  'select-files': [files: File[]]
  submit: [value: string]
  'update:modelValue': [value: string]
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const canSubmit = computed<boolean>(() => {
  if (props.disabled || props.submitting || props.uploading) {
    return false
  }

  return props.modelValue.trim().length > 0
})

function openFilePicker(): void {
  if (props.disabled || props.uploading || props.submitting) {
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

function handleSubmit(): void {
  const message = props.modelValue.trim()
  if (!message || !canSubmit.value) {
    return
  }

  emit('submit', message)
}
</script>

<template>
  <div class="space-y-3">
    <input
      ref="fileInputRef"
      :accept="accept"
      class="hidden"
      multiple
      type="file"
      @change="handleInputChange"
    />

    <NInput
      :autosize="{ minRows: 3, maxRows: 6 }"
      :disabled="disabled || submitting"
      :value="modelValue"
      placeholder="文件上传与 SSE 验证已接通，现在可以发送一条消息检查实时事件。"
      type="textarea"
      @update:value="(value) => emit('update:modelValue', value)"
    />

    <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div class="text-xs leading-6 text-[color:var(--app-text-tertiary)]">
        支持 xlsx / csv / docx / pdf / pptx / png / jpg / jpeg / md / json / txt，单文件 50MB。
      </div>

      <div class="flex flex-wrap justify-end gap-2">
        <NButton secondary strong :disabled="disabled || submitting" :loading="uploading" @click="openFilePicker">
          📎 上传文件
        </NButton>
        <NButton tertiary strong :disabled="!canSubmit" :loading="submitting" @click="handleSubmit">发送消息</NButton>
      </div>
    </div>
  </div>
</template>
