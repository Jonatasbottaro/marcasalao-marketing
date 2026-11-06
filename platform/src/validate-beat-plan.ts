/**
 * Validador de BeatPlan (BeatPlan v1).
 *
 * BeatPlan e a traducao temporal de uma Composition valida. Este validador
 * recebe explicitamente ProjectManifest, Composition e BeatPlan: nao le
 * arquivos, nao acessa rede, nao descobre artefatos, nao abre assets, nao
 * verifica existencia fisica e nao conhece nenhum projeto especifico.
 *
 * O validador NAO gera beats, NAO corrige tempos, NAO reordena o array, NAO
 * preenche lacunas, NAO corta beats e NAO altera a Composition. As entradas
 * nao sao mutadas.
 *
 * Os erros sao coletados todos, em ordem de emissao fixa: primeiro o manifesto
 * do projeto, depois a composicao, depois a estrutura do plano, depois os
 * vinculos entre os tres, depois a relacao com as cenas e por ultimo a
 * timeline. Warnings sao heuristicas tecnicas: nao tornam o plano invalido e
 * nao substituem aprovacao editorial nem leitura humana cronometrada.
 */

import {
    BEAT_FIELDS,
    BEAT_MOTION_INTENTS,
    BEAT_NARRATIVE_FUNCTIONS,
    BEAT_PLAN_MAX_NARRATION_LENGTH,
    BEAT_PLAN_MAX_ON_SCREEN_TEXT_LENGTH,
    BEAT_PLAN_MAX_TAGS,
    BEAT_PLAN_METADATA_STATUSES,
    BEAT_PLAN_MIN_READING_MS,
    BEAT_PLAN_MS_PER_WORD,
    BEAT_PLAN_SCHEMA_VERSION,
    BEAT_PLAN_TOP_LEVEL_FIELDS,
    BEAT_TRANSITIONS,
    BEAT_VALIDATION_STATUSES,
    KEBAB_CASE_PATTERN,
} from './beat-plan-contract.js'
import { validateComposition } from './validate-composition.js'
import { validateProjectManifest } from './validate-project.js'
import {
    BEAT_PLAN_VALID_SUMMARY,
    beatPlanInvalidSummary,
    issue,
    type BeatPlanValidationReport,
    type CompositionValidationReport,
    type ValidationIssue,
} from './validation-report.js'

/** Campos permitidos em metadata (forma fechada). */
const METADATA_FIELDS = ['status', 'description', 'tags'] as const

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

function isSafeNonNegativeInteger(value: unknown): value is number {
    return (
        typeof value === 'number' &&
        Number.isInteger(value) &&
        value >= 0 &&
        value <= Number.MAX_SAFE_INTEGER
    )
}

function isSafePositiveInteger(value: unknown): value is number {
    return (
        typeof value === 'number' &&
        Number.isInteger(value) &&
        value > 0 &&
        value <= Number.MAX_SAFE_INTEGER
    )
}

/** Detecta caminhos absolutos POSIX, Windows (letra de unidade) e UNC. */
function isAbsoluteishPath(value: string): boolean {
    return value.startsWith('/') || value.startsWith('\\') || /^[A-Za-z]:[\\/]/.test(value)
}

/** Detecta URL/protocolo, inclusive protocol-relative. */
function hasUrlScheme(value: string): boolean {
    return value.startsWith('//') || /^[A-Za-z][A-Za-z0-9+.-]*:/.test(value)
}

function pathSegments(value: string): string[] {
    return value.split(/[\\/]/).filter((segment) => segment.length > 0)
}

/** Quantidade de palavras apos trim; espacos repetidos nao contam a mais. */
function countWords(text: string): number {
    const trimmed = text.trim()
    if (trimmed.length === 0) return 0
    return trimmed.split(/\s+/).length
}

/**
 * Heuristica deterministica de tempo minimo de leitura: max(1000, palavras*300).
 * Nao considera complexidade semantica, fonte, contraste nem publico.
 */
function estimatedMinimumReadingMs(text: string): number {
    return Math.max(BEAT_PLAN_MIN_READING_MS, countWords(text) * BEAT_PLAN_MS_PER_WORD)
}

/** Referencia estavel a uma cena da Composition informada. */
interface SceneRef {
    id: string
    path: string
}

/** sceneId sintaticamente valido de um beat, com o path de origem. */
interface BeatSceneRef {
    id: string
    path: string
}

