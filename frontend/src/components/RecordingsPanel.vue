<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api, upload } from '../api'
import { ACCEPTED_AUDIO, elapsed, formatSize, isBusy, TRANSCRIPT_STATUS_LABEL } from '../stores/recordings'
import type { Recording, TranscriptionMode, TranscriptionSettings } from '../types'

const props = defineProps<{ interviewId: number; person: string; recordings: Recording[] }>()
const emit = defineEmits<{ changed: [recordings: Recording[]] }>()

const items = ref<Recording[]>([...props.recordings])
const settings = ref<TranscriptionSettings | null>(null)
const error = ref('')
const progress = ref<number | null>(null)
const optionsFor = ref<number | null>(null)
const confirmDelete = ref<number | null>(null)
const drafts = reactive<Record<number, string>>({})
const now = ref(Date.now())
const form = reactive({ modus: 'mix' as TranscriptionMode, name_ich: '', name_partner: '', begriffe: '' })

const base = computed(() => `/interviews/${props.interviewId}/aufnahmen`)
const busy = computed(() => items.value.some(isBusy))

let timer: ReturnType<typeof setInterval> | undefined

function replace(recording: Recording) {
  const index = items.value.findIndex((r) => r.id === recording.id)
  if (index >= 0) items.value[index] = recording
  else items.value.push(recording)
  if (recording.transkript_status === 'fertig' && drafts[recording.id] === undefined) drafts[recording.id] = recording.transkript
  emit('changed', items.value)
}

