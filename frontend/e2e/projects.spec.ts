import { expect, test } from '@playwright/test'
import { importCatalog, login, unique } from './helpers'

test.beforeEach(async ({ page }) => login(page))

test('Projekt anlegen, Gruppe darin, kopieren, wechseln, KI-Anweisung anpassen', async ({ page }) => {
  const project = unique('Projekt')
  await page.goto('/projekte')
  await page.getByLabel('Neues Projekt').fill(project)
  await page.getByRole('button', { name: 'Anlegen' }).click()

  // Neues Projekt ist das aktuelle, die Gruppenliste ist leer
  await expect(page.getByTestId('current-project')).toContainText(project)
  await expect(page.getByText('Noch keine Gruppen in diesem Projekt')).toBeVisible()
  const group = unique('Gruppe')
  await page.getByLabel('Neue Gruppe').fill(group)
  await page.getByRole('button', { name: 'Anlegen' }).click()
  await page.getByRole('link', { name: group }).click()
  await importCatalog(page)

  // Kopieren: Gruppe und Katalog kommen mit
  await page.goto('/projekte')
  const row = page.getByTestId('project-row').filter({ hasText: project }).first()
  await row.getByRole('button', { name: 'Kopieren' }).click()
  await row.getByRole('button', { name: 'Kopie anlegen' }).click()
  const copy = page.getByTestId('project-row').filter({ hasText: `${project} (Kopie)` })
  await expect(copy).toContainText('1 Gruppe · 1 Katalog · 0 Interviews')
  await copy.getByRole('button', { name: 'Öffnen' }).click()
  await expect(page.getByTestId('current-project')).toContainText(`${project} (Kopie)`)
  await expect(page.getByRole('link', { name: group })).toBeVisible()

  // Projektauswahl oben wechselt die Gruppenliste
  await page.getByTestId('project-switch').selectOption({ label: 'Standardprojekt' })
  await expect(page.getByRole('link', { name: group })).toHaveCount(0)

  // Eigene KI-Anweisung
  await page.goto('/projekte')
  await page.getByTestId('project-row').filter({ hasText: `${project} (Kopie)` }).getByRole('link', { name: 'Details' }).click()
  await page.getByLabel('Eigene Anweisung: KI-Bewertung einzelner Interviews').check()
  await expect(page.getByLabel('Anweisung (System-Prompt)')).toHaveValue(/Gesamtbewertung/)
  await page.getByLabel('Anweisung (System-Prompt)').fill('Bewerte aus Sicht des Einkaufs.')
  await page.getByRole('button', { name: 'Speichern' }).click()
  await expect(page.getByText('Gespeichert.')).toBeVisible()
  await page.goto('/projekte')
  await expect(page.getByTestId('project-row').filter({ hasText: `${project} (Kopie)` })).toContainText(
    'eigene KI-Anweisung',
  )
})

test('Sammelexport herunterladen und Projekt-Analyse starten', async ({ page }) => {
  const project = unique('Auswertung')
  await page.goto('/projekte')
  await page.getByLabel('Neues Projekt').fill(project)
  await page.getByRole('button', { name: 'Anlegen' }).click()
  const group = unique('Gruppe')
  await page.getByLabel('Neue Gruppe').fill(group)
  await page.getByRole('button', { name: 'Anlegen' }).click()
  await page.getByRole('link', { name: group }).click()
  await importCatalog(page)
  await page.getByRole('link', { name: 'Interview starten' }).first().click()
  await page.getByLabel('Interviewte Person').fill('Anna')
  await page.getByRole('button', { name: 'Interview starten' }).click()
  await page.getByRole('navigation', { name: 'Alle Fragen' }).getByRole('button', { name: 'Abschluss' }).click()
  await page.getByLabel('Gesamtnotiz').fill('Offenes Gespräch')
  await expect(page.getByTestId('save-state')).toHaveText('gespeichert')

  await page.goto('/projekte')
  await page.getByTestId('project-row').filter({ hasText: project }).getByRole('link', { name: 'Details' }).click()
  const exports = page.getByTestId('project-export')
  const download = page.waitForEvent('download')
  await exports.getByRole('link', { name: 'JSON' }).click()
  expect((await download).suggestedFilename()).toMatch(/^projekt-\d+-.*-interviews\.json$/)

  const panel = page.getByTestId('project-analysis')
  await expect(panel.getByTestId('analysis-sources')).toContainText('würden 1 Interview,')
  await panel.getByRole('button', { name: 'Projekt analysieren' }).click()
  await expect(panel.getByTestId('analysis-status')).toHaveText('Fehler', { timeout: 15_000 })
  await expect(panel.getByTestId('analysis-error')).toContainText('nicht erreichbar')
})
