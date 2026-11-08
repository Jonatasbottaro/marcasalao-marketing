/**
 * Execucao local do piloto TEMPORAL-01 (`npm run pilot:local`).
 *
 * Sobe o servidor efemero do proprio SDK, roda um `requestId` de demonstracao do
 * inicio ao fim e derruba tudo no `finally`. O binario do servidor fica no cache
 * do usuario, nunca no checkout, e o endereco dele nao e escolhivel daqui.
 * Importar este modulo nao sobe servidor.
 */
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { TestWorkflowEnvironment } from '@temporalio/testing'
import { Worker } from '@temporalio/worker'

import * as pilotActivities from '../activities/pilot-activities.js'
import { parseInputArguments, pilotStartOptions } from '../client/pilot-start.js'
import { PILOT_FAILURE_CODES } from '../pilot-core/failures.js'
import { parsePilotInput } from '../pilot-core/pilot-input.js'
import type { TemporalPilotResult } from '../pilot-core/pilot-result.js'
import { PILOT_NAMESPACE, PILOT_TASK_QUEUE } from '../workflows/content-pilot-workflow.js'

const WORKFLOW_NAME = 'contentPilotWorkflow'
const workflowsPath = fileURLToPath(new URL('../workflows/content-pilot-workflow.js', import.meta.url))

function refuse(message: string): number {
    process.stderr.write(`${message}\n`)
    return 1
}

export async function runPilotLocally(argv: readonly string[]): Promise<number> {
    const parsed = parseInputArguments(argv)
    if (!parsed.ok) return refuse(parsed.message)

    const input = parsePilotInput(parsed.rawInput)
    if (!input.ok) return refuse(`A entrada pedida nao passa no contrato do piloto: ${input.code} em ${input.path}.`)

    const env = await TestWorkflowEnvironment.createLocal()
    try {
        const worker = await Worker.create({
            connection: env.nativeConnection,
            namespace: PILOT_NAMESPACE,
            taskQueue: PILOT_TASK_QUEUE,
            workflowsPath,
            activities: pilotActivities,
        })

        const result: TemporalPilotResult = await worker.runUntil(async () => {
            const handle = await env.client.workflow.start(WORKFLOW_NAME, pilotStartOptions(input.input))
            return await handle.result()
        })

        process.stdout.write(`${JSON.stringify(result, null, 4)}\n`)
        if (result.status !== 'completed') {
            process.stderr.write(`o piloto nao concluiu: ${result.failureCode ?? PILOT_FAILURE_CODES.workflowFailed}\n`)
        }
        return result.status === 'completed' ? 0 : 1
    } finally {
        await env.teardown()
    }
}

function isEntrypoint(): boolean {
    const argv1 = process.argv[1]
    return argv1 !== undefined && pathToFileURL(path.resolve(argv1)).href === import.meta.url
}

if (isEntrypoint()) {
    runPilotLocally(process.argv.slice(2)).then(
        (code) => {
            process.exitCode = code
        },
        (error: unknown) => {
            const message = error instanceof Error ? error.message : 'erro desconhecido'
            process.stderr.write(`a execucao local do piloto nao rodou: ${message}\n`)
            process.exitCode = 1
        },
    )
}