async function refresh() {
  try {
    const fresh = await api.get<Recording[]>(base.value)
    for (const recording of fresh) {
      const old = items.value.find((r) => r.id === recording.id)
      // Ein frisch fertiges Transkript ersetzt den Entwurf; eigene Korrekturen bleiben sonst stehen.
      if (old && old.transkript_status !== 'fertig' && recording.transkript_status === 'fertig') delete drafts[recording.id]
    }
    items.value = []
    fresh.forEach(replace)
    emit('changed', items.value)
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  error.value = ''
  const data = new FormData()
  data.append('datei', file)
  progress.value = 0
  try {
    replace(await upload<Recording>(base.value, data, (fraction) => (progress.value = fraction)))
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    progress.value = null
    input.value = ''
  }
}

function openOptions(recording: Recording) {
  const last = recording.transkript_optionen
  form.modus = last.modus ?? settings.value?.modus ?? 'mix'
  form.name_ich = last.name_ich ?? settings.value?.name_ich ?? 'Ich'
  form.name_partner = last.name_partner ?? props.person
  form.begriffe = last.begriffe?.join(', ') ?? settings.value?.begriffe ?? ''
  optionsFor.value = recording.id
}

async function start(recording: Recording) {
  error.value = ''
  try {
    replace(await api.post<Recording>(`${base.value}/${recording.id}/transkription`, { ...form }))
    optionsFor.value = null
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function saveTranscript(recording: Recording) {
  error.value = ''
  try {
    const saved = await api.put<Recording>(`${base.value}/${recording.id}/transkript`, { transkript: drafts[recording.id] })
    drafts[recording.id] = saved.transkript
    replace(saved)
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function remove(recording: Recording) {
  error.value = ''
  try {
    await api.delete(`${base.value}/${recording.id}`)
    items.value = items.value.filter((r) => r.id !== recording.id)
    confirmDelete.value = null
    emit('changed', items.value)
  } catch (e) {
    error.value = (e as Error).message
  }
}

function lastLines(log: string, count = 6) {
  return log.split('\n').slice(-count).join('\n')
}

watch(
  busy,
  (isRunning) => {
    clearInterval(timer)
    if (isRunning)
      timer = setInterval(() => {
        now.value = Date.now()
        void refresh()
      }, 4000)
  },
  { immediate: true },
)

onMounted(async () => {
  items.value.forEach((r) => r.transkript_status === 'fertig' && (drafts[r.id] = r.transkript))
  try {
    settings.value = await api.get<TranscriptionSettings>('/einstellungen/transkription')
  } catch {
    // Ohne Einstellungen gelten die Vorgaben im Formular.
  }
})

onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="card space-y-3" data-testid="recordings">
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <h2 class="font-semibold">Aufnahme und Transkript</h2>
      <RouterLink to="/einstellungen" class="link text-sm">Transkriptions-Server einstellen</RouterLink>
    </div>
    <p class="muted">
      OBS-Aufnahme (.mkv mit Spuren Mix/Ich/Partner) oder eine andere Audiodatei anhängen und transkribieren lassen. Das
      Transkript erscheint hier und im Export.
    </p>
    <p v-if="settings && !settings.ffmpeg_verfuegbar" class="text-sm text-amber-900">
      ffmpeg ist auf dem Server nicht installiert – Transkribieren schlägt fehl. Im Docker-Image ist es enthalten.
    </p>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <ul v-if="items.length" class="space-y-3">
      <li
        v-for="recording in items"
        :key="recording.id"
        class="space-y-2 rounded-md border border-stone-200 p-3"
        data-testid="recording"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="truncate font-medium">{{ recording.dateiname }}</div>
            <div class="text-xs text-stone-500">
              {{ formatSize(recording.groesse) }} ·
              <span data-testid="transcript-status">{{ TRANSCRIPT_STATUS_LABEL[recording.transkript_status] }}</span>
              <template v-if="recording.transkript_start && recording.transkript_status !== 'keine'">
                · {{ elapsed(recording.transkript_start, recording.transkript_ende, now) }}
              </template>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              v-if="!isBusy(recording) && optionsFor !== recording.id"
              class="btn"
              :class="{ 'btn-primary': recording.transkript_status === 'keine' }"
              @click="openOptions(recording)"
            >
              {{ recording.transkript_status === 'keine' ? 'Transkribieren' : 'Neu transkribieren' }}
            </button>
            <a :href="`/api${base}/${recording.id}/datei`" class="btn" download>Audio</a>
            <button v-if="confirmDelete !== recording.id" class="btn btn-danger" @click="confirmDelete = recording.id">
              Löschen
            </button>
          </div>
        </div>

        <div v-if="confirmDelete === recording.id" class="flex flex-wrap items-center gap-2 text-sm">
          <span>Aufnahme und Transkript endgültig löschen?</span>
          <button class="btn btn-danger" @click="remove(recording)">Ja, löschen</button>
          <button class="btn" @click="confirmDelete = null">Abbrechen</button>
        </div>

        <form
          v-if="optionsFor === recording.id"
          class="grid gap-3 rounded-md bg-stone-50 p-3 sm:grid-cols-2"
          @submit.prevent="start(recording)"
        >
          <div class="sm:col-span-2">
            <label class="label" :for="`modus-${recording.id}`">Modus</label>
            <select :id="`modus-${recording.id}`" v-model="form.modus" class="input">
              <option value="mix">Mix-Spur mit Sprechererkennung (Standard, auch für einfache Audiodateien)</option>
              <option value="tracks">Spuren 2 und 3 getrennt (nur OBS-Aufnahme mit 3 Spuren)</option>
            </select>
          </div>
          <div>
            <label class="label" :for="`ich-${recording.id}`">Name Interviewer (Spur 2)</label>
            <input :id="`ich-${recording.id}`" v-model="form.name_ich" class="input" maxlength="100" />
          </div>
          <div>
            <label class="label" :for="`partner-${recording.id}`">Name Gesprächspartner (Spur 3)</label>
            <input :id="`partner-${recording.id}`" v-model="form.name_partner" class="input" maxlength="100" />
          </div>
          <div class="sm:col-span-2">
            <label class="label" :for="`begriffe-${recording.id}`">Kontextbegriffe (kommagetrennt, optional)</label>
            <input
              :id="`begriffe-${recording.id}`"
              v-model="form.begriffe"
              class="input"
              placeholder="z. B. Firmennamen, Produkte, Fachbegriffe"
            />
          </div>
          <div class="flex flex-wrap gap-2 sm:col-span-2">
            <button type="submit" class="btn btn-primary">Transkription starten</button>
            <button type="button" class="btn" @click="optionsFor = null">Abbrechen</button>
          </div>
        </form>

        <div v-if="isBusy(recording)" class="space-y-1">
          <p class="muted">
            Lange Aufnahmen brauchen Zeit (Blöcke à 50 min). Die Seite darf geschlossen werden, der Server arbeitet weiter.
          </p>
          <pre
            v-if="recording.transkript_log"
            class="overflow-x-auto rounded bg-stone-100 p-2 text-xs whitespace-pre-wrap text-stone-600"
            data-testid="transcript-log"
            >{{ lastLines(recording.transkript_log) }}</pre
          >
        </div>

        <div v-if="recording.transkript_status === 'fehler'" class="error-box space-y-1" role="alert">
          <div>{{ recording.transkript_fehler }}</div>
          <details v-if="recording.transkript_log">
            <summary class="cursor-pointer text-xs">Protokoll</summary>
            <pre class="text-xs whitespace-pre-wrap">{{ recording.transkript_log }}</pre>
          </details>
        </div>

        <details v-if="recording.transkript || drafts[recording.id]" class="space-y-2" open>
          <summary class="cursor-pointer text-sm font-medium">Transkript</summary>
          <label class="sr-only" :for="`transkript-${recording.id}`">Transkript</label>
          <textarea
            :id="`transkript-${recording.id}`"
            v-model="drafts[recording.id]"
            class="input min-h-80 font-mono text-sm leading-relaxed"
            :readonly="isBusy(recording)"
            data-testid="transcript"
          ></textarea>
          <div class="flex flex-wrap gap-2">
            <button
              class="btn"
              :disabled="drafts[recording.id] === recording.transkript || isBusy(recording)"
              @click="saveTranscript(recording)"
            >
              Korrekturen speichern
            </button>
            <a :href="`/api${base}/${recording.id}/transkript.md`" class="btn" download>Transkript (Markdown)</a>
          </div>
        </details>
      </li>
    </ul>

    <div>
      <label class="label" for="aufnahme-datei">Aufnahme hochladen</label>
      <input
        id="aufnahme-datei"
        type="file"
        :accept="ACCEPTED_AUDIO"
        class="block text-sm"
        :disabled="progress !== null"
        @change="onFile"
      />
      <div v-if="progress !== null" class="mt-2 h-2 rounded bg-stone-100" role="progressbar" aria-label="Upload">
        <div class="h-full rounded bg-accent-600 transition-all" :style="{ width: `${Math.round(progress * 100)}%` }"></div>
      </div>
    </div>
  </div>
</template>
