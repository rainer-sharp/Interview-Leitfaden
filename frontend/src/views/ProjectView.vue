<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api } from '../api'
import ProjectAnalysisPanel from '../components/ProjectAnalysisPanel.vue'
import { currentProjectId, loadProjects, setCurrentProject } from '../stores/project'
import type { LlmSettings, Project } from '../types'

const props = defineProps<{ id: number }>()
const router = useRouter()

type Field = 'ki_anweisung' | 'ki_analyse_anweisung'

const project = ref<Project | null>(null)
const general = reactive<Record<Field, string>>({ ki_anweisung: '', ki_analyse_anweisung: '' })
const form = reactive({ name: '', beschreibung: '', ki_anweisung: '', ki_analyse_anweisung: '' })
const own = reactive<Record<Field, boolean>>({ ki_anweisung: false, ki_analyse_anweisung: false })
const onlyTranscripts = ref(false)
const error = ref('')
const message = ref('')

const INSTRUCTIONS: { field: Field; title: string; help: string }[] = [
  {
    field: 'ki_anweisung',
    title: 'Anweisung für die KI-Bewertung einzelner Interviews',
    help: 'Legt fest, wie das Sprachmodell ein einzelnes Interview zusammenfasst und bewertet.',
  },
  {
    field: 'ki_analyse_anweisung',
    title: 'Anweisung für die KI-Analyse des Projekts',
    help: 'Legt Aufbau und Schwerpunkte der Analyse über alle Interviews fest. Die Kurzzusammenfassung wird daraus abgeleitet.',
  },
]

const value = (field: Field) => (own[field] ? form[field].trim() : '')
const changed = computed(
  () =>
    !!project.value &&
    (form.name !== project.value.name ||
      form.beschreibung !== project.value.beschreibung ||
      INSTRUCTIONS.some(({ field }) => value(field) !== project.value![field])),
)
const exportQuery = computed(() => (onlyTranscripts.value ? '?nur_transkripte=true' : ''))

function fill(values: Project) {
  project.value = values
  Object.assign(form, {
    name: values.name,
    beschreibung: values.beschreibung,
    ki_anweisung: values.ki_anweisung,
    ki_analyse_anweisung: values.ki_analyse_anweisung,
  })
  own.ki_anweisung = !!values.ki_anweisung
  own.ki_analyse_anweisung = !!values.ki_analyse_anweisung
}

function toggleOwn(field: Field) {
  // Als Ausgangspunkt die allgemeine Anweisung übernehmen, damit nur noch angepasst werden muss.
  if (own[field] && !form[field].trim()) form[field] = general[field]
}

function open() {
  setCurrentProject(props.id)
  router.push('/')
}

async function save() {
  error.value = message.value = ''
  if (INSTRUCTIONS.some(({ field }) => own[field] && !form[field].trim())) {
    error.value = 'Eine eigene Anweisung ist leer. Text eintragen oder das Häkchen „Eigene Anweisung“ entfernen.'
    return
  }
  try {
    fill(
      await api.put<Project>(`/projekte/${props.id}`, {
        name: form.name,
        beschreibung: form.beschreibung,
        ki_anweisung: value('ki_anweisung'),
        ki_analyse_anweisung: value('ki_analyse_anweisung'),
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
    const llm = await api.get<LlmSettings>('/einstellungen/llm')
    general.ki_anweisung = llm.anweisung
    general.ki_analyse_anweisung = llm.analyse_anweisung
  } catch (e) {
    error.value = (e as Error).message
  }
})
</script>

<template>
  <main class="page max-w-3xl space-y-6">
    <RouterLink to="/projekte" class="link text-sm">← Alle Projekte</RouterLink>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="page-title">{{ project?.name ?? 'Projekt' }}</h1>
        <p v-if="project" class="muted">
          {{ project.gruppen }} {{ project.gruppen === 1 ? 'Gruppe' : 'Gruppen' }} · {{ project.interviews }}
          {{ project.interviews === 1 ? 'Interview' : 'Interviews' }}
        </p>
      </div>
      <button v-if="project && project.id !== currentProjectId" class="btn" @click="open">Als aktuelles Projekt öffnen</button>
    </div>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <template v-if="project">
      <section class="card space-y-3" data-testid="project-export">
        <h2 class="font-semibold">Alle Interviews als eine Datei</h2>
        <p class="muted">
          Fasst alle Interviews des Projekts zusammen: je Interview Fragen mit Notizen, Gesamtnotiz, KI-Bewertung und
          Transkripte. Markdown zum Lesen und Weitergeben, JSON zur Weiterverarbeitung (z. B. in anderen KI-Werkzeugen).
        </p>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="onlyTranscripts" type="checkbox" /> Nur Transkripte
        </label>
        <div class="flex flex-wrap gap-2">
          <a :href="`/api/projekte/${id}/export.md${exportQuery}`" class="btn" download>Markdown</a>
          <a :href="`/api/projekte/${id}/export.json${exportQuery}`" class="btn" download>JSON</a>
        </div>
      </section>

      <ProjectAnalysisPanel :project-id="id" />

      <form class="card space-y-4" data-testid="project-settings" @submit.prevent="save">
        <h2 class="font-semibold">Projekt bearbeiten</h2>
        <div>
          <label class="label" for="p-name">Name</label>
          <input id="p-name" v-model="form.name" class="input" required maxlength="200" />
        </div>
        <div>
          <label class="label" for="p-desc">Beschreibung</label>
          <input id="p-desc" v-model="form.beschreibung" class="input" />
        </div>

        <div v-for="item in INSTRUCTIONS" :key="item.field" class="space-y-2 border-t border-stone-200 pt-4">
          <h3 class="font-medium">{{ item.title }}</h3>
          <p class="muted">
            {{ item.help }} Ohne eigene Anweisung gilt die allgemeine aus den
            <RouterLink to="/einstellungen" class="link">Einstellungen</RouterLink>.
          </p>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="own[item.field]" type="checkbox" @change="toggleOwn(item.field)" />
            <span>Eigene Anweisung: {{ item.title.replace('Anweisung für die ', '') }}</span>
          </label>
          <template v-if="own[item.field]">
            <label class="label" :for="`p-${item.field}`">Anweisung (System-Prompt)</label>
            <textarea :id="`p-${item.field}`" v-model="form[item.field]" class="input min-h-72 font-mono text-sm"></textarea>
            <button type="button" class="link text-sm" @click="form[item.field] = general[item.field]">
              Allgemeine Anweisung als Vorlage einsetzen
            </button>
          </template>
          <details v-else class="text-sm">
            <summary class="cursor-pointer">Allgemeine Anweisung ansehen</summary>
            <pre class="mt-2 rounded bg-stone-50 p-3 text-xs whitespace-pre-wrap text-stone-700">{{ general[item.field] }}</pre>
          </details>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <button type="submit" class="btn btn-primary" :disabled="!changed">Speichern</button>
          <span v-if="message" class="text-sm text-accent-800" role="status">{{ message }}</span>
        </div>
      </form>
    </template>
  </main>
</template>
