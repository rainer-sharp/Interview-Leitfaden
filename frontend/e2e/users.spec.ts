import { expect, test } from '@playwright/test'
import { importCatalog, login, unique } from './helpers'

test('Admin legt Interviewer an; Interviewer sieht nur sein Projekt und fremde Interviews nur lesend', async ({ browser }) => {
  // --- Admin: Projekt mit Katalog und eigenem Interview, dann Konto für den Interviewer
  const admin = await browser.newPage()
  await login(admin)
  const project = unique('Projekt')
  await admin.goto('/projekte')
  await admin.getByLabel('Neues Projekt').fill(project)
  await admin.getByRole('button', { name: 'Anlegen' }).click()
  const group = unique('Gruppe')
  await admin.getByLabel('Neue Gruppe').fill(group)
  await admin.getByRole('button', { name: 'Anlegen' }).click()
  await admin.getByRole('link', { name: group }).click()
  await importCatalog(admin)
  await admin.getByRole('link', { name: 'Interview starten' }).first().click()
  await admin.getByLabel('Interviewte Person').fill('Vom Admin')
  await admin.getByRole('button', { name: 'Interview starten' }).click()
  await expect(admin.getByTestId('question-screen')).toBeVisible()

  const username = `i${Date.now()}`
  await admin.goto('/benutzer')
  const form = admin.getByTestId('new-account')
  await form.getByLabel('Benutzername').fill(username)
  await form.getByLabel('Anzeigename').fill('Ina Interview')
  await form.getByLabel('Erstes Passwort').fill('ina-passwort')
  await form.getByLabel(project).check()
  await form.getByRole('button', { name: 'Konto anlegen' }).click()
  await expect(admin.getByRole('status')).toContainText(`Konto „${username}“ angelegt`)

  // --- Interviewer in einem eigenen Browser-Kontext
  const context = await browser.newContext()
  const ina = await context.newPage()
  await login(ina, username, 'ina-passwort')
  await expect(ina.getByTestId('current-user')).toHaveText('Ina Interview')
  await expect(ina.getByRole('link', { name: 'Einstellungen' })).toHaveCount(0)
  await expect(ina.getByRole('link', { name: 'Benutzer' })).toHaveCount(0)
  await expect(ina.getByTestId('project-switch').locator('option')).toHaveText([project])

  // Fremdes Interview: lesen ja, ändern nein
  await ina.getByRole('link', { name: 'Interviews' }).first().click()
  const row = ina.getByTestId('interview-row').filter({ hasText: 'Vom Admin' })
  await expect(row.getByRole('button', { name: 'Löschen' })).toHaveCount(0)
  await row.getByRole('link', { name: 'Ansehen' }).click()
  await expect(ina.getByTestId('readonly-hint')).toContainText('Administrator')

  // Eigenes Interview führen
  await ina.goto('/interviews/neu')
  await ina.getByLabel('Interviewte Person').fill('Von Ina')
  await ina.getByRole('button', { name: 'Interview starten' }).click()
  await ina.getByPlaceholder('Notizen zur Antwort …').fill('Eigene Notiz')
  await expect(ina.getByTestId('save-state')).toHaveText('gespeichert')
  await expect(ina.getByTestId('readonly-hint')).toHaveCount(0)
  await context.close()
})
