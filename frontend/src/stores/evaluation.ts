import type { Evaluation, EvaluationStatus } from '../types'

export const EVALUATION_STATUS_LABEL: Record<EvaluationStatus, string> = {
  keine: 'noch nicht bewertet',
  wartend: 'wartet auf den LLM-Server',
  laeuft: 'wird bewertet …',
  fertig: 'bewertet',
  fehler: 'Fehler',
}

export function evaluationBusy(evaluation: Pick<Evaluation, 'status'> | null): boolean {
  return evaluation?.status === 'wartend' || evaluation?.status === 'laeuft'
}

/** Hinweis vor dem Start: was fließt in die Bewertung ein? */
export function sourcesHint(evaluation: Pick<Evaluation, 'hat_transkript' | 'transkription_laeuft'>): string {
  if (evaluation.transkription_laeuft)
    return evaluation.hat_transkript
      ? 'Eine Transkription läuft noch – deren Ergebnis fehlt, wenn die Bewertung jetzt startet.'
      : 'Die Transkription läuft noch. Jetzt gestartet, bewertet das LLM nur die Notizen.'
  return evaluation.hat_transkript
    ? 'Bewertet werden Notizen, Gesamtnotiz und Transkript.'
    : 'Kein Transkript vorhanden – bewertet werden nur Notizen und Gesamtnotiz.'
}
