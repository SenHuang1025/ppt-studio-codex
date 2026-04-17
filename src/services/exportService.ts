import { getApiBaseUrl } from './api'
import type { ProjectExportTask } from '@/types/export'

function encodeProjectExportPath(projectId: string): string {
  return `/projects/${encodeURIComponent(projectId)}/export`
}

function encodeProjectExportTaskPath(projectId: string, taskId: string): string {
  return `${encodeProjectExportPath(projectId)}/tasks/${encodeURIComponent(taskId)}`
}

export const projectExportService = {
  async startPdfExport(projectId: string): Promise<ProjectExportTask> {
    return requestJson<ProjectExportTask>(`${encodeProjectExportPath(projectId)}/pdf`, {
      method: 'POST'
    })
  },

  async getTask(projectId: string, taskId: string): Promise<ProjectExportTask> {
    return requestJson<ProjectExportTask>(encodeProjectExportTaskPath(projectId, taskId), {
      method: 'GET'
    })
  },

  async downloadArtifact(projectId: string, task: Pick<ProjectExportTask, 'artifact_name' | 'download_url' | 'id'>): Promise<void> {
    const baseUrl = await getApiBaseUrl()
    const requestUrl = new URL(
      trimLeadingSlash(task.download_url || `${encodeProjectExportTaskPath(projectId, task.id)}/download`),
      ensureTrailingSlash(baseUrl)
    )
    const response = await fetch(requestUrl, {
      method: 'GET'
    })

    if (!response.ok) {
      throw new Error(await resolveDownloadErrorMessage(response))
    }

    const blob = await response.blob()
    const fileName = resolveDownloadFileName(response.headers, task.artifact_name || `project-export-${task.id}.pdf`)
    triggerBlobDownload(blob, fileName)
  }
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const baseUrl = await getApiBaseUrl()
  const requestUrl = new URL(trimLeadingSlash(path), ensureTrailingSlash(baseUrl))
  const response = await fetch(requestUrl, {
    ...init,
    headers: {
      accept: 'application/json',
      ...(init.headers || {})
    }
  })

  const payload = await parseJsonResponse(response)
  if (!response.ok) {
    throw new Error(extractErrorMessage(payload) || `导出请求失败（HTTP ${response.status}）。`)
  }

  return payload as T
}

async function parseJsonResponse(response: Response): Promise<unknown> {
  const text = await response.text()

  if (!text.trim()) {
    return null
  }

  try {
    return JSON.parse(text) as unknown
  } catch {
    return { detail: text }
  }
}

function extractErrorMessage(payload: unknown): string | null {
  if (typeof payload === 'string') {
    return payload.trim() || null
  }

  if (!payload || typeof payload !== 'object') {
    return null
  }

  const candidate = payload as Record<string, unknown>
  if (typeof candidate.detail === 'string' && candidate.detail.trim()) {
    return candidate.detail.trim()
  }
  if (typeof candidate.message === 'string' && candidate.message.trim()) {
    return candidate.message.trim()
  }

  return null
}

async function resolveDownloadErrorMessage(response: Response): Promise<string> {
  return extractErrorMessage(await parseJsonResponse(response))
    || `导出文件下载失败（HTTP ${response.status}）。`
}

function resolveDownloadFileName(headers: Headers, fallback: string): string {
  const contentDisposition = headers.get('content-disposition') || ''
  const utf8Match = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1])
  }

  const asciiMatch = contentDisposition.match(/filename\s*=\s*"([^"]+)"/i) || contentDisposition.match(/filename\s*=\s*([^;]+)/i)
  if (asciiMatch?.[1]) {
    return asciiMatch[1].trim()
  }

  return fallback
}

function triggerBlobDownload(blob: Blob, fileName: string): void {
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')

  anchor.href = objectUrl
  anchor.download = fileName
  anchor.style.display = 'none'
  document.body.append(anchor)
  anchor.click()
  anchor.remove()

  window.setTimeout(() => {
    URL.revokeObjectURL(objectUrl)
  }, 0)
}

function ensureTrailingSlash(value: string): string {
  return value.endsWith('/') ? value : `${value}/`
}

function trimLeadingSlash(value: string): string {
  return value.replace(/^\/+/, '')
}
