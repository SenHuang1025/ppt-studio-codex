<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NSkeleton } from 'naive-ui'
import GlassPanel from '@/components/common/GlassPanel.vue'
import ProjectCard from '@/components/dashboard/ProjectCard.vue'
import type { ProjectFilterValue } from '@/stores/projectStore'
import type { Project } from '@/types/project'

const props = defineProps<{
  activeFilter: ProjectFilterValue
  deletingById: Record<string, boolean>
  error: string | null
  loaded: boolean
  loading: boolean
  projects: Project[]
  renamingById: Record<string, boolean>
}>()

const emit = defineEmits<{
  'clear-filter': []
  create: []
  delete: [project: Project]
  open: [projectId: string]
  rename: [project: Project]
  retry: []
}>()

const showSkeleton = computed<boolean>(() => !props.error && (!props.loaded || (props.loading && props.projects.length === 0)))
const isFilteredEmptyState = computed<boolean>(() => props.activeFilter !== 'all')
const emptyTitle = computed<string>(() =>
  isFilteredEmptyState.value ? '这个状态下还没有项目' : '从第一份演示稿开始建立你的工作台'
)
const emptyDescription = computed<string>(() =>
  isFilteredEmptyState.value
    ? '可以切回全部项目，或者立即新建一个新的项目继续进入对话工作区。'
    : '输入一个明确主题，创建项目后即可跳转到 `/project/:id/chat`，继续进行大纲规划和后续创作。'
)

function emitRetry(): void {
  emit('retry')
}

function emitCreate(): void {
  emit('create')
}

function clearFilter(): void {
  emit('clear-filter')
}
</script>

<template>
  <section class="space-y-4">
    <div
      v-if="loading && projects.length > 0"
      class="flex items-center justify-between rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.72)] px-4 py-3 text-sm text-[color:var(--app-text-secondary)]"
    >
      <span>正在刷新项目列表…</span>
      <span class="mono-meta text-[10px] text-[color:var(--app-text-tertiary)]">sync</span>
    </div>

    <div v-if="showSkeleton" class="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
      <GlassPanel
        v-for="index in 6"
        :key="index"
        variant="soft"
        class="min-h-[258px] space-y-4 p-5"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 space-y-2">
            <NSkeleton text :repeat="2" />
          </div>
          <NSkeleton round height="40px" width="40px" />
        </div>
        <NSkeleton round height="132px" />
        <div class="space-y-2">
          <NSkeleton text :repeat="2" />
        </div>
      </GlassPanel>
    </div>

    <div v-else-if="projects.length > 0" class="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
      <ProjectCard
        v-for="project in projects"
        :key="project.id"
        :deleting="deletingById[project.id] ?? false"
        :project="project"
        :renaming="renamingById[project.id] ?? false"
        @delete="$emit('delete', $event)"
        @open="$emit('open', $event)"
        @rename="$emit('rename', $event)"
      />
    </div>

    <GlassPanel
      v-else-if="error"
      variant="strong"
      class="rounded-[var(--radius-2xl)] p-8 md:p-10"
    >
      <p class="mono-meta mb-3 text-[color:#9f4b2a]">加载失败</p>
      <h3 class="m-0 text-2xl font-semibold text-[color:var(--app-text-primary)]">项目列表暂时不可用</h3>
      <p class="mt-4 max-w-[44rem] text-sm leading-7 text-[color:var(--app-text-secondary)]">
        {{ error }}
      </p>
      <div class="mt-6 flex flex-wrap gap-3">
        <NButton secondary strong @click="emitRetry">重新加载</NButton>
        <NButton type="primary" @click="emitCreate">先新建一个项目</NButton>
      </div>
    </GlassPanel>

    <GlassPanel
      v-else
      variant="strong"
      class="relative overflow-hidden rounded-[var(--radius-2xl)] p-8 md:p-10"
    >
      <div class="absolute inset-y-0 right-0 w-[38%] bg-[radial-gradient(circle_at_top,rgba(143,191,159,0.16),transparent_66%)]" />
      <div class="relative z-10 grid gap-6 lg:grid-cols-[minmax(0,1fr)_240px] lg:items-end">
        <div>
          <p class="mono-meta mb-3 text-[color:var(--app-text-tertiary)]">
            {{ isFilteredEmptyState ? '筛选结果为空' : '空状态引导' }}
          </p>
          <h3 class="m-0 max-w-[30rem] text-3xl font-semibold leading-tight text-[color:var(--app-text-primary)]">
            {{ emptyTitle }}
          </h3>
          <p class="mt-4 max-w-[40rem] text-sm leading-7 text-[color:var(--app-text-secondary)]">
            {{ emptyDescription }}
          </p>

          <div class="mt-6 flex flex-wrap gap-3">
            <NButton type="primary" @click="emitCreate">
              {{ isFilteredEmptyState ? '新建一个项目' : '创建第一个项目' }}
            </NButton>
            <NButton v-if="isFilteredEmptyState" secondary strong @click="clearFilter">
              查看全部项目
            </NButton>
          </div>
        </div>

        <div class="rounded-[var(--radius-2xl)] border border-dashed border-[color:var(--app-border-subtle)] bg-[rgba(255,253,248,0.78)] p-5 text-sm leading-7 text-[color:var(--app-text-secondary)]">
          <div class="mono-meta mb-3 text-[10px] text-[color:var(--app-text-tertiary)]">开始方式</div>
          <div>1. 输入演示主题</div>
          <div>2. 新建项目并进入对话工作区</div>
          <div>3. 后续阶段再接入资料上传与 Agent 规划</div>
        </div>
      </div>
    </GlassPanel>
  </section>
</template>
