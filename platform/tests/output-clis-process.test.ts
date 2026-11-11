/**
 * Testes de processo das CLIs da R001-04: `content:profiles` e
 * `content:plan-output`, executadas como JavaScript compilado em `dist/`.
 *
 * O contrato observado e o do processo: exit code, o que sai em stdout, o que sai
 * em stderr e a paridade com as funcoes puras em memoria. stdout do plano e o
 * artefato (parseavel por qualquer consumidor); diagnostico e pendencia vao para
 * stderr, inclusive no sucesso, porque "nao hah o que certificar" nao e erro.
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { after, test } from 'node:test'

import type { OutputPlan } from '../src/output-plan-contract.js'
import { CATALOG_VERSION, OUTPUT_PROFILES } from '../src/output-profiles/catalog.js'
import { resolveOutputPlan } from '../src/resolve-output-profile.js'
import {
    catalogProject,
    compositionWithScenes,
    moduleRoot,
    officialPairs,
    readProjectExample,
    sceneWith,
} from './contract-harness.js'

const profilesCli = path.join(moduleRoot, 'dist', 'src', 'output-profiles-cli.js')
const planCli = path.join(moduleRoot, 'dist', 'src', 'output-plan-cli.js')
const projectCli = path.join(moduleRoot, 'dist', 'src', 'validate-project-cli.js')
const compositionCli = path.join(moduleRoot, 'dist', 'src', 'validate-composition-cli.js')

const tempDir = mkdtempSync(path.join(os.tmpdir(), 'clis-saida-'))
const spacedDir = path.join(tempDir, 'pasta com espaco')
mkdirSync(spacedDir)

interface Run {
    status: number | null
    stdout: string
    stderr: string
}

/** Os argumentos vao como array: sem shell, sem interpolacao de caminho. */
function run(cli: string, args: string[]): Run {
    const result = spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8' })
    return { status: result.status, stdout: result.stdout ?? '', stderr: result.stderr ?? '' }
}

function writeJson(dir: string, name: string, document: unknown): string {
    const filePath = path.join(dir, name)
    writeFileSync(filePath, `${JSON.stringify(document, null, 2)}\n`, 'utf8')
    return filePath
}

const okProject = writeJson(tempDir, 'projeto-ok.json', catalogProject())
const horizontalOnlyProject = writeJson(tempDir, 'projeto-horizontal.json', catalogProject({ outputProfiles: ['youtube-video-horizontal'] }))
const brokenProject = writeJson(tempDir, 'projeto-invalido.json', { ...catalogProject(), schemaVersion: 2 })
const spacedProject = writeJson(spacedDir, 'projeto com espaco.json', catalogProject())
const malformedFile = path.join(tempDir, 'malformado.json')
writeFileSync(malformedFile, '{ nao e json', 'utf8')
const missingFile = path.join(tempDir, 'nao-existe.json')

/** Composition de Shorts com a soma de duracoes pedida, no preset do catalogo. */
function shortsComposition(durations: readonly number[]): string {
    return writeJson(tempDir, `comp-shorts-${durations.join('_')}.json`, compositionWithScenes(
        durations.map((durationMs, index) => sceneWith({ id: `cena-${index + 1}`, durationMs })),
        {
            projectId: 'projeto-teste',
            id: 'comp-shorts',
            title: 'Composicao Shorts',
            format: { profile: 'youtube-shorts', width: 1080, height: 1920, fps: 30 },
        },
    ))
}

/** Composicao vertical no preset de Reels do Instagram, para a duracao promovida na R001-05. */
function reelsComposition(durations: readonly number[]): string {
    return writeJson(tempDir, `comp-reels-${durations.join('_')}.json`, compositionWithScenes(
        durations.map((durationMs, index) => sceneWith({ id: `cena-${index + 1}`, durationMs })),
        {
            projectId: 'projeto-teste',
            id: 'comp-reels',
            title: 'Composicao Reels',
            format: { profile: 'instagram-reels-video', width: 1080, height: 1920, fps: 30 },
        },
    ))
}

interface ListingEntry {
    id: string
    name: string
    revision: number
    network: string
    publication: string
    mediaKind: string
    width: number
    height: number
    aspectRatio: string
    fps: number | null
    exportState: string
    exportEvidence: string[]
    pendingRuleIds: string[]
    availability: string
    blockCode: string | null
    blockReason: string | null
}

