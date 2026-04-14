import type { OutlinePage, ProjectPage } from './project'

export const PREVIEW_PAGE_STATUS_VALUES = ['generated', 'generating', 'pending'] as const

export type PreviewPageStatus = (typeof PREVIEW_PAGE_STATUS_VALUES)[number]

export const SLIDE_RENDERER_STATE_VALUES = ['idle', 'loading', 'ready', 'error'] as const

export type SlideRendererState = (typeof SLIDE_RENDERER_STATE_VALUES)[number]

export const SLIDE_RENDERER_ERROR_KIND_VALUES = ['server-unavailable', 'slide-load-failed'] as const

export type SlideRendererErrorKind = (typeof SLIDE_RENDERER_ERROR_KIND_VALUES)[number]

export interface RealtimePageGenerationState {
  pageNumber: number
  status: PreviewPageStatus
  title: string | null
  updatedAt: string
  vueCode?: string | null
}

export interface PreviewPageItem {
  contentBrief: string | null
  generatedPage: ProjectPage | null
  hasGeneratedCode: boolean
  layout: string | null
  outlinePage: OutlinePage | null
  pageNumber: number
  pageType: string | null
  status: PreviewPageStatus
  title: string
  updatedAt: string | null
  version: number | null
}
