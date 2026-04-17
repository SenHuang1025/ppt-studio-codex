import type { OutlinePage, ProjectPage } from './project'

export const PREVIEW_PAGE_STATUS_VALUES = ['generated', 'confirmed', 'generating', 'pending'] as const

export type PreviewPageStatus = (typeof PREVIEW_PAGE_STATUS_VALUES)[number]

export const PAGE_GENERATION_STAGE_VALUES = ['draft', 'critic', 'synthesis'] as const

export type PageGenerationStage = (typeof PAGE_GENERATION_STAGE_VALUES)[number]

export const PREVIEW_RENDER_TARGET_KIND_VALUES = ['live', 'version'] as const

export type PreviewRenderTargetKind = (typeof PREVIEW_RENDER_TARGET_KIND_VALUES)[number]

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
  chatMessageCount: number
  contentBrief: string | null
  generatedPage: ProjectPage | null
  hasGeneratedCode: boolean
  layout: string | null
  outlinePage: OutlinePage | null
  pageNumber: number
  pageType: string | null
  status: PreviewPageStatus
  thumbnailSignature: string | null
  title: string
  updatedAt: string | null
  version: number | null
}

export interface IframeScrollSnapshotElement {
  left: number
  path: string
  top: number
}

export interface IframeScrollSnapshot {
  elements: IframeScrollSnapshotElement[]
  window: {
    left: number
    top: number
  }
}

export interface PreviewRefreshRequest {
  pageNumber: number
  reason: 'page_complete' | 'page_updated'
  sequence: number
  version: number | null
}

export interface PreviewVersionSelection {
  changeDescription: string | null
  createdAt: string
  pageNumber: number
  previewToken: number
  sourceVersion: number
  vueCode: string
}
