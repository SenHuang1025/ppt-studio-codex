import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { chatService, type ChatMessageListOptions } from '@/services/chatService'
import { fileService } from '@/services/fileService'
import { projectService } from '@/services/projectService'
import { themeService } from '@/services/themeService'
import type { ChatMessage } from '@/types/chat'
import type { UploadedFile } from '@/types/file'
import type { ProjectDetailResponse, ProjectPage } from '@/types/project'
import { MAX_UPLOAD_FILE_SIZE_BYTES, UPLOAD_FILE_EXTENSIONS } from '@/types/file'
import { DEFAULT_PREVIEW_THEME_ID, type ThemeConfig } from '@/types/theme'
import { getFileExtension, SUPPORTED_UPLOAD_EXTENSION_SET } from '@/utils/file'

export type WorkspaceMode = 'chat' | 'preview'

interface InitializeWorkspacePayload {
  mode: WorkspaceMode
  projectId: string
}

interface LoadProjectOptions {
  force?: boolean
}

interface LoadFilesOptions {
  force?: boolean
}

interface LoadChatMessagesOptions extends ChatMessageListOptions {
  force?: boolean
}

interface LoadPageChatMessagesOptions {
  force?: boolean
}

interface LoadThemePresetsOptions {
  force?: boolean
}

interface SyncPreviewThemeOptions {
  force?: boolean
}

interface UploadFilesResult {
  errors: string[]
  uploadedFiles: UploadedFile[]
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const currentProjectId = ref<string | null>(null)
  const currentMode = ref<WorkspaceMode>('chat')
  const currentPreviewPage = ref<number>(1)
  const project = ref<ProjectDetailResponse | null>(null)
  const projectLoading = ref(false)
  const projectLoaded = ref(false)
  const projectError = ref<string | null>(null)
  const uploadedFiles = ref<UploadedFile[]>([])
  const filesLoading = ref(false)
  const filesLoaded = ref(false)
  const filesUploading = ref(false)
  const filesError = ref<string | null>(null)
  const deletingFileIds = ref<string[]>([])
  const chatMessages = ref<ChatMessage[]>([])
  const chatMessagesLoading = ref(false)
  const chatMessagesLoaded = ref(false)
  const chatMessagesError = ref<string | null>(null)
  const previewProjectChatExpanded = ref(false)
  const pageChatMessages = ref<Record<number, ChatMessage[]>>({})
  const pageChatMessagesLoading = ref<Record<number, boolean>>({})
  const pageChatMessagesLoaded = ref<Record<number, boolean>>({})
  const pageChatMessagesError = ref<Record<number, string | null>>({})
  const themePresets = ref<ThemeConfig[]>([])
  const themePresetsLoading = ref(false)
  const themePresetsLoaded = ref(false)
  const themePresetsError = ref<string | null>(null)
  const themeApplyingId = ref<string | null>(null)
  const previewThemeSyncing = ref(false)
  const previewThemeSyncError = ref<string | null>(null)

  const hasProject = computed<boolean>(() => project.value !== null)
  const projectName = computed<string>(() => project.value?.name ?? '未命名项目')
  const activePreviewThemeId = computed<string>(() => project.value?.theme_config?.id ?? DEFAULT_PREVIEW_THEME_ID)
  const projectPages = computed<ProjectPage[]>(() =>
    [...(project.value?.pages ?? [])].sort((left, right) => left.page_number - right.page_number)
  )
  const totalPreviewPages = computed<number>(() => {
    const outlineTotal = project.value?.outline?.total_pages ?? 0
    const projectTotal = project.value?.total_pages ?? 0
    const highestGeneratedPageNumber = projectPages.value[projectPages.value.length - 1]?.page_number ?? 0

    return Math.max(1, outlineTotal, projectTotal, highestGeneratedPageNumber)
  })

  let lastLoadToken = 0
  let lastFilesLoadToken = 0
  let lastChatMessagesLoadToken = 0
  let lastChatMessagesOptions: ChatMessageListOptions = {}
  let lastPageChatMessagesLoadTokens: Record<number, number> = {}
  let lastPreviewThemeSyncKey: string | null = null

