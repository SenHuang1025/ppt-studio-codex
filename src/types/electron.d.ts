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
  getPreviewSlidesDir: () => Promise<string>
  getPythonBaseUrl: () => Promise<string>
  saveApiKey: (apiKey: string) => Promise<void>
}

declare global {
  interface Window {
    pptStudio: PptStudioRuntime
  }
}

export {}
