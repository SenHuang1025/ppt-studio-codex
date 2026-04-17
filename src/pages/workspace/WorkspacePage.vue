<script setup lang="ts">
import { computed, h, onBeforeUnmount, ref, toRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NInput, NSkeleton, NTag, useDialog, useMessage } from 'naive-ui'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'
import GlassPanel from '@/components/common/GlassPanel.vue'
import ModeSwitchPill from '@/components/common/ModeSwitchPill.vue'
import OutlinePanel from '@/components/outline/OutlinePanel.vue'
import PreviewPanel from '@/components/preview/PreviewPanel.vue'
import { usePageOptimizeSession } from '@/composables/usePageOptimizeSession'
import { usePreviewWorkspace } from '@/composables/usePreviewWorkspace'
import { useWorkspaceAgentSession } from '@/composables/useWorkspaceAgentSession'
import { projectExportService } from '@/services/exportService'
import { notifyApiError, resolveAppErrorMessage } from '@/services/errorHandling'
import { pageService } from '@/services/pageService'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import type { WorkspaceMode } from '@/stores/workspaceStore'
import type { ProjectExportTask } from '@/types/export'
import { UPLOAD_FILE_ACCEPT_ATTRIBUTE, type UploadedFile } from '@/types/file'
import type { Outline, PageVersion } from '@/types/project'
import type { PreviewVersionSelection } from '@/types/preview'
import type { ThemeConfig } from '@/types/theme'
import { PROJECT_STATUS_META, formatProjectUpdatedAt } from '@/utils/project'

const props = defineProps<{
  projectId: string
  mode: WorkspaceMode
}>()

const dialog = useDialog()
const message = useMessage()
const route = useRoute()
const router = useRouter()
const workspaceStore = useWorkspaceStore()
const chatPanelRef = ref<InstanceType<typeof ChatPanel> | null>(null)
const previewPanelRef = ref<InstanceType<typeof PreviewPanel> | null>(null)
const chatDraft = ref<string>('')
const optimizeDraft = ref<string>('')
const versionDrawerLoading = ref(false)
const versionDrawerRollingBack = ref(false)
const versionDrawerRollingBackVersion = ref<number | null>(null)
const versionDrawerShow = ref(false)
const versionDrawerPageNumber = ref<number | null>(null)
const versionDrawerVersions = ref<PageVersion[]>([])
const selectedPreviewVersion = ref<PreviewVersionSelection | null>(null)
const insertingPageAfter = ref<number | null>(null)
const deletingPageNumber = ref<number | null>(null)
const duplicatingPageNumber = ref<number | null>(null)
const reorderingPages = ref(false)
const exportStarting = ref(false)
const exportTask = ref<ProjectExportTask | null>(null)
let exportPollTimer: number | null = null
const session = useWorkspaceAgentSession({
  projectId: toRef(props, 'projectId'),
  router,
  workspaceStore
})
const pageOptimizeSession = usePageOptimizeSession({
  currentPageNumber: toRef(workspaceStore, 'currentPreviewPage'),
  projectId: toRef(props, 'projectId'),
  workspaceStore
})

const modeLabel = computed<string>(() => (workspaceStore.currentMode === 'chat' ? '规划大纲' : '预览与调整'))
const resolvedOutline = computed<Outline | null>(() => workspaceStore.project?.outline ?? session.latestOutlineEvent.value)
const {
  goToNextPage: handlePreviewNextPage,
  goToPreviousPage: handlePreviewPreviousPage,
  previewPageItems,
  previewRouteQuery,
  previewThemeError,
  selectPage: handlePreviewSelectPage
} = usePreviewWorkspace({
  mode: toRef(props, 'mode'),
  pageGenerationStates: session.pageGenerationStates,
  projectId: toRef(props, 'projectId'),
  resolvedOutline,
  route,
  router,
  workspaceStore
})
const projectStatusMeta = computed(() =>
  workspaceStore.project ? PROJECT_STATUS_META[workspaceStore.project.status] : null
)
const projectStatusClass = computed<string>(() => {
  const tone = projectStatusMeta.value?.tone

  switch (tone) {
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
    default:
      return 'border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] text-[color:var(--app-text-secondary)]'
  }
})
const projectSummary = computed<string>(() => {
  const project = workspaceStore.project

  if (!project) {
    return '正在读取项目基础信息'
  }

  return `${resolvedOutline.value?.total_pages ?? project.total_pages} 页 · ${modeLabel.value}`
})
const projectUpdatedAt = computed<string>(() =>
  workspaceStore.project ? formatProjectUpdatedAt(workspaceStore.project.updated_at) : '等待加载'
)
const shortProjectId = computed<string>(() => props.projectId.slice(0, 8))
const deletingFileIds = computed<string[]>(() =>
  workspaceStore.uploadedFiles.filter((file) => workspaceStore.isDeletingFile(file.id)).map((file) => file.id)
)

