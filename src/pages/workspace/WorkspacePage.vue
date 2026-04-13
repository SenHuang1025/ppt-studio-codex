<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NSkeleton, NTag, useMessage } from 'naive-ui'
import ChatInput from '@/components/chat/ChatInput.vue'
import FileCard from '@/components/chat/FileCard.vue'
import FileUploadArea from '@/components/chat/FileUploadArea.vue'
import GlassPanel from '@/components/common/GlassPanel.vue'
import ModeSwitchPill from '@/components/common/ModeSwitchPill.vue'
import { AgentSSEClient } from '@/services/sseService'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import type { WorkspaceMode } from '@/stores/workspaceStore'
import type {
  AgentEventLogItem,
  AgentSSEEventName,
  AgentStreamEvent,
  AssistantMessageEventPayload,
  ErrorEventPayload,
  FileParsedEventPayload,
  ThinkingEventPayload
} from '@/types/chat'
import { UPLOAD_FILE_ACCEPT_ATTRIBUTE, type UploadedFile } from '@/types/file'
import { PROJECT_STATUS_META, formatProjectUpdatedAt } from '@/utils/project'

const props = defineProps<{
  projectId: string
  mode: WorkspaceMode
}>()

const message = useMessage()
const router = useRouter()
const workspaceStore = useWorkspaceStore()
const chatDraft = ref<string>('')
const agentClient = new AgentSSEClient()
const agentConnectionState = ref<'idle' | 'connecting' | 'streaming' | 'completed' | 'error'>('idle')
const latestThinking = ref<string>('')
const latestAssistantMessage = ref<string>('')
const latestError = ref<string | null>(null)
const agentEventLog = ref<AgentEventLogItem[]>([])
let agentEventSequence = 0

const modeLabel = computed<string>(() => (workspaceStore.currentMode === 'chat' ? '规划大纲' : '预览与调整'))
const projectStatusMeta = computed(() =>
  workspaceStore.project ? PROJECT_STATUS_META[workspaceStore.project.status] : null
)
const agentStatusMeta = computed<{ label: string; type: 'default' | 'error' | 'info' | 'success' | 'warning' }>(() => {
  switch (agentConnectionState.value) {
    case 'connecting':
      return { label: '建立连接中', type: 'warning' }
    case 'streaming':
      return { label: '流式处理中', type: 'info' }
    case 'completed':
      return { label: '本轮完成', type: 'success' }
    case 'error':
      return { label: '发生错误', type: 'error' }
    case 'idle':
    default:
      return { label: '等待发送', type: 'default' }
  }
})
const isAgentRequestInFlight = computed<boolean>(
  () => agentConnectionState.value === 'connecting' || agentConnectionState.value === 'streaming'
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

  return `${project.total_pages} 页 · ${modeLabel.value}`
})
const projectUpdatedAt = computed<string>(() =>
  workspaceStore.project ? formatProjectUpdatedAt(workspaceStore.project.updated_at) : '等待加载'
)
const shortProjectId = computed<string>(() => props.projectId.slice(0, 8))
const uploadedFileCount = computed<number>(() => workspaceStore.uploadedFiles.length)
const previewPageNumbers = computed<number[]>(() => {
  const totalPages = workspaceStore.project?.total_pages ?? 0
  const loadedPages = workspaceStore.project?.pages.length ?? 0
  const placeholderCount = Math.max(totalPages, loadedPages, 6)
  return Array.from({ length: placeholderCount }, (_, index) => index + 1)
})
const outlineItems = computed<Array<{ title: string; type: string; summary: string }>>(() => {
  const projectName = workspaceStore.project?.name ?? '当前项目'

  return [
    {
      summary: `围绕「${projectName}」建立演示开场、目标与受众语境。`,
      title: '开场定调',
      type: '封面页'
    },
    {
      summary: '这里会在后续阶段承接文件解析结果、证据卡片和结构化洞察。',
      title: '材料整理',
      type: '资料页'
    },
    {
      summary: '这里会在大纲确认后推进到逐页生成，目前仅保留工作区骨架。',
      title: '行动方案',
      type: '策略页'
    }
  ]
})

