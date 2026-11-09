export type SaveState = 'saved' | 'pending' | 'saving' | 'error'

export interface StorageLike {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

export interface SaveQueueOptions {
  delay: number
  retryDelay: number
  /** Puffer für ungespeicherte Änderungen, z. B. localStorage – überlebt Reload und Verbindungsabbruch. */
  storage?: StorageLike | null
  storageKey?: string
  onState?: (state: SaveState) => void
  /** Endgültig abgelehnte Änderung (4xx): wird verworfen statt endlos wiederholt. */
  onRejected?: (error: unknown) => void
}

type Patch = Record<string, unknown>

function isPermanent(error: unknown): boolean {
  const status = (error as { status?: number })?.status ?? 0
  return status >= 400 && status < 500 && status !== 408 && status !== 429
}

/**
 * Sammelt Änderungen je Schlüssel, speichert sie nach einer Tipp-Pause nacheinander
 * und wiederholt bei Netzwerkfehlern, bis der Server sie angenommen hat.
 */
export class SaveQueue<P extends Patch = Patch> {
  private pending = new Map<string, P>()
  private timer: ReturnType<typeof setTimeout> | undefined
  private running: Promise<void> | null = null
  private _state: SaveState = 'saved'

  constructor(
    private readonly send: (key: string, patch: P) => Promise<void>,
    private readonly options: SaveQueueOptions,
  ) {
    this.restore()
  }

  get state(): SaveState {
    return this._state
  }

  get hasPending(): boolean {
    return this.pending.size > 0
  }

  pendingFor(key: string): P | undefined {
    return this.pending.get(key)
  }

  set(key: string, patch: P): void {
    this.pending.set(key, { ...this.pending.get(key), ...patch })
    this.persist()
    if (this._state !== 'error') this.setState('pending')
    this.schedule(this.options.delay)
  }

  async flush(): Promise<void> {
    clearTimeout(this.timer)
    while (this.running) await this.running
    if (!this.pending.size) return
    this.running = this.drain()
    try {
      await this.running
    } finally {
      this.running = null
    }
  }

  dispose(): void {
    clearTimeout(this.timer)
  }

  private schedule(delay: number) {
    clearTimeout(this.timer)
    this.timer = setTimeout(() => void this.flush(), delay)
  }

  private async drain() {
    this.setState('saving')
    while (this.pending.size) {
      const [key, patch] = this.pending.entries().next().value as [string, P]
      try {
        await this.send(key, patch)
      } catch (error) {
        if (!isPermanent(error)) {
          this.setState('error')
          this.schedule(this.options.retryDelay)
          return
        }
        this.options.onRejected?.(error)
      }
      // Kam während des Sendens eine neuere Änderung dazu, bleibt sie für die nächste Runde stehen.
      if (this.pending.get(key) === patch) this.pending.delete(key)
      this.persist()
    }
    this.setState('saved')
  }

  private setState(state: SaveState) {
    this._state = state
    this.options.onState?.(state)
  }

  private persist() {
    const { storage, storageKey } = this.options
    if (!storage || !storageKey) return
    try {
      if (this.pending.size) storage.setItem(storageKey, JSON.stringify([...this.pending]))
      else storage.removeItem(storageKey)
    } catch {
      // Speicher voll oder gesperrt: dann bleibt nur der Puffer im Arbeitsspeicher.
    }
  }

  private restore() {
    const { storage, storageKey } = this.options
    if (!storage || !storageKey) return
    try {
      const saved = storage.getItem(storageKey)
      if (saved) this.pending = new Map(JSON.parse(saved) as [string, P][])
    } catch {
      this.pending = new Map()
    }
    if (this.pending.size) {
      this._state = 'pending'
      this.schedule(0)
    }
  }
}

export function browserStorage(): StorageLike | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}
