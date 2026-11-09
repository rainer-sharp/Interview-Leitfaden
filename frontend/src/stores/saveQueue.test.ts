import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SaveQueue, type StorageLike } from './saveQueue'

class MemoryStorage implements StorageLike {
  data = new Map<string, string>()
  getItem = (key: string) => this.data.get(key) ?? null
  setItem = (key: string, value: string) => void this.data.set(key, value)
  removeItem = (key: string) => void this.data.delete(key)
}

const options = { delay: 1000, retryDelay: 5000 }

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('SaveQueue', () => {
  it('speichert erst nach der Tipp-Pause und fasst Änderungen zusammen', async () => {
    const send = vi.fn().mockResolvedValue(undefined)
    const states: string[] = []
    const queue = new SaveQueue(send, { ...options, onState: (s) => states.push(s) })
    queue.set('1', { notiz: 'H' })
    await vi.advanceTimersByTimeAsync(600)
    queue.set('1', { notiz: 'Hallo' })
    queue.set('1', { status: 'spaeter' })
    await vi.advanceTimersByTimeAsync(999)
    expect(send).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(send).toHaveBeenCalledExactlyOnceWith('1', { notiz: 'Hallo', status: 'spaeter' })
    expect(queue.state).toBe('saved')
    expect(states).toEqual(['pending', 'pending', 'pending', 'saving', 'saved'])
  })

  it('wiederholt nach Netzwerkfehler und verliert nichts', async () => {
    const send = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(undefined)
    const queue = new SaveQueue(send, options)
    queue.set('1', { notiz: 'A' })
    await vi.advanceTimersByTimeAsync(1000)
    expect(queue.state).toBe('error')
    queue.set('1', { notiz: 'AB' })
    expect(queue.state).toBe('error')
    await vi.advanceTimersByTimeAsync(1000)
    expect(send).toHaveBeenLastCalledWith('1', { notiz: 'AB' })
    expect(queue.state).toBe('saved')
  })

  it('verwirft vom Server abgelehnte Änderungen statt endlos zu wiederholen', async () => {
    const rejected = vi.fn()
    const send = vi.fn().mockRejectedValue(Object.assign(new Error('abgeschlossen'), { status: 409 }))
    const queue = new SaveQueue(send, { ...options, onRejected: rejected })
    queue.set('1', { notiz: 'A' })
    await queue.flush()
    expect(rejected).toHaveBeenCalledOnce()
    expect(queue.hasPending).toBe(false)
  })

  it('behält eine während des Sendens getippte Änderung', async () => {
    let release!: () => void
    const send = vi.fn().mockImplementationOnce(() => new Promise<void>((r) => (release = r)))
    send.mockResolvedValue(undefined)
    const queue = new SaveQueue(send, options)
    queue.set('1', { notiz: 'A' })
    const first = queue.flush()
    queue.set('1', { notiz: 'AB' })
    release()
    await first
    expect(send).toHaveBeenLastCalledWith('1', { notiz: 'AB' })
    expect(queue.hasPending).toBe(false)
  })

  it('übersteht einen Reload über den Speicher', async () => {
    const storage = new MemoryStorage()
    const offline = new SaveQueue(vi.fn().mockRejectedValue(new Error('offline')), {
      ...options,
      storage,
      storageKey: 'k',
    })
    offline.set('7', { notiz: 'Wichtig' })
    offline.dispose()

    const send = vi.fn().mockResolvedValue(undefined)
    const reloaded = new SaveQueue(send, { ...options, storage, storageKey: 'k' })
    expect(reloaded.pendingFor('7')).toEqual({ notiz: 'Wichtig' })
    await vi.advanceTimersByTimeAsync(0)
    expect(send).toHaveBeenCalledWith('7', { notiz: 'Wichtig' })
    expect(storage.getItem('k')).toBeNull()
  })

  it('läuft auch ohne nutzbaren Speicher', () => {
    const broken: StorageLike = {
      getItem: () => {
        throw new Error('gesperrt')
      },
      setItem: () => {
        throw new Error('gesperrt')
      },
      removeItem: () => {},
    }
    const queue = new SaveQueue(vi.fn(), { ...options, storage: broken, storageKey: 'k' })
    expect(() => queue.set('1', { notiz: 'A' })).not.toThrow()
  })
})
