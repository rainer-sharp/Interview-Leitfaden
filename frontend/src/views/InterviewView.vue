<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import InterviewSummaryPane from '../components/InterviewSummaryPane.vue'
import EvaluationPanel from '../components/EvaluationPanel.vue'
import RecordingsPanel from '../components/RecordingsPanel.vue'
import StatusDot from '../components/StatusDot.vue'
import { firstOpenIndex, formatDate, shortcutFor, statusAfterNote, STATUS_LABEL } from '../stores/interviewState'
import { SaveQueue, browserStorage, type SaveState } from '../stores/saveQueue'
import type { Answer, AnswerStatus, Interview } from '../types'

const props = defineProps<{ id: number }>()
const route = useRoute()
const router = useRouter()

const interview = ref<Interview | null>(null)
const index = ref(0)
const error = ref('')
const saveState = ref<SaveState>('saved')
const showList = ref(false)
const noteField = ref<HTMLTextAreaElement | null>(null)

const EXPORTS = [
  { ext: 'pdf', label: 'PDF' },
  { ext: 'md', label: 'Markdown' },
  { ext: 'csv', label: 'CSV (Excel)' },
]

type Patch = { notiz?: string; status?: AnswerStatus; gesamtnotiz?: string }

const queue = new SaveQueue<Patch>(
  async (key, patch) => {
    if (key === 'gesamt') {
      await api.put(`/interviews/${props.id}`, patch)
      return
    }
    const saved = await api.put<Answer>(`/interviews/${props.id}/answers/${key}`, patch)
    // Nur den Status übernehmen: die Notiz im Feld kann schon neuer sein als die gespeicherte.
    const local = interview.value?.answers.find((a) => a.id === saved.id)
    if (local && !queue.pendingFor(key)?.status) local.status = saved.status
  },
  {
    delay: 1200,
    retryDelay: 5000,
    storage: browserStorage(),
    storageKey: `interview-${props.id}-ungespeichert`,
    onState: (state) => (saveState.value = state),
    onRejected: (e) => (error.value = `Nicht gespeichert: ${(e as Error).message}`),
  },
)

const answers = computed(() => interview.value?.answers ?? [])
const total = computed(() => answers.value.length)
const onSummary = computed(() => index.value >= total.value)
const current = computed<Answer | undefined>(() => answers.value[index.value])
const readonly = computed(() => interview.value?.status !== 'laufend')
const done = computed(() => answers.value.filter((a) => a.status !== 'offen').length)

const sections = computed(() => {
  const result: { abschnitt: string; items: { answer: Answer; index: number }[] }[] = []
  answers.value.forEach((answer, i) => {
    const last = result[result.length - 1]
    const item = { answer, index: i }
    if (last?.abschnitt === answer.question_snapshot.abschnitt) last.items.push(item)
    else result.push({ abschnitt: answer.question_snapshot.abschnitt, items: [item] })
  })
  return result
})

const saveLabel = computed(
  () =>
    ({
      saved: 'gespeichert',
      pending: 'Änderungen …',
      saving: 'speichert …',
      error: 'offline – wird lokal gehalten und erneut gesendet',
    })[saveState.value],
)

function go(target: number) {
  void queue.flush()
  index.value = Math.max(0, Math.min(target, total.value))
  showList.value = false
  router.replace({ query: { ...route.query, frage: onSummary.value ? 'abschluss' : String(index.value + 1) } })
  nextTick(() => noteField.value?.focus())
}

function setStatus(status: AnswerStatus) {
  const answer = current.value
  if (!answer || readonly.value || answer.status === status) return
  answer.status = status
  queue.set(String(answer.id), { status })
}

function onNote(event: Event) {
  const answer = current.value!
  answer.notiz = (event.target as HTMLTextAreaElement).value
  answer.status = statusAfterNote(answer.status, answer.notiz)
  queue.set(String(answer.id), { notiz: answer.notiz })
}

function next() {
  if (current.value?.notiz.trim()) setStatus('beantwortet')
  go(index.value + 1)
}

function skip() {
  setStatus('uebersprungen')
  go(index.value + 1)
}

function later() {
  setStatus('spaeter')
  go(index.value + 1)
}

function onKeydown(event: KeyboardEvent) {
  const shortcut = shortcutFor(event)
  if (!shortcut || !interview.value) return
  event.preventDefault()
  if (shortcut === 'back') go(index.value - 1)
  else if (onSummary.value || readonly.value) {
    if (shortcut === 'next' && !onSummary.value) go(index.value + 1)
  } else if (shortcut === 'next') next()
  else skip()
}

