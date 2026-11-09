<script setup lang="ts">
import Sortable from 'sortablejs'
import { computed, onMounted, ref } from 'vue'
import type { Directive } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import QuestionForm, { type QuestionDraft } from '../components/QuestionForm.vue'
import { moveBetweenSections, moveSection, moveStep, renameSection, toSections } from '../stores/catalogOrder'
import type { Question, Questionnaire } from '../types'

const props = defineProps<{ id: number }>()

const catalog = ref<Questionnaire | null>(null)
const questions = ref<Question[]>([])
const error = ref('')
const editingId = ref<number | null>(null)
const renamingSection = ref<number | null>(null)
const sectionName = ref('')
const editingName = ref(false)
const catalogName = ref('')

const sections = computed(() => toSections(questions.value))
const sectionNames = computed(() => [...new Set(questions.value.map((q) => q.abschnitt))])

async function guarded(action: () => Promise<void>) {
  error.value = ''
  try {
    await action()
  } catch (e) {
    error.value = (e as Error).message
    await load()
  }
}

async function load() {
  try {
    catalog.value = await api.get<Questionnaire>(`/questionnaires/${props.id}`)
    questions.value = catalog.value.questions
  } catch (e) {
    error.value = (e as Error).message
  }
}

// Schnelle Klicks nacheinander senden, damit die letzte Reihenfolge auch zuletzt ankommt.
let orderQueue = Promise.resolve()

function applyOrder(next: Question[]) {
  questions.value = next
  orderQueue = orderQueue.then(() =>
    guarded(async () => {
      await api.put(
        `/questionnaires/${props.id}/order`,
        next.map((q) => ({ id: q.id, abschnitt: q.abschnitt })),
      )
    }),
  )
  return orderQueue
}

// SortableJS verschiebt selbst im DOM. Das wird zurückgedreht, damit Vue der einzige Besitzer der Liste bleibt.
const vSortable: Directive<HTMLElement> = {
  mounted(el) {
    Sortable.create(el, {
      group: 'fragen',
      handle: '[data-drag-handle]',
      animation: 120,
      forceFallback: true,
      onEnd(event) {
        const { item, from, to, oldIndex, newIndex } = event
        if (oldIndex === undefined || newIndex === undefined) return
        item.remove()
        from.insertBefore(item, from.children[oldIndex] ?? null)
        if (from === to && oldIndex === newIndex) return
        applyOrder(
          moveBetweenSections(
            questions.value,
            Number(from.dataset.section),
            oldIndex,
            Number(to.dataset.section),
            newIndex,
          ),
        )
      },
    })
  },
  unmounted(el) {
    Sortable.get(el)?.destroy()
  },
}

const addQuestion = (draft: QuestionDraft) =>
  guarded(async () => {
    await api.post(`/questionnaires/${props.id}/questions`, draft)
    await load()
  })

const saveQuestion = (id: number, draft: QuestionDraft) =>
  guarded(async () => {
    await api.put(`/questions/${id}`, draft)
    editingId.value = null
    await load()
  })

const removeQuestion = (question: Question) =>
  guarded(async () => {
    if (!confirm(`Frage „${question.text}“ löschen?`)) return
    await api.delete(`/questions/${question.id}`)
    await load()
  })

const saveCatalogName = () =>
  guarded(async () => {
    await api.put(`/questionnaires/${props.id}`, { name: catalogName.value })
    editingName.value = false
    await load()
  })

function startRename(index: number, name: string) {
  renamingSection.value = index
  sectionName.value = name
}

async function saveRename(index: number) {
  const name = sectionName.value.trim()
  renamingSection.value = null
  if (name) await applyOrder(renameSection(questions.value, index, name))
}

onMounted(load)
</script>

