<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import type { ServerCheck, TranscriptionMode, TranscriptionSettings } from '../types'

const current = ref<TranscriptionSettings | null>(null)
const form = reactive({ url: '', model: '', api_key: '', modus: 'mix' as TranscriptionMode, name_ich: '', begriffe: '' })
const removeKey = ref(false)
const error = ref('')
const message = ref('')
const check = ref<ServerCheck | null>(null)
const checking = ref(false)

function fill(values: TranscriptionSettings) {
  current.value = values
  Object.assign(form, { ...values, api_key: '' })
  removeKey.value = false
}

function payload() {
  const body: Record<string, string> = {
    url: form.url.trim(),
    model: form.model.trim(),
    modus: form.modus,
    name_ich: form.name_ich.trim(),
    begriffe: form.begriffe,
  }
  // Leeres Feld = Schlüssel unverändert lassen; „entfernen“ setzt ihn auf die Vorgabe zurück.
  if (removeKey.value) body.api_key = ''
  else if (form.api_key.trim()) body.api_key = form.api_key.trim()
  return body
}

async function save() {
  error.value = message.value = ''
  try {
    fill(await api.put<TranscriptionSettings>('/einstellungen/transkription', payload()))
    message.value = 'Gespeichert.'
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function test() {
  error.value = message.value = ''
  check.value = null
  checking.value = true
  try {
    const { url, model, api_key } = payload()
    check.value = await api.post<ServerCheck>('/einstellungen/transkription/test', { url, model, api_key: api_key || undefined })
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    checking.value = false
  }
}

onMounted(async () => {
  try {
    fill(await api.get<TranscriptionSettings>('/einstellungen/transkription'))
  } catch (e) {
    error.value = (e as Error).message
  }
})
</script>

<template>
  <main class="page max-w-3xl space-y-6">
    <h1 class="page-title">Einstellungen</h1>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <form v-if="current" class="card space-y-4" @submit.prevent="save">
      <div>
        <h2 class="font-semibold">Transkriptions-Server</h2>
        <p class="muted">
          OpenAI-kompatibler Endpunkt (z. B. vLLM mit Nemotron-Transcribe). Leere Felder fallen auf die Vorgabe aus der
          <code>.env</code> bzw. aus <code>transcribe_interview.py</code> zurück.
        </p>
      </div>
      <p v-if="!current.ffmpeg_verfuegbar" class="text-sm text-amber-900">
        ffmpeg/ffprobe fehlen auf diesem Server. Im Docker-Image sind sie enthalten.
      </p>
      <div>
        <label class="label" for="url">Server-URL</label>
        <input id="url" v-model="form.url" class="input" placeholder="http://192.168.101.95:8001/v1" />
      </div>
      <div>
        <label class="label" for="model">Modell</label>
        <input id="model" v-model="form.model" class="input" list="modelle" />
        <datalist id="modelle">
          <option v-for="m in check?.modelle ?? []" :key="m" :value="m" />
        </datalist>
      </div>
      <div>
        <label class="label" for="api_key">API-Schlüssel</label>
        <input
          id="api_key"
          v-model="form.api_key"
          type="password"
          class="input"
          autocomplete="off"
          :placeholder="current.api_key_gesetzt ? 'gesetzt – leer lassen, um ihn zu behalten' : 'keiner (lokaler Server)'"
          :disabled="removeKey"
        />
        <label v-if="current.api_key_gesetzt" class="mt-1 flex items-center gap-2 text-sm">
          <input v-model="removeKey" type="checkbox" /> Schlüssel entfernen
        </label>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button type="button" class="btn" :disabled="checking" @click="test">
          {{ checking ? 'Prüfe …' : 'Verbindung testen' }}
        </button>
        <span
          v-if="check"
          class="text-sm"
          :class="check.ok ? 'text-accent-800' : 'text-red-800'"
          data-testid="server-check"
          role="status"
          >{{ check.meldung }}</span
        >
      </div>

      <div class="border-t border-stone-200 pt-4">
        <h2 class="font-semibold">Vorgaben für neue Transkriptionen</h2>
        <p class="muted">Lassen sich beim Start einer Transkription noch ändern.</p>
      </div>
      <div>
        <label class="label" for="modus">Modus</label>
        <select id="modus" v-model="form.modus" class="input">
          <option value="mix">Mix-Spur mit Sprechererkennung</option>
          <option value="tracks">Spuren 2 und 3 getrennt (OBS)</option>
        </select>
      </div>
      <div>
        <label class="label" for="name_ich">Name Interviewer</label>
        <input id="name_ich" v-model="form.name_ich" class="input" maxlength="100" />
      </div>
      <div>
        <label class="label" for="begriffe">Kontextbegriffe</label>
        <textarea
          id="begriffe"
          v-model="form.begriffe"
          class="input min-h-24"
          placeholder="Komma oder eine pro Zeile, z. B. SestigSystems, DigiKey, Nexar"
        ></textarea>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <button type="submit" class="btn btn-primary">Speichern</button>
        <span v-if="message" class="text-sm text-accent-800" role="status">{{ message }}</span>
      </div>
    </form>
  </main>
</template>