function onGesamtnotiz(text: string) {
  interview.value!.gesamtnotiz = text
  queue.set('gesamt', { gesamtnotiz: text })
}

async function setFinished(finished: boolean) {
  error.value = ''
  try {
    await queue.flush()
    if (queue.hasPending) throw new Error('Noch nicht alles gespeichert. Bitte Verbindung prüfen.')
    interview.value = await api.post<Interview>(`/interviews/${props.id}/${finished ? 'abschliessen' : 'wiederoeffnen'}`)
  } catch (e) {
    error.value = (e as Error).message
  }
}

function flushOnHide() {
  if (document.visibilityState === 'hidden') void queue.flush()
}

function warnBeforeUnload(event: BeforeUnloadEvent) {
  void queue.flush()
  if (queue.hasPending) event.preventDefault()
}

watch(
  () => route.query.frage,
  (frage) => {
    if (!interview.value) return
    const wanted = frage === 'abschluss' ? total.value : Number(frage) - 1
    if (Number.isInteger(wanted) && wanted !== index.value && wanted >= 0 && wanted <= total.value) index.value = wanted
  },
)

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  document.addEventListener('visibilitychange', flushOnHide)
  window.addEventListener('beforeunload', warnBeforeUnload)
  try {
    const loaded = await api.get<Interview>(`/interviews/${props.id}`)
    // Lokal gepufferte, noch nicht gesendete Eingaben haben Vorrang vor dem Serverstand.
    for (const answer of loaded.answers) Object.assign(answer, queue.pendingFor(String(answer.id)) ?? {})
    const gesamt = queue.pendingFor('gesamt')?.gesamtnotiz
    if (gesamt !== undefined) loaded.gesamtnotiz = gesamt
    interview.value = loaded
  } catch (e) {
    error.value = (e as Error).message
    return
  }
  const frage = route.query.frage
  const wanted = frage === 'abschluss' ? total.value : Number(frage) - 1
  const start =
    Number.isInteger(wanted) && wanted >= 0 && wanted <= total.value
      ? wanted
      : readonly.value
        ? total.value
        : firstOpenIndex(answers.value)
  go(start)
})

