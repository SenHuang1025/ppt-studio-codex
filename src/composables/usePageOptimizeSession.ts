import { computed, onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { useChatTimeline } from '@/composables/useChatTimeline'
import { pageService } from '@/services/pageService'
import { AgentSSEClient } from '@/services/sseService'
import type { useWorkspaceStore } from '@/stores/workspaceStore'
import type {
  AgentConnectionState,
  AgentEventLogItem,
  AgentSSEEventName,
  AgentStreamEvent,
  AssistantChatTimelineItem,
  AssistantMessageEventPayload,
  ChatMessage,
  ChatTimelineItem,
  DeliberationChatTimelineItem,
  DeliberationRoundEventPayload,
  DeliberationStartedEventPayload,
  DeliberationSummaryEventPayload,
  ErrorEventPayload,
  PageCompleteEventPayload,
  PageGeneratingEventPayload,
  PageOptimizingEventPayload,
  PageUpdatedEventPayload,
  StatusChatTimelineItem,
  ThinkingChatTimelineItem,
  ThinkingEventPayload,
  UserChatTimelineItem
} from '@/types/chat'
import type { PreviewRefreshRequest } from '@/types/preview'
import { detectGenerationFallbackSummary } from '@/utils/preview'

type WorkspaceStore = ReturnType<typeof useWorkspaceStore>

interface UsePageOptimizeSessionOptions {
  currentPageNumber: Ref<number>
  projectId: Ref<string>
  workspaceStore: WorkspaceStore
}

export function usePageOptimizeSession(options: UsePageOptimizeSessionOptions) {
  const agentClient = new AgentSSEClient()
  const agentConnectionState = ref<AgentConnectionState>('idle')
  const agentEventLog = ref<AgentEventLogItem[]>([])
  const sessionTimelineItems = ref<ChatTimelineItem[]>([])
  const currentStreamPageNumber = ref<number | null>(null)
  const latestError = ref<string | null>(null)
  const latestUpdatedPage = ref<PageUpdatedEventPayload | null>(null)
  const currentThinkingItemId = ref<string | null>(null)
  const currentAssistantItemId = ref<string | null>(null)
  const currentDeliberationItemId = ref<string | null>(null)
  const currentStreamOptimisticItemIds = ref<string[]>([])
  const deferredOptimisticCleanupAssistantId = ref<string | null>(null)
  const activeOptimizingPageNumber = ref<number | null>(null)
  const optimizationUpdatedSignal = ref(0)
  const latestPreviewRefreshRequest = ref<PreviewRefreshRequest | null>(null)
  const currentActionLabel = ref<string | null>(null)
  const confirmingPage = ref(false)
  let agentEventSequence = 0
  let sessionItemSequence = 0
  let deliberationEntrySequence = 0

  const pageMessages = computed<ChatMessage[]>(() =>
    options.workspaceStore.pageChatMessages[options.currentPageNumber.value] ?? []
  )
  const pageMessagesLoading = computed<boolean>(() =>
    options.workspaceStore.pageChatMessagesLoading[options.currentPageNumber.value] ?? false
  )
  const pageMessagesLoaded = computed<boolean>(() =>
    options.workspaceStore.pageChatMessagesLoaded[options.currentPageNumber.value] ?? false
  )
  const pageMessagesError = computed<string | null>(() =>
    options.workspaceStore.pageChatMessagesError[options.currentPageNumber.value] ?? null
  )
  const timelineItems = useChatTimeline(pageMessages, sessionTimelineItems)
  const isAgentRequestInFlight = computed<boolean>(
    () => agentConnectionState.value === 'connecting' || agentConnectionState.value === 'streaming'
  )
  const isBusy = computed<boolean>(() => isAgentRequestInFlight.value || confirmingPage.value)
  const isCurrentPageOptimizing = computed<boolean>(() =>
    isAgentRequestInFlight.value && currentStreamPageNumber.value === options.currentPageNumber.value
  )

  agentClient.onThinking(handleThinkingEvent)
  agentClient.onPageGenerating(handlePageGeneratingEvent)
  agentClient.onPageComplete(handlePageCompleteEvent)
  agentClient.onPageOptimizing(handlePageOptimizingEvent)
  agentClient.onPageUpdated(handlePageUpdatedEvent)
  agentClient.onDeliberationStarted(handleDeliberationStarted)
  agentClient.onDeliberationRound(handleDeliberationRound)
  agentClient.onDeliberationSummary(handleDeliberationSummary)
  agentClient.onAssistantMessage(handleAssistantMessageEvent)
  agentClient.onError(handleAgentErrorEvent)
  agentClient.onDone(handleAgentDone)
  agentClient.onReconnect(handleAgentReconnect)
  agentClient.onEvent(pushAgentEventLog)

  watch(
    [options.projectId, options.currentPageNumber],
    ([projectId, pageNumber], previousValue) => {
      const projectChanged = !previousValue || previousValue[0] !== projectId
      if (projectChanged) {
        agentClient.disconnect()
        agentConnectionState.value = 'idle'
        latestError.value = null
        latestUpdatedPage.value = null
        currentStreamPageNumber.value = null
        activeOptimizingPageNumber.value = null
        currentActionLabel.value = null
      }
      resetVisibleSessionState(pageNumber, { clearEvents: projectChanged })
      void loadPageMessages(projectId, pageNumber, { force: true }).catch(() => undefined)
    },
    { immediate: true }
  )

  onBeforeUnmount(() => {
    agentClient.disconnect()
  })

  async function loadPageMessages(
    projectId: string,
    pageNumber: number,
    loadOptions?: { force?: boolean }
  ): Promise<ChatMessage[]> {
    const normalizedPageNumber = normalizePageNumber(pageNumber)

    if (!projectId.trim() || normalizedPageNumber === null) {
      return []
    }

    try {
      return await options.workspaceStore.loadPageChatMessages(projectId, normalizedPageNumber, loadOptions)
    } catch (error: unknown) {
      throw error
    }
  }

  async function sendPageMessage(messageContent: string): Promise<string | null> {
    const normalizedMessage = messageContent.trim()
    const pageNumber = normalizePageNumber(options.currentPageNumber.value)
    const projectId = options.projectId.value.trim()

    if (!normalizedMessage || pageNumber === null || !projectId || isBusy.value) {
      return null
    }

    prepareNewStream(pageNumber, {
      actionLabel: null
    })
    const userItem = createUserMessageTimelineItem(normalizedMessage)
    appendSessionItem(userItem)
    registerOptimisticItem(userItem.id)
    upsertThinkingTimelineItem('page_optimizer', `正在读取第 ${pageNumber} 页代码和该页最近对话...`)

    try {
      await agentClient.connect(projectId, normalizedMessage, pageNumber)
      return null
    } catch (error: unknown) {
      return handleStreamConnectionFailure(resolveUiError(error))
    }
  }

  async function sendQuickActionPrompt(messageContent: string, actionOptions?: {
    actionLabel?: string | null
  }): Promise<string | null> {
    const normalizedMessage = messageContent.trim()
    const pageNumber = normalizePageNumber(options.currentPageNumber.value)
    const projectId = options.projectId.value.trim()

    if (!normalizedMessage || pageNumber === null || !projectId || isBusy.value) {
      return null
    }

    prepareNewStream(pageNumber, {
      actionLabel: actionOptions?.actionLabel ?? null
    })
    const userItem = createUserMessageTimelineItem(normalizedMessage)
    appendSessionItem(userItem)
    registerOptimisticItem(userItem.id)
    upsertThinkingTimelineItem(
      'page_optimizer',
      actionOptions?.actionLabel?.trim()
        ? `正在执行「${actionOptions.actionLabel.trim()}」，并读取第 ${pageNumber} 页上下文...`
        : `正在读取第 ${pageNumber} 页代码和该页最近对话...`
    )

    try {
      await agentClient.connect(projectId, normalizedMessage, pageNumber)
      return null
    } catch (error: unknown) {
      return handleStreamConnectionFailure(resolveUiError(error))
    }
  }

  async function regenerateCurrentPage(): Promise<string | null> {
    const pageNumber = normalizePageNumber(options.currentPageNumber.value)
    const projectId = options.projectId.value.trim()

    if (pageNumber === null || !projectId || isBusy.value) {
      return null
    }

    prepareNewStream(pageNumber, {
      actionLabel: '重新生成'
    })
    appendSessionItem(
      createStatusTimelineItem(
        '重新生成',
        `正在重新生成第 ${pageNumber} 页，沿用当前大纲与主题配置。`,
        'warning'
      )
    )
    upsertThinkingTimelineItem('page_generator', `正在重新生成第 ${pageNumber} 页，并准备新的 Vue SFC...`)

    try {
      await agentClient.generatePage(projectId, pageNumber)
      return null
    } catch (error: unknown) {
      return handleStreamConnectionFailure(resolveUiError(error, '当前页重新生成失败，请确认 Python 后端已经启动。'))
    }
  }

  async function confirmCurrentPage(): Promise<string | null> {
    const pageNumber = normalizePageNumber(options.currentPageNumber.value)
    const projectId = options.projectId.value.trim()

    if (pageNumber === null || !projectId || isBusy.value) {
      return null
    }

    confirmingPage.value = true
    latestError.value = null

    try {
      await pageService.confirm(projectId, pageNumber)
      await options.workspaceStore.loadProject(projectId, { force: true })
      appendSessionItem(
        createStatusTimelineItem(
          '页面已确认',
          `第 ${pageNumber} 页已标记为 confirmed，缩略图与状态标签会同步更新。`,
          'success'
        )
      )
      optimizationUpdatedSignal.value += 1
      return null
    } catch (error: unknown) {
      const uiError = resolveUiError(error, '确认当前页失败，请确认 Python 后端已经启动。')
      latestError.value = uiError
      appendSessionItem(createStatusTimelineItem('确认失败', uiError, 'error'))
      return uiError
    } finally {
      confirmingPage.value = false
    }
  }

  function handleMessageRevealComplete(itemId: string): void {
    if (itemId !== deferredOptimisticCleanupAssistantId.value) {
      return
    }

    clearCurrentStreamOptimisticItems()
    deferredOptimisticCleanupAssistantId.value = null
  }

  function disconnect(): void {
    agentClient.disconnect()
  }

  function resetVisibleSessionState(nextPageNumber: number, options?: { clearEvents?: boolean }): void {
    if (currentStreamPageNumber.value !== normalizePageNumber(nextPageNumber)) {
      sessionTimelineItems.value = []
    }

    currentThinkingItemId.value = null
    currentAssistantItemId.value = null
    currentDeliberationItemId.value = null
    deferredOptimisticCleanupAssistantId.value = null
    currentStreamOptimisticItemIds.value = []

    if (options?.clearEvents) {
      agentEventLog.value = []
      agentEventSequence = 0
    }
  }

  function handleThinkingEvent(payload: ThinkingEventPayload): void {
    if (!isEventForCurrentStream()) {
      return
    }

    agentConnectionState.value = 'streaming'
    if (!isStreamVisible()) {
      return
    }

    upsertThinkingTimelineItem(payload.agent, payload.content)
  }

  function handlePageGeneratingEvent(payload: PageGeneratingEventPayload): void {
    if (!isEventForCurrentStream(payload.page_number)) {
      return
    }

    agentConnectionState.value = 'streaming'
    activeOptimizingPageNumber.value = payload.page_number
    if (!isStreamVisible()) {
      return
    }

    upsertThinkingTimelineItem('page_generator', `正在重新生成第 ${payload.page_number} 页《${payload.title}》...`)
  }

  function handlePageCompleteEvent(payload: PageCompleteEventPayload): void {
    if (!isEventForCurrentStream(payload.page_number)) {
      return
    }

    agentConnectionState.value = 'streaming'
    activeOptimizingPageNumber.value = null
    latestUpdatedPage.value = {
      change_description: currentActionLabel.value ? `${currentActionLabel.value} 已完成` : '当前页重新生成完成',
      page_number: payload.page_number,
      status: payload.status,
      title: payload.title,
      version: typeof payload.version === 'number' ? payload.version : null,
      vue_code: payload.vue_code
    }
    optimizationUpdatedSignal.value += 1
    latestPreviewRefreshRequest.value = {
      pageNumber: payload.page_number,
      reason: 'page_complete',
      sequence: optimizationUpdatedSignal.value,
      version: typeof payload.version === 'number' ? payload.version : null
    }
    void options.workspaceStore.loadProject(options.projectId.value, { force: true }).catch(() => undefined)

    if (!isStreamVisible()) {
      return
    }

    appendSessionItem(
      createStatusTimelineItem(
        '重新生成完成',
        `第 ${payload.page_number} 页《${payload.title}》已完成重生成，预览即将刷新。`,
        'success'
      )
    )
  }

  function handlePageOptimizingEvent(payload: PageOptimizingEventPayload): void {
    if (!isEventForCurrentStream(payload.page_number)) {
      return
    }

    agentConnectionState.value = 'streaming'
    activeOptimizingPageNumber.value = payload.page_number
    if (!isStreamVisible()) {
      return
    }

    upsertThinkingTimelineItem('page_optimizer', `正在优化第 ${payload.page_number} 页《${payload.title}》...`)
  }

  function handlePageUpdatedEvent(payload: PageUpdatedEventPayload): void {
    if (!isEventForCurrentStream(payload.page_number)) {
      return
    }

    agentConnectionState.value = 'streaming'
    activeOptimizingPageNumber.value = null
    latestUpdatedPage.value = payload
    optimizationUpdatedSignal.value += 1
    latestPreviewRefreshRequest.value = {
      pageNumber: payload.page_number,
      reason: 'page_updated',
      sequence: optimizationUpdatedSignal.value,
      version: payload.version ?? null
    }
    void options.workspaceStore.loadProject(options.projectId.value, { force: true }).catch(() => undefined)
  }

  function handleAssistantMessageEvent(payload: AssistantMessageEventPayload): void {
    if (!isEventForCurrentStream(payload.page_number)) {
      return
    }

    agentConnectionState.value = 'streaming'
    clearThinkingTimelineItem()
    if (!isStreamVisible()) {
      return
    }

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

  function handleDeliberationStarted(payload: DeliberationStartedEventPayload): void {
    if (!isEventForCurrentStream(payload.page_number)) {
      return
    }

    agentConnectionState.value = 'streaming'
    if (!isStreamVisible()) {
      return
    }

    const item = createDeliberationTimelineItem(
      payload.target,
      payload.rounds,
      currentStreamPageNumber.value,
      findCurrentPageTitle()
    )
    currentDeliberationItemId.value = appendSessionItem(item)
  }

  function handleDeliberationRound(payload: DeliberationRoundEventPayload): void {
    if (!isEventForCurrentStream(payload.page_number)) {
      return
    }

    agentConnectionState.value = 'streaming'
    if (!isStreamVisible()) {
      return
    }

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
                id: `page-opt-deliberation-entry-${++deliberationEntrySequence}`,
                role: payload.role
              }
            ],
            pageNumber: currentStreamPageNumber.value,
            pageTitle: findCurrentPageTitle(),
            target: payload.target
          }
        : item
    )
  }

  function handleDeliberationSummary(payload: DeliberationSummaryEventPayload): void {
    if (!isEventForCurrentStream(payload.page_number)) {
      return
    }

    agentConnectionState.value = 'streaming'
    if (!isStreamVisible()) {
      return
    }

    ensureDeliberationTimelineItem(payload.target)

    if (!currentDeliberationItemId.value) {
      return
    }

    updateSessionItem(currentDeliberationItemId.value, (item) =>
      item.type === 'deliberation_message'
        ? {
            ...item,
            pageNumber: currentStreamPageNumber.value,
            pageTitle: findCurrentPageTitle(),
            summary: payload.summary,
            target: payload.target
          }
        : item
    )
  }

  function handleAgentErrorEvent(payload: ErrorEventPayload): void {
    latestError.value = payload.message
    agentConnectionState.value = 'error'
    activeOptimizingPageNumber.value = null
    clearThinkingTimelineItem()
    if (isStreamVisible()) {
      appendSessionItem(createStatusTimelineItem('优化失败', payload.message, 'error'))
    }
  }

  function handleAgentReconnect(attempt: number): void {
    latestError.value = null
    agentConnectionState.value = 'reconnecting'
    activeOptimizingPageNumber.value = currentStreamPageNumber.value
    if (isStreamVisible()) {
      appendSessionItem(
        createStatusTimelineItem(
          '连接恢复中',
          `优化会话连接意外断开，正在尝试第 ${attempt} 次恢复，不会重复提交当前页请求。`,
          'warning'
        )
      )
    }
  }

  function handleAgentDone(): void {
    clearThinkingTimelineItem()
    activeOptimizingPageNumber.value = null
    agentConnectionState.value = latestError.value ? 'error' : 'completed'
    void finalizeAgentStream()
  }

  async function finalizeAgentStream(): Promise<void> {
    const streamPageNumber = currentStreamPageNumber.value
    const assistantItemId = currentAssistantItemId.value
    const shouldRefreshProjectHistory = streamPageNumber !== null

    if (streamPageNumber !== null && streamPageNumber === options.currentPageNumber.value) {
      const messagesRefreshed = await loadPageMessages(options.projectId.value, streamPageNumber, { force: true })
        .then(() => true)
        .catch(() => false)

      if (messagesRefreshed) {
        if (assistantItemId) {
          deferredOptimisticCleanupAssistantId.value = assistantItemId
        } else {
          clearCurrentStreamOptimisticItems()
        }
      }
    }

    if (shouldRefreshProjectHistory) {
      await options.workspaceStore.refreshChatMessages().catch(() => undefined)
      await options.workspaceStore.loadProject(options.projectId.value, { force: true }).catch(() => undefined)
    }

    currentThinkingItemId.value = null
    currentAssistantItemId.value = null
    currentDeliberationItemId.value = null
    currentStreamPageNumber.value = null
    currentActionLabel.value = null
  }

  function handleStreamConnectionFailure(errorMessage: string): string {
    latestError.value = errorMessage
    agentConnectionState.value = 'error'
    activeOptimizingPageNumber.value = null
    clearThinkingTimelineItem()
    if (isStreamVisible()) {
      appendSessionItem(createStatusTimelineItem('会话失败', errorMessage, 'error'))
    }
    currentAssistantItemId.value = null
    currentDeliberationItemId.value = null
    currentStreamOptimisticItemIds.value = []
    currentStreamPageNumber.value = null
    deferredOptimisticCleanupAssistantId.value = null
    currentActionLabel.value = null
    return errorMessage
  }

  function prepareNewStream(pageNumber: number, meta?: { actionLabel?: string | null }): void {
    agentClient.disconnect()
    latestError.value = null
    latestUpdatedPage.value = null
    agentEventLog.value = []
    agentConnectionState.value = 'connecting'
    currentStreamPageNumber.value = pageNumber
    activeOptimizingPageNumber.value = pageNumber
    currentThinkingItemId.value = null
    currentAssistantItemId.value = null
    currentDeliberationItemId.value = null
    currentStreamOptimisticItemIds.value = []
    deferredOptimisticCleanupAssistantId.value = null
    currentActionLabel.value = meta?.actionLabel ?? null
  }

  function createSessionMeta(prefix: string): Pick<ChatTimelineItem, 'createdAt' | 'dedupeKey' | 'id' | 'sortOrder' | 'source'> {
    sessionItemSequence += 1
    return {
      createdAt: new Date().toISOString(),
      dedupeKey: null,
      id: `page-opt-${prefix}-${sessionItemSequence}`,
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
      return
    }

    currentDeliberationItemId.value = appendSessionItem(
      createDeliberationTimelineItem(target, null, currentStreamPageNumber.value, findCurrentPageTitle())
    )
  }

  function createUserMessageTimelineItem(content: string): UserChatTimelineItem {
    return {
      ...createSessionMeta('user'),
      content,
      dedupeKey: buildMessageDedupeKey('user', 'text', content, currentStreamPageNumber.value),
      pageNumber: currentStreamPageNumber.value,
      type: 'user_message'
    }
  }

  function createAssistantTimelineItem(content: string): AssistantChatTimelineItem {
    return {
      ...createSessionMeta('assistant'),
      animate: true,
      content,
      contentFormat: 'markdown',
      dedupeKey: buildMessageDedupeKey('assistant', 'text', content, currentStreamPageNumber.value),
      pageNumber: currentStreamPageNumber.value,
      type: 'assistant_message'
    }
  }

  function createDeliberationTimelineItem(
    target: string,
    rounds: number | null,
    pageNumber: number | null,
    pageTitle: string | null
  ): DeliberationChatTimelineItem {
    return {
      ...createSessionMeta('deliberation'),
      entries: [],
      pageNumber,
      pageTitle,
      rounds,
      summary: null,
      target,
      type: 'deliberation_message'
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
      label,
      tone,
      type: 'status_message'
    }
  }

  function pushAgentEventLog(event: AgentStreamEvent): void {
    if (!isRelevantEventForLog(event)) {
      return
    }

    agentEventSequence += 1
    agentEventLog.value = [
      {
        event: event.event,
        id: `page-opt-agent-event-${agentEventSequence}`,
        received_at: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        summary: summarizeAgentEvent(event)
      },
      ...agentEventLog.value
    ].slice(0, 8)
  }

  function isEventForCurrentStream(pageNumber?: number): boolean {
    if (currentStreamPageNumber.value === null) {
      return false
    }

    if (typeof pageNumber === 'number') {
      return pageNumber === currentStreamPageNumber.value
    }

    return true
  }

  function isStreamVisible(): boolean {
    return currentStreamPageNumber.value === options.currentPageNumber.value
  }

  function isRelevantEventForLog(event: AgentStreamEvent): boolean {
    if (currentStreamPageNumber.value === null) {
      return false
    }

    if (!isKnownAgentStreamEvent(event)) {
      return true
    }

    const data = event.data
    if (typeof data === 'object' && data !== null && 'page_number' in data) {
      return data.page_number === currentStreamPageNumber.value
    }

    return true
  }

  function findCurrentPageTitle(): string | null {
    const pageNumber = currentStreamPageNumber.value ?? options.currentPageNumber.value
    const page = options.workspaceStore.projectPages.find((item) => item.page_number === pageNumber)
    return page?.title ?? null
  }

  return {
    activeOptimizingPageNumber,
    agentConnectionState,
    agentEventLog,
    confirmCurrentPage,
    confirmingPage,
    currentActionLabel,
    disconnect,
    handleMessageRevealComplete,
    isAgentRequestInFlight,
    isBusy,
    isCurrentPageOptimizing,
    latestError,
    latestUpdatedPage,
    latestPreviewRefreshRequest,
    loadPageMessages,
    optimizationUpdatedSignal,
    pageMessages,
    pageMessagesError,
    pageMessagesLoaded,
    pageMessagesLoading,
    regenerateCurrentPage,
    sendPageMessage,
    sendQuickActionPrompt,
    timelineItems
  }
}