/** Resultado da leitura estrutural de um beat; null significa campo invalido. */
interface ParsedBeat {
    index: number
    order: number | null
    sceneRefs: BeatSceneRef[]
    startMs: number | null
    durationMs: number | null
    narrationText: string | null
    onScreenText: string | null
}

interface StructureScan {
    beatPlanId: string | null
    projectId: string | null
    compositionId: string | null
    schemaVersion: number | null
    locale: string | null
    beatCount: number
    beats: ParsedBeat[]
    narrationBeatCount: number
    onScreenTextBeatCount: number
    metadataStatus: string | null
}

function emptyParsedBeat(index: number): ParsedBeat {
    return {
        index,
        order: null,
        sceneRefs: [],
        startMs: null,
        durationMs: null,
        narrationText: null,
        onScreenText: null,
    }
}

function validateNarration(value: unknown, basePath: string, errors: ValidationIssue[]): string | null {
    if (!isPlainObject(value)) {
        errors.push(issue(
            'BEAT_PLAN_NARRATION_INVALID',
            basePath,
            'narration must be an object with a single text field when present.',
        ))
        return null
    }

    for (const key of Object.keys(value)) {
        if (key !== 'text') {
            errors.push(issue(
                'BEAT_PLAN_NARRATION_INVALID',
                `${basePath}.${key}`,
                `Unknown narration field "${key}"; narration v1 accepts only text (no provider, voice, file or TTS settings).`,
            ))
        }
    }

    if (!isNonEmptyString(value.text)) {
        errors.push(issue(
            'BEAT_PLAN_NARRATION_TEXT_REQUIRED',
            `${basePath}.text`,
            'narration.text is required and must be a non-empty string.',
        ))
        return null
    }

    return value.text
}

function validateEditorialEvidence(value: unknown, basePath: string, errors: ValidationIssue[]): void {
    if (!Array.isArray(value) || value.length === 0) {
        errors.push(issue(
            'BEAT_PLAN_EDITORIAL_EVIDENCE_REQUIRED',
            basePath,
            'editorialEvidence is required and must be a non-empty array.',
        ))
        return
    }

    const seen = new Set<string>()
    value.forEach((item, index) => {
        const itemPath = `${basePath}[${index}]`
        if (!isNonEmptyString(item)) {
            errors.push(issue(
                'BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID',
                itemPath,
                'editorialEvidence items must be non-empty strings.',
            ))
            return
        }
        if (isAbsoluteishPath(item) || hasUrlScheme(item)) {
            errors.push(issue(
                'BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID',
                itemPath,
                'editorialEvidence must hold conceptual identifiers, not absolute paths or URLs.',
            ))
            return
        }
        if (pathSegments(item).some((segment) => segment === '..')) {
            errors.push(issue(
                'BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID',
                itemPath,
                'editorialEvidence must not contain path traversal segments.',
            ))
            return
        }
        if (seen.has(item)) {
            errors.push(issue(
                'BEAT_PLAN_EDITORIAL_EVIDENCE_DUPLICATE',
                itemPath,
                `Editorial evidence "${item}" is duplicated in the same beat.`,
            ))
            return
        }
        seen.add(item)
    })
}

function validateSceneIds(value: unknown, basePath: string, errors: ValidationIssue[]): BeatSceneRef[] {
    if (!Array.isArray(value) || value.length === 0) {
        errors.push(issue(
            'BEAT_PLAN_SCENE_IDS_REQUIRED',
            basePath,
            'sceneIds is required and must be a non-empty array.',
        ))
        return []
    }

    const refs: BeatSceneRef[] = []
    const seen = new Set<string>()
    value.forEach((item, index) => {
        const itemPath = `${basePath}[${index}]`
        if (!isNonEmptyString(item)) {
            errors.push(issue(
                'BEAT_PLAN_SCENE_ID_INVALID',
                itemPath,
                'sceneIds items must be non-empty kebab-case strings.',
            ))
            return
        }
        if (!KEBAB_CASE_PATTERN.test(item)) {
            errors.push(issue(
                'BEAT_PLAN_SCENE_ID_INVALID',
                itemPath,
                'sceneIds items must be kebab-case (lowercase letters, digits and dashes).',
            ))
            return
        }
        if (seen.has(item)) {
            errors.push(issue(
                'BEAT_PLAN_SCENE_ID_DUPLICATE',
                itemPath,
                `sceneId "${item}" is duplicated inside the same beat.`,
            ))
            return
        }
        seen.add(item)
        refs.push({ id: item, path: itemPath })
    })

    return refs
}

