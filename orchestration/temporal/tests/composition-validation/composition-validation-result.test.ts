/**
 * Testes puros do contrato de resultado e classificacao de falhas de
 * TEMPORAL-02 (fatia Workflow).
 *
 * Nao inicia servidor Temporal, nao toca rede e nao usa disco. Valida:
 * - invariantes de CompositionValidationWorkflowResult para valid, invalid e failed;
 * - propagacao direta de report.projectId e report.compositionId (nunca via summary);
 * - nulidade obrigatoria de projectId, compositionId e validation em failed;
 * - classificacao defensiva de falhas Temporal percorrendo causes com protecao contra ciclos;
 * - sanitizacao completa (sem vazar mensagem, stack, details, caminho ou payload);
 * - fidelidade da Retry Policy e timeout aos valores canonicos do PRD.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
    ActivityFailure,
    ApplicationFailure,
    RetryState,
    TimeoutFailure,
    TimeoutType,
} from '@temporalio/common'

import { TEMPORAL_COMPOSITION_ACTIVITY_FAILED } from '../../src/activities/composition-validation-activity.js'
import { classifyCompositionActivityFailure } from '../../src/workflows/composition-validation-failure-classifier.js'
import {
    COMPOSITION_VALIDATION_RESULT_SCHEMA_VERSION,
    COMPOSITION_VALIDATION_STEP,
    COMPOSITION_WORKFLOW_FAILURE_CODES,
    NON_RETRYABLE_COMPOSITION_ACTIVITY_ERROR_TYPES,
    failedCompositionValidationResult,
    isCompositionWorkflowFailureCode,
    resultFromCompositionValidationReport,
    type CompositionValidationReport,
} from '../../src/workflows/composition-validation-result.js'
import { COMPOSITION_VALIDATION_ACTIVITY_OPTIONS } from '../../src/workflows/composition-validation-workflow.js'

function makeReport(overrides: Partial<CompositionValidationReport> = {}): CompositionValidationReport {
    return {
        valid: true,
        errors: [],
        warnings: [],
        summary: 'Composition is valid.',
        projectId: 'marca-salao',
        compositionId: 'comp-001',
        schemaVersion: 1,
        sceneCount: 1,
        totalDurationMs: 5000,
        format: { profile: 'square-1080', width: 1080, height: 1080, fps: 30 },
        rendererAdapter: 'undecided',
        ...overrides,
    }
}

function wrapInActivityFailure(cause: Error | undefined): ActivityFailure {
    return new ActivityFailure(
        'Activity task failed',
        'validateCompositionActivity',
        '1',
        RetryState.MAXIMUM_ATTEMPTS_REACHED,
        'worker-test',
        cause,
    )
}

test('resultFromCompositionValidationReport constroi resultado valid com invariantes do PRD', () => {
    const report = makeReport({ valid: true, projectId: 'marca-salao', compositionId: 'comp-valid' })
    const result = resultFromCompositionValidationReport('req-valid-1', report)

    assert.equal(result.schemaVersion, COMPOSITION_VALIDATION_RESULT_SCHEMA_VERSION)
    assert.equal(result.schemaVersion, 1)
    assert.equal(result.requestId, 'req-valid-1')
    assert.equal(result.projectId, 'marca-salao')
    assert.equal(result.compositionId, 'comp-valid')
    assert.equal(result.status, 'valid')
    assert.strictEqual(result.validation, report)
    assert.deepEqual(result.completedSteps, [COMPOSITION_VALIDATION_STEP])
    assert.equal(result.failureCode, null)
})

test('resultFromCompositionValidationReport constroi resultado invalid como retorno normal de dominio', () => {
    const report = makeReport({
        valid: false,
        summary: 'Composition is invalid: 1 error(s).',
        projectId: null,
        compositionId: 'comp-bad',
        errors: [{ code: 'COMPOSITION_PROJECT_ID_MISMATCH', path: '$.projectId', message: 'Mismatch' }],
    })
    const result = resultFromCompositionValidationReport('req-invalid-1', report)

    assert.equal(result.schemaVersion, 1)
    assert.equal(result.requestId, 'req-invalid-1')
    assert.equal(result.projectId, null)
    assert.equal(result.compositionId, 'comp-bad')
    assert.equal(result.status, 'invalid')
    assert.strictEqual(result.validation, report)
    assert.deepEqual(result.completedSteps, ['validate-composition'])
    assert.equal(result.failureCode, null)
})

test('failedCompositionValidationResult zera validacao, ids e completedSteps', () => {
    const result = failedCompositionValidationResult(
        'req-failed-1',
        COMPOSITION_WORKFLOW_FAILURE_CODES.timeout,
    )

    assert.deepEqual(result, {
        schemaVersion: 1,
        requestId: 'req-failed-1',
        projectId: null,
        compositionId: null,
        status: 'failed',
        validation: null,
        completedSteps: [],
        failureCode: 'TEMPORAL_COMPOSITION_TIMEOUT',
    })
})

test('classifyCompositionActivityFailure classifica ApplicationFailure e TimeoutFailure via cadeia de causes', () => {
    const nonRetryable = ApplicationFailure.create({
        type: COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
        message: 'fixed message',
        nonRetryable: true,
    })
    assert.equal(
        classifyCompositionActivityFailure(wrapInActivityFailure(nonRetryable)),
        COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
    )

    const transient = ApplicationFailure.create({
        type: COMPOSITION_WORKFLOW_FAILURE_CODES.transientFailure,
        message: 'transient',
    })
    assert.equal(
        classifyCompositionActivityFailure(wrapInActivityFailure(transient)),
        COMPOSITION_WORKFLOW_FAILURE_CODES.transientFailure,
    )

    const timeout = new TimeoutFailure('Activity timed out', undefined, TimeoutType.START_TO_CLOSE)
    assert.equal(
        classifyCompositionActivityFailure(wrapInActivityFailure(timeout)),
        COMPOSITION_WORKFLOW_FAILURE_CODES.timeout,
    )

    // ApplicationFailure com cause interna comum preserva seu proprio type conhecido
    const appWithInnerCause = ApplicationFailure.create({
        type: COMPOSITION_WORKFLOW_FAILURE_CODES.transientFailure,
        message: 'wrapped transient',
        cause: new TypeError('internal cause with /tmp/secret'),
    })
    assert.equal(
        classifyCompositionActivityFailure(wrapInActivityFailure(appWithInnerCause)),
        COMPOSITION_WORKFLOW_FAILURE_CODES.transientFailure,
    )

    // ApplicationFailure envolvendo TimeoutFailure na cadeia prioriza timeout
    const appWrappingTimeout = ApplicationFailure.create({
        type: 'OuterError',
        message: 'outer',
        cause: timeout,
    })
    assert.equal(
        classifyCompositionActivityFailure(wrapInActivityFailure(appWrappingTimeout)),
        COMPOSITION_WORKFLOW_FAILURE_CODES.timeout,
    )
})

test('classifyCompositionActivityFailure mapeia falha desconhecida, ciclo e nao-Error para ACTIVITY_FAILED sanitizado', () => {
    const unknownApp = ApplicationFailure.create({
        type: 'VendorGateway503',
        message: 'sensitive token sk-live-123 /etc/passwd',
        details: [{ secret: 'never-leak' }],
    })
    assert.equal(
        classifyCompositionActivityFailure(wrapInActivityFailure(unknownApp)),
        COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
    )

    assert.equal(
        classifyCompositionActivityFailure(wrapInActivityFailure(new Error('raw error C:\\secret'))),
        COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
    )

    assert.equal(
        classifyCompositionActivityFailure(wrapInActivityFailure(undefined)),
        COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
    )

    // Protecao contra ciclo em cause
    const errA = new Error('a') as Error & { cause?: unknown }
    const errB = new Error('b') as Error & { cause?: unknown }
    errA.cause = errB
    errB.cause = errA
    assert.equal(
        classifyCompositionActivityFailure(errA),
        COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
    )

    // Nao-Error
    for (const value of [null, undefined, 'string-error', 42, { message: 'obj' }]) {
        assert.equal(
            classifyCompositionActivityFailure(value),
            COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed,
        )
    }

    // Garante que o resultado failed nao vaza nada do erro original
    const code = classifyCompositionActivityFailure(wrapInActivityFailure(unknownApp))
    const result = failedCompositionValidationResult('req-sanitize', code)
    const serialized = JSON.stringify(result)
    assert.equal(serialized.includes('VendorGateway503'), false)
    assert.equal(serialized.includes('sk-live-123'), false)
    assert.equal(serialized.includes('never-leak'), false)
    assert.equal(serialized.includes('/etc/passwd'), false)
})

test('politica de retry, timeout e codigos seguem literalmente o PRD e alinham com a Activity', () => {
    assert.equal(COMPOSITION_VALIDATION_ACTIVITY_OPTIONS.startToCloseTimeout, '5 seconds')
    assert.deepEqual(COMPOSITION_VALIDATION_ACTIVITY_OPTIONS.retry, {
        initialInterval: '1 second',
        backoffCoefficient: 2,
        maximumInterval: '2 seconds',
        maximumAttempts: 2,
        nonRetryableErrorTypes: ['TEMPORAL_COMPOSITION_ACTIVITY_FAILED'],
    })

    assert.deepEqual([...NON_RETRYABLE_COMPOSITION_ACTIVITY_ERROR_TYPES], [
        TEMPORAL_COMPOSITION_ACTIVITY_FAILED,
    ])
    assert.equal(COMPOSITION_WORKFLOW_FAILURE_CODES.activityFailed, TEMPORAL_COMPOSITION_ACTIVITY_FAILED)
    assert.equal(isCompositionWorkflowFailureCode('TEMPORAL_COMPOSITION_TIMEOUT'), true)
    assert.equal(isCompositionWorkflowFailureCode('TEMPORAL_COMPOSITION_ACTIVITY_FAILED'), true)
    assert.equal(isCompositionWorkflowFailureCode('TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE'), true)
    assert.equal(isCompositionWorkflowFailureCode('TEMPORAL_COMPOSITION_INPUT_INVALID'), false)
})