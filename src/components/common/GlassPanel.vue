<script setup lang="ts">
import { computed } from 'vue'

type GlassVariant = 'soft' | 'default' | 'strong'

const props = withDefaults(
  defineProps<{
    tag?: string
    variant?: GlassVariant
  }>(),
  {
    tag: 'div',
    variant: 'default'
  }
)

const panelClass = computed<string>(() => {
  switch (props.variant) {
    case 'soft':
      return 'glass-panel-soft'
    case 'strong':
      return 'glass-panel-strong'
    default:
      return 'glass-panel'
  }
})
</script>

<template>
  <component :is="tag" :class="panelClass">
    <slot />
  </component>
</template>

