import { execFile, spawn } from 'node:child_process'
import net from 'node:net'
import path from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { promisify } from 'node:util'
import type { ChildProcessWithoutNullStreams } from 'node:child_process'
import { app } from 'electron'

const execFileAsync = promisify(execFile)

const PYTHON_HOST = '127.0.0.1'
const PYTHON_PORT = 18922
const START_TIMEOUT_MS = 30_000
const HEALTH_CHECK_INTERVAL_MS = 500
const STOP_TIMEOUT_MS = 5_000

interface PythonSidecarOptions {
  extraEnv?: Record<string, string | undefined>
}

export class PythonSidecar {
  private process: ChildProcessWithoutNullStreams | null = null
  private startPromise: Promise<void> | null = null
  private stopPromise: Promise<void> | null = null
  private usingExistingService = false
  private restartAttempts = 0
  private readonly baseUrl = `http://${PYTHON_HOST}:${PYTHON_PORT}`

  public constructor(private readonly options: PythonSidecarOptions = {}) {}

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
      this.log('info', `Reusing existing Python sidecar at ${this.baseUrl}`)
      return
    }

    const backendDirectory = this.resolveBackendDirectory()
    this.usingExistingService = false

    this.startPromise = new Promise<void>((resolve, reject) => {
      const child = spawn('uv', ['run', 'fastapi', 'dev', 'app/main.py', '--port', String(PYTHON_PORT)], {
        cwd: backendDirectory,
        env: {
          ...process.env,
          ...this.options.extraEnv,
          PPT_STUDIO_ENV: 'development',
          PPT_STUDIO_HOST: PYTHON_HOST,
          PPT_STUDIO_PORT: String(PYTHON_PORT),
          PYTHONIOENCODING: 'utf-8',
          PYTHONUTF8: '1'
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
        this.log('info', `Started Python sidecar from ${backendDirectory} (pid=${child.pid ?? 'unknown'})`)
        resolve()
      })

      child.once('error', (error: Error) => {
        this.log('error', `Failed to start Python sidecar: ${error.message}`)
        this.process = null
        reject(error)
      })

      child.on('exit', (code: number | null, signal: NodeJS.Signals | null) => {
        const message = `Python sidecar exited (code=${code ?? 'null'}, signal=${signal ?? 'null'})`

        if (code === 0 || signal === 'SIGTERM' || signal === 'SIGINT') {
          this.log('info', message)
        } else {
          this.log('warn', message)
        }

        this.process = null
        if (!this.usingExistingService && code !== 0 && signal !== 'SIGTERM' && signal !== 'SIGINT') {
          void this.recover().catch((error: unknown) => {
            const message = error instanceof Error ? error.message : String(error)
            this.log('error', `Automatic Python sidecar recovery failed: ${message}`)
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
    const healthUrl = new URL('/health', this.baseUrl).toString()

    while (Date.now() < deadline) {
      if (!this.isRunning() && !this.startPromise) {
        throw new Error('Python sidecar exited before becoming ready.')
      }

      try {
        const response = await fetch(healthUrl, {
          signal: AbortSignal.timeout(1_000)
        })

        if (response.ok) {
          const payload = (await response.json()) as { status?: string }

          if (payload.status === 'ok') {
            this.log('info', `Python sidecar is ready at ${healthUrl}`)
            return
          }
        }
      } catch {
        // Ignore transient connection failures while the backend is still starting.
      }

      await delay(HEALTH_CHECK_INTERVAL_MS)
    }

    const error = new Error(`Python sidecar health check timed out after ${timeoutMs}ms.`)
    this.log('error', error.message)
    throw error
  }

  public getBaseUrl(): string {
    return this.baseUrl
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
      this.log('warn', `Initial Python sidecar shutdown signal failed: ${message}`)
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
      this.log('error', `Failed to force stop Python sidecar: ${message}`)
      throw error
    }

    const forceExited = await this.waitForExit(child, STOP_TIMEOUT_MS)

    if (!forceExited) {
      const error = new Error('Python sidecar did not exit after forced shutdown.')
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
      `Python sidecar port ${PYTHON_PORT} is already in use, but the existing service did not pass the PPT Studio health check. Stop the conflicting process before launching Electron.`
    )
    this.log('error', error.message)
    throw error
  }

  private async checkPortInUse(): Promise<boolean> {
    return new Promise<boolean>((resolve, reject) => {
      const socket = net.createConnection({
        host: PYTHON_HOST,
        port: PYTHON_PORT
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
      const response = await fetch(new URL('/health', this.baseUrl), {
        signal: AbortSignal.timeout(1_500)
      })

      if (!response.ok) {
        return false
      }

      const payload = (await response.json()) as { status?: string }
      return payload.status === 'ok'
    } catch {
      return false
    }
  }

  private resolveBackendDirectory(): string {
    if (app.isPackaged) {
      return path.join(process.resourcesPath, 'python-backend')
    }

    return path.join(app.getAppPath(), 'python-backend')
  }

  private log(level: 'info' | 'warn' | 'error', message: string): void {
    const normalizedMessage = message.trim()

    if (!normalizedMessage) {
      return
    }

    const formattedMessage = `[PythonSidecar] ${normalizedMessage}`

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
