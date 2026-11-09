import { ref } from 'vue'
import { api } from '../api'

/** null = noch nicht geprüft */
export const loggedIn = ref<boolean | null>(null)

export async function checkSession(): Promise<boolean> {
  if (loggedIn.value === null) {
    try {
      loggedIn.value = (await api.get<{ angemeldet: boolean }>('/auth/status')).angemeldet
    } catch {
      loggedIn.value = false
    }
  }
  return loggedIn.value
}

export async function login(passwort: string): Promise<void> {
  await api.post('/auth/login', { passwort })
  loggedIn.value = true
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
  loggedIn.value = false
}
