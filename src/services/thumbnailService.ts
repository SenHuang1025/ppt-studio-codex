import { getApiBaseUrl } from './api'

export interface ThumbnailUrlOptions {
  projectId: string
  pageNumber: number
  signature?: string | number | null
}

export async function buildPageThumbnailUrl(options: ThumbnailUrlOptions): Promise<string> {
  const baseUrl = await getApiBaseUrl()
  const url = new URL(
    `projects/${encodeURIComponent(options.projectId)}/pages/${options.pageNumber}/thumbnail`,
    ensureTrailingSlash(baseUrl)
  )

  const normalizedSignature = String(options.signature ?? '').trim()
  if (normalizedSignature) {
    url.searchParams.set('v', normalizedSignature)
  }

  return url.toString()
}

function ensureTrailingSlash(value: string): string {
  return value.endsWith('/') ? value : `${value}/`
}
