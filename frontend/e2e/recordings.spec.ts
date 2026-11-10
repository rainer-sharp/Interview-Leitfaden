import { expect, test } from '@playwright/test'
import { createGroup, importCatalog, login, unique } from './helpers'

test.beforeEach(async ({ page }) => login(page))

test('Server einstellen und Verbindung prüfen', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'Einstellungen' }).click()
  await page.getByLabel('Server-URL').fill('http://127.0.0.1:9/v1')
  await page.getByLabel('Name Interviewer').fill('Rainer')
  await page.getByRole('button', { name: 'Speichern' }).click()
  await expect(page.getByText('Gespeichert.')).toBeVisible()

  await page.reload()
  await expect(page.getByLabel('Server-URL')).toHaveValue('http://127.0.0.1:9/v1')
  await page.getByRole('button', { name: 'Verbindung testen' }).click()
  await expect(page.getByTestId('server-check')).toContainText('Nicht erreichbar')
})

test('Aufnahme anhängen, Transkription starten, Fehler sehen, löschen', async ({ page }) => {
  await createGroup(page)
  await importCatalog(page)
  await page.getByRole('link', { name: 'Interview starten' }).click()
  const person = unique('Person')
  await page.getByLabel('Interviewte Person').fill(person)
  await page.getByRole('button', { name: 'Interview starten' }).click()
  await page.getByRole('navigation', { name: 'Alle Fragen' }).getByRole('button', { name: 'Abschluss' }).click()

  const panel = page.getByTestId('recordings')
  await panel.getByLabel('Aufnahme hochladen').setInputFiles({
    name: 'gespräch.wav',
    mimeType: 'audio/wav',
    buffer: Buffer.from('RIFF----WAVEfmt kein echtes Audio'),
  })
  const row = panel.getByTestId('recording')
  await expect(row).toContainText('gespräch.wav')
  await expect(row.getByTestId('transcript-status')).toHaveText('nicht transkribiert')

  await row.getByRole('button', { name: 'Transkribieren' }).click()
  await expect(row.getByLabel('Name Gesprächspartner (Spur 3)')).toHaveValue(person)
  await row.getByRole('button', { name: 'Transkription starten' }).click()
  // Die Testdatei ist kein Audio (bzw. ffmpeg fehlt): der Auftrag endet mit einer Fehlermeldung.
  await expect(row.getByTestId('transcript-status')).toHaveText('Fehler', { timeout: 15_000 })
  await expect(row.getByRole('alert')).toBeVisible()

  await row.getByRole('button', { name: 'Löschen' }).click()
  await row.getByRole('button', { name: 'Ja, löschen' }).click()
  await expect(panel.getByTestId('recording')).toHaveCount(0)
})
