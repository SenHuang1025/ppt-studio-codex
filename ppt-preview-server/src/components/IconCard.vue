<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  icon?: string
  value: string | number
  label: string
  trend?: string
}

const props = withDefaults(defineProps<Props>(), {
  icon: '',
  trend: ''
})

const trendTone = computed<'positive' | 'negative' | 'neutral'>(() => {
  const normalizedTrend = props.trend.trim().toLowerCase()

  if (!normalizedTrend) {
    return 'neutral'
  }

  if (normalizedTrend.startsWith('-') || normalizedTrend.includes('down') || normalizedTrend.includes('↓')) {
    return 'negative'
  }

  if (normalizedTrend.startsWith('+') || normalizedTrend.includes('up') || normalizedTrend.includes('↑')) {
    return 'positive'
  }

  return 'neutral'
})

const normalizedValue = computed(() => String(props.value))
</script>

<template>
  <article class="icon-card">
    <div class="icon-card__header">
      <div class="icon-card__badge" :class="{ 'icon-card__badge--empty': !icon }">
        {{ icon || '•' }}
      </div>
      <span
        v-if="trend"
        class="icon-card__trend"
        :class="`icon-card__trend--${trendTone}`"
      >
        {{ trend }}
      </span>
    </div>
    <div class="icon-card__value">{{ normalizedValue }}</div>
    <div class="icon-card__label">{{ props.label }}</div>
  </article>
</template>

<style scoped>
.icon-card {
  display: grid;
  gap: 20px;
  min-height: 214px;
  padding: 28px 30px;
  border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
  border-radius: var(--slide-radius-lg);
  background: linear-gradient(180deg, var(--slide-surface-strong) 0%, var(--slide-surface-soft) 100%);
  box-shadow: var(--slide-shadow-card);
}

.icon-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.icon-card__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 58px;
  min-height: 58px;
  padding: 10px 14px;
  border-radius: 18px;
  background: linear-gradient(
    180deg,
    var(--slide-primary-soft) 0%,
    color-mix(in srgb, var(--slide-primary) 10%, transparent) 100%
  );
  color: var(--slide-primary);
  font-size: 28px;
  font-weight: 700;
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 28%, transparent);
}

.icon-card__badge--empty {
  background: var(--slide-neutral-soft);
  color: var(--slide-text-secondary);
}

.icon-card__trend {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  color: var(--slide-text-secondary);
  font-size: 15px;
  font-weight: 700;
}

.icon-card__trend--positive {
  background: var(--slide-primary-soft);
  color: var(--slide-primary);
}

.icon-card__trend--negative {
  background: var(--slide-danger-soft);
  color: var(--slide-danger);
}

.icon-card__trend--neutral {
  background: var(--slide-neutral-soft);
}

.icon-card__value {
  font-family: var(--slide-font-title);
  font-size: 52px;
  line-height: 1;
  letter-spacing: -0.04em;
}

.icon-card__label {
  color: var(--slide-text-secondary);
  font-size: 18px;
  line-height: 1.6;
}
</style>
