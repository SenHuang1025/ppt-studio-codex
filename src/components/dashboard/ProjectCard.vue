<script setup lang="ts">
import { computed } from 'vue'
import type { DropdownOption } from 'naive-ui'
import { NDropdown } from 'naive-ui'
import GlassPanel from '@/components/common/GlassPanel.vue'
import type { Project } from '@/types/project'
import { PROJECT_STATUS_META, formatProjectPageCount, formatProjectUpdatedAt, getProjectInitial } from '@/utils/project'

type ProjectCardAction = 'delete' | 'rename'

const props = defineProps<{
  deleting: boolean
  project: Project
  renaming: boolean
}>()

const emit = defineEmits<{
  delete: [project: Project]
  open: [projectId: string]
  rename: [project: Project]
}>()

const menuOptions = computed<DropdownOption[]>(() => [
  {
    disabled: props.deleting,
    key: 'rename',
    label: '重命名'
  },
  {
    disabled: props.deleting || props.renaming,
    key: 'delete',
    label: '删除项目'
  }
])

const statusMeta = computed(() => PROJECT_STATUS_META[props.project.status])
const statusBadgeClass = computed<string>(() => {
  switch (statusMeta.value.tone) {
    case 'accent':
      return 'border-[rgba(241,143,1,0.24)] bg-[rgba(241,143,1,0.14)] text-[color:var(--accent-200)]'
    case 'muted':
      return 'border-[rgba(95,95,95,0.12)] bg-[rgba(95,95,95,0.08)] text-[color:var(--app-text-secondary)]'
    case 'primary':
      return 'border-[rgba(104,166,125,0.18)] bg-[rgba(104,166,125,0.16)] text-[color:var(--primary-300)]'
    case 'sage':
      return 'border-[rgba(143,191,159,0.28)] bg-[rgba(143,191,159,0.16)] text-[color:var(--primary-300)]'
    case 'success':
      return 'border-[rgba(104,166,125,0.2)] bg-[rgba(104,166,125,0.12)] text-[color:var(--primary-300)]'
    case 'warning':
      return 'border-[rgba(241,143,1,0.24)] bg-[rgba(241,143,1,0.12)] text-[color:var(--accent-200)]'
  }
})

const footerLabel = computed<string>(() => {
  if (props.deleting) {
    return '删除中...'
  }

  if (props.renaming) {
    return '保存中...'
  }

  return '点击继续创作'
})

function handleOpen(): void {
  if (props.deleting) {
    return
  }

  emit('open', props.project.id)
}

function handleMenuSelect(key: string | number): void {
  if (key !== 'rename' && key !== 'delete') {
    return
  }

  const action = key as ProjectCardAction

  if (action === 'rename') {
    emit('rename', props.project)
    return
  }

  emit('delete', props.project)
}
</script>

<template>
  <GlassPanel
    tag="article"
    variant="soft"
    class="interactive-lift group flex h-full min-h-[258px] cursor-pointer flex-col overflow-hidden p-5"
    :class="deleting ? 'pointer-events-none opacity-65' : ''"
    role="button"
    tabindex="0"
    @click="handleOpen"
    @keydown.enter.prevent="handleOpen"
    @keydown.space.prevent="handleOpen"
  >
    <div class="mb-4 flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="mono-meta mb-2 text-[10px] text-[color:var(--app-text-tertiary)]">项目卡片</p>
        <h3 class="truncate text-lg font-semibold text-[color:var(--app-text-primary)]">
          {{ project.name }}
        </h3>
      </div>

      <NDropdown
        :options="menuOptions"
        placement="bottom-end"
        trigger="click"
        @select="handleMenuSelect"
      >
        <button
          class="flex h-10 w-10 items-center justify-center rounded-full border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] text-lg text-[color:var(--app-text-secondary)] transition duration-250 hover:border-[color:var(--app-border-strong)] hover:text-[color:var(--primary-300)]"
          type="button"
          @click.stop
        >
          ···
        </button>
      </NDropdown>
    </div>

    <div class="mb-5 rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[linear-gradient(180deg,rgba(255,253,248,0.95)_0%,rgba(248,240,225,0.92)_100%)] p-5">
      <div class="flex items-center justify-between gap-3">
        <span
          class="inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium"
          :class="statusBadgeClass"
        >
          {{ statusMeta.label }}
        </span>
        <span class="mono-meta truncate text-[10px] text-[color:var(--app-text-tertiary)]">
          {{ project.id.slice(0, 8) }}
        </span>
      </div>

      <div class="mt-8 flex items-end justify-between gap-3">
        <div class="text-[3rem] leading-none text-[color:var(--primary-300)]">
          {{ getProjectInitial(project.name) }}
        </div>
        <div class="rounded-full bg-[rgba(255,255,255,0.72)] px-3 py-1 text-xs text-[color:var(--app-text-secondary)]">
          {{ formatProjectPageCount(project.total_pages) }}
        </div>
      </div>
    </div>

    <div class="mt-auto flex items-end justify-between gap-3">
      <div>
        <div class="mono-meta mb-2 text-[10px] text-[color:var(--app-text-tertiary)]">最近更新</div>
        <div class="text-sm text-[color:var(--app-text-secondary)]">
          {{ formatProjectUpdatedAt(project.updated_at) }}
        </div>
      </div>

      <div class="text-right text-xs text-[color:var(--app-text-tertiary)]">
        {{ footerLabel }}
      </div>
    </div>
  </GlassPanel>
</template>