  async function initializeWorkspace(payload: InitializeWorkspacePayload): Promise<void> {
    const normalizedProjectId = payload.projectId.trim()
    const projectChanged = normalizedProjectId !== currentProjectId.value

    currentProjectId.value = normalizedProjectId
    setMode(payload.mode)

    if (projectChanged) {
      currentPreviewPage.value = 1
      project.value = null
      projectLoaded.value = false
      projectError.value = null
      previewProjectChatExpanded.value = false
      previewThemeSyncError.value = null
      themeApplyingId.value = null
      lastPreviewThemeSyncKey = null
      resetFileState()
      resetChatMessageState()
    }

    await loadProject(normalizedProjectId, {
      force: projectChanged || !projectLoaded.value
    })
    await loadFiles(normalizedProjectId, {
      force: projectChanged || !filesLoaded.value
    })
    await loadChatMessages(normalizedProjectId, {
      includePageMessages: true,
      force: projectChanged || !chatMessagesLoaded.value
    })

    if (payload.mode === 'preview') {
      await Promise.all([
        loadThemePresets().catch(() => undefined),
        syncPreviewTheme({ force: projectChanged }).catch(() => undefined)
      ])
    }
  }

  async function loadProject(projectId: string, options?: LoadProjectOptions): Promise<ProjectDetailResponse | null> {
    const normalizedProjectId = projectId.trim()

    if (!normalizedProjectId) {
      resetWorkspace()
      throw new Error('Project id is required.')
    }

    if (!options?.force && projectLoaded.value && currentProjectId.value === normalizedProjectId && project.value) {
      return project.value
    }

    const loadToken = ++lastLoadToken
    currentProjectId.value = normalizedProjectId
    projectLoading.value = true
    projectError.value = null

    try {
      const projectDetail = await projectService.getById(normalizedProjectId)

      if (loadToken !== lastLoadToken) {
        return projectDetail
      }

      project.value = projectDetail
      projectLoaded.value = true
      syncPreviewPage(projectDetail)
      return projectDetail
    } catch (error: unknown) {
      if (loadToken === lastLoadToken) {
        projectError.value = normalizeWorkspaceError(error)
        projectLoaded.value = false

        if (currentProjectId.value === normalizedProjectId) {
          project.value = null
        }
      }

      throw error
    } finally {
      if (loadToken === lastLoadToken) {
        projectLoading.value = false
      }
    }
  }

  function setMode(mode: WorkspaceMode): void {
    currentMode.value = mode
  }

  function setPreviewProjectChatExpanded(expanded: boolean): void {
    previewProjectChatExpanded.value = expanded
  }

  function setPreviewPage(pageNumber: number): void {
    const normalizedPage = Number.isFinite(pageNumber) ? Math.max(1, Math.floor(pageNumber)) : 1
    currentPreviewPage.value = normalizedPage
  }

  async function loadFiles(projectId: string, options?: LoadFilesOptions): Promise<UploadedFile[]> {
    const normalizedProjectId = projectId.trim()

    if (!normalizedProjectId) {
      resetFileState()
      throw new Error('Project id is required.')
    }

    if (!options?.force && filesLoaded.value && currentProjectId.value === normalizedProjectId) {
      return uploadedFiles.value
    }

    const loadToken = ++lastFilesLoadToken
    currentProjectId.value = normalizedProjectId
    filesLoading.value = true
    filesError.value = null

    try {
      const response = await fileService.list(normalizedProjectId)

      if (loadToken !== lastFilesLoadToken) {
        return response.files
      }

      uploadedFiles.value = sortUploadedFiles(response.files)
      filesLoaded.value = true
      return uploadedFiles.value
    } catch (error: unknown) {
      if (loadToken === lastFilesLoadToken) {
        filesError.value = normalizeWorkspaceError(error)
        filesLoaded.value = false

        if (currentProjectId.value === normalizedProjectId) {
          uploadedFiles.value = []
        }
      }

      throw error
    } finally {
      if (loadToken === lastFilesLoadToken) {
        filesLoading.value = false
      }
    }
  }