function validateBeat(
    value: unknown,
    index: number,
    seenIds: Set<string>,
    errors: ValidationIssue[],
): ParsedBeat | null {
    const basePath = `beats[${index}]`
    const parsed = emptyParsedBeat(index)

    if (!isPlainObject(value)) {
        errors.push(issue(
            'BEAT_PLAN_BEAT_INVALID',
            basePath,
            'Each beat must be an object.',
        ))
        return null
    }

    for (const key of Object.keys(value)) {
        if (!(BEAT_FIELDS as readonly string[]).includes(key)) {
            errors.push(issue(
                'BEAT_PLAN_BEAT_INVALID',
                `${basePath}.${key}`,
                `Unknown beat field "${key}"; the schema does not allow additional properties.`,
            ))
        }
    }

    if (value.id === undefined || !isNonEmptyString(value.id)) {
        errors.push(issue(
            'BEAT_PLAN_BEAT_ID_REQUIRED',
            `${basePath}.id`,
            'beat.id is required and must be a non-empty string.',
        ))
    } else if (!KEBAB_CASE_PATTERN.test(value.id)) {
        errors.push(issue(
            'BEAT_PLAN_BEAT_ID_INVALID',
            `${basePath}.id`,
            'beat.id must be kebab-case (lowercase letters, digits and dashes).',
        ))
    } else if (seenIds.has(value.id)) {
        errors.push(issue(
            'BEAT_PLAN_BEAT_ID_DUPLICATE',
            `${basePath}.id`,
            `Beat id "${value.id}" is duplicated in the beat plan.`,
        ))
    } else {
        seenIds.add(value.id)
    }

    if (!isSafePositiveInteger(value.order)) {
        errors.push(issue(
            'BEAT_PLAN_ORDER_INVALID',
            `${basePath}.order`,
            'beat.order is required and must be a safe integer greater than or equal to 1.',
        ))
    } else {
        parsed.order = value.order
    }

    parsed.sceneRefs = validateSceneIds(value.sceneIds, `${basePath}.sceneIds`, errors)

    const narrativeFunction = value.narrativeFunction
    if (
        typeof narrativeFunction !== 'string' ||
        !(BEAT_NARRATIVE_FUNCTIONS as readonly string[]).includes(narrativeFunction)
    ) {
        errors.push(issue(
            'BEAT_PLAN_NARRATIVE_FUNCTION_INVALID',
            `${basePath}.narrativeFunction`,
            `beat.narrativeFunction must be one of: ${BEAT_NARRATIVE_FUNCTIONS.join(', ')}.`,
        ))
    }

    if (!isSafeNonNegativeInteger(value.startMs)) {
        errors.push(issue(
            'BEAT_PLAN_START_INVALID',
            `${basePath}.startMs`,
            'beat.startMs is required and must be a safe integer greater than or equal to zero.',
        ))
    } else {
        parsed.startMs = value.startMs
    }

    if (!isSafePositiveInteger(value.durationMs)) {
        errors.push(issue(
            'BEAT_PLAN_DURATION_INVALID',
            `${basePath}.durationMs`,
            'beat.durationMs is required and must be a safe integer greater than zero.',
        ))
    } else {
        parsed.durationMs = value.durationMs
    }

    if (value.narration !== undefined) {
        parsed.narrationText = validateNarration(value.narration, `${basePath}.narration`, errors)
    }

    if (value.onScreenText !== undefined) {
        if (!isNonEmptyString(value.onScreenText)) {
            errors.push(issue(
                'BEAT_PLAN_ON_SCREEN_TEXT_INVALID',
                `${basePath}.onScreenText`,
                'beat.onScreenText must be a non-empty string when present.',
            ))
        } else {
            parsed.onScreenText = value.onScreenText
        }
    }

    if (!isNonEmptyString(value.visualIntent)) {
        errors.push(issue(
            'BEAT_PLAN_VISUAL_INTENT_REQUIRED',
            `${basePath}.visualIntent`,
            'beat.visualIntent is required and must be a non-empty declarative description.',
        ))
    }

    const motionIntent = value.motionIntent
    if (typeof motionIntent !== 'string' || !(BEAT_MOTION_INTENTS as readonly string[]).includes(motionIntent)) {
        errors.push(issue(
            'BEAT_PLAN_MOTION_INTENT_INVALID',
            `${basePath}.motionIntent`,
            `beat.motionIntent must be one of: ${BEAT_MOTION_INTENTS.join(', ')}.`,
        ))
    }

    const transitionIn = value.transitionIn
    if (typeof transitionIn !== 'string' || !(BEAT_TRANSITIONS as readonly string[]).includes(transitionIn)) {
        errors.push(issue(
            'BEAT_PLAN_TRANSITION_IN_INVALID',
            `${basePath}.transitionIn`,
            `beat.transitionIn must be one of: ${BEAT_TRANSITIONS.join(', ')}.`,
        ))
    }

    const transitionOut = value.transitionOut
    if (typeof transitionOut !== 'string' || !(BEAT_TRANSITIONS as readonly string[]).includes(transitionOut)) {
        errors.push(issue(
            'BEAT_PLAN_TRANSITION_OUT_INVALID',
            `${basePath}.transitionOut`,
            `beat.transitionOut must be one of: ${BEAT_TRANSITIONS.join(', ')}.`,
        ))
    }

    validateEditorialEvidence(value.editorialEvidence, `${basePath}.editorialEvidence`, errors)

    const validationStatus = value.validationStatus
    if (
        typeof validationStatus !== 'string' ||
        !(BEAT_VALIDATION_STATUSES as readonly string[]).includes(validationStatus)
    ) {
        errors.push(issue(
            'BEAT_PLAN_VALIDATION_STATUS_INVALID',
            `${basePath}.validationStatus`,
            `beat.validationStatus must be one of: ${BEAT_VALIDATION_STATUSES.join(', ')}. "validated" is technical only and grants no editorial or publishing authorization.`,
        ))
    }

    return parsed
}

