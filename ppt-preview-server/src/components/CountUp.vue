<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

interface Props {
  end: number
  duration?: number
  prefix?: string
  suffix?: string
  decimals?: number
}

const props = withDefaults(defineProps<Props>(), {
  duration: 1.2,
  prefix: '',
  suffix: '',
  decimals: 0
})

const animatedValue = ref(0)
let frameId: number | null = null

const numberFormatter = computed(() => {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: props.decimals,
    maximumFractionDigits: props.decimals
  })
})

const displayStyle = computed(() => ({
  '--count-up-digits': String(Math.max(String(Math.trunc(Math.abs(props.end))).length, 1))
}))

const displayValue = computed(() => {
  const formattedValue = Number(animatedValue.value.toFixed(props.decimals))
  return `${props.prefix}${numberFormatter.value.format(formattedValue)}${props.suffix}`
})

function stopAnimation(): void {
  if (frameId !== null) {
    cancelAnimationFrame(frameId)
    frameId = null
  }
}

function animateTo(targetValue: number): void {
  stopAnimation()

  const durationMs = Math.max(props.duration, 0) * 1_000
  const startValue = animatedValue.value

  if (durationMs === 0 || startValue === targetValue) {
    animatedValue.value = targetValue
    return
  }

  const delta = targetValue - startValue
  const startedAt = performance.now()

  const step = (timestamp: number) => {
    const progress = Math.min((timestamp - startedAt) / durationMs, 1)
    const easedProgress = 1 - Math.pow(1 - progress, 3)
    animatedValue.value = startValue + delta * easedProgress

    if (progress < 1) {
      frameId = requestAnimationFrame(step)
      return
    }

    animatedValue.value = targetValue
    frameId = null
  }

  frameId = requestAnimationFrame(step)
}

watch(
  () => [props.end, props.duration] as const,
  ([end]) => {
    animateTo(end)
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  stopAnimation()
})
</script>

<template>
  <span class="count-up" :style="displayStyle">{{ displayValue }}</span>
</template>

<style scoped>
.count-up {
  display: inline-flex;
  align-items: baseline;
  min-width: calc(var(--count-up-digits) * 0.56em);
  gap: 4px;
  font-family: var(--slide-font-title);
  font-size: inherit;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
  color: inherit;
}
</style>
