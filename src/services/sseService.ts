import { getApiBaseUrl } from './api'
import type {
  AgentChatRequestPayload,
  AgentSSEEvent,
  AgentSSEEventMap,
  AgentSSEEventName,
  AgentStreamEvent,
  AssistantMessageEventPayload,
  ErrorEventPayload,
  FileParsedEventPayload,
  OutlineEventPayload,
  ThinkingEventPayload
} from '@/types/chat'

type EventHandler<TPayload> = (payload: TPayload) => void
type AnyEventHandler = (event: AgentStreamEvent) => void

export class AgentSSEClient {
  private abortController: AbortController | null = null
  private readonly thinkingHandlers = new Set<EventHandler<ThinkingEventPayload>>()
  private readonly fileParsedHandlers = new Set<EventHandler<FileParsedEventPayload>>()
  private readonly outlineHandlers = new Set<EventHandler<OutlineEventPayload>>()
  private readonly assistantMessageHandlers = new Set<EventHandler<AssistantMessageEventPayload>>()
  private readonly errorHandlers = new Set<EventHandler<ErrorEventPayload>>()
  private readonly doneHandlers = new Set<EventHandler<Record<string, never>>>()
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

    const controller = new AbortController()
    this.abortController = controller

    try {
      const response = await fetch(await this.buildChatUrl(normalizedProjectId), {
        body: JSON.stringify(this.buildRequestPayload(normalizedMessage, pageNumber)),
        headers: {
          accept: 'text/event-stream',
          'content-type': 'application/json'
        },
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

      await this.consumeEventStream(response.body, controller)
    } catch (error: unknown) {
      if (this.isAbortError(error) && controller.signal.aborted) {
        return
      }

      throw this.normalizeClientError(error)
    } finally {
      if (this.abortController === controller) {
        this.abortController = null
      }
    }
  }

  public disconnect(): void {
    this.abortController?.abort()
    this.abortController = null
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

  public onAssistantMessage(callback: EventHandler<AssistantMessageEventPayload>): () => void {
    return this.registerHandler(this.assistantMessageHandlers, callback)
  }

  public onError(callback: EventHandler<ErrorEventPayload>): () => void {
    return this.registerHandler(this.errorHandlers, callback)
  }

  public onDone(callback: EventHandler<Record<string, never>>): () => void {
    return this.registerHandler(this.doneHandlers, callback)
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

  private buildRequestPayload(message: string, pageNumber?: number): AgentChatRequestPayload {
    if (pageNumber === undefined) {
      return { message }
    }

    return {
      message,
      page_number: pageNumber
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
      case 'assistant_message':
        this.emitHandlers(this.assistantMessageHandlers, event.data)
        return
      case 'error':
        this.emitHandlers(this.errorHandlers, event.data)
        return
      case 'done':
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
