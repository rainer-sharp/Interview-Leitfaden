export interface QuestionnaireSummary {
  id: number
  group_id: number
  name: string
  version: number
  importiert_am: string
  fragen: number
  interviews: number
}

export interface Group {
  id: number
  name: string
  beschreibung: string
  questionnaires: QuestionnaireSummary[]
}

export type QuestionType = 'text' | 'skala' | 'ja_nein' | 'auswahl'

export interface Question {
  id: number
  questionnaire_id: number
  abschnitt: string
  position: number
  text: string
  hinweis: string
  pflicht: boolean
  typ: QuestionType
}

export interface Questionnaire extends QuestionnaireSummary {
  group_name: string
  questions: Question[]
}

export interface ImportIssue {
  zeile: number | null
  meldung: string
}

export interface ImportRow {
  zeile: number
  abschnitt: string
  position: number | null
  frage: string
  hinweis: string
  pflicht: boolean
  typ: string
}

export interface ImportPreview {
  ok: boolean
  format: string
  encoding: string | null
  trennzeichen: string | null
  rows: ImportRow[]
  errors: ImportIssue[]
  warnings: ImportIssue[]
}
