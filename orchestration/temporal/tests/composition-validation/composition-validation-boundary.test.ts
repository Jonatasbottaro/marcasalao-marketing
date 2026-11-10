/**
 * Guardas estaticas de fronteira para TEMPORAL-02-02.
 *
 * Comprova automaticamente que:
 * - os modulos de composition-validation nao importam @temporalio/*, workflows,
 *   activities, worker, client do piloto, platform, filesystem, rede ou child_process;
 * - nao usam process.env, Date.now, Math.random ou fetch;
 * - os tres codigos do preflight tem fonte unica em composition-validation-failures.ts
 *   e nao sao redeclarados literalmente em composition-validation-preflight.ts;
 * - os quatro codigos de etapas posteriores nao foram implementados nesta fatia;
 * - nao existem validate-composition-activity.ts nem validate-composition-workflow.ts;
 * - nenhuma referencia a OutputPlan ou BeatPlan existe no codigo;
 * - platform/ permanece livre de @temporalio/*.
 */
import assert from 'node:assert/strict'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import {
    COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST,
    COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES,
} from '../../src/composition-validation/composition-validation-failures.js'

const temporalRoot = fileURLToPath(new URL('../../../', import.meta.url))
const compositionValidationSrcDir = path.join(temporalRoot, 'src', 'composition-validation')
const platformSrcDir = fileURLToPath(new URL('../../../../../platform/src', import.meta.url))

function listTsFiles(dir: string): string[] {
    return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
        const full = path.join(dir, entry.name)
        if (entry.isDirectory()) return listTsFiles(full)
        return entry.name.endsWith('.ts') ? [full] : []
    })
}

function stripComments(source: string): string {
    return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '')
}

function importLines(source: string): string[] {
    return stripComments(source)
        .split(/\r?\n/)
        .filter((line) => /^\s*(import|export)\b/.test(line))
}

test('modulos de composition-validation existem e sao completamente independentes de Temporal, rede, disco, relogio, ambiente e aleatoriedade', () => {
    const files = listTsFiles(compositionValidationSrcDir)
    assert.deepEqual(
        files.map((f) => path.basename(f)).sort(),
        [
            'composition-validation-failures.ts',
            'composition-validation-input.ts',
            'composition-validation-preflight.ts',
        ],
    )

    const forbiddenImports = [
        /@temporalio\//,
        /\.\.\/workflows\//,
        /\.\.\/activities\//,
        /\.\.\/worker\//,
        /\.\.\/client\//,
        /\.\.\/local\//,
        /marcasalao-marketing-platform/,
        /platform\/src/,
        /node:fs/,
        /['"]fs['"]/,
        /node:net/,
        /node:http/,
        /node:https/,
        /node:child_process/,
        /node:dgram/,
        /node:tls/,
    ]

    const forbiddenTokens = [
        /\bprocess\.env\b/,
        /\bDate\.now\b/,
        /\bnew\s+Date\b/,
        /\bMath\.random\b/,
        /\bfetch\s*\(/,
        /\bOutputPlan\b/,
        /\bBeatPlan\b/,
    ]

    for (const file of files) {
        const raw = readFileSync(file, 'utf8')
        const code = stripComments(raw)
        const imports = importLines(raw)

        for (const pattern of forbiddenImports) {
            assert.equal(
                imports.some((line) => pattern.test(line)),
                false,
                `${path.basename(file)} nao pode importar ${pattern}`,
            )
        }

        for (const token of forbiddenTokens) {
            assert.equal(
                token.test(code),
                false,
                `${path.basename(file)} nao pode usar ${token}`,
            )
        }
    }
})

test('fonte unica imutavel para os tres codigos de preflight e ausencia dos quatro codigos futuros', () => {
    assert.deepEqual(Object.values(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES), [
        'TEMPORAL_COMPOSITION_INPUT_INVALID',
        'TEMPORAL_COMPOSITION_INPUT_TOO_LARGE',
        'TEMPORAL_COMPOSITION_SENSITIVE_INPUT',
    ])
    assert.deepEqual(
        [...COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST],
        Object.values(COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES),
    )

    const preflightFile = path.join(compositionValidationSrcDir, 'composition-validation-preflight.ts')
    const inputFile = path.join(compositionValidationSrcDir, 'composition-validation-input.ts')

    for (const file of [preflightFile, inputFile]) {
        const code = stripComments(readFileSync(file, 'utf8'))
        for (const literal of COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST) {
            assert.equal(
                code.includes(literal),
                false,
                `${path.basename(file)} nao deve redeclarar manualmente o literal ${literal}`,
            )
        }
    }

    const futureCodes = [
        'TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE',
        'TEMPORAL_COMPOSITION_ACTIVITY_FAILED',
        'TEMPORAL_COMPOSITION_TIMEOUT',
        'TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT',
    ]

    for (const file of listTsFiles(compositionValidationSrcDir)) {
        const code = stripComments(readFileSync(file, 'utf8'))
        for (const futureCode of futureCodes) {
            assert.equal(
                code.includes(futureCode),
                false,
                `${path.basename(file)} nao deve declarar codigo de etapa futura (${futureCode})`,
            )
        }
    }
})

test('Activity e Workflow de TEMPORAL-02 continuam ausentes e platform/ segue livre de Temporal', () => {
    assert.equal(
        existsSync(path.join(temporalRoot, 'src', 'activities', 'validate-composition-activity.ts')),
        false,
    )
    assert.equal(
        existsSync(path.join(temporalRoot, 'src', 'workflows', 'validate-composition-workflow.ts')),
        false,
    )

    for (const file of listTsFiles(platformSrcDir)) {
        const raw = readFileSync(file, 'utf8')
        assert.equal(
            raw.includes('@temporalio'),
            false,
            `platform/src/${path.basename(file)} nao pode referenciar @temporalio`,
        )
    }
})
