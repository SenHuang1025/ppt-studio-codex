export type ApiQueryPrimitive = string | number | boolean | null | undefined
export type ApiQueryParams = object
export type ApiMethod = 'DELETE' | 'GET' | 'PATCH' | 'POST' | 'PUT'
export type ApiJsonBody = object
export type ApiRequestBody = ApiJsonBody | BodyInit | null

export interface ApiRequestOptions {
  body?: ApiRequestBody
  headers?: HeadersInit
  method?: ApiMethod
  params?: ApiQueryParams
  signal?: AbortSignal
}

export interface ApiRequestConfig extends ApiRequestOptions {
  path: string
}

export interface ApiRequestContext {
  baseUrl: string
  config: ApiRequestConfig
  init: RequestInit
  url: string
}

export interface ApiResponseContext<TData = unknown> extends ApiRequestContext {
  data: TData
  response: Response
}

export interface BackendErrorPayload {
  detail?: string | unknown[]
  error?: string
}

type ApiInterceptor<TContext> = (context: TContext) => Promise<TContext> | TContext

const API_PREFIX = '/api'

let cachedApiBaseUrlPromise: Promise<string> | null = null

class ApiInterceptorManager<TContext> {
  private readonly handlers = new Map<number, ApiInterceptor<TContext>>()
  private nextId = 0

  public use(handler: ApiInterceptor<TContext>): number {
    const interceptorId = this.nextId
    this.handlers.set(interceptorId, handler)
    this.nextId += 1
    return interceptorId
  }

  public eject(interceptorId: number): void {
    this.handlers.delete(interceptorId)
  }

  public async run(context: TContext): Promise<TContext> {
    let nextContext = context

    for (const handler of this.handlers.values()) {
      nextContext = await handler(nextContext)
    }

    return nextContext
  }
}

export class ApiError extends Error {
  public readonly status: number | null
  public readonly url: string | null
  public readonly detail: unknown

  public constructor(
    message: string,
    options?: {
      cause?: unknown
      detail?: unknown
      status?: number | null
      url?: string | null
    }
  ) {
    super(message, options?.cause ? { cause: options.cause } : undefined)
    this.name = 'ApiError'
    this.status = options?.status ?? null
    this.url = options?.url ?? null
    this.detail = options?.detail
  }
}

class ApiClient {
  public readonly interceptors = {
    request: new ApiInterceptorManager<ApiRequestContext>(),
    response: new ApiInterceptorManager<ApiResponseContext<unknown>>()
  }

  public async request<TResponse>(config: ApiRequestConfig): Promise<TResponse> {
    const baseUrl = await getApiBaseUrl()
    const url = buildRequestUrl(baseUrl, config.path, config.params)
    const requestContext = await this.interceptors.request.run({
      baseUrl,
      config,
      init: createRequestInit(config),
      url
    })

    let response: Response

    try {
      response = await fetch(requestContext.url, requestContext.init)
    } catch (error: unknown) {
      const runtime = resolvePptStudioRuntime()
      await runtime?.recoverPythonSidecar().catch(() => undefined)

      if (error instanceof ApiError) {
        throw error
      }

      throw new ApiError('无法连接到 PPT Studio 后端服务，Electron 已尝试恢复 Python sidecar。', {
        cause: error,
        detail: error,
        url: requestContext.url
      })
    }

    const data = await parseResponseBody(response)

    if (!response.ok) {
      throw createResponseError(response, requestContext.url, data)
    }

    const responseContext = await this.interceptors.response.run({
      ...requestContext,
      data,
      response
    })

    return responseContext.data as TResponse
  }

  public get<TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method'>): Promise<TResponse> {
    return this.request<TResponse>({
      ...options,
      method: 'GET',
      path
    })
  }

  public post<TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method'>): Promise<TResponse> {
    return this.request<TResponse>({
      ...options,
      method: 'POST',
      path
    })
  }

  public patch<TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method'>): Promise<TResponse> {
    return this.request<TResponse>({
      ...options,
      method: 'PATCH',
      path
    })
  }

  public put<TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method'>): Promise<TResponse> {
    return this.request<TResponse>({
      ...options,
      method: 'PUT',
      path
    })
  }

  public delete<TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method'>): Promise<TResponse> {
    return this.request<TResponse>({
      ...options,
      method: 'DELETE',
      path
    })
  }
}

export const apiClient = new ApiClient()

export async function getApiBaseUrl(forceRefresh = false): Promise<string> {
  if (forceRefresh || cachedApiBaseUrlPromise === null) {
    cachedApiBaseUrlPromise = resolveApiBaseUrl().catch((error: unknown) => {
      cachedApiBaseUrlPromise = null
      throw error
    })
  }

  return cachedApiBaseUrlPromise
}

export function resetApiBaseUrlCache(): void {
  cachedApiBaseUrlPromise = null
}

async function resolveApiBaseUrl(): Promise<string> {
  const runtime = resolvePptStudioRuntime()

  if (!runtime) {
    throw new ApiError('PPT Studio Electron runtime is unavailable in the current context.')
  }

  try {
    const pythonBaseUrl = normalizeUrl(await runtime.getPythonBaseUrl())

    if (!pythonBaseUrl) {
      throw new Error('Electron runtime returned an empty Python base URL.')
    }

    return new URL(trimLeadingSlash(API_PREFIX), ensureTrailingSlash(pythonBaseUrl)).toString().replace(/\/$/, '')
  } catch (error: unknown) {
    await runtime.recoverPythonSidecar().catch(() => undefined)
    if (error instanceof ApiError) {
      throw error
    }

    throw new ApiError('无法连接 Python 后端，Electron 已尝试恢复 sidecar，请稍后重试。', {
      cause: error,
      detail: error
    })
  }
}

