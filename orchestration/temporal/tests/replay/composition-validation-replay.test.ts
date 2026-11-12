/**
 * Replay formal de TEMPORAL-02 com Worker.runReplayHistory (SDK 1.25.0).
 *
 * - replay da historia versionada (fixture normalizado, dados ficticios) passa
 *   com o Workflow integrado atual;
 * - o mesmo fixture replayado contra um Workflow divergente de teste FALHA:
 *   prova que o gate detecta nao-determinismo, nao e simples repeticao;
 * - historia fresca gerada na propria execucao tambem replaya com sucesso.
 *
 * O fixture nao contem project/composition sensiveis (exemplos tecnicos),
 * caminhos locais, timestamps de maquina nem runIds reais (normalizados na
 * captura). Nao ha alegacao de compatibilidade com versoes futuras.
 */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { TestWorkflowEnvironment } from '@temporalio/testing'
import { Worker, bundleWorkflowCode } from '@temporalio/worker'

import { validateCompositionActivity } from '../../src/activities/composition-validation-activity.js'
import { executeCompositionValidation } from '../../src/client/composition-validation-start.js'
import { COMPOSITION_VALIDATION_TASK_QUEUE } from '../../src/client/composition-validation-start.js'
import type { JsonObject } from '../../src/composition-validation/composition-validation-input.js'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const packageRoot = path.resolve(testDir, '../../..')
const repositoryRoot = path.resolve(packageRoot, '../..')
const workflowsPath = path.join(packageRoot, 'dist/src/workflows/composition-validation-workflow.js')
const divergentPath = path.join(packageRoot, 'dist/tests/replay/fixtures/divergent-workflow.js')
const fixturePath = path.join(packageRoot, 'tests/replay/fixtures/composition-validation-valid.history.json')

const project = JSON.parse(
    fs.readFileSync(path.join(repositoryRoot, 'platform/examples/projects/marca-salao.project.json'), 'utf8'),
) as JsonObject

const composition = JSON.parse(
    fs.readFileSync(
        path.join(repositoryRoot, 'platform/examples/compositions/marca-salao-pilot.composition.json'),
        'utf8',
    ),
) as JsonObject

function readFixture(): unknown {
    return JSON.parse(fs.readFileSync(fixturePath, 'utf8'))
}

test('replay formal: historia versionada passa com o Workflow integrado', async () => {
    const workflowBundle = await bundleWorkflowCode({ workflowsPath })
    await Worker.runReplayHistory({ workflowBundle }, readFixture())
})

test('replay formal: historia versionada falha contra Workflow divergente (gate de determinismo)', async () => {
    const divergentBundle = await bundleWorkflowCode({ workflowsPath: divergentPath })
    await assert.rejects(Worker.runReplayHistory({ workflowBundle: divergentBundle }, readFixture()))
})

test('replay formal: historia fresca da execucao atual replaya sem divergencia', async () => {
    const workflowBundle = await bundleWorkflowCode({ workflowsPath })
    const env = await TestWorkflowEnvironment.createTimeSkipping()
    const worker = await Worker.create({
        connection: env.nativeConnection,
        taskQueue: COMPOSITION_VALIDATION_TASK_QUEUE,
        workflowBundle,
        activities: { validateCompositionActivity },
    })
    const workerRun = worker.run()
    try {
        const execution = await executeCompositionValidation(env.client, {
            schemaVersion: 1,
            requestId: 'req-replay-fresh',
            project,
            composition,
        })
        assert.equal(execution.ok, true)
        if (execution.ok) {
            // Instancia History do SDK (eventId Long): validateHistory usa direto.
            const history = await execution.start.handle.fetchHistory()
            await Worker.runReplayHistory({ workflowBundle }, history)
        }
    } finally {
        worker.shutdown()
        await workerRun
        await env.teardown()
    }
})