/**
 * order: unico, continuo a partir de 1 e igual a posicao no array. Nenhum
 * reordenamento nem correcao automatica e feita: apenas se reporta.
 */
function validateBeatOrdering(beats: ParsedBeat[], errors: ValidationIssue[]): void {
    const seen = new Set<number>()
    let duplicated = false
    let incomplete = false

    for (const beat of beats) {
        if (beat.order === null) {
            incomplete = true
            continue
        }
        if (seen.has(beat.order)) {
            errors.push(issue(
                'BEAT_PLAN_ORDER_DUPLICATE',
                `beats[${beat.index}].order`,
                `beat.order ${beat.order} is duplicated in the beat plan.`,
            ))
            duplicated = true
            continue
        }
        seen.add(beat.order)
    }

    if (duplicated || incomplete) return

    for (let position = 1; position < beats.length; position++) {
        const previous = beats[position - 1]
        const current = beats[position]
        if (previous === undefined || current === undefined) continue
        if (previous.order === null || current.order === null) continue
        if (current.order <= previous.order) {
            errors.push(issue(
                'BEAT_PLAN_ARRAY_ORDER_MISMATCH',
                `beats[${current.index}].order`,
                `The beats array must be sorted by order: beat at index ${current.index} has order ${current.order} after order ${previous.order}.`,
            ))
            return
        }
    }

    for (let position = 0; position < beats.length; position++) {
        const beat = beats[position]
        if (beat === undefined || beat.order === null) continue
        if (beat.order !== position + 1) {
            errors.push(issue(
                'BEAT_PLAN_ORDER_SEQUENCE_INVALID',
                `beats[${beat.index}].order`,
                `beat.order must form a continuous sequence starting at 1: expected ${position + 1}, found ${beat.order}.`,
            ))
            return
        }
    }
}