interface Listing {
    catalogVersion: string
    filters: { network: string | null; publication: string | null; mediaKind: string | null }
    project: { consulted: boolean; valid: boolean | null; id: string | null }
    counts: { listed: number; allowed: number; blocked: number; notConsulted: number }
    profiles: ListingEntry[]
    diagnostics: { code: string; path: string; message: string }[]
    summary: string
}

function idsOf(profiles: readonly ListingEntry[]): string[] {
    return profiles.map((profile) => profile.id)
}

after(() => rmSync(tempDir, { recursive: true, force: true }))

test('content:profiles sem projeto lista o catalogo inteiro com permissao nao consultada', () => {
    const result = run(profilesCli, ['--json'])
    assert.equal(result.status, 0, result.stderr)

    const body = JSON.parse(result.stdout) as Listing
    assert.deepEqual(Object.keys(body).sort(), [
        'catalogVersion', 'counts', 'diagnostics', 'filters', 'profiles', 'project', 'summary',
    ])
    assert.equal(body.catalogVersion, CATALOG_VERSION)
    assert.deepEqual(body.filters, { network: null, publication: null, mediaKind: null })
    assert.deepEqual(body.project, { consulted: false, valid: null, id: null })
    assert.deepEqual(body.diagnostics, [])
    assert.deepEqual(idsOf(body.profiles), OUTPUT_PROFILES.map((profile) => profile.id))
    assert.deepEqual(body.counts, {
        listed: OUTPUT_PROFILES.length,
        allowed: 0,
        blocked: 0,
        notConsulted: OUTPUT_PROFILES.length,
    })
    for (const profile of body.profiles) {
        assert.equal(profile.availability, 'not-consulted')
        assert.equal(profile.blockCode, null)
        assert.equal(profile.blockReason, null)
    }
    assert.match(body.summary, /permissao de projeto ainda nao consultada/)
})

test('content:profiles filtra por rede, destino e midia preservando a ordem do catalogo', () => {
    const youtubeVideos = JSON.parse(run(profilesCli, ['--network', 'youtube', '--media', 'video', '--json']).stdout) as Listing
    assert.deepEqual(idsOf(youtubeVideos.profiles), ['youtube-video-horizontal', 'youtube-shorts'])
    assert.deepEqual(youtubeVideos.filters, { network: 'youtube', publication: null, mediaKind: 'video' })
    assert.deepEqual(youtubeVideos.counts, { listed: 2, allowed: 0, blocked: 0, notConsulted: 2 })

    const reels = JSON.parse(run(profilesCli, ['--publication', 'reels', '--json']).stdout) as Listing
    assert.deepEqual(idsOf(reels.profiles), ['instagram-reels-video', 'facebook-reels-video'])

    const storiesImage = JSON.parse(run(profilesCli, ['--network', 'instagram', '--publication', 'stories', '--media', 'image', '--json']).stdout) as Listing
    assert.deepEqual(idsOf(storiesImage.profiles), ['instagram-stories-image'])
})

test('content:profiles aceita combinacao valida sem resultado e lista vazio com exit 0', () => {
    const result = run(profilesCli, ['--network', 'youtube', '--publication', 'stories', '--json'])
    assert.equal(result.status, 0, result.stderr)

    const body = JSON.parse(result.stdout) as Listing
    assert.deepEqual(body.profiles, [])
    assert.deepEqual(body.counts, { listed: 0, allowed: 0, blocked: 0, notConsulted: 0 })
})

test('content:profiles com projeto valido habilita o allowlist e da motivo para cada bloqueio', () => {
    const result = run(profilesCli, ['--network', 'youtube', '--project', horizontalOnlyProject, '--json'])
    assert.equal(result.status, 0, result.stderr)

    const body = JSON.parse(result.stdout) as Listing
    assert.deepEqual(body.project, { consulted: true, valid: true, id: 'projeto-teste' })
    assert.deepEqual(idsOf(body.profiles), ['youtube-video-horizontal', 'youtube-shorts'])
    assert.deepEqual(body.counts, { listed: 2, allowed: 1, blocked: 1, notConsulted: 0 })
    assert.deepEqual(body.diagnostics, [])

    const blocked = body.profiles[1] as ListingEntry
    assert.equal(blocked.availability, 'blocked')
    assert.equal(blocked.blockCode, 'OUTPUT_PROFILE_NOT_ALLOWED')
    assert.match(blocked.blockReason ?? '', /"youtube-shorts"/)
    assert.match(blocked.blockReason ?? '', /"projeto-teste"/)
})

