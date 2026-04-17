import { getApiBaseUrl } from './api'
import type {
  AgentChatRequestPayload,
  AgentConfirmOutlineRequestPayload,
  AgentSSEEvent,
  AgentSSEEventMap,
  AgentSSEEventName,
  AgentStreamEvent,
  AssistantMessageEventPayload,
  DeliberationRoundEventPayload,
  DeliberationStartedEventPayload,
  DeliberationSummaryEventPayload,
  ErrorEventPayload,
  FileParsedEventPayload,
  OutlineEventPayload,
  PageCompleteEventPayload,
  PageGeneratingEventPayload,
  PageOptimizingEventPayload,
  PageUpdatedEventPayload,
  ThinkingEventPayload
} from '@/types/chat'

type StreamMode = 'chat' | 'confirm-outline' | 'generate-page'

interface StreamOpenPayload {
  includeApiKey: boolean
  payload: object
  streamMode: StreamMode
  url: string
}

interface ActiveStreamSession {
  controller: AbortController
  includeApiKey: boolean
  payload: object
  streamId: string | null
  streamMode: StreamMode
  url: string
}

type EventHandler<TPayload> = (payload: TPayload) => void
type AnyEventHandler = (event: AgentStreamEvent) => void
type ReconnectHandler = (attempt: number) => void

export class AgentSSEClient {
  private abortController: AbortController | null = null
  private activeSession: ActiveStreamSession | null = null
  private reconnectAttempt = 0
  private reconnectTimerId: number | null = null
  private intentionalDisconnect = false
  private readonly thinkingHandlers = new Set<EventHandler<ThinkingEventPayload>>()
  private readonly fileParsedHandlers = new Set<EventHandler<FileParsedEventPayload>>()
  private readonly outlineHandlers = new Set<EventHandler<OutlineEventPayload>>()
  private readonly deliberationStartedHandlers = new Set<EventHandler<DeliberationStartedEventPayload>>()
  private readonly deliberationRoundHandlers = new Set<EventHandler<DeliberationRoundEventPayload>>()
  private readonly deliberationSummaryHandlers = new Set<EventHandler<DeliberationSummaryEventPayload>>()
  private readonly pageGeneratingHandlers = new Set<EventHandler<PageGeneratingEventPayload>>()
  private readonly pageCompleteHandlers = new Set<EventHandler<PageCompleteEventPayload>>()
  private readonly pageOptimizingHandlers = new Set<EventHandler<PageOptimizingEventPayload>>()
  private readonly pageUpdatedHandlers = new Set<EventHandler<PageUpdatedEventPayload>>()
  private readonly assistantMessageHandlers = new Set<EventHandler<AssistantMessageEventPayload>>()
  private readonly errorHandlers = new Set<EventHandler<ErrorEventPayload>>()
  private readonly doneHandlers = new Set<EventHandler<Record<string, never>>>()
  private readonly reconnectHandlers = new Set<ReconnectHandler>()
  private readonly anyEventHandlers = new Set<AnyEventHandler>()

  public async connect(projectId: string, message: string, pageNumber?: number): Promise<void> {
    const normalizedProjectId = projectId.trim()
    const normalizedMessage = message.trim()

    if (!normalizedProjectId) {
      throw new Error('Project id is required before starting an SSE chat session.')
    }

    if (!normalizedMessage) {
      throw new Error('Message content is required before starting an SSE chat session.')
    }

    this.disconnect()

    await this.openStream({
      includeApiKey: true,
      payload: this.buildRequestPayload(normalizedMessage, pageNumber),
      streamMode: 'chat',
      url: await this.buildChatUrl(normalizedProjectId)
    })
  }

  public async confirmOutline(projectId: string, outline?: AgentConfirmOutlineRequestPayload['outline']): Promise<void> {
    const normalizedProjectId = projectId.trim()
    if (!normalizedProjectId) {
      throw new Error('Project id is required before confirming the outline.')
    }

    this.disconnect()

    await this.openStream({
      includeApiKey: true,
      payload: this.buildConfirmOutlinePayload(outline),
      streamMode: 'confirm-outline',
      url: await this.buildConfirmOutlineUrl(normalizedProjectId)
    })
  }

