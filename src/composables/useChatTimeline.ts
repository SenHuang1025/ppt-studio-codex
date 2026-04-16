import { computed, type ComputedRef, type Ref } from 'vue'
import type {
  AssistantChatTimelineItem,
  ChatMessage,
  ChatTimelineFileAttachment,
  ChatTimelineItem,
  FileUploadChatTimelineItem,
  OutlineChatTimelineItem,
  StatusChatTimelineItem,
  UserChatTimelineItem
} from '@/types/chat'
import type { Outline } from '@/types/project'

export function useChatTimeline(
  persistedMessages: Ref<ChatMessage[]>,
  sessionItems: Ref<ChatTimelineItem[]>
): ComputedRef<ChatTimelineItem[]> {
  const persistedTimelineItems = computed<ChatTimelineItem[]>(() =>
    persistedMessages.value.map((message, index) => mapPersistedChatMessage(message, index))
  )

  return computed<ChatTimelineItem[]>(() => {
    const sessionDedupeKeys = new Set(
      sessionItems.value
        .map((item) => item.dedupeKey)
        .filter((item): item is string => typeof item === 'string' && item.length > 0)
    )

    return [...persistedTimelineItems.value.filter((item) => !shouldHidePersistedItem(item, sessionDedupeKeys)), ...sessionItems.value]
      .sort(compareTimelineItems)
  })
}

function shouldHidePersistedItem(item: ChatTimelineItem, sessionDedupeKeys: Set<string>): boolean {
  return item.source === 'persisted'
    && typeof item.dedupeKey === 'string'
    && sessionDedupeKeys.has(item.dedupeKey)
}

function compareTimelineItems(left: ChatTimelineItem, right: ChatTimelineItem): number {
  const leftTimestamp = Date.parse(left.createdAt)
  const rightTimestamp = Date.parse(right.createdAt)

  if (!Number.isNaN(leftTimestamp) && !Number.isNaN(rightTimestamp) && leftTimestamp !== rightTimestamp) {
    return leftTimestamp - rightTimestamp
  }

  if (left.sortOrder !== right.sortOrder) {
    return left.sortOrder - right.sortOrder
  }

  return left.id.localeCompare(right.id)
}

function mapPersistedChatMessage(message: ChatMessage, index: number): ChatTimelineItem {
  const baseItem = {
    createdAt: message.created_at,
    id: `persisted-${message.id}`,
    source: 'persisted' as const,
    sortOrder: index
  }

  if (message.message_type === 'outline') {
    const outline = parseOutlineMetadata(message.metadata)
    const item: OutlineChatTimelineItem = {
      ...baseItem,
      dedupeKey: buildOutlineDedupeKey(outline, message.content, message.page_number),
      focusPageNumber: outline?.pages[0]?.page_number ?? message.page_number ?? null,
      outline,
      summary: message.content,
      type: 'outline_message'
    }
    return item
  }

  if (message.message_type === 'file_upload') {
    const item: FileUploadChatTimelineItem = {
      ...baseItem,
      dedupeKey: buildSimpleDedupeKey(message.role, message.message_type, message.content, message.page_number),
      files: parseFileAttachments(message.metadata),
      type: 'file_upload'
    }
    return item
  }

  if (message.message_type === 'status' || message.role === 'system') {
    const item: StatusChatTimelineItem = {
      ...baseItem,
      content: message.content,
      dedupeKey: buildSimpleDedupeKey(message.role, message.message_type, message.content, message.page_number),
      label: typeof message.metadata?.label === 'string' ? message.metadata.label : '系统状态',
      tone: parseStatusTone(message.metadata?.tone),
      type: 'status_message'
    }
    return item
  }

  if (message.role === 'user') {
    const item: UserChatTimelineItem = {
      ...baseItem,
      content: message.content,
      dedupeKey: buildSimpleDedupeKey(message.role, message.message_type, message.content, message.page_number),
      pageNumber: message.page_number,
      type: 'user_message'
    }
    return item
  }

  const item: AssistantChatTimelineItem = {
    ...baseItem,
    content: message.content,
    contentFormat: message.message_type === 'code' ? 'plain' : 'markdown',
    dedupeKey: buildSimpleDedupeKey(message.role, message.message_type, message.content, message.page_number),
    pageNumber: message.page_number,
    type: 'assistant_message'
  }
  return item
}

