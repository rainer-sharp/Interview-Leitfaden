<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '../stores/session'

const route = useRoute()
const router = useRouter()
const passwort = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await login(passwort.value)
    const target = typeof route.query.weiter === 'string' && route.query.weiter.startsWith('/') ? route.query.weiter : '/'
    router.replace(target)
  } catch (e) {
    error.value = (e as Error).message
    passwort.value = ''
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="flex min-h-dvh items-center justify-center px-4">
    <form class="card w-full max-w-sm space-y-4" @submit.prevent="submit">
      <h1 class="text-xl font-semibold">Interview-Leitfaden</h1>
      <p v-if="error" class="error-box" role="alert">{{ error }}</p>
      <div>
        <label class="label" for="password">Passwort</label>
        <input
          id="password"
          v-model="passwort"
          type="password"
          class="input"
          autocomplete="current-password"
          required
          autofocus
        />
      </div>
      <button class="btn btn-primary w-full" :disabled="busy">Anmelden</button>
    </form>
  </main>
</template>
