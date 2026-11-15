import { computed, ref } from 'vue'
import { api } from '../api'

export interface SessionUser {
  id: number
  benutzername: string
  name: string
  rolle: 'admin' | 'interviewer'
}

/** null = noch nicht geprüft */
export const loggedIn = ref<boolean | null>(null)
export const currentUser = ref<SessionUser | null>(null)
export const isAdmin = computed(() => currentUser.value?.rolle === 'admin')

type Status = { angemeldet: boolean; benutzer?: SessionUser }

export async function checkSession(): Promise<boolean> {
  if (loggedIn.value === null) {
    try {
      const status = await api.get<Status>('/auth/status')
      loggedIn.value = status.angemeldet
      currentUser.value = status.benutzer ?? null
    } catch {
      loggedIn.value = false
    }
  }
  return loggedIn.value
}

export async function login(benutzername: string, passwort: string): Promise<void> {
  const status = await api.post<Status>('/auth/login', { benutzername, passwort })
  loggedIn.value = true
  currentUser.value = status.benutzer ?? null
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
  loggedIn.value = false
  currentUser.value = null
}
