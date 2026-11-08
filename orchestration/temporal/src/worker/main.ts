/**
 * Worker do piloto TEMPORAL-01.
 *
 * Polla a Task Queue exclusiva do piloto e executa as tres Activities contra um
 * servidor local. O shutdown gracioso vem do Runtime do SDK, que escuta SIGINT,
 * SIGTERM, SIGQUIT e SIGUSR2: Ctrl+C para de pollar, deixa a Activity em curso
 * terminar e fecha a conexao. Importar este modulo nao inicia nada.
 */
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { NativeConnection, Worker } from '@temporalio/worker'

import * as pilotActivities from '../activities/pilot-activities.js'
import { resolveAddressArgument } from '../local-address.js'
import { PILOT_NAMESPACE, PILOT_TASK_QUEUE } from '../workflows/content-pilot-workflow.js'

/** O bundle do Workflow e gerado pelo webpack a partir deste arquivo-fonte. */
const workflowsPath = fileURLToPath(new URL('../workflows/content-pilot-workflow.js', import.meta.url))

export async function runPilotWorker(argv: readonly string[]): Promise<number> {
    const address = resolveAddressArgument(argv)
    if (!address.ok) {
        process.stderr.write(`${address.message}\n`)
        return 1
    }

    const connection = await NativeConnection.create({ address: address.address })
    try {
        const worker = await Worker.create({
            connection,
            namespace: PILOT_NAMESPACE,
            taskQueue: PILOT_TASK_QUEUE,
            workflowsPath,
            activities: pilotActivities,
        })

        process.stdout.write(`worker do piloto na task queue ${PILOT_TASK_QUEUE} contra ${address.address}\n`)
        await worker.run()
        process.stdout.write('worker do piloto encerrado\n')
        return 0
    } finally {
        await connection.close()
    }
}

function isEntrypoint(): boolean {
    const argv1 = process.argv[1]
    return argv1 !== undefined && import.meta.url === pathToFileURL(path.resolve(argv1)).href
}

if (isEntrypoint()) {
    runPilotWorker(process.argv.slice(2)).then(
        (code) => {
            process.exitCode = code
        },
        (error: unknown) => {
            const message = error instanceof Error ? error.message : 'erro desconhecido'
            process.stderr.write(`o worker do piloto nao rodou: ${message}\n`)
            process.exitCode = 1
        },
    )
}
