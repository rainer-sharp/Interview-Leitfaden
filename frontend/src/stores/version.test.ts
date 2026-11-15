import { beforeEach, describe, expect, it } from 'vitest'
import { checkVersion, formatVersion, loadedVersion, updateAvailable } from './version'

describe('version', () => {
  beforeEach(() => {
    loadedVersion.value = null
    updateAvailable.value = false
  })

  it('merkt sich den Stand beim Laden und meldet erst einen anderen als Update', async () => {
    expect(await checkVersion(async () => 'c908556')).toBe(false)
    expect(loadedVersion.value).toBe('c908556')
    expect(await checkVersion(async () => 'c908556')).toBe(false)
    expect(await checkVersion(async () => 'e1f2a3b')).toBe(true)
    expect(updateAvailable.value).toBe(true)
  })

  it('ignoriert einen nicht erreichbaren Server', async () => {
    await checkVersion(async () => 'c908556')
    expect(await checkVersion(async () => null)).toBe(false)
    expect(loadedVersion.value).toBe('c908556')
  })

  it('ein gemeldetes Update bleibt bestehen', async () => {
    await checkVersion(async () => 'alt')
    await checkVersion(async () => 'neu')
    expect(await checkVersion(async () => null)).toBe(true)
  })
})

describe('formatVersion', () => {
  it('zeigt Releases ohne v und Zwischenstände mit Abstand zum Release', () => {
    expect(formatVersion('v1.0.0')).toBe('1.0.0')
    expect(formatVersion('v1.0.0-3-g75f7e44')).toBe('1.0.0+3 (75f7e44)')
    expect(formatVersion('v1.1.0-rc.1')).toBe('1.1.0-rc.1')
    expect(formatVersion('v1.1.0-rc.1-2-gabc1234')).toBe('1.1.0-rc.1+2 (abc1234)')
  })

  it('lässt Commit-Kennungen und Sonderwerte stehen, markiert lokale Änderungen', () => {
    expect(formatVersion('75f7e44')).toBe('75f7e44')
    expect(formatVersion('entwicklung')).toBe('entwicklung')
    expect(formatVersion('v1.0.0-geaendert')).toBe('1.0.0 (geändert)')
    expect(formatVersion('75f7e44-geaendert')).toBe('75f7e44 (geändert)')
  })
})
