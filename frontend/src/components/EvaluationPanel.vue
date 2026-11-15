<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import { EVALUATION_STATUS_LABEL, evaluationBusy, sourcesHint } from '../stores/evaluation'
import { elapsed } from '../stores/recordings'
import type { Evaluation, Recording } from '../types'

const props = defineProps<{ interviewId: number; recordings: Recording[]; projectId?: number }>()

const evaluation = ref<Evaluation | null>(null)
const draft = ref('')
const error = ref('')
const confirmDelete = ref(false)
const now = ref(Date.now())

const base = computed(() => `/interviews/${props.interviewId}/bewertung`)
const busy = computed(() => evaluationBusy(evaluation.value))
const hasText = computed(() => !!evaluation.value?.text)
const finishedAt = computed(() => {
  const end = evaluation.value?.fertig_am
  return end ? new Date(end.endsWith('Z') ? end : `${end}Z`).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' }) : ''
})

let timer: ReturnType<typeof setInterval> | undefined

function apply(fresh: Evaluation) {
  const wasBusy = busy.value
  // Eigene, noch nicht gespeicherte Korrekturen bleiben stehen – außer ein neues Ergebnis ist da.
  if (draft.value === (evaluation.value?.text ?? '') || (wasBusy && fresh.status === 'fertig')) draft.value = fresh.text
  evaluation.value = fresh
}

async function refresh() {
  try {
    apply(await api.get<Evaluation>(base.value))
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function start() {
  error.value = ''
  try {
    apply(await api.post<Evaluation>(base.value))
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function save() {
  error.value = ''
  try {
    const saved = await api.put<Evaluation>(base.value, { text: draft.value })
    evaluation.value = saved
    draft.value = saved.text
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function remove() {
  error.value = ''
  try {
    await api.delete(base.value)
    confirmDelete.value = false
    draft.value = ''
    await refresh()
  } catch (e) {
    error.value = (e as Error).message
  }
}

watch(
  busy,
  (running) => {
    clearInterval(timer)
    if (running)
      timer = setInterval(() => {
        now.value = Date.now()
        void refresh()
      }, 3000)
  },
  { immediate: true },
)

// Neues oder gelöschtes Transkript ändert den Hinweis, was in die Bewertung einfließt.
watch(
  () => props.recordings.map((r) => `${r.id}:${r.transkript_status}:${r.transkript.length}`).join(),
  () => void refresh(),
)

onMounted(refresh)
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="card space-y-3" data-testid="evaluation">
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <h2 class="font-semibold">KI-Bewertung</h2>
      <RouterLink to="/einstellungen" class="link text-sm">LLM-Server einstellen</RouterLink>
    </div>
    <p class="muted">
      Ein Sprachmodell fasst das Interview zusammen und bewertet es insgesamt – aus Notizen, Gesamtnotiz und, falls
      vorhanden, dem Transkript. Das Ergebnis ist ein Vorschlag: bitte prüfen und bei Bedarf korrigieren.
    </p>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <template v-if="evaluation">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="text-sm text-stone-600">
          <span data-testid="evaluation-status">{{ EVALUATION_STATUS_LABEL[evaluation.status] }}</span>
          <template v-if="busy && evaluation.gestartet_am"> · {{ elapsed(evaluation.gestartet_am, null, now) }}</template>
          <template v-else-if="hasText && finishedAt">
            · {{ finishedAt }}<template v-if="evaluation.modell"> · {{ evaluation.modell }}</template> ·
            {{ evaluation.mit_transkript ? 'mit Transkript' : 'nur Notizen' }}<template v-if="evaluation.bearbeitet">
              · von Hand überarbeitet</template
            >
          </template>
        </div>
        <div class="flex flex-wrap gap-2">
          <button v-if="!busy" class="btn" :class="{ 'btn-primary': !hasText }" @click="start">
            {{ hasText ? 'Neu bewerten' : 'Interview bewerten' }}
          </button>
          <button
            v-if="evaluation.status !== 'keine' && !confirmDelete"
            class="btn btn-danger"
            @click="confirmDelete = true"
          >
            {{ busy ? 'Abbrechen' : 'Verwerfen' }}
          </button>
        </div>
      </div>
      <p v-if="!busy" class="muted" data-testid="evaluation-sources">
        {{ sourcesHint(evaluation) }}
        <span data-testid="evaluation-instructions">
          Anweisung:
          {{ evaluation.anweisung_quelle === 'projekt' ? `eigene des Projekts „${evaluation.projekt_name}“` : 'allgemeine' }}
          (<RouterLink :to="projectId ? `/projekte/${projectId}` : '/projekte'" class="link">im Projekt anpassen</RouterLink>).
        </span>
      </p>
      <p v-else class="muted">
        Je nach Länge des Transkripts dauert das einige Minuten. Die Seite darf geschlossen werden, der Server arbeitet
        weiter.
      </p>

      <div v-if="confirmDelete" class="flex flex-wrap items-center gap-2 text-sm">
        <span>{{ busy ? 'Laufende Bewertung abbrechen?' : 'Bewertung endgültig verwerfen?' }}</span>
        <button class="btn btn-danger" @click="remove">Ja</button>
        <button class="btn" @click="confirmDelete = false">Nein</button>
      </div>

      <div v-if="evaluation.status === 'fehler'" class="error-box" role="alert" data-testid="evaluation-error">
        {{ evaluation.fehler }}
        <template v-if="hasText"> Die vorherige Bewertung bleibt erhalten.</template>
      </div>

      <div v-if="hasText" class="space-y-2">
        <label class="sr-only" for="bewertung-text">Bewertung</label>
        <textarea
          id="bewertung-text"
          v-model="draft"
          class="input min-h-96 text-sm leading-relaxed"
          :readonly="busy"
          data-testid="evaluation-text"
        ></textarea>
        <div class="flex flex-wrap gap-2">
          <button class="btn" :disabled="draft === evaluation.text || busy || !draft.trim()" @click="save">
            Korrekturen speichern
          </button>
          <a :href="`/api${base}.pdf`" class="btn" download>Bewertung (PDF)</a>
          <a :href="`/api${base}.md`" class="btn" download>Bewertung (Markdown)</a>
        </div>
      </div>
    </template>
  </div>
</template>
