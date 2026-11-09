import type { Question } from '../types'

export interface Section {
  abschnitt: string
  questions: Question[]
}

/** Abschnitte sind zusammenhängende Läufe in Reihenfolge der Positionen. */
export function toSections(questions: Question[]): Section[] {
  const sections: Section[] = []
  for (const question of questions) {
    const last = sections[sections.length - 1]
    if (last?.abschnitt === question.abschnitt) last.questions.push(question)
    else sections.push({ abschnitt: question.abschnitt, questions: [question] })
  }
  return sections
}

function flatten(sections: Section[]): Question[] {
  return sections.flatMap((section) =>
    section.questions.map((question) => ({ ...question, abschnitt: section.abschnitt })),
  )
}

export function moveBetweenSections(
  questions: Question[],
  fromSection: number,
  fromIndex: number,
  toSection: number,
  toIndex: number,
): Question[] {
  const sections = toSections(questions).map((s) => ({ ...s, questions: [...s.questions] }))
  const [moved] = sections[fromSection].questions.splice(fromIndex, 1)
  sections[toSection].questions.splice(toIndex, 0, moved)
  return flatten(sections)
}

/** Einen Schritt verschieben; an der Abschnittsgrenze wechselt die Frage zuerst den Abschnitt. */
export function moveStep(questions: Question[], id: number, direction: -1 | 1): Question[] {
  const result = [...questions]
  const index = result.findIndex((q) => q.id === id)
  const neighbor = result[index + direction]
  if (!neighbor) return result
  if (neighbor.abschnitt !== result[index].abschnitt) {
    result[index] = { ...result[index], abschnitt: neighbor.abschnitt }
  } else {
    result[index + direction] = result[index]
    result[index] = neighbor
  }
  return result
}

export function moveSection(questions: Question[], sectionIndex: number, direction: -1 | 1): Question[] {
  const sections = toSections(questions)
  const target = sectionIndex + direction
  if (!sections[target]) return questions
  ;[sections[sectionIndex], sections[target]] = [sections[target], sections[sectionIndex]]
  return flatten(sections)
}

export function renameSection(questions: Question[], sectionIndex: number, abschnitt: string): Question[] {
  const sections = toSections(questions)
  sections[sectionIndex].abschnitt = abschnitt
  return flatten(sections)
}
