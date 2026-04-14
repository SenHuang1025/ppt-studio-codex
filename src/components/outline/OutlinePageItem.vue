<script setup lang="ts">
import { NTag } from 'naive-ui'
import type { OutlinePage } from '@/types/project'

defineProps<{
  active?: boolean
  expanded?: boolean
  page: OutlinePage
}>()

defineEmits<{
  toggle: [pageNumber: number]
}>()
</script>

<template>
  <article
    class="rounded-[var(--radius-xl)] border p-4 transition duration-250"
    :class="
      active
        ? 'border-[rgba(104,166,125,0.34)] bg-[color:var(--surface-canvas)] shadow-[var(--shadow-highlight)]'
        : 'border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor-2)]'
    "
  >
    <button
      class="flex w-full items-start justify-between gap-4 border-none bg-transparent p-0 text-left"
      type="button"
      @click="$emit('toggle', page.page_number)"
    >
      <div class="min-w-0">
        <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">
          第 {{ page.page_number }} 页
        </div>
        <div class="mt-2 text-base font-semibold text-[color:var(--app-text-primary)]">{{ page.title }}</div>
        <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">{{ page.content_brief }}</div>
      </div>

      <div class="flex shrink-0 flex-col items-end gap-2">
        <NTag round :bordered="false" class="border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.82)] text-[color:var(--app-text-secondary)]">
          {{ page.type }}
        </NTag>
        <span class="text-xs text-[color:var(--app-text-tertiary)]">{{ expanded ? '收起详情' : '展开详情' }}</span>
      </div>
    </button>

    <div v-if="expanded" class="mt-4 space-y-4 border-t border-[color:var(--app-border-subtle)] pt-4">
      <div>
        <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">Layout</div>
        <div class="mt-2 rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-canvas)] px-3 py-3 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          {{ page.layout }}
        </div>
      </div>

      <div>
        <div class="mono-meta text-[10px] uppercase tracking-[0.16em] text-[color:var(--app-text-tertiary)]">Data Refs</div>
        <div v-if="page.data_refs.length > 0" class="mt-2 flex flex-wrap gap-2">
          <span
            v-for="dataRef in page.data_refs"
            :key="dataRef"
            class="rounded-full border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.76)] px-3 py-1 text-xs text-[color:var(--app-text-secondary)]"
          >
            {{ dataRef }}
          </span>
        </div>
        <div
          v-else
          class="mt-2 rounded-[var(--radius-lg)] border border-dashed border-[color:var(--app-border-subtle)] bg-[color:var(--surface-canvas)] px-3 py-3 text-sm leading-6 text-[color:var(--app-text-secondary)]"
        >
          当前页还没有明确的数据引用，后续可以继续在左侧补充资料或说明希望引用哪部分内容。
        </div>
      </div>
    </div>
  </article>
</template>
