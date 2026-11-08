/**
 * Cliente do piloto TEMPORAL-01.
 *
 * Inicia uma execucao na Task Queue do piloto contra um servidor local e imprime
 * o TemporalPilotResult como JSON. Codigo de saida: 0 em completed, 1 em rejeicao,
 * falha ou colisao de workflowId. Importar este modulo nao abre conexao.
 */
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { Client, Connection } from '@temporalio/client'

import { PILOT_FAILURE_CODES } from '../pilot-core/failures.js'
import { parsePilotInput } from '../pilot-core/pilot-input.js'
import { failedPilotResult, type TemporalPilotResult } from '../pilot-core/pilot-result.js'
import { PILOT_NAMESPACE } from '../workflows/content-pilot-workflow.js'
import { describeStartFailure, parseRunArguments, pilotStartOptions } from './pilot-start.js'

const WORKFLOW_NAME = 'contentPilotWorkflow'

function printJson(value: unknown): void {
    process.stdout.write(`${JSON.stringify(value, null, 4)}\n`)
}

function refuse(message: string): number {
    process.stderr.write(`${message}\n`)
    return 1
}

export async function runPilotClient(argv: readonly string[]): Promise<number> {
    const parsed = parseRunArguments(argv)
    if (!parsed.ok) return refuse(parsed.message)

    const input = parsePilotInput(parsed.config.rawInput)
    if (!input.ok) return refuse(`A entrada pedida nao passa no contrato do piloto: ${input.code} em ${input.path}.`)

    const connection = await Connection.connect({ address: parsed.config.address })
    try {
        const client = new Client({ connection, namespace: PILOT_NAMESPACE })
        const options = pilotStartOptions(input.input)

        let handle: Awaited<ReturnType<typeof client.workflow.start>>
        try {
            handle = await client.workflow.start(WORKFLOW_NAME, options)
        } catch (error) {
            // A colisao de workflowId e uma saida estruturada do piloto, nao um stack trace.
            printJson(failedPilotResult({ requestId: input.input.requestId, projectId: input.input.projectId }, describeStartFailure(error), []))
            return 1
        }

        const result: TemporalPilotResult = await handle.result()
        printJson(result)
        if (result.status !== 'completed') {
            process.stderr.write(`o piloto nao concluiu: ${result.failureCode ?? PILOT_FAILURE_CODES.workflowFailed}\n`)
        }
        return result.status === 'completed' ? 0 : 1
    } finally {
        await connection.close()
    }
}

function isEntrypoint(): boolean {
    const argv1 = process.argv[1]
    return argv1 !== undefined && import.meta.url === pathToFileURL(path.resolve(argv1)).href
}

if (isEntrypoint()) {
    runPilotClient(process.argv.slice(2)).then(
        (code) => {
            process.exitCode = code
        },
        (error: unknown) => {
            const message = error instanceof Error ? error.message : 'erro desconhecido'
            process.stderr.write(`o cliente do piloto nao rodou: ${message}\n`)
            process.exitCode = 1
        },
    )
}
