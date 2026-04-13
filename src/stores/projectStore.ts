import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { projectService } from '@/services/projectService'
import type { Project, ProjectCreatePayload, ProjectStatus } from '@/types/project'
import { PROJECT_STATUS_META, matchesProjectStatusFilter, sortProjectsByUpdatedAt } from '@/utils/project'

export type ProjectFilterValue = ProjectStatus | 'all'

export interface ProjectFilterOption {
  label: string
  value: ProjectFilterValue
}

export const PROJECT_FILTER_OPTIONS: ProjectFilterOption[] = [
  { label: '全部', value: 'all' },
  { label: PROJECT_STATUS_META.draft.label, value: 'draft' },
  { label: PROJECT_STATUS_META.planning.label, value: 'planning' },
  { label: PROJECT_STATUS_META.generating.label, value: 'generating' },
  { label: PROJECT_STATUS_META.editing.label, value: 'editing' },
  { label: PROJECT_STATUS_META.completed.label, value: 'completed' },
  { label: PROJECT_STATUS_META.archived.label, value: 'archived' }
]

interface LoadProjectsOptions {
  filter?: ProjectFilterValue
  silent?: boolean
}

const DEFAULT_SORT = 'updated_at'
const DEFAULT_ORDER = 'desc'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const activeFilter = ref<ProjectFilterValue>('all')
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref<string | null>(null)
  const creating = ref(false)
  const renamingById = ref<Record<string, boolean>>({})
  const deletingById = ref<Record<string, boolean>>({})

  const total = computed<number>(() => projects.value.length)
  const hasProjects = computed<boolean>(() => projects.value.length > 0)
  const isEmpty = computed<boolean>(() => loaded.value && !loading.value && !error.value && projects.value.length === 0)
  const activeFilterLabel = computed<string>(() => {
    return PROJECT_FILTER_OPTIONS.find((option) => option.value === activeFilter.value)?.label ?? '全部'
  })

  async function ensureLoaded(): Promise<void> {
    if (loaded.value) {
      return
    }

    await loadProjects()
  }

  async function loadProjects(options?: LoadProjectsOptions): Promise<void> {
    if (options?.filter) {
      activeFilter.value = options.filter
    }

    if (!options?.silent) {
      loading.value = true
    }

    error.value = null

    try {
      const response = await projectService.list({
        order: DEFAULT_ORDER,
        sort: DEFAULT_SORT,
        status: activeFilter.value === 'all' ? undefined : activeFilter.value
      })

      projects.value = sortProjectsByUpdatedAt(response.projects)
      loaded.value = true
    } catch (cause: unknown) {
      error.value = normalizeProjectError(cause)

      if (!loaded.value) {
        projects.value = []
      }

      throw cause
    } finally {
      if (!options?.silent) {
        loading.value = false
      }
    }
  }

  async function setFilter(filter: ProjectFilterValue): Promise<void> {
    if (filter === activeFilter.value && loaded.value) {
      return
    }

    await loadProjects({ filter })
  }

  async function createProject(payload: ProjectCreatePayload): Promise<Project> {
    creating.value = true
    error.value = null

    try {
      const createdProject = await projectService.create(payload)

      if (matchesProjectStatusFilter(createdProject, activeFilter.value)) {
        projects.value = sortProjectsByUpdatedAt([
          createdProject,
          ...projects.value.filter((project) => project.id !== createdProject.id)
        ])
      }

      loaded.value = true
      return createdProject
    } catch (cause: unknown) {
      error.value = normalizeProjectError(cause)
      throw cause
    } finally {
      creating.value = false
    }
  }

  async function renameProject(projectId: string, name: string): Promise<Project> {
    setPendingState(renamingById.value, projectId, true)
    error.value = null

    try {
      const updatedProject = await projectService.update(projectId, { name })
      upsertProject(updatedProject)
      return updatedProject
    } catch (cause: unknown) {
      error.value = normalizeProjectError(cause)
      throw cause
    } finally {
      setPendingState(renamingById.value, projectId, false)
    }
  }

  async function deleteProject(projectId: string): Promise<void> {
    setPendingState(deletingById.value, projectId, true)
    error.value = null

    try {
      await projectService.remove(projectId)
      projects.value = projects.value.filter((project) => project.id !== projectId)
      loaded.value = true
    } catch (cause: unknown) {
      error.value = normalizeProjectError(cause)
      throw cause
    } finally {
      setPendingState(deletingById.value, projectId, false)
    }
  }

  function isRenaming(projectId: string): boolean {
    return renamingById.value[projectId] ?? false
  }

  function isDeleting(projectId: string): boolean {
    return deletingById.value[projectId] ?? false
  }

  function upsertProject(project: Project): void {
    const nextProjects = projects.value.filter((item) => item.id !== project.id)

    if (matchesProjectStatusFilter(project, activeFilter.value)) {
      nextProjects.unshift(project)
    }

    projects.value = sortProjectsByUpdatedAt(nextProjects)
    loaded.value = true
  }

  return {
    activeFilter,
    activeFilterLabel,
    createProject,
    creating,
    deleteProject,
    deletingById,
    ensureLoaded,
    error,
    hasProjects,
    isDeleting,
    isEmpty,
    isRenaming,
    loadProjects,
    loaded,
    loading,
    projects,
    renameProject,
    renamingById,
    setFilter,
    total
  }
})

function normalizeProjectError(cause: unknown): string {
  if (cause instanceof Error && cause.message.trim()) {
    return cause.message.trim()
  }

  return '项目请求失败，请检查 Python 后端和 Electron 侧车是否已经就绪。'
}

function setPendingState(target: Record<string, boolean>, projectId: string, value: boolean): void {
  if (value) {
    target[projectId] = true
    return
  }

  delete target[projectId]
}
