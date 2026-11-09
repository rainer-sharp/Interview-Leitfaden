<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import type { Group } from '../types'

const groups = ref<Group[]>([])
const loaded = ref(false)
const name = ref('')
const beschreibung = ref('')
const error = ref('')

async function load() {
  try {
    groups.value = await api.get<Group[]>('/groups')
    loaded.value = true
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function create() {
  error.value = ''
  try {
    await api.post('/groups', { name: name.value, beschreibung: beschreibung.value })
    name.value = ''
    beschreibung.value = ''
    await load()
  } catch (e) {
    error.value = (e as Error).message
  }
}

onMounted(load)
</script>

<template>
  <main class="page space-y-6">
    <h1 class="page-title">Personengruppen</h1>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <ul v-if="groups.length" class="grid gap-3 sm:grid-cols-2">
      <li v-for="group in groups" :key="group.id">
        <RouterLink :to="`/gruppen/${group.id}`" class="card block hover:border-accent-600">
          <span class="block font-medium">{{ group.name }}</span>
          <span v-if="group.beschreibung" class="muted block">{{ group.beschreibung }}</span>
          <span class="muted mt-1 block">
            {{ group.questionnaires.length }}
            {{ group.questionnaires.length === 1 ? 'Katalog' : 'Kataloge' }}
          </span>
        </RouterLink>
      </li>
    </ul>
    <p v-else-if="loaded" class="muted">Noch keine Gruppen. Legen Sie unten die erste an.</p>

    <form class="card grid gap-3 sm:grid-cols-[1fr_2fr_auto] sm:items-end" @submit.prevent="create">
      <div>
        <label class="label" for="group-name">Neue Gruppe</label>
        <input id="group-name" v-model="name" class="input" required placeholder="z. B. Lagerpersonal" />
      </div>
      <div>
        <label class="label" for="group-desc">Beschreibung (optional)</label>
        <input id="group-desc" v-model="beschreibung" class="input" />
      </div>
      <button class="btn btn-primary">Anlegen</button>
    </form>
  </main>
</template>
