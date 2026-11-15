<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, upload } from '../api'
import { formatSize } from '../stores/recordings'
import { formatVersion } from '../stores/version'
import type { RestoreResult, SafetyCopy } from '../types'

const file = ref<File | null>(null)
const confirmed = ref(false)
const progress = ref<number | null>(null)
const busy = ref(false)
const error = ref('')
const result = ref<RestoreResult | null>(null)
const copies = ref<SafetyCopy[]>([])
const confirmCopy = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const version = ref('')

function formatTime(value: string) {
  return new Date(value).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'medium' })
}

async function loadCopies() {
  try {
    copies.value = await api.get<SafetyCopy[]>('/restore/sicherungskopien')
  } catch (e) {
    error.value = (e as Error).message
  }
}

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
  confirmed.value = false
  result.value = null
  error.value = ''
}

async function done(action: Promise<RestoreResult>) {
  error.value = ''
  result.value = null
  busy.value = true
  try {
    result.value = await action
    file.value = null
    confirmed.value = false
    confirmCopy.value = null
    if (fileInput.value) fileInput.value.value = ''
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
    progress.value = null
    await loadCopies()
  }
}

function restore() {
  if (!file.value) return
  const data = new FormData()
  data.append('datei', file.value)
  progress.value = 0
  void done(upload<RestoreResult>('/restore', data, (fraction) => (progress.value = fraction)))
}

function restoreCopy(name: string) {
  void done(api.post<RestoreResult>(`/restore/sicherungskopien/${encodeURIComponent(name)}`))
}

onMounted(async () => {
  await loadCopies()
  try {
    version.value = (await api.get<{ version: string }>('/health')).version
  } catch {
    // Nur eine Anzeige
  }
})
</script>

<template>
  <main class="page max-w-3xl space-y-6">
    <h1 class="page-title">Sicherung</h1>

    <section class="card space-y-3">
      <h2 class="font-semibold">Backup herunterladen</h2>
      <p class="muted">
        ZIP mit der kompletten Datenbank, allen Interviews als CSV und den Fragenkatalogen im Importformat. Audiodateien
        sind nicht enthalten.
      </p>
      <a href="/api/backup" class="btn btn-primary" download>Backup herunterladen</a>
    </section>

    <section class="card space-y-3" data-testid="restore">
      <h2 class="font-semibold">Backup wiederherstellen</h2>
      <p class="muted">
        Backup-ZIP aus der App bzw. <code>scripts/backup.sh</code> oder eine tägliche Sicherung
        (<code>backups/interviews-&lt;datum&gt;.db</code>). <strong>Alle aktuellen Daten werden ersetzt.</strong> Der
        jetzige Stand wird vorher als Sicherungskopie abgelegt und lässt sich unten zurückholen.
      </p>
      <p v-if="error" class="error-box" role="alert">{{ error }}</p>
      <div>
        <label class="label" for="backup-datei">Backup-Datei (.zip oder .db)</label>
        <input
          id="backup-datei"
          ref="fileInput"
          type="file"
          accept=".zip,.db,.sqlite,application/zip"
          class="block text-sm"
          :disabled="busy"
          @change="onFile"
        />
      </div>
      <template v-if="file">
        <label class="flex items-start gap-2 text-sm">
          <input v-model="confirmed" type="checkbox" class="mt-1" :disabled="busy" />
          <span>Ja, alle aktuellen Daten durch „{{ file.name }}“ ({{ formatSize(file.size) }}) ersetzen.</span>
        </label>
        <button class="btn btn-danger" :disabled="!confirmed || busy" @click="restore">
          {{ busy ? 'Stelle wieder her …' : 'Wiederherstellen' }}
        </button>
      </template>
      <div v-if="progress !== null" class="h-2 rounded bg-stone-100" role="progressbar" aria-label="Upload">
        <div class="h-full rounded bg-accent-600 transition-all" :style="{ width: `${Math.round(progress * 100)}%` }"></div>
      </div>

      <div v-if="result" class="space-y-1 rounded-md bg-accent-50 p-3 text-sm" role="status" data-testid="restore-result">
        <p class="font-medium">Wiederhergestellt.</p>
        <p>
          {{ result.gruppen }} Gruppen · {{ result.kataloge }} Kataloge · {{ result.interviews }} Interviews ·
          {{ result.aufnahmen }} Aufnahmen
        </p>
        <p v-if="result.fehlende_audiodateien" class="text-amber-900">
          Zu {{ result.fehlende_audiodateien }} Aufnahme(n) fehlt die Audiodatei (nicht im Backup). Transkripte sind
          vorhanden.
        </p>
        <p class="text-stone-600">Vorheriger Stand gesichert als {{ result.sicherungskopie }}.</p>
        <p><a href="/" class="link">Zur Übersicht</a> (lädt die Daten neu)</p>
      </div>
    </section>

    <section class="card space-y-3" data-testid="safety-copies">
      <h2 class="font-semibold">Stände vor früheren Wiederherstellungen</h2>
      <p class="muted">Die letzten fünf werden aufbewahrt (im Datenverzeichnis unter <code>wiederherstellung/</code>).</p>
      <p v-if="!copies.length" class="muted">Noch keine.</p>
      <ul v-else class="divide-y divide-stone-100">
        <li v-for="copy in copies" :key="copy.name" class="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
          <span>{{ formatTime(copy.erstellt) }} · {{ formatSize(copy.groesse) }}</span>
          <span v-if="confirmCopy === copy.name" class="flex flex-wrap items-center gap-2">
            Aktuelle Daten durch diesen Stand ersetzen?
            <button class="btn btn-danger" :disabled="busy" @click="restoreCopy(copy.name)">Ja, zurückholen</button>
            <button class="btn" @click="confirmCopy = null">Abbrechen</button>
          </span>
          <button v-else class="btn" :disabled="busy" @click="confirmCopy = copy.name">Zurückholen</button>
        </li>
      </ul>
    </section>

    <p v-if="version" class="muted text-center" data-testid="app-version">Version {{ formatVersion(version) }}</p>
  </main>
</template>
