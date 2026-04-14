<script setup lang="ts">
withDefaults(
  defineProps<{
    agent?: string
    label: string
  }>(),
  {
    agent: 'assistant'
  }
)
</script>

<template>
  <div class="rounded-[var(--radius-xl)] border border-[rgba(104,166,125,0.18)] bg-[rgba(255,249,239,0.82)] px-4 py-3 shadow-[var(--shadow-glass-1)]">
    <div class="flex items-center gap-3">
      <div class="flex min-w-[72px] items-center gap-1.5">
        <span class="thinking-dot animation-delay-0" />
        <span class="thinking-dot animation-delay-1" />
        <span class="thinking-dot animation-delay-2" />
      </div>

      <div class="min-w-0 flex-1">
        <div class="mono-meta text-[10px] uppercase tracking-[0.18em] text-[color:var(--app-text-tertiary)]">
          {{ agent }}
        </div>
        <div class="mt-1 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          {{ label }}
        </div>
      </div>
    </div>

    <div class="mt-3 h-1 overflow-hidden rounded-full bg-[rgba(194,186,166,0.48)]">
      <div class="thinking-line h-full rounded-full" />
    </div>
  </div>
</template>

<style scoped>
.thinking-dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 999px;
  background: rgba(104, 166, 125, 0.78);
  animation: thinking-breathe 1.45s ease-in-out infinite;
}

.animation-delay-0 {
  animation-delay: 0s;
}

.animation-delay-1 {
  animation-delay: 0.16s;
}

.animation-delay-2 {
  animation-delay: 0.32s;
}

.thinking-line {
  width: 34%;
  background: var(--gradient-brand);
  animation: thinking-scan 1.8s ease-in-out infinite;
  transform-origin: left center;
}

@keyframes thinking-breathe {
  0%,
  100% {
    opacity: 0.42;
    transform: translateY(0) scale(0.92);
  }

  50% {
    opacity: 1;
    transform: translateY(-1px) scale(1);
  }
}

@keyframes thinking-scan {
  0% {
    transform: translateX(-28%) scaleX(0.72);
  }

  50% {
    transform: translateX(110%) scaleX(1);
  }

  100% {
    transform: translateX(240%) scaleX(0.72);
  }
}
</style>
