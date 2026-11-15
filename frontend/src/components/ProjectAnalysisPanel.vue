<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { EVALUATION_STATUS_LABEL, evaluationBusy } from '../stores/evaluation'
import { elapsed } from '../stores/recordings'
import type { ProjectAnalysis } from '../types'

const props = defineProps<{ projectId: number }>()

const analysis = ref<ProjectAnalysis | null>(null)
const draftShort = ref('')
const draftLong = ref('')
const error = ref('')
const confirmDelete = ref(false)
const now = ref(Date.now())

const base = computed(() => `/projekte/${props.projectId}/analyse`)
const busy = computed(() => evaluationBusy(analysis.value))
const hasText = computed(() => !!(analysis.value?.analyse || analysis.value?.kurzfassung))
const changed = computed(
  () => !!analysis.value && (draftShort.value !== analysis.value.kurzfassung || draftLong.value !== analysis.value.analyse),
)
const finishedAt = computed(() => {
  const end = analysis.value?.fertig_am
  return end ? new Date(end.endsWith('Z') ? end : `${end}Z`).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' }) : ''
})

let timer: ReturnType<typeof setInterval> | undefined

function apply(fresh: ProjectAnalysis) {
  const old = analysis.value
  const untouched = !old || (draftShort.value === old.kurzfassung && draftLong.value === old.analyse)
  // Eigene, noch nicht gespeicherte Korrekturen bleiben stehen – außer ein neues Ergebnis ist da.
  if (untouched || (evaluationBusy(old) && fresh.status === 'fertig')) {
    draftShort.value = fresh.kurzfassung
    draftLong.value = fresh.analyse
  }
  analysis.value = fresh
}

async function call(action: () => Promise<ProjectAnalysis | void>) {
  error.value = ''
  try {
    const result = await action()
    if (result) apply(result)
  } catch (e) {
    error.value = (e as Error).message
  }
}

const refresh = () => call(() => api.get<ProjectAnalysis>(base.value))
const start = () => call(() => api.post<ProjectAnalysis>(base.value))
const save = () =>
  call(async () => {
    const saved = await api.put<ProjectAnalysis>(base.value, { kurzfassung: draftShort.value, analyse: draftLong.value })
    draftShort.value = saved.kurzfassung
    draftLong.value = saved.analyse
    return saved
  })
const remove = () =>
  call(async () => {
    await api.delete(base.value)
    confirmDelete.value = false
    draftShort.value = draftLong.value = ''
    return api.get<ProjectAnalysis>(base.value)
  })

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
watch(() => props.projectId, refresh)
onMounted(refresh)
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <section class="card space-y-3" data-testid="project-analysis">
    <h2 class="font-semibold">KI-Analyse des Projekts</h2>
    <p class="muted">
      Ein Sprachmodell wertet alle Interviews des Projekts gemeinsam aus und schreibt daraus eine Kurzzusammenfassung.
      Grundlage sind Notizen, Gesamtnotizen, die KI-Bewertungen der einzelnen Interviews und die Transkripte. Das
      Ergebnis ist ein Vorschlag: bitte prüfen und bei Bedarf korrigieren.
    </p>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>

    <template v-if="analysis">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="text-sm text-stone-600">
          <span data-testid="analysis-status">{{ EVALUATION_STATUS_LABEL[analysis.status] }}</span>
          <template v-if="busy">
            <template v-if="analysis.gestartet_am"> · {{ elapsed(analysis.gestartet_am, null, now) }}</template>
            <template v-if="analysis.fortschritt"> · {{ analysis.fortschritt }}</template>
          </template>
          <template v-else-if="hasText && finishedAt">
            · {{ finishedAt }} · {{ analysis.interviews }} Interviews<template v-if="analysis.modell">
              · {{ analysis.modell }}</template
            ><template v-if="analysis.umfang !== 'vollständig'"> · {{ analysis.umfang }}</template
            ><template v-if="analysis.bearbeitet"> · von Hand überarbeitet</template>
          </template>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-if="!busy"
            class="btn"
            :class="{ 'btn-primary': !hasText }"
            :disabled="!analysis.interviews_jetzt"
            @click="start"
          >
            {{ hasText ? 'Neu analysieren' : 'Projekt analysieren' }}
          </button>
          <button v-if="analysis.status !== 'keine' && !confirmDelete" class="btn btn-danger" @click="confirmDelete = true">
            {{ busy ? 'Abbrechen' : 'Verwerfen' }}
          </button>
        </div>
      </div>
      <p v-if="!busy" class="muted" data-testid="analysis-sources">
        <template v-if="analysis.interviews_jetzt">
          Einfließen würden {{ analysis.interviews_jetzt }}
          {{ analysis.interviews_jetzt === 1 ? 'Interview' : 'Interviews' }}, davon {{ analysis.mit_transkript }} mit Transkript
          und {{ analysis.mit_bewertung }} mit KI-Bewertung. Anweisung:
          {{ analysis.anweisung_quelle === 'projekt' ? 'eigene des Projekts' : 'allgemeine' }} (unten anpassbar).
          Sehr umfangreiche Projekte werden gekürzt; was gekürzt wurde, steht beim Ergebnis.
        </template>
        <template v-else>Das Projekt hat noch keine Interviews mit Notizen oder Transkript.</template>
      </p>
      <p v-else class="muted">
        Läuft im Hintergrund nach eventuell wartenden Interview-Bewertungen; bei vielen Transkripten einige Minuten. Die
        Seite darf geschlossen werden.
      </p>

      <div v-if="confirmDelete" class="flex flex-wrap items-center gap-2 text-sm">
        <span>{{ busy ? 'Laufende Analyse abbrechen?' : 'Analyse endgültig verwerfen?' }}</span>
        <button class="btn btn-danger" @click="remove">Ja</button>
        <button class="btn" @click="confirmDelete = false">Nein</button>
      </div>

      <div v-if="analysis.status === 'fehler'" class="error-box" role="alert" data-testid="analysis-error">
        {{ analysis.fehler }}
        <template v-if="hasText"> Die vorherige Analyse bleibt erhalten.</template>
      </div>

      <div v-if="hasText" class="space-y-3">
        <div>
          <label class="label" for="analyse-kurz">Kurzzusammenfassung</label>
          <textarea
            id="analyse-kurz"
            v-model="draftShort"
            class="input min-h-48 text-sm leading-relaxed"
            :readonly="busy"
            data-testid="analysis-short"
          ></textarea>
        </div>
        <details>
          <summary class="cursor-pointer text-sm font-medium">Ausführliche Analyse</summary>
          <label class="sr-only" for="analyse-lang">Analyse</label>
          <textarea
            id="analyse-lang"
            v-model="draftLong"
            class="input mt-2 min-h-96 text-sm leading-relaxed"
            :readonly="busy"
          ></textarea>
        </details>
        <div class="flex flex-wrap gap-2">
          <button class="btn" :disabled="!changed || busy" @click="save">Korrekturen speichern</button>
          <a :href="`/api${base}.pdf`" class="btn" download>Analyse (PDF)</a>
          <a :href="`/api${base}.md`" class="btn" download>Analyse (Markdown)</a>
        </div>
      </div>
    </template>
  </section>
</template>
