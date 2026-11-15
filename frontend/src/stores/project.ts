import { computed, ref } from 'vue'
import { api } from '../api'
import type { Project } from '../types'

/**
 * Das aktuelle Projekt: Gruppen, Interviews und „Interview starten“ zeigen nur dessen Inhalte.
 * Gemerkt im Browser (je Gerät), sonst das erste Projekt.
 */
const STORAGE_KEY = 'interview-leitfaden.projekt'

export const projects = ref<Project[]>([])
export const currentProjectId = ref<number | null>(readStored())
export const currentProject = computed(() => projects.value.find((p) => p.id === currentProjectId.value) ?? null)

function readStored(): number | null {
  try {
    const value = Number(localStorage.getItem(STORAGE_KEY))
    return Number.isInteger(value) && value > 0 ? value : null
  } catch {
    return null
  }
}

export function setCurrentProject(id: number) {
  currentProjectId.value = id
  try {
    localStorage.setItem(STORAGE_KEY, String(id))
  } catch {
    // Ohne Speicher gilt die Auswahl bis zum Neuladen
  }
}

/** Wählt ein gültiges Projekt: das gemerkte, wenn es noch existiert, sonst das älteste. */
export function pickProject(list: Pick<Project, 'id'>[], wanted: number | null): number | null {
  if (wanted !== null && list.some((p) => p.id === wanted)) return wanted
  return list.length ? Math.min(...list.map((p) => p.id)) : null
}

export async function loadProjects(): Promise<Project[]> {
  projects.value = await api.get<Project[]>('/projekte')
  const id = pickProject(projects.value, currentProjectId.value)
  if (id !== null && id !== currentProjectId.value) setCurrentProject(id)
  return projects.value
}

/** Projekt-ID für Anfragen; lädt die Liste beim ersten Mal. */
export async function ensureProject(): Promise<number | null> {
  if (!projects.value.length) await loadProjects()
  return currentProjectId.value
}