<template>
  <main class="page space-y-6">
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>
    <template v-if="catalog">
      <RouterLink :to="`/gruppen/${catalog.group_id}`" class="link text-sm">← {{ catalog.group_name }}</RouterLink>

      <div class="flex flex-wrap items-start justify-between gap-3">
        <form v-if="editingName" class="flex flex-wrap items-center gap-2" @submit.prevent="saveCatalogName">
          <input v-model="catalogName" class="input w-auto" aria-label="Name des Katalogs" required />
          <button class="btn btn-primary">Speichern</button>
          <button type="button" class="btn" @click="editingName = false">Abbrechen</button>
        </form>
        <div v-else>
          <h1 class="page-title">{{ catalog.name }}</h1>
          <p class="muted">
            Version {{ catalog.version }} · {{ questions.length }} Fragen ·
            <button class="link" @click="((catalogName = catalog.name), (editingName = true))">umbenennen</button>
          </p>
        </div>
        <RouterLink
          v-if="questions.length"
          :to="{ path: '/interviews/neu', query: { katalog: catalog.id } }"
          class="btn btn-primary"
        >
          Interview starten
        </RouterLink>
      </div>

      <p v-if="catalog.interviews" class="muted">
        Änderungen gelten nur für neue Interviews; die {{ catalog.interviews }} bestehenden behalten ihre Fragen.
      </p>

      <section v-for="(section, sectionIndex) in sections" :key="`${sectionIndex}-${section.abschnitt}`" class="space-y-2">
        <div class="flex flex-wrap items-center gap-2">
          <form v-if="renamingSection === sectionIndex" class="flex gap-2" @submit.prevent="saveRename(sectionIndex)">
            <input v-model="sectionName" class="input w-auto" aria-label="Name des Abschnitts" required />
            <button class="btn">OK</button>
          </form>
          <h2 v-else class="text-lg font-semibold">{{ section.abschnitt }}</h2>
          <div class="ml-auto flex gap-1">
            <button class="btn" @click="startRename(sectionIndex, section.abschnitt)">Umbenennen</button>
            <button
              class="btn"
              :aria-label="`Abschnitt ${section.abschnitt} nach oben`"
              :disabled="sectionIndex === 0"
              @click="applyOrder(moveSection(questions, sectionIndex, -1))"
            >
              ↑
            </button>
            <button
              class="btn"
              :aria-label="`Abschnitt ${section.abschnitt} nach unten`"
              :disabled="sectionIndex === sections.length - 1"
              @click="applyOrder(moveSection(questions, sectionIndex, 1))"
            >
              ↓
            </button>
          </div>
        </div>

        <ul v-sortable class="space-y-2" :data-section="sectionIndex" data-testid="question-list">
          <li v-for="question in section.questions" :key="question.id" class="card" data-testid="question">
            <QuestionForm
              v-if="editingId === question.id"
              :initial="question"
              :sections="sectionNames"
              submit-label="Speichern"
              @submit="saveQuestion(question.id, $event)"
              @cancel="editingId = null"
            />
            <div v-else class="flex items-start gap-3">
              <span
                data-drag-handle
                class="cursor-grab touch-none px-1 text-xl leading-6 text-stone-400 select-none"
                title="Zum Verschieben ziehen"
                aria-hidden="true"
                >⠿</span
              >
              <div class="min-w-0 flex-1">
                <p>{{ question.text }}</p>
                <p v-if="question.hinweis" class="muted">{{ question.hinweis }}</p>
                <p class="mt-1 flex gap-2 text-xs text-stone-500">
                  <span v-if="question.pflicht" class="rounded bg-accent-100 px-1.5 py-0.5 text-accent-800">Pflicht</span>
                  <span v-else class="rounded bg-stone-100 px-1.5 py-0.5">optional</span>
                  <span v-if="question.typ !== 'text'" class="rounded bg-stone-100 px-1.5 py-0.5">{{ question.typ }}</span>
                </p>
              </div>
              <div class="flex flex-wrap justify-end gap-1">
                <button class="btn" aria-label="Frage nach oben" @click="applyOrder(moveStep(questions, question.id, -1))">↑</button>
                <button class="btn" aria-label="Frage nach unten" @click="applyOrder(moveStep(questions, question.id, 1))">↓</button>
                <button class="btn" @click="editingId = question.id">Bearbeiten</button>
                <button class="btn btn-danger" @click="removeQuestion(question)">Löschen</button>
              </div>
            </div>
          </li>
        </ul>
      </section>

      <section class="card">
        <h2 class="mb-3 font-semibold">Frage hinzufügen</h2>
        <QuestionForm
          :sections="sectionNames"
          :default-section="sectionNames[sectionNames.length - 1]"
          submit-label="Hinzufügen"
          @submit="addQuestion"
        />
      </section>
    </template>
  </main>
</template>
