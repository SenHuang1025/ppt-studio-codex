<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NSkeleton, NTag, useMessage } from 'naive-ui'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import GlassPanel from '@/components/common/GlassPanel.vue'
import ModeSwitchPill from '@/components/common/ModeSwitchPill.vue'
import OutlinePanel from '@/components/outline/OutlinePanel.vue'
import ThemePresetPicker from '@/components/preview/ThemePresetPicker.vue'
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
const uploadedFileCount = computed<number>(() => workspaceStore.uploadedFiles.length)
const deletingFileIds = computed<string[]>(() =>
  workspaceStore.uploadedFiles.filter((file) => workspaceStore.isDeletingFile(file.id)).map((file) => file.id)
)
const previewThemeError = computed<string | null>(() => {
  return workspaceStore.previewThemeSyncError || workspaceStore.themePresetsError
})
const previewPageNumbers = computed<number[]>(() => {
  const totalPages = workspaceStore.project?.total_pages ?? 0
  const loadedPages = workspaceStore.project?.pages.length ?? 0
  const placeholderCount = Math.max(totalPages, loadedPages, 6)
  return Array.from({ length: placeholderCount }, (_, index) => index + 1)
})

watch(
  () => [props.projectId, props.mode] as const,
  ([projectId, mode], previousValue) => {
    if (!previousValue || previousValue[0] !== projectId || previousValue[1] !== mode) {
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
    params: { id: props.projectId }
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

    <div v-else class="grid min-h-[780px] gap-6 xl:grid-cols-[220px_minmax(0,1fr)_360px]">
      <GlassPanel class="flex flex-col gap-4 p-4">
        <div>
          <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">缩略图轨道</p>
          <h2 class="m-0 text-base font-semibold">页面列表</h2>
        </div>

        <button
          v-for="pageNumber in previewPageNumbers"
          :key="pageNumber"
          class="rounded-[var(--radius-xl)] border p-3 text-left transition duration-250 hover:-translate-y-0.5 hover:border-[color:var(--app-border-strong)] hover:shadow-[var(--shadow-hover)]"
          :class="
            workspaceStore.currentPreviewPage === pageNumber
              ? 'border-[color:var(--app-border-strong)] bg-[color:var(--app-primary-soft)] text-[color:var(--primary-300)]'
              : 'border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)]'
          "
          type="button"
          @click="workspaceStore.setPreviewPage(pageNumber)"
        >
          <div class="mb-2 flex items-center justify-between">
            <span class="mono-meta text-[color:var(--app-text-tertiary)]">第 {{ pageNumber }} 页</span>
            <span
              class="h-2 w-2 rounded-full"
              :class="workspaceStore.currentPreviewPage === pageNumber ? 'bg-[color:var(--accent-100)]' : 'bg-[color:var(--primary-200)]'"
            />
          </div>
          <div class="aspect-[16/9] rounded-[var(--radius-lg)] bg-[linear-gradient(180deg,#fff8ed_0%,#ebe2cd_100%)]" />
        </button>
      </GlassPanel>

      <section class="workspace-solid flex flex-col gap-5 rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">稳定画布</p>
            <h2 class="m-0 text-xl font-semibold">页面预览区</h2>
          </div>
          <NTag round :bordered="false" type="info">16:9 预览核心区</NTag>
        </div>

        <div class="grid flex-1 place-items-center rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-preview-stage)] p-8">
          <div class="w-full max-w-[980px] rounded-[var(--radius-xl)] bg-[color:var(--surface-preview-stage)] shadow-[var(--shadow-canvas)]">
            <div class="aspect-[16/9] rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-canvas)] p-8">
              <div class="flex h-full flex-col justify-between rounded-[var(--radius-lg)] border border-dashed border-[color:var(--app-border-subtle)] p-6">
                <div>
                  <div class="mono-meta mb-3 text-[color:var(--app-text-tertiary)]">预览画布</div>
                  <h3 class="m-0 text-2xl font-semibold">第 {{ workspaceStore.currentPreviewPage }} 页预览骨架</h3>
                </div>
                <div class="text-sm leading-6 text-[color:var(--app-text-secondary)]">
                  这里刻意保持稳定实色底板。iframe 预览、页面生成结果、翻页热更新和真实缩略图数据都会留到 Phase 3，再在这个骨架上继续接入。
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <GlassPanel variant="strong" class="flex flex-col gap-5 p-5">
        <ThemePresetPicker
          :active-theme-id="workspaceStore.activePreviewThemeId"
          :applying-theme-id="workspaceStore.themeApplyingId"
          :error="previewThemeError"
          :loading="workspaceStore.themePresetsLoading"
          :syncing="workspaceStore.previewThemeSyncing"
          :themes="workspaceStore.themePresets"
          @apply="handleThemeApply"
          @retry="handleThemeRetry"
        />

        <div>
          <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">单页优化区</p>
          <h2 class="m-0 text-xl font-semibold">当前页操作</h2>
          <div class="mt-2 text-sm text-[color:var(--app-text-secondary)]">当前页：第 {{ workspaceStore.currentPreviewPage }} 页</div>
        </div>

        <div class="grid gap-3">
          <button
            class="rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] px-4 py-3 text-left text-sm transition duration-250 hover:border-[color:var(--app-border-strong)] hover:bg-[color:var(--app-primary-soft)] hover:text-[color:var(--primary-300)]"
            type="button"
          >
            调整版式平衡
          </button>
          <button
            class="rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] px-4 py-3 text-left text-sm transition duration-250 hover:border-[color:var(--app-border-strong)] hover:bg-[color:var(--app-primary-soft)] hover:text-[color:var(--primary-300)]"
            type="button"
          >
            替换配色强调
          </button>
          <button
            class="rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] px-4 py-3 text-left text-sm transition duration-250 hover:border-[color:var(--app-border-strong)] hover:bg-[color:var(--app-primary-soft)] hover:text-[color:var(--primary-300)]"
            type="button"
          >
            收紧叙事节奏
          </button>
        </div>

        <div class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          绑定当前页的优化对话、快捷操作真实行为和版本历史都会放到后续阶段。当前先完成三栏骨架、页码占位和模式切换。
        </div>

        <NInput placeholder="描述你想对当前页做的修改..." size="large" />
      </GlassPanel>
    </div>
  </section>
</template>
