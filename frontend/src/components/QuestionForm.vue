<script setup lang="ts">
import { reactive } from 'vue'
import type { Question, QuestionType } from '../types'

export type QuestionDraft = Pick<Question, 'text' | 'abschnitt' | 'hinweis' | 'pflicht' | 'typ'>

const props = defineProps<{
  initial?: Question
  sections: string[]
  submitLabel: string
  defaultSection?: string
}>()
const emit = defineEmits<{ submit: [draft: QuestionDraft]; cancel: [] }>()

const blank = (): QuestionDraft => ({
  text: props.initial?.text ?? '',
  abschnitt: props.initial?.abschnitt ?? props.defaultSection ?? 'Allgemein',
  hinweis: props.initial?.hinweis ?? '',
  pflicht: props.initial?.pflicht ?? false,
  typ: (props.initial?.typ ?? 'text') as QuestionType,
})
const draft = reactive(blank())
const uid = Math.random().toString(36).slice(2)

function submit() {
  emit('submit', { ...draft })
  if (!props.initial) {
    draft.text = ''
    draft.hinweis = ''
    draft.pflicht = false
  }
}
</script>

<template>
  <form class="space-y-3" @submit.prevent="submit">
    <div>
      <label class="label" :for="`text-${uid}`">Frage</label>
      <textarea :id="`text-${uid}`" v-model="draft.text" class="input" rows="2" required></textarea>
    </div>
    <div class="grid gap-3 sm:grid-cols-2">
      <div>
        <label class="label" :for="`section-${uid}`">Abschnitt</label>
        <input :id="`section-${uid}`" v-model="draft.abschnitt" class="input" :list="`sections-${uid}`" required />
        <datalist :id="`sections-${uid}`">
          <option v-for="section in sections" :key="section" :value="section" />
        </datalist>
      </div>
      <div>
        <label class="label" :for="`hint-${uid}`">Hinweis für den Interviewer</label>
        <input :id="`hint-${uid}`" v-model="draft.hinweis" class="input" />
      </div>
    </div>
    <div class="flex flex-wrap items-center gap-x-6 gap-y-3">
      <label class="flex items-center gap-2"><input v-model="draft.pflicht" type="checkbox" /> Pflichtfrage</label>
      <label class="flex items-center gap-2">
        Typ
        <select v-model="draft.typ" class="input w-auto">
          <option value="text">Text</option>
          <option value="skala">Skala</option>
          <option value="ja_nein">Ja/Nein</option>
          <option value="auswahl">Auswahl</option>
        </select>
      </label>
      <div class="ml-auto flex gap-2">
        <button class="btn btn-primary">{{ submitLabel }}</button>
        <button v-if="initial" type="button" class="btn" @click="emit('cancel')">Abbrechen</button>
      </div>
    </div>
    <p v-if="draft.typ !== 'text'" class="muted">
      Der Typ wird gespeichert; im Interview wird in dieser Version jede Antwort als Notiz erfasst.
    </p>
  </form>
</template>