function resolvePptStudioRuntime(): Window['pptStudio'] | null {
  if (typeof window === 'undefined') {
    return null
  }

  if (!('pptStudio' in window)) {
    return null
  }

  return window.pptStudio
}

function createRequestInit(config: ApiRequestConfig): RequestInit {
  const headers = new Headers(config.headers)
  const method = config.method ?? 'GET'
  const body = serializeRequestBody(config.body)

  if (!headers.has('accept')) {
    headers.set('accept', 'application/json')
  }

  if (isJsonBody(config.body) && !headers.has('content-type')) {
    headers.set('content-type', 'application/json')
  }

  return {
    body,
    headers,
    method,
    signal: config.signal
  }
}

function serializeRequestBody(body: ApiRequestBody | undefined): BodyInit | undefined {
  if (body === undefined || body === null) {
    return undefined
  }

  if (isJsonBody(body)) {
    return JSON.stringify(body)
  }

  return body
}

function isJsonBody(body: ApiRequestBody | undefined): body is ApiJsonBody {
  if (body === null || body === undefined) {
    return false
  }

  if (Array.isArray(body)) {
    return true
  }

  if (typeof body !== 'object') {
    return false
  }

  return !(
    body instanceof ArrayBuffer ||
    body instanceof Blob ||
    body instanceof FormData ||
    body instanceof ReadableStream ||
    body instanceof URLSearchParams ||
    ArrayBuffer.isView(body)
  )
}

function buildRequestUrl(baseUrl: string, path: string, params?: ApiQueryParams): string {
  const url = new URL(trimLeadingSlash(path), ensureTrailingSlash(baseUrl))

  if (params) {
    appendQueryParams(url.searchParams, params)
  }

  return url.toString()
}

function appendQueryParams(searchParams: URLSearchParams, params: ApiQueryParams): void {
  for (const [key, rawValue] of Object.entries(params)) {
    appendQueryValue(searchParams, key, rawValue)
  }
}

function appendQueryValue(searchParams: URLSearchParams, key: string, value: unknown): void {
  if (Array.isArray(value)) {
    for (const item of value) {
      appendSingleQueryValue(searchParams, key, item)
    }

    return
  }

  appendSingleQueryValue(searchParams, key, value)
}

function appendSingleQueryValue(searchParams: URLSearchParams, key: string, value: unknown): void {
  if (value === undefined || value === null) {
    return
  }

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    searchParams.append(key, String(value))
  }
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204 || response.status === 205) {
    return undefined
  }

  const text = await response.text()

  if (!text) {
    return undefined
  }

  if (isJsonContentType(response.headers.get('content-type'))) {
    try {
      return JSON.parse(text) as unknown
    } catch (error: unknown) {
      throw new ApiError('Received an invalid JSON response from the PPT Studio backend.', {
        cause: error,
        detail: text,
        status: response.status,
        url: response.url || null
      })
    }
  }

  return text
}

function isJsonContentType(contentType: string | null): boolean {
  if (!contentType) {
    return false
  }

  const normalizedContentType = contentType.toLowerCase()
  return normalizedContentType.includes('application/json') || normalizedContentType.includes('+json')
}

function createResponseError(response: Response, url: string, detail: unknown): ApiError {
  const message =
    extractErrorMessage(detail) ??
    `Backend request failed with status ${response.status}${response.statusText ? ` ${response.statusText}` : ''}.`

  return new ApiError(message, {
    detail,
    status: response.status,
    url
  })
}

function extractErrorMessage(detail: unknown): string | null {
  if (typeof detail === 'string') {
    const message = detail.trim()
    return message || null
  }

  if (!detail || typeof detail !== 'object') {
    return null
  }

  if ('message' in detail && typeof detail.message === 'string' && detail.message.trim()) {
    return detail.message.trim()
  }

  if ('error' in detail && typeof detail.error === 'string' && detail.error.trim()) {
    return detail.error.trim()
  }

  if ('detail' in detail) {
    const nestedDetail = detail.detail

    if (typeof nestedDetail === 'string' && nestedDetail.trim()) {
      return nestedDetail.trim()
    }

    if (Array.isArray(nestedDetail)) {
      const messages = nestedDetail
        .map((item) => {
          if (!item || typeof item !== 'object' || !('msg' in item) || typeof item.msg !== 'string') {
            return null
          }

          const message = item.msg.trim()
          return message || null
        })
        .filter((message): message is string => message !== null)

      if (messages.length > 0) {
        return messages.join('; ')
      }
    }
  }

  return null
}

export function isBackendErrorPayload(detail: unknown): detail is BackendErrorPayload {
  if (!detail || typeof detail !== 'object') {
    return false
  }

  return 'error' in detail || 'detail' in detail
}

function ensureTrailingSlash(value: string): string {
  return value.endsWith('/') ? value : `${value}/`
}

function trimLeadingSlash(value: string): string {
  return value.replace(/^\/+/, '')
}

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, '')
}
