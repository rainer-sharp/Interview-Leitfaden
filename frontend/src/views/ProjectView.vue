<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import { loadProjects } from '../stores/project'
import type { LlmSettings, Project } from '../types'

const props = defineProps<{ id: number }>()

const project = ref<Project | null>(null)
const general = ref('')
const form = reactive({ name: '', beschreibung: '', ki_anweisung: '' })
const ownInstructions = ref(false)
const error = ref('')
const message = ref('')

const changed = computed(
  () =>
    !!project.value &&
    (form.name !== project.value.name ||
      form.beschreibung !== project.value.beschreibung ||
      (ownInstructions.value ? form.ki_anweisung.trim() : '') !== project.value.ki_anweisung),
)

function fill(values: Project) {
  project.value = values
  Object.assign(form, { name: values.name, beschreibung: values.beschreibung, ki_anweisung: values.ki_anweisung })
  ownInstructions.value = !!values.ki_anweisung
}

function toggleOwn() {
  // Als Ausgangspunkt die allgemeine Anweisung übernehmen, damit nur noch angepasst werden muss.
  if (ownInstructions.value && !form.ki_anweisung.trim()) form.ki_anweisung = general.value
}

async function save() {
  error.value = message.value = ''
  if (ownInstructions.value && !form.ki_anweisung.trim()) {
    error.value = 'Die eigene Anweisung ist leer. Text eintragen oder „Eigene Anweisung“ abwählen.'
    return
  }
  try {
    fill(
      await api.put<Project>(`/projekte/${props.id}`, {
        name: form.name,
        beschreibung: form.beschreibung,
        ki_anweisung: ownInstructions.value ? form.ki_anweisung : '',
      }),
    )
    await loadProjects()
    message.value = 'Gespeichert.'
  } catch (e) {
    error.value = (e as Error).message
  }
}

onMounted(async () => {
  try {
    fill(await api.get<Project>(`/projekte/${props.id}`))
    general.value = (await api.get<LlmSettings>('/einstellungen/llm')).anweisung
  } catch (e) {
    error.value = (e as Error).message
  }
})
</script>

<template>
  <main class="page max-w-3xl space-y-6">
    <RouterLink to="/projekte" class="link text-sm">← Alle Projekte</RouterLink>
    <h1 class="page-title">{{ project?.name ?? 'Projekt' }}</h1>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <form v-if="project" class="card space-y-4" @submit.prevent="save">
      <div>
        <label class="label" for="p-name">Name</label>
        <input id="p-name" v-model="form.name" class="input" required maxlength="200" />
      </div>
      <div>
        <label class="label" for="p-desc">Beschreibung</label>
        <input id="p-desc" v-model="form.beschreibung" class="input" />
      </div>

      <div class="space-y-2 border-t border-stone-200 pt-4">
        <h2 class="font-semibold">Anweisung für die KI-Bewertung</h2>
        <p class="muted">
          Legt fest, wie das Sprachmodell die Interviews dieses Projekts zusammenfasst und bewertet, z. B. Maßstab,
          Schwerpunkte oder zusätzliche Abschnitte. Ohne eigene Anweisung gilt die allgemeine aus den
          <RouterLink to="/einstellungen" class="link">Einstellungen</RouterLink>.
        </p>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="ownInstructions" type="checkbox" @change="toggleOwn" /> Eigene Anweisung für dieses Projekt
        </label>
        <template v-if="ownInstructions">
          <label class="label" for="p-ki">Anweisung (System-Prompt)</label>
          <textarea id="p-ki" v-model="form.ki_anweisung" class="input min-h-80 font-mono text-sm"></textarea>
          <button type="button" class="link text-sm" @click="form.ki_anweisung = general">
            Allgemeine Anweisung als Vorlage einsetzen
          </button>
        </template>
        <details v-else class="text-sm">
          <summary class="cursor-pointer">Allgemeine Anweisung ansehen</summary>
          <pre class="mt-2 rounded bg-stone-50 p-3 text-xs whitespace-pre-wrap text-stone-700">{{ general }}</pre>
        </details>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <button type="submit" class="btn btn-primary" :disabled="!changed">Speichern</button>
        <span v-if="message" class="text-sm text-accent-800" role="status">{{ message }}</span>
      </div>
    </form>
  </main>
</template>