function validateMetadata(
    value: unknown,
    errors: ValidationIssue[],
): string | null {
    if (!isPlainObject(value)) {
        errors.push(issue(
            'BEAT_PLAN_METADATA_INVALID',
            'metadata',
            'metadata must be an object when present.',
        ))
        return null
    }

    for (const key of Object.keys(value)) {
        if (!(METADATA_FIELDS as readonly string[]).includes(key)) {
            errors.push(issue(
                'BEAT_PLAN_METADATA_INVALID',
                `metadata.${key}`,
                `Unknown metadata field "${key}"; only status, description and tags are allowed.`,
            ))
        }
    }

    let metadataStatus: string | null = null
    if (value.status !== undefined) {
        const status = value.status
        if (typeof status !== 'string' || !(BEAT_PLAN_METADATA_STATUSES as readonly string[]).includes(status)) {
            errors.push(issue(
                'BEAT_PLAN_METADATA_STATUS_INVALID',
                'metadata.status',
                `metadata.status must be one of: ${BEAT_PLAN_METADATA_STATUSES.join(', ')}.`,
            ))
        } else {
            metadataStatus = status
        }
    }

    if (value.description !== undefined && !isNonEmptyString(value.description)) {
        errors.push(issue(
            'BEAT_PLAN_METADATA_DESCRIPTION_INVALID',
            'metadata.description',
            'metadata.description must be a non-empty string when present.',
        ))
    }

    if (value.tags !== undefined) {
        if (!Array.isArray(value.tags)) {
            errors.push(issue(
                'BEAT_PLAN_METADATA_TAG_INVALID',
                'metadata.tags',
                'metadata.tags must be an array of non-empty strings.',
            ))
        } else if (value.tags.length > BEAT_PLAN_MAX_TAGS) {
            errors.push(issue(
                'BEAT_PLAN_METADATA_TAG_LIMIT',
                'metadata.tags',
                `metadata.tags accepts at most ${BEAT_PLAN_MAX_TAGS} items.`,
            ))
        } else {
            const seen = new Set<string>()
            value.tags.forEach((tag, index) => {
                if (!isNonEmptyString(tag)) {
                    errors.push(issue(
                        'BEAT_PLAN_METADATA_TAG_INVALID',
                        `metadata.tags[${index}]`,
                        'metadata.tags items must be non-empty strings.',
                    ))
                    return
                }
                if (seen.has(tag)) {
                    errors.push(issue(
                        'BEAT_PLAN_METADATA_TAG_DUPLICATE',
                        `metadata.tags[${index}]`,
                        `Tag "${tag}" is duplicated.`,
                    ))
                    return
                }
                seen.add(tag)
            })
        }
    }

    return metadataStatus
}

function validateStructure(input: unknown, errors: ValidationIssue[]): StructureScan {
    const scan: StructureScan = {
        beatPlanId: null,
        projectId: null,
        compositionId: null,
        schemaVersion: null,
        locale: null,
        beatCount: 0,
        beats: [],
        narrationBeatCount: 0,
        onScreenTextBeatCount: 0,
        metadataStatus: null,
    }

    if (!isPlainObject(input)) {
        errors.push(issue(
            'BEAT_PLAN_MANIFEST_INVALID',
            '',
            'Beat plan must be a JSON object.',
        ))
        return scan
    }

    const record = input

    for (const key of Object.keys(record)) {
        if (!(BEAT_PLAN_TOP_LEVEL_FIELDS as readonly string[]).includes(key)) {
            errors.push(issue(
                'BEAT_PLAN_UNKNOWN_FIELD',
                key,
                `Unknown top-level field "${key}"; the schema does not allow additional properties.`,
            ))
        }
    }

    if (record.schemaVersion !== BEAT_PLAN_SCHEMA_VERSION) {
        errors.push(issue(
            'BEAT_PLAN_SCHEMA_VERSION_UNSUPPORTED',
            'schemaVersion',
            `schemaVersion must be ${BEAT_PLAN_SCHEMA_VERSION}.`,
        ))
    }

    if (record.projectId === undefined || !isNonEmptyString(record.projectId)) {
        errors.push(issue(
            'BEAT_PLAN_PROJECT_ID_REQUIRED',
            'projectId',
            'projectId is required and must be a non-empty string.',
        ))
    } else if (!KEBAB_CASE_PATTERN.test(record.projectId)) {
        errors.push(issue(
            'BEAT_PLAN_PROJECT_ID_INVALID',
            'projectId',
            'projectId must be kebab-case (lowercase letters, digits and dashes).',
        ))
    } else {
        scan.projectId = record.projectId
    }

    if (record.compositionId === undefined || !isNonEmptyString(record.compositionId)) {
        errors.push(issue(
            'BEAT_PLAN_COMPOSITION_ID_REQUIRED',
            'compositionId',
            'compositionId is required and must be a non-empty string.',
        ))
    } else if (!KEBAB_CASE_PATTERN.test(record.compositionId)) {
        errors.push(issue(
            'BEAT_PLAN_COMPOSITION_ID_INVALID',
            'compositionId',
            'compositionId must be kebab-case (lowercase letters, digits and dashes).',
        ))
    } else {
        scan.compositionId = record.compositionId
    }

    if (record.id === undefined || !isNonEmptyString(record.id)) {
        errors.push(issue(
            'BEAT_PLAN_ID_REQUIRED',
            'id',
            'id is required and must be a non-empty string.',
        ))
    } else if (!KEBAB_CASE_PATTERN.test(record.id)) {
        errors.push(issue(
            'BEAT_PLAN_ID_INVALID',
            'id',
            'id must be kebab-case (lowercase letters, digits and dashes).',
        ))
    } else {
        scan.beatPlanId = record.id
    }

    if (!isNonEmptyString(record.locale)) {
        errors.push(issue(
            'BEAT_PLAN_LOCALE_REQUIRED',
            'locale',
            'locale is required and must be a non-empty string.',
        ))
    } else {
        scan.locale = record.locale
    }

    if (!Array.isArray(record.beats)) {
        errors.push(issue(
            'BEAT_PLAN_BEATS_REQUIRED',
            'beats',
            'beats is required and must be a non-empty array.',
        ))
    } else if (record.beats.length === 0) {
        errors.push(issue(
            'BEAT_PLAN_BEATS_REQUIRED',
            'beats',
            'beats must not be empty: a beat plan needs at least one beat.',
        ))
    } else {
        const seenIds = new Set<string>()
        record.beats.forEach((beat, index) => {
            if (isPlainObject(beat)) scan.beatCount++
            const parsed = validateBeat(beat, index, seenIds, errors)
            if (parsed === null) return
            scan.beats.push(parsed)
            if (parsed.narrationText !== null) scan.narrationBeatCount++
            if (parsed.onScreenText !== null) scan.onScreenTextBeatCount++
        })
        validateBeatOrdering(scan.beats, errors)
    }

    if (record.metadata !== undefined) {
        scan.metadataStatus = validateMetadata(record.metadata, errors)
    }

    scan.schemaVersion = typeof record.schemaVersion === 'number' ? record.schemaVersion : null

    return scan
}

