<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, useDialog, useMessage } from 'naive-ui'
import GlassPanel from '@/components/common/GlassPanel.vue'
import CreateProjectDialog from '@/components/dashboard/CreateProjectDialog.vue'
import ProjectFilter from '@/components/dashboard/ProjectFilter.vue'
import ProjectGrid from '@/components/dashboard/ProjectGrid.vue'
import { notifyApiError, resolveAppErrorMessage } from '@/services/errorHandling'
import { useProjectStore } from '@/stores/projectStore'
import type { ProjectFilterValue } from '@/stores/projectStore'
import type { Project } from '@/types/project'

type ProjectDialogMode = 'create' | 'rename'

const router = useRouter()
const dialog = useDialog()
const message = useMessage()
const projectStore = useProjectStore()

const heroDraftName = ref<string>('')
const dialogVisible = ref<boolean>(false)
const dialogMode = ref<ProjectDialogMode>('create')
const renameTarget = ref<Project | null>(null)

const heroTitle = computed<string>(() =>
  projectStore.hasProjects ? '继续最近的演示稿，或立即开启一个新项目。' : '把一个主题，变成一份真正可继续创作的演示稿。'
)
const heroDescription = computed<string>(() =>
  projectStore.hasProjects
    ? 'Dashboard 现在直接连接真实项目 API。你可以筛选项目、继续已有稿件，或从一个新标题立即进入对话工作区。'
    : '先确定主题，再创建项目进入 `/project/:id/chat`。资料上传和 Agent 规划会在后续阶段继续补齐，但首页已经可以真实管理项目。'
)
const dialogInitialName = computed<string>(() =>
  dialogMode.value === 'rename' ? renameTarget.value?.name ?? '' : heroDraftName.value.trim()
)
const summaryCards = computed<Array<{ label: string; value: string }>>(() => [
  { label: '当前筛选', value: projectStore.activeFilterLabel },
  { label: '项目数量', value: String(projectStore.total) },
  { label: '工作区入口', value: '/project/:id/chat' }
])

onMounted(() => {
  void projectStore.ensureLoaded().catch(() => undefined)
})

function openCreateDialog(prefillName?: string): void {
  dialogMode.value = 'create'
  renameTarget.value = null

  if (typeof prefillName === 'string') {
    heroDraftName.value = prefillName
  }

  dialogVisible.value = true
}

function openRenameDialog(project: Project): void {
  dialogMode.value = 'rename'
  renameTarget.value = project
  dialogVisible.value = true
}

async function handleDialogSubmit(name: string): Promise<void> {
  try {
    if (dialogMode.value === 'rename' && renameTarget.value) {
      const renamedProject = await projectStore.renameProject(renameTarget.value.id, name)
      message.success(`项目已重命名为「${renamedProject.name}」`)
      dialogVisible.value = false
      renameTarget.value = null
      return
    }

    const createdProject = await projectStore.createProject({ name })
    message.success(`已创建项目「${createdProject.name}」`)
    dialogVisible.value = false
    heroDraftName.value = ''

    await router.push({
      name: 'project-chat',
      params: { id: createdProject.id }
    })
  } catch (cause: unknown) {
    notifyApiError(cause, {
      fallback: '项目操作失败，请稍后重试。'
    })
  }
}

function handleOpenProject(projectId: string): void {
  void router.push({
    name: 'project-chat',
    params: { id: projectId }
  })
}

function handleDeleteProject(project: Project): void {
  dialog.warning({
    closable: false,
    content: `删除「${project.name}」后，本地项目目录和数据库记录都会被移除，此操作不可恢复。`,
    negativeText: '取消',
    positiveText: '确认删除',
    positiveButtonProps: {
      type: 'error'
    },
    title: '删除项目',
    async onPositiveClick() {
      try {
        await projectStore.deleteProject(project.id)
        message.success(`已删除项目「${project.name}」`)
      } catch (cause: unknown) {
        notifyApiError(cause, {
          fallback: '删除项目失败，请稍后重试。'
        })
        throw cause
      }
    }
  })
}

function handleCreateFromHero(): void {
  openCreateDialog(heroDraftName.value)
}

async function handleFilterChange(filter: ProjectFilterValue): Promise<void> {
  try {
    await projectStore.setFilter(filter)
  } catch (cause: unknown) {
    notifyApiError(cause, {
      fallback: '项目筛选失败，请稍后重试。'
    })
  }
}

async function retryLoadProjects(): Promise<void> {
  try {
    await projectStore.loadProjects()
  } catch (cause: unknown) {
    notifyApiError(cause, {
      fallback: '项目加载失败，请稍后重试。'
    })
  }
}

