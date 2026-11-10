import { expect, test } from '@playwright/test'
import { createGroup, importCatalog, login, unique } from './helpers'

test.beforeEach(async ({ page }) => login(page))

test('LLM-Server einstellen und Verbindung prüfen', async ({ page }) => {
  await page.goto('/einstellungen')
  const form = page.getByTestId('settings-llm')
  await expect(form.getByLabel('Server-URL')).toHaveValue('http://127.0.0.1:9/v1')
  await form.getByLabel('Modell').fill('mein-modell')
  await form.getByRole('button', { name: 'Speichern' }).click()
  await expect(form.getByText('Gespeichert.')).toBeVisible()

  await page.reload()
  await expect(form.getByLabel('Modell')).toHaveValue('mein-modell')
  await form.getByRole('button', { name: 'Verbindung testen' }).click()
  await expect(page.getByTestId('llm-check')).toContainText('nicht erreichbar')
  await form.getByLabel('Modell').fill('')
  await form.getByRole('button', { name: 'Speichern' }).click()
  await expect(form.getByLabel('Modell')).toHaveValue('')
})

test('Interview bewerten lassen: Hinweis, Auftrag, Fehlermeldung', async ({ page }) => {
  await createGroup(page)
  await importCatalog(page)
  await page.getByRole('link', { name: 'Interview starten' }).click()
  await page.getByLabel('Interviewte Person').fill(unique('Person'))
  await page.getByRole('button', { name: 'Interview starten' }).click()
  await page.getByRole('navigation', { name: 'Alle Fragen' }).getByRole('button', { name: 'Abschluss' }).click()
  await page.getByLabel('Gesamtnotiz').fill('Sehr offenes Gespräch')
  await expect(page.getByTestId('save-state')).toHaveText('gespeichert')

  const panel = page.getByTestId('evaluation')
  await expect(panel.getByTestId('evaluation-status')).toHaveText('noch nicht bewertet')
  await expect(panel.getByTestId('evaluation-sources')).toContainText('nur Notizen')
  await panel.getByRole('button', { name: 'Interview bewerten' }).click()
  // Der LLM-Server der E2E-Umgebung ist absichtlich nicht erreichbar.
  await expect(panel.getByTestId('evaluation-status')).toHaveText('Fehler', { timeout: 15_000 })
  await expect(panel.getByTestId('evaluation-error')).toContainText('nicht erreichbar')

  await panel.getByRole('button', { name: 'Verwerfen' }).click()
  await panel.getByRole('button', { name: 'Ja' }).click()
  await expect(panel.getByTestId('evaluation-status')).toHaveText('noch nicht bewertet')
})
