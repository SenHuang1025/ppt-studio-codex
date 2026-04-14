import { computed, onBeforeUnmount, ref, toRef, type Ref } from 'vue'
import type { Router } from 'vue-router'
import { useChatTimeline } from '@/composables/useChatTimeline'
import { AgentSSEClient } from '@/services/sseService'
import type { useWorkspaceStore } from '@/stores/workspaceStore'
import type {
  AgentConnectionState,
  AgentEventLogItem,
  AgentSSEEventName,
  AgentStreamEvent,
  AssistantChatTimelineItem,
  AssistantMessageEventPayload,
  ChatTimelineFileAttachment,
  ChatTimelineItem,
  DeliberationChatTimelineItem,
  DeliberationRoundEventPayload,
  DeliberationStartedEventPayload,
  DeliberationSummaryEventPayload,
  ErrorEventPayload,
  FileAnalysisChatTimelineItem,
  FileParsedEventPayload,
  OutlineChatTimelineItem,
  OutlineEventPayload,
  PageCompleteEventPayload,
  PageGeneratingEventPayload,
  StatusChatTimelineItem,
  ThinkingChatTimelineItem,
  ThinkingEventPayload,
  UserChatTimelineItem
} from '@/types/chat'
import type { UploadedFile } from '@/types/file'
import type { RealtimePageGenerationState } from '@/types/preview'
import type { Outline, PageStatus } from '@/types/project'

type WorkspaceStore = ReturnType<typeof useWorkspaceStore>

interface UseWorkspaceAgentSessionOptions {
  projectId: Ref<string>
  router: Router
  workspaceStore: WorkspaceStore
}

