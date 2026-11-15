<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import { currentUser } from '../stores/session'
import type { Account, Project, Role } from '../types'

const accounts = ref<Account[]>([])
const allProjects = ref<Project[]>([])
const error = ref('')
const message = ref('')
const editing = ref<number | null>(null)
const confirmDelete = ref<number | null>(null)
const ROLE_LABEL: Record<Role, string> = { admin: 'Admin', interviewer: 'Interviewer' }

const blank = () => ({ benutzername: '', name: '', passwort: '', rolle: 'interviewer' as Role, projekte: [] as number[] })
const form = reactive(blank())
const edit = reactive({ name: '', rolle: 'interviewer' as Role, aktiv: true, passwort: '', projekte: [] as number[] })

function formatTime(value: string | null) {
  if (!value) return 'noch nie'
  return new Date(value.endsWith('Z') ? value : `${value}Z`).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })
}

function projectNames(ids: number[]) {
  const names = allProjects.value.filter((p) => ids.includes(p.id)).map((p) => p.name)
  return names.length ? names.join(', ') : 'keine'
}

async function guarded(action: () => Promise<void>) {
  error.value = message.value = ''
  try {
    await action()
  } catch (e) {
    error.value = (e as Error).message
  }
}

const load = () =>
  guarded(async () => {
    ;[accounts.value, allProjects.value] = await Promise.all([
      api.get<Account[]>('/benutzer'),
      api.get<Project[]>('/projekte'),
    ])
  })

const create = () =>
  guarded(async () => {
    const created = await api.post<Account>('/benutzer', { ...form, projekte: form.rolle === 'admin' ? [] : form.projekte })
    Object.assign(form, blank())
    await load()
    message.value = `Konto „${created.benutzername}“ angelegt. Bitte Benutzername und Passwort persönlich weitergeben.`
  })

function startEdit(account: Account) {
  Object.assign(edit, { name: account.name, rolle: account.rolle, aktiv: account.aktiv, passwort: '', projekte: [...account.projekte] })
  editing.value = account.id
  confirmDelete.value = null
}

const save = (account: Account) =>
  guarded(async () => {
    const body: Record<string, unknown> = { name: edit.name, rolle: edit.rolle, aktiv: edit.aktiv, projekte: edit.projekte }
    if (edit.passwort) body.passwort = edit.passwort
    await api.put<Account>(`/benutzer/${account.id}`, body)
    editing.value = null
    await load()
    message.value = edit.passwort ? 'Gespeichert. Das neue Passwort gilt ab sofort.' : 'Gespeichert.'
  })

const remove = (account: Account) =>
  guarded(async () => {
    await api.delete(`/benutzer/${account.id}`)
    confirmDelete.value = null
    await load()
  })

onMounted(load)
</script>

