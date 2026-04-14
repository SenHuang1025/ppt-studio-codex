import type { FileParseStatus } from './file'
import type { Outline } from './project'

export const CHAT_ROLE_VALUES = ['user', 'assistant', 'system'] as const

export type ChatRole = (typeof CHAT_ROLE_VALUES)[number]

export const CHAT_MESSAGE_TYPE_VALUES = ['text', 'file_upload', 'outline', 'code', 'status'] as const

export type ChatMessageType = (typeof CHAT_MESSAGE_TYPE_VALUES)[number]

export interface ChatMessage {
  content: string
  created_at: string
  id: string
  message_type: ChatMessageType
  metadata: Record<string, unknown> | null
  page_number: number | null
  project_id: string
  role: ChatRole
}

export interface ChatMessageListResponse {
  messages: ChatMessage[]
  total: number
}

export interface AgentConfirmOutlineRequestPayload {
  outline?: Outline | null
}

export type AgentConnectionState = 'idle' | 'connecting' | 'streaming' | 'completed' | 'error'

export const AGENT_SSE_EVENT_NAMES = [
  'thinking',
  'file_parsed',
  'outline',
  'deliberation_started',
  'deliberation_round',
  'deliberation_summary',
  'page_generating',
  'page_complete',
  'assistant_message',
  'error',
  'done'
] as const

export type AgentSSEEventName = (typeof AGENT_SSE_EVENT_NAMES)[number]

export interface AgentChatRequestPayload {
  message: string
  page_number?: number
}

export interface ChatTimelineFileAttachment {
  fileSize: number | null
  fileType: string
  id: string
  name: string
  parseStatus: FileParseStatus | 'local'
}

export interface ChatTimelineDeliberationEntry {
  content: string
  id: string
  role: string
}

export interface ChatTimelineBaseItem {
  createdAt: string
  dedupeKey?: string | null
  id: string
  sortOrder: number
  source: 'persisted' | 'session'
}

export interface UserChatTimelineItem extends ChatTimelineBaseItem {
  content: string
  type: 'user_message'
}

export interface AssistantChatTimelineItem extends ChatTimelineBaseItem {
  animate?: boolean
  content: string
  contentFormat: 'markdown' | 'plain'
  type: 'assistant_message'
}

export interface OutlineChatTimelineItem extends ChatTimelineBaseItem {
  focusPageNumber: number | null
  outline: Outline | null
  summary: string
  type: 'outline_message'
}

export interface FileUploadChatTimelineItem extends ChatTimelineBaseItem {
  files: ChatTimelineFileAttachment[]
  type: 'file_upload'
}

export interface FileAnalysisChatTimelineItem extends ChatTimelineBaseItem {
  fileId: string
  fileName: string
  summary: string
  type: 'file_analysis'
}

export interface StatusChatTimelineItem extends ChatTimelineBaseItem {
  content: string
  label: string
  tone: 'error' | 'info' | 'success' | 'warning'
  type: 'status_message'
}

export interface DeliberationChatTimelineItem extends ChatTimelineBaseItem {
  entries: ChatTimelineDeliberationEntry[]
  rounds: number | null
  summary: string | null
  target: string
  type: 'deliberation_message'
}

export interface ThinkingChatTimelineItem extends ChatTimelineBaseItem {
  agent: string
  content: string
  type: 'thinking'
}

export type ChatTimelineItem =
  | UserChatTimelineItem
  | AssistantChatTimelineItem
  | OutlineChatTimelineItem
  | FileUploadChatTimelineItem
  | FileAnalysisChatTimelineItem
  | StatusChatTimelineItem
  | DeliberationChatTimelineItem
  | ThinkingChatTimelineItem

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

export interface DeliberationStartedEventPayload {
  rounds: number
  target: string
}

export interface DeliberationRoundEventPayload {
  content: string
  role: string
  target: string
}

export interface DeliberationSummaryEventPayload {
  summary: string
  target: string
}

export interface PageGeneratingEventPayload {
  page_number: number
  status: string
  title: string
}

export interface PageCompleteEventPayload {
  page_number: number
  status: string
  title: string
  vue_code: string
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
  deliberation_started: DeliberationStartedEventPayload
  deliberation_round: DeliberationRoundEventPayload
  deliberation_summary: DeliberationSummaryEventPayload
  page_generating: PageGeneratingEventPayload
  page_complete: PageCompleteEventPayload
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
