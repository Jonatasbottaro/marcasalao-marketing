/**
 * Exemplos versionados da R001-04: o que esta em `examples/` precisa executar.
 *
 * Os cinco planos sao comparados **byte a byte** com o stdout da CLI e depois
 * relidos pelo schema (Ajv) e por `validateOutputPlan` com o projeto
 * correspondente. A composicao antiga so entra na demonstracao de perfil
 * divergente depois de provar que `validateComposition` a aceita no manifesto
 * usado na demonstracao: sem essa prova o caso morreria em erro de composicao e
 * nunca alcanaria a comparacao entre os dois perfis.
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import type { OutputPlan } from '../src/output-plan-contract.js'
import { CATALOG_VERSION, findOutputProfile } from '../src/output-profiles/catalog.js'
import { resolveOutputPlan } from '../src/resolve-output-profile.js'
import { validateComposition } from '../src/validate-composition.js'
import { validateCompositionForOutputPlan } from '../src/validate-composition-output.js'
import { validateOutputPlan } from '../src/validate-output-plan.js'
import { validateProjectManifest } from '../src/validate-project.js'
import type { OutputCompatibilityReport } from '../src/validation-report.js'
import {
    moduleRoot,
    outputPlanSchemaCheck,
    readCompositionExample,
    readProjectExample,
} from './contract-harness.js'

const SOCIAL_PROJECT_FILE = 'marca-salao-social.project.json'
const TECHNICAL_COMPOSITION_FILE = 'marca-salao-social-reel.composition.json'
const LEGACY_COMPOSITION_FILE = 'marca-salao-pilot.composition.json'
const plansDir = path.join(moduleRoot, 'examples', 'output-plans')
const planCli = path.join(moduleRoot, 'dist', 'src', 'output-plan-cli.js')
const socialProjectPath = path.join(moduleRoot, 'examples', 'projects', SOCIAL_PROJECT_FILE)
const socialProject = readProjectExample(SOCIAL_PROJECT_FILE)

/** Um plano versionado e aCLI que o produz, na ordem em que aparecem no repositorio. */
const VERSIONED_PLANS: readonly { file: string; profileId: string; ruleContext?: 'studio-upload' }[] = [
    { file: 'instagram-feed-image-square.output-plan.json', profileId: 'instagram-feed-image-square' },
    { file: 'instagram-reels-video.output-plan.json', profileId: 'instagram-reels-video' },
    { file: 'facebook-reels-video.output-plan.json', profileId: 'facebook-reels-video' },
    { file: 'youtube-video-horizontal.output-plan.json', profileId: 'youtube-video-horizontal' },
    { file: 'youtube-shorts-studio-upload.output-plan.json', profileId: 'youtube-shorts', ruleContext: 'studio-upload' },
]

/** Perfis que a allowlist tecnica precisa cobrir, alem do preset legado da pilot. */
const REQUIRED_ALLOWLIST = VERSIONED_PLANS.map((plan) => plan.profileId)

/** Executa a CLI de plano e devolve o processo inteiro: stdout, stderr e exit. */
function runPlanCli(profileId: string, ruleContext?: string): { status: number | null; stdout: string; stderr: string } {
    const args = ['--project', socialProjectPath, '--profile', profileId, '--json']
    if (ruleContext !== undefined) args.push('--rule-context', ruleContext)
    const result = spawnSync(process.execPath, [planCli, ...args], { encoding: 'utf8' })
    return { status: result.status, stdout: result.stdout ?? '', stderr: result.stderr ?? '' }
}

function readFixture(filePath: string): string {
    return readFileSync(filePath, 'utf8')
}

function compatCodes(report: OutputCompatibilityReport): string[] {
    return report.errors.map((error) => error.code)
}

test('o manifesto tecnico social e valido e cobre os perfis dos exemplos', () => {
    const report = validateProjectManifest(socialProject)
    assert.deepEqual(report.errors, [], report.errors.map((error) => `${error.code} @${error.path}`).join(' | '))
    assert.equal(report.valid, true)
    assert.equal(report.projectId, 'marca-salao', 'o manifesto tecnico reusa o id do projeto oficial: e assim que a composicao antiga passa a valer nele')

    const allowed = socialProject.outputProfiles as string[]
    for (const profileId of REQUIRED_ALLOWLIST) {
        assert.ok(allowed.includes(profileId), `${profileId} precisa estar na allowlist tecnica`)
        assert.ok(findOutputProfile(profileId) !== null, `${profileId} precisa existir no catalogo`)
    }
    assert.ok(allowed.includes('vertical-social'), 'sem o preset legado a composicao da demonstracao seria rejeitada antes da comparacao')
    assert.deepEqual(allowed.filter((id) => !REQUIRED_ALLOWLIST.includes(id) && id !== 'vertical-social'), [])
})

