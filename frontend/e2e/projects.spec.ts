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
  await page.getByTestId('project-row').filter({ hasText: `${project} (Kopie)` }).getByRole('link', { name: 'Bearbeiten' }).click()
  await page.getByLabel('Eigene Anweisung für dieses Projekt').check()
  await expect(page.getByLabel('Anweisung (System-Prompt)')).toHaveValue(/Gesamtbewertung/)
  await page.getByLabel('Anweisung (System-Prompt)').fill('Bewerte aus Sicht des Einkaufs.')
  await page.getByRole('button', { name: 'Speichern' }).click()
  await expect(page.getByText('Gespeichert.')).toBeVisible()
  await page.goto('/projekte')
  await expect(page.getByTestId('project-row').filter({ hasText: `${project} (Kopie)` })).toContainText(
    'eigene KI-Anweisung',
  )
})