<template>
  <main class="page max-w-4xl space-y-6">
    <h1 class="page-title">Benutzer</h1>
    <p class="muted">
      <strong>Admins</strong> sehen und ändern alles und verwalten Benutzer, Einstellungen und Sicherung.
      <strong>Interviewer</strong> sehen die ihnen zugeordneten Projekte mit allen Interviews darin, ändern aber nur ihre
      eigenen Interviews. Sie dürfen Projekte anlegen (werden dabei Mitglied), Kataloge pflegen und die KI-Funktionen
      nutzen.
    </p>
    <p v-if="error" class="error-box" role="alert">{{ error }}</p>
    <p v-if="message" class="rounded-md bg-accent-50 p-3 text-sm" role="status">{{ message }}</p>

    <ul class="space-y-3">
      <li v-for="account in accounts" :key="account.id" class="card space-y-3" data-testid="account-row">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="font-medium">
              {{ account.name }} <span class="font-normal text-stone-500">({{ account.benutzername }})</span>
              <span class="ml-1 rounded bg-stone-100 px-1.5 py-0.5 text-xs">{{ ROLE_LABEL[account.rolle] }}</span>
              <span v-if="!account.aktiv" class="ml-1 rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-800">gesperrt</span>
              <span v-if="account.id === currentUser?.id" class="ml-1 text-xs text-accent-800">(Sie)</span>
            </div>
            <div class="muted">
              <template v-if="account.rolle === 'interviewer'">Projekte: {{ projectNames(account.projekte) }} · </template>
              {{ account.interviews }} Interviews · letzte Anmeldung {{ formatTime(account.letzte_anmeldung) }}
            </div>
          </div>
          <div v-if="editing !== account.id" class="flex flex-wrap gap-2">
            <button class="btn" @click="startEdit(account)">Bearbeiten</button>
            <button
              v-if="account.id !== currentUser?.id && !account.interviews"
              class="btn btn-danger"
              @click="(confirmDelete = account.id), (editing = null)"
            >
              Löschen
            </button>
          </div>
        </div>

        <div v-if="confirmDelete === account.id" class="flex flex-wrap items-center gap-2 text-sm">
          <span>Konto „{{ account.benutzername }}“ endgültig löschen?</span>
          <button class="btn btn-danger" @click="remove(account)">Ja, löschen</button>
          <button class="btn" @click="confirmDelete = null">Abbrechen</button>
        </div>

        <form v-if="editing === account.id" class="grid gap-3 rounded-md bg-stone-50 p-3 sm:grid-cols-2" @submit.prevent="save(account)">
          <div>
            <label class="label" :for="`name-${account.id}`">Anzeigename</label>
            <input :id="`name-${account.id}`" v-model="edit.name" class="input" maxlength="200" />
          </div>
          <div>
            <label class="label" :for="`rolle-${account.id}`">Rolle</label>
            <select :id="`rolle-${account.id}`" v-model="edit.rolle" class="input">
              <option value="interviewer">Interviewer</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div>
            <label class="label" :for="`pw-${account.id}`">Neues Passwort (optional)</label>
            <input
              :id="`pw-${account.id}`"
              v-model="edit.passwort"
              type="password"
              class="input"
              autocomplete="new-password"
              minlength="8"
              placeholder="leer lassen = unverändert"
            />
          </div>
          <label class="flex items-center gap-2 self-end text-sm">
            <input v-model="edit.aktiv" type="checkbox" /> Konto aktiv (ohne Häkchen: gesperrt, sofort abgemeldet)
          </label>
          <fieldset v-if="edit.rolle === 'interviewer'" class="sm:col-span-2">
            <legend class="label">Projekte</legend>
            <label v-for="project in allProjects" :key="project.id" class="mr-4 inline-flex items-center gap-2 text-sm">
              <input v-model="edit.projekte" type="checkbox" :value="project.id" /> {{ project.name }}
            </label>
          </fieldset>
          <div class="flex flex-wrap gap-2 sm:col-span-2">
            <button class="btn btn-primary">Speichern</button>
            <button type="button" class="btn" @click="editing = null">Abbrechen</button>
          </div>
        </form>
      </li>
    </ul>

    <form class="card grid gap-3 sm:grid-cols-2" data-testid="new-account" @submit.prevent="create">
      <h2 class="font-semibold sm:col-span-2">Neues Konto</h2>
      <div>
        <label class="label" for="new-username">Benutzername</label>
        <input
          id="new-username"
          v-model="form.benutzername"
          class="input"
          required
          maxlength="100"
          pattern="[A-Za-z0-9_.@\-]+"
          title="Buchstaben, Ziffern und . _ - @, keine Leerzeichen"
          autocomplete="off"
          placeholder="z. B. a.berg"
        />
      </div>
      <div>
        <label class="label" for="new-name">Anzeigename</label>
        <input id="new-name" v-model="form.name" class="input" maxlength="200" placeholder="z. B. Anna Berg" />
      </div>
      <div>
        <label class="label" for="new-password">Erstes Passwort</label>
        <input
          id="new-password"
          v-model="form.passwort"
          type="password"
          class="input"
          required
          minlength="8"
          autocomplete="new-password"
        />
        <p class="muted mt-1">Mindestens 8 Zeichen. Die Person kann es unter „Mein Konto“ ändern.</p>
      </div>
      <div>
        <label class="label" for="new-role">Rolle</label>
        <select id="new-role" v-model="form.rolle" class="input">
          <option value="interviewer">Interviewer</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <fieldset v-if="form.rolle === 'interviewer'" class="sm:col-span-2">
        <legend class="label">Projekte</legend>
        <label v-for="project in allProjects" :key="project.id" class="mr-4 inline-flex items-center gap-2 text-sm">
          <input v-model="form.projekte" type="checkbox" :value="project.id" /> {{ project.name }}
        </label>
      </fieldset>
      <div class="sm:col-span-2">
        <button class="btn btn-primary">Konto anlegen</button>
      </div>
    </form>
  </main>
</template>