function clearFilter(): void {
  void handleFilterChange('all')
}

function closeDialog(): void {
  dialogVisible.value = false
  renameTarget.value = null
}

function resolveErrorMessage(cause: unknown): string {
  return resolveAppErrorMessage(cause, '项目操作失败，请稍后重试。')
}
</script>

<template>
  <section class="flex min-h-[calc(100vh-3rem)] flex-col gap-6 pb-4">
    <GlassPanel variant="strong" class="relative overflow-hidden p-8 md:p-10">
      <div class="absolute inset-0 bg-[var(--gradient-paper-wash)] opacity-90" />
      <div class="absolute inset-y-0 right-0 w-[34%] bg-[radial-gradient(circle_at_top,rgba(143,191,159,0.18),transparent_68%)]" />

      <div class="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,1.12fr)_320px]">
        <div class="flex flex-col justify-between gap-8">
          <div class="max-w-[46rem]">
            <p class="mono-meta mb-4 text-[color:var(--app-text-secondary)]">Dashboard / AI Agent 演示稿工作台</p>
            <h1 class="page-title max-w-[48rem] gradient-text-primary">
              {{ heroTitle }}
            </h1>
            <p class="page-subtitle mt-5 max-w-[42rem]">
              {{ heroDescription }}
            </p>
          </div>

          <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <NInput
              v-model:value="heroDraftName"
              clearable
              placeholder="输入你想创建的 PPT 主题，例如：品牌焕新提案"
              size="large"
              @keydown.enter.prevent="handleCreateFromHero"
            />
            <div class="flex flex-wrap gap-3">
              <NButton secondary strong size="large" @click="retryLoadProjects">刷新列表</NButton>
              <NButton type="primary" size="large" @click="handleCreateFromHero">新建项目</NButton>
            </div>
          </div>
        </div>

        <div class="grid gap-3 self-start">
          <div
            v-for="card in summaryCards"
            :key="card.label"
            class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,253,248,0.76)] p-4 shadow-[var(--shadow-glass-1)]"
          >
            <div class="mono-meta mb-2 text-[10px] text-[color:var(--app-text-tertiary)]">{{ card.label }}</div>
            <div class="text-sm font-medium text-[color:var(--app-text-primary)]">{{ card.value }}</div>
          </div>

          <div class="rounded-[var(--radius-xl)] border border-dashed border-[color:var(--app-border-subtle)] bg-[rgba(255,253,248,0.64)] p-4 text-sm leading-7 text-[color:var(--app-text-secondary)]">
            支持项目列表、状态筛选、新建、删除、重命名和最小路由跳转。文件上传、SSE、预览与工作区正式实现仍留在后续任务。
          </div>
        </div>
      </div>
    </GlassPanel>

    <GlassPanel
      v-if="projectStore.error && projectStore.projects.length > 0"
      class="flex flex-col gap-3 border-[rgba(183,91,53,0.16)] bg-[rgba(255,248,237,0.78)] p-4 md:flex-row md:items-center md:justify-between"
    >
      <div>
        <div class="mono-meta mb-2 text-[10px] text-[color:#9f4b2a]">请求异常</div>
        <div class="text-sm text-[color:var(--app-text-secondary)]">{{ projectStore.error }}</div>
      </div>
      <NButton secondary strong @click="retryLoadProjects">重新加载</NButton>
    </GlassPanel>

    <ProjectFilter
      :loading="projectStore.loading"
      :model-value="projectStore.activeFilter"
      :total="projectStore.total"
      @update:model-value="handleFilterChange"
    />

    <ProjectGrid
      :active-filter="projectStore.activeFilter"
      :deleting-by-id="projectStore.deletingById"
      :error="projectStore.error"
      :loaded="projectStore.loaded"
      :loading="projectStore.loading"
      :projects="projectStore.projects"
      :renaming-by-id="projectStore.renamingById"
      @clear-filter="clearFilter"
      @create="openCreateDialog()"
      @delete="handleDeleteProject"
      @open="handleOpenProject"
      @rename="openRenameDialog"
      @retry="retryLoadProjects"
    />

    <CreateProjectDialog
      :initial-name="dialogInitialName"
      :mode="dialogMode"
      :pending="dialogMode === 'create' ? projectStore.creating : Boolean(renameTarget && projectStore.isRenaming(renameTarget.id))"
      :show="dialogVisible"
      @submit="handleDialogSubmit"
      @update:show="(value) => (value ? (dialogVisible = value) : closeDialog())"
    />
  </section>
</template>
