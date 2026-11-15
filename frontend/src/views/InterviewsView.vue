<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import { currentProject, currentProjectId, ensureProject } from '../stores/project'
import { formatDate } from '../stores/interviewState'
import type { InterviewSummary } from '../types'

const interviews = ref<InterviewSummary[]>([])
const loaded = ref(false)
const error = ref('')
const confirmDelete = ref<number | null>(null)
const allProjects = ref(false)

async function load() {
  try {
    const projectId = await ensureProject()
    interviews.value = await api.get<InterviewSummary[]>(
      allProjects.value ? '/interviews' : `/interviews?projekt_id=${projectId}`,
    )
    loaded.value = true
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function remove(id: number) {
  error.value = ''
  try {
    await api.delete(`/interviews/${id}`)
    confirmDelete.value = null
    await load()
  } catch (e) {
    error.value = (e as Error).message
  }
}

onMounted(load)
watch([currentProjectId, allProjects], load)
</script>

<template>
  <main class="page space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="page-title">Interviews</h1>
        <p v-if="currentProject && !allProjects" class="muted">Projekt: {{ currentProject.name }}</p>
      </div>
      <RouterLink to="/interviews/neu" class="btn btn-primary">Neues Interview</RouterLink>
    </div>
    <label class="flex items-center gap-2 text-sm">
      <input v-model="allProjects" type="checkbox" /> Interviews aller Projekte zeigen
    </label>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <ul v-if="interviews.length" class="space-y-2">
      <li
        v-for="interview in interviews"
        :key="interview.id"
        class="card flex flex-wrap items-center justify-between gap-3"
        data-testid="interview-row"
      >
        <div class="min-w-0">
          <div class="font-medium">
            {{ interview.person }}<span v-if="interview.organisation" class="font-normal text-stone-600">
              · {{ interview.organisation }}</span
            >
          </div>
          <div class="muted">
            {{ formatDate(interview.datum) }} · <template v-if="allProjects">{{ interview.projekt_name }} · </template
            >{{ interview.group_name }} · {{ interview.questionnaire_name }}
            (V{{ interview.version }})
          </div>
          <div class="mt-1 flex items-center gap-2 text-xs">
            <span
              class="rounded px-1.5 py-0.5"
              :class="interview.status === 'laufend' ? 'bg-amber-100 text-amber-900' : 'bg-accent-100 text-accent-800'"
            >
              {{ interview.status === 'laufend' ? 'läuft' : 'abgeschlossen' }}
            </span>
            <span class="text-stone-500">{{ interview.bearbeitet }}/{{ interview.fragen }} Fragen bearbeitet</span>
          </div>
        </div>
        <div v-if="confirmDelete === interview.id" class="flex flex-wrap items-center gap-2">
          <span class="text-sm">Interview mit allen Notizen endgültig löschen?</span>
          <button class="btn btn-danger" @click="remove(interview.id)">Ja, löschen</button>
          <button class="btn" @click="confirmDelete = null">Abbrechen</button>
        </div>
        <div v-else class="flex flex-wrap gap-2">
          <RouterLink :to="`/interviews/${interview.id}`" class="btn btn-primary">
            {{ interview.status === 'laufend' ? 'Fortsetzen' : 'Ansehen' }}
          </RouterLink>
          <button class="btn btn-danger" @click="confirmDelete = interview.id">Löschen</button>
        </div>
      </li>
    </ul>
    <p v-else-if="loaded" class="muted">Noch keine Interviews{{ allProjects ? '' : ' in diesem Projekt' }}.</p>
  </main>
</template>
