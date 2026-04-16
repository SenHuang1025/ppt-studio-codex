<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { NButton, NTag } from 'naive-ui'
import OutlinePageItem from '@/components/outline/OutlinePageItem.vue'
import type { Outline } from '@/types/project'

const props = withDefaults(
  defineProps<{
    activePageNumber?: number | null
    confirming?: boolean
    disabled?: boolean
    outline: Outline | null
    previewLinkEnabled?: boolean
    projectName: string
  }>(),
  {
    activePageNumber: null,
    confirming: false,
    disabled: false,
    previewLinkEnabled: false
  }
)

const emit = defineEmits<{
  adjust: []
  confirm: []
  'select-page': [pageNumber: number]
  preview: [pageNumber: number]
}>()

const expandedPageNumbers = ref<number[]>([])
const pageElementMap = new Map<number, HTMLDivElement>()

const hasOutline = computed<boolean>(() => Boolean(props.outline && props.outline.pages.length > 0))

watch(
  () => props.activePageNumber,
  (pageNumber) => {
    if (!pageNumber) {
      return
    }

    ensurePageVisible(pageNumber)
  }
)

watch(
  () => props.outline,
  () => {
    expandedPageNumbers.value = []
  }
)

function setPageRef(pageNumber: number, element: HTMLDivElement | null): void {
  if (!element) {
    pageElementMap.delete(pageNumber)
    return
  }

  pageElementMap.set(pageNumber, element)
}

function togglePage(pageNumber: number): void {
  expandedPageNumbers.value = expandedPageNumbers.value.includes(pageNumber)
    ? expandedPageNumbers.value.filter((value) => value !== pageNumber)
    : [...expandedPageNumbers.value, pageNumber]

  emit('select-page', pageNumber)
}

function ensurePageVisible(pageNumber: number): void {
  if (!expandedPageNumbers.value.includes(pageNumber)) {
    expandedPageNumbers.value = [...expandedPageNumbers.value, pageNumber]
  }

  void nextTick(() => {
    pageElementMap.get(pageNumber)?.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    })
  })
}
</script>

<template>
  <section class="workspace-solid flex min-h-0 flex-col rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] p-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">高对比度工作区</p>
        <h2 class="m-0 text-xl font-semibold">大纲编辑器</h2>
        <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          {{ projectName }}
        </div>
      </div>

      <NTag round :bordered="false" class="border border-[rgba(104,166,125,0.16)] bg-[rgba(255,249,239,0.9)] text-[color:var(--app-text-secondary)]">
        {{ hasOutline && outline ? `${outline.total_pages} 页` : '等待大纲' }}
      </NTag>
    </div>

    <div v-if="hasOutline && outline" class="mt-5 flex items-center justify-between gap-4 rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-canvas)] px-4 py-4">
      <div class="min-w-0">
        <div class="text-base font-semibold text-[color:var(--app-text-primary)]">{{ outline.title }}</div>
        <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          {{ outline.theme_suggestion }}
        </div>
      </div>
      <div class="mono-meta shrink-0 text-[10px] uppercase tracking-[0.18em] text-[color:var(--app-text-tertiary)]">
        Theme Suggestion
      </div>
    </div>

    <div v-if="hasOutline && outline" class="mt-5 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
      <div
        v-for="page in outline.pages"
        :key="page.page_number"
        :ref="(element) => setPageRef(page.page_number, element as HTMLDivElement | null)"
      >
        <OutlinePageItem
          :active="activePageNumber === page.page_number"
          :expanded="expandedPageNumbers.includes(page.page_number)"
          :page="page"
          :preview-link-enabled="previewLinkEnabled"
          @preview="emit('preview', $event)"
          @toggle="togglePage"
        />
      </div>
    </div>

    <div
      v-else
      class="mt-5 grid min-h-[320px] flex-1 place-items-center rounded-[var(--radius-2xl)] border border-dashed border-[color:var(--app-border-subtle)] bg-[color:var(--surface-canvas)] px-6 py-8 text-center"
    >
      <div class="max-w-[30rem]">
        <div class="mono-meta text-[10px] uppercase tracking-[0.18em] text-[color:var(--app-text-tertiary)]">Outline Pending</div>
        <div class="mt-3 text-2xl font-semibold text-[color:var(--app-text-primary)]">右侧会在这里沉淀你的演示结构。</div>
        <div class="mt-4 text-sm leading-7 text-[color:var(--app-text-secondary)]">
          先上传资料，再在左侧说明希望面向谁、解决什么问题、想保留多少页或强调哪些重点。Agent 生成大纲后，这里会变成可展开、可确认的工作面。
        </div>
      </div>
    </div>

    <div class="mt-5 border-t border-[color:var(--app-border-subtle)] pt-5">
      <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div class="text-sm leading-6 text-[color:var(--app-text-secondary)]">
          {{ hasOutline ? '确认后将切到预览模式；正式页面生成保留到后续阶段接入。' : '上传资料并在左侧描述需求后，这里会出现可确认的大纲。' }}
        </div>

        <div class="flex flex-wrap justify-end gap-3">
          <NButton secondary strong :disabled="disabled" @click="emit('adjust')">我想调整</NButton>
          <NButton
            type="warning"
            strong
            :disabled="disabled || !hasOutline"
            :loading="confirming"
            @click="emit('confirm')"
          >
            确认大纲，开始生成
          </NButton>
        </div>
      </div>
    </div>
  </section>
</template>
