<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  animated?: boolean
  tone?: 'accent' | 'error' | 'muted' | 'primary'
  value: number
}>(), {
  animated: false,
  tone: 'primary'
})

const clampedValue = computed<number>(() => Math.min(1, Math.max(0, props.value)))

const trackClass = computed<string>(() => {
  switch (props.tone) {
    case 'accent':
      return 'bg-[rgba(241,143,1,0.14)]'
    case 'error':
      return 'bg-[rgba(183,91,53,0.12)]'
    case 'muted':
      return 'bg-[rgba(95,95,95,0.12)]'
    case 'primary':
    default:
      return 'bg-[rgba(104,166,125,0.12)]'
  }
})

const barClass = computed<string>(() => {
  switch (props.tone) {
    case 'accent':
      return 'bg-[linear-gradient(90deg,rgba(241,143,1,0.72)_0%,rgba(249,183,82,0.98)_100%)]'
    case 'error':
      return 'bg-[linear-gradient(90deg,rgba(183,91,53,0.72)_0%,rgba(207,118,83,0.98)_100%)]'
    case 'muted':
      return 'bg-[linear-gradient(90deg,rgba(95,95,95,0.34)_0%,rgba(128,128,128,0.62)_100%)]'
    case 'primary':
    default:
      return 'bg-[linear-gradient(90deg,rgba(104,166,125,0.72)_0%,rgba(158,205,172,0.98)_100%)]'
  }
})

const glowClass = computed<string>(() => {
  switch (props.tone) {
    case 'accent':
      return 'bg-[linear-gradient(90deg,rgba(255,255,255,0)_0%,rgba(255,240,216,0.18)_45%,rgba(255,240,216,0.72)_100%)]'
    case 'error':
      return 'bg-[linear-gradient(90deg,rgba(255,255,255,0)_0%,rgba(255,232,225,0.18)_45%,rgba(255,232,225,0.68)_100%)]'
    case 'muted':
      return 'bg-[linear-gradient(90deg,rgba(255,255,255,0)_0%,rgba(255,255,255,0.16)_45%,rgba(255,255,255,0.52)_100%)]'
    case 'primary':
    default:
      return 'bg-[linear-gradient(90deg,rgba(255,255,255,0)_0%,rgba(245,255,248,0.18)_45%,rgba(245,255,248,0.72)_100%)]'
  }
})

const barStyle = computed<Record<string, string>>(() => ({
  width: `${Math.round(clampedValue.value * 1000) / 10}%`
}))
</script>

<template>
  <div class="relative h-[3px] w-full overflow-hidden rounded-full" :class="trackClass">
    <div
      class="absolute inset-y-0 left-0 rounded-full transition-[width] duration-300 ease-out"
      :class="barClass"
      :style="barStyle"
    />
    <div
      v-if="animated"
      class="linear-progress-glow pointer-events-none absolute inset-y-0 left-0 w-24 opacity-70"
      :class="glowClass"
    />
  </div>
</template>

<style scoped>
.linear-progress-glow {
  animation: linear-progress-glow-sweep 1.8s ease-in-out infinite;
  transform: translateX(-140%);
}

@keyframes linear-progress-glow-sweep {
  0% {
    opacity: 0;
    transform: translateX(-140%);
  }

  18% {
    opacity: 0.72;
  }

  100% {
    opacity: 0;
    transform: translateX(760%);
  }
}
</style>