/** Cenas da Composition informada, em ordem estavel, somente quando confiavel. */
function compositionSceneRefs(compositionInput: unknown): SceneRef[] {
    if (!isPlainObject(compositionInput)) return []
    const scenes = compositionInput.scenes
    if (!Array.isArray(scenes)) return []

    const refs: SceneRef[] = []
    scenes.forEach((scene, index) => {
        if (isPlainObject(scene) && isNonEmptyString(scene.id)) {
            refs.push({ id: scene.id, path: `composition.scenes[${index}].id` })
        }
    })
    return refs
}

interface TimelineScan {
    totalDurationMs: number | null
    overflow: boolean
    planEndMs: number | null
}

/**
 * Timeline estritamente linear na v1: comeca em zero, contigua, sem lacunas,
 * sem sobreposicao. Sobreposicao, trilhas paralelas e lacunas intencionais
 * ficam fora da v1. Nenhum tempo e corrigido automaticamente.
 */
function validateTimeline(beats: ParsedBeat[], errors: ValidationIssue[]): TimelineScan {
    let totalDurationMs = 0
    let overflow = false
    let previousEndMs: number | null = null
    let planEndMs: number | null = null

    beats.forEach((beat, position) => {
        const basePath = `beats[${beat.index}]`

        if (beat.startMs === null || beat.durationMs === null) {
            previousEndMs = null
            planEndMs = null
            return
        }

        if (position === 0) {
            if (beat.startMs !== 0) {
                errors.push(issue(
                    'BEAT_PLAN_TIMELINE_START_INVALID',
                    `${basePath}.startMs`,
                    'The first beat must start at 0 ms.',
                ))
            }
        } else if (previousEndMs !== null) {
            if (beat.startMs > previousEndMs) {
                errors.push(issue(
                    'BEAT_PLAN_TIMELINE_GAP',
                    `${basePath}.startMs`,
                    `Beat starts at ${beat.startMs} ms, after the previous beat ended at ${previousEndMs} ms; the v1 timeline must be contiguous.`,
                ))
            } else if (beat.startMs < previousEndMs) {
                errors.push(issue(
                    'BEAT_PLAN_TIMELINE_OVERLAP',
                    `${basePath}.startMs`,
                    `Beat starts at ${beat.startMs} ms, before the previous beat ended at ${previousEndMs} ms; the v1 timeline must not overlap.`,
                ))
            }
        }

        const beatEndMs = beat.startMs + beat.durationMs
        if (beatEndMs > Number.MAX_SAFE_INTEGER || totalDurationMs + beat.durationMs > Number.MAX_SAFE_INTEGER) {
            overflow = true
            previousEndMs = null
            planEndMs = null
            return
        }

        totalDurationMs += beat.durationMs
        previousEndMs = beatEndMs
        planEndMs = beatEndMs
    })

    if (overflow) {
        errors.push(issue(
            'BEAT_PLAN_DURATION_OVERFLOW',
            'beats',
            'Beat timing exceeds Number.MAX_SAFE_INTEGER; derived durations are reported as null instead of an approximate value.',
        ))
        return { totalDurationMs: null, overflow: true, planEndMs: null }
    }

    return { totalDurationMs, overflow: false, planEndMs }
}

