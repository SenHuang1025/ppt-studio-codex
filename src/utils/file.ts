import type { FileParseStatus } from '@/types/file'
import { UPLOAD_FILE_EXTENSIONS } from '@/types/file'

export interface FileParseStatusMeta {
  label: string
  tone: 'error' | 'neutral' | 'processing' | 'success'
}

export const FILE_PARSE_STATUS_META: Record<FileParseStatus, FileParseStatusMeta> = {
  failed: {
    label: 'failed',
    tone: 'error'
  },
  parsed: {
    label: 'parsed',
    tone: 'success'
  },
  parsing: {
    label: 'parsing',
    tone: 'processing'
  },
  pending: {
    label: 'pending',
    tone: 'neutral'
  }
}

export const SUPPORTED_UPLOAD_EXTENSION_SET = new Set<string>(UPLOAD_FILE_EXTENSIONS)

export function formatFileSize(bytes: number | null | undefined): string {
  if (typeof bytes !== 'number' || !Number.isFinite(bytes) || bytes < 0) {
    return '大小未知'
  }

  const units = ['B', 'KB', 'MB', 'GB'] as const
  let unitIndex = 0
  let value = bytes

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }

  if (unitIndex === 0) {
    return `${Math.round(value)} ${units[unitIndex]}`
  }

  const fractionDigits = value >= 10 ? 1 : 2
  return `${value.toFixed(fractionDigits)} ${units[unitIndex]}`
}

export function getFileExtension(fileName: string): string | null {
  const segments = fileName.trim().toLowerCase().split('.')
  const extension = segments.length > 1 ? segments.at(-1) : null

  return extension && extension.trim() ? extension.trim() : null
}

export function formatUploadedFileType(fileType: string): string {
  const normalized = fileType.trim().toUpperCase()
  return normalized || 'FILE'
}