watch(
  () => [props.projectId, props.mode] as const,
  ([projectId, mode], previousValue) => {
    if (!previousValue || previousValue[0] !== projectId || previousValue[1] !== mode) {
      agentClient.disconnect()
      resetAgentSessionState()
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

agentClient.onThinking(handleThinkingEvent)
agentClient.onFileParsed(handleFileParsedEvent)
agentClient.onAssistantMessage(handleAssistantMessageEvent)
agentClient.onError(handleAgentErrorEvent)
agentClient.onDone(() => {
  agentConnectionState.value = latestError.value ? 'error' : 'completed'
})
agentClient.onEvent((event) => {
  pushAgentEventLog(event)
})

onBeforeUnmount(() => {
  agentClient.disconnect()
})

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
      message.success(
        result.uploadedFiles.length === 1
          ? `已上传 ${result.uploadedFiles[0].original_name}`
          : `已上传 ${result.uploadedFiles.length} 个文件`
      )
    }

    if (result.errors.length > 0) {
      message.error(result.errors.join('；'))
    }
  } catch (error: unknown) {
    message.error(resolveUiError(error))
  }
}

async function handleDeleteFile(file: UploadedFile): Promise<void> {
  try {
    await workspaceStore.deleteUploadedFile(file.id)
    message.success(`已删除 ${file.original_name}`)
  } catch (error: unknown) {
    message.error(resolveUiError(error))
  }
}

async function handleChatSubmit(messageContent: string): Promise<void> {
  const normalizedMessage = messageContent.trim()
  if (!normalizedMessage || isAgentRequestInFlight.value) {
    return
  }

  resetAgentSessionState()
  agentConnectionState.value = 'connecting'
  chatDraft.value = ''

  try {
    await agentClient.connect(props.projectId, normalizedMessage)
  } catch (error: unknown) {
    const uiError = resolveUiError(error)
    latestError.value = uiError
    agentConnectionState.value = 'error'
  }
}

function resolveUiError(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }

  return '文件操作失败，请确认 Python 后端已经启动。'
}

function handleThinkingEvent(payload: ThinkingEventPayload): void {
  latestThinking.value = payload.content
  agentConnectionState.value = 'streaming'
}

function handleFileParsedEvent(_: FileParsedEventPayload): void {
  agentConnectionState.value = 'streaming'
  void workspaceStore.loadFiles(props.projectId, { force: true }).catch(() => undefined)
}

function handleAssistantMessageEvent(payload: AssistantMessageEventPayload): void {
  latestAssistantMessage.value = payload.content
  agentConnectionState.value = 'streaming'
}

function handleAgentErrorEvent(payload: ErrorEventPayload): void {
  latestError.value = payload.message
  agentConnectionState.value = 'error'
}

function resetAgentSessionState(): void {
  latestThinking.value = ''
  latestAssistantMessage.value = ''
  latestError.value = null
  agentEventLog.value = []
  agentConnectionState.value = 'idle'
}

function pushAgentEventLog(event: AgentStreamEvent): void {
  agentEventSequence += 1
  const eventSummary = summarizeAgentEvent(event)

  agentEventLog.value = [
    {
      event: event.event,
      id: `agent-event-${agentEventSequence}`,
      received_at: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
      summary: eventSummary
    },
    ...agentEventLog.value
  ].slice(0, 8)
}

function summarizeAgentEvent(event: AgentStreamEvent): string {
  if (isKnownAgentStreamEvent(event)) {
    switch (event.event) {
      case 'thinking':
        return event.data.content
      case 'file_parsed':
        return `${event.data.file_name}：${event.data.summary}`
      case 'outline':
        return `已收到 ${event.data.outline.total_pages} 页大纲事件`
      case 'assistant_message':
        return event.data.content
      case 'error':
        return event.data.message
      case 'done':
        return '实时会话已结束'
    }
  }

  return `收到 ${event.event} 事件`
}