test('validateComposition aceita a composicao antiga no manifesto da demonstracao', () => {
    const report = validateComposition(readCompositionExample(LEGACY_COMPOSITION_FILE), socialProject)
    assert.deepEqual(
        report.errors.map((error) => `${error.code} @${error.path}: ${error.message}`),
        [],
        'a prova precisa vir antes: sem composicao valida a compatibilidade nao compara perfil nenhum',
    )
    assert.equal(report.format?.profile, 'vertical-social')
})

test('dois perfis permitidos no mesmo manifesto chegam a OUTPUT_COMPAT_PROFILE_MISMATCH', () => {
    const resolution = resolveOutputPlan(socialProject, 'youtube-shorts', { ruleContext: 'studio-upload' })
    assert.notEqual(resolution.plan, null, resolution.report.errors.map((error) => error.code).join(' | '))

    const report = validateCompositionForOutputPlan(
        readCompositionExample(LEGACY_COMPOSITION_FILE),
        socialProject,
        resolution.plan,
    )
    assert.deepEqual(compatCodes(report), ['OUTPUT_COMPAT_PROFILE_MISMATCH'])
    assert.match(report.errors[0]?.message ?? '', /"vertical-social" is not the plan profile "youtube-shorts"/)
})

test('a composicao social positiva valida contra o manifesto e casa com o plano do mesmo perfil', () => {
    const composition = readCompositionExample(TECHNICAL_COMPOSITION_FILE)
    const compositionReport = validateComposition(composition, socialProject)
    assert.deepEqual(
        compositionReport.errors.map((error) => `${error.code} @${error.path}: ${error.message}`),
        [],
    )
    assert.equal(compositionReport.format?.profile, 'instagram-reels-video')

    const resolution = resolveOutputPlan(socialProject, 'instagram-reels-video')
    assert.notEqual(resolution.plan, null)
    const compat = validateCompositionForOutputPlan(composition, socialProject, resolution.plan)
    assert.deepEqual(
        compat.errors.map((error) => `${error.code} @${error.path}: ${error.message}`),
        [],
        'o exemplo positivo nao pode depender de aviso: erros tem de ser zero',
    )
    assert.equal(compat.valid, true)
})

test('cada plano versionado e exatamente o stdout da CLI', () => {
    for (const planFixture of VERSIONED_PLANS) {
        const result = runPlanCli(planFixture.profileId, planFixture.ruleContext)
        assert.equal(result.status, 0, `${planFixture.file}: ${result.stderr}`)

        const versioned = readFixture(path.join(plansDir, planFixture.file))
        assert.equal(
            versioned.includes('\r'),
            false,
            `${planFixture.file} contem CRLF; exemplos versionados devem usar exclusivamente LF`,
        )
        assert.ok(
            versioned.endsWith('\n') && !versioned.endsWith('\n\n'),
            `${planFixture.file} deve terminar com exatamente uma quebra de linha LF`,
        )
        assert.equal(
            versioned,
            result.stdout,
            `${planFixture.file} divergiu do stdout da CLI (indentacao, ordem das chaves ou newline final)`,
        )
    }
})

test('cada plano versionado passa no schema e no validador com o projeto correspondente', () => {
    for (const planFixture of VERSIONED_PLANS) {
        const filePath = path.join(plansDir, planFixture.file)
        const document = JSON.parse(readFixture(filePath)) as OutputPlan

        const schema = outputPlanSchemaCheck(document)
        assert.equal(schema.valid, true, `${planFixture.file}: ${schema.detail}`)

        const report = validateOutputPlan(document, socialProject)
        assert.deepEqual(
            report.errors.map((error) => `${error.code} @${error.path}: ${error.message}`),
            [],
            `${planFixture.file} nao validou contra ${SOCIAL_PROJECT_FILE}`,
        )
        assert.equal(report.catalogVersion, CATALOG_VERSION)
        assert.equal(report.projectId, 'marca-salao')
        assert.equal(report.profileId, planFixture.profileId)

        const profile = findOutputProfile(planFixture.profileId)
        assert.notEqual(profile, null)
        assert.equal(report.profileRevision, (profile as { revision: number }).revision)
        assert.equal(report.ruleContext, planFixture.ruleContext ?? null)
    }
})

