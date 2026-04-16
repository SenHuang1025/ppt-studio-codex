import type { LocationQueryValue } from 'vue-router'
import type { PageStatus, ProjectPage, ProjectStatus } from '@/types/project'
import type {
  PageGenerationStage,
  PreviewPageStatus,
  PreviewVersionSelection,
  RealtimePageGenerationState
} from '@/types/preview'

export function clampPreviewPageNumber(pageNumber: number, totalPages?: number): number {
  const normalizedPageNumber = Number.isFinite(pageNumber) ? Math.max(1, Math.floor(pageNumber)) : 1

  if (!Number.isFinite(totalPages) || !totalPages || totalPages <= 0) {
    return normalizedPageNumber
  }

  return Math.min(normalizedPageNumber, Math.floor(totalPages))
}

export function parsePreviewPageQuery(
  queryValue: LocationQueryValue | LocationQueryValue[] | undefined
): number | null {
  const rawValue = Array.isArray(queryValue) ? queryValue[0] : queryValue

  if (rawValue === undefined || rawValue === null || rawValue === '') {
    return null
  }

  const parsedPageNumber = Number.parseInt(String(rawValue), 10)
  return Number.isFinite(parsedPageNumber) ? Math.max(1, parsedPageNumber) : 1
}

export function getPreviewPageStatusLabel(status: PreviewPageStatus): string {
  switch (status) {
    case 'confirmed':
      return '已确认'
    case 'generated':
      return '已生成'
    case 'generating':
      return '生成中'
    default:
      return '待生成'
  }
}

export function getPageGenerationStageName(stage: PageGenerationStage | null | undefined): string | null {
  switch (stage) {
    case 'draft':
      return '草案'
    case 'critic':
      return '评审'
    case 'synthesis':
      return '综合'
    default:
      return null
  }
}

export function getActivePageGenerationStageLabel(stage: PageGenerationStage | null | undefined): string | null {
  switch (stage) {
    case 'draft':
      return '生成草案中'
    case 'critic':
      return '评审中'
    case 'synthesis':
      return '综合输出中'
    default:
      return null
  }
}

export function detectGenerationFallbackSummary(summary: string | null | undefined): boolean {
  if (!summary) {
    return false
  }

  return /回退|fallback/i.test(summary)
}

export function formatPreviewPageType(pageType: string | null | undefined): string {
  const normalizedPageType = pageType?.trim()

  if (!normalizedPageType) {
    return '未标注'
  }

  return normalizedPageType.replace(/[_-]+/g, ' ')
}

export function formatPreviewUpdatedAt(updatedAt: string | null | undefined): string {
  if (!updatedAt) {
    return '等待生成'
  }

  const date = new Date(updatedAt)

  if (Number.isNaN(date.getTime())) {
    return '时间未知'
  }

  return new Intl.DateTimeFormat('zh-CN', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: '2-digit'
  }).format(date)
}

export function resolvePreviewPageStatus(options: {
  generatedPage: ProjectPage | null
  projectStatus: ProjectStatus | null | undefined
  realtimeState: Pick<RealtimePageGenerationState, 'status'> | null
}): PreviewPageStatus {
  if (options.realtimeState?.status) {
    return options.realtimeState.status
  }

  if (options.generatedPage?.status === 'confirmed') {
    return 'confirmed'
  }

  if (options.generatedPage && isGeneratedProjectPageStatus(options.generatedPage.status)) {
    return 'generated'
  }

  if (options.generatedPage?.status === 'generating') {
    return 'generating'
  }

  if (options.projectStatus === 'generating') {
    return 'pending'
  }

  return 'pending'
}

export function resolvePreviewPageTitle(options: {
  generatedPage: ProjectPage | null
  outlinePageTitle: string | null | undefined
  pageNumber: number
  realtimeTitle: string | null
}): string {
  const title = normalizePreviewText(options.realtimeTitle)
    || normalizePreviewText(options.generatedPage?.title)
    || normalizePreviewText(options.outlinePageTitle)

  return title || `第 ${options.pageNumber} 页`
}

export function isGeneratedProjectPageStatus(status: PageStatus): boolean {
  return status === 'generated' || status === 'optimizing' || status === 'confirmed'
}

export function normalizePreviewText(value: string | null | undefined): string | null {
  const normalizedValue = value?.trim()
  return normalizedValue ? normalizedValue : null
}

export function formatPreviewVersionHistoryLabel(selection: PreviewVersionSelection | null | undefined): string | null {
  if (!selection) {
    return null
  }

  return `历史预览 · v${selection.sourceVersion}`
}
