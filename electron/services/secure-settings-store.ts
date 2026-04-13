import { mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { app, safeStorage } from 'electron'

interface SecureSettingsState {
  apiKey?: string
}

export class SecureSettingsStore {
  public async getApiKey(): Promise<string | null> {
    const state = await this.readState()
    const encryptedApiKey = state.apiKey

    if (!encryptedApiKey) {
      return null
    }

    this.ensureEncryptionAvailable()

    try {
      return safeStorage.decryptString(Buffer.from(encryptedApiKey, 'base64'))
    } catch (error: unknown) {
      throw new Error('Failed to decrypt the stored API key.', {
        cause: error
      })
    }
  }

  public async setApiKey(apiKey: string): Promise<void> {
    const normalizedApiKey = apiKey.trim()

    if (!normalizedApiKey) {
      await this.clearApiKey()
      return
    }

    this.ensureEncryptionAvailable()

    const encryptedApiKey = safeStorage.encryptString(normalizedApiKey).toString('base64')
    await this.writeState({ apiKey: encryptedApiKey })
  }

  public async clearApiKey(): Promise<void> {
    const state = await this.readState()

    if (!state.apiKey) {
      return
    }

    delete state.apiKey

    if (Object.keys(state).length === 0) {
      await rm(this.getStorePath(), {
        force: true
      })
      return
    }

    await this.writeState(state)
  }

  private ensureEncryptionAvailable(): void {
    if (!safeStorage.isEncryptionAvailable()) {
      throw new Error('Electron safeStorage is not available on this system.')
    }
  }

  private getStorePath(): string {
    return path.join(app.getPath('userData'), 'secure-settings.json')
  }

  private async readState(): Promise<SecureSettingsState> {
    try {
      const rawContent = await readFile(this.getStorePath(), 'utf8')
      const parsed = JSON.parse(rawContent) as SecureSettingsState

      if (!parsed || typeof parsed !== 'object') {
        return {}
      }

      return {
        apiKey: typeof parsed.apiKey === 'string' ? parsed.apiKey : undefined
      }
    } catch (error: unknown) {
      if (isFileMissingError(error)) {
        return {}
      }

      throw new Error('Failed to read the secure settings store.', {
        cause: error
      })
    }
  }

  private async writeState(state: SecureSettingsState): Promise<void> {
    const storePath = this.getStorePath()

    await mkdir(path.dirname(storePath), { recursive: true })

    try {
      await writeFile(storePath, JSON.stringify(state, null, 2), 'utf8')
    } catch (error: unknown) {
      throw new Error('Failed to write the secure settings store.', {
        cause: error
      })
    }
  }
}

function isFileMissingError(error: unknown): error is NodeJS.ErrnoException {
  return Boolean(error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT')
}