  public async generatePage(projectId: string, pageNumber: number): Promise<void> {
    const normalizedProjectId = projectId.trim()
    const normalizedPageNumber = Number.isFinite(pageNumber) ? Math.max(1, Math.floor(pageNumber)) : null

    if (!normalizedProjectId) {
      throw new Error('Project id is required before generating a page.')
    }

    if (normalizedPageNumber === null) {
      throw new Error('A valid page number is required before generating a page.')
    }

    this.disconnect()

    await this.openStream({
      includeApiKey: true,
      payload: {},
      streamMode: 'generate-page',
      url: await this.buildGeneratePageUrl(normalizedProjectId, normalizedPageNumber)
    })
  }

  public disconnect(): void {
    this.intentionalDisconnect = true
    this.clearReconnectTimer()
    void this.cancelActiveStream().catch(() => undefined)
    this.abortController?.abort()
    this.abortController = null
    this.activeSession = null
  }

  public async reconnect(): Promise<void> {
    if (!this.activeSession) {
      throw new Error('当前没有可恢复的实时会话。')
    }

    const previousSession = this.activeSession
    await this.openStream({
      includeApiKey: previousSession.includeApiKey,
      payload: previousSession.payload,
      streamMode: previousSession.streamMode,
      url: previousSession.url
    }, {
      reconnecting: true,
      streamId: previousSession.streamId
    })
  }

  public onThinking(callback: EventHandler<ThinkingEventPayload>): () => void {
    return this.registerHandler(this.thinkingHandlers, callback)
  }

  public onFileParsed(callback: EventHandler<FileParsedEventPayload>): () => void {
    return this.registerHandler(this.fileParsedHandlers, callback)
  }

  public onOutline(callback: EventHandler<OutlineEventPayload>): () => void {
    return this.registerHandler(this.outlineHandlers, callback)
  }

  public onDeliberationStarted(callback: EventHandler<DeliberationStartedEventPayload>): () => void {
    return this.registerHandler(this.deliberationStartedHandlers, callback)
  }

  public onDeliberationRound(callback: EventHandler<DeliberationRoundEventPayload>): () => void {
    return this.registerHandler(this.deliberationRoundHandlers, callback)
  }

  public onDeliberationSummary(callback: EventHandler<DeliberationSummaryEventPayload>): () => void {
    return this.registerHandler(this.deliberationSummaryHandlers, callback)
  }

  public onPageGenerating(callback: EventHandler<PageGeneratingEventPayload>): () => void {
    return this.registerHandler(this.pageGeneratingHandlers, callback)
  }

  public onPageComplete(callback: EventHandler<PageCompleteEventPayload>): () => void {
    return this.registerHandler(this.pageCompleteHandlers, callback)
  }

  public onPageOptimizing(callback: EventHandler<PageOptimizingEventPayload>): () => void {
    return this.registerHandler(this.pageOptimizingHandlers, callback)
  }

  public onPageUpdated(callback: EventHandler<PageUpdatedEventPayload>): () => void {
    return this.registerHandler(this.pageUpdatedHandlers, callback)
  }

  public onAssistantMessage(callback: EventHandler<AssistantMessageEventPayload>): () => void {
    return this.registerHandler(this.assistantMessageHandlers, callback)
  }

  public onError(callback: EventHandler<ErrorEventPayload>): () => void {
    return this.registerHandler(this.errorHandlers, callback)
  }

  public onDone(callback: EventHandler<Record<string, never>>): () => void {
    return this.registerHandler(this.doneHandlers, callback)
  }

  public onReconnect(callback: ReconnectHandler): () => void {
    return this.registerHandler(this.reconnectHandlers, callback)
  }

  public onEvent(callback: AnyEventHandler): () => void {
    return this.registerHandler(this.anyEventHandlers, callback)
  }

  private async buildChatUrl(projectId: string): Promise<string> {
    const baseUrl = await getApiBaseUrl()
    return new URL(
      `projects/${encodeURIComponent(projectId)}/agent/chat`,
      ensureTrailingSlash(baseUrl)
    ).toString()
  }

  private async buildConfirmOutlineUrl(projectId: string): Promise<string> {
    const baseUrl = await getApiBaseUrl()
    return new URL(
      `projects/${encodeURIComponent(projectId)}/agent/confirm-outline`,
      ensureTrailingSlash(baseUrl)
    ).toString()
  }

