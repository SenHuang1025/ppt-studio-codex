<script setup lang="ts">
import { onErrorCaptured, ref, watch } from 'vue'
import { NButton } from 'naive-ui'
import { reportGlobalError, resolveAppErrorMessage } from '@/services/errorHandling'

const props = withDefaults(defineProps<{
  description?: string
  resetKey?: string | number | null
  title?: string
}>(), {
  description: '当前区域发生异常，已阻止页面整体崩溃。你可以重试或刷新当前视图。',
  resetKey: null,
  title: '局部渲染失败'
})

const errorMessage = ref<string | null>(null)

watch(
  () => props.resetKey,
  () => {
    errorMessage.value = null
  }
)

onErrorCaptured((error, _instance, info) => {
  errorMessage.value = resolveAppErrorMessage(error, props.description)
  reportGlobalError(error, {
    context: `ErrorBoundary:${info}`,
    notify: false
  })
  return false
})

function resetBoundary(): void {
  errorMessage.value = null
}
</script>

<template>
  <div v-if="errorMessage" class="rounded-[var(--radius-2xl)] border border-[rgba(183,91,53,0.16)] bg-[rgba(255,248,237,0.82)] p-5">
    <div class="mono-meta mb-2 text-[10px] text-[color:#9f4b2a]">Error Boundary</div>
    <div class="text-base font-semibold text-[color:var(--app-text-primary)]">{{ title }}</div>
    <div class="mt-2 text-sm leading-7 text-[color:var(--app-text-secondary)]">
      {{ errorMessage }}
    </div>
    <NButton class="mt-4" secondary strong @click="resetBoundary">
      重试渲染
    </NButton>
  </div>
  <slot v-else />
</template>