  async function refreshWorkspace(): Promise<void> {
    const projectId = requireCurrentProjectId()

    await loadProject(projectId, { force: true })
    await loadFiles(projectId, { force: true })
    await loadChatMessages(projectId, { ...lastChatMessagesOptions, force: true })
    if (pageChatMessagesLoaded.value[currentPreviewPage.value]) {
      await loadPageChatMessages(projectId, currentPreviewPage.value, { force: true }).catch(() => undefined)
    }

    if (currentMode.value === 'preview') {
      await Promise.all([
        loadThemePresets().catch(() => undefined),
        syncPreviewTheme({ force: true }).catch(() => undefined)
      ])
    }
  }

  async function loadChatMessages(
    projectId: string,
    options?: LoadChatMessagesOptions
  ): Promise<ChatMessage[]> {
    const normalizedProjectId = projectId.trim()

    if (!normalizedProjectId) {
      resetChatMessageState()
      throw new Error('Project id is required.')
    }

    const normalizedOptions = normalizeChatMessageListOptions(options)
    const shouldReuseCache = !options?.force
      && chatMessagesLoaded.value
      && currentProjectId.value === normalizedProjectId
      && areChatMessageListOptionsEqual(lastChatMessagesOptions, normalizedOptions)

    if (shouldReuseCache) {
      return chatMessages.value
    }

    const loadToken = ++lastChatMessagesLoadToken
    currentProjectId.value = normalizedProjectId
    chatMessagesLoading.value = true
    chatMessagesError.value = null

    try {
      const response = await chatService.list(normalizedProjectId, normalizedOptions)

      if (loadToken !== lastChatMessagesLoadToken) {
        return response.messages
      }

      chatMessages.value = sortChatMessages(response.messages)
      chatMessagesLoaded.value = true
      lastChatMessagesOptions = normalizedOptions
      return chatMessages.value
    } catch (error: unknown) {
      if (loadToken === lastChatMessagesLoadToken) {
        chatMessagesError.value = normalizeWorkspaceError(error)
        chatMessagesLoaded.value = false

        if (currentProjectId.value === normalizedProjectId) {
          chatMessages.value = []
        }
      }

      throw error
    } finally {
      if (loadToken === lastChatMessagesLoadToken) {
        chatMessagesLoading.value = false
      }
    }
  }

  async function refreshChatMessages(): Promise<void> {
    const projectId = requireCurrentProjectId()
    await loadChatMessages(projectId, {
      ...lastChatMessagesOptions,
      force: true
    })
  }

  async function loadPageChatMessages(
    projectId: string,
    pageNumber: number,
    options?: LoadPageChatMessagesOptions
  ): Promise<ChatMessage[]> {
    const normalizedProjectId = projectId.trim()
    const normalizedPageNumber = normalizePageNumber(pageNumber)

    if (!normalizedProjectId || normalizedPageNumber === null) {
      return []
    }

    if (!options?.force && pageChatMessagesLoaded.value[normalizedPageNumber]) {
      return pageChatMessages.value[normalizedPageNumber] ?? []
    }

    const requestToken = (lastPageChatMessagesLoadTokens[normalizedPageNumber] ?? 0) + 1
    lastPageChatMessagesLoadTokens = {
      ...lastPageChatMessagesLoadTokens,
      [normalizedPageNumber]: requestToken
    }
    pageChatMessagesLoading.value = {
      ...pageChatMessagesLoading.value,
      [normalizedPageNumber]: true
    }
    pageChatMessagesError.value = {
      ...pageChatMessagesError.value,
      [normalizedPageNumber]: null
    }

    try {
      const response = await chatService.list(normalizedProjectId, {
        includeGlobal: false,
        pageNumber: normalizedPageNumber
      })

      if (lastPageChatMessagesLoadTokens[normalizedPageNumber] !== requestToken) {
        return response.messages
      }

      pageChatMessages.value = {
        ...pageChatMessages.value,
        [normalizedPageNumber]: sortChatMessages(response.messages)
      }
      pageChatMessagesLoaded.value = {
        ...pageChatMessagesLoaded.value,
        [normalizedPageNumber]: true
      }
      return pageChatMessages.value[normalizedPageNumber] ?? []
    } catch (error: unknown) {
      if (lastPageChatMessagesLoadTokens[normalizedPageNumber] === requestToken) {
        pageChatMessages.value = {
          ...pageChatMessages.value,
          [normalizedPageNumber]: []
        }
        pageChatMessagesLoaded.value = {
          ...pageChatMessagesLoaded.value,
          [normalizedPageNumber]: false
        }
        pageChatMessagesError.value = {
          ...pageChatMessagesError.value,
          [normalizedPageNumber]: normalizeWorkspaceError(error)
        }
      }

      throw error
    } finally {
      if (lastPageChatMessagesLoadTokens[normalizedPageNumber] === requestToken) {
        pageChatMessagesLoading.value = {
          ...pageChatMessagesLoading.value,
          [normalizedPageNumber]: false
        }
      }
    }
  }