  private async buildGeneratePageUrl(projectId: string, pageNumber: number): Promise<string> {
    const baseUrl = await getApiBaseUrl()
    return new URL(
      `projects/${encodeURIComponent(projectId)}/pages/${pageNumber}/regenerate`,
      ensureTrailingSlash(baseUrl)
    ).toString()
  }

  private buildRequestPayload(message: string, pageNumber?: number): AgentChatRequestPayload {
    if (pageNumber === undefined) {
      return { message }
    }

    return {
      message,
      page_number: pageNumber
    }
  }

  private buildConfirmOutlinePayload(outline?: AgentConfirmOutlineRequestPayload['outline']): AgentConfirmOutlineRequestPayload {
    if (!outline) {
      return {}
    }

    return { outline }
  }

  private async openStream(
    options: StreamOpenPayload,
    reconnectOptions?: {
      reconnecting?: boolean
      streamId?: string | null
    }
  ): Promise<void> {
    const controller = new AbortController()
    this.abortController = controller
    this.intentionalDisconnect = false
    this.clearReconnectTimer()

    const headers: HeadersInit = {
      accept: 'text/event-stream',
      'content-type': 'application/json'
    }

    if (options.includeApiKey) {
      headers['x-ppt-studio-api-key'] = await this.resolveApiKey()
    }

    if (reconnectOptions?.streamId) {
      headers['x-ppt-studio-stream-id'] = reconnectOptions.streamId
    }

    this.activeSession = {
      controller,
      includeApiKey: options.includeApiKey,
      payload: options.payload,
      streamId: reconnectOptions?.streamId ?? null,
      streamMode: options.streamMode,
      url: options.url
    }

    try {
      const response = await fetch(options.url, {
        body: JSON.stringify(options.payload),
        headers,
        method: 'POST',
        signal: controller.signal
      })

      if (!response.ok) {
        throw await this.buildResponseError(response)
      }

      if (!response.body) {
        throw new Error('Backend returned an empty SSE response body.')
      }

      const contentType = response.headers.get('content-type')?.toLowerCase() ?? ''
      if (!contentType.includes('text/event-stream')) {
        throw new Error(`Expected an SSE response but received "${contentType || 'unknown'}".`)
      }

      this.reconnectAttempt = 0
      this.captureStreamId(response)
      await this.consumeEventStream(response.body, controller)
    } catch (error: unknown) {
      if (this.isAbortError(error) && controller.signal.aborted) {
        return
      }

      const normalizedError = this.normalizeClientError(error)
      if (this.shouldScheduleReconnect(normalizedError)) {
        this.scheduleReconnect()
      }

      throw normalizedError
    } finally {
      if (this.abortController === controller) {
        this.abortController = null
      }
    }
  }

  private async consumeEventStream(stream: ReadableStream<Uint8Array>, controller: AbortController): Promise<void> {
    const reader = stream.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let streamCompleted = false

    try {
      while (!streamCompleted) {
        const { done, value } = await reader.read()

        if (done) {
          buffer += decoder.decode()
        } else if (value) {
          buffer += decoder.decode(value, { stream: true })
        }

        const parsedBlocks = splitEventBlocks(buffer)
        buffer = parsedBlocks.remaining

        for (const block of parsedBlocks.blocks) {
          const event = parseEventBlock(block)
          if (!event) {
            continue
          }

          this.dispatchEvent(event)

          if (event.event === 'done') {
            streamCompleted = true
            break
          }
        }

        if (done) {
          break
        }
      }

      const trailingEvent = parseEventBlock(buffer)
      if (trailingEvent) {
        this.dispatchEvent(trailingEvent)
      }

      if (!streamCompleted && !controller.signal.aborted) {
        throw new Error('SSE 连接已中断，正在尝试恢复。')
      }
    } catch (error: unknown) {
      if (this.isAbortError(error) && controller.signal.aborted) {
        return
      }

      throw error
    } finally {
      await reader.cancel().catch(() => undefined)
      reader.releaseLock()
    }
  }