test('os cinco planos cobrem imagem, Reels de cada rede, horizontal e Shorts com contexto', () => {
    const byProfile = VERSIONED_PLANS.map((planFixture) => {
        const document = JSON.parse(readFixture(path.join(plansDir, planFixture.file))) as OutputPlan
        return { profileId: document.profileId, mediaKind: document.mediaKind, ruleContext: document.ruleContext ?? null }
    })

    assert.deepEqual(byProfile, [
        { profileId: 'instagram-feed-image-square', mediaKind: 'image', ruleContext: null },
        { profileId: 'instagram-reels-video', mediaKind: 'video', ruleContext: null },
        { profileId: 'facebook-reels-video', mediaKind: 'video', ruleContext: null },
        { profileId: 'youtube-video-horizontal', mediaKind: 'video', ruleContext: null },
        { profileId: 'youtube-shorts', mediaKind: 'video', ruleContext: 'studio-upload' },
    ])

    const reels = byProfile.filter((item) => item.profileId.endsWith('-reels-video')).map((item) => item.profileId)
    assert.deepEqual(reels, ['instagram-reels-video', 'facebook-reels-video'], 'Reels de cada rede que tem Reels')
})

test('cada plano versionado ecoa o preset do catalogo, sem numero de tabela paralela', () => {
    for (const planFixture of VERSIONED_PLANS) {
        const document = JSON.parse(readFixture(path.join(plansDir, planFixture.file))) as OutputPlan
        const profile = findOutputProfile(planFixture.profileId)
        assert.notEqual(profile, null, `${planFixture.profileId} nao esta no catalogo`)

        const resolved = profile as { mediaKind: string; geometry: { width: number; height: number; aspectRatio: string }; fps: number }
        const expected = resolved.mediaKind === 'image'
            ? resolved.geometry
            : { ...resolved.geometry, fps: resolved.fps }
        assert.deepEqual(document.mediaKind === 'image' ? document.image : document.video, expected, planFixture.file)
        assert.equal(document.catalogVersion, CATALOG_VERSION)
        assert.equal(document.projectId, 'marca-salao')
    }
})

test('a CLI roda os dois exemplos pelos pontos de entrada, positivo e de perfil divergente', () => {
    const positive = spawnSync(process.execPath, [
        planCli,
        '--project', socialProjectPath,
        '--profile', 'instagram-reels-video',
        '--composition', path.join(moduleRoot, 'examples', 'compositions', TECHNICAL_COMPOSITION_FILE),
        '--json',
    ], { encoding: 'utf8' })
    assert.equal(positive.status, 0, positive.stderr)
    assert.deepEqual(Object.keys(JSON.parse(positive.stdout) as OutputPlan), [
        'schemaVersion', 'projectId', 'catalogVersion', 'profileId', 'profileRevision', 'mediaKind', 'video',
    ])
    assert.match(positive.stderr, /compatibilidade: composicao "social-reel-example" compativel/)

    const divergent = spawnSync(process.execPath, [
        planCli,
        '--project', socialProjectPath,
        '--profile', 'youtube-shorts',
        '--rule-context', 'studio-upload',
        '--composition', path.join(moduleRoot, 'examples', 'compositions', LEGACY_COMPOSITION_FILE),
        '--json',
    ], { encoding: 'utf8' })
    assert.equal(divergent.status, 1, 'perfil divergente e incompatibilidade, nao erro de uso')
    assert.equal(divergent.stdout, '')
    assert.match(divergent.stderr, /camada compatibilidade/)
    assert.match(divergent.stderr, /OUTPUT_COMPAT_PROFILE_MISMATCH/)
    assert.ok(!divergent.stderr.includes('OUTPUT_COMPAT_COMPOSITION_INVALID'), 'a composicao antiga precisa chegar valida na comparacao')
})
