import { access } from 'node:fs/promises'
import { execFile, spawn } from 'node:child_process'
import net from 'node:net'
import path from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { promisify } from 'node:util'
import type { ChildProcessWithoutNullStreams } from 'node:child_process'
import { app } from 'electron'

const execFileAsync = promisify(execFile)

const PREVIEW_HOST = '127.0.0.1'
const PREVIEW_PORT = 18921
const START_TIMEOUT_MS = 25_000
const HEALTH_CHECK_INTERVAL_MS = 500
const STOP_TIMEOUT_MS = 5_000
const PREVIEW_HEALTH_MARKER = 'ppt-studio-preview-service'

export class PreviewServerManager {
  private process: ChildProcessWithoutNullStreams | null = null
  private startPromise: Promise<void> | null = null
  private stopPromise: Promise<void> | null = null
  private usingExistingService = false
  private restartAttempts = 0
  private readonly baseUrl = `http://${PREVIEW_HOST}:${PREVIEW_PORT}`

  public async start(): Promise<void> {
    if (this.isRunning()) {
      return
    }

    if (this.startPromise) {
      return this.startPromise
    }

    const existingServiceMode = await this.resolveExistingServiceMode()

    if (existingServiceMode === 'reuse') {
      this.usingExistingService = true
      this.log('info', `Reusing existing preview server at ${this.baseUrl}`)
      return
    }

    const previewDirectory = this.resolvePreviewDirectory()
    await Promise.all([access(previewDirectory), access(this.getSlidesDir())])
    this.usingExistingService = false

    this.startPromise = new Promise<void>((resolve, reject) => {
      const previewCommand = this.resolvePreviewCommand()
      const child = spawn(previewCommand.command, previewCommand.args, {
        cwd: previewDirectory,
        env: {
          ...process.env
        },
        stdio: 'pipe',
        windowsHide: true,
        detached: process.platform !== 'win32'
      })

      this.process = child

      child.stdout.on('data', (chunk: Buffer) => {
        this.log('info', chunk.toString())
      })

      child.stderr.on('data', (chunk: Buffer) => {
        this.log('error', chunk.toString())
      })

      child.once('spawn', () => {
        this.log('info', `Started preview server from ${previewDirectory} (pid=${child.pid ?? 'unknown'})`)
        resolve()
      })

      child.once('error', (error: Error) => {
        this.log('error', `Failed to start preview server: ${error.message}`)
        this.process = null
        reject(error)
      })

      child.on('exit', (code: number | null, signal: NodeJS.Signals | null) => {
        const message = `Preview server exited (code=${code ?? 'null'}, signal=${signal ?? 'null'})`

        if (code === 0 || signal === 'SIGTERM' || signal === 'SIGINT') {
          this.log('info', message)
        } else {
          this.log('warn', message)
        }

        this.process = null
        if (!this.usingExistingService && code !== 0 && signal !== 'SIGTERM' && signal !== 'SIGINT') {
          void this.recover().catch((error: unknown) => {
            const message = error instanceof Error ? error.message : String(error)
            this.log('error', `Automatic preview server recovery failed: ${message}`)
          })
        }
      })
    }).finally(() => {
      this.startPromise = null
    })

    return this.startPromise
  }

  public async stop(): Promise<void> {
    if (this.stopPromise) {
      return this.stopPromise
    }

    const child = this.process

    if (!child || child.exitCode !== null) {
      this.usingExistingService = false
      this.process = null
      return
    }

    this.stopPromise = this.stopProcess(child).finally(() => {
      this.stopPromise = null
      this.process = null
      this.usingExistingService = false
    })

    return this.stopPromise
  }

  public async waitForReady(timeoutMs = START_TIMEOUT_MS): Promise<void> {
    const deadline = Date.now() + timeoutMs

    while (Date.now() < deadline) {
      if (!this.isRunning() && !this.startPromise) {
        throw new Error('Preview server exited before becoming ready.')
      }

      try {
        if (await this.checkExistingServiceHealth()) {
          this.log('info', `Preview server is ready at ${this.baseUrl}/`)
          return
        }
      } catch {
        // Ignore transient connection failures while the preview server is still starting.
      }

      await delay(HEALTH_CHECK_INTERVAL_MS)
    }

    const error = new Error(`Preview server health check timed out after ${timeoutMs}ms.`)
    this.log('error', error.message)
    throw error
  }

  public getBaseUrl(): string {
    return this.baseUrl
  }

  public getSlidesDir(): string {
    return path.join(this.resolvePreviewDirectory(), 'src', 'slides')
  }

  public getThemeFile(): string {
    return path.join(this.resolvePreviewDirectory(), 'src', 'theme', 'variables.css')
  }