  async function refreshPageChatMessages(pageNumber: number): Promise<void> {
    const projectId = requireCurrentProjectId()
    await loadPageChatMessages(projectId, pageNumber, { force: true })
  }

  async function loadThemePresets(options?: LoadThemePresetsOptions): Promise<ThemeConfig[]> {
    if (!options?.force && themePresetsLoaded.value) {
      return themePresets.value
    }

    themePresetsLoading.value = true
    themePresetsError.value = null

    try {
      const response = await themeService.list()
      themePresets.value = response.themes
      themePresetsLoaded.value = true
      return themePresets.value
    } catch (error: unknown) {
      themePresetsError.value = normalizeWorkspaceError(error)

      if (!themePresetsLoaded.value) {
        themePresets.value = []
      }

      throw error
    } finally {
      themePresetsLoading.value = false
    }
  }

  async function syncPreviewTheme(options?: SyncPreviewThemeOptions): Promise<ThemeConfig> {
    const projectId = requireCurrentProjectId()
    const syncKey = buildPreviewThemeSyncKey(projectId, activePreviewThemeId.value)

    if (!options?.force && lastPreviewThemeSyncKey === syncKey) {
      const cachedTheme = themePresets.value.find((theme) => theme.id === activePreviewThemeId.value)

      if (cachedTheme) {
        return cachedTheme
      }
    }

    previewThemeSyncing.value = true
    previewThemeSyncError.value = null

    try {
      const response = await projectService.syncTheme(projectId)
      lastPreviewThemeSyncKey = buildPreviewThemeSyncKey(projectId, response.theme.id)
      return response.theme
    } catch (error: unknown) {
      previewThemeSyncError.value = normalizeWorkspaceError(error)
      lastPreviewThemeSyncKey = null
      throw error
    } finally {
      previewThemeSyncing.value = false
    }
  }

  async function applyTheme(themeConfig: ThemeConfig): Promise<ProjectDetailResponse> {
    const projectId = requireCurrentProjectId()
    themeApplyingId.value = themeConfig.id
    previewThemeSyncError.value = null

    try {
      const updatedProject = await projectService.updateTheme(projectId, themeConfig)
      project.value = updatedProject
      projectLoaded.value = true
      syncPreviewPage(updatedProject)
      lastPreviewThemeSyncKey = buildPreviewThemeSyncKey(
        updatedProject.id,
        updatedProject.theme_config?.id ?? DEFAULT_PREVIEW_THEME_ID
      )
      return updatedProject
    } catch (error: unknown) {
      previewThemeSyncError.value = normalizeWorkspaceError(error)
      throw error
    } finally {
      themeApplyingId.value = null
    }
  }

  async function uploadFilesForProject(selectedFiles: File[]): Promise<UploadFilesResult> {
    const projectId = requireCurrentProjectId()
    const { errors: validationErrors, validFiles } = validateUploadFiles(selectedFiles)
    const errors = [...validationErrors]
    const createdFiles: UploadedFile[] = []

    if (validFiles.length === 0) {
      filesError.value = errors.join('；')
      return {
        errors,
        uploadedFiles: createdFiles
      }
    }

    filesUploading.value = true
    filesError.value = null

    try {
      for (const file of validFiles) {
        try {
          const uploadedFile = await fileService.upload(projectId, file)
          createdFiles.push(uploadedFile)
        } catch (error: unknown) {
          errors.push(`${file.name}：${normalizeWorkspaceError(error)}`)
        }
      }

      if (createdFiles.length > 0 && currentProjectId.value === projectId) {
        uploadedFiles.value = mergeUploadedFiles(uploadedFiles.value, createdFiles)
        filesLoaded.value = true
      }

      if (errors.length > 0) {
        filesError.value = errors.join('；')
      }

      return {
        errors,
        uploadedFiles: createdFiles
      }
    } finally {
      filesUploading.value = false
    }
  }

