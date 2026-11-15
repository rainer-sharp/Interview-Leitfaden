<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api } from '../api'
import { currentProjectId, loadProjects, projects, setCurrentProject } from '../stores/project'
import { isAdmin } from '../stores/session'
import type { Project } from '../types'

const router = useRouter()
const error = ref('')
const loaded = ref(false)
const name = ref('')
const beschreibung = ref('')
const copyFor = ref<number | null>(null)
const copyName = ref('')
const confirmDelete = ref<number | null>(null)

async function guarded(action: () => Promise<void>) {
  error.value = ''
  try {
    await action()
  } catch (e) {
    error.value = (e as Error).message
  }
}

const load = () =>
  guarded(async () => {
    await loadProjects()
    loaded.value = true
  })

function open(project: Project) {
  setCurrentProject(project.id)
  router.push('/')
}

const create = () =>
  guarded(async () => {
    const created = await api.post<Project>('/projekte', { name: name.value, beschreibung: beschreibung.value })
    name.value = beschreibung.value = ''
    await loadProjects()
    open(created)
  })

function startCopy(project: Project) {
  copyFor.value = project.id
  copyName.value = `${project.name} (Kopie)`
  confirmDelete.value = null
}

const copy = (project: Project) =>
  guarded(async () => {
    await api.post<Project>(`/projekte/${project.id}/kopie`, { name: copyName.value.trim() || undefined })
    copyFor.value = null
    await loadProjects()
  })

const remove = (project: Project) =>
  guarded(async () => {
    await api.delete(`/projekte/${project.id}`)
    confirmDelete.value = null
    await loadProjects()
  })

onMounted(load)
</script>

<template>
  <main class="page space-y-6">
    <h1 class="page-title">Projekte</h1>
    <p class="muted">
      Ein Projekt fasst Personengruppen mit ihren Fragenkatalogen und die dazugehörigen Interviews zusammen. Beim Kopieren
      werden Gruppen und Kataloge übernommen, Interviews nicht. Unter „Details“: alle Interviews als eine Datei, KI-Analyse
      des Projekts und eigene KI-Anweisungen.
    </p>
    <p v-if="!isAdmin" class="muted">Sie sehen die Projekte, denen Sie zugeordnet sind, und die, die Sie selbst angelegt haben.</p>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <ul v-if="projects.length" class="space-y-3">
      <li
        v-for="project in projects"
        :key="project.id"
        class="card space-y-3"
        :class="{ 'border-accent-600': project.id === currentProjectId }"
        data-testid="project-row"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="font-medium">
              {{ project.name }}
              <span v-if="project.id === currentProjectId" class="ml-1 text-xs text-accent-800">(aktuell)</span>
            </div>
            <div v-if="project.beschreibung" class="muted">{{ project.beschreibung }}</div>
            <div class="muted mt-1">
              {{ project.gruppen }} {{ project.gruppen === 1 ? 'Gruppe' : 'Gruppen' }} · {{ project.kataloge }}
              {{ project.kataloge === 1 ? 'Katalog' : 'Kataloge' }} · {{ project.interviews }}
              {{ project.interviews === 1 ? 'Interview' : 'Interviews' }}
              <template v-if="project.ki_anweisung || project.ki_analyse_anweisung"> · eigene KI-Anweisung</template>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <button class="btn btn-primary" @click="open(project)">Öffnen</button>
            <RouterLink :to="`/projekte/${project.id}`" class="btn">Details</RouterLink>
            <button class="btn" @click="startCopy(project)">Kopieren</button>
            <button
              v-if="isAdmin && projects.length > 1 && !project.interviews"
              class="btn btn-danger"
              @click="(confirmDelete = project.id), (copyFor = null)"
            >
              Löschen
            </button>
          </div>
        </div>

        <form
          v-if="copyFor === project.id"
          class="flex flex-wrap items-end gap-2 rounded-md bg-stone-50 p-3"
          @submit.prevent="copy(project)"
        >
          <div class="min-w-60 flex-1">
            <label class="label" :for="`copy-${project.id}`">Name der Kopie</label>
            <input :id="`copy-${project.id}`" v-model="copyName" class="input" required maxlength="200" />
          </div>
          <button class="btn btn-primary">Kopie anlegen</button>
          <button type="button" class="btn" @click="copyFor = null">Abbrechen</button>
        </form>

        <div v-if="confirmDelete === project.id" class="flex flex-wrap items-center gap-2 text-sm">
          <span>Projekt mit allen Gruppen und Katalogen endgültig löschen?</span>
          <button class="btn btn-danger" @click="remove(project)">Ja, löschen</button>
          <button class="btn" @click="confirmDelete = null">Abbrechen</button>
        </div>
      </li>
    </ul>

    <form v-if="loaded" class="card grid gap-3 sm:grid-cols-[1fr_2fr_auto] sm:items-end" @submit.prevent="create">
      <div>
        <label class="label" for="project-name">Neues Projekt</label>
        <input id="project-name" v-model="name" class="input" required maxlength="200" placeholder="z. B. Lieferanten 2027" />
      </div>
      <div>
        <label class="label" for="project-desc">Beschreibung (optional)</label>
        <input id="project-desc" v-model="beschreibung" class="input" />
      </div>
      <button class="btn btn-primary">Anlegen</button>
    </form>
  </main>
</template>
