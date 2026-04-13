<script setup lang="ts">
import { computed } from 'vue'
import AmbientBackground from '@/components/common/AmbientBackground.vue'
import AppDock from '@/components/common/AppDock.vue'
import { useShellStore } from '@/stores/shell'

const shellStore = useShellStore()

const contentPadding = computed<string>(() => (shellStore.dockCollapsed ? '112px' : '148px'))
</script>

<template>
  <div class="app-shell relative min-h-screen overflow-hidden">
    <AmbientBackground />
    <AppDock />
    <main
      class="relative z-10 min-h-screen overflow-auto px-5 py-5 transition-[padding] duration-300 md:px-6 md:py-6"
      :style="{ paddingLeft: contentPadding }"
    >
      <div class="mx-auto min-h-[calc(100vh-3rem)] max-w-[1640px]">
        <slot />
      </div>
    </main>
  </div>
</template>