function normalizePageNumber(pageNumber: number): number | null {
  if (!Number.isFinite(pageNumber)) {
    return null
  }

  return Math.max(1, Math.floor(pageNumber))
}

function buildMessageDedupeKey(
  role: 'assistant' | 'user',
  messageType: string,
  content: string,
  pageNumber: number | null
): string {
  return [role, messageType, pageNumber ?? 'global', normalizeForKey(content)].join('|')
}

function normalizeForKey(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

function resolveUiError(error: unknown, fallback = '页面优化请求失败，请确认 Python 后端已经启动。'): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }

  return fallback
}

function summarizeAgentEvent(event: AgentStreamEvent): string {
  if (isKnownAgentStreamEvent(event)) {
    switch (event.event) {
      case 'thinking':
        return event.data.content
      case 'page_optimizing':
        return `正在优化第 ${event.data.page_number} 页《${event.data.title}》`
      case 'page_updated':
        return `第 ${event.data.page_number} 页已更新到 v${event.data.version ?? '?'}`
      case 'deliberation_started':
        return `开始 ${formatDeliberationTarget(event.data.target)} 思辨，共 ${event.data.rounds} 轮`
      case 'deliberation_round':
        return `${formatDeliberationRole(event.data.role)}：${event.data.content}`
      case 'deliberation_summary':
        return detectGenerationFallbackSummary(event.data.summary)
          ? `思辨回退：${event.data.summary}`
          : event.data.summary
      case 'assistant_message':
        return event.data.content
      case 'error':
        return event.data.message
      case 'done':
        return '页面优化会话已结束'
      case 'file_parsed':
        return `${event.data.file_name}：${event.data.summary}`
      case 'outline':
        return `已收到 ${event.data.outline.total_pages} 页大纲事件`
      case 'page_generating':
        return `正在生成第 ${event.data.page_number} 页《${event.data.title}》`
      case 'page_complete':
        return `第 ${event.data.page_number} 页《${event.data.title}》已完成`
    }
  }

  return `收到 ${event.event} 事件`
}

function formatDeliberationTarget(target: string): string {
  return target === 'page_optimizer' ? '页面优化' : target
}

function formatDeliberationRole(role: string): string {
  switch (role) {
    case 'draft':
      return '草案'
    case 'critic':
      return '评审'
    case 'synthesis':
      return '综合'
    default:
      return role
  }
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
    || event.event === 'page_optimizing'
    || event.event === 'page_updated'
    || event.event === 'assistant_message'
    || event.event === 'error'
    || event.event === 'done'
}
