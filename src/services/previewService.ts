let cachedPreviewBaseUrlPromise: Promise<string> | null = null
const PREVIEW_REACHABILITY_TIMEOUT_MS = 1500

export async function getPreviewBaseUrl(forceRefresh = false): Promise<string> {
  if (forceRefresh || cachedPreviewBaseUrlPromise === null) {
    cachedPreviewBaseUrlPromise = resolvePreviewBaseUrl().catch((error: unknown) => {
      cachedPreviewBaseUrlPromise = null
      throw error
    })
  }

  return cachedPreviewBaseUrlPromise
}

export function resetPreviewBaseUrlCache(): void {
  cachedPreviewBaseUrlPromise = null
}

export function buildPreviewSlideUrl(baseUrl: string, pageNumber: number): string {
  const normalizedPageNumber = Number.isFinite(pageNumber) ? Math.max(1, Math.floor(pageNumber)) : 1
  return new URL(`slide/${normalizedPageNumber}`, ensureTrailingSlash(baseUrl)).toString()
}

export function buildPreviewVersionUrl(baseUrl: string, pageNumber: number): string {
  const normalizedPageNumber = Number.isFinite(pageNumber) ? Math.max(1, Math.floor(pageNumber)) : 1
  const targetUrl = new URL('version-preview', ensureTrailingSlash(baseUrl))
  targetUrl.searchParams.set('page', String(normalizedPageNumber))
  return targetUrl.toString()
}

export async function ensurePreviewServerReachable(baseUrl: string): Promise<void> {
  try {
    await fetch(ensureTrailingSlash(baseUrl), {
      cache: 'no-store',
      mode: 'no-cors',
      signal: AbortSignal.timeout(PREVIEW_REACHABILITY_TIMEOUT_MS)
    })
  } catch {
    const runtime = resolveRuntime()
    await runtime.recoverPreviewServer().catch(() => undefined)
    throw new Error('预览服务连接失败，Electron 已尝试恢复 preview server。')
  }
}

async function resolvePreviewBaseUrl(): Promise<string> {
  const runtime = resolveRuntime()
  let baseUrl = ''

  try {
    baseUrl = normalizeUrl(await runtime.getPreviewBaseUrl())
  } catch (error: unknown) {
    await runtime.recoverPreviewServer().catch(() => undefined)
    throw error
  }

  if (!baseUrl) {
    throw new Error('Electron runtime returned an empty preview server URL.')
  }

  return baseUrl
}

function resolveRuntime(): Window['pptStudio'] {
  if (typeof window === 'undefined' || !window.pptStudio) {
    throw new Error('PPT Studio Electron runtime is unavailable in the current context.')
  }

  return window.pptStudio
}

function ensureTrailingSlash(value: string): string {
  return value.endsWith('/') ? value : `${value}/`
}

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, '')
}
