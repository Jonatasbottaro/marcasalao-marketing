/**
 * Testes da Activity validateCompositionActivity (TEMPORAL-02-03).
 *
 * Cobre:
 * - Paridade estrita campo a campo com validateComposition(composition, project) do nucleo;
 * - Preservacao da ordem correta dos argumentos (Composition primeiro, ProjectManifest depois);
 * - Imutabilidade dos inputs recebidos;
 * - Idempotencia das chamadas sucessivas;
 * - Retorno normal de relatorios com valid: false (sem excecao);
 * - Tratamento e conversao de erros inesperados em ApplicationFailure nao-retryable;
 * - Pureza e isolamento de fronteira (zero I/O, rede, subprocesso, sem imports internos de platform/src).
 */

import assert from 'node:assert/strict'
import childProcess from 'node:child_process'
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { ApplicationFailure } from '@temporalio/common'
import {
    validateComposition,
    type Composition,
    type CompositionValidationReport,
    type ProjectManifest,
} from 'marcasalao-marketing-platform'

import {
    TEMPORAL_COMPOSITION_ACTIVITY_FAILED,
    TEMPORAL_COMPOSITION_ACTIVITY_FAILED_MESSAGE,
    validateCompositionActivity,
    type CompositionValidationActivityInput,
} from '../../src/activities/composition-validation-activity.js'

const testDir = path.dirname(fileURLToPath(import.meta.url))
const repositoryRoot = path.resolve(testDir, '../../../../..')
const platformExamplesProjectsDir = path.join(repositoryRoot, 'platform', 'examples', 'projects')
const platformExamplesCompositionsDir = path.join(repositoryRoot, 'platform', 'examples', 'compositions')

function readJson<T>(filePath: string): T {
    return JSON.parse(fs.readFileSync(filePath, 'utf8')) as T
}

function deepFreeze<T>(obj: T): T {
    if (obj === null || typeof obj !== 'object') return obj
    Object.freeze(obj)
    for (const key of Object.keys(obj as object)) {
        const val = (obj as Record<string, unknown>)[key]
        if (val !== null && typeof val === 'object' && !Object.isFrozen(val)) {
            deepFreeze(val)
        }
    }
    return obj
}

const marcaSalaoProject = readJson<ProjectManifest>(
    path.join(platformExamplesProjectsDir, 'marca-salao.project.json'),
)
const marcaSalaoComposition = readJson<Composition>(
    path.join(platformExamplesCompositionsDir, 'marca-salao-pilot.composition.json'),
)
const fixtureProject = readJson<ProjectManifest>(
    path.join(platformExamplesProjectsDir, 'fixture-project.project.json'),
)
const fixtureComposition = readJson<Composition>(
    path.join(platformExamplesCompositionsDir, 'fixture-project-pilot.composition.json'),
)

interface CorpusCase {
    readonly description: string
    readonly project: unknown
    readonly composition: unknown
}

const corpus: CorpusCase[] = [
    {
        description: 'exemplo oficial Marca Salao (valido)',
        project: marcaSalaoProject,
        composition: marcaSalaoComposition,
    },
    {
        description: 'exemplo oficial Fixture Project (valido)',
        project: fixtureProject,
        composition: fixtureComposition,
    },
    {
        description: 'project com schemaVersion invalido (invalido)',
        project: { ...marcaSalaoProject, schemaVersion: 99 },
        composition: marcaSalaoComposition,
    },
    {
        description: 'project sem id e com locale vazio (invalido)',
        project: { ...marcaSalaoProject, id: '', locale: '' },
        composition: marcaSalaoComposition,
    },
    {
        description: 'composition com schemaVersion invalido (invalido)',
        project: marcaSalaoProject,
        composition: { ...marcaSalaoComposition, schemaVersion: 99 },
    },
    {
        description: 'composition com scenes vazias (valido no contrato v1)',
        project: marcaSalaoProject,
        composition: { ...marcaSalaoComposition, scenes: [] },
    },
    {
        description: 'projectId incompativel entre composition e project (mismatch)',
        project: marcaSalaoProject,
        composition: { ...marcaSalaoComposition, projectId: 'outro-projeto' },
    },
    {
        description: 'locale incompativel entre composition e project (mismatch)',
        project: marcaSalaoProject,
        composition: { ...marcaSalaoComposition, locale: 'en-US' },
    },
    {
        description: 'format.profile nao autorizado pelo manifesto (mismatch)',
        project: marcaSalaoProject,
        composition: {
            ...marcaSalaoComposition,
            format: { ...marcaSalaoComposition.format, profile: 'perfil-inexistente' },
        },
    },
    {
        description: 'composition com warnings (cena curta com duracao < 500ms)',
        project: marcaSalaoProject,
        composition: {
            ...marcaSalaoComposition,
            scenes: [
                {
                    id: 'curta',
                    type: 'text',
                    durationMs: 200,
                    content: { text: 'Oi' },
                },
            ],
        },
    },
    {
        description: 'multiplos erros acumulados de projeto e composicao',
        project: { ...marcaSalaoProject, id: 'invalido!', locale: '' },
        composition: { ...marcaSalaoComposition, projectId: 'diferente', format: { profile: 'x', width: 0, height: 0, fps: 0 } },
    },
]

