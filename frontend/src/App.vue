<script setup lang="ts">
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { logout } from './stores/session'

const route = useRoute()
const router = useRouter()

async function signOut() {
  await logout()
  router.replace('/login')
}
</script>

<template>
  <header v-if="!route.meta.focus" class="border-b border-stone-200 bg-white">
    <nav class="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
      <RouterLink to="/" class="font-semibold text-accent-800">Interview-Leitfaden</RouterLink>
      <RouterLink to="/" class="nav-link">Gruppen</RouterLink>
      <RouterLink to="/interviews" class="nav-link">Interviews</RouterLink>
      <RouterLink to="/einstellungen" class="nav-link">Einstellungen</RouterLink>
      <a href="/api/backup" class="nav-link" download title="Datenbank und alle Interviews als ZIP">Backup</a>
      <div class="ml-auto flex items-center gap-2">
        <RouterLink to="/interviews/neu" class="btn btn-primary">Neues Interview</RouterLink>
        <button class="btn" @click="signOut">Abmelden</button>
      </div>
    </nav>
  </header>
  <RouterView />
</template>
