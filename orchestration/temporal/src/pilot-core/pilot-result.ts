/**
 * Relatorio estruturado do piloto TEMPORAL-01.
 *
 * Camada de nucleo: nao importa nada de @temporalio. O resultado e a unica saida
 * publica de uma execucao, entao ele e sempre serializavel, sempre com ordem
 * estavel, sempre com codigo estavel quando ha falha, e nunca com valor de
 * entrada alem dos identificadores que passaram pelas regras do parse.
 */
import type { PilotFailureCode } from './failures.js'
import { PILOT_SCHEMA_VERSION, type PilotIdentities, type TemporalPilotInput } from './pilot-input.js'
import { PILOT_STEPS, type PilotOutput, type PilotStep } from './pilot-plan.js'

export type PilotStatus = 'completed' | 'rejected' | 'failed'

export interface TemporalPilotResult {
    schemaVersion: typeof PILOT_SCHEMA_VERSION
    /** null quando a entrada rejeitada nao informou um identificador valido. */
    requestId: string | null
    projectId: string | null
    status: PilotStatus
    /** Subconjunto de PILOT_STEPS na ordem em que as etapas concluidas foram chamadas. */
    completedSteps: PilotStep[]
    /** null em completed; sempre presente nos demais. */
    failureCode: PilotFailureCode | null
    /** null em rejected e em failed: nada saiu do piloto. */
    output: PilotOutput | null
}

function pilotResult(
    identities: PilotIdentities,
    status: PilotStatus,
    completedSteps: readonly PilotStep[],
    failureCode: PilotFailureCode | null,
    output: PilotOutput | null,
): TemporalPilotResult {
    return {
        schemaVersion: PILOT_SCHEMA_VERSION,
        requestId: identities.requestId,
        projectId: identities.projectId,
        status,
        completedSteps: [...completedSteps],
        failureCode,
        output,
    }
}

export function completedPilotResult(input: TemporalPilotInput, output: PilotOutput): TemporalPilotResult {
    return pilotResult(input, 'completed', PILOT_STEPS, null, output)
}

export function rejectedPilotResult(identities: PilotIdentities, failureCode: PilotFailureCode, completedSteps: readonly PilotStep[]): TemporalPilotResult {
    return pilotResult(identities, 'rejected', completedSteps, failureCode, null)
}

export function failedPilotResult(identities: PilotIdentities, failureCode: PilotFailureCode, completedSteps: readonly PilotStep[]): TemporalPilotResult {
    return pilotResult(identities, 'failed', completedSteps, failureCode, null)
}
