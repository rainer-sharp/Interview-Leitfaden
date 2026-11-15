<script setup lang="ts">
import { watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { currentProjectId, loadProjects, projects, setCurrentProject } from './stores/project'
import { currentUser, isAdmin, logout } from './stores/session'
import { formatVersion, loadedVersion, reloadApp, updateAvailable } from './stores/version'

const route = useRoute()
const PROJECT_URL = 'https://github.com/rainer-sharp/Interview-Leitfaden'

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
      <template v-if="isAdmin">
        <RouterLink to="/einstellungen" class="nav-link">Einstellungen</RouterLink>
        <RouterLink to="/sicherung" class="nav-link">Sicherung</RouterLink>
        <RouterLink to="/benutzer" class="nav-link">Benutzer</RouterLink>
      </template>
      <div class="ml-auto flex items-center gap-2">
        <RouterLink to="/interviews/neu" class="btn btn-primary">Neues Interview</RouterLink>
        <RouterLink v-if="currentUser" to="/konto" class="nav-link text-sm" title="Mein Konto" data-testid="current-user">
          {{ currentUser.name }}
        </RouterLink>
        <button class="btn" @click="signOut">Abmelden</button>
      </div>
    </nav>
  </header>
  <RouterView />
  <footer v-if="!route.meta.focus" class="mx-auto max-w-5xl px-4 pt-4 pb-6 text-center text-xs text-stone-500">
    Interview-Leitfaden<span v-if="loadedVersion" data-testid="footer-version"> {{ formatVersion(loadedVersion) }}</span>
    · Apache-2.0 ·
    <a :href="PROJECT_URL" class="link" target="_blank" rel="noopener">Projektseite</a>
  </footer>
</template>
