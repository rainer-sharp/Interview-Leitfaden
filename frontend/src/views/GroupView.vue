<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api } from '../api'
import { loadProjects, projects } from '../stores/project'
import type { Group, QuestionnaireSummary } from '../types'

const props = defineProps<{ id: number }>()
const router = useRouter()

const group = ref<Group | null>(null)
const error = ref('')
const editing = ref(false)
const editName = ref('')
const editDesc = ref('')
const editProject = ref<number | null>(null)
const newCatalog = ref('')

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
    group.value = await api.get<Group>(`/groups/${props.id}`)
  })

function startEdit() {
  editName.value = group.value!.name
  editDesc.value = group.value!.beschreibung
  editProject.value = group.value!.projekt_id
  editing.value = true
}

const saveEdit = () =>
  guarded(async () => {
    group.value = await api.put<Group>(`/groups/${props.id}`, {
      name: editName.value,
      beschreibung: editDesc.value,
      projekt_id: editProject.value,
    })
    editing.value = false
    await loadProjects() // Zähler in der Projektliste
  })

const removeGroup = () =>
  guarded(async () => {
    if (!confirm(`Gruppe „${group.value!.name}“ mit allen Katalogen löschen?`)) return
    await api.delete(`/groups/${props.id}`)
    router.push('/')
  })

const createCatalog = () =>
  guarded(async () => {
    const created = await api.post<QuestionnaireSummary>(`/groups/${props.id}/questionnaires`, { name: newCatalog.value })
    router.push(`/kataloge/${created.id}`)
  })

const removeCatalog = (catalog: QuestionnaireSummary) =>
  guarded(async () => {
    if (!confirm(`Katalog „${catalog.name}“ (Version ${catalog.version}) löschen?`)) return
    await api.delete(`/questionnaires/${catalog.id}`)
    await load()
  })

onMounted(load)
</script>

<template>
  <main class="page space-y-6">
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>
    <template v-if="group">
      <RouterLink to="/" class="link text-sm">← Alle Gruppen</RouterLink>

      <form v-if="editing" class="card space-y-3" @submit.prevent="saveEdit">
        <div>
          <label class="label" for="edit-name">Name</label>
          <input id="edit-name" v-model="editName" class="input" required />
        </div>
        <div>
          <label class="label" for="edit-desc">Beschreibung</label>
          <input id="edit-desc" v-model="editDesc" class="input" />
        </div>
        <div v-if="projects.length > 1">
          <label class="label" for="edit-project">Projekt</label>
          <select id="edit-project" v-model.number="editProject" class="input">
            <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.name }}</option>
          </select>
          <p v-if="editProject !== group.projekt_id" class="muted mt-1">
            Die Gruppe wandert mit allen Katalogen und Interviews in das gewählte Projekt.
          </p>
        </div>
        <div class="flex gap-2">
          <button class="btn btn-primary">Speichern</button>
          <button type="button" class="btn" @click="editing = false">Abbrechen</button>
        </div>
      </form>
      <div v-else class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 class="page-title">{{ group.name }}</h1>
          <p v-if="group.beschreibung" class="muted">{{ group.beschreibung }}</p>
          <p class="muted">Projekt: {{ group.projekt_name }}</p>
        </div>
        <div class="flex gap-2">
          <button class="btn" @click="startEdit">Bearbeiten</button>
          <button class="btn btn-danger" @click="removeGroup">Löschen</button>
        </div>
      </div>

      <section class="space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-lg font-semibold">Fragenkataloge</h2>
          <RouterLink :to="`/gruppen/${id}/import`" class="btn btn-primary">Fragenliste importieren</RouterLink>
        </div>
        <ul v-if="group.questionnaires.length" class="space-y-2">
          <li
            v-for="catalog in group.questionnaires"
            :key="catalog.id"
            class="card flex flex-wrap items-center justify-between gap-3"
          >
            <div>
              <RouterLink :to="`/kataloge/${catalog.id}`" class="font-medium hover:underline">
                {{ catalog.name }}
              </RouterLink>
              <span class="muted ml-2">Version {{ catalog.version }}</span>
              <div class="muted">{{ catalog.fragen }} Fragen · {{ catalog.interviews }} Interviews</div>
            </div>
            <div class="flex flex-wrap gap-2">
              <RouterLink
                v-if="catalog.fragen"
                :to="{ path: '/interviews/neu', query: { katalog: catalog.id } }"
                class="btn"
              >
                Interview starten
              </RouterLink>
              <button class="btn btn-danger" @click="removeCatalog(catalog)">Löschen</button>
            </div>
          </li>
        </ul>
        <p v-else class="muted">Noch kein Katalog. Importieren Sie eine Fragenliste oder legen Sie einen leeren Katalog an.</p>

        <form class="flex flex-wrap items-end gap-2" @submit.prevent="createCatalog">
          <div class="min-w-0 flex-1">
            <label class="label" for="new-catalog">Leeren Katalog anlegen</label>
            <input id="new-catalog" v-model="newCatalog" class="input" required placeholder="Name des Katalogs" />
          </div>
          <button class="btn">Anlegen</button>
        </form>
      </section>
    </template>
  </main>
</template>