export function useWorkspaceAgentSession(options: UseWorkspaceAgentSessionOptions) {
  const agentClient = new AgentSSEClient()
  const agentConnectionState = ref<AgentConnectionState>('idle')
  const latestThinking = ref<string>('')
  const latestAssistantMessage = ref<string>('')
  const latestError = ref<string | null>(null)
  const latestOutlineEvent = ref<Outline | null>(null)
  const agentEventLog = ref<AgentEventLogItem[]>([])
  const sessionTimelineItems = ref<ChatTimelineItem[]>([])
  const activeOutlinePageNumber = ref<number | null>(null)
  const pageGenerationStates = ref<Record<number, RealtimePageGenerationState>>({})
  const currentStreamPurpose = ref<'chat' | 'confirm-outline' | null>(null)
  const currentThinkingItemId = ref<string | null>(null)
  const currentAssistantItemId = ref<string | null>(null)
  const currentOutlineItemId = ref<string | null>(null)
  const currentDeliberationItemId = ref<string | null>(null)
  const currentStreamOptimisticItemIds = ref<string[]>([])
  const deferredOptimisticCleanupAssistantId = ref<string | null>(null)
  let agentEventSequence = 0
  let sessionItemSequence = 0
  let deliberationEntrySequence = 0

  const timelineItems = useChatTimeline(toRef(options.workspaceStore, 'chatMessages'), sessionTimelineItems)
  const isAgentRequestInFlight = computed<boolean>(
    () => agentConnectionState.value === 'connecting' || agentConnectionState.value === 'streaming'
  )
  const isChatSubmitting = computed<boolean>(() =>
    currentStreamPurpose.value === 'chat' && isAgentRequestInFlight.value
  )
  const isConfirmingOutline = computed<boolean>(() =>
    currentStreamPurpose.value === 'confirm-outline' && isAgentRequestInFlight.value
  )
  const currentGeneratingPageNumber = computed<number | null>(() => {
    const generatingEntries = Object.values(pageGenerationStates.value)
      .filter((entry) => entry.status === 'generating')
      .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))

    return generatingEntries[0]?.pageNumber ?? null
  })

  agentClient.onThinking(handleThinkingEvent)
  agentClient.onFileParsed(handleFileParsedEvent)
  agentClient.onOutline(handleOutlineEvent)
  agentClient.onDeliberationStarted(handleDeliberationStarted)
  agentClient.onDeliberationRound(handleDeliberationRound)
  agentClient.onDeliberationSummary(handleDeliberationSummary)
  agentClient.onPageGenerating(handlePageGeneratingEvent)
  agentClient.onPageComplete(handlePageCompleteEvent)
  agentClient.onAssistantMessage(handleAssistantMessageEvent)
  agentClient.onError(handleAgentErrorEvent)
  agentClient.onDone(handleAgentDone)
  agentClient.onEvent((event) => {
    pushAgentEventLog(event)
  })

  onBeforeUnmount(() => {
    agentClient.disconnect()
  })

  async function handleChatSubmit(messageContent: string): Promise<string | null> {
    const normalizedMessage = messageContent.trim()
    if (!normalizedMessage || isAgentRequestInFlight.value) {
      return null
    }

    prepareNewStream('chat', 'orchestrator', '正在查看你的需求、历史消息和已上传资料...')
    const userItem = createUserMessageTimelineItem(normalizedMessage)
    appendSessionItem(userItem)
    registerOptimisticItem(userItem.id)

    try {
      await agentClient.connect(options.projectId.value, normalizedMessage)
      return null
    } catch (error: unknown) {
      return handleStreamConnectionFailure(resolveUiError(error))
    }
  }

  async function handleConfirmOutline(outline: Outline | null): Promise<string | null> {
    if (!outline || isAgentRequestInFlight.value) {
      return null
    }

    prepareNewStream('confirm-outline', 'planner', '正在确认当前大纲，并准备切换到预览模式...')

    try {
      await agentClient.confirmOutline(options.projectId.value, outline)
      return null
    } catch (error: unknown) {
      return handleStreamConnectionFailure(resolveUiError(error))
    }
  }

  function appendFileUploadTimelineItem(files: UploadedFile[]): void {
    const item: Extract<ChatTimelineItem, { type: 'file_upload' }> = {
      ...createSessionMeta('file-upload'),
      dedupeKey: null,
      files: files.map(mapUploadedFileToAttachment),
      type: 'file_upload'
    }
    appendSessionItem(item)
  }

  function appendStatusTimelineItem(
    label: string,
    content: string,
    tone: StatusChatTimelineItem['tone']
  ): void {
    appendSessionItem(createStatusTimelineItem(label, content, tone))
  }

  function handleMessageRevealComplete(itemId: string): void {
    if (itemId !== deferredOptimisticCleanupAssistantId.value) {
      return
    }

    clearCurrentStreamOptimisticItems()
    deferredOptimisticCleanupAssistantId.value = null
  }

  function resetRealtimeSessionState(options?: { clearTimeline?: boolean }): void {
    latestThinking.value = ''
    latestAssistantMessage.value = ''
    latestError.value = null
    latestOutlineEvent.value = null
    agentEventLog.value = []
    agentConnectionState.value = 'idle'
    activeOutlinePageNumber.value = null
    currentStreamPurpose.value = null
    currentThinkingItemId.value = null
    currentAssistantItemId.value = null
    currentOutlineItemId.value = null
    currentDeliberationItemId.value = null
    currentStreamOptimisticItemIds.value = []
    deferredOptimisticCleanupAssistantId.value = null
    pageGenerationStates.value = {}

    if (options?.clearTimeline) {
      sessionTimelineItems.value = []
      sessionItemSequence = 0
      deliberationEntrySequence = 0
    }
  }

  function setActiveOutlinePage(pageNumber: number | null): void {
    activeOutlinePageNumber.value = pageNumber
  }

  function disconnect(): void {
    agentClient.disconnect()
  }

  function handleThinkingEvent(payload: ThinkingEventPayload): void {
    latestThinking.value = payload.content
    agentConnectionState.value = 'streaming'
    upsertThinkingTimelineItem(payload.agent, payload.content)
  }

  function handleFileParsedEvent(payload: FileParsedEventPayload): void {
    agentConnectionState.value = 'streaming'
    appendSessionItem(createFileAnalysisTimelineItem(payload))
    void options.workspaceStore.loadFiles(options.projectId.value, { force: true }).catch(() => undefined)
  }

  function handleAssistantMessageEvent(payload: AssistantMessageEventPayload): void {
    latestAssistantMessage.value = payload.content
    agentConnectionState.value = 'streaming'
    clearThinkingTimelineItem()

    if (currentAssistantItemId.value) {
      updateSessionItem(currentAssistantItemId.value, (item) =>
        item.type === 'assistant_message'
          ? {
              ...item,
              animate: true,
              content: payload.content
            }
          : item
      )
      return
    }

    const assistantItem = createAssistantTimelineItem(payload.content)
    currentAssistantItemId.value = appendSessionItem(assistantItem)
    registerOptimisticItem(currentAssistantItemId.value)
  }

  function handlePageGeneratingEvent(payload: PageGeneratingEventPayload): void {
    agentConnectionState.value = 'streaming'
    upsertPageGenerationState({
      pageNumber: payload.page_number,
      status: 'generating',
      title: payload.title,
      updatedAt: new Date().toISOString()
    })

    if (currentStreamPurpose.value === 'confirm-outline') {
      void ensurePreviewMode()
    }
  }

  function handlePageCompleteEvent(payload: PageCompleteEventPayload): void {
    agentConnectionState.value = 'streaming'
    upsertPageGenerationState({
      pageNumber: payload.page_number,
      status: 'generated',
      title: payload.title,
      updatedAt: new Date().toISOString()
    })

    if (currentStreamPurpose.value === 'confirm-outline') {
      void ensurePreviewMode()

      if (!hasGeneratedPreviewForPage(options.workspaceStore.currentPreviewPage)) {
        options.workspaceStore.setPreviewPage(payload.page_number)
      }
    }

    void options.workspaceStore.loadProject(options.projectId.value, { force: true }).catch(() => undefined)
  }

  function handleOutlineEvent(payload: OutlineEventPayload): void {
    latestOutlineEvent.value = payload.outline
    agentConnectionState.value = 'streaming'
    activeOutlinePageNumber.value = payload.outline.pages[0]?.page_number ?? null

    if (currentOutlineItemId.value) {
      updateSessionItem(currentOutlineItemId.value, (item) =>
        item.type === 'outline_message'
          ? {
              ...item,
              dedupeKey: buildOutlineDedupeKey(payload.outline),
              focusPageNumber: payload.outline.pages[0]?.page_number ?? null,
              outline: payload.outline,
              summary: buildOutlineSummary(payload.outline)
            }
          : item
      )
    } else {
      const outlineItem = createOutlineTimelineItem(payload.outline)
      currentOutlineItemId.value = appendSessionItem(outlineItem)
      registerOptimisticItem(currentOutlineItemId.value)
    }

    void options.workspaceStore.loadProject(options.projectId.value, { force: true }).catch(() => undefined)
  }

  function handleDeliberationStarted(payload: DeliberationStartedEventPayload): void {
    agentConnectionState.value = 'streaming'
    if (currentDeliberationItemId.value) {
      updateSessionItem(currentDeliberationItemId.value, (item) =>
        item.type === 'deliberation_message'
          ? {
              ...item,
              rounds: payload.rounds,
              target: payload.target
            }
          : item
      )
      return
    }

    const item = createDeliberationTimelineItem(payload.target, payload.rounds)
    currentDeliberationItemId.value = appendSessionItem(item)
  }

  function handleDeliberationRound(payload: DeliberationRoundEventPayload): void {
    agentConnectionState.value = 'streaming'
    ensureDeliberationTimelineItem(payload.target)
    if (!currentDeliberationItemId.value) {
      return
    }

    updateSessionItem(currentDeliberationItemId.value, (item) =>
      item.type === 'deliberation_message'
        ? {
            ...item,
            entries: [
              ...item.entries,
              {
                content: payload.content,
                id: `deliberation-entry-${++deliberationEntrySequence}`,
                role: payload.role
              }
            ]
          }
        : item
    )
  }

  function handleDeliberationSummary(payload: DeliberationSummaryEventPayload): void {
    agentConnectionState.value = 'streaming'
    ensureDeliberationTimelineItem(payload.target)
    if (!currentDeliberationItemId.value) {
      return
    }

    updateSessionItem(currentDeliberationItemId.value, (item) =>
      item.type === 'deliberation_message'
        ? {
            ...item,
            summary: payload.summary
          }
        : item
    )
  }

  function handleAgentErrorEvent(payload: ErrorEventPayload): void {
    latestError.value = payload.message
    agentConnectionState.value = 'error'
    clearThinkingTimelineItem()
    appendStatusTimelineItem('会话异常', payload.message, 'error')
  }

  function handleAgentDone(): void {
    clearThinkingTimelineItem()
    agentConnectionState.value = latestError.value ? 'error' : 'completed'
    void finalizeAgentStream()
  }

  async function finalizeAgentStream(): Promise<void> {
    const streamPurpose = currentStreamPurpose.value
    const assistantItemId = currentAssistantItemId.value
    const chatMessagesRefreshed = await options.workspaceStore.refreshChatMessages().then(() => true).catch(() => false)
    await options.workspaceStore.loadProject(options.projectId.value, { force: true }).catch(() => undefined)

    if (chatMessagesRefreshed) {
      if (assistantItemId) {
        deferredOptimisticCleanupAssistantId.value = assistantItemId
      } else {
        clearCurrentStreamOptimisticItems()
      }
    }

    currentStreamPurpose.value = null
    currentThinkingItemId.value = null
    currentAssistantItemId.value = null
    currentOutlineItemId.value = null
    currentDeliberationItemId.value = null

    if (streamPurpose === 'confirm-outline' && !latestError.value) {
      await ensurePreviewMode()
    }
  }

  function handleStreamConnectionFailure(errorMessage: string): string {
    latestError.value = errorMessage
    agentConnectionState.value = 'error'
    clearThinkingTimelineItem()
    appendStatusTimelineItem(
      currentStreamPurpose.value === 'confirm-outline' ? '确认失败' : '会话失败',
      errorMessage,
      'error'
    )
    currentStreamPurpose.value = null
    currentAssistantItemId.value = null
    currentOutlineItemId.value = null
    currentDeliberationItemId.value = null
    currentStreamOptimisticItemIds.value = []
    deferredOptimisticCleanupAssistantId.value = null
    return errorMessage
  }

  function prepareNewStream(purpose: 'chat' | 'confirm-outline', agent: string, content: string): void {
    agentClient.disconnect()
    latestThinking.value = content
    latestAssistantMessage.value = ''
    latestError.value = null
    agentEventLog.value = []
    agentConnectionState.value = 'connecting'
    currentStreamPurpose.value = purpose
    currentThinkingItemId.value = null
    currentAssistantItemId.value = null
    currentOutlineItemId.value = null
    currentDeliberationItemId.value = null
    currentStreamOptimisticItemIds.value = []
    deferredOptimisticCleanupAssistantId.value = null
    if (purpose === 'confirm-outline') {
      pageGenerationStates.value = {}
    }
    upsertThinkingTimelineItem(agent, content)
  }

  function createSessionMeta(prefix: string): Pick<ChatTimelineItem, 'createdAt' | 'id' | 'sortOrder' | 'source'> {
    sessionItemSequence += 1
    return {
      createdAt: new Date().toISOString(),
      id: `session-${prefix}-${sessionItemSequence}`,
      sortOrder: sessionItemSequence,
      source: 'session'
    }
  }

  function appendSessionItem(item: ChatTimelineItem): string {
    sessionTimelineItems.value = [...sessionTimelineItems.value, item]
    return item.id
  }

  function updateSessionItem(itemId: string, updater: (item: ChatTimelineItem) => ChatTimelineItem): void {
    sessionTimelineItems.value = sessionTimelineItems.value.map((item) =>
      item.id === itemId ? updater(item) : item
    )
  }

  function clearCurrentStreamOptimisticItems(): void {
    if (currentStreamOptimisticItemIds.value.length === 0) {
      return
    }

    const optimisticIdSet = new Set(currentStreamOptimisticItemIds.value)
    sessionTimelineItems.value = sessionTimelineItems.value.filter((item) => !optimisticIdSet.has(item.id))
    currentStreamOptimisticItemIds.value = []
  }

  function registerOptimisticItem(itemId: string | null): void {
    if (!itemId || currentStreamOptimisticItemIds.value.includes(itemId)) {
      return
    }

    currentStreamOptimisticItemIds.value = [...currentStreamOptimisticItemIds.value, itemId]
  }

  function upsertThinkingTimelineItem(agent: string, content: string): void {
    if (currentThinkingItemId.value) {
      updateSessionItem(currentThinkingItemId.value, (item) =>
        item.type === 'thinking'
          ? {
              ...item,
              agent,
              content
            }
          : item
      )
      return
    }

    const item: ThinkingChatTimelineItem = {
      ...createSessionMeta('thinking'),
      agent,
      content,
      dedupeKey: null,
      type: 'thinking'
    }
    currentThinkingItemId.value = appendSessionItem(item)
  }

  function clearThinkingTimelineItem(): void {
    if (!currentThinkingItemId.value) {
      return
    }

    const itemId = currentThinkingItemId.value
    sessionTimelineItems.value = sessionTimelineItems.value.filter((item) => item.id !== itemId)
    currentThinkingItemId.value = null
  }

  function ensureDeliberationTimelineItem(target: string): void {
    if (currentDeliberationItemId.value) {
      updateSessionItem(currentDeliberationItemId.value, (item) =>
        item.type === 'deliberation_message'
          ? {
              ...item,
              target
            }
          : item
      )
      return
    }

    const item = createDeliberationTimelineItem(target, null)
    currentDeliberationItemId.value = appendSessionItem(item)
  }

  function createUserMessageTimelineItem(content: string): UserChatTimelineItem {
    return {
      ...createSessionMeta('user'),
      content,
      dedupeKey: buildMessageDedupeKey('user', 'text', content),
      type: 'user_message'
    }
  }

  function createAssistantTimelineItem(content: string): AssistantChatTimelineItem {
    return {
      ...createSessionMeta('assistant'),
      animate: true,
      content,
      contentFormat: 'markdown',
      dedupeKey: buildMessageDedupeKey('assistant', 'text', content),
      type: 'assistant_message'
    }
  }

  function createOutlineTimelineItem(outline: Outline): OutlineChatTimelineItem {
    return {
      ...createSessionMeta('outline'),
      dedupeKey: buildOutlineDedupeKey(outline),
      focusPageNumber: outline.pages[0]?.page_number ?? null,
      outline,
      summary: buildOutlineSummary(outline),
      type: 'outline_message'
    }
  }

  function createDeliberationTimelineItem(target: string, rounds: number | null): DeliberationChatTimelineItem {
    return {
      ...createSessionMeta('deliberation'),
      dedupeKey: null,
      entries: [],
      rounds,
      summary: null,
      target,
      type: 'deliberation_message'
    }
  }

  function createFileAnalysisTimelineItem(payload: FileParsedEventPayload): FileAnalysisChatTimelineItem {
    return {
      ...createSessionMeta('file-analysis'),
      dedupeKey: null,
      fileId: payload.file_id,
      fileName: payload.file_name,
      summary: payload.summary,
      type: 'file_analysis'
    }
  }

  function createStatusTimelineItem(
    label: string,
    content: string,
    tone: StatusChatTimelineItem['tone']
  ): StatusChatTimelineItem {
    return {
      ...createSessionMeta('status'),
      content,
      dedupeKey: null,
      label,
      tone,
      type: 'status_message'
    }
  }

  function mapUploadedFileToAttachment(file: UploadedFile): ChatTimelineFileAttachment {
    return {
      fileSize: file.file_size,
      fileType: file.file_type,
      id: file.id,
      name: file.original_name,
      parseStatus: file.parse_status
    }
  }

  function buildMessageDedupeKey(role: 'assistant' | 'user', messageType: string, content: string): string {
    return [role, messageType, normalizeForKey(content)].join('|')
  }

  function buildOutlineDedupeKey(outline: Outline): string {
    return [
      'assistant',
      'outline',
      outline.total_pages,
      normalizeForKey(outline.title),
      normalizeForKey(outline.pages.map((page) => page.title).join(','))
    ].join('|')
  }

  function buildOutlineSummary(outline: Outline): string {
    return `已生成《${outline.title}》共 ${outline.total_pages} 页大纲。`
  }

  function normalizeForKey(value: string): string {
    return value.replace(/\s+/g, ' ').trim()
  }

  function pushAgentEventLog(event: AgentStreamEvent): void {
    agentEventSequence += 1
    agentEventLog.value = [
      {
        event: event.event,
        id: `agent-event-${agentEventSequence}`,
        received_at: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        summary: summarizeAgentEvent(event)
      },
      ...agentEventLog.value
    ].slice(0, 8)
  }

  function upsertPageGenerationState(nextState: RealtimePageGenerationState): void {
    pageGenerationStates.value = {
      ...pageGenerationStates.value,
      [nextState.pageNumber]: nextState
    }
  }

  function hasGeneratedPreviewForPage(pageNumber: number): boolean {
    const realtimeState = pageGenerationStates.value[pageNumber]
    if (realtimeState?.status === 'generated') {
      return true
    }

    const projectPage = options.workspaceStore.project?.pages.find((page) => page.page_number === pageNumber)
    if (!projectPage) {
      return false
    }

    return isGeneratedProjectPageStatus(projectPage.status)
  }

  async function ensurePreviewMode(): Promise<void> {
    if (options.workspaceStore.currentMode !== 'preview') {
      options.workspaceStore.setMode('preview')
    }

    if (options.router.currentRoute.value.name !== 'project-preview') {
      await options.router.push({
        name: 'project-preview',
        params: { id: options.projectId.value },
        query: {
          page: String(Math.max(1, options.workspaceStore.currentPreviewPage))
        }
      }).catch(() => undefined)
    }
  }

  return {
    activeOutlinePageNumber,
    agentConnectionState,
    agentEventLog,
    appendFileUploadTimelineItem,
    appendStatusTimelineItem,
    disconnect,
    handleChatSubmit,
    handleConfirmOutline,
    handleMessageRevealComplete,
    isAgentRequestInFlight,
    isChatSubmitting,
    isConfirmingOutline,
    currentGeneratingPageNumber,
    latestAssistantMessage,
    latestError,
    latestOutlineEvent,
    latestThinking,
    pageGenerationStates,
    resetRealtimeSessionState,
    setActiveOutlinePage,
    timelineItems
  }
}

function isGeneratedProjectPageStatus(status: PageStatus): boolean {
  return status === 'generated' || status === 'optimizing' || status === 'confirmed'
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
      case 'deliberation_started':
        return `开始 ${event.data.target} 思辨，共 ${event.data.rounds} 轮`
      case 'deliberation_round':
        return `${event.data.role}：${event.data.content}`
      case 'deliberation_summary':
        return event.data.summary
      case 'page_generating':
        return `正在生成第 ${event.data.page_number} 页《${event.data.title}》`
      case 'page_complete':
        return `第 ${event.data.page_number} 页《${event.data.title}》已完成`
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
    || event.event === 'deliberation_started'
    || event.event === 'deliberation_round'
    || event.event === 'deliberation_summary'
    || event.event === 'page_generating'
    || event.event === 'page_complete'
    || event.event === 'assistant_message'
    || event.event === 'error'
    || event.event === 'done'
}

function resolveUiError(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }

  return '文件操作失败，请确认 Python 后端已经启动。'
}
