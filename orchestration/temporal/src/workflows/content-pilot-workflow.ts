/**
 * Workflow deterministico do piloto TEMPORAL-01.
 *
 * Coordena as tres etapas por proxy, declara timeout e retry de cada Activity e
 * devolve sempre um TemporalPilotResult estruturado. Aqui nao ha relogio,
 * aleatoriedade, ambiente, rede, arquivo nem chamada direta de Activity: o
 * unico efeito externo possivel e o que as Activities fazem.
 */
import { proxyActivities, type ActivityOptions } from '@temporalio/workflow'

import { PILOT_FAILURE_CODES } from '../pilot-core/failures.js'
import { echoIdentities, type PilotIdentities, type TemporalPilotInput } from '../pilot-core/pilot-input.js'
import type { PilotOutput, PilotStep } from '../pilot-core/pilot-plan.js'
import { failedPilotResult, rejectedPilotResult, type TemporalPilotResult } from '../pilot-core/pilot-result.js'
import { outcomeFor } from '../pilot-core/pilot-outcome.js'
import { signalOf } from './pilot-failure-signal.js'
import type * as pilotActivities from '../activities/pilot-activities.js'

/** Task Queue exclusiva do piloto. */
export const PILOT_TASK_QUEUE = 'marketing-temporal-pilot-v1'

/** Namespace do piloto. Worker e cliente leem daqui para nao divergir. */
export const PILOT_NAMESPACE = 'default'

/** Codigo cujo significado e "a entrada nao passou": retry nao corrige entrada. */
const NON_RETRYABLE_PILOT_CODES: string[] = [
    PILOT_FAILURE_CODES.schemaUnsupported,
    PILOT_FAILURE_CODES.requestIdRequired,
    PILOT_FAILURE_CODES.projectIdRequired,
    PILOT_FAILURE_CODES.operationInvalid,
    PILOT_FAILURE_CODES.payloadInvalid,
    PILOT_FAILURE_CODES.inputInvalid,
    PILOT_FAILURE_CODES.nonRetryable,
]

const ACTIVITY_OPTIONS: ActivityOptions = {
    startToCloseTimeout: '5 seconds',
    retry: {
        initialInterval: '1 second',
        backoffCoefficient: 2,
        maximumInterval: '5 seconds',
        maximumAttempts: 3,
        nonRetryableErrorTypes: NON_RETRYABLE_PILOT_CODES,
    },
}

const { validatePilotRequest, preparePilotExecution, finalizePilotExecution } = proxyActivities<typeof pilotActivities>(ACTIVITY_OPTIONS)

function refusalFor(identities: PilotIdentities, error: unknown, completedSteps: readonly PilotStep[]): TemporalPilotResult {
    const outcome = outcomeFor(signalOf(error))

    return outcome.status === 'rejected'
        ? rejectedPilotResult(identities, outcome.failureCode, completedSteps)
        : failedPilotResult(identities, outcome.failureCode, completedSteps)
}

export async function contentPilotWorkflow(rawInput: unknown): Promise<TemporalPilotResult> {
    const completedSteps: PilotStep[] = []
    let identities = echoIdentities(rawInput)

    let pilotInput: TemporalPilotInput
    try {
        pilotInput = await validatePilotRequest(rawInput)
    } catch (error) {
        return refusalFor(identities, error, completedSteps)
    }
    completedSteps.push('validate')
    identities = { requestId: pilotInput.requestId, projectId: pilotInput.projectId }

    let output: PilotOutput
    try {
        output = await preparePilotExecution(pilotInput)
    } catch (error) {
        return refusalFor(identities, error, completedSteps)
    }
    completedSteps.push('prepare')

    try {
        return await finalizePilotExecution(pilotInput, output)
    } catch (error) {
        return refusalFor(identities, error, completedSteps)
    }
}
