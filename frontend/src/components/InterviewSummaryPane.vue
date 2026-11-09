<script setup lang="ts">
import { computed } from 'vue'
import { countByStatus, STATUS_LABEL } from '../stores/interviewState'
import type { Interview } from '../types'
import StatusDot from './StatusDot.vue'

const props = defineProps<{ interview: Interview; readonly: boolean }>()
const emit = defineEmits<{ jump: [index: number]; gesamtnotiz: [text: string]; finish: []; reopen: [] }>()

const counts = computed(() => countByStatus(props.interview.answers))
const unfinished = computed(() =>
  props.interview.answers.map((answer, index) => ({ answer, index })).filter(({ answer }) => answer.status !== 'beantwortet'),
)
const missingRequired = computed(() => unfinished.value.filter(({ answer }) => answer.question_snapshot.pflicht).length)
</script>

<template>
  <section class="mx-auto max-w-3xl space-y-6" data-testid="summary">
    <div>
      <h1 class="text-2xl font-semibold">{{ readonly ? 'Interview abgeschlossen' : 'Abschluss' }}</h1>
      <p class="muted mt-1">
        {{ counts.beantwortet }} beantwortet · {{ counts.spaeter }} später · {{ counts.uebersprungen }} übersprungen ·
        {{ counts.offen }} offen
      </p>
    </div>

    <div v-if="unfinished.length" class="card space-y-2">
      <h2 class="font-semibold">Noch nicht beantwortet</h2>
      <p v-if="missingRequired && !readonly" class="text-sm text-amber-900">
        {{ missingRequired }} {{ missingRequired === 1 ? 'Pflichtfrage ist' : 'Pflichtfragen sind' }} noch ohne Antwort.
      </p>
      <ul class="divide-y divide-stone-100">
        <li v-for="{ answer, index } in unfinished" :key="answer.id">
          <button
            class="flex w-full items-start gap-2 py-2 text-left text-sm hover:bg-stone-50"
            @click="emit('jump', index)"
          >
            <StatusDot :status="answer.status" class="mt-1" />
            <span class="flex-1">
              {{ index + 1 }}. {{ answer.question_snapshot.text }}
              <span v-if="answer.question_snapshot.pflicht" class="text-accent-700">(Pflicht)</span>
            </span>
            <span class="text-stone-500">{{ STATUS_LABEL[answer.status] }}</span>
          </button>
        </li>
      </ul>
    </div>
    <p v-else class="muted">Alle Fragen sind beantwortet.</p>

    <div>
      <label class="label" for="gesamtnotiz">Gesamtnotiz</label>
      <textarea
        id="gesamtnotiz"
        :value="interview.gesamtnotiz"
        class="input min-h-40"
        placeholder="Gesamteindruck, wichtigste Erkenntnisse, nächste Schritte …"
        :readonly="readonly"
        @input="emit('gesamtnotiz', ($event.target as HTMLTextAreaElement).value)"
      ></textarea>
    </div>

    <slot />

    <div class="flex flex-wrap gap-2">
      <button v-if="!readonly" class="btn btn-primary" @click="emit('finish')">Interview abschließen</button>
      <button v-else class="btn" @click="emit('reopen')">Wieder öffnen und bearbeiten</button>
    </div>
  </section>
</template>
