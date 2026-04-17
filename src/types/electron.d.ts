export interface PptStudioRuntime {
  readonly platform: NodeJS.Platform
  readonly versions: Readonly<{
    chrome: string
    electron: string
    node: string
  }>
  clearApiKey: () => Promise<void>
  getApiKey: () => Promise<string | null>
  getPreviewBaseUrl: () => Promise<string>
  getPreviewServerStatus: () => Promise<{
    baseUrl: string
    restartAttempts: number
    running: boolean
    usingExistingService: boolean
  }>
  getPreviewSlidesDir: () => Promise<string>
  getPythonBaseUrl: () => Promise<string>
  getPythonSidecarStatus: () => Promise<{
    baseUrl: string
    restartAttempts: number
    running: boolean
    usingExistingService: boolean
  }>
  recoverPreviewServer: () => Promise<void>
  recoverPythonSidecar: () => Promise<void>
  saveApiKey: (apiKey: string) => Promise<void>
}

declare global {
  interface Window {
    pptStudio: PptStudioRuntime
  }
}

export {}
