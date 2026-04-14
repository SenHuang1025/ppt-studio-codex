<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NSkeleton, NTag, useMessage } from 'naive-ui'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import GlassPanel from '@/components/common/GlassPanel.vue'
import ModeSwitchPill from '@/components/common/ModeSwitchPill.vue'
import OutlinePanel from '@/components/outline/OutlinePanel.vue'
import PreviewPanel from '@/components/preview/PreviewPanel.vue'
import { usePreviewWorkspace } from '@/composables/usePreviewWorkspace'
import { useWorkspaceAgentSession } from '@/composables/useWorkspaceAgentSession'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import type { WorkspaceMode } from '@/stores/workspaceStore'
import { UPLOAD_FILE_ACCEPT_ATTRIBUTE, type UploadedFile } from '@/types/file'
import type { Outline } from '@/types/project'
import type { ThemeConfig } from '@/types/theme'
import { PROJECT_STATUS_META, formatProjectUpdatedAt } from '@/utils/project'

const props = defineProps<{
  projectId: string
  mode: WorkspaceMode
}>()

const message = useMessage()
const route = useRoute()
const router = useRouter()
const workspaceStore = useWorkspaceStore()
const chatPanelRef = ref<InstanceType<typeof ChatPanel> | null>(null)
const chatDraft = ref<string>('')
const session = useWorkspaceAgentSession({
  projectId: toRef(props, 'projectId'),
  router,
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

function handleModeSelect(mode: WorkspaceMode): void {
  workspaceStore.setMode(mode)

  void router.push({
    name: mode === 'chat' ? 'project-chat' : 'project-preview',
    params: { id: props.projectId },
    query: mode === 'preview' ? previewRouteQuery.value : undefined
  })
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
    const uiError = resolveUiError(error)
    session.appendStatusTimelineItem('上传失败', uiError, 'error')
    message.error(uiError)
  }
}

async function handleDeleteFile(file: UploadedFile): Promise<void> {
  try {
    await workspaceStore.deleteUploadedFile(file.id)
    message.success(`已删除 ${file.original_name}`)
  } catch (error: unknown) {
    const uiError = resolveUiError(error)
    session.appendStatusTimelineItem('删除失败', uiError, 'error')
    message.error(uiError)
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
    message.error(uiError)
  }
}

async function handleConfirmOutline(): Promise<void> {
  const uiError = await session.handleConfirmOutline(resolvedOutline.value)
  if (uiError) {
    message.error(uiError)
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
    message.error(resolveUiError(error, '主题切换失败，请确认 Python 后端与 preview server 已正常运行。'))
  }
}

function handleThemeRetry(): void {
  void Promise.all([
    workspaceStore.loadThemePresets({ force: true }),
    workspaceStore.syncPreviewTheme({ force: true })
  ]).catch(() => undefined)
}

function resolveUiError(error: unknown, fallback = '文件操作失败，请确认 Python 后端已经启动。'): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }

  return fallback
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

      <OutlinePanel
        :active-page-number="session.activeOutlinePageNumber.value"
        :confirming="session.isConfirmingOutline.value"
        :disabled="workspaceStore.projectLoading || workspaceStore.filesUploading || session.isAgentRequestInFlight.value"
        :outline="resolvedOutline"
        :project-name="workspaceStore.projectName"
        @adjust="handleAdjustOutline"
        @confirm="handleConfirmOutline"
        @select-page="handleOutlineFocus"
      />
    </div>

    <PreviewPanel
      v-else
      :active-theme-id="workspaceStore.activePreviewThemeId"
      :applying-theme-id="workspaceStore.themeApplyingId"
      :current-generating-page-number="session.currentGeneratingPageNumber.value"
      :current-page-number="workspaceStore.currentPreviewPage"
      :items="previewPageItems"
      :theme-error="previewThemeError"
      :theme-loading="workspaceStore.themePresetsLoading"
      :theme-syncing="workspaceStore.previewThemeSyncing"
      :themes="workspaceStore.themePresets"
      @apply-theme="handleThemeApply"
      @next-page="handlePreviewNextPage"
      @previous-page="handlePreviewPreviousPage"
      @retry-theme="handleThemeRetry"
      @select-page="handlePreviewSelectPage"
    />
  </section>
</template>
