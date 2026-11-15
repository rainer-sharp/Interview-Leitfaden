<script setup lang="ts">
import { reactive, ref } from 'vue'
import { api } from '../api'
import { currentUser } from '../stores/session'

const form = reactive({ altes_passwort: '', neues_passwort: '', wiederholung: '' })
const error = ref('')
const message = ref('')

async function save() {
  error.value = message.value = ''
  if (form.neues_passwort !== form.wiederholung) {
    error.value = 'Die beiden neuen Passwörter stimmen nicht überein.'
    return
  }
  try {
    await api.put('/auth/passwort', { altes_passwort: form.altes_passwort, neues_passwort: form.neues_passwort })
    Object.assign(form, { altes_passwort: '', neues_passwort: '', wiederholung: '' })
    message.value = 'Passwort geändert. Auf anderen Geräten müssen Sie sich neu anmelden.'
  } catch (e) {
    error.value = (e as Error).message
  }
}
</script>

<template>
  <main class="page max-w-xl space-y-6">
    <h1 class="page-title">Mein Konto</h1>
    <p v-if="currentUser" class="muted">
      Angemeldet als <strong>{{ currentUser.name }}</strong> ({{ currentUser.benutzername }}),
      Rolle {{ currentUser.rolle === 'admin' ? 'Admin' : 'Interviewer' }}.
    </p>
    <form class="card space-y-4" @submit.prevent="save">
      <h2 class="font-semibold">Passwort ändern</h2>
      <p v-if="error" class="error-box" role="alert">{{ error }}</p>
      <p v-if="message" class="text-sm text-accent-800" role="status">{{ message }}</p>
      <div>
        <label class="label" for="old-pw">Bisheriges Passwort</label>
        <input id="old-pw" v-model="form.altes_passwort" type="password" class="input" required autocomplete="current-password" />
      </div>
      <div>
        <label class="label" for="new-pw">Neues Passwort</label>
        <input
          id="new-pw"
          v-model="form.neues_passwort"
          type="password"
          class="input"
          required
          minlength="8"
          autocomplete="new-password"
        />
      </div>
      <div>
        <label class="label" for="repeat-pw">Neues Passwort wiederholen</label>
        <input id="repeat-pw" v-model="form.wiederholung" type="password" class="input" required autocomplete="new-password" />
      </div>
      <button class="btn btn-primary">Passwort ändern</button>
    </form>
  </main>
</template>