test('content:profiles com manifesto invalido lista filtrado bloqueado pelo manifesto e sai 1', () => {
    const result = run(profilesCli, ['--publication', 'shorts', '--project', brokenProject, '--json'])
    assert.equal(result.status, 1, 'manifesto invalido precisa sair 1')
    assert.match(result.stderr, /OUTPUT_PROJECT_INVALID/)

    const body = JSON.parse(result.stdout) as Listing
    assert.deepEqual(idsOf(body.profiles), ['youtube-shorts'])
    assert.deepEqual(body.project, { consulted: true, valid: false, id: 'projeto-teste' })
    assert.deepEqual(body.counts, { listed: 1, allowed: 0, blocked: 1, notConsulted: 0 })
    assert.equal(body.profiles[0]?.availability, 'blocked')
    assert.equal(body.profiles[0]?.blockCode, 'OUTPUT_PROJECT_INVALID')
    assert.ok(body.diagnostics.length > 0, 'o diagnostico do manifesto tem de acompanhar a lista')
    assert.deepEqual(body.diagnostics.map((item) => item.code), ['PROJECT_SCHEMA_VERSION_UNSUPPORTED'])
})

test('content:profiles trata enum desconhecido, flag duplicada, flag estranha e valor ausente como erro de uso', () => {
    const usages = [
        ['--network', 'tiktok'],
        ['--publication', 'lives'],
        ['--media', 'audio'],
        ['--rule-context', 'in-app'],
        ['--network', 'instagram', '--network', 'facebook'],
        ['--json', '--json'],
        ['--canal', 'youtube'],
        ['--network'],
        ['--network', 'instagram', '--publication'],
    ]

    for (const args of usages) {
        const result = run(profilesCli, args)
        assert.equal(result.status, 2, `${args.join(' ')}: esperava 2, stdout=${result.stdout} stderr=${result.stderr}`)
        assert.equal(result.stdout, '', `${args.join(' ')}: erro de uso nao imprime listagem em stdout`)
        assert.match(result.stderr, /^Erro de uso: /)
        assert.ok(!result.stderr.includes(' at '), 'sem stack trace')
    }
})

test('content:profiles trata arquivo ausente e JSON malformado como erro de uso', () => {
    for (const filePath of [missingFile, malformedFile]) {
        const result = run(profilesCli, ['--project', filePath])
        assert.equal(result.status, 2, `${filePath}: esperava 2`)
        assert.equal(result.stdout, '')
        assert.match(result.stderr, /^Erro: /)
    }
})

test('content:profiles na saida humana mostra ID, nome, destino, midia, resolucao, fps e capacidade', () => {
    const result = run(profilesCli, ['--network', 'youtube', '--project', okProject])
    assert.equal(result.status, 0, result.stderr)

    assert.match(result.stdout, /youtube-shorts/)
    assert.match(result.stdout, /Shorts do YouTube/)
    assert.match(result.stdout, /destino: youtube\/shorts/)
    assert.match(result.stdout, /midia: video/)
    assert.match(result.stdout, /resolucao: 1080x1920 \(9:16\)/)
    assert.match(result.stdout, /fps: 30/)
    assert.match(result.stdout, /capacidade de catalogo: canvas-template-mapped/)
    assert.match(result.stdout, /templates\/story_reel_vertical\/index\.html:5/)
    assert.match(result.stdout, /pendencias de fonte: P-YT-03/)

    const horizontal = run(profilesCli, ['--network', 'youtube', '--publication', 'video'])
    assert.match(horizontal.stdout, /fps: 30/, 'perfil de video traz o fps do preset')
    assert.match(horizontal.stdout, /pendencias de fonte: \(nenhuma\)/, 'a duracao e o peso do video longo do YouTube foram certificados')

    const storiesImage = run(profilesCli, ['--network', 'instagram', '--publication', 'stories', '--media', 'image'])
    assert.match(storiesImage.stdout, /instagram-stories-image/)
    assert.match(storiesImage.stdout, /fps: n\/a/, 'perfil de imagem nao tem fps')
})

