<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api } from '../api'
import type { Group, ImportPreview, Questionnaire } from '../types'

const props = defineProps<{ id: number }>()
const router = useRouter()

const group = ref<Group | null>(null)
const file = ref<File | null>(null)
const preview = ref<ImportPreview | null>(null)
const error = ref('')
const busy = ref(false)
const modus = ref<'neu' | 'version' | 'anhaengen'>('neu')
const name = ref('')
const targetId = ref<number | null>(null)

const catalogs = computed(() => group.value?.questionnaires ?? [])
const canSave = computed(() => {
  if (!preview.value?.ok || busy.value) return false
  return modus.value === 'neu' ? name.value.trim() !== '' : targetId.value !== null
})

const encodingLabel = computed(() => {
  const p = preview.value
  if (!p) return ''
  const parts = [p.format.toUpperCase()]
  if (p.encoding) parts.push(`Zeichensatz ${p.encoding}`)
  if (p.trennzeichen) parts.push(`Trennzeichen „${p.trennzeichen}“`)
  return parts.join(' · ')
})

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  file.value = input.files?.[0] ?? null
  preview.value = null
  error.value = ''
  if (!file.value) return
  if (!name.value) name.value = file.value.name.replace(/\.[^.]+$/, '')
  const form = new FormData()
  form.append('file', file.value)
  busy.value = true
  try {
    preview.value = await api.post<ImportPreview>('/import/vorschau', form)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}

async function save() {
  const form = new FormData()
  form.append('file', file.value!)
  form.append('modus', modus.value)
  if (modus.value === 'neu') {
    form.append('group_id', String(props.id))
    form.append('name', name.value)
  } else {
    form.append('questionnaire_id', String(targetId.value))
  }
  busy.value = true
  error.value = ''
  try {
    const catalog = await api.post<Questionnaire>('/import', form)
    router.push(`/kataloge/${catalog.id}`)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    group.value = await api.get<Group>(`/groups/${props.id}`)
  } catch (e) {
    error.value = (e as Error).message
  }
})
</script>

<template>
  <main class="page space-y-6">
    <RouterLink :to="`/gruppen/${id}`" class="link text-sm">← {{ group?.name ?? 'Zurück' }}</RouterLink>
    <h1 class="page-title">Fragenliste importieren</h1>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <section class="card space-y-2">
      <label class="label" for="import-file">Datei (CSV, XLSX oder JSON)</label>
      <input id="import-file" type="file" accept=".csv,.txt,.xlsx,.json" class="input" @change="onFile" />
      <p class="muted">
        Nur die Spalte <code>frage</code> ist Pflicht. Optional: abschnitt, position, hinweis, pflicht, typ.
        <a href="/api/import/beispiel.csv" class="link" download>Beispieldatei herunterladen</a>
      </p>
    </section>

    <template v-if="preview">
      <section v-if="preview.errors.length" class="error-box" data-testid="import-errors">
        <h2 class="font-semibold">
          {{ preview.errors.length }} Fehler – so kann die Datei nicht
          gespeichert werden
        </h2>
        <ul class="mt-1 list-disc pl-5">
          <li v-for="(issue, index) in preview.errors" :key="index">
            <template v-if="issue.zeile">Zeile {{ issue.zeile }}: </template>{{ issue.meldung }}
          </li>
        </ul>
      </section>
      <ul v-if="preview.warnings.length" class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm">
        <li v-for="(issue, index) in preview.warnings" :key="index">{{ issue.meldung }}</li>
      </ul>

      <section v-if="preview.rows.length" class="card space-y-2">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h2 class="font-semibold">Vorschau: {{ preview.rows.length }} Fragen</h2>
          <span class="muted">{{ encodingLabel }}</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm" data-testid="import-preview">
            <thead class="text-stone-500">
              <tr>
                <th class="py-1 pr-3 font-medium">Abschnitt</th>
                <th class="py-1 pr-3 font-medium">Frage</th>
                <th class="py-1 pr-3 font-medium">Hinweis</th>
                <th class="py-1 pr-3 font-medium">Pflicht</th>
                <th class="py-1 font-medium">Typ</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in preview.rows" :key="row.zeile" class="border-t border-stone-100 align-top">
                <td class="py-1 pr-3">{{ row.abschnitt }}</td>
                <td class="py-1 pr-3">{{ row.frage || '—' }}</td>
                <td class="py-1 pr-3 text-stone-600">{{ row.hinweis }}</td>
                <td class="py-1 pr-3">{{ row.pflicht ? 'ja' : 'nein' }}</td>
                <td class="py-1">{{ row.typ }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <form v-if="preview.ok" class="card space-y-3" @submit.prevent="save">
        <fieldset class="space-y-1">
          <legend class="label">Speichern als</legend>
          <label class="block"><input v-model="modus" type="radio" value="neu" /> Neuer Katalog</label>
          <label class="block" :class="{ 'text-stone-400': !catalogs.length }">
            <input v-model="modus" type="radio" value="version" :disabled="!catalogs.length" />
            Neue Version eines bestehenden Katalogs
          </label>
          <label class="block" :class="{ 'text-stone-400': !catalogs.length }">
            <input v-model="modus" type="radio" value="anhaengen" :disabled="!catalogs.length" />
            An bestehenden Katalog anhängen
          </label>
        </fieldset>
        <div v-if="modus === 'neu'">
          <label class="label" for="catalog-name">Name des Katalogs</label>
          <input id="catalog-name" v-model="name" class="input" required />
        </div>
        <div v-else>
          <label class="label" for="catalog-target">Katalog</label>
          <select id="catalog-target" v-model.number="targetId" class="input" required>
            <option v-for="catalog in catalogs" :key="catalog.id" :value="catalog.id">
              {{ catalog.name }} (Version {{ catalog.version }}, {{ catalog.fragen }} Fragen)
            </option>
          </select>
        </div>
        <button class="btn btn-primary" :disabled="!canSave">{{ preview.rows.length }} Fragen speichern</button>
      </form>
    </template>
  </main>
</template>