onBeforeRouteLeave(() => queue.flush())

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.removeEventListener('visibilitychange', flushOnHide)
  window.removeEventListener('beforeunload', warnBeforeUnload)
  void queue.flush().finally(() => queue.dispose())
})
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <header class="sticky top-[env(safe-area-inset-top,0px)] z-10 border-b border-stone-200 bg-white">
      <div class="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2">
        <RouterLink to="/interviews" class="btn" title="Interview unterbrechen – es kann jederzeit fortgesetzt werden">
          ⏸ Pause
        </RouterLink>
        <div v-if="interview" class="min-w-0 flex-1">
          <div class="truncate text-sm font-medium">
            {{ interview.person }}<span v-if="interview.organisation"> · {{ interview.organisation }}</span>
          </div>
          <div class="truncate text-xs text-stone-500">
            {{ formatDate(interview.datum) }} · {{ interview.group_name }} · {{ interview.questionnaire_name }}
          </div>
        </div>
        <span
          class="text-xs"
          :class="saveState === 'error' ? 'font-medium text-red-800' : 'text-stone-500'"
          data-testid="save-state"
          aria-live="polite"
          >{{ saveLabel }}</span
        >
        <button class="btn lg:hidden" :aria-expanded="showList" @click="showList = !showList">Fragenliste</button>
      </div>
      <div
        v-if="interview"
        class="h-1.5 bg-stone-100"
        role="progressbar"
        :aria-valuenow="done"
        aria-valuemin="0"
        :aria-valuemax="total"
        aria-label="Bearbeitete Fragen"
      >
        <div class="h-full bg-accent-600 transition-all" :style="{ width: `${(done / Math.max(total, 1)) * 100}%` }"></div>
      </div>
    </header>

    <p v-if="error" class="error-box mx-auto mt-3 w-full max-w-6xl" role="alert">{{ error }}</p>

    <div v-if="interview" class="mx-auto flex w-full max-w-6xl flex-1 gap-6 px-4 py-6">
      <nav
        class="w-72 shrink-0 space-y-4 overflow-y-auto lg:block"
        :class="showList ? 'fixed inset-x-0 top-24 bottom-0 z-20 block w-auto bg-white p-4 shadow-lg lg:static lg:p-0 lg:shadow-none' : 'hidden'"
        aria-label="Alle Fragen"
      >
        <div v-for="(section, s) in sections" :key="s">
          <h2 class="mb-1 text-xs font-semibold tracking-wide text-stone-500 uppercase">{{ section.abschnitt }}</h2>
          <ul>
            <li v-for="item in section.items" :key="item.answer.id">
              <button
                class="flex w-full items-start gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-stone-100"
                :class="{ 'bg-accent-50 font-medium': item.index === index }"
                :aria-current="item.index === index ? 'step' : undefined"
                @click="go(item.index)"
              >
                <StatusDot :status="item.answer.status" class="mt-1" />
                <span class="line-clamp-2"
                  >{{ item.index + 1 }}. {{ item.answer.question_snapshot.text
                  }}<span v-if="item.answer.question_snapshot.pflicht" class="text-accent-700" title="Pflichtfrage">
                    *</span
                  ></span
                >
              </button>
            </li>
          </ul>
        </div>
        <button
          class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm font-medium hover:bg-stone-100"
          :class="{ 'bg-accent-50': onSummary }"
          @click="go(total)"
        >
          ✓ Abschluss
        </button>
        <ul class="space-y-1 border-t border-stone-200 pt-3 text-xs text-stone-500">
          <li v-for="status in ['beantwortet', 'spaeter', 'uebersprungen', 'offen'] as const" :key="status" class="flex items-center gap-2">
            <StatusDot :status="status" /> {{ STATUS_LABEL[status] }}
          </li>
        </ul>
      </nav>

      <main class="min-w-0 flex-1">
        <InterviewSummaryPane
          v-if="onSummary"
          :interview="interview"
          :readonly="readonly"
          @jump="go"
          @gesamtnotiz="onGesamtnotiz"
          @finish="setFinished(true)"
          @reopen="setFinished(false)"
        >
          <div class="card space-y-2">
            <h2 class="font-semibold">Exportieren</h2>
            <p class="muted">Der Export enthält den gespeicherten Stand.</p>
            <div class="flex flex-wrap gap-2">
              <a v-for="format in EXPORTS" :key="format.ext" :href="`/api/interviews/${id}/export.${format.ext}`" class="btn" download>
                {{ format.label }}
              </a>
            </div>
          </div>
          <RecordingsPanel
            :interview-id="id"
            :person="interview.person"
            :recordings="interview.aufnahmen"
            @changed="interview.aufnahmen = $event"
          />
          <EvaluationPanel :interview-id="id" :recordings="interview.aufnahmen" :project-id="interview.projekt_id" />
        </InterviewSummaryPane>

        <article v-else-if="current" class="mx-auto max-w-3xl space-y-5" data-testid="question-screen">
          <div class="flex flex-wrap items-baseline justify-between gap-2 text-sm text-stone-500">
            <span>{{ current.question_snapshot.abschnitt }}</span>
            <span data-testid="position">{{ index + 1 }}/{{ total }}</span>
          </div>
          <h1 class="text-2xl leading-snug font-semibold sm:text-3xl" data-testid="question-text">
            {{ current.question_snapshot.text }}
          </h1>
          <p class="flex flex-wrap items-center gap-2 text-sm text-stone-600">
            <span v-if="current.question_snapshot.pflicht" class="rounded bg-accent-100 px-1.5 py-0.5 text-xs text-accent-800"
              >Pflicht</span
            >
            <span v-if="current.question_snapshot.hinweis">{{ current.question_snapshot.hinweis }}</span>
          </p>
          <div>
            <label for="note" class="sr-only">Notiz</label>
            <textarea
              id="note"
              ref="noteField"
              :key="current.id"
              :value="current.notiz"
              class="input min-h-64 text-base leading-relaxed"
              placeholder="Notizen zur Antwort …"
              :readonly="readonly"
              @input="onNote"
            ></textarea>
            <p class="mt-1 flex items-center gap-2 text-sm text-stone-500" data-testid="answer-status">
              <StatusDot :status="current.status" /> {{ STATUS_LABEL[current.status] }}
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <button class="btn" :disabled="index === 0" @click="go(index - 1)">
              ← Zurück <kbd class="hidden text-xs text-stone-400 sm:inline">Strg+←</kbd>
            </button>
            <template v-if="!readonly">
              <button class="btn" @click="skip">
                Überspringen <kbd class="hidden text-xs text-stone-400 sm:inline">Strg+S</kbd>
              </button>
              <button class="btn" @click="later">Später nochmal</button>
            </template>
            <button class="btn btn-primary ml-auto" @click="readonly ? go(index + 1) : next()">
              {{ index === total - 1 ? 'Zum Abschluss' : 'Weiter' }} →
              <kbd class="hidden text-xs opacity-75 sm:inline">Strg+Enter</kbd>
            </button>
          </div>
        </article>
      </main>
    </div>
  </div>
</template>
