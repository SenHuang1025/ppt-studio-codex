<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NInput } from 'naive-ui'

const props = withDefaults(
  defineProps<{
    accept?: string
    disabled?: boolean
    helperText?: string
    modelValue: string
    placeholder?: string
    showFileUpload?: boolean
    submitLabel?: string
    submitting?: boolean
    uploading?: boolean
  }>(),
  {
    accept: '',
    disabled: false,
    helperText: '支持 xlsx / csv / docx / pdf / pptx / png / jpg / jpeg / md / json / txt，单文件 50MB。',
    placeholder: '描述你的演示目标、受众和想突出的重点；也可以结合已上传资料继续调整大纲。',
    showFileUpload: true,
    submitLabel: '发送消息',
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
const inputRef = ref<InstanceType<typeof NInput> | null>(null)
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

function handleKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' || event.shiftKey) {
    return
  }

  event.preventDefault()
  handleSubmit()
}

function focusInput(): void {
  inputRef.value?.focus()
}

defineExpose({
  focusInput
})
</script>

<template>
  <div class="space-y-3">
    <input
      v-if="showFileUpload"
      ref="fileInputRef"
      :accept="accept"
      class="hidden"
      multiple
      type="file"
      @change="handleInputChange"
    />

    <NInput
      ref="inputRef"
      :autosize="{ minRows: 3, maxRows: 6 }"
      :disabled="disabled || submitting"
      :value="modelValue"
      :placeholder="placeholder"
      type="textarea"
      @keydown="handleKeydown"
      @update:value="(value) => emit('update:modelValue', value)"
    />

    <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div class="text-xs leading-6 text-[color:var(--app-text-tertiary)]">
        {{ helperText }}
      </div>

      <div class="flex flex-wrap justify-end gap-2">
        <NButton
          v-if="showFileUpload"
          secondary
          strong
          :disabled="disabled || submitting || uploading"
          :loading="uploading"
          @click="openFilePicker"
        >
          📎 上传文件
        </NButton>
        <NButton tertiary strong :disabled="!canSubmit" :loading="submitting" @click="handleSubmit">
          {{ submitLabel }}
        </NButton>
      </div>
    </div>
  </div>
</template>