  public getStatus(): { baseUrl: string; restartAttempts: number; running: boolean; usingExistingService: boolean } {
    return {
      baseUrl: this.baseUrl,
      restartAttempts: this.restartAttempts,
      running: this.isRunning(),
      usingExistingService: this.usingExistingService
    }
  }

  public async recover(): Promise<void> {
    this.restartAttempts += 1
    await this.stop().catch(() => undefined)
    await this.start()
    await this.waitForReady()
  }

  private async stopProcess(child: ChildProcessWithoutNullStreams): Promise<void> {
    const pid = child.pid

    if (!pid) {
      return
    }

    try {
      if (process.platform === 'win32') {
        await execFileAsync('taskkill', ['/pid', String(pid), '/t'])
      } else {
        process.kill(-pid, 'SIGTERM')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      this.log('warn', `Initial preview server shutdown signal failed: ${message}`)
    }

    const exited = await this.waitForExit(child, STOP_TIMEOUT_MS)

    if (exited) {
      return
    }

    try {
      if (process.platform === 'win32') {
        await execFileAsync('taskkill', ['/pid', String(pid), '/t', '/f'])
      } else {
        process.kill(-pid, 'SIGKILL')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      this.log('error', `Failed to force stop preview server: ${message}`)
      throw error
    }

    const forceExited = await this.waitForExit(child, STOP_TIMEOUT_MS)

    if (!forceExited) {
      const error = new Error('Preview server did not exit after forced shutdown.')
      this.log('error', error.message)
      throw error
    }
  }

  private async waitForExit(child: ChildProcessWithoutNullStreams, timeoutMs: number): Promise<boolean> {
    if (child.exitCode !== null) {
      return true
    }

    return new Promise<boolean>((resolve) => {
      const timeout = setTimeout(() => {
        cleanup()
        resolve(false)
      }, timeoutMs)

      const handleExit = () => {
        cleanup()
        resolve(true)
      }

      const cleanup = () => {
        clearTimeout(timeout)
        child.off('exit', handleExit)
      }

      child.once('exit', handleExit)
    })
  }

  private isRunning(): boolean {
    return this.usingExistingService || (this.process !== null && this.process.exitCode === null)
  }

  private async resolveExistingServiceMode(): Promise<'spawn' | 'reuse'> {
    const isPortInUse = await this.checkPortInUse()

    if (!isPortInUse) {
      return 'spawn'
    }

    const isHealthyService = await this.checkExistingServiceHealth()

    if (isHealthyService) {
      return 'reuse'
    }

    const error = new Error(
      `Preview server port ${PREVIEW_PORT} is already in use, but the existing service did not pass the PPT Studio preview health check. Stop the conflicting process before launching Electron.`
    )
    this.log('error', error.message)
    throw error
  }

  private async checkPortInUse(): Promise<boolean> {
    return new Promise<boolean>((resolve, reject) => {
      const socket = net.createConnection({
        host: PREVIEW_HOST,
        port: PREVIEW_PORT
      })

      const cleanup = () => {
        socket.removeAllListeners()
        socket.destroy()
      }

      socket.once('connect', () => {
        cleanup()
        resolve(true)
      })

      socket.once('error', (error: NodeJS.ErrnoException) => {
        cleanup()

        if (error.code === 'ECONNREFUSED') {
          resolve(false)
          return
        }

        reject(error)
      })

      socket.setTimeout(1_000, () => {
        cleanup()
        resolve(true)
      })
    })
  }

  private async checkExistingServiceHealth(): Promise<boolean> {
    try {
      const response = await fetch(new URL('/', this.baseUrl), {
        signal: AbortSignal.timeout(1_500)
      })

      if (!response.ok) {
        return false
      }

      const contentType = response.headers.get('content-type') ?? ''

      if (!contentType.includes('text/html')) {
        return false
      }

      const payload = await response.text()
      return payload.includes(PREVIEW_HEALTH_MARKER)
    } catch {
      return false
    }
  }

  private resolvePreviewDirectory(): string {
    if (app.isPackaged) {
      return path.join(process.resourcesPath, 'ppt-preview-server')
    }

    return path.join(app.getAppPath(), 'ppt-preview-server')
  }

  private resolvePreviewCommand(): { command: string; args: string[] } {
    if (process.platform === 'win32') {
      return {
        command: process.env.ComSpec ?? process.env.COMSPEC ?? 'cmd.exe',
        args: ['/d', '/s', '/c', 'pnpm dev']
      }
    }

    return {
      command: 'pnpm',
      args: ['dev']
    }
  }

  private log(level: 'info' | 'warn' | 'error', message: string): void {
    const normalizedMessage = message.trim()

    if (!normalizedMessage) {
      return
    }

    const formattedMessage = `[PreviewServer] ${normalizedMessage}`

    if (level === 'error') {
      console.error(formattedMessage)
      return
    }

    if (level === 'warn') {
      console.warn(formattedMessage)
      return
    }

    console.log(formattedMessage)
  }
}