function buildWarnings(
    scan: StructureScan,
    sceneRefs: SceneRef[],
    compositionReliable: boolean,
    referencedSceneIds: Set<string>,
): ValidationIssue[] {
    const warnings: ValidationIssue[] = []
    if (scan.beats.length === 0) return warnings

    if (!scan.beats.some((beat) => beat.narrationText !== null)) {
        warnings.push(issue(
            'BEAT_PLAN_NARRATION_MISSING',
            'beats',
            'No beat declares narration; pieces without narration are allowed and this is not an editorial judgement.',
        ))
    }

    if (!scan.beats.some((beat) => beat.onScreenText !== null)) {
        warnings.push(issue(
            'BEAT_PLAN_ON_SCREEN_TEXT_MISSING',
            'beats',
            'No beat declares onScreenText; pieces without on-screen text are allowed and this is not an editorial judgement.',
        ))
    }

    for (const beat of scan.beats) {
        const basePath = `beats[${beat.index}]`

        if (beat.narrationText !== null && beat.narrationText.length > BEAT_PLAN_MAX_NARRATION_LENGTH) {
            warnings.push(issue(
                'BEAT_PLAN_NARRATION_TEXT_LONG',
                `${basePath}.narration.text`,
                `Narration text has ${beat.narrationText.length} characters; more than ${BEAT_PLAN_MAX_NARRATION_LENGTH} is a technical heuristic, not editorial approval.`,
            ))
        }

        if (beat.onScreenText === null) continue

        if (beat.onScreenText.length > BEAT_PLAN_MAX_ON_SCREEN_TEXT_LENGTH) {
            warnings.push(issue(
                'BEAT_PLAN_ON_SCREEN_TEXT_LONG',
                `${basePath}.onScreenText`,
                `On-screen text has ${beat.onScreenText.length} characters; more than ${BEAT_PLAN_MAX_ON_SCREEN_TEXT_LENGTH} is a technical heuristic, not editorial approval.`,
            ))
        }

        if (beat.durationMs !== null) {
            const minimumReadingMs = estimatedMinimumReadingMs(beat.onScreenText)
            if (beat.durationMs < minimumReadingMs) {
                warnings.push(issue(
                    'BEAT_PLAN_READING_TIME_RISK',
                    `${basePath}.durationMs`,
                    `Beat lasts ${beat.durationMs} ms but its on-screen text needs an estimated minimum of ${minimumReadingMs} ms to be read; heuristic only, it does not replace timed human reading.`,
                ))
            }
        }
    }

    if (!compositionReliable) return warnings

    for (const scene of sceneRefs) {
        if (referencedSceneIds.has(scene.id)) continue
        warnings.push(issue(
            'BEAT_PLAN_SCENE_UNREFERENCED',
            scene.path,
            `Composition scene "${scene.id}" is not referenced by any beat; BeatPlan v1 does not require every scene to be referenced.`,
        ))
    }

    return warnings
}

/**
 * Valida um BeatPlan contra um ProjectManifest e uma Composition informados
 * explicitamente. Os tres sao dados de entrada: o nucleo nao le arquivos, nao
 * acessa rede e nao conhece projetos especificos. As entradas nao sao mutadas.
 */