watch(
  () => [props.projectId, props.mode] as const,
  ([projectId, mode], previousValue) => {
    if (!previousValue || previousValue[0] !== projectId) {
      session.disconnect()
      session.resetRealtimeSessionState({ clearTimeline: true })
      clearExportPolling()
      exportTask.value = null
    }

    void workspaceStore
      .initializeWorkspace({
        mode,
        projectId
      })
      .catch(() => undefined)
  },
  { immediate: true }
)

watch(
  () => props.mode,
  (mode) => {
    workspaceStore.setMode(mode)
  }
)

onBeforeUnmount(() => {
  clearExportPolling()
})

function handleModeSelect(mode: WorkspaceMode): void {
  workspaceStore.setMode(mode)

  void router.push({
    name: mode === 'chat' ? 'project-chat' : 'project-preview',
    params: { id: props.projectId },
    query: mode === 'preview' ? previewRouteQuery.value : undefined
  })
}

function openChatMode(): void {
  handleModeSelect('chat')
}

function openPreviewModeForPage(pageNumber: number): void {
  workspaceStore.setPreviewPage(pageNumber)
  handleModeSelect('preview')
}

function reloadProject(): void {
  void workspaceStore.refreshWorkspace().catch(() => undefined)
}

async function handleFilesSelected(files: File[]): Promise<void> {
  try {
    const result = await workspaceStore.uploadFiles(files)

    if (result.uploadedFiles.length > 0) {
      session.appendFileUploadTimelineItem(result.uploadedFiles)
      message.success(
        result.uploadedFiles.length === 1
          ? `已上传 ${result.uploadedFiles[0].original_name}`
          : `已上传 ${result.uploadedFiles.length} 个文件`
      )
    }

    if (result.errors.length > 0) {
      const errorMessage = result.errors.join('；')
      session.appendStatusTimelineItem('上传提醒', errorMessage, 'warning')
      message.error(errorMessage)
    }
  } catch (error: unknown) {
    const uiError = notifyApiError(error, {
      fallback: '文件上传失败，请稍后重试。'
    })
    session.appendStatusTimelineItem('上传失败', uiError, 'error')
  }
}

async function handleDeleteFile(file: UploadedFile): Promise<void> {
  try {
    await workspaceStore.deleteUploadedFile(file.id)
    message.success(`已删除 ${file.original_name}`)
  } catch (error: unknown) {
    const uiError = notifyApiError(error, {
      fallback: '删除文件失败，请稍后重试。'
    })
    session.appendStatusTimelineItem('删除失败', uiError, 'error')
  }
}

async function handleChatSubmit(messageContent: string): Promise<void> {
  const normalizedMessage = messageContent.trim()
  if (!normalizedMessage || session.isAgentRequestInFlight.value) {
    return
  }

  chatDraft.value = ''
  const uiError = await session.handleChatSubmit(normalizedMessage)
  if (uiError) {
    notifyApiError(uiError)
  }
}

async function handleConfirmOutline(): Promise<void> {
  const uiError = await session.handleConfirmOutline(resolvedOutline.value)
  if (uiError) {
    notifyApiError(uiError)
  }
}

function handleAdjustOutline(): void {
  chatPanelRef.value?.focusComposer()
}

function handleOutlineFocus(pageNumber: number): void {
  session.setActiveOutlinePage(pageNumber)
}

async function handleThemeApply(theme: ThemeConfig): Promise<void> {
  try {
    await workspaceStore.applyTheme(theme)
    message.success(`已应用 ${theme.label}`)
  } catch (error: unknown) {
    notifyApiError(error, {
      fallback: '主题切换失败，请确认 Python 后端与 preview server 已正常运行。'
    })
  }
}

function handleThemeRetry(): void {
  void Promise.all([
    workspaceStore.loadThemePresets({ force: true }),
    workspaceStore.syncPreviewTheme({ force: true })
  ]).catch(() => undefined)
}