function isKnownAgentStreamEvent(event: AgentStreamEvent): event is Extract<AgentStreamEvent, { event: AgentSSEEventName }> {
  return event.event === 'thinking'
    || event.event === 'file_parsed'
    || event.event === 'outline'
    || event.event === 'assistant_message'
    || event.event === 'error'
    || event.event === 'done'
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
          {{ workspaceStore.currentMode === 'chat' ? '确认大纲（后续）' : `当前第 ${workspaceStore.currentPreviewPage} 页` }}
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
      <GlassPanel variant="strong" class="flex min-h-0 flex-col gap-5 p-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">AI 协作区</p>
            <h2 class="m-0 text-xl font-semibold">对话流</h2>
          </div>
          <NTag round :bordered="false" type="info">2.3 SSE 验证</NTag>
        </div>

        <div class="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
          <div class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4">
            <p class="mb-2 text-sm text-[color:var(--app-text-tertiary)]">系统</p>
            <div class="text-sm leading-6 text-[color:var(--app-text-secondary)]">
              当前项目基础信息和文件管理 API 已接通真实后端。上传成功后，文件会落盘到项目目录 `uploads/` 下，并在 `uploaded_files` 表中登记为
              `pending`。
            </div>
          </div>

          <div class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4">
            <p class="mb-2 text-sm text-[color:var(--app-text-tertiary)]">智能助手</p>
            <div class="text-sm leading-6">
              我已经进入「{{ workspaceStore.projectName }}」工作区。本次已接通最小 SSE 会话验证：可以发送消息、触发文件解析并接收实时事件；真正的 Agent 路由与大纲规划仍留到 `2.4`。
            </div>
          </div>

          <section class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="mb-2 text-sm text-[color:var(--app-text-tertiary)]">实时会话状态</p>
                <div class="text-base font-semibold">SSE 调试面板</div>
              </div>
              <NTag round :bordered="false" :type="agentStatusMeta.type">{{ agentStatusMeta.label }}</NTag>
            </div>

            <div class="mt-4 grid gap-3 md:grid-cols-2">
              <div class="rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] p-3">
                <div class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">最近 thinking</div>
                <div class="text-sm leading-6 text-[color:var(--app-text-secondary)]">
                  {{ latestThinking || '发送消息后，这里会显示后端返回的 thinking 事件。' }}
                </div>
              </div>

              <div class="rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] p-3">
                <div class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">最近 assistant_message</div>
                <div class="text-sm leading-6 text-[color:var(--app-text-secondary)]">
                  {{ latestAssistantMessage || '当前还没有收到助手消息。' }}
                </div>
              </div>
            </div>

            <div
              v-if="latestError"
              class="mt-3 rounded-[var(--radius-lg)] border border-[rgba(183,91,53,0.16)] bg-[rgba(255,248,237,0.82)] p-3 text-sm leading-6 text-[color:#9f4b2a]"
            >
              {{ latestError }}
            </div>

            <div class="mt-4">
              <div class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">最近事件日志</div>
              <div
                v-if="agentEventLog.length === 0"
                class="rounded-[var(--radius-lg)] border border-dashed border-[color:var(--app-border-subtle)] px-3 py-4 text-sm leading-6 text-[color:var(--app-text-secondary)]"
              >
                还没有实时事件。发送一条消息后，这里会显示 `thinking`、`file_parsed`、`assistant_message`、`done` 等事件。
              </div>

              <div v-else class="space-y-2">
                <div
                  v-for="event in agentEventLog"
                  :key="event.id"
                  class="rounded-[var(--radius-lg)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] px-3 py-3"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="text-sm font-medium">{{ event.event }}</div>
                    <div class="mono-meta text-[color:var(--app-text-tertiary)]">{{ event.received_at }}</div>
                  </div>
                  <div class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">{{ event.summary }}</div>
                </div>
              </div>
            </div>
          </section>

          <FileUploadArea
            :accept="UPLOAD_FILE_ACCEPT_ATTRIBUTE"
            :disabled="workspaceStore.projectLoading"
            :uploading="workspaceStore.filesUploading"
            @select-files="handleFilesSelected"
          />

          <section class="space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <div class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">项目资料</div>
                <div class="text-base font-semibold">已上传文件</div>
              </div>
              <NTag round :bordered="false" type="success">{{ uploadedFileCount }} 个</NTag>
            </div>

            <div
              v-if="workspaceStore.filesError"
              class="rounded-[var(--radius-xl)] border border-[rgba(183,91,53,0.16)] bg-[rgba(255,248,237,0.82)] p-4 text-sm leading-6 text-[color:#9f4b2a]"
            >
              {{ workspaceStore.filesError }}
            </div>

            <div v-if="workspaceStore.filesLoading" class="space-y-3">
              <div
                v-for="index in 2"
                :key="index"
                class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] p-4"
              >
                <NSkeleton :sharp="false" height="18px" width="56%" />
                <NSkeleton class="mt-3" :sharp="false" height="14px" width="36%" />
                <NSkeleton class="mt-4" :sharp="false" height="24px" width="24%" />
              </div>
            </div>

            <div
              v-else-if="uploadedFileCount === 0"
              class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,249,239,0.54)] p-4 text-sm leading-6 text-[color:var(--app-text-secondary)]"
            >
              还没有上传任何资料。可以点击上方区域或使用底部 `📎` 按钮，把表格、文档、PDF、图片或文本资料加入当前项目。
            </div>

            <div v-else class="space-y-3">
              <FileCard
                v-for="file in workspaceStore.uploadedFiles"
                :key="file.id"
                :deleting="workspaceStore.isDeletingFile(file.id)"
                :file="file"
                @delete="handleDeleteFile"
              />
            </div>
          </section>
        </div>

        <div class="mt-auto space-y-3">
          <div class="h-1.5 overflow-hidden rounded-full bg-[color:var(--app-bg-muted)]">
            <div
              class="h-full rounded-full bg-[var(--gradient-brand)] transition-[width] duration-250"
              :class="workspaceStore.filesUploading ? 'w-3/4' : uploadedFileCount > 0 ? 'w-1/2' : 'w-1/3'"
            />
          </div>
          <ChatInput
            v-model="chatDraft"
            :accept="UPLOAD_FILE_ACCEPT_ATTRIBUTE"
            :disabled="workspaceStore.projectLoading"
            :submitting="isAgentRequestInFlight"
            :uploading="workspaceStore.filesUploading"
            @select-files="handleFilesSelected"
            @submit="handleChatSubmit"
          />
        </div>
      </GlassPanel>

      <section class="workspace-solid flex flex-col gap-5 rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">高对比度工作区</p>
            <h2 class="m-0 text-xl font-semibold">大纲编辑器</h2>
          </div>
          <NTag round :bordered="false" type="success">稳定实色工作面</NTag>
        </div>

        <div class="grid gap-4">
          <div
            v-for="(item, index) in outlineItems"
            :key="item.title"
            class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor-2)] p-5"
          >
            <div class="mb-3 flex items-center justify-between">
              <div>
                <div class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">第 {{ index + 1 }} 页</div>
                <div class="text-base font-semibold">{{ item.title }}</div>
              </div>
              <NTag size="small" round :bordered="false">{{ item.type }}</NTag>
            </div>
            <div class="text-sm leading-6 text-[color:var(--app-text-secondary)]">
              {{ item.summary }}
            </div>
          </div>
        </div>
      </section>
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
                  这里刻意保持稳定实色底板。iframe 预览、页面生成结果、翻页热更新和真实缩略图数据都不会在本次 `1.8` 提前实现。
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <GlassPanel variant="strong" class="flex flex-col gap-5 p-5">
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
