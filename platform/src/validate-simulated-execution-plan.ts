/**
 * Validador puro do SimulatedExecutionPlan v1.
 *
 * Verifica estrutura, versao, executionId (formato e rederivacao), output,
 * steps (ordem, agrupamento por beat, janela temporal, operacoes, inputs,
 * referencias de artefatos), timeline consolidada e artefatos esperados.
 * A forma estrutural tambem e espelhada em
 * schemas/simulated-execution-plan.schema.json (draft-07); as regras
 * semanticas entre campos vivem apenas aqui.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import { containsControlCharacter } from './relative-path.js'
import {
    deriveSimulatedExecutionId,
    SIMULATED_EXECUTION_ID_MAX_LENGTH,
    SIMULATED_PLAN_SCHEMA_VERSION,
    SIMULATED_PLAN_TOP_LEVEL_FIELDS,
    SIMULATED_STEP_OPERATIONS,
    SIMULATION_ADAPTER,
    simulatedPlanInvalidSummary,
    SIMULATED_PLAN_VALID_SUMMARY,
    type SimulatedStepOperation,
} from './simulated-execution-plan-contract.js'
import { EXPECTED_ARTIFACT_KINDS } from './creative-execution-package-contract.js'
import { issue, type ValidationIssue } from './validation-report.js'

export interface SimulatedExecutionPlanValidationReport {
    readonly valid: boolean
    readonly errors: readonly ValidationIssue[]
    readonly warnings: readonly ValidationIssue[]
    readonly summary: string
    readonly executionId: string | null
}

const EXECUTION_ID_PATTERN = /^simulation-[a-z0-9]+(-[a-z0-9]+)*$/
const EXECUTION_HASH_ID_PATTERN = /^simulation-v1-[0-9a-f]{64}$/
const ASPECT_RATIO_PATTERN = /^\d+:\d+$/

const OUTPUT_FIELDS = ['profileId', 'mediaKind', 'width', 'height', 'aspectRatio', 'fps', 'durationMs'] as const
const STEP_FIELDS = [
    'stepId',
    'order',
    'beatId',
    'sceneId',
    'startMs',
    'durationMs',
    'endMs',
    'operation',
    'inputs',
    'expectedArtifactIds',
] as const
const INPUT_FIELDS = [
    'sceneId',
    'startMs',
    'durationMs',
    'endMs',
    'onScreenText',
    'narrationText',
    'motionIntent',
    'transitionIn',
    'transitionOut',
] as const
const ARTIFACT_FIELDS = ['id', 'kind', 'required', 'logicalName', 'contentType'] as const

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

function unknownFields(value: Record<string, unknown>, allowed: readonly string[], prefix: string, errors: ValidationIssue[]): void {
    for (const field of Object.keys(value)) {
        if (!allowed.includes(field)) {
            errors.push(issue('SIMULATED_PLAN_UNKNOWN_FIELD', `${prefix}${field}`, `Unknown field "${field}" is not part of the simulated plan contract.`))
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

export function validateSimulatedExecutionPlan(input: unknown): SimulatedExecutionPlanValidationReport {
    const errors: ValidationIssue[] = []

    if (!isPlainObject(input)) {
        errors.push(issue('SIMULATED_PLAN_INVALID', '', 'Simulated execution plan must be a JSON object.'))
        return { valid: false, errors, warnings: [], summary: simulatedPlanInvalidSummary(errors.length), executionId: null }
    }

    const executionId = isNonEmptyString(input.executionId) ? input.executionId : null

    if (input.schemaVersion !== SIMULATED_PLAN_SCHEMA_VERSION) {
        errors.push(issue('SIMULATED_PLAN_SCHEMA_VERSION_UNSUPPORTED', 'schemaVersion', `schemaVersion must be the integer ${SIMULATED_PLAN_SCHEMA_VERSION}.`))
    }
    unknownFields(input, SIMULATED_PLAN_TOP_LEVEL_FIELDS, '', errors)

    if (executionId === null) {
        errors.push(issue('SIMULATED_PLAN_EXECUTION_ID_INVALID', 'executionId', 'executionId is required and must be a non-empty string.'))
    } else if (
        executionId.length > SIMULATED_EXECUTION_ID_MAX_LENGTH
        || (!EXECUTION_ID_PATTERN.test(executionId) && !EXECUTION_HASH_ID_PATTERN.test(executionId))
    ) {
        errors.push(issue('SIMULATED_PLAN_EXECUTION_ID_INVALID', 'executionId', 'executionId must be the readable simulation-<packageId> form or the simulation-v1-<sha256> form, within the documented limit.'))
    }

    const packageId = isKebab(input.packageId) ? input.packageId : null
    if (packageId === null) {
        errors.push(issue('SIMULATED_PLAN_PACKAGE_ID_INVALID', 'packageId', 'packageId is required and must be kebab-case.'))
    } else if (executionId !== null && (EXECUTION_ID_PATTERN.test(executionId) || EXECUTION_HASH_ID_PATTERN.test(executionId))) {
        if (executionId !== deriveSimulatedExecutionId(packageId)) {
            errors.push(issue('SIMULATED_PLAN_EXECUTION_ID_MISMATCH', 'executionId', 'executionId does not match the deterministic derivation from packageId.'))
        }
    }

    if (input.caseId !== null && !isKebab(input.caseId)) {
        errors.push(issue('SIMULATED_PLAN_CASE_ID_INVALID', 'caseId', 'caseId must be null or kebab-case.'))
    }
    if (input.adapter !== SIMULATION_ADAPTER) {
        errors.push(issue('SIMULATED_PLAN_ADAPTER_INVALID', 'adapter', `adapter must be "${SIMULATION_ADAPTER}" in v1.`))
    }

    // output
    let outputDurationMs: number | null = null
    const output = input.output
    if (!isPlainObject(output)) {
        errors.push(issue('SIMULATED_PLAN_OUTPUT_INVALID', 'output', 'output is required and must be an object.'))
    } else {
        unknownFields(output, OUTPUT_FIELDS, 'output.', errors)
        if (!isKebab(output.profileId)) {
            errors.push(issue('SIMULATED_PLAN_OUTPUT_PROFILE_INVALID', 'output.profileId', 'output.profileId must be kebab-case.'))
        }
        if (output.mediaKind !== 'video') {
            errors.push(issue('SIMULATED_PLAN_OUTPUT_MEDIA_KIND_INVALID', 'output.mediaKind', 'output.mediaKind must be "video" in v1.'))
        }
        if (!isPositiveSafeInteger(output.width) || !isPositiveSafeInteger(output.height)) {
            errors.push(issue('SIMULATED_PLAN_OUTPUT_DIMENSIONS_INVALID', 'output.width', 'output.width and output.height must be positive safe integers.'))
        }
        if (typeof output.aspectRatio !== 'string' || !ASPECT_RATIO_PATTERN.test(output.aspectRatio)) {
            errors.push(issue('SIMULATED_PLAN_OUTPUT_ASPECT_RATIO_INVALID', 'output.aspectRatio', 'output.aspectRatio must have the W:H form.'))
        }
        if (typeof output.fps !== 'number' || !Number.isSafeInteger(output.fps) || output.fps < 1 || output.fps > 120) {
            errors.push(issue('SIMULATED_PLAN_OUTPUT_FPS_INVALID', 'output.fps', 'output.fps must be an integer between 1 and 120.'))
        }
        if (!isPositiveSafeInteger(output.durationMs)) {
            errors.push(issue('SIMULATED_PLAN_OUTPUT_DURATION_INVALID', 'output.durationMs', 'output.durationMs must be a positive safe integer.'))
        } else {
            outputDurationMs = output.durationMs
        }
    }

    // expectedArtifacts (antes dos steps, para validar referencias)
    const artifactIds = new Set<string>()
    const artifacts = input.expectedArtifacts
    if (!Array.isArray(artifacts) || artifacts.length === 0) {
        errors.push(issue('SIMULATED_PLAN_ARTIFACTS_INVALID', 'expectedArtifacts', 'expectedArtifacts is required and must be a non-empty array.'))
    } else {
        const kindCounts = new Map<string, number>()
        artifacts.forEach((artifact, index) => {
            const path = `expectedArtifacts[${index}]`
            if (!isPlainObject(artifact)) {
                errors.push(issue('SIMULATED_PLAN_ARTIFACT_INVALID', path, 'Each expected artifact must be an object.'))
                return
            }
            unknownFields(artifact, ARTIFACT_FIELDS, `${path}.`, errors)
            if (!isKebab(artifact.id)) {
                errors.push(issue('SIMULATED_PLAN_ARTIFACT_ID_INVALID', `${path}.id`, 'artifact id must be kebab-case.'))
            } else if (artifactIds.has(artifact.id)) {
                errors.push(issue('SIMULATED_PLAN_ARTIFACT_ID_DUPLICATE', `${path}.id`, `Duplicate artifact id "${artifact.id}".`))
            } else {
                artifactIds.add(artifact.id)
            }
            if (!(EXPECTED_ARTIFACT_KINDS as readonly string[]).includes(artifact.kind as string)) {
                errors.push(issue('SIMULATED_PLAN_ARTIFACT_KIND_INVALID', `${path}.kind`, 'artifact kind must be one of the documented logical kinds.'))
            } else {
                kindCounts.set(artifact.kind as string, (kindCounts.get(artifact.kind as string) ?? 0) + 1)
            }
            if (typeof artifact.required !== 'boolean') {
                errors.push(issue('SIMULATED_PLAN_ARTIFACT_REQUIRED_INVALID', `${path}.required`, 'required must be an explicit boolean.'))
            }
            if (!isLogicalFileName(artifact.logicalName)) {
                errors.push(issue('SIMULATED_PLAN_ARTIFACT_NAME_INVALID', `${path}.logicalName`, 'logicalName must be a logical file name without separators, traversal or control characters.'))
            }
            if (!isNonEmptyString(artifact.contentType)) {
                errors.push(issue('SIMULATED_PLAN_ARTIFACT_CONTENT_TYPE_INVALID', `${path}.contentType`, 'contentType must be a non-empty logical content type.'))
            }
        })
        for (const kind of EXPECTED_ARTIFACT_KINDS) {
            const count = kindCounts.get(kind) ?? 0
            if (count === 0) {
                errors.push(issue('SIMULATED_PLAN_ARTIFACT_KIND_MISSING', 'expectedArtifacts', `Required logical artifact kind "${kind}" is missing.`))
            } else if (count > 1) {
                errors.push(issue('SIMULATED_PLAN_ARTIFACT_KIND_DUPLICATE', 'expectedArtifacts', `Logical artifact kind "${kind}" is declared more than once.`))
            }
        }
    }

    // steps
    let lastBeatEndMs: number | null = null
    const steps = input.steps
    if (!Array.isArray(steps) || steps.length === 0) {
        errors.push(issue('SIMULATED_PLAN_STEPS_INVALID', 'steps', 'steps is required and must be a non-empty array.'))
    } else {
        const seenStepIds = new Set<string>()
        let expectedBeatStartMs = 0
        steps.forEach((step, index) => {
            const path = `steps[${index}]`
            if (!isPlainObject(step)) {
                errors.push(issue('SIMULATED_PLAN_STEP_INVALID', path, 'Each step must be an object.'))
                return
            }
            unknownFields(step, STEP_FIELDS, `${path}.`, errors)
            if (!isKebab(step.stepId)) {
                errors.push(issue('SIMULATED_PLAN_STEP_ID_INVALID', `${path}.stepId`, 'stepId must be kebab-case.'))
            } else if (seenStepIds.has(step.stepId)) {
                errors.push(issue('SIMULATED_PLAN_STEP_ID_DUPLICATE', `${path}.stepId`, `Duplicate stepId "${step.stepId}".`))
            } else {
                seenStepIds.add(step.stepId)
            }
            if (step.order !== index + 1) {
                errors.push(issue('SIMULATED_PLAN_STEP_ORDER_INVALID', `${path}.order`, 'order must be contiguous from 1 and equal to the array position.'))
            }
            if (!isKebab(step.beatId) || !isKebab(step.sceneId)) {
                errors.push(issue('SIMULATED_PLAN_STEP_REFERENCE_INVALID', `${path}.beatId`, 'beatId and sceneId must be kebab-case.'))
            }
            const windowOk = typeof step.startMs === 'number'
                && Number.isSafeInteger(step.startMs)
                && step.startMs >= 0
                && isPositiveSafeInteger(step.durationMs)
                && step.endMs === step.startMs + step.durationMs
            if (!windowOk) {
                errors.push(issue('SIMULATED_PLAN_STEP_WINDOW_INVALID', `${path}.startMs`, 'startMs/durationMs/endMs must form a safe positive window with endMs = startMs + durationMs.'))
            }
            if (!(SIMULATED_STEP_OPERATIONS as readonly string[]).includes(step.operation as string)) {
                errors.push(issue('SIMULATED_PLAN_STEP_OPERATION_INVALID', `${path}.operation`, 'operation must be one of the documented simulated operations.'))
            }

            // agrupamento por beat: blocos de quatro operacoes na ordem fixa
            const positionInBeat = index % SIMULATED_STEP_OPERATIONS.length
            const expectedOperation = SIMULATED_STEP_OPERATIONS[positionInBeat] as SimulatedStepOperation
            if (step.operation !== expectedOperation) {
                errors.push(issue('SIMULATED_PLAN_STEP_SEQUENCE_INVALID', `${path}.operation`, 'steps must group four operations per beat in the fixed order.'))
            }
            if (positionInBeat === 0) {
                if (windowOk && step.startMs !== expectedBeatStartMs) {
                    errors.push(issue('SIMULATED_PLAN_TIMELINE_GAP', `${path}.startMs`, 'beat windows must be contiguous and start at zero.'))
                }
            } else {
                const previous = steps[index - 1]
                if (
                    !isPlainObject(previous)
                    || previous.beatId !== step.beatId
                    || previous.startMs !== step.startMs
                    || previous.durationMs !== step.durationMs
                    || previous.endMs !== step.endMs
                ) {
                    errors.push(issue('SIMULATED_PLAN_STEP_SEQUENCE_INVALID', `${path}.beatId`, 'all operations of a beat must share beatId and time window.'))
                }
            }
            if (positionInBeat === SIMULATED_STEP_OPERATIONS.length - 1 && windowOk) {
                expectedBeatStartMs = step.endMs as number
                lastBeatEndMs = step.endMs as number
            }

            // inputs
            const inputs = step.inputs
            if (!isPlainObject(inputs)) {
                errors.push(issue('SIMULATED_PLAN_STEP_INPUTS_INVALID', `${path}.inputs`, 'inputs is required and must be an object.'))
            } else {
                unknownFields(inputs, INPUT_FIELDS, `${path}.inputs.`, errors)
                for (const textField of ['onScreenText', 'narrationText', 'motionIntent', 'transitionIn', 'transitionOut'] as const) {
                    if (inputs[textField] !== undefined && !isNonEmptyString(inputs[textField])) {
                        errors.push(issue('SIMULATED_PLAN_STEP_INPUTS_INVALID', `${path}.inputs.${textField}`, `${textField}, when present, must be a non-empty string.`))
                    }
                }
                if (inputs.sceneId !== undefined && !isKebab(inputs.sceneId)) {
                    errors.push(issue('SIMULATED_PLAN_STEP_INPUTS_INVALID', `${path}.inputs.sceneId`, 'inputs.sceneId, when present, must be kebab-case.'))
                }
                for (const timeField of ['startMs', 'durationMs', 'endMs'] as const) {
                    if (inputs[timeField] !== undefined && (typeof inputs[timeField] !== 'number' || !Number.isSafeInteger(inputs[timeField]))) {
                        errors.push(issue('SIMULATED_PLAN_STEP_INPUTS_INVALID', `${path}.inputs.${timeField}`, `${timeField}, when present, must be a safe integer.`))
                    }
                }
            }

            // referencias de artefatos
            if (
                !Array.isArray(step.expectedArtifactIds)
                || step.expectedArtifactIds.some((artifactId) => !isKebab(artifactId))
                || new Set(step.expectedArtifactIds).size !== step.expectedArtifactIds.length
            ) {
                errors.push(issue('SIMULATED_PLAN_STEP_ARTIFACTS_INVALID', `${path}.expectedArtifactIds`, 'expectedArtifactIds must be an array of unique kebab-case ids.'))
            } else {
                for (const artifactId of step.expectedArtifactIds) {
                    if (!artifactIds.has(artifactId as string)) {
                        errors.push(issue('SIMULATED_PLAN_ARTIFACT_REFERENCE_INVALID', `${path}.expectedArtifactIds`, `Unknown artifact id "${artifactId}".`))
                    }
                }
            }
        })
        if (steps.length % SIMULATED_STEP_OPERATIONS.length !== 0) {
            errors.push(issue('SIMULATED_PLAN_STEP_SEQUENCE_INVALID', 'steps', 'steps must contain complete groups of four operations per beat.'))
        }
    }

    if (outputDurationMs !== null && lastBeatEndMs !== null && outputDurationMs !== lastBeatEndMs) {
        errors.push(issue('SIMULATED_PLAN_DURATION_MISMATCH', 'output.durationMs', 'output.durationMs must equal the end of the last beat window.'))
    }

    return {
        valid: errors.length === 0,
        errors,
        warnings: [],
        summary: errors.length === 0 ? SIMULATED_PLAN_VALID_SUMMARY : simulatedPlanInvalidSummary(errors.length),
        executionId,
    }
}