  async function deleteUploadedFile(fileId: string): Promise<void> {
    const projectId = requireCurrentProjectId()
    const normalizedFileId = fileId.trim()

    if (!normalizedFileId) {
      throw new Error('File id is required.')
    }

    deletingFileIds.value = [...deletingFileIds.value, normalizedFileId]

    try {
      await fileService.remove(projectId, normalizedFileId)

      if (currentProjectId.value === projectId) {
        uploadedFiles.value = uploadedFiles.value.filter((file) => file.id !== normalizedFileId)
      }
    } catch (error: unknown) {
      filesError.value = normalizeWorkspaceError(error)
      throw error
    } finally {
      deletingFileIds.value = deletingFileIds.value.filter((id) => id !== normalizedFileId)
    }
  }

  function isDeletingFile(fileId: string): boolean {
    return deletingFileIds.value.includes(fileId)
  }

  function resetWorkspace(): void {
    currentProjectId.value = null
    currentMode.value = 'chat'
    currentPreviewPage.value = 1
    project.value = null
    projectLoading.value = false
    projectLoaded.value = false
    projectError.value = null
    previewProjectChatExpanded.value = false
    previewThemeSyncing.value = false
    previewThemeSyncError.value = null
    themeApplyingId.value = null
    lastPreviewThemeSyncKey = null
    resetFileState()
    resetChatMessageState()
  }

  function syncPreviewPage(projectDetail: ProjectDetailResponse): void {
    const highestGeneratedPageNumber = projectDetail.pages.reduce((maxPageNumber, page) =>
      Math.max(maxPageNumber, page.page_number), 0)
    const availablePages = Math.max(
      projectDetail.total_pages,
      projectDetail.outline?.total_pages ?? 0,
      highestGeneratedPageNumber
    )

    if (availablePages <= 0) {
      currentPreviewPage.value = 1
      return
    }

    if (currentPreviewPage.value < 1 || currentPreviewPage.value > availablePages) {
      currentPreviewPage.value = Math.min(Math.max(1, currentPreviewPage.value), availablePages)
      return
    }

    currentPreviewPage.value = Math.min(currentPreviewPage.value, availablePages)
  }

  function resetFileState(): void {
    uploadedFiles.value = []
    filesLoading.value = false
    filesLoaded.value = false
    filesUploading.value = false
    filesError.value = null
    deletingFileIds.value = []
  }

  function resetChatMessageState(): void {
    chatMessages.value = []
    chatMessagesLoading.value = false
    chatMessagesLoaded.value = false
    chatMessagesError.value = null
    resetPageChatMessageState()
    lastChatMessagesOptions = {}
  }

  function resetPageChatMessageState(): void {
    pageChatMessages.value = {}
    pageChatMessagesLoading.value = {}
    pageChatMessagesLoaded.value = {}
    pageChatMessagesError.value = {}
    lastPageChatMessagesLoadTokens = {}
  }

  function requireCurrentProjectId(): string {
    const projectId = currentProjectId.value?.trim()

    if (!projectId) {
      throw new Error('Project id is required.')
    }

    return projectId
  }

