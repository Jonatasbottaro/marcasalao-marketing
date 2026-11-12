/**
 * Captura da historia de replay de TEMPORAL-02 (metodo documentado no README).
 *
 * Sobe createLocal, roda o Workflow integrado com Worker e cliente reais sobre
 * documentos de exemplo ficticios, grava a history e normaliza apenas campos
 * dependentes da maquina (timestamps e runIds) para valores fixos. O fixture
 * resultante e versionado em tests/replay/fixtures/ e consumido pelo teste de
 * replay formal. Uso: node scripts/capture-composition-replay-history.mjs
 * (requer build anterior; TEMP do processo redirecionavel para dentro da raiz).
 */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { TestWorkflowEnvironment } from '@temporalio/testing'

import { executeCompositionValidation } from '../dist/src/client/composition-validation-start.js'
import { createCompositionValidationWorker } from '../dist/src/worker/composition-validation-worker.js'

const packageRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..')
const repositoryRoot = path.resolve(packageRoot, '../..')
const fixturePath = path.join(packageRoot, 'tests/replay/fixtures/composition-validation-valid.history.json')

const FIXED_TIMESTAMP = '2026-01-01T00:00:00.000Z'
const FIXED_RUN_ID = '00000000-0000-0000-0000-000000000001'
const TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function normalize(value, key) {
    if (typeof value === 'string') {
        if (TIMESTAMP_PATTERN.test(value)) return FIXED_TIMESTAMP
        if (UUID_PATTERN.test(value)) return FIXED_RUN_ID
        return value
    }
    if (Array.isArray(value)) return value.map((item) => normalize(item, key))
    if (value !== null && typeof value === 'object') {
        // protobufjs serializa WKT como {seconds, nanos} (ou {} quando zero);
        // o proto JSON do replay exige Timestamp ISO e Duration string ("5s").
        const isDuration = /Timeout$|Interval$|Backoff$/.test(key ?? '')
        const isTimestamp = /Time$/.test(key ?? '')
        const isWktShell = 'seconds' in value || Object.keys(value).length === 0
        if ((isDuration || isTimestamp) && isWktShell) {
            const seconds = Number(value.seconds ?? 0)
            const nanos = Number(value.nanos ?? 0)
            return isDuration ? `${seconds + nanos / 1e9}s` : FIXED_TIMESTAMP
        }
        return Object.fromEntries(Object.entries(value).map(([k, item]) => [k, normalize(item, k)]))
    }
    return value
}

const project = JSON.parse(
    fs.readFileSync(path.join(repositoryRoot, 'platform/examples/projects/marca-salao.project.json'), 'utf8'),
)
const composition = JSON.parse(
    fs.readFileSync(
        path.join(repositoryRoot, 'platform/examples/compositions/marca-salao-pilot.composition.json'),
        'utf8',
    ),
)

const env = await TestWorkflowEnvironment.createLocal()
const runtime = await createCompositionValidationWorker({ address: env.address })
const workerRun = runtime.worker.run()
try {
    const execution = await executeCompositionValidation(env.client, {
        schemaVersion: 1,
        requestId: 'req-replay-0001',
        project,
        composition,
    })
    assert.equal(execution.ok, true)
    assert.equal(execution.result.status, 'valid')

    const history = await execution.start.handle.fetchHistory()
    const normalized = normalize(JSON.parse(JSON.stringify(history)), null)
    const serialized = `${JSON.stringify(normalized, null, 2)}\n`
    fs.writeFileSync(fixturePath, serialized, 'utf8')
    process.stdout.write(
        `${JSON.stringify({
            fixture: 'tests/replay/fixtures/composition-validation-valid.history.json',
            bytes: Buffer.byteLength(serialized, 'utf8'),
            sha256: createHash('sha256').update(serialized).digest('hex'),
            events: normalized.events?.length ?? 0,
        })}\n`,
    )
} finally {
    runtime.worker.shutdown()
    await workerRun
    await runtime.connection.close()
    await env.teardown()
}