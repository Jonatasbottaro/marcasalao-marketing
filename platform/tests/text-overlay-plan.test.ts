/**
 * Testes unitarios do TextOverlayPlan v1:
 * - Validacao semantica e codigos de erro estaveis
 * - Resolucao temporal dos intervalos a partir do pacote canonico
 * - Serializacao canonica deterministica
 * - Compatibilidade com casos reais do repositorio (Marca Salao e Multitrack Hub)
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { test } from 'node:test'

import { createCreativeExecutionPackageFromCase } from '../src/creative-execution-packages.js'
import { serializeTextOverlayPlan } from '../src/serialize-text-overlay-plan.js'
import { validateTextOverlayPlan } from '../src/validate-text-overlay-plan.js'
import { moduleRoot } from './contract-harness.js'

const examplesRoot = path.join(moduleRoot, 'examples')
const marcaManifest = path.join(examplesRoot, 'pipelines', 'marca-salao-pipeline-pilot.pipeline.json')
const multitrackManifest = path.join(examplesRoot, 'pipelines', 'multitrack-hub-pipeline-pilot.pipeline.json')

function loadExamplePackage(manifestPath: string) {
    const result = createCreativeExecutionPackageFromCase(manifestPath, examplesRoot)
    if (result.status !== 'generated' || result.package === null) {
        throw new Error(`Falha ao gerar pacote do caso ${manifestPath}: ${result.summary}`)
    }
    return {
        pkg: result.package,
        caseId: result.caseId as string,
    }
}

test('validacao semantica: rejeita pacote invalido', () => {
    const plan = {
        schemaVersion: 1,
        caseId: 'marca-salao-pipeline-pilot',
        overlays: [],
    }
    const result = validateTextOverlayPlan({ schemaVersion: 999 }, 'marca-salao-pipeline-pilot', plan)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'PACKAGE_INVALID')
    }
})

test('validacao semantica: rejeita divergencia de caseId', () => {
    const { pkg } = loadExamplePackage(marcaManifest)
    const plan = {
        schemaVersion: 1,
        caseId: 'outro-caso',
        overlays: [
            {
                beatId: 'demonstration-body',
                text: 'Titulo para outro caso',
            },
        ],
    }
    const result = validateTextOverlayPlan(pkg, 'marca-salao-pipeline-pilot', plan)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'CASE_ID_MISMATCH')
        assert.equal(result.subject, 'outro-caso')
    }
})

test('validacao semantica: rejeita duplicidade de beatId', () => {
    const { pkg, caseId } = loadExamplePackage(marcaManifest)
    const plan = {
        schemaVersion: 1,
        caseId,
        overlays: [
            {
                beatId: 'demonstration-body',
                text: 'Primeiro titulo',
            },
            {
                beatId: 'demonstration-body',
                text: 'Segundo titulo para o mesmo beat',
            },
        ],
    }
    const result = validateTextOverlayPlan(pkg, caseId, plan)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'OVERLAY_BEAT_DUPLICATE')
        assert.equal(result.subject, 'demonstration-body')
    }
})

test('validacao semantica: rejeita beatId inexistente no pacote canonico', () => {
    const { pkg, caseId } = loadExamplePackage(marcaManifest)
    const plan = {
        schemaVersion: 1,
        caseId,
        overlays: [
            {
                beatId: 'beat-fantasma-inexistente',
                text: 'Titulo sem beat correspondente',
            },
        ],
    }
    const result = validateTextOverlayPlan(pkg, caseId, plan)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'UNKNOWN_BEAT_REFERENCE')
        assert.equal(result.subject, 'beat-fantasma-inexistente')
    }
})

test('validacao semantica: rejeita texto vazio ou apenas espacos', () => {
    const { pkg, caseId } = loadExamplePackage(marcaManifest)
    const plan = {
        schemaVersion: 1,
        caseId,
        overlays: [
            {
                beatId: 'demonstration-body',
                text: '   \t  \n ',
            },
        ],
    }
    const result = validateTextOverlayPlan(pkg, caseId, plan)
    assert.equal(result.ok, false)
    if (!result.ok) {
        assert.equal(result.failureCode, 'OVERLAY_TEXT_EMPTY')
        assert.equal(result.subject, 'demonstration-body')
    }
})

test('resolucao e compatibilidade com Marca Salao (feed reel)', () => {
    const { pkg, caseId } = loadExamplePackage(marcaManifest)
    const plan = {
        schemaVersion: 1,
        caseId,
        overlays: [
            {
                beatId: 'demonstration-body',
                text: 'Agendamento online descomplicado',
            },
        ],
    }
    const result = validateTextOverlayPlan(pkg, caseId, plan)
    assert.equal(result.ok, true)
    if (result.ok) {
        assert.equal(result.resolvedOverlays.length, 1)
        const overlay = result.resolvedOverlays[0]
        assert.ok(overlay !== undefined)
        assert.equal(overlay.beatId, 'demonstration-body')
        assert.equal(overlay.text, 'Agendamento online descomplicado')
        assert.equal(overlay.startMs, 4000)
        assert.equal(overlay.endMs, 10000)
        assert.equal(overlay.durationMs, 6000)
    }
})

test('resolucao e compatibilidade com Multitrack Hub (reels)', () => {
    const { pkg, caseId } = loadExamplePackage(multitrackManifest)
    const plan = {
        schemaVersion: 1,
        caseId,
        overlays: [
            {
                beatId: 'opening-hook',
                text: 'Sua mixagem profissional',
            },
            {
                beatId: 'closing-cta',
                text: 'Acesse multitrackhub.com.br',
            },
        ],
    }
    const result = validateTextOverlayPlan(pkg, caseId, plan)
    assert.equal(result.ok, true)
    if (result.ok) {
        assert.equal(result.resolvedOverlays.length, 2)
        const first = result.resolvedOverlays[0]
        const second = result.resolvedOverlays[1]
        assert.ok(first !== undefined)
        assert.ok(second !== undefined)
        assert.equal(first.beatId, 'opening-hook')
        assert.equal(first.startMs, 0)
        assert.equal(first.endMs, 3000)
        assert.equal(second.beatId, 'closing-cta')
        assert.equal(second.startMs, 12000)
        assert.equal(second.endMs, 15000)
    }
})

test('serializacao canonica e deterministica', () => {
    const plan1 = {
        schemaVersion: 1 as const,
        caseId: 'marca-salao-pipeline-pilot',
        overlays: [
            {
                beatId: 'demonstration-body',
                text: 'Titulo A',
            },
        ],
    }
    const json1 = serializeTextOverlayPlan(plan1)
    const json2 = serializeTextOverlayPlan({
        caseId: 'marca-salao-pipeline-pilot',
        schemaVersion: 1,
        overlays: [
            {
                text: 'Titulo A',
                beatId: 'demonstration-body',
            },
        ],
    } as any)

    assert.equal(json1, json2, 'A ordem de propriedades do objeto original nao deve alterar os bytes')
    assert.ok(json1.endsWith('\n'), 'A serializacao canonica deve terminar com newline')
    assert.equal(JSON.parse(json1).caseId, 'marca-salao-pipeline-pilot')
})