async function handleOptimizeSubmit(messageContent: string): Promise<void> {
  const normalizedMessage = messageContent.trim()
  if (!normalizedMessage || pageOptimizeSession.isBusy.value) {
    return
  }

  optimizeDraft.value = ''
  const uiError = await pageOptimizeSession.sendPageMessage(normalizedMessage)
  if (uiError) {
    notifyApiError(uiError)
    return
  }

  previewPanelRef.value?.focusOptimizeComposer()
}

async function handleOptimizeQuickPrompt(payload: { actionLabel: string; prompt: string }): Promise<void> {
  const uiError = await pageOptimizeSession.sendQuickActionPrompt(payload.prompt, {
    actionLabel: payload.actionLabel
  })

  if (uiError) {
    notifyApiError(uiError)
    return
  }

  optimizeDraft.value = ''
}

async function handleOptimizeRegeneratePage(): Promise<void> {
  const uiError = await pageOptimizeSession.regenerateCurrentPage()

  if (uiError) {
    notifyApiError(uiError)
    return
  }

  message.success(`已开始重新生成第 ${workspaceStore.currentPreviewPage} 页`)
}

async function handleOptimizeConfirmPage(): Promise<void> {
  const uiError = await pageOptimizeSession.confirmCurrentPage()

  if (uiError) {
    notifyApiError(uiError)
    return
  }

  message.success(`第 ${workspaceStore.currentPreviewPage} 页已确认`)
}

async function handleStartPdfExport(): Promise<void> {
  if (exportStarting.value) {
    return
  }

  exportStarting.value = true
  clearExportPolling()

  try {
    exportTask.value = await projectExportService.startPdfExport(props.projectId)
    message.success('已开始导出 PDF')
    scheduleExportPolling(0)
  } catch (error: unknown) {
    notifyApiError(error, {
      fallback: '启动 PDF 导出失败，请确认当前项目已全部生成。'
    })
  } finally {
    exportStarting.value = false
  }
}

function handleEnterFullscreen(): void {
  if (workspaceStore.currentMode !== 'preview') {
    return
  }

  workspaceStore.setPreviewFullscreenActive(true)
}

function handleExitFullscreen(): void {
  workspaceStore.setPreviewFullscreenActive(false)
}

function handleFullscreenError(errorMessage: string): void {
  workspaceStore.setPreviewFullscreenActive(false)
  notifyApiError(errorMessage)
}

async function handleDownloadExportArtifact(): Promise<void> {
  if (!exportTask.value) {
    return
  }

  try {
    await projectExportService.downloadArtifact(props.projectId, exportTask.value)
  } catch (error: unknown) {
    notifyApiError(error, {
      fallback: '导出文件下载失败，请稍后重试。'
    })
  }
}

async function refreshExportTask(): Promise<void> {
  if (!exportTask.value) {
    return
  }

  const previousStatus = exportTask.value.status

  try {
    const latestTask = await projectExportService.getTask(props.projectId, exportTask.value.id)
    exportTask.value = latestTask

    if (previousStatus !== latestTask.status) {
      if (latestTask.status === 'completed') {
        message.success('PDF 导出完成')
      } else if (latestTask.status === 'failed') {
        notifyApiError(latestTask.error || 'PDF 导出失败')
      }
    }
  } catch (error: unknown) {
    clearExportPolling()
    notifyApiError(error, {
      fallback: '导出状态刷新失败，请稍后手动重试。'
    })
    return
  }

  if (exportTask.value && ['pending', 'running'].includes(exportTask.value.status)) {
    scheduleExportPolling()
  } else {
    clearExportPolling()
  }
}

async function handleShowPageVersionHistory(pageNumber: number): Promise<void> {
  versionDrawerShow.value = true
  versionDrawerPageNumber.value = pageNumber
  versionDrawerLoading.value = true

  try {
    versionDrawerVersions.value = await pageService.listVersions(props.projectId, pageNumber)
  } catch (error: unknown) {
    notifyApiError(error, {
      fallback: '历史版本加载失败，请确认 Python 后端已经启动。'
    })
    versionDrawerShow.value = false
  } finally {
    versionDrawerLoading.value = false
  }
}

