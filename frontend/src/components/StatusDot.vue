<script setup lang="ts">
import type { AnswerStatus } from '../types'

defineProps<{ status: AnswerStatus }>()
</script>

<template>
  <span
    class="inline-block size-2.5 shrink-0 rounded-full"
    :class="{
      'border-2 border-stone-400': status === 'offen',
      'bg-accent-600': status === 'beantwortet',
      'bg-amber-500': status === 'spaeter',
      'bg-stone-400': status === 'uebersprungen',
    }"
    :data-status="status"
    aria-hidden="true"
  ></span>
</template>