function parseOutlineMetadata(metadata: Record<string, unknown> | null): Outline | null {
  const outlineValue = metadata?.outline
  if (!outlineValue || typeof outlineValue !== 'object' || Array.isArray(outlineValue)) {
    return null
  }

  const candidate = outlineValue as Record<string, unknown>
  if (
    typeof candidate.title !== 'string'
    || typeof candidate.total_pages !== 'number'
    || typeof candidate.theme_suggestion !== 'string'
    || !Array.isArray(candidate.pages)
  ) {
    return null
  }

  const pages = candidate.pages
    .map((page) => parseOutlinePage(page))
    .filter((page): page is NonNullable<Outline['pages'][number]> => page !== null)

  return {
    pages,
    theme_suggestion: candidate.theme_suggestion,
    title: candidate.title,
    total_pages: candidate.total_pages
  }
}

function parseOutlinePage(value: unknown): Outline['pages'][number] | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null
  }

  const candidate = value as Record<string, unknown>
  if (
    typeof candidate.page_number !== 'number'
    || typeof candidate.title !== 'string'
    || typeof candidate.type !== 'string'
    || typeof candidate.content_brief !== 'string'
    || typeof candidate.layout !== 'string'
  ) {
    return null
  }

  const dataRefs = Array.isArray(candidate.data_refs)
    ? candidate.data_refs.filter((item): item is string => typeof item === 'string')
    : []

  return {
    content_brief: candidate.content_brief,
    data_refs: dataRefs,
    layout: candidate.layout,
    page_number: candidate.page_number,
    title: candidate.title,
    type: candidate.type
  }
}

function parseFileAttachments(metadata: Record<string, unknown> | null): ChatTimelineFileAttachment[] {
  const filesValue = metadata?.files
  if (!Array.isArray(filesValue)) {
    return []
  }

  return filesValue
    .map((file, index) => parseFileAttachment(file, index))
    .filter((file): file is ChatTimelineFileAttachment => file !== null)
}

function parseFileAttachment(value: unknown, index: number): ChatTimelineFileAttachment | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null
  }

  const candidate = value as Record<string, unknown>
  const name = typeof candidate.name === 'string'
    ? candidate.name
    : typeof candidate.original_name === 'string'
      ? candidate.original_name
      : null

  if (!name) {
    return null
  }

  return {
    fileSize: typeof candidate.fileSize === 'number'
      ? candidate.fileSize
      : typeof candidate.file_size === 'number'
        ? candidate.file_size
        : null,
    fileType: typeof candidate.fileType === 'string'
      ? candidate.fileType
      : typeof candidate.file_type === 'string'
        ? candidate.file_type
        : 'file',
    id: typeof candidate.id === 'string' ? candidate.id : `persisted-file-${index}`,
    name,
    parseStatus: parseFileStatus(candidate.parseStatus ?? candidate.parse_status)
  }
}

function parseFileStatus(value: unknown): ChatTimelineFileAttachment['parseStatus'] {
  return value === 'pending' || value === 'parsing' || value === 'parsed' || value === 'failed' ? value : 'local'
}

function parseStatusTone(value: unknown): StatusChatTimelineItem['tone'] {
  return value === 'success' || value === 'warning' || value === 'error' ? value : 'info'
}

function buildSimpleDedupeKey(
  role: string,
  messageType: string,
  content: string,
  pageNumber: number | null
): string {
  return [role, messageType, pageNumber ?? 'global', normalizeForKey(content)].join('|')
}

function buildOutlineDedupeKey(outline: Outline | null, content: string, pageNumber: number | null): string {
  if (!outline) {
    return buildSimpleDedupeKey('assistant', 'outline', content, pageNumber)
  }

  const titles = outline.pages.map((page) => page.title.trim()).join(',')
  return ['assistant', 'outline', outline.total_pages, normalizeForKey(outline.title), normalizeForKey(titles)].join('|')
}

function normalizeForKey(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}