async function handlePreviewPageVersion(version: PageVersion): Promise<void> {
  const pageNumber = versionDrawerPageNumber.value
  if (!pageNumber) {
    return
  }

  try {
    const previewVersion = await pageService.previewVersion(props.projectId, pageNumber, version.version)
    selectedPreviewVersion.value = {
      changeDescription: previewVersion.change_description,
      createdAt: previewVersion.created_at,
      pageNumber,
      previewToken: Date.now(),
      sourceVersion: previewVersion.version,
      vueCode: previewVersion.vue_code
    }
    if (workspaceStore.currentPreviewPage !== pageNumber) {
      workspaceStore.setPreviewPage(pageNumber)
    }
  } catch (error: unknown) {
    notifyApiError(error, {
      fallback: '历史版本预览失败，请确认 Python 后端已经启动。'
    })
  }
}

async function handleRollbackPageVersion(version: PageVersion): Promise<void> {
  const pageNumber = versionDrawerPageNumber.value
  if (!pageNumber || versionDrawerRollingBack.value) {
    return
  }

  versionDrawerRollingBack.value = true
  versionDrawerRollingBackVersion.value = version.version

  try {
    await pageService.rollback(props.projectId, pageNumber, version.version)
    versionDrawerVersions.value = await pageService.listVersions(props.projectId, pageNumber)
    selectedPreviewVersion.value = null
    await workspaceStore.loadProject(props.projectId, { force: true })
    if (workspaceStore.currentPreviewPage !== pageNumber) {
      workspaceStore.setPreviewPage(pageNumber)
    }
    message.success(`第 ${pageNumber} 页已回滚到 v${version.version}`)
  } catch (error: unknown) {
    notifyApiError(error, {
      fallback: '页面回滚失败，请确认 Python 后端已经启动。'
    })
  } finally {
    versionDrawerRollingBack.value = false
    versionDrawerRollingBackVersion.value = null
  }
}

function handleDeletePage(pageNumber: number): void {
  if (deletingPageNumber.value !== null || reorderingPages.value) {
    return
  }

  dialog.warning({
    title: `删除第 ${pageNumber} 页`,
    content: '删除后该页文件、数据库记录、页面对话会移除，后续页码会自动前移。该操作不可撤销。',
    negativeText: '取消',
    positiveText: '确认删除',
    onPositiveClick: async () => {
      deletingPageNumber.value = pageNumber

      try {
        await pageService.remove(props.projectId, pageNumber)
        selectedPreviewVersion.value = null
        versionDrawerShow.value = false
        await refreshProjectAfterPageMutation(pageNumber)
        message.success(`已删除第 ${pageNumber} 页`)
      } catch (error: unknown) {
        notifyApiError(error, {
          fallback: '删除页面失败，请确认 Python 后端已经启动。'
        })
      } finally {
        deletingPageNumber.value = null
      }
    }
  })
}

function handleInsertPageAfter(pageNumber: number): void {
  if (insertingPageAfter.value !== null || reorderingPages.value) {
    return
  }

  const insertDescription = ref('')

  dialog.create({
    title: `在第 ${pageNumber} 页后插入新页`,
    content: () => h('div', { class: 'space-y-3' }, [
      h(
        'div',
        { class: 'text-sm leading-6 text-[color:var(--app-text-secondary)]' },
        '描述新页要表达的内容，后端会复用当前 page generator 生成完整 Vue SFC。'
      ),
      h(NInput, {
        autofocus: true,
        maxlength: 2000,
        placeholder: '例如：增加一页展示 Q2 增长机会，包含三个关键抓手和下一步行动。',
        showCount: true,
        type: 'textarea',
        value: insertDescription.value,
        'onUpdate:value': (value: string) => {
          insertDescription.value = value
        }
      })
    ]),
    negativeText: '取消',
    positiveText: '生成并插入',
    onPositiveClick: async () => {
      const normalizedDescription = insertDescription.value.trim()
      if (!normalizedDescription) {
        message.warning('请先描述新页内容')
        return false
      }

      insertingPageAfter.value = pageNumber

      try {
        const insertedPage = await pageService.insertAfter(props.projectId, pageNumber, {
          description: normalizedDescription
        })
        selectedPreviewVersion.value = null
        await refreshProjectAfterPageMutation(insertedPage.page_number)
        message.success(`已插入第 ${insertedPage.page_number} 页`)
      } catch (error: unknown) {
        notifyApiError(error, {
          fallback: '插入新页失败，请确认 API Key、Python 后端与 preview server 已正常运行。'
        })
      } finally {
        insertingPageAfter.value = null
      }
    }
  })
}