  return {
    chatMessages,
    chatMessagesError,
    chatMessagesLoaded,
    chatMessagesLoading,
    deleteUploadedFile,
    filesError,
    filesLoaded,
    filesLoading,
    filesUploading,
    currentMode,
    currentPreviewPage,
    currentProjectId,
    pageChatMessages,
    pageChatMessagesError,
    pageChatMessagesLoaded,
    pageChatMessagesLoading,
    previewProjectChatExpanded,
    activePreviewThemeId,
    applyTheme,
    hasProject,
    initializeWorkspace,
    isDeletingFile,
    loadChatMessages,
    loadFiles,
    loadPageChatMessages,
    loadProject,
    loadThemePresets,
    project,
    projectError,
    projectLoaded,
    projectLoading,
    projectName,
    projectPages,
    previewThemeSyncError,
    previewThemeSyncing,
    refreshChatMessages,
    refreshPageChatMessages,
    refreshWorkspace,
    resetPageChatMessageState,
    resetWorkspace,
    setMode,
    setPreviewPage,
    setPreviewProjectChatExpanded,
    syncPreviewTheme,
    themeApplyingId,
    themePresets,
    themePresetsError,
    themePresetsLoaded,
    themePresetsLoading,
    totalPreviewPages,
    uploadedFiles,
    uploadFiles: uploadFilesForProject
  }
})

function normalizeWorkspaceError(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }

  return '项目上下文加载失败，请确认 Python 后端与项目 API 已正常运行。'
}

function validateUploadFiles(files: File[]): { errors: string[]; validFiles: File[] } {
  const errors: string[] = []
  const validFiles: File[] = []

  for (const file of files) {
    const extension = getFileExtension(file.name)

    if (!extension || !SUPPORTED_UPLOAD_EXTENSION_SET.has(extension)) {
      errors.push(`${file.name} 格式不支持，仅允许 ${UPLOAD_FILE_EXTENSIONS.join(', ')}。`)
      continue
    }

    if (file.size > MAX_UPLOAD_FILE_SIZE_BYTES) {
      errors.push(`${file.name} 超过 50MB 单文件限制。`)
      continue
    }

    validFiles.push(file)
  }

  return {
    errors,
    validFiles
  }
}

function mergeUploadedFiles(existingFiles: UploadedFile[], nextFiles: UploadedFile[]): UploadedFile[] {
  const fileMap = new Map<string, UploadedFile>()

  for (const file of existingFiles) {
    fileMap.set(file.id, file)
  }

  for (const file of nextFiles) {
    fileMap.set(file.id, file)
  }

  return sortUploadedFiles(Array.from(fileMap.values()))
}

function normalizeChatMessageListOptions(options?: ChatMessageListOptions): ChatMessageListOptions {
  return {
    includeGlobal: options?.includeGlobal ?? false,
    includePageMessages: options?.includePageMessages ?? false,
    limit: options?.limit,
    pageNumber: options?.pageNumber
  }
}

function areChatMessageListOptionsEqual(
  left: ChatMessageListOptions,
  right: ChatMessageListOptions
): boolean {
  return left.includeGlobal === right.includeGlobal
    && left.includePageMessages === right.includePageMessages
    && left.limit === right.limit
    && left.pageNumber === right.pageNumber
}

function normalizePageNumber(pageNumber: number): number | null {
  if (!Number.isFinite(pageNumber)) {
    return null
  }

  return Math.max(1, Math.floor(pageNumber))
}

function sortChatMessages(messages: ChatMessage[]): ChatMessage[] {
  return [...messages].sort((left, right) => {
    const leftTimestamp = Date.parse(left.created_at)
    const rightTimestamp = Date.parse(right.created_at)

    if (!Number.isNaN(leftTimestamp) && !Number.isNaN(rightTimestamp) && leftTimestamp !== rightTimestamp) {
      return leftTimestamp - rightTimestamp
    }

    return left.id.localeCompare(right.id)
  })
}

function sortUploadedFiles(files: UploadedFile[]): UploadedFile[] {
  return [...files].sort((left, right) => {
    const leftTimestamp = Date.parse(left.created_at)
    const rightTimestamp = Date.parse(right.created_at)

    if (!Number.isNaN(leftTimestamp) && !Number.isNaN(rightTimestamp) && leftTimestamp !== rightTimestamp) {
      return rightTimestamp - leftTimestamp
    }

    return right.id.localeCompare(left.id)
  })
}

function buildPreviewThemeSyncKey(projectId: string, themeId: string): string {
  return `${projectId}:${themeId}`
}