  private dispatchEvent(event: AgentStreamEvent): void {
    if (isKnownAgentStreamEvent(event)) {
      this.dispatchKnownEvent(event)
    }

    this.emitHandlers(this.anyEventHandlers, event)
  }

  private dispatchKnownEvent(event: AgentSSEEvent): void {
    switch (event.event) {
      case 'thinking':
        this.emitHandlers(this.thinkingHandlers, event.data)
        return
      case 'file_parsed':
        this.emitHandlers(this.fileParsedHandlers, event.data)
        return
      case 'outline':
        this.emitHandlers(this.outlineHandlers, event.data)
        return
      case 'deliberation_started':
        this.emitHandlers(this.deliberationStartedHandlers, event.data)
        return
      case 'deliberation_round':
        this.emitHandlers(this.deliberationRoundHandlers, event.data)
        return
      case 'deliberation_summary':
        this.emitHandlers(this.deliberationSummaryHandlers, event.data)
        return
      case 'page_generating':
        this.emitHandlers(this.pageGeneratingHandlers, event.data)
        return
      case 'page_complete':
        this.emitHandlers(this.pageCompleteHandlers, event.data)
        return
      case 'page_optimizing':
        this.emitHandlers(this.pageOptimizingHandlers, event.data)
        return
      case 'page_updated':
        this.emitHandlers(this.pageUpdatedHandlers, event.data)
        return
      case 'assistant_message':
        this.emitHandlers(this.assistantMessageHandlers, event.data)
        return
      case 'error':
        this.emitHandlers(this.errorHandlers, event.data)
        return
      case 'done':
        this.clearReconnectTimer()
        this.activeSession = null
        this.emitHandlers(this.doneHandlers, event.data)
        return
    }
  }

  private emitHandlers<TPayload>(handlers: Set<EventHandler<TPayload>>, payload: TPayload): void {
    for (const handler of handlers) {
      handler(payload)
    }
  }

  private registerHandler<TPayload>(handlers: Set<EventHandler<TPayload>>, callback: EventHandler<TPayload>): () => void {
    handlers.add(callback)
    return () => {
      handlers.delete(callback)
    }
  }

  private async buildResponseError(response: Response): Promise<Error> {
    let detail: unknown = null

    try {
      const rawText = await response.text()
      if (rawText) {
        detail = isJsonContentType(response.headers.get('content-type')) ? JSON.parse(rawText) : rawText
      }
    } catch (error: unknown) {
      detail = error
    }

    const detailMessage = extractErrorMessage(detail)
    const statusText = response.statusText ? ` ${response.statusText}` : ''

    return new Error(detailMessage ?? `Agent chat request failed with status ${response.status}${statusText}.`)
  }

  private isAbortError(error: unknown): boolean {
    return error instanceof DOMException && error.name === 'AbortError'
  }

  private normalizeClientError(error: unknown): Error {
    if (error instanceof Error) {
      return error
    }

    return new Error('Unable to establish the SSE chat stream.')
  }

  private async resolveApiKey(): Promise<string> {
    const runtime = resolveRuntime()
    const apiKey = (await runtime.getApiKey())?.trim() ?? ''

    if (!apiKey) {
      throw new Error('请先在设置页配置 API Key')
    }

    return apiKey
  }

  private captureStreamId(response: Response): void {
    const streamId = response.headers.get('x-ppt-studio-stream-id')?.trim() ?? ''
    if (!streamId || !this.activeSession) {
      return
    }

    this.activeSession.streamId = streamId
  }

  private shouldScheduleReconnect(error: Error): boolean {
    if (this.intentionalDisconnect || !this.activeSession) {
      return false
    }

    if (this.activeSession.streamMode === 'generate-page') {
      return true
    }

    if (this.activeSession.streamMode === 'confirm-outline') {
      return true
    }

    return true
  }

  private scheduleReconnect(): void {
    if (!this.activeSession || this.reconnectTimerId !== null) {
      return
    }

    const nextAttempt = this.reconnectAttempt + 1
    if (nextAttempt > 3) {
      return
    }

    this.reconnectAttempt = nextAttempt
    this.emitHandlers(this.reconnectHandlers, nextAttempt)
    const reconnectDelay = Math.min(3000, 600 * nextAttempt)
    this.reconnectTimerId = window.setTimeout(() => {
      this.reconnectTimerId = null
      void this.reconnect().catch(() => undefined)
    }, reconnectDelay)
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimerId === null) {
      return
    }