async function handleDuplicatePage(pageNumber: number): Promise<void> {
  if (duplicatingPageNumber.value !== null || reorderingPages.value) {
    return
  }

  duplicatingPageNumber.value = pageNumber

  try {
    const duplicatedPage = await pageService.duplicate(props.projectId, pageNumber)
    selectedPreviewVersion.value = null
    await refreshProjectAfterPageMutation(duplicatedPage.page_number)
    message.success(`已复制到第 ${duplicatedPage.page_number} 页`)
  } catch (error: unknown) {
    notifyApiError(error, {
      fallback: '复制页面失败，请确认该页已生成且 Python 后端已经启动。'
    })
  } finally {
    duplicatingPageNumber.value = null
  }
}

async function handleReorderPages(pageNumbers: number[]): Promise<void> {
  if (reorderingPages.value) {
    return
  }

  const normalizedPageNumbers = pageNumbers.filter((pageNumber) => Number.isFinite(pageNumber) && pageNumber > 0)
  if (normalizedPageNumbers.length !== pageNumbers.length) {
    notifyApiError('页面排序参数无效。')
    return
  }

  reorderingPages.value = true

  try {
    const currentLogicalPage = workspaceStore.currentPreviewPage
    const nextPreviewPage = normalizedPageNumbers.indexOf(currentLogicalPage) + 1
    await pageService.reorder(props.projectId, {
      page_numbers: normalizedPageNumbers
    })
    selectedPreviewVersion.value = null
    await refreshProjectAfterPageMutation(nextPreviewPage > 0 ? nextPreviewPage : workspaceStore.currentPreviewPage)
    message.success('页面顺序已更新')
  } catch (error: unknown) {
    notifyApiError(error, {
      fallback: '页面排序失败，请确认 Python 后端已经启动。'
    })
  } finally {
    reorderingPages.value = false
  }
}

async function refreshProjectAfterPageMutation(preferredPageNumber: number): Promise<void> {
  selectedPreviewVersion.value = null
  versionDrawerShow.value = false
  versionDrawerPageNumber.value = null
  versionDrawerVersions.value = []

  const project = await workspaceStore.loadProject(props.projectId, { force: true })
  const totalPages = Math.max(1, project?.total_pages ?? getCurrentTotalPageCount())
  const normalizedPageNumber = Math.min(Math.max(1, Math.floor(preferredPageNumber || 1)), totalPages)

  workspaceStore.setPreviewPage(normalizedPageNumber)
  workspaceStore.resetPageChatMessageState()
  await Promise.all([
    workspaceStore.refreshChatMessages().catch(() => undefined),
    workspaceStore.loadPageChatMessages(props.projectId, normalizedPageNumber, { force: true }).catch(() => undefined)
  ])
  if (workspaceStore.currentMode === 'preview') {
    await router.replace({
      name: 'project-preview',
      params: { id: props.projectId },
      query: {
        ...route.query,
        page: String(normalizedPageNumber)
      }
    }).catch(() => undefined)
  }
}

function getCurrentTotalPageCount(): number {
  return Math.max(1, resolvedOutline.value?.total_pages ?? workspaceStore.project?.total_pages ?? previewPageItems.value.length)
}

function scheduleExportPolling(delayMs = 1000): void {
  clearExportPolling()
  exportPollTimer = window.setTimeout(() => {
    void refreshExportTask()
  }, delayMs)
}

function clearExportPolling(): void {
  if (exportPollTimer === null) {
    return
  }

  window.clearTimeout(exportPollTimer)
  exportPollTimer = null
}

watch(versionDrawerShow, (show) => {
  if (show) {
    return
  }

  if (!selectedPreviewVersion.value) {
    return
  }

  selectedPreviewVersion.value = null
})

function resolveUiError(error: unknown, fallback = '文件操作失败，请确认 Python 后端已经启动。'): string {
  return resolveAppErrorMessage(error, fallback)
}
</script>

