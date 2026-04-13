<script setup lang="ts">
import { computed } from 'vue'

type WorkspaceMode = 'chat' | 'preview'

interface ModeItem {
  key: WorkspaceMode
  label: string
}

const props = defineProps<{
  activeMode: WorkspaceMode
}>()

const emit = defineEmits<{
  select: [mode: WorkspaceMode]
}>()

const items = computed<ModeItem[]>(() => [
  { key: 'chat', label: '规划大纲' },
  { key: 'preview', label: '预览调整' }
])

function selectMode(mode: WorkspaceMode): void {
  if (mode === props.activeMode) {
    return
  }

  emit('select', mode)
}
</script>

<template>
  <div class="glass-panel-strong relative mx-auto grid w-full max-w-[24rem] grid-cols-2 gap-2 p-1">
    <div
      class="pointer-events-none absolute inset-y-1 left-1 w-[calc(50%-0.5rem)] rounded-full bg-[var(--gradient-brand)] shadow-[var(--shadow-highlight)] transition-transform duration-300 ease-out"
      :class="activeMode === 'preview' ? 'translate-x-[calc(100%+0.5rem)]' : 'translate-x-0'"
    />

    <button
      v-for="item in items"
      :key="item.key"
      class="relative z-10 rounded-full px-4 py-3 text-sm font-medium transition duration-250"
      :class="
        activeMode === item.key
          ? 'text-[color:var(--surface-canvas)]'
          : 'text-[color:var(--app-text-secondary)] hover:text-[color:var(--primary-300)]'
      "
      type="button"
      @click="selectMode(item.key)"
    >
      {{ item.label }}
    </button>
  </div>
</template>
