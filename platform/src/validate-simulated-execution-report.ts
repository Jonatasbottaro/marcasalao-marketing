/**
 * Validador puro do SimulatedExecutionReport v1.
 *
 * Verifica estrutura, versao, IDs, estados, coerencia entre status e
 * falha/cancelamento, contagem e unicidade de artefatos, hashes SHA-256,
 * eventos (sequencia contigua, tipos, coerencia com o status) e summary.
 * A forma estrutural tambem e espelhada em
 * schemas/simulated-execution-report.schema.json (draft-07); as regras
 * semanticas vivem apenas aqui.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'
import { containsControlCharacter } from './relative-path.js'
import {
    SIMULATED_EXECUTION_EVENT_TYPES,
    SIMULATED_EXECUTION_STATUSES,
    SIMULATED_REPORT_SCHEMA_VERSION,
    SIMULATED_REPORT_TOP_LEVEL_FIELDS,
    simulatedReportInvalidSummary,
    SIMULATED_REPORT_VALID_SUMMARY,
    type SimulatedExecutionStatus,
} from './simulated-execution-report-contract.js'
import { issue, type ValidationIssue } from './validation-report.js'

export interface SimulatedExecutionReportValidationReport {
    readonly valid: boolean
    readonly errors: readonly ValidationIssue[]
    readonly warnings: readonly ValidationIssue[]
    readonly summary: string
    readonly executionId: string | null
}

const EXECUTION_ID_PATTERN = /^simulation-[a-z0-9]+(-[a-z0-9]+)*$/
const EXECUTION_HASH_ID_PATTERN = /^simulation-v1-[0-9a-f]{64}$/
const SHA256_PATTERN = /^[0-9a-f]{64}$/

const ARTIFACT_FIELDS = ['id', 'logicalName', 'contentType', 'sha256'] as const
const EVENT_FIELDS = ['sequence', 'type', 'executionId', 'stepId', 'artifactId', 'failureCode'] as const

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

function isKebab(value: unknown): value is string {
    return typeof value === 'string' && KEBAB_CASE_PATTERN.test(value)
}

function unknownFields(value: Record<string, unknown>, allowed: readonly string[], prefix: string, errors: ValidationIssue[]): void {
    for (const field of Object.keys(value)) {
        if (!allowed.includes(field)) {
            errors.push(issue('SIMULATED_REPORT_UNKNOWN_FIELD', `${prefix}${field}`, `Unknown field "${field}" is not part of the simulated report contract.`))
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

export function validateSimulatedExecutionReport(input: unknown): SimulatedExecutionReportValidationReport {
    const errors: ValidationIssue[] = []

    if (!isPlainObject(input)) {
        errors.push(issue('SIMULATED_REPORT_INVALID', '', 'Simulated execution report must be a JSON object.'))
        return { valid: false, errors, warnings: [], summary: simulatedReportInvalidSummary(errors.length), executionId: null }
    }

    const executionId = isNonEmptyString(input.executionId) ? input.executionId : null

    if (input.schemaVersion !== SIMULATED_REPORT_SCHEMA_VERSION) {
        errors.push(issue('SIMULATED_REPORT_SCHEMA_VERSION_UNSUPPORTED', 'schemaVersion', `schemaVersion must be the integer ${SIMULATED_REPORT_SCHEMA_VERSION}.`))
    }
    unknownFields(input, SIMULATED_REPORT_TOP_LEVEL_FIELDS, '', errors)

    if (executionId === null) {
        errors.push(issue('SIMULATED_REPORT_EXECUTION_ID_INVALID', 'executionId', 'executionId is required and must be a non-empty string.'))
    } else if (!EXECUTION_ID_PATTERN.test(executionId) && !EXECUTION_HASH_ID_PATTERN.test(executionId)) {
        errors.push(issue('SIMULATED_REPORT_EXECUTION_ID_INVALID', 'executionId', 'executionId must be the readable simulation-<packageId> form or the simulation-v1-<sha256> form.'))
    }
    if (!isKebab(input.packageId)) {
        errors.push(issue('SIMULATED_REPORT_PACKAGE_ID_INVALID', 'packageId', 'packageId is required and must be kebab-case.'))
    }

    const status = input.status
    const statusOk = (SIMULATED_EXECUTION_STATUSES as readonly string[]).includes(status as string)
    if (!statusOk) {
        errors.push(issue('SIMULATED_REPORT_STATUS_INVALID', 'status', 'status must be one of the documented execution states.'))
    }

    const resumedFromStatus = input.resumedFromStatus
    if (
        resumedFromStatus !== null
        && resumedFromStatus !== 'failed'
        && resumedFromStatus !== 'cancelled'
    ) {
        errors.push(issue('SIMULATED_REPORT_RESUME_INVALID', 'resumedFromStatus', 'resumedFromStatus must be null, "failed" or "cancelled".'))
    }

    // completedSteps
    const completedSteps = input.completedSteps
    const completedSet = new Set<string>()
    if (
        !Array.isArray(completedSteps)
        || completedSteps.some((stepId) => !isKebab(stepId))
        || new Set(completedSteps).size !== completedSteps.length
    ) {
        errors.push(issue('SIMULATED_REPORT_COMPLETED_STEPS_INVALID', 'completedSteps', 'completedSteps must be an array of unique kebab-case step ids.'))
    } else {
        for (const stepId of completedSteps) completedSet.add(stepId as string)
    }

    const failedStepId = input.failedStepId
    const failureCode = input.failureCode
    if (failedStepId !== null && !isKebab(failedStepId)) {
        errors.push(issue('SIMULATED_REPORT_FAILED_STEP_INVALID', 'failedStepId', 'failedStepId must be null or kebab-case.'))
    }
    if (failureCode !== null && !isNonEmptyString(failureCode)) {
        errors.push(issue('SIMULATED_REPORT_FAILURE_CODE_INVALID', 'failureCode', 'failureCode must be null or a non-empty string.'))
    }

    if (statusOk) {
        if (status === 'completed' && (failedStepId !== null || failureCode !== null)) {
            errors.push(issue('SIMULATED_REPORT_STATUS_INCOHERENT', 'status', 'completed requires failedStepId and failureCode to be null.'))
        }
        if (status === 'failed' && (failedStepId === null || failureCode === null)) {
            errors.push(issue('SIMULATED_REPORT_STATUS_INCOHERENT', 'status', 'failed requires failedStepId and failureCode.'))
        }
        if (status === 'failed' && isKebab(failedStepId) && completedSet.has(failedStepId)) {
            errors.push(issue('SIMULATED_REPORT_STATUS_INCOHERENT', 'failedStepId', 'the failed step cannot be listed as completed.'))
        }
        if (status === 'cancelled' && failureCode !== null) {
            errors.push(issue('SIMULATED_REPORT_STATUS_INCOHERENT', 'failureCode', 'cancelled is not failed: failureCode must be null.'))
        }
    }

    // artifacts
    const artifacts = input.artifacts
    if (!Array.isArray(artifacts)) {
        errors.push(issue('SIMULATED_REPORT_ARTIFACTS_INVALID', 'artifacts', 'artifacts is required and must be an array.'))
    } else {
        if (input.artifactCount !== artifacts.length) {
            errors.push(issue('SIMULATED_REPORT_ARTIFACT_COUNT_INVALID', 'artifactCount', 'artifactCount must equal artifacts.length.'))
        }
        const seenIds = new Set<string>()
        artifacts.forEach((artifact, index) => {
            const path = `artifacts[${index}]`
            if (!isPlainObject(artifact)) {
                errors.push(issue('SIMULATED_REPORT_ARTIFACT_INVALID', path, 'Each artifact report must be an object.'))
                return
            }
            unknownFields(artifact, ARTIFACT_FIELDS, `${path}.`, errors)
            if (!isKebab(artifact.id)) {
                errors.push(issue('SIMULATED_REPORT_ARTIFACT_ID_INVALID', `${path}.id`, 'artifact id must be kebab-case.'))
            } else if (seenIds.has(artifact.id)) {
                errors.push(issue('SIMULATED_REPORT_ARTIFACT_ID_DUPLICATE', `${path}.id`, `Duplicate artifact id "${artifact.id}".`))
            } else {
                seenIds.add(artifact.id)
            }
            if (!isLogicalFileName(artifact.logicalName)) {
                errors.push(issue('SIMULATED_REPORT_ARTIFACT_NAME_INVALID', `${path}.logicalName`, 'logicalName must be a logical file name without separators, traversal or control characters.'))
            }
            if (!isNonEmptyString(artifact.contentType)) {
                errors.push(issue('SIMULATED_REPORT_ARTIFACT_CONTENT_TYPE_INVALID', `${path}.contentType`, 'contentType must be a non-empty logical content type.'))
            }
            if (typeof artifact.sha256 !== 'string' || !SHA256_PATTERN.test(artifact.sha256)) {
                errors.push(issue('SIMULATED_REPORT_ARTIFACT_HASH_INVALID', `${path}.sha256`, 'sha256 must be a 64-character lowercase hex digest.'))
            }
        })
    }

    // events
    const events = input.events
    if (!Array.isArray(events) || events.length === 0) {
        errors.push(issue('SIMULATED_REPORT_EVENTS_INVALID', 'events', 'events is required and must be a non-empty array.'))
    } else {
        events.forEach((event, index) => {
            const path = `events[${index}]`
            if (!isPlainObject(event)) {
                errors.push(issue('SIMULATED_REPORT_EVENT_INVALID', path, 'Each event must be an object.'))
                return
            }
            unknownFields(event, EVENT_FIELDS, `${path}.`, errors)
            if (event.sequence !== index + 1) {
                errors.push(issue('SIMULATED_REPORT_EVENT_SEQUENCE_INVALID', `${path}.sequence`, 'sequence must be contiguous from 1 and equal to the array position.'))
            }
            if (!(SIMULATED_EXECUTION_EVENT_TYPES as readonly string[]).includes(event.type as string)) {
                errors.push(issue('SIMULATED_REPORT_EVENT_TYPE_INVALID', `${path}.type`, 'event type must be one of the documented lifecycle events.'))
            }
            if (executionId !== null && event.executionId !== executionId) {
                errors.push(issue('SIMULATED_REPORT_EVENT_EXECUTION_INVALID', `${path}.executionId`, 'event executionId must equal the report executionId.'))
            }
            for (const optional of ['stepId', 'artifactId', 'failureCode'] as const) {
                if (event[optional] !== undefined && !isNonEmptyString(event[optional])) {
                    errors.push(issue('SIMULATED_REPORT_EVENT_FIELD_INVALID', `${path}.${optional}`, `${optional}, when present, must be a non-empty string.`))
                }
            }
            if (event.type === 'step-failed' && !isNonEmptyString(event.failureCode)) {
                errors.push(issue('SIMULATED_REPORT_EVENT_FIELD_INVALID', `${path}.failureCode`, 'step-failed requires failureCode.'))
            }
        })
        const first = events[0]
        if (isPlainObject(first) && first.type !== 'execution-started') {
            errors.push(issue('SIMULATED_REPORT_EVENT_ORDER_INVALID', 'events[0].type', 'the first event must be execution-started.'))
        }
        const last = events[events.length - 1]
        if (isPlainObject(last) && statusOk) {
            const expectedLast = status === 'completed'
                ? 'execution-completed'
                : status === 'failed'
                    ? 'execution-failed'
                    : status === 'cancelled'
                        ? 'execution-cancelled'
                        : null
            if (expectedLast !== null && last.type !== expectedLast) {
                errors.push(issue('SIMULATED_REPORT_EVENT_ORDER_INVALID', `events[${events.length - 1}].type`, `the last event must be ${expectedLast} for status ${status}.`))
            }
        }
    }

    if (!isNonEmptyString(input.summary)) {
        errors.push(issue('SIMULATED_REPORT_SUMMARY_INVALID', 'summary', 'summary is required and must be a non-empty string.'))
    }

    return {
        valid: errors.length === 0,
        errors,
        warnings: [],
        summary: errors.length === 0 ? SIMULATED_REPORT_VALID_SUMMARY : simulatedReportInvalidSummary(errors.length),
        executionId,
    }
}