<template>
  <section class="flex min-h-[calc(100vh-3rem)] flex-col gap-6 pb-4">
    <header class="grid items-center gap-4 lg:grid-cols-[240px_minmax(0,1fr)_240px]">
      <div class="min-w-0">
        <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">当前项目</p>
        <div v-if="workspaceStore.projectLoading && !workspaceStore.project" class="space-y-2">
          <NSkeleton :sharp="false" height="18px" width="70%" />
          <NSkeleton :sharp="false" height="14px" width="48%" />
        </div>
        <template v-else>
          <div class="flex flex-wrap items-center gap-3">
            <div class="truncate text-lg font-semibold">{{ workspaceStore.projectName }}</div>
            <NTag
              v-if="projectStatusMeta"
              :bordered="false"
              round
              size="small"
              :class="projectStatusClass"
            >
              {{ projectStatusMeta.label }}
            </NTag>
          </div>
          <div class="mt-2 flex flex-wrap gap-3 text-sm text-[color:var(--app-text-secondary)]">
            <span>{{ projectSummary }}</span>
            <span>项目 ID {{ shortProjectId }}</span>
            <span>最近更新 {{ projectUpdatedAt }}</span>
          </div>
        </template>
      </div>

      <ModeSwitchPill :active-mode="workspaceStore.currentMode" @select="handleModeSelect" />

      <div class="flex justify-end gap-3">
        <NButton secondary strong :loading="workspaceStore.projectLoading" @click="reloadProject">刷新项目</NButton>
        <NButton tertiary strong disabled>
          {{ workspaceStore.currentMode === 'chat'
            ? resolvedOutline
              ? `${resolvedOutline.total_pages} 页大纲`
              : '等待大纲'
            : `当前第 ${workspaceStore.currentPreviewPage} 页` }}
        </NButton>
      </div>
    </header>

    <GlassPanel
      v-if="workspaceStore.projectError"
      class="flex flex-col gap-3 border-[rgba(183,91,53,0.16)] bg-[rgba(255,248,237,0.78)] p-4 md:flex-row md:items-center md:justify-between"
    >
      <div>
        <div class="mono-meta mb-2 text-[10px] text-[color:#9f4b2a]">项目上下文加载失败</div>
        <div class="text-sm text-[color:var(--app-text-secondary)]">{{ workspaceStore.projectError }}</div>
      </div>
      <NButton secondary strong @click="reloadProject">重试</NButton>
    </GlassPanel>

    <div
      v-if="workspaceStore.currentMode === 'chat'"
      class="grid min-h-[780px] gap-6 xl:grid-cols-[minmax(360px,0.92fr)_minmax(460px,1.08fr)]"
    >
      <ErrorBoundary title="对话面板渲染失败" :reset-key="`${props.projectId}:${workspaceStore.currentMode}:chat-panel`">
        <ChatPanel
          ref="chatPanelRef"
          :accept="UPLOAD_FILE_ACCEPT_ATTRIBUTE"
          :chat-error="workspaceStore.chatMessagesError"
          :chat-loaded="workspaceStore.chatMessagesLoaded"
          :chat-loading="workspaceStore.chatMessagesLoading"
          :connection-state="session.agentConnectionState.value"
          :debug-events="session.agentEventLog.value"
          :deleting-file-ids="deletingFileIds"
          :disabled="workspaceStore.projectLoading || session.isConfirmingOutline.value"
          :draft="chatDraft"
          :files="workspaceStore.uploadedFiles"
          :files-error="workspaceStore.filesError"
          :files-loading="workspaceStore.filesLoading"
          :project-name="workspaceStore.projectName"
          :submitting="session.isChatSubmitting.value"
          :timeline-items="session.timelineItems.value"
          :uploading="workspaceStore.filesUploading"
          @delete-file="handleDeleteFile"
          @focus-outline="handleOutlineFocus"
          @message-reveal-complete="session.handleMessageRevealComplete"
          @select-files="handleFilesSelected"
          @submit="handleChatSubmit"
          @update:draft="chatDraft = $event"
        />
      </ErrorBoundary>

      <ErrorBoundary title="大纲面板渲染失败" :reset-key="`${props.projectId}:${workspaceStore.currentMode}:outline-panel`">
        <OutlinePanel
          :active-page-number="session.activeOutlinePageNumber.value"
          :confirming="session.isConfirmingOutline.value"
          :disabled="workspaceStore.projectLoading || workspaceStore.filesUploading || session.isAgentRequestInFlight.value"
          :outline="resolvedOutline"
          preview-link-enabled
          :project-name="workspaceStore.projectName"
          @adjust="handleAdjustOutline"
          @confirm="handleConfirmOutline"
          @preview="openPreviewModeForPage"
          @select-page="handleOutlineFocus"
        />
      </ErrorBoundary>
    </div>

    <ErrorBoundary v-else title="预览工作区渲染失败" :reset-key="`${props.projectId}:${workspaceStore.currentMode}:preview-panel`">
      <PreviewPanel
        ref="previewPanelRef"
        :active-theme-id="workspaceStore.activePreviewThemeId"
        :active-optimizing-page-number="pageOptimizeSession.activeOptimizingPageNumber.value"
        :applying-theme-id="workspaceStore.themeApplyingId"
        :current-page-number="workspaceStore.currentPreviewPage"
        :export-starting="exportStarting"
        :export-task="exportTask"
        :fullscreen-active="workspaceStore.previewFullscreenActive"
        :generation-progress="session.generationProgress.value"
        :items="previewPageItems"
        :optimize-chat-connection-state="pageOptimizeSession.agentConnectionState.value"
        :optimize-confirming-page="pageOptimizeSession.confirmingPage.value"
        :optimize-current-action-label="pageOptimizeSession.currentActionLabel.value"
        :optimize-chat-debug-events="pageOptimizeSession.agentEventLog.value"
        :optimize-chat-draft="optimizeDraft"
        :optimize-chat-error="pageOptimizeSession.pageMessagesError.value"
        :optimize-chat-loaded="pageOptimizeSession.pageMessagesLoaded.value"
        :optimize-chat-loading="pageOptimizeSession.pageMessagesLoading.value"
        :optimize-preview-refresh-request="pageOptimizeSession.latestPreviewRefreshRequest.value"
        :optimize-chat-submitting="pageOptimizeSession.isCurrentPageOptimizing.value"
        :optimize-chat-timeline-items="pageOptimizeSession.timelineItems.value"
        :project-chat-expanded="workspaceStore.previewProjectChatExpanded"
        :project-chat-loaded="workspaceStore.chatMessagesLoaded"
        :project-chat-loading="workspaceStore.chatMessagesLoading"
        :project-chat-timeline-items="session.timelineItems.value"
        :version-drawer-loading="versionDrawerLoading"
        :version-drawer-page-number="versionDrawerPageNumber"
        :version-drawer-rolling-back="versionDrawerRollingBack"
        :version-drawer-rolling-back-version="versionDrawerRollingBackVersion"
        :version-drawer-selected-version="selectedPreviewVersion"
        :version-drawer-show="versionDrawerShow"
        :version-drawer-versions="versionDrawerVersions"
        :theme-error="previewThemeError"
        :theme-loading="workspaceStore.themePresetsLoading"
        :theme-syncing="workspaceStore.previewThemeSyncing"
        :themes="workspaceStore.themePresets"
        @apply-theme="handleThemeApply"
        @delete-page="handleDeletePage"
        @duplicate-page="handleDuplicatePage"
        @insert-page-after="handleInsertPageAfter"
        @next-page="handlePreviewNextPage"
        @open-chat-mode="openChatMode"
        @download-export-artifact="handleDownloadExportArtifact"
        @enter-fullscreen="handleEnterFullscreen"
        @exit-fullscreen="handleExitFullscreen"
        @fullscreen-error="handleFullscreenError"
        @optimize-confirm-page="handleOptimizeConfirmPage"
        @optimize-message-reveal-complete="pageOptimizeSession.handleMessageRevealComplete"
        @project-message-reveal-complete="session.handleMessageRevealComplete"
        @optimize-quick-prompt="handleOptimizeQuickPrompt"
        @optimize-regenerate-page="handleOptimizeRegeneratePage"
        @optimize-submit="handleOptimizeSubmit"
        @preview-page-version="handlePreviewPageVersion"
        @previous-page="handlePreviewPreviousPage"
        @reorder-pages="handleReorderPages"
        @rollback-page-version="handleRollbackPageVersion"
        @retry-theme="handleThemeRetry"
        @select-page="handlePreviewSelectPage"
        @show-page-version-history="handleShowPageVersionHistory"
        @start-export-pdf="handleStartPdfExport"
        @update:optimize-chat-draft="optimizeDraft = $event"
        @update:project-chat-expanded="workspaceStore.setPreviewProjectChatExpanded($event)"
        @update:version-drawer-show="versionDrawerShow = $event"
      />
    </ErrorBoundary>
  </section>
</template>
