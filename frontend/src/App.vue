<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <header v-if="!route.meta.focus" class="border-b border-stone-200 bg-white">
    <nav class="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
      <RouterLink to="/" class="font-semibold text-accent-800">Interview-Leitfaden</RouterLink>
      <RouterLink to="/" class="nav-link">Gruppen</RouterLink>
      <RouterLink to="/interviews" class="nav-link">Interviews</RouterLink>
      <RouterLink to="/interviews/neu" class="btn btn-primary ml-auto">Neues Interview</RouterLink>
    </nav>
  </header>
  <RouterView />
</template>
