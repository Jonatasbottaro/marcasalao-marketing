/**
 * Derivacao de plano e de chave de idempotencia do piloto TEMPORAL-01.
 *
 * Camada de nucleo: nao importa nada de @temporalio. Cada valor abaixo e funcao
 * apenas da entrada ja validada: sem relogio, sem aleatoriedade, sem ambiente.
 * E por isso que a idempotencia aqui e estrutural, e nao um controle de
 * duplicidade implementado no alto.
 */
import type { TemporalPilotInput } from './pilot-input.js'

/** Etapas canonicas do piloto, em ordem estavel. */
export const PILOT_STEPS = ['validate', 'prepare', 'finalize'] as const

export type PilotStep = (typeof PILOT_STEPS)[number]

/** Saida pequena e serializavel produzida pela etapa de preparacao. */
export interface PilotOutput {
    executionKey: string
    workflowId: string
    plannedSteps: PilotStep[]
    label: string
    count: number
    flag: boolean
}

/** Chaves exatas da saida do plano, em ordem canonica. */
const OUTPUT_KEYS = ['count', 'executionKey', 'flag', 'label', 'plannedSteps', 'workflowId']

/**
 * Contrato da saida do plano. Vale para um valor que voltou de serializacao:
 * as seis chaves, nenhuma a mais, cada uma do tipo esperado e as etapas na
 * ordem canonica.
 */
export function isPilotOutput(value: unknown): value is PilotOutput {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) return false

    const record = value as Record<string, unknown>
    const keys = Object.keys(record).sort()
    if (keys.length !== OUTPUT_KEYS.length || keys.some((key, index) => key !== OUTPUT_KEYS[index])) return false
    if (typeof record.executionKey !== 'string' || record.executionKey === '') return false
    if (typeof record.workflowId !== 'string' || record.workflowId === '') return false
    if (typeof record.label !== 'string') return false
    if (typeof record.count !== 'number' || !Number.isInteger(record.count) || record.count < 0) return false
    if (typeof record.flag !== 'boolean') return false

    const steps: unknown = record.plannedSteps
    return Array.isArray(steps) && steps.length === PILOT_STEPS.length && PILOT_STEPS.every((step, index) => steps[index] === step)
}

export function pilotExecutionKey(input: TemporalPilotInput): string {
    return `${input.requestId}::${input.operation}`
}

export function pilotWorkflowId(input: TemporalPilotInput): string {
    return `temporal-pilot-${input.requestId}`
}

export function buildPilotOutput(input: TemporalPilotInput): PilotOutput {
    return {
        executionKey: pilotExecutionKey(input),
        workflowId: pilotWorkflowId(input),
        plannedSteps: [...PILOT_STEPS],
        label: input.payload.label ?? '',
        count: input.payload.count ?? 0,
        flag: input.payload.flag ?? false,
    }
}
