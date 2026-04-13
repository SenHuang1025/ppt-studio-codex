<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GlassPanel from '@/components/common/GlassPanel.vue'
import { useShellStore } from '@/stores/shell'

interface DockItem {
  key: 'dashboard' | 'project' | 'settings'
  label: string
  short: string
  to: string
}

const route = useRoute()
const router = useRouter()
const shellStore = useShellStore()

const projectId = computed<string | null>(() => (typeof route.params.id === 'string' ? route.params.id : null))

const items = computed<DockItem[]>(() => {
  const dockItems: DockItem[] = [
    { key: 'dashboard', label: '首页', short: '首', to: '/' },
    { key: 'settings', label: '设置', short: '设', to: '/settings' }
  ]

  if (projectId.value) {
    dockItems.splice(1, 0, {
      key: 'project',
      label: '项目',
      short: '稿',
      to: route.name === 'project-preview' ? `/project/${projectId.value}/preview` : `/project/${projectId.value}/chat`
    })
  }

  return dockItems
})

const activeKey = computed<DockItem['key']>(() => {
  if (route.name === 'settings') {
    return 'settings'
  }

  if (String(route.name).startsWith('project')) {
    return 'project'
  }

  return 'dashboard'
})

function navigate(target: string): void {
  void router.push(target)
}

function toggleDock(): void {
  shellStore.toggleDockCollapsed()
}
</script>

<template>
  <GlassPanel
    variant="strong"
    class="fixed inset-y-4 left-4 z-20 flex flex-col p-3 transition-[width] duration-300"
    :class="shellStore.dockCollapsed ? 'w-[76px]' : 'w-[112px]'"
  >
    <button
      class="mb-4 flex h-14 w-full items-center justify-center rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] text-sm font-semibold tracking-[0.28em] text-[color:var(--primary-300)] shadow-[var(--shadow-glass-1)] transition duration-250 hover:border-[color:var(--app-border-strong)]"
      type="button"
      @click="navigate('/')"
    >
      PS
    </button>

    <nav class="flex flex-1 flex-col gap-3">
      <button
        v-for="item in items"
        :key="item.key"
        class="group flex w-full items-center gap-2 rounded-[var(--radius-lg)] border px-3 py-3 text-left transition duration-250 hover:-translate-y-0.5"
        :class="
          activeKey === item.key
            ? 'border-[color:var(--app-primary-ring)] bg-[color:var(--app-primary-soft)] text-[color:var(--primary-300)] shadow-[var(--shadow-highlight)]'
            : 'border-[color:var(--app-border-subtle)] bg-transparent text-[color:var(--app-text-secondary)] hover:border-[color:var(--app-border-strong)] hover:bg-[color:var(--surface-card)] hover:text-[color:var(--primary-300)]'
        "
        :title="item.label"
        type="button"
        @click="navigate(item.to)"
      >
        <span class="mono-meta text-[11px]">{{ item.short }}</span>
        <span v-if="!shellStore.dockCollapsed" class="text-xs font-medium">
          {{ item.label }}
        </span>
      </button>
    </nav>

    <button
      class="mt-4 flex h-11 w-full items-center justify-center rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] text-xs font-medium text-[color:var(--app-text-secondary)] transition duration-250 hover:border-[color:var(--app-border-strong)] hover:text-[color:var(--primary-300)]"
      type="button"
      @click="toggleDock"
    >
      {{ shellStore.dockCollapsed ? '>>' : '<<' }}
    </button>
  </GlassPanel>
</template>