test('content:profiles com caminho de fixture contendo espaco lista o catalogo do projeto', () => {
    const result = run(profilesCli, ['--network', 'youtube', '--project', spacedProject, '--json'])
    assert.equal(result.status, 0, result.stderr)

    const body = JSON.parse(result.stdout) as Listing
    assert.deepEqual(body.counts, { listed: 2, allowed: 2, blocked: 0, notConsulted: 0 })
    assert.ok(!result.stdout.includes(spacedDir), 'a saida nao pode expor o caminho da maquina')
})

test('content:plan-output exige --project e --profile e recusa entrada malformada como erro de uso', () => {
    const composition = shortsComposition([90000])
    const usages = [
        [],
        ['--project', okProject],
        ['--profile', 'youtube-shorts'],
        ['--project', okProject, '--profile'],
        ['--project', okProject, '--profile', 'youtube-shorts', '--canal', 'yt'],
        ['--project', okProject, '--profile', 'youtube-shorts', '--media', 'audio'],
        ['--project', okProject, '--profile', 'youtube-shorts', '--rule-context', 'nao-existe'],
        ['--project', okProject, '--profile', 'youtube-shorts', '--rule-context'],
        ['--project', okProject, '--profile', 'youtube-shorts', '--profile', 'youtube-video-horizontal'],
        ['--project', missingFile, '--profile', 'youtube-shorts'],
        ['--project', malformedFile, '--profile', 'youtube-shorts'],
        ['--project', okProject, '--profile', 'youtube-shorts', '--composition', missingFile],
        ['--project', okProject, '--profile', 'youtube-shorts', '--composition', malformedFile],
    ]

    for (const args of usages) {
        const result = run(planCli, args)
        assert.equal(result.status, 2, `${args.join(' ')}: stdout=${result.stdout} stderr=${result.stderr}`)
        assert.equal(result.stdout, '', `${args.join(' ')}: erro de uso deixa stdout vazio`)
        assert.ok(!result.stderr.includes(' at '), 'sem stack trace')
        assert.match(result.stderr, /^(Erro de uso: |Erro: )/, `mensagem de uso esperada em ${args.join(' ')}`)
    }

    assert.equal(run(planCli, ['--project', okProject, '--profile', 'youtube-shorts', '--composition', composition]).status, 0)
})

test('content:plan-output em JSON escreve em stdout exatamente o plano canonico do resolvedor', () => {
    const resolution = resolveOutputPlan(catalogProject(), 'youtube-shorts', { ruleContext: 'studio-upload' })
    assert.notEqual(resolution.plan, null)
    const expected = resolution.plan as OutputPlan

    const result = run(planCli, ['--project', okProject, '--profile', 'youtube-shorts', '--rule-context', 'studio-upload', '--json'])
    assert.equal(result.status, 0, result.stderr)
    assert.equal(result.stdout, `${JSON.stringify(expected, null, 2)}\n`, 'stdout e o artefato, com indentacao de 2 e newline final')
    assert.deepEqual(Object.keys(JSON.parse(result.stdout) as Record<string, unknown>), [
        'schemaVersion', 'projectId', 'catalogVersion', 'profileId', 'profileRevision', 'mediaKind', 'ruleContext', 'video',
    ], 'a ordem canonica de serializacao e do resolvedor')

    const withoutContext = run(planCli, ['--project', okProject, '--profile', 'youtube-shorts', '--json'])
    assert.equal(withoutContext.status, 0, withoutContext.stderr)
    assert.equal((JSON.parse(withoutContext.stdout) as OutputPlan).ruleContext, undefined)
})

test('content:plan-output mantem o sucesso com aviso de contexto e o rotulo da camada no stderr', () => {
    const result = run(planCli, ['--project', okProject, '--profile', 'youtube-shorts', '--json'])
    assert.equal(result.status, 0, result.stderr)
    assert.match(result.stderr, /camada plano/)
    assert.match(result.stderr, /OUTPUT_PLAN_CONTEXT_NOT_DECLARED/)
    assert.match(result.stderr, /R-YT-01/)
})

test('content:plan-output informa pendencias e requiresInspection mesmo no sucesso', () => {
    const result = run(planCli, ['--project', okProject, '--profile', 'youtube-shorts', '--rule-context', 'studio-upload', '--json'])
    assert.equal(result.status, 0, result.stderr)

    assert.match(result.stderr, /pendencias de fonte: P-YT-03/)
    assert.match(result.stderr, /requer inspecao: media-file, codec, bytes, audio-streams, publication/)

    const image = run(planCli, ['--project', okProject, '--profile', 'instagram-feed-image-square', '--json'])
    assert.equal(image.status, 0, image.stderr)
    assert.match(image.stderr, /requer inspecao: media-file, image-format, bytes, publication/)
})

