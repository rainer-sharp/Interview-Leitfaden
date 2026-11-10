import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { defineConfig } from '@playwright/test'

const python = process.env.PY ?? resolve(import.meta.dirname, '../.venv/bin/python')
const port = 8765
// Playwright lädt die Konfiguration auch in den Workern; das Temp-Verzeichnis wird dann nur nicht genutzt.
const dataDir = process.env.E2E_DATA_DIR ?? mkdtempSync(join(tmpdir(), 'interview-e2e-'))
process.env.E2E_DATA_DIR = dataDir

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  timeout: 30_000,
  use: { baseURL: `http://127.0.0.1:${port}`, locale: 'de-DE', screenshot: 'only-on-failure' },
  webServer: {
    command:
      `rm -rf ../backend/static && cp -r dist ../backend/static && cd ../backend && ` +
      `"${python}" -m alembic upgrade head && ` +
      `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port ${port}`,
    url: `http://127.0.0.1:${port}/api/health`,
    reuseExistingServer: false,
    env: {
      DATABASE_URL: `sqlite:///${dataDir}/e2e.db`,
      SECRET_KEY: 'e2e-geheimnis',
      ADMIN_PASSWORD: 'e2e-passwort',
      // Nicht erreichbar: E2E prüft nur den Ablauf bis zur Fehlermeldung, kein echtes LLM.
      LLM_URL: 'http://127.0.0.1:9/v1',
    },
  },
})