test('paridade: validateCompositionActivity retorna exatamente o mesmo relatorio que a chamada direta em todo o corpus', async () => {
    for (const testCase of corpus) {
        const directReport = validateComposition(testCase.composition, testCase.project)
        const activityReport = await validateCompositionActivity({
            project: testCase.project,
            composition: testCase.composition,
        })

        assert.deepStrictEqual(
            activityReport,
            directReport,
            `Paridade violada no caso: ${testCase.description}`,
        )

        // Verificacao explicita campo a campo
        assert.equal(activityReport.valid, directReport.valid)
        assert.deepStrictEqual(activityReport.errors, directReport.errors)
        assert.deepStrictEqual(activityReport.warnings, directReport.warnings)
        assert.equal(activityReport.summary, directReport.summary)
        assert.equal(activityReport.projectId, directReport.projectId)
        assert.equal(activityReport.compositionId, directReport.compositionId)
        assert.equal(activityReport.schemaVersion, directReport.schemaVersion)
        assert.equal(activityReport.sceneCount, directReport.sceneCount)
        assert.equal(activityReport.totalDurationMs, directReport.totalDurationMs)
        assert.deepStrictEqual(activityReport.format, directReport.format)
        assert.equal(activityReport.rendererAdapter, directReport.rendererAdapter)
    }
})

test('ordem dos argumentos: validateCompositionActivity respeita estritamente (composition, project)', async () => {
    // Ordem correta: Composition primeiro, Project depois
    const correctDirectReport = validateComposition(marcaSalaoComposition, marcaSalaoProject)
    assert.equal(correctDirectReport.valid, true)

    // Se invertidos, o relatorio e invalido pois Composition nao e ProjectManifest
    const invertedDirectReport = validateComposition(marcaSalaoProject, marcaSalaoComposition)
    assert.equal(invertedDirectReport.valid, false)

    // A Activity recebe { project, composition } e deve chamar (composition, project)
    const activityReport = await validateCompositionActivity({
        project: marcaSalaoProject,
        composition: marcaSalaoComposition,
    })

    assert.equal(activityReport.valid, true)
    assert.deepStrictEqual(activityReport, correctDirectReport)
    assert.notDeepEqual(activityReport, invertedDirectReport)
})

test('imutabilidade: validateCompositionActivity nao altera nem muta os inputs recebidos', async () => {
    for (const testCase of corpus) {
        const projectClone = structuredClone(testCase.project)
        const compositionClone = structuredClone(testCase.composition)

        // Passa objetos profundamente congelados para garantir que nao ha escrita interna
        const frozenProject = deepFreeze(structuredClone(testCase.project))
        const frozenComposition = deepFreeze(structuredClone(testCase.composition))

        const report = await validateCompositionActivity({
            project: frozenProject,
            composition: frozenComposition,
        })

        assert.ok(report, 'deve produzir relatorio')
        assert.deepStrictEqual(frozenProject, projectClone, 'project nao deve ser mutado')
        assert.deepStrictEqual(frozenComposition, compositionClone, 'composition nao deve ser mutada')
    }
})

test('idempotencia: invocar validateCompositionActivity multiplas vezes com o mesmo input produz relatorios identicos', async () => {
    const input: CompositionValidationActivityInput = {
        project: marcaSalaoProject,
        composition: marcaSalaoComposition,
    }

    const report1 = await validateCompositionActivity(input)
    const report2 = await validateCompositionActivity(input)
    const report3 = await validateCompositionActivity(input)

    assert.deepStrictEqual(report1, report2)
    assert.deepStrictEqual(report2, report3)
})

