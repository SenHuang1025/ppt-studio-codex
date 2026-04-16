<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NDrawer, NDrawerContent, NSkeleton, NTag } from 'naive-ui'
import type { PageVersion } from '@/types/project'
import type { PreviewVersionSelection } from '@/types/preview'
import { formatPreviewUpdatedAt } from '@/utils/preview'

const props = withDefaults(defineProps<{
  loading?: boolean
  pageNumber: number
  rollingBack?: boolean
  rollingBackVersion?: number | null
  selectedVersion: PreviewVersionSelection | null
  show: boolean
  versions: PageVersion[]
}>(), {
  loading: false,
  rollingBack: false,
  rollingBackVersion: null
})

const emit = defineEmits<{
  close: []
  previewVersion: [version: PageVersion]
  rollbackVersion: [version: PageVersion]
  'update:show': [value: boolean]
}>()

const title = computed<string>(() => `第 ${props.pageNumber} 页历史版本`)

function handleClose(): void {
  emit('update:show', false)
  emit('close')
}

function isSelected(version: PageVersion): boolean {
  return props.selectedVersion?.sourceVersion === version.version
}
</script>

<template>
  <NDrawer
    :show="show"
    :width="420"
    placement="right"
    resizable
    @mask-click="handleClose"
    @update:show="emit('update:show', $event)"
  >
    <NDrawerContent closable :title="title">
      <div class="flex h-full flex-col gap-4">
        <div class="rounded-[var(--radius-xl)] border border-[rgba(131,53,0,0.12)] bg-[rgba(255,249,239,0.9)] px-4 py-3 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          点击某个版本会在中间预览区临时查看该版本；只有点击“回滚到此版本”才会真正写回数据库和预览文件。
        </div>

        <div v-if="loading" class="space-y-3">
          <div
            v-for="index in 4"
            :key="index"
            class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-white p-4"
          >
            <NSkeleton :sharp="false" height="12px" width="24%" />
            <NSkeleton class="mt-3" :sharp="false" height="14px" width="72%" />
            <NSkeleton class="mt-2" :sharp="false" height="14px" width="48%" />
          </div>
        </div>

        <div
          v-else-if="versions.length === 0"
          class="rounded-[var(--radius-xl)] border border-dashed border-[color:var(--app-border-subtle)] bg-[rgba(255,252,246,0.86)] px-4 py-5 text-sm leading-7 text-[color:var(--app-text-secondary)]"
        >
          当前页还没有历史版本。
        </div>

        <div v-else class="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
          <article
            v-for="version in versions"
            :key="version.id"
            class="rounded-[var(--radius-xl)] border p-4 transition duration-200"
            :class="isSelected(version)
              ? 'border-[rgba(104,166,125,0.22)] bg-[rgba(244,251,246,0.96)] shadow-[var(--shadow-soft)]'
              : 'border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)]'"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="flex items-center gap-2">
                  <div class="text-sm font-semibold text-[color:var(--app-text-primary)]">v{{ version.version }}</div>
                  <NTag v-if="isSelected(version)" round :bordered="false" type="success">
                    预览中
                  </NTag>
                </div>
                <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
                  {{ version.change_description || '未记录修改描述' }}
                </div>
                <div class="mt-2 text-xs text-[color:var(--app-text-tertiary)]">
                  {{ formatPreviewUpdatedAt(version.created_at) }}
                </div>
              </div>
            </div>

            <div class="mt-4 grid grid-cols-2 gap-3">
              <NButton secondary strong @click="emit('previewVersion', version)">
                {{ isSelected(version) ? '重新预览' : '预览此版本' }}
              </NButton>
              <NButton
                type="warning"
                strong
                :loading="rollingBack && rollingBackVersion === version.version"
                @click="emit('rollbackVersion', version)"
              >
                回滚到此版本
              </NButton>
            </div>
          </article>
        </div>
      </div>
    </NDrawerContent>
  </NDrawer>
</template>
