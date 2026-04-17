import { createDiscreteApi } from 'naive-ui'
import type { Router } from 'vue-router'
import type { ApiError } from './api'

const { message } = createDiscreteApi(['message'])

let appRouter: Router | null = null
let lastToastAt = 0
let lastToastMessage = ''

export function installErrorHandling(options: { router: Router }): void {
  appRouter = options.router

  window.addEventListener('error', (event) => {
    reportGlobalError(event.error ?? event.message, {
      context: 'window.error',
      notify: true
    })
  })

  window.addEventListener('unhandledrejection', (event) => {
    reportGlobalError(event.reason, {
      context: 'window.unhandledrejection',
      notify: true
    })
  })
}

export function reportGlobalError(
  error: unknown,
  options?: {
    context?: string
    notify?: boolean
  }
): string {
  const resolvedMessage = resolveAppErrorMessage(error)
  console.error(`[PPT Studio] ${options?.context ?? 'error'}`, error)

  if (options?.notify) {
    showErrorToast(resolvedMessage)
  }

  if (shouldRedirectToSettings(error)) {
    void appRouter?.push({ name: 'settings' }).catch(() => undefined)
  }

  return resolvedMessage
}

export function showErrorToast(messageText: string): void {
  const normalizedMessage = messageText.trim()
  if (!normalizedMessage) {
    return
  }

  const now = Date.now()
  if (normalizedMessage === lastToastMessage && now - lastToastAt < 1600) {
    return
  }

  lastToastMessage = normalizedMessage
  lastToastAt = now
  message.error(normalizedMessage)
}

export function resolveAppErrorMessage(error: unknown, fallback = '操作失败，请稍后重试。'): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }

  if (typeof error === 'string' && error.trim()) {
    return error.trim()
  }

  return fallback
}

export function shouldRedirectToSettings(error: unknown): boolean {
  const messageText = resolveAppErrorMessage(error).toLowerCase()

  return messageText.includes('api key')
    || messageText.includes('设置页')
    || messageText.includes('invalid api key')
    || messageText.includes('已过期')
}

export function notifyApiError(
  error: unknown,
  options?: {
    fallback?: string
    redirectToSettingsOnAuthError?: boolean
  }
): string {
  const resolvedMessage = resolveAppErrorMessage(error, options?.fallback)
  showErrorToast(resolvedMessage)

  if (options?.redirectToSettingsOnAuthError !== false && shouldRedirectToSettings(error)) {
    void appRouter?.push({ name: 'settings' }).catch(() => undefined)
  }

  return resolvedMessage
}

export function isApiErrorLike(error: unknown): error is ApiError {
  return error instanceof Error && error.name === 'ApiError'
}