test('content:plan-output trata contexto fora do escopo como aviso e mantem o plano', () => {
    const result = run(planCli, ['--project', okProject, '--profile', 'youtube-shorts', '--rule-context', 'api-publishing', '--json'])
    assert.equal(result.status, 0, result.stderr)
    assert.match(result.stderr, /OUTPUT_PLAN_RULE_NOT_APPLIED/)
    assert.match(result.stderr, /@in-app, @studio-upload/)
    assert.match(result.stderr, /@api-publishing/)
})

test('content:plan-output sai 1 com stdout vazio para perfil desconhecido ou bloqueado pelo projeto', () => {
    const unknown = run(planCli, ['--project', okProject, '--profile', 'tiktok-lives', '--json'])
    assert.equal(unknown.status, 1, unknown.stdout)
    assert.equal(unknown.stdout, '')
    assert.match(unknown.stderr, /OUTPUT_PROFILE_UNKNOWN/)

    const blocked = run(planCli, ['--project', horizontalOnlyProject, '--profile', 'youtube-shorts', '--json'])
    assert.equal(blocked.status, 1, blocked.stdout)
    assert.equal(blocked.stdout, '')
    assert.match(blocked.stderr, /OUTPUT_PROFILE_NOT_ALLOWED/)

    const ambiguous = run(planCli, ['--project', okProject, '--profile', 'youtube-shorts', '--network', 'instagram', '--json'])
    assert.equal(ambiguous.status, 1, ambiguous.stdout)
    assert.equal(ambiguous.stdout, '')
    assert.match(ambiguous.stderr, /OUTPUT_PROFILE_AMBIGUOUS_SELECTION/)

    const invalidProject = run(planCli, ['--project', brokenProject, '--profile', 'youtube-shorts', '--json'])
    assert.equal(invalidProject.status, 1, invalidProject.stdout)
    assert.equal(invalidProject.stdout, '')
    assert.match(invalidProject.stderr, /OUTPUT_PROJECT_INVALID/)
})

test('content:plan-output mantem o plano em stdout quando a composicao e compativel', () => {
    const result = run(planCli, [
        '--project', okProject, '--profile', 'youtube-shorts', '--rule-context', 'studio-upload',
        '--composition', shortsComposition([90000, 90000]), '--json',
    ])
    assert.equal(result.status, 0, result.stderr)

    const plan = JSON.parse(result.stdout) as OutputPlan
    assert.equal(plan.profileId, 'youtube-shorts')
    assert.ok(!result.stderr.includes('OUTPUT_COMPAT_'), 'sem erro de compatibilidade no sucesso')
    assert.match(result.stderr, /compatibilidade: composicao "comp-shorts" compativel/)
})

test('a regra de duracao de Shorts alcana in-app e studio-upload pelo comando com --composition', () => {
    for (const context of ['in-app', 'studio-upload'] as const) {
        const inside = run(planCli, [
            '--project', okProject, '--profile', 'youtube-shorts', '--rule-context', context,
            '--composition', shortsComposition([90000, 90000]), '--json',
        ])
        assert.equal(inside.status, 0, `${context}: 180000 ms deveria ser compativel\n${inside.stderr}`)

        const outside = run(planCli, [
            '--project', okProject, '--profile', 'youtube-shorts', '--rule-context', context,
            '--composition', shortsComposition([90000, 90001]), '--json',
        ])
        assert.equal(outside.status, 1, `${context}: 180001 ms deveria estourar a regra`)
        assert.equal(outside.stdout, '')
        assert.match(outside.stderr, /camada compatibilidade/)
        assert.match(outside.stderr, /OUTPUT_COMPAT_DURATION_EXCEEDED/)
        assert.match(outside.stderr, /Declared scene total of 180001 ms exceeds 180 s/)
        assert.match(outside.stderr, /"R-YT-01" @in-app, @studio-upload/)
    }
})

