/**
 * Validador puro do CreativeExecutionPackage v1.
 *
 * Verifica estrutura, schemaVersion, IDs, output, timeline (ordem, startMs,
 * endMs, contiguidade), duracao consolidada, artefatos esperados, unicidade
 * de IDs, source references e ausencia de propriedades extras. A forma
 * estrutural tambem e espelhada em schemas/creative-execution-package.schema.json
 * (draft-07); as regras semanticas entre campos (contiguidade, igualdade de
 * duracoes, derivacao do packageId, consistencia de source) vivem apenas aqui.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 * Codigos estaveis e ordem de emissao fixa; a automacao deve confiar nos
 * codigos, nao nas mensagens livres.
 */

import {
    BEAT_MOTION_INTENTS,
    BEAT_NARRATIVE_FUNCTIONS,
    BEAT_TRANSITIONS,
} from './beat-plan-contract.js'
import {
    deriveExecutionPackageId,
    EXECUTION_PACKAGE_ID_MAX_LENGTH,
    EXECUTION_PACKAGE_SCHEMA_VERSION,
    EXECUTION_PACKAGE_TOP_LEVEL_FIELDS,
    EXPECTED_ARTIFACT_KINDS,
    executionPackageInvalidSummary,
    EXECUTION_PACKAGE_VALID_SUMMARY,
} from './creative-execution-package-contract.js'
import { KEBAB_CASE_PATTERN } from './project-contract.js'
import { containsControlCharacter } from './relative-path.js'
import { issue, type ValidationIssue } from './validation-report.js'

export interface CreativeExecutionPackageValidationReport {
    readonly valid: boolean
    readonly errors: readonly ValidationIssue[]
    readonly warnings: readonly ValidationIssue[]
    readonly summary: string
    readonly packageId: string | null
}

const OUTPUT_FIELDS = [
    'profileId',
    'mediaKind',
    'width',
    'height',
    'aspectRatio',
    'fps',
    'plannedContainer',
    'rendererAdapter',
    'durationMs',
] as const

const STEP_FIELDS = [
    'order',
    'beatId',
    'sceneIds',
    'startMs',
    'durationMs',
    'endMs',
    'narrativeFunction',
    'motionIntent',
    'transitionIn',
    'transitionOut',
    'onScreenText',
    'narrationText',
] as const

const ARTIFACT_FIELDS = ['id', 'kind', 'required', 'logicalName', 'contentType'] as const

const SOURCE_FIELDS = [
    'projectId',
    'compositionId',
    'outputPlanId',
    'beatPlanId',
    'projectSchemaVersion',
    'compositionSchemaVersion',
    'outputPlanSchemaVersion',
    'beatPlanSchemaVersion',
] as const

const PACKAGE_ID_PATTERN = /^execution-[a-z0-9]+(-[a-z0-9]+)*$/
const PACKAGE_HASH_ID_PATTERN = /^execution-v1-[0-9a-f]{64}$/
const ASPECT_RATIO_PATTERN = /^\d+:\d+$/

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

function isKebab(value: unknown): value is string {
    return typeof value === 'string' && KEBAB_CASE_PATTERN.test(value)
}

function isPositiveSafeInteger(value: unknown): value is number {
    return typeof value === 'number' && Number.isSafeInteger(value) && value > 0
}

function unknownFields(value: Record<string, unknown>, allowed: readonly string[], pathPrefix: string, errors: ValidationIssue[]): void {
    for (const field of Object.keys(value)) {
        if (!allowed.includes(field)) {
            errors.push(issue('EXECUTION_PACKAGE_UNKNOWN_FIELD', `${pathPrefix}${field}`, `Unknown field "${field}" is not part of the execution package contract.`))
        }
    }
}

function isLogicalFileName(value: unknown): value is string {
    return isNonEmptyString(value)
        && !containsControlCharacter(value)
        && !value.includes('/')
        && !value.includes('\\')
        && !value.includes('..')
}

/**
 * Valida um pacote de execucao completo. A entrada nunca e mutada; o
 * relatorio ecoa o packageId declarado quando disponivel como string.
 */
