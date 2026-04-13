import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useShellStore = defineStore('shell', () => {
  const dockCollapsed = ref(false)

  function toggleDockCollapsed(): void {
    dockCollapsed.value = !dockCollapsed.value
  }

  return {
    dockCollapsed,
    toggleDockCollapsed
  }
})

