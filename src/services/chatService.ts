import { apiClient } from './api'
import type { ChatMessageListResponse } from '@/types/chat'

export interface ChatMessageListOptions {
  includeGlobal?: boolean
  includePageMessages?: boolean
  limit?: number
  pageNumber?: number
}

function encodeProjectChatMessagesPath(projectId: string): string {
  return `/projects/${encodeURIComponent(projectId)}/chat/messages`
}

export const chatService = {
  list(projectId: string, options?: ChatMessageListOptions): Promise<ChatMessageListResponse> {
    return apiClient.get<ChatMessageListResponse>(encodeProjectChatMessagesPath(projectId), {
      params: {
        include_global: options?.includeGlobal,
        include_page_messages: options?.includePageMessages,
        limit: options?.limit,
        page_number: options?.pageNumber
      }
    })
  }
}
