<script setup lang="ts">
import { defineAsyncComponent } from 'vue'

const slideComponent = defineAsyncComponent(() => import('./slides/version-preview.vue'))
</script>

<template>
  <component :is="slideComponent" />
</template>
