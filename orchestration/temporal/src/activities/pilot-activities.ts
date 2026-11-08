/**
 * Activities do piloto TEMPORAL-01.
 *
 * As tres funcoes sao puras: recebem valor, devolvem valor, nao leem relogio,
 * ambiente, disco, rede nem arquivos, nao escrevem no repositorio e nao produzem
 * efeito real de negocio. Toda recusa e um ApplicationFailure nao retryable com
 * codigo estavel e mensagem sanitizada, para que o Workflow possa classificar
 * sem depender de texto livre.
 *
 * Cada atividade revalida o que recebeu porque o valor chega por serializacao:
 * a fronteira confiavel e o contrato, nao o chamador.
 */
import { ApplicationFailure } from '@temporalio/common'

import { PILOT_FAILURE_CODES } from '../pilot-core/failures.js'
import { parsePilotInput, type TemporalPilotInput } from '../pilot-core/pilot-input.js'
import { buildPilotOutput, isPilotOutput, type PilotOutput } from '../pilot-core/pilot-plan.js'
import { completedPilotResult, type TemporalPilotResult } from '../pilot-core/pilot-result.js'

function refuse(code: string, message: string): never {
    throw ApplicationFailure.create({ type: code, message, nonRetryable: true })
}

function requireValidInput(value: unknown): TemporalPilotInput {
    const parsed = parsePilotInput(value)
    if (!parsed.ok) refuse(parsed.code, parsed.message)
    return parsed.input
}

/** Forma canonica da saida: ordem fixa das seis chaves, sem dependencia de ordem de objeto. */
function canonicalOutput(output: PilotOutput): string {
    return JSON.stringify([output.executionKey, output.workflowId, output.plannedSteps, output.label, output.count, output.flag])
}

export async function validatePilotRequest(rawInput: unknown): Promise<TemporalPilotInput> {
    return requireValidInput(rawInput)
}

export async function preparePilotExecution(rawInput: TemporalPilotInput): Promise<PilotOutput> {
    return buildPilotOutput(requireValidInput(rawInput))
}

export async function finalizePilotExecution(rawInput: TemporalPilotInput, rawOutput: PilotOutput): Promise<TemporalPilotResult> {
    const input = requireValidInput(rawInput)
    const expected = buildPilotOutput(input)

    if (!isPilotOutput(rawOutput) || canonicalOutput(rawOutput) !== canonicalOutput(expected)) {
        refuse(PILOT_FAILURE_CODES.nonRetryable, 'A saida recebida nao corresponde ao plano desta entrada.')
    }

    return completedPilotResult(input, expected)
}
