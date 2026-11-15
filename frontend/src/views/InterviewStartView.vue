<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { today } from '../stores/interviewState'
import { currentProject, ensureProject, setCurrentProject } from '../stores/project'
import type { Group, Interview } from '../types'

const route = useRoute()
const router = useRouter()

const groups = ref<Group[]>([])
const groupId = ref<number | null>(null)
const catalogId = ref<number | null>(null)
const person = ref('')
const organisation = ref('')
const datum = ref(today())
const error = ref('')
const busy = ref(false)
const loaded = ref(false)

const usableGroups = computed(() =>
  groups.value.filter((g) => g.projekt_id === currentProject.value?.id && g.questionnaires.some((c) => c.fragen > 0)),
)
const catalogs = computed(
  () => groups.value.find((g) => g.id === groupId.value)?.questionnaires.filter((c) => c.fragen > 0) ?? [],
)

// Projekt oben gewechselt: Gruppe aus dem alten Projekt verwerfen
watch(usableGroups, (list) => {
  if (!list.some((g) => g.id === groupId.value)) groupId.value = list.length === 1 ? list[0].id : null
})

watch(groupId, () => {
  if (!catalogs.value.some((c) => c.id === catalogId.value)) {
    // Neueste Version vorschlagen
    catalogId.value = catalogs.value.length ? catalogs.value[catalogs.value.length - 1].id : null
  }
})

async function start() {
  busy.value = true
  error.value = ''
  try {
    const interview = await api.post<Interview>('/interviews', {
      questionnaire_id: catalogId.value,
      person: person.value,
      organisation: organisation.value,
      datum: datum.value,
    })
    router.replace(`/interviews/${interview.id}`)
  } catch (e) {
    error.value = (e as Error).message
    busy.value = false
  }
}

onMounted(async () => {
  try {
    await ensureProject()
    groups.value = await api.get<Group[]>('/groups')
  } catch (e) {
    error.value = (e as Error).message
    return
  }
  const wanted = Number(route.query.katalog)
  const owner = groups.value.find((g) => g.questionnaires.some((c) => c.id === wanted))
  // Start aus einem Katalog heraus: dessen Projekt wird das aktuelle
  if (owner) setCurrentProject(owner.projekt_id)
  groupId.value = owner?.id ?? (usableGroups.value.length === 1 ? usableGroups.value[0].id : null)
  if (owner) catalogId.value = wanted
  loaded.value = true
})
</script>

<template>
  <main class="page max-w-xl space-y-6">
    <div>
      <h1 class="page-title">Interview starten</h1>
      <p v-if="currentProject" class="muted">Projekt: {{ currentProject.name }}</p>
    </div>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>
    <p v-if="loaded && !usableGroups.length" class="muted">
      Dieses Projekt hat noch keinen Katalog mit Fragen. Legen Sie zuerst eine Gruppe an und importieren Sie eine
      Fragenliste – oder wählen Sie oben ein anderes Projekt.
    </p>

    <form v-else-if="loaded" class="card space-y-4" @submit.prevent="start">
      <div>
        <label class="label" for="start-group">Personengruppe</label>
        <select id="start-group" v-model.number="groupId" class="input" required>
          <option v-for="group in usableGroups" :key="group.id" :value="group.id">{{ group.name }}</option>
        </select>
      </div>
      <div>
        <label class="label" for="start-catalog">Fragenkatalog</label>
        <select id="start-catalog" v-model.number="catalogId" class="input" required :disabled="!catalogs.length">
          <option v-for="catalog in catalogs" :key="catalog.id" :value="catalog.id">
            {{ catalog.name }} (Version {{ catalog.version }}, {{ catalog.fragen }} Fragen)
          </option>
        </select>
      </div>
      <div>
        <label class="label" for="start-person">Interviewte Person</label>
        <input id="start-person" v-model="person" class="input" required maxlength="200" autocomplete="off" />
        <p class="muted mt-1">Ein Kürzel genügt, wenn die Notizen pseudonym bleiben sollen.</p>
      </div>
      <div>
        <label class="label" for="start-org">Organisation (optional)</label>
        <input id="start-org" v-model="organisation" class="input" maxlength="200" autocomplete="off" />
      </div>
      <div>
        <label class="label" for="start-date">Datum</label>
        <input id="start-date" v-model="datum" type="date" class="input w-auto" required />
      </div>
      <button class="btn btn-primary" :disabled="busy || !catalogId">Interview starten</button>
    </form>
  </main>
</template>