export function validateCreativeExecutionPackage(input: unknown): CreativeExecutionPackageValidationReport {
    const errors: ValidationIssue[] = []

    if (!isPlainObject(input)) {
        errors.push(issue('EXECUTION_PACKAGE_INVALID', '', 'Execution package must be a JSON object.'))
        return { valid: false, errors, warnings: [], summary: executionPackageInvalidSummary(errors.length), packageId: null }
    }

    const packageId = isNonEmptyString(input.packageId) ? input.packageId : null

    if (input.schemaVersion !== EXECUTION_PACKAGE_SCHEMA_VERSION) {
        errors.push(issue('EXECUTION_PACKAGE_SCHEMA_VERSION_UNSUPPORTED', 'schemaVersion', `schemaVersion must be the integer ${EXECUTION_PACKAGE_SCHEMA_VERSION}.`))
    }
    unknownFields(input, EXECUTION_PACKAGE_TOP_LEVEL_FIELDS, '', errors)

    if (packageId === null) {
        errors.push(issue('EXECUTION_PACKAGE_ID_INVALID', 'packageId', 'packageId is required and must be a non-empty string.'))
    } else if (
        packageId.length > EXECUTION_PACKAGE_ID_MAX_LENGTH
        || (!PACKAGE_ID_PATTERN.test(packageId) && !PACKAGE_HASH_ID_PATTERN.test(packageId))
    ) {
        errors.push(issue('EXECUTION_PACKAGE_ID_INVALID', 'packageId', 'packageId must be the readable execution-<ids> form or the execution-v1-<sha256> form, within the documented limit.'))
    }

    const idFields = ['projectId', 'compositionId', 'outputPlanId', 'beatPlanId'] as const
    const idErrorCodes: Record<(typeof idFields)[number], string> = {
        projectId: 'EXECUTION_PACKAGE_PROJECT_ID_INVALID',
        compositionId: 'EXECUTION_PACKAGE_COMPOSITION_ID_INVALID',
        outputPlanId: 'EXECUTION_PACKAGE_OUTPUT_PLAN_ID_INVALID',
        beatPlanId: 'EXECUTION_PACKAGE_BEAT_PLAN_ID_INVALID',
    }
    const ids: Record<string, string> = {}
    for (const field of idFields) {
        const value = input[field]
        if (!isKebab(value)) {
            errors.push(issue(idErrorCodes[field], field, `${field} is required and must be kebab-case.`))
        } else {
            ids[field] = value
        }
    }

    if (
        packageId !== null
        && (PACKAGE_ID_PATTERN.test(packageId) || PACKAGE_HASH_ID_PATTERN.test(packageId))
        && idFields.every((field) => ids[field] !== undefined)
    ) {
        const expected = deriveExecutionPackageId({
            projectId: ids.projectId as string,
            compositionId: ids.compositionId as string,
            outputPlanId: ids.outputPlanId as string,
            beatPlanId: ids.beatPlanId as string,
        })
        if (packageId !== expected) {
            errors.push(issue('EXECUTION_PACKAGE_ID_MISMATCH', 'packageId', 'packageId does not match the deterministic derivation from the declared source ids.'))
        }
    }

    // output
    let outputDurationMs: number | null = null
    const output = input.output
    if (!isPlainObject(output)) {
        errors.push(issue('EXECUTION_PACKAGE_OUTPUT_INVALID', 'output', 'output is required and must be an object.'))
    } else {
        unknownFields(output, OUTPUT_FIELDS, 'output.', errors)
        if (!isKebab(output.profileId)) {
            errors.push(issue('EXECUTION_PACKAGE_OUTPUT_PROFILE_INVALID', 'output.profileId', 'output.profileId must be kebab-case.'))
        }
        if (output.mediaKind !== 'video') {
            errors.push(issue('EXECUTION_PACKAGE_OUTPUT_MEDIA_KIND_INVALID', 'output.mediaKind', 'output.mediaKind must be "video" in v1.'))
        }
        if (!isPositiveSafeInteger(output.width) || !isPositiveSafeInteger(output.height)) {
            errors.push(issue('EXECUTION_PACKAGE_OUTPUT_DIMENSIONS_INVALID', 'output.width', 'output.width and output.height must be positive safe integers.'))
        }
        if (typeof output.aspectRatio !== 'string' || !ASPECT_RATIO_PATTERN.test(output.aspectRatio)) {
            errors.push(issue('EXECUTION_PACKAGE_OUTPUT_ASPECT_RATIO_INVALID', 'output.aspectRatio', 'output.aspectRatio must have the W:H form with positive integers.'))
        }
        if (typeof output.fps !== 'number' || !Number.isSafeInteger(output.fps) || output.fps < 1 || output.fps > 120) {
            errors.push(issue('EXECUTION_PACKAGE_OUTPUT_FPS_INVALID', 'output.fps', 'output.fps must be an integer between 1 and 120.'))
        }
        if (output.plannedContainer !== undefined && output.plannedContainer !== 'mp4' && output.plannedContainer !== 'webm') {
            errors.push(issue('EXECUTION_PACKAGE_OUTPUT_CONTAINER_INVALID', 'output.plannedContainer', 'output.plannedContainer, when present, must be "mp4" or "webm".'))
        }
        if (!isKebab(output.rendererAdapter)) {
            errors.push(issue('EXECUTION_PACKAGE_OUTPUT_RENDERER_INVALID', 'output.rendererAdapter', 'output.rendererAdapter must be kebab-case.'))
        }
        if (!isPositiveSafeInteger(output.durationMs)) {
            errors.push(issue('EXECUTION_PACKAGE_OUTPUT_DURATION_INVALID', 'output.durationMs', 'output.durationMs must be a positive safe integer.'))
        } else {
            outputDurationMs = output.durationMs
        }
    }

    // timeline
    let lastEndMs: number | null = null
    const timeline = input.timeline
    if (!Array.isArray(timeline) || timeline.length === 0) {
        errors.push(issue('EXECUTION_PACKAGE_TIMELINE_INVALID', 'timeline', 'timeline is required and must be a non-empty array.'))
    } else {
        const seenBeatIds = new Set<string>()
        let expectedStartMs = 0
        timeline.forEach((step, index) => {
            const path = `timeline[${index}]`
            if (!isPlainObject(step)) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_INVALID', path, 'Each timeline step must be an object.'))
                return
            }
            unknownFields(step, STEP_FIELDS, `${path}.`, errors)
            if (step.order !== index + 1) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_ORDER_INVALID', `${path}.order`, 'order must be unique, contiguous from 1 and equal to the array position.'))
            }
            if (!isKebab(step.beatId)) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_BEAT_ID_INVALID', `${path}.beatId`, 'beatId must be kebab-case.'))
            } else if (seenBeatIds.has(step.beatId)) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_BEAT_ID_DUPLICATE', `${path}.beatId`, `Duplicate beatId "${step.beatId}".`))
            } else {
                seenBeatIds.add(step.beatId)
            }
            if (
                !Array.isArray(step.sceneIds)
                || step.sceneIds.length === 0
                || step.sceneIds.some((sceneId) => !isKebab(sceneId))
                || new Set(step.sceneIds).size !== step.sceneIds.length
            ) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_SCENES_INVALID', `${path}.sceneIds`, 'sceneIds must be a non-empty array of unique kebab-case ids.'))
            }
            if (typeof step.startMs !== 'number' || !Number.isSafeInteger(step.startMs) || step.startMs < 0 || step.startMs !== expectedStartMs) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_START_INVALID', `${path}.startMs`, 'startMs must be a non-negative safe integer; the first step starts at 0 and the timeline is contiguous.'))
            }
            if (!isPositiveSafeInteger(step.durationMs)) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_DURATION_INVALID', `${path}.durationMs`, 'durationMs must be a positive safe integer.'))
            }
            const endOk = typeof step.startMs === 'number'
                && typeof step.durationMs === 'number'
                && Number.isSafeInteger(step.startMs + step.durationMs)
                && step.endMs === step.startMs + step.durationMs
            if (!endOk) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_END_INVALID', `${path}.endMs`, 'endMs must equal startMs + durationMs as a safe integer.'))
            } else {
                expectedStartMs = step.endMs as number
                lastEndMs = step.endMs as number
            }
            if (
                !(BEAT_NARRATIVE_FUNCTIONS as readonly string[]).includes(step.narrativeFunction as string)
                || !(BEAT_MOTION_INTENTS as readonly string[]).includes(step.motionIntent as string)
                || !(BEAT_TRANSITIONS as readonly string[]).includes(step.transitionIn as string)
                || !(BEAT_TRANSITIONS as readonly string[]).includes(step.transitionOut as string)
            ) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_ENUM_INVALID', `${path}.narrativeFunction`, 'narrativeFunction, motionIntent and transitions must use the neutral BeatPlan enums.'))
            }
            if (
                (step.onScreenText !== undefined && !isNonEmptyString(step.onScreenText))
                || (step.narrationText !== undefined && !isNonEmptyString(step.narrationText))
            ) {
                errors.push(issue('EXECUTION_PACKAGE_STEP_TEXT_INVALID', `${path}.onScreenText`, 'onScreenText and narrationText, when present, must be non-empty strings.'))
            }
        })
    }

    if (outputDurationMs !== null && lastEndMs !== null && outputDurationMs !== lastEndMs) {
        errors.push(issue('EXECUTION_PACKAGE_DURATION_MISMATCH', 'output.durationMs', 'output.durationMs must equal the end of the last timeline step.'))
    }

    // expectedArtifacts
    const artifacts = input.expectedArtifacts
    if (!Array.isArray(artifacts) || artifacts.length === 0) {
        errors.push(issue('EXECUTION_PACKAGE_ARTIFACTS_INVALID', 'expectedArtifacts', 'expectedArtifacts is required and must be a non-empty array.'))
    } else {
        const seenIds = new Set<string>()
        const kindCounts = new Map<string, number>()
        artifacts.forEach((artifact, index) => {
            const path = `expectedArtifacts[${index}]`
            if (!isPlainObject(artifact)) {
                errors.push(issue('EXECUTION_PACKAGE_ARTIFACT_INVALID', path, 'Each expected artifact must be an object.'))
                return
            }
            unknownFields(artifact, ARTIFACT_FIELDS, `${path}.`, errors)
            if (!isKebab(artifact.id)) {
                errors.push(issue('EXECUTION_PACKAGE_ARTIFACT_ID_INVALID', `${path}.id`, 'artifact id must be kebab-case.'))
            } else if (seenIds.has(artifact.id)) {
                errors.push(issue('EXECUTION_PACKAGE_ARTIFACT_ID_DUPLICATE', `${path}.id`, `Duplicate artifact id "${artifact.id}".`))
            } else {
                seenIds.add(artifact.id)
            }
            if (!(EXPECTED_ARTIFACT_KINDS as readonly string[]).includes(artifact.kind as string)) {
                errors.push(issue('EXECUTION_PACKAGE_ARTIFACT_KIND_INVALID', `${path}.kind`, 'artifact kind must be one of the documented logical kinds.'))
            } else {
                kindCounts.set(artifact.kind as string, (kindCounts.get(artifact.kind as string) ?? 0) + 1)
            }
            if (typeof artifact.required !== 'boolean') {
                errors.push(issue('EXECUTION_PACKAGE_ARTIFACT_REQUIRED_INVALID', `${path}.required`, 'required must be an explicit boolean.'))
            }
            if (!isLogicalFileName(artifact.logicalName)) {
                errors.push(issue('EXECUTION_PACKAGE_ARTIFACT_NAME_INVALID', `${path}.logicalName`, 'logicalName must be a non-empty logical file name without separators, traversal or control characters.'))
            }
            if (!isNonEmptyString(artifact.contentType)) {
                errors.push(issue('EXECUTION_PACKAGE_ARTIFACT_CONTENT_TYPE_INVALID', `${path}.contentType`, 'contentType must be a non-empty logical content type.'))
            }
        })
        for (const kind of EXPECTED_ARTIFACT_KINDS) {
            const count = kindCounts.get(kind) ?? 0
            if (count === 0) {
                errors.push(issue('EXECUTION_PACKAGE_ARTIFACT_KIND_MISSING', 'expectedArtifacts', `Required logical artifact kind "${kind}" is missing.`))
            } else if (count > 1) {
                errors.push(issue('EXECUTION_PACKAGE_ARTIFACT_KIND_DUPLICATE', 'expectedArtifacts', `Logical artifact kind "${kind}" is declared more than once.`))
            }
        }
    }

    // source
    const source = input.source
    if (!isPlainObject(source)) {
        errors.push(issue('EXECUTION_PACKAGE_SOURCE_INVALID', 'source', 'source is required and must be an object.'))
    } else {
        unknownFields(source, SOURCE_FIELDS, 'source.', errors)
        for (const field of idFields) {
            if (ids[field] !== undefined && source[field] !== ids[field]) {
                errors.push(issue('EXECUTION_PACKAGE_SOURCE_MISMATCH', `source.${field}`, `source.${field} must equal the top-level ${field}.`))
            }
        }
        for (const field of ['projectSchemaVersion', 'compositionSchemaVersion', 'outputPlanSchemaVersion', 'beatPlanSchemaVersion'] as const) {
            const value = source[field]
            if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 1) {
                errors.push(issue('EXECUTION_PACKAGE_SOURCE_VERSION_INVALID', `source.${field}`, `${field} must be a positive safe integer.`))
            }
        }
    }

    return {
        valid: errors.length === 0,
        errors,
        warnings: [],
        summary: errors.length === 0 ? EXECUTION_PACKAGE_VALID_SUMMARY : executionPackageInvalidSummary(errors.length),
        packageId,
    }
}