export function validateBeatPlan(
    beatPlanInput: unknown,
    compositionInput: unknown,
    projectInput: unknown,
): BeatPlanValidationReport {
    const errors: ValidationIssue[] = []

    const projectReport = validateProjectManifest(projectInput)
    let compositionReport: CompositionValidationReport | null = null

    if (!projectReport.valid) {
        errors.push(issue(
            'BEAT_PLAN_PROJECT_MANIFEST_INVALID',
            'project',
            `The supplied ProjectManifest is invalid: ${projectReport.errors.length} error(s).`,
        ))
    } else {
        compositionReport = validateComposition(compositionInput, projectInput)
        if (!compositionReport.valid) {
            errors.push(issue(
                'BEAT_PLAN_COMPOSITION_INVALID',
                'composition',
                `The supplied Composition is invalid for this project: ${compositionReport.errors.length} error(s).`,
            ))
        }
    }

    const scan = validateStructure(beatPlanInput, errors)
    const compositionReliable = compositionReport !== null && compositionReport.valid
    const sceneRefs = compositionReliable ? compositionSceneRefs(compositionInput) : []
    const knownSceneIds = new Set(sceneRefs.map((scene) => scene.id))
    const referencedSceneIds = new Set<string>()

    if (compositionReliable && isPlainObject(beatPlanInput)) {
        const project = projectInput as Record<string, unknown>
        const composition = compositionInput as Record<string, unknown>

        if (scan.projectId !== null && scan.projectId !== project.id) {
            errors.push(issue(
                'BEAT_PLAN_PROJECT_ID_MISMATCH',
                'projectId',
                `beatPlan.projectId "${scan.projectId}" does not match project.id "${String(project.id)}".`,
            ))
        }

        if (scan.compositionId !== null && scan.compositionId !== composition.id) {
            errors.push(issue(
                'BEAT_PLAN_COMPOSITION_ID_MISMATCH',
                'compositionId',
                `beatPlan.compositionId "${scan.compositionId}" does not match composition.id "${String(composition.id)}".`,
            ))
        }

        if (scan.locale !== null) {
            if (scan.locale !== project.locale) {
                errors.push(issue(
                    'BEAT_PLAN_LOCALE_MISMATCH',
                    'locale',
                    `beatPlan.locale "${scan.locale}" does not match project.locale "${String(project.locale)}".`,
                ))
            } else if (scan.locale !== composition.locale) {
                errors.push(issue(
                    'BEAT_PLAN_LOCALE_MISMATCH',
                    'locale',
                    `beatPlan.locale "${scan.locale}" does not match composition.locale "${String(composition.locale)}".`,
                ))
            }
        }

        for (const beat of scan.beats) {
            for (const sceneRef of beat.sceneRefs) {
                if (knownSceneIds.has(sceneRef.id)) {
                    referencedSceneIds.add(sceneRef.id)
                    continue
                }
                errors.push(issue(
                    'BEAT_PLAN_SCENE_NOT_FOUND',
                    sceneRef.path,
                    `sceneId "${sceneRef.id}" does not exist in the supplied Composition.`,
                ))
            }
        }
    }

    const timeline = validateTimeline(scan.beats, errors)

    if (
        !timeline.overflow &&
        compositionReliable &&
        compositionReport !== null &&
        compositionReport.totalDurationMs !== null &&
        timeline.planEndMs !== null &&
        timeline.planEndMs !== compositionReport.totalDurationMs
    ) {
        errors.push(issue(
            'BEAT_PLAN_TIMELINE_END_MISMATCH',
            'beats',
            `The last beat ends at ${timeline.planEndMs} ms but the Composition lasts ${compositionReport.totalDurationMs} ms; the beat plan must end exactly with the composition.`,
        ))
    }

    const warnings = buildWarnings(scan, sceneRefs, compositionReliable, referencedSceneIds)

    return {
        valid: errors.length === 0,
        errors,
        warnings,
        summary: errors.length === 0 ? BEAT_PLAN_VALID_SUMMARY : beatPlanInvalidSummary(errors.length),
        projectId: scan.projectId,
        compositionId: scan.compositionId,
        beatPlanId: scan.beatPlanId,
        schemaVersion: scan.schemaVersion,
        beatCount: scan.beatCount,
        compositionSceneCount: compositionReliable && compositionReport !== null ? compositionReport.sceneCount : 0,
        referencedSceneCount: referencedSceneIds.size,
        totalDurationMs: timeline.totalDurationMs,
        compositionDurationMs: compositionReliable && compositionReport !== null ? compositionReport.totalDurationMs : null,
        narrationBeatCount: scan.narrationBeatCount,
        onScreenTextBeatCount: scan.onScreenTextBeatCount,
        metadataStatus: scan.metadataStatus,
    }
}
