/**
 * Inicio do piloto TEMPORAL-01 pelo cliente.
 *
 * Aqui mora a unica escolha de enderecamento do piloto: task queue, workflowId
 * derivado do requestId e politicas de colisao. O endereco e validado pela guarda
 * compartilhada de src/local-address.ts, para que o cliente e o worker de
 * demonstracao nao possam divergir sobre o que significa "local": um erro de
 * digitacao nao liga o piloto contra producao, staging ou Temporal Cloud.
 */
import { WorkflowExecutionAlreadyStartedError } from '@temporalio/common'
import { WorkflowIdConflictPolicy, WorkflowIdReusePolicy } from '@temporalio/client'

import { PILOT_FAILURE_CODES, type PilotFailureCode } from '../pilot-core/failures.js'
import { PILOT_OPERATION, PILOT_SCHEMA_VERSION, parsePilotInput, type TemporalPilotInput } from '../pilot-core/pilot-input.js'
import { pilotWorkflowId } from '../pilot-core/pilot-plan.js'
import { DEFAULT_PILOT_ADDRESS, checkLocalAddress } from '../local-address.js'
import { PILOT_TASK_QUEUE } from '../workflows/content-pilot-workflow.js'

const INPUT_FLAG_NAMES = ['--request-id', '--project-id', '--label']
const RUN_FLAG_NAMES = ['--address', ...INPUT_FLAG_NAMES]

const DEMO_REQUEST_ID = 'req-0001'
const DEMO_PROJECT_ID = 'marcasalao'
const DEMO_LABEL = 'piloto'

export interface PilotRunConfig {
    address: string
    rawInput: Record<string, unknown>
}

type Refusal = { ok: false; message: string }

export type RunArgumentsResult = { ok: true; config: PilotRunConfig } | Refusal

export type InputArgumentsResult = { ok: true; rawInput: Record<string, unknown> } | Refusal

export interface PilotStartOptions {
    taskQueue: string
    workflowId: string
    args: unknown[]
    workflowIdReusePolicy: WorkflowIdReusePolicy
    workflowIdConflictPolicy: WorkflowIdConflictPolicy
}

function refuse(message: string): Refusal {
    return { ok: false, message }
}

function readFlags(argv: readonly string[], allowed: readonly string[]): { ok: true; values: Map<string, string> } | Refusal {
    const values = new Map<string, string>()

    for (let index = 0; index < argv.length; index += 2) {
        const flag = argv[index] as string
        if (!allowed.includes(flag)) return refuse(`Flag nao reconhecida: ${flag}. As flags sao ${allowed.join(', ')}.`)
        const value = argv[index + 1]
        if (value === undefined || value.startsWith('--')) return refuse(`A flag ${flag} exige um valor.`)
        if (values.has(flag)) return refuse(`A flag ${flag} foi repetida.`)
        values.set(flag, value)
    }

    return { ok: true, values }
}

function buildRawInput(values: Map<string, string>): Record<string, unknown> {
    return {
        schemaVersion: PILOT_SCHEMA_VERSION,
        requestId: values.get('--request-id') ?? DEMO_REQUEST_ID,
        projectId: values.get('--project-id') ?? DEMO_PROJECT_ID,
        operation: PILOT_OPERATION,
        payload: { label: values.get('--label') ?? DEMO_LABEL },
    }
}

function refusalForInput(rawInput: Record<string, unknown>): Refusal | null {
    const parsed = parsePilotInput(rawInput)
    if (parsed.ok) return null
    return refuse(`A entrada pedida nao passa no contrato do piloto: ${parsed.code} em ${parsed.path}.`)
}

export function parseRunArguments(argv: readonly string[]): RunArgumentsResult {
    const flags = readFlags(argv, RUN_FLAG_NAMES)
    if (!flags.ok) return flags

    const address = flags.values.get('--address') ?? DEFAULT_PILOT_ADDRESS
    const addressProblem = checkLocalAddress(address)
    if (addressProblem !== null) return refuse(addressProblem)

    const rawInput = buildRawInput(flags.values)
    const inputProblem = refusalForInput(rawInput)
    if (inputProblem !== null) return inputProblem

    return { ok: true, config: { address, rawInput } }
}

/**
 * Argumentos da execucao local, que sobe o servidor efemero do proprio SDK. La
 * nao ha endereco a escolher, entao --address e recusada em vez de ignorada.
 */
export function parseInputArguments(argv: readonly string[]): InputArgumentsResult {
    if (argv.includes('--address')) {
        return refuse('A execucao local usa o servidor efemero do proprio SDK: --address nao se aplica a ela.')
    }

    const flags = readFlags(argv, INPUT_FLAG_NAMES)
    if (!flags.ok) return flags

    const rawInput = buildRawInput(flags.values)
    const inputProblem = refusalForInput(rawInput)
    if (inputProblem !== null) return inputProblem

    return { ok: true, rawInput }
}

export function pilotStartOptions(input: TemporalPilotInput): PilotStartOptions {
    return {
        taskQueue: PILOT_TASK_QUEUE,
        workflowId: pilotWorkflowId(input),
        args: [input],
        workflowIdReusePolicy: WorkflowIdReusePolicy.REJECT_DUPLICATE,
        workflowIdConflictPolicy: WorkflowIdConflictPolicy.FAIL,
    }
}

/** Colisao de workflowId tem codigo proprio: um segundo pedido nunca e silencioso. */
export function describeStartFailure(error: unknown): PilotFailureCode {
    return error instanceof WorkflowExecutionAlreadyStartedError ? PILOT_FAILURE_CODES.workflowIdConflict : PILOT_FAILURE_CODES.workflowFailed
}
