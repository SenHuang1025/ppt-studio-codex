import type { ThemeConfig } from './theme'

export const PROJECT_STATUS_VALUES = [
  'draft',
  'planning',
  'generating',
  'editing',
  'completed',
  'archived'
] as const

export type ProjectStatus = (typeof PROJECT_STATUS_VALUES)[number]

export const PAGE_STATUS_VALUES = ['planned', 'generating', 'generated', 'optimizing', 'confirmed'] as const

export type PageStatus = (typeof PAGE_STATUS_VALUES)[number]

export interface OutlinePage {
  content_brief: string
  data_refs: string[]
  layout: string
  page_number: number
  title: string
  type: string
}

export interface Outline {
  pages: OutlinePage[]
  theme_suggestion: string
  title: string
  total_pages: number
}

export interface ProjectPage {
  chat_message_count: number
  created_at: string
  id: string
  page_number: number
  page_type: string | null
  project_id: string
  status: PageStatus
  title: string | null
  updated_at: string
  version: number
  vue_code: string | null
}

export interface PageVersion {
  change_description: string | null
  created_at: string
  id: string
  page_id: string
  version: number
  vue_code: string
}

export interface PageInsertAfterPayload {
  description: string
}

export interface PageMutationResponse {
  success: boolean
}

export interface PageReorderPayload {
  page_numbers: number[]
}

export interface Project {
  created_at: string
  description: string | null
  id: string
  name: string
  status: ProjectStatus
  theme_config: ThemeConfig | null
  total_pages: number
  updated_at: string
}

export interface ProjectCreatePayload {
  description?: string | null
  name: string
}

export interface ProjectUpdatePayload {
  description?: string | null
  name?: string
  status?: ProjectStatus
}

export interface ProjectListResponse {
  projects: Project[]
  total: number
}

export interface ProjectDetailResponse extends Project {
  outline: Outline | null
  pages: ProjectPage[]
}

export interface ProjectDeleteResponse {
  success: boolean
}
