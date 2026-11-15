<script setup lang="ts">
import { watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { currentProjectId, loadProjects, projects, setCurrentProject } from './stores/project'
import { logout } from './stores/session'
import { reloadApp, updateAvailable } from './stores/version'

const route = useRoute()

// Projektliste für die Auswahl oben, sobald eine angemeldete Seite offen ist.
watch(
  () => route.path,
  () => {
    if (!route.meta.public && !projects.value.length) loadProjects().catch(() => {})
  },
  { immediate: true },
)

function onProject(event: Event) {
  setCurrentProject(Number((event.target as HTMLSelectElement).value))
}

async function signOut() {
  try {
    await logout()
  } finally {
    // Volles Neuladen statt Wechsel innerhalb der App: lädt eine neue Version und leert alle Daten im Speicher.
    reloadApp('/login')
  }
}
</script>

<template>
  <div
    v-if="updateAvailable"
    class="flex flex-wrap items-center justify-center gap-3 bg-amber-100 px-4 py-2 text-sm text-amber-950"
    role="status"
    data-testid="update-banner"
  >
    <span>Eine neue Version der App ist installiert. Bitte neu laden – gespeicherte Notizen bleiben erhalten.</span>
    <button class="btn" @click="reloadApp()">Jetzt neu laden</button>
  </div>
  <header v-if="!route.meta.focus" class="border-b border-stone-200 bg-white">
    <nav class="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
      <RouterLink to="/" class="font-semibold text-accent-800">Interview-Leitfaden</RouterLink>
      <label v-if="projects.length" class="flex items-center gap-2 text-sm">
        <span class="sr-only">Aktuelles Projekt</span>
        <select
          :value="currentProjectId ?? undefined"
          class="input w-auto max-w-56 py-1"
          data-testid="project-switch"
          @change="onProject"
        >
          <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.name }}</option>
        </select>
      </label>
      <RouterLink to="/projekte" class="nav-link">Projekte</RouterLink>
      <RouterLink to="/" class="nav-link">Gruppen</RouterLink>
      <RouterLink to="/interviews" class="nav-link">Interviews</RouterLink>
      <RouterLink to="/einstellungen" class="nav-link">Einstellungen</RouterLink>
      <RouterLink to="/sicherung" class="nav-link">Sicherung</RouterLink>
      <div class="ml-auto flex items-center gap-2">
        <RouterLink to="/interviews/neu" class="btn btn-primary">Neues Interview</RouterLink>
        <button class="btn" @click="signOut">Abmelden</button>
      </div>
    </nav>
  </header>
  <RouterView />
</template>
