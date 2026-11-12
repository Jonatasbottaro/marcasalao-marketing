/**
 * Execucao local real da validacao de Composition (`npm run composition:validate:local`).
 *
 * Sobe o servidor efemero do proprio SDK (createLocal), cria o Worker real pela
 * mesma fabrica do CLI de worker, usa o cliente real e mede tres caminhos:
 * valid, invalid e colisao de Workflow ID. Tudo derrubado no finally.
 * O binario do servidor usa o TEMP do processo (redirecionavel para dentro da
 * raiz do projeto); nenhum servidor remoto, nenhum Docker, nenhum namespace
 * de producao. Importar este modulo nao sobe servidor.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { TestWorkflowEnvironment } from '@temporalio/testing'

import type { JsonObject } from '../composition-validation/composition-validation-input.js'
import {
    executeCompositionValidation,
    startCompositionValidation,
    COMPOSITION_VALIDATION_START_FAILURE_CODES,
} from '../client/composition-validation-start.js'
import { createCompositionValidationWorker } from '../worker/composition-validation-worker.js'

const repositoryRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '../../../../..')

function readExample(relative: string): JsonObject {
    return JSON.parse(fs.readFileSync(path.join(repositoryRoot, relative), 'utf8')) as JsonObject
}

function printJson(value: unknown): void {
    process.stdout.write(`${JSON.stringify(value)}\n`)
}

export async function runCompositionValidationLocally(argv: readonly string[]): Promise<number> {
    if (argv.length > 0) {
        process.stderr.write('A execucao local nao aceita argumentos: usa o servidor efemero do SDK e documentos de exemplo.\n')
        return 2
    }

    const project = readExample('platform/examples/projects/marca-salao.project.json')
    const composition = readExample('platform/examples/compositions/marca-salao-pilot.composition.json')
    const validInput = { schemaVersion: 1, requestId: 'req-local-valid', project, composition }
    const invalidInput = {
        schemaVersion: 1,
        requestId: 'req-local-invalid',
        project,
        composition: { ...composition, projectId: 'outro-projeto-incompativel' },
    }

    const env = await TestWorkflowEnvironment.createLocal()
    const runtime = await createCompositionValidationWorker({ address: env.address })
    const workerRun = runtime.worker.run()
    let outcomesOk = true
    try {
        const valid = await executeCompositionValidation(env.client, validInput)
        const validOk = valid.ok && valid.result.status === 'valid'
        outcomesOk = outcomesOk && validOk
        printJson({
            scenario: 'valid',
            ok: validOk,
            workflowId: valid.ok ? valid.start.workflowId : null,
            status: valid.ok ? valid.result.status : null,
            failureCode: valid.ok ? valid.result.failureCode : valid.start.failureCode,
        })

        const invalid = await executeCompositionValidation(env.client, invalidInput)
        const invalidOk = invalid.ok && invalid.result.status === 'invalid'
        outcomesOk = outcomesOk && invalidOk
        printJson({
            scenario: 'invalid',
            ok: invalidOk,
            workflowId: invalid.ok ? invalid.start.workflowId : null,
            status: invalid.ok ? invalid.result.status : null,
            failureCode: invalid.ok ? invalid.result.failureCode : invalid.start.failureCode,
        })

        const collision = await startCompositionValidation(env.client, validInput)
        const collisionOk =
            !collision.ok &&
            collision.failureCode === COMPOSITION_VALIDATION_START_FAILURE_CODES.workflowIdConflict
        outcomesOk = outcomesOk && collisionOk
        printJson({
            scenario: 'collision',
            ok: collisionOk,
            workflowId: collision.workflowId,
            status: null,
            failureCode: collision.ok ? null : collision.failureCode,
        })

        return outcomesOk ? 0 : 1
    } finally {
        runtime.worker.shutdown()
        await workerRun
        await runtime.connection.close()
        await env.teardown()
    }
}

function isEntrypoint(): boolean {
    const argv1 = process.argv[1]
    return argv1 !== undefined && import.meta.url === pathToFileURL(path.resolve(argv1)).href
}

if (isEntrypoint()) {
    runCompositionValidationLocally(process.argv.slice(2)).then(
        (code) => {
            process.exitCode = code
        },
        () => {
            process.stderr.write('a execucao local de composition nao rodou: erro tecnico sanitizado.\n')
            process.exitCode = 1
        },
    )
}