test('a duracao de Reels certificada na R001-05 alcana a camada compatibilidade', () => {
    // 15 minutos sai da pendencia P-IG-01 e vira R-IG-09 com valor: a borda passa a
    // ser verificavel, e no contexto certificado pela pagina (api-publishing).
    const inside = run(planCli, [
        '--project', okProject, '--profile', 'instagram-reels-video', '--rule-context', 'api-publishing',
        '--composition', reelsComposition([450000, 450000]), '--json',
    ])
    assert.equal(inside.status, 0, `900000 ms e o proprio teto de 15 minutos\n${inside.stderr}`)

    const outside = run(planCli, [
        '--project', okProject, '--profile', 'instagram-reels-video', '--rule-context', 'api-publishing',
        '--composition', reelsComposition([450000, 450001]), '--json',
    ])
    assert.equal(outside.status, 1, '900001 ms estoura os 15 minutos certificados')
    assert.equal(outside.stdout, '')
    assert.match(outside.stderr, /OUTPUT_COMPAT_DURATION_EXCEEDED/)
    assert.match(outside.stderr, /Declared scene total of 900001 ms exceeds 900 s/)
    assert.match(outside.stderr, /"R-IG-09" @api-publishing/)
})

test('limite que o preset cumpre nao gera aviso: resolucao minima do Story do Facebook', () => {
    // R-FB-04 (minimo 540x960) e avaliada contra a geometria do plano e atendida; o
    // que continua sem dado no plano (duracao e faixa de frame rate) vira aviso.
    // Sem pendencia de peso de video: P-FB-03 nomeia o numero que a fonte nao da.
    const result = run(planCli, [
        '--project', okProject, '--profile', 'facebook-stories-video', '--rule-context', 'api-publishing', '--json',
    ])
    assert.equal(result.status, 0, result.stderr)
    assert.ok(!result.stderr.includes('R-FB-04'), `limite cumprido nao pode aparecer como pendencia de dado:\n${result.stderr}`)
    assert.match(result.stderr, /R-FB-03/)
    assert.match(result.stderr, /R-FB-05/)
    assert.match(result.stderr, /pendencias de fonte: P-FB-03/)
})

test('content:plan-output rotula as tres camadas quando a composicao e rejeitada', () => {
    const rejected = writeJson(tempDir, 'comp-rejeitada.json', compositionWithScenes([sceneWith({ type: 'audio' })], {
        projectId: 'projeto-teste',
        id: 'comp-rejeitada',
        title: 'Composicao Rejeitada',
        format: { profile: 'youtube-shorts', width: 1080, height: 1920, fps: 30 },
    }))

    const result = run(planCli, ['--project', okProject, '--profile', 'youtube-shorts', '--composition', rejected, '--json'])
    assert.equal(result.status, 1, result.stdout)
    assert.equal(result.stdout, '')

    assert.match(result.stderr, /camada composicao/, 'a composicao tem de trazer o proprio erro')
    assert.match(result.stderr, /COMPOSITION_SCENE_TYPE_INVALID/)
    assert.match(result.stderr, /camada plano/, 'a camada do plano traz o aviso sem duracao')
    assert.match(result.stderr, /camada compatibilidade/)
})

test('content:plan-output falha a operacao de imagem com --composition como incompatibilidade', () => {
    const composition = writeJson(tempDir, 'comp-quadrada.json', compositionWithScenes([sceneWith()], {
        projectId: 'projeto-teste',
        id: 'comp-quadrada',
        title: 'Composicao Quadrada',
        format: { profile: 'instagram-feed-image-square', width: 1080, height: 1080, fps: 30 },
    }))

    const result = run(planCli, ['--project', okProject, '--profile', 'instagram-feed-image-square', '--composition', composition, '--json'])
    assert.equal(result.status, 1, result.stdout)
    assert.equal(result.stdout, '')
    assert.match(result.stderr, /camada compatibilidade/)
    assert.match(result.stderr, /OUTPUT_COMPAT_IMAGE_NO_COMPOSITION/)
    assert.match(result.stderr, /never fabricates fps/)
})

test('content:plan-output na saida humana traz contexto, capacidade do catalogo e pendencias', () => {
    const result = run(planCli, ['--project', okProject, '--profile', 'youtube-shorts', '--rule-context', 'in-app'])
    assert.equal(result.status, 0, result.stderr)

    assert.match(result.stdout, /youtube-shorts/)
    assert.match(result.stdout, /Shorts do YouTube/)
    assert.match(result.stdout, /revisao 3/)
    assert.match(result.stdout, /destino: youtube\/shorts/)
    assert.match(result.stdout, /resolucao: 1080x1920 \(9:16\)/)
    assert.match(result.stdout, /fps: 30/)
    assert.match(result.stdout, /contexto declarado: in-app/)
    assert.match(result.stdout, /capacidade de catalogo: canvas-template-mapped/)
    assert.match(result.stdout, /pendencias de fonte: P-YT-03/)
    assert.match(result.stdout, /requer inspecao: media-file, codec, bytes, audio-streams, publication/)
    assert.match(result.stdout, /"schemaVersion": 1/, 'o plano canonico precisa aparecer na saida humana')
})

test('content:plan-output aceita caminho de fixture com espaco para projeto e composicao', () => {
    const spacedComposition = writeJson(spacedDir, 'comp com espaco.json', compositionWithScenes([sceneWith({ durationMs: 90000 })], {
        projectId: 'projeto-teste',
        id: 'comp-espaco',
        title: 'Composicao Espaco',
        format: { profile: 'youtube-shorts', width: 1080, height: 1920, fps: 30 },
    }))

    const result = run(planCli, ['--project', spacedProject, '--profile', 'youtube-shorts', '--rule-context', 'studio-upload', '--composition', spacedComposition, '--json'])
    assert.equal(result.status, 0, result.stderr)
    assert.equal((JSON.parse(result.stdout) as OutputPlan).profileId, 'youtube-shorts')
    assert.ok(!result.stdout.includes(spacedDir) && !result.stderr.includes(spacedDir), 'nenhum caminho absoluto da maquina na saida')
})

test('as duas CLIs nao muta os arquivos lidos', () => {
    const projectPath = writeJson(tempDir, 'projeto-imutavel.json', catalogProject())
    const compositionPath = shortsComposition([90000])
    const beforeProject = readFileSync(projectPath, 'utf8')
    const beforeComposition = readFileSync(compositionPath, 'utf8')

    const result = run(planCli, ['--project', projectPath, '--profile', 'youtube-shorts', '--composition', compositionPath, '--json'])
    assert.equal(result.status, 0, result.stderr)
    assert.equal(run(profilesCli, ['--project', projectPath, '--json']).status, 0)

    assert.equal(readFileSync(projectPath, 'utf8'), beforeProject)
    assert.equal(readFileSync(compositionPath, 'utf8'), beforeComposition)
})

test('conteudo do catalogo e filtrado pela mesma tabela lida, sem dicionario proprio', () => {
    const listing = JSON.parse(run(profilesCli, ['--json']).stdout) as Listing
    const byId = new Map(listing.profiles.map((profile) => [profile.id, profile]))

    for (const profile of OUTPUT_PROFILES) {
        const entry = byId.get(profile.id)
        assert.ok(entry, `${profile.id} sumiu da listagem`)
        assert.equal(entry.name, profile.name)
        assert.equal(entry.revision, profile.revision)
        assert.equal(entry.network, profile.network)
        assert.equal(entry.publication, profile.publication)
        assert.equal(entry.mediaKind, profile.mediaKind)
        assert.equal(entry.width, profile.geometry.width)
        assert.equal(entry.height, profile.geometry.height)
        assert.equal(entry.aspectRatio, profile.geometry.aspectRatio)
        assert.equal(entry.fps, profile.mediaKind === 'video' ? profile.fps : null)
        assert.equal(entry.exportState, profile.exportState)
        assert.deepEqual(entry.exportEvidence, [...profile.exportEvidence])
        assert.deepEqual(entry.pendingRuleIds, [...profile.pendingIds])
    }
})

test('regressao: os comandos legados seguem aceitando as fixtures oficiais', () => {
    for (const pair of officialPairs) {
        const projectPath = path.join(moduleRoot, 'examples', 'projects', pair.project)
        const compositionPath = path.join(moduleRoot, 'examples', 'compositions', pair.composition)

        const projectRun = run(projectCli, ['--project', projectPath, '--json'])
        assert.equal(projectRun.status, 0, `${pair.project}: ${projectRun.stderr}`)

        const compositionRun = run(compositionCli, ['--project', projectPath, '--composition', compositionPath, '--json'])
        assert.equal(compositionRun.status, 0, `${pair.composition}: ${compositionRun.stderr}`)

        // As CLIs novas nao mudam os exemplos oficiais: o allowlist deles
        // continua sem nenhum perfil do catalogo social.
        const allowed = readProjectExample(pair.project).outputProfiles as string[]
        const catalogIds = new Set(OUTPUT_PROFILES.map((profile) => profile.id))
        assert.deepEqual(allowed.filter((id) => catalogIds.has(id)), [])
    }
})
