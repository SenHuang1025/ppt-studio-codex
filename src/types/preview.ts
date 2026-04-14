import type { OutlinePage, ProjectPage } from './project'

export const PREVIEW_PAGE_STATUS_VALUES = ['generated', 'generating', 'pending'] as const

export type PreviewPageStatus = (typeof PREVIEW_PAGE_STATUS_VALUES)[number]

export const PAGE_GENERATION_STAGE_VALUES = ['draft', 'critic', 'synthesis'] as const

export type PageGenerationStage = (typeof PAGE_GENERATION_STAGE_VALUES)[number]

export const SLIDE_RENDERER_STATE_VALUES = ['idle', 'loading', 'ready', 'error'] as const

export type SlideRendererState = (typeof SLIDE_RENDERER_STATE_VALUES)[number]

export const SLIDE_RENDERER_ERROR_KIND_VALUES = ['server-unavailable', 'slide-load-failed'] as const

export type SlideRendererErrorKind = (typeof SLIDE_RENDERER_ERROR_KIND_VALUES)[number]

export interface RealtimePageGenerationState {
  error: string | null
  fallbackDetected: boolean
  pageNumber: number
  stage: PageGenerationStage | null
  status: PreviewPageStatus
  title: string | null
  updatedAt: string
  vueCode?: string | null
}

export interface WorkspaceGenerationProgressState {
  completionRatio: number
  currentGeneratingPageNumber: number | null
  currentGeneratingPageTitle: string | null
  currentGenerationStage: PageGenerationStage | null
  currentGenerationStageLabel: string | null
  generatedCount: number
  generationError: string | null
  generatingCount: number
  isGenerationActive: boolean
  isGenerationCompleted: boolean
  latestCompletedPageNumber: number | null
  latestCompletedPageTitle: string | null
  pageGeneratorFallbackDetected: boolean
  pendingCount: number
  totalPages: number
  visualProgressRatio: number
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