test('resultado de dominio invalido (valid: false) e retornado normalmente sem lancar excecao', async () => {
    const invalidInputs: CompositionValidationActivityInput[] = [
        {
            project: { ...marcaSalaoProject, schemaVersion: 99 },
            composition: marcaSalaoComposition,
        },
        {
            project: marcaSalaoProject,
            composition: { ...marcaSalaoComposition, projectId: 'id-mismatch' },
        },
        {
            project: marcaSalaoProject,
            composition: { ...marcaSalaoComposition, scenes: [{ invalid: true }] },
        },
    ]

    for (const input of invalidInputs) {
        // Nao deve lancar excecao
        const report = await validateCompositionActivity(input)
        assert.equal(report.valid, false)
        assert.ok(report.errors.length > 0)
        assert.equal(typeof report.summary, 'string')
    }
})

test('tratamento de falha inesperada: lanca ApplicationFailure nao-retryable com codigo e mensagem fixa sanitizada', async () => {
    const invalidInvocationInputs: unknown[] = [
        null,
        undefined,
        'string invalida',
        12345,
        true,
    ]

    for (const badInput of invalidInvocationInputs) {
        let caught: unknown = null
        try {
            await validateCompositionActivity(badInput as CompositionValidationActivityInput)
            assert.fail('Deveria ter lancado erro para input malformado')
        } catch (error) {
            caught = error
        }

        assert.ok(
            caught instanceof ApplicationFailure,
            'O erro capturado deve ser uma instancia de ApplicationFailure',
        )
        assert.equal(caught.type, TEMPORAL_COMPOSITION_ACTIVITY_FAILED)
        assert.equal(caught.message, TEMPORAL_COMPOSITION_ACTIVITY_FAILED_MESSAGE)
        assert.equal(caught.nonRetryable, true)

        // Assegura ausencia de vazamento de stack trace ou caminho absoluto na mensagem
        assert.equal(caught.message.includes('Error:'), false)
        assert.equal(caught.message.includes('TypeError:'), false)
        assert.equal(caught.message.includes('\\'), false)
        assert.equal(caught.message.includes('/'), false)
    }
})

test('pureza e fronteira em runtime: execucao da Activity nao dispara I/O de disco, rede ou processos filhos', async () => {
    let ioAttempted = false
    const originalWriteFileSync = fs.writeFileSync
    const originalSpawn = childProcess.spawn
    const originalHttpRequest = http.request

    try {
        // Espionagem defensiva
        fs.writeFileSync = () => {
            ioAttempted = true
            throw new Error('I/O de escrita em disco proibido')
        }
        childProcess.spawn = () => {
            ioAttempted = true
            throw new Error('Execucao de subprocessos proibida')
        }
        http.request = () => {
            ioAttempted = true
            throw new Error('Acesso a rede proibido')
        }

        const report = await validateCompositionActivity({
            project: marcaSalaoProject,
            composition: marcaSalaoComposition,
        })

        assert.equal(report.valid, true)
        assert.equal(ioAttempted, false, 'Nenhuma operacao externa de I/O deve ser acionada')
    } finally {
        fs.writeFileSync = originalWriteFileSync
        childProcess.spawn = originalSpawn
        http.request = originalHttpRequest
    }
})

test('isolamento de fronteira estatico: modulo da Activity consome unicamente marcasalao-marketing-platform e nao importa caminhos internos', () => {
    const activitySourcePath = path.resolve(testDir, '../../../src/activities/composition-validation-activity.ts')
    const sourceCode = fs.readFileSync(activitySourcePath, 'utf8')

    // Deve importar do pacote oficial
    assert.ok(
        sourceCode.includes("from 'marcasalao-marketing-platform'"),
        'Deve importar exclusivamente de marcasalao-marketing-platform',
    )

    // Nao pode importar caminhos relativos para platform/src
    assert.equal(
        sourceCode.includes('platform/src'),
        false,
        'Nao deve importar caminhos relativos internos de platform/src',
    )
    assert.equal(
        sourceCode.includes('../platform'),
        false,
        'Nao deve conter imports relativos para ../platform',
    )

    // Nao pode importar fs, net ou child_process
    assert.equal(sourceCode.includes('node:fs'), false)
    assert.equal(sourceCode.includes('node:child_process'), false)
    assert.equal(sourceCode.includes('node:net'), false)
    assert.equal(sourceCode.includes('node:http'), false)
})
