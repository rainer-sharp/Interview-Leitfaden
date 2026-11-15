import { resolve } from 'node:path'
import type { Page } from '@playwright/test'

export const testdata = (name: string) => resolve(import.meta.dirname, '../../testdata', name)

let counter = 0
export const unique = (prefix: string) => `${prefix} ${Date.now()}-${++counter}`

export async function login(page: Page, benutzername = 'admin', passwort = 'e2e-passwort') {
  await page.goto('/login')
  await page.getByLabel('Benutzername').fill(benutzername)
  await page.getByLabel('Passwort').fill(passwort)
  await page.getByRole('button', { name: 'Anmelden' }).click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'))
}

export async function createGroup(page: Page, name = unique('Gruppe')) {
  await page.goto('/')
  await page.getByLabel('Neue Gruppe').fill(name)
  await page.getByRole('button', { name: 'Anlegen' }).click()
  await page.getByRole('link', { name }).click()
  await page.getByRole('heading', { name, level: 1 }).waitFor()
  return name
}

export async function importCatalog(page: Page, file = 'fragen_utf8.csv', name = unique('Katalog')) {
  await page.getByRole('link', { name: 'Fragenliste importieren' }).click()
  await page.getByLabel('Datei (CSV, XLSX oder JSON)').setInputFiles(testdata(file))
  await page.getByTestId('import-preview').waitFor()
  await page.getByLabel('Name des Katalogs').fill(name)
  await page.getByRole('button', { name: /Fragen speichern/ }).click()
  await page.waitForURL(/\/kataloge\/\d+/)
  return name
}