    window.clearTimeout(this.reconnectTimerId)
    this.reconnectTimerId = null
  }

  private async cancelActiveStream(): Promise<void> {
    const activeSession = this.activeSession
    if (!activeSession?.streamId) {
      return
    }

    const baseUrl = await getApiBaseUrl()
    const cancelPath = activeSession.streamMode === 'generate-page'
      ? `projects/${extractProjectId(activeSession.url)}/pages/streams/${activeSession.streamId}/cancel`
      : `projects/${extractProjectId(activeSession.url)}/agent/streams/${activeSession.streamId}/cancel`

    await fetch(new URL(cancelPath, ensureTrailingSlash(baseUrl)).toString(), {
      method: 'POST'
    }).catch(() => undefined)
  }
}

function splitEventBlocks(buffer: string): { blocks: string[]; remaining: string } {
  const normalizedBuffer = normalizeNewlines(buffer)
  const chunks = normalizedBuffer.split('\n\n')

  return {
    blocks: chunks.slice(0, -1).map((block) => block.trim()).filter((block) => block.length > 0),
    remaining: chunks.at(-1) ?? ''
  }
}

function parseEventBlock(block: string): AgentStreamEvent | null {
  const trimmedBlock = block.trim()
  if (!trimmedBlock) {
    return null
  }

  let eventName = 'message'
  const dataLines: string[] = []

  for (const line of normalizeNewlines(trimmedBlock).split('\n')) {
    if (!line || line.startsWith(':')) {
      continue
    }

    if (line.startsWith('event:')) {
      eventName = line.slice('event:'.length).trim()
      continue
    }

    if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trimStart())
    }
  }

  const dataPayload = dataLines.join('\n')
  const parsedData = parseEventData(dataPayload)

  if (!isKnownAgentSSEEventName(eventName)) {
    return {
      data: parsedData,
      event: eventName
    }
  }

  return {
    data: parsedData as AgentSSEEventMap[typeof eventName],
    event: eventName
  }
}

function parseEventData(rawData: string): unknown {
  if (!rawData) {
    return {}
  }

  try {
    return JSON.parse(rawData) as unknown
  } catch {
    return rawData
  }
}

function isKnownAgentSSEEventName(value: string): value is AgentSSEEventName {
  return value === 'thinking'
    || value === 'file_parsed'
    || value === 'outline'
    || value === 'deliberation_started'
    || value === 'deliberation_round'
    || value === 'deliberation_summary'
    || value === 'page_generating'
    || value === 'page_complete'
    || value === 'page_optimizing'
    || value === 'page_updated'
    || value === 'assistant_message'
    || value === 'error'
    || value === 'done'
}

function isKnownAgentStreamEvent(event: AgentStreamEvent): event is AgentSSEEvent {
  return isKnownAgentSSEEventName(event.event)
}

function isJsonContentType(contentType: string | null): boolean {
  const normalizedContentType = contentType?.toLowerCase() ?? ''
  return normalizedContentType.includes('application/json') || normalizedContentType.includes('+json')
}

function extractErrorMessage(detail: unknown): string | null {
  if (typeof detail === 'string') {
    return detail.trim() || null
  }

  if (!detail || typeof detail !== 'object') {
    return null
  }

  if ('message' in detail && typeof detail.message === 'string') {
    const message = detail.message.trim()
    return message || null
  }

  if ('detail' in detail && typeof detail.detail === 'string') {
    const message = detail.detail.trim()
    return message || null
  }

  return null
}

function normalizeNewlines(value: string): string {
  return value.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
}

function ensureTrailingSlash(value: string): string {
  return value.endsWith('/') ? value : `${value}/`
}

function resolveRuntime(): Window['pptStudio'] {
  if (typeof window === 'undefined' || !window.pptStudio) {
    throw new Error('PPT Studio Electron runtime is unavailable in the current context.')
  }

  return window.pptStudio
}

function extractProjectId(url: string): string {
  const match = url.match(/projects\/([^/]+)/)
  return decodeURIComponent(match?.[1] ?? '')
}
