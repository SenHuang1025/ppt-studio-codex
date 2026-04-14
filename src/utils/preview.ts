import type { LocationQueryValue } from 'vue-router'
import type { PreviewPageStatus } from '@/types/preview'

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
    case 'generated':
      return '已生成'
    case 'generating':
      return '生成中'
    default:
      return '待生成'
  }
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
