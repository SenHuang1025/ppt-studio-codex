import type { Outline } from './project'

export const AGENT_SSE_EVENT_NAMES = [
  'thinking',
  'file_parsed',
  'outline',
  'assistant_message',
  'error',
  'done'
] as const

export type AgentSSEEventName = (typeof AGENT_SSE_EVENT_NAMES)[number]

export interface AgentChatRequestPayload {
  message: string
  page_number?: number
}

export interface ThinkingEventPayload {
  agent: string
  content: string
}

export interface FileParsedEventPayload {
  file_id: string
  file_name: string
  summary: string
}

export interface OutlineEventPayload {
  outline: Outline
}

export interface AssistantMessageEventPayload {
  content: string
}

export interface ErrorEventPayload {
  message: string
}

export type DoneEventPayload = Record<string, never>

export interface AgentSSEEventMap {
  thinking: ThinkingEventPayload
  file_parsed: FileParsedEventPayload
  outline: OutlineEventPayload
  assistant_message: AssistantMessageEventPayload
  error: ErrorEventPayload
  done: DoneEventPayload
}

export type AgentSSEEvent = {
  [TEventName in AgentSSEEventName]: {
    event: TEventName
    data: AgentSSEEventMap[TEventName]
  }
}[AgentSSEEventName]

export interface UnknownAgentSSEEvent {
  event: string
  data: unknown
}

export type AgentStreamEvent = AgentSSEEvent | UnknownAgentSSEEvent

export interface AgentEventLogItem {
  id: string
  event: string
  received_at: string
  summary: string
}
