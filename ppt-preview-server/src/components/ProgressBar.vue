<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  value: number
  color?: string
  label?: string
  animated?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  color: 'var(--slide-primary)',
  label: '',
  animated: true
})

const clampedValue = computed(() => Math.min(100, Math.max(0, props.value)))
const progressStyle = computed(() => ({
  '--progress-color': props.color.trim() || 'var(--slide-primary)',
  '--progress-width': `${clampedValue.value}%`
}))
</script>

<template>
  <div class="progress-bar" :class="{ 'progress-bar--animated': animated }" :style="progressStyle">
    <div class="progress-meta">
      <span v-if="label" class="progress-label">{{ label }}</span>
      <span class="progress-value">{{ clampedValue }}%</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" />
    </div>
  </div>
</template>

<style scoped>
.progress-bar {
  display: grid;
  gap: 10px;
}

.progress-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--slide-text);
}

.progress-label {
  font-size: 16px;
  font-weight: 600;
}

.progress-value {
  font-size: 14px;
  color: var(--slide-text-secondary);
  font-variant-numeric: tabular-nums;
}

.progress-track {
  position: relative;
  overflow: hidden;
  height: 16px;
  border-radius: 999px;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--slide-border) 20%, transparent) 0%,
      color-mix(in srgb, var(--slide-border) 44%, transparent) 100%
    );
  box-shadow: inset 0 1px 2px color-mix(in srgb, var(--slide-text) 8%, transparent);
}

.progress-fill {
  position: relative;
  height: 100%;
  width: var(--progress-width);
  border-radius: inherit;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--progress-color) 76%, white 24%) 0%, var(--progress-color) 100%);
  box-shadow:
    inset 0 -1px 0 color-mix(in srgb, white 28%, transparent),
    0 8px 18px color-mix(in srgb, var(--progress-color) 24%, transparent 76%);
}

.progress-fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, color-mix(in srgb, white 30%, transparent) 46%, transparent 100%);
  opacity: 0.66;
}

.progress-bar--animated .progress-fill {
  transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1);
}
</style>
