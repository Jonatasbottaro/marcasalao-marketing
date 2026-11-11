/**
 * Testes de processo da CLI do BeatPlan (`content:validate-beat-plan`).
 *
 * A superficie conferida aqui e a de processo: os tres exit codes (0 valido,
 * 1 documento invalido, 2 uso/arquivo/JSON), o contrato de saida (stdout somente
 * o relatorio; stderr somente a operacao), a paridade com o validador em memoria
 * e — exigencia da reconciliacao — o uso do helper compartilhado `cli-input.ts`,
 * sem parser, exit code ou leitura de arquivo reimplementados.
 *
 * Os documentos sao temporarios e sinteticos: nenhum teste depende dos exemplos
 * oficiais, que tem verificacao propria no bloco final de
 * `beat-plan-validation.test.ts`.
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { after, test } from 'node:test'

import type { Beat } from '../src/beat-plan-contract.js'
import type { BeatPlanValidationReport } from '../src/validation-report.js'
import { validateBeatPlan } from '../src/validate-beat-plan.js'
import { compositionWith, moduleRoot, projectWith } from './contract-harness.js'

const cliPath = path.join(moduleRoot, 'dist', 'src', 'validate-beat-plan-cli.js')
const cliSourcePath = path.join(moduleRoot, 'src', 'validate-beat-plan-cli.ts')
const tempDir = mkdtempSync(path.join(os.tmpdir(), 'beat-plan-cli-'))

const baseProject = projectWith({})
const baseComposition = compositionWith({})
const baseBeat: Beat = {
    id: 'abertura',
    order: 1,
    sceneIds: ['opening'],
    narrativeFunction: 'hook',
    startMs: 0,
    durationMs: 3000,
    narration: { text: 'Narracao tecnica de teste.' },
    onScreenText: 'Texto de teste.',
    visualIntent: 'Intencao visual tecnica de teste.',
    motionIntent: 'none',
    transitionIn: 'none',
    transitionOut: 'cut',
    editorialEvidence: ['technical-example'],
    validationStatus: 'draft',
}

/** BeatPlan valido contra a composicao de uma cena (0 a 3000 ms) do harness. */
function beatPlanWith(beats: readonly Beat[] = [baseBeat], overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        schemaVersion: 1,
        projectId: 'projeto-teste',
        compositionId: 'comp-contrato',
        id: 'plano-processo',
        locale: 'pt-BR',
        beats: beats.map((beat) => ({ ...beat })),
        ...overrides,
    }
}

interface CliResult {
    status: number | null
    stdout: string
    stderr: string
}

function run(args: string[]): CliResult {
    const result = spawnSync(process.execPath, [cliPath, ...args], { encoding: 'utf8' })
    return { status: result.status, stdout: result.stdout ?? '', stderr: result.stderr ?? '' }
}

let stageCount = 0

/** Escreve o JSON em arquivo novo: cada execucao ve exatamente o documento do teste. */
function stage(label: string, document: unknown): string {
    const filePath = path.join(tempDir, `${label}-${stageCount++}.json`)
    writeFileSync(filePath, `${JSON.stringify(document, null, 2)}\n`, 'utf8')
    return filePath
}

function triple(project: unknown, composition: unknown, beatPlan: unknown, label: string): string[] {
    return [
        '--project',
        stage(`${label}-projeto`, project),
        '--composition',
        stage(`${label}-composicao`, composition),
        '--beat-plan',
        stage(`${label}-plano`, beatPlan),
    ]
}

after(() => rmSync(tempDir, { recursive: true, force: true }))

test('a CLI do beat plan reutiliza o helper compartilhado sem reimplementar a entrada', () => {
    const source = readFileSync(cliSourcePath, 'utf8')

    assert.match(source, /from '\.\/cli-input\.js'/, 'a CLI precisa importar cli-input.ts')
    for (const symbol of ['EXIT_VALID', 'EXIT_INVALID', 'EXIT_USAGE', 'parseFlags', 'readJsonFile', 'formatIssue']) {
        assert.ok(source.includes(symbol), `a CLI precisa usar ${symbol} do helper compartilhado`)
    }

    // Nada da camada de entrada pode ser duplicado: parser, codigo de saida,
    // leitura de JSON ou formatacao de diagnostico redefinidos no arquivo da CLI.
    for (const forbidden of [
        'function parseArgs',
        'function parseFlags',
        'function readJsonFile',
        'function formatIssue',
        'const EXIT_VALID',
        'const EXIT_INVALID',
        'const EXIT_USAGE',
        'readFileSync',
        'process.exit(',
        '#!',
    ]) {
        assert.ok(!source.includes(forbidden), `a CLI nao pode reimplementar "${forbidden}"`)
    }
})

test('exit 0: o JSON do stdout e exatamente o relatorio do validador em memoria', () => {
    const beatPlan = beatPlanWith()
    const result = run([...triple(baseProject, baseComposition, beatPlan, 'valido'), '--json'])
    assert.equal(result.status, 0, result.stderr)
    assert.equal(result.stderr, '', 'sucesso nao escreve nada em stderr')

    const report = JSON.parse(result.stdout) as BeatPlanValidationReport
    assert.deepEqual(report, validateBeatPlan(beatPlan, baseComposition, baseProject))
    assert.equal(report.valid, true, JSON.stringify(report.errors))
    assert.equal(report.summary, 'Beat plan is valid.')
    assert.equal(report.beatPlanId, 'plano-processo')
    assert.deepEqual(report.warnings, [], 'beat plan completo nao emite aviso')

    // Saida canonica: indentacao de dois espacos e uma unica newline final.
    assert.equal(result.stdout, `${JSON.stringify(report, null, 2)}\n`)
    assert.ok(!result.stdout.includes('\r'), 'stdout nao pode conter CR')
})

test('exit 0 sem --json: o stdout traz somente o relatorio em texto', () => {
    const result = run(triple(baseProject, baseComposition, beatPlanWith(), 'texto'))
    assert.equal(result.status, 0, result.stderr)
    assert.equal(result.stdout.split('\n')[0], 'Beat plan is valid.')
    assert.ok(!result.stdout.includes('{'), 'modo texto nao imprime JSON')
    assert.equal(result.stderr, '')
})

test('exit 1: plano, projeto e composicao invalidos devolvem o mesmo relatorio do validador', () => {
    const sceneNotFoundPlan = beatPlanWith([{ ...baseBeat, sceneIds: ['cena-que-nao-existe'] }])
    const cases: Array<{ name: string; document: unknown; code: string }> = [
        { name: 'schemaVersion desconhecido', document: beatPlanWith([baseBeat], { schemaVersion: 9 }), code: 'BEAT_PLAN_SCHEMA_VERSION_UNSUPPORTED' },
        { name: 'plano sem beats', document: beatPlanWith([]), code: 'BEAT_PLAN_BEATS_REQUIRED' },
        { name: 'cena inexistente', document: sceneNotFoundPlan, code: 'BEAT_PLAN_SCENE_NOT_FOUND' },
        { name: 'timeline fora da composicao', document: beatPlanWith([{ ...baseBeat, durationMs: 2000 }]), code: 'BEAT_PLAN_TIMELINE_END_MISMATCH' },
    ]

    for (const caseItem of cases) {
        const result = run([...triple(baseProject, baseComposition, caseItem.document, caseItem.name), '--json'])
        assert.equal(result.status, 1, `${caseItem.name}: stdout=${result.stdout} stderr=${result.stderr}`)
        const report = JSON.parse(result.stdout) as BeatPlanValidationReport
        assert.equal(report.valid, false, caseItem.name)
        assert.deepEqual(
            report,
            validateBeatPlan(caseItem.document, baseComposition, baseProject),
            `CLI divergiu do validador em "${caseItem.name}"`,
        )
        assert.ok(report.errors.some((error) => error.code === caseItem.code), `${caseItem.name}: faltou ${caseItem.code}`)
    }

    // Beat plan valido com documento de outra camada invalido: continua exit 1.
    const invalidProject = projectWith({ id: 'Projeto_Invalido' })
    const projectRun = run([...triple(invalidProject, baseComposition, beatPlanWith(), 'projeto-invalido'), '--json'])
    assert.equal(projectRun.status, 1, projectRun.stdout)
    assert.deepEqual(
        JSON.parse(projectRun.stdout) as BeatPlanValidationReport,
        validateBeatPlan(beatPlanWith(), baseComposition, invalidProject),
    )
    assert.ok(projectRun.stdout.includes('BEAT_PLAN_PROJECT_MANIFEST_INVALID'))

    const invalidComposition = compositionWith({ scenes: 'nenhuma' })
    const compositionRun = run([...triple(baseProject, invalidComposition, beatPlanWith(), 'composicao-invalida'), '--json'])
    assert.equal(compositionRun.status, 1, compositionRun.stdout)
    assert.ok(compositionRun.stdout.includes('BEAT_PLAN_COMPOSITION_INVALID'))
    assert.deepEqual(
        JSON.parse(compositionRun.stdout) as BeatPlanValidationReport,
        validateBeatPlan(beatPlanWith(), invalidComposition, baseProject),
    )

    // Sem --json o texto tambem carrega os codigos: o stdout continua sendo o relatorio.
    const humanRun = run(triple(baseProject, baseComposition, beatPlanWith([baseBeat], { schemaVersion: 9 }), 'texto-invalido'))
    assert.equal(humanRun.status, 1)
    assert.match(humanRun.stdout, /BEAT_PLAN_SCHEMA_VERSION_UNSUPPORTED/)
    assert.equal(humanRun.stderr, '', 'diagnostico de dominio nao migra para stderr')
})

test('exit 1: null lido do disco e documento invalido, nao erro de leitura', () => {
    const result = run([
        '--project', stage('nulo-projeto', baseProject),
        '--composition', stage('nulo-composicao', baseComposition),
        '--beat-plan', path.join(tempDir, 'inexistente-para-error.json'),
        '--json',
    ])
    assert.equal(result.status, 2, `${result.stdout}${result.stderr}`)

    const nullPlanPath = path.join(tempDir, 'nulo.json')
    writeFileSync(nullPlanPath, 'null\n', 'utf8')
    const nullRun = run([
        '--project', stage('nulo-projeto-2', baseProject),
        '--composition', stage('nulo-composicao-2', baseComposition),
        '--beat-plan', nullPlanPath,
        '--json',
    ])
    assert.equal(nullRun.status, 1, `${nullRun.stdout}${nullRun.stderr}`)
    const report = JSON.parse(nullRun.stdout) as BeatPlanValidationReport
    assert.deepEqual(report.errors.map((error) => error.code), ['BEAT_PLAN_MANIFEST_INVALID'])
})

test('exit 2: todo erro de uso devolve stdout vazio e diagnostico em stderr', () => {
    const goodProject = stage('uso-projeto', baseProject)
    const goodComposition = stage('uso-composicao', baseComposition)
    const goodPlan = stage('uso-plano', beatPlanWith())

    const malformed = path.join(tempDir, 'malformado.json')
    writeFileSync(malformed, '{ nao e json', 'utf8')
    const missing = path.join(tempDir, 'nao-existe.json')

    const usageCases: Array<{ name: string; args: string[] }> = [
        { name: 'nenhum argumento', args: [] },
        { name: 'faltando --beat-plan', args: ['--project', goodProject, '--composition', goodComposition] },
        { name: 'faltando --composition', args: ['--project', goodProject, '--beat-plan', goodPlan] },
        { name: 'faltando --project', args: ['--composition', goodComposition, '--beat-plan', goodPlan] },
        { name: 'flag sem valor', args: ['--project'] },
        { name: 'valor ausente antes de outra flag', args: ['--project', '--composition', goodComposition, '--beat-plan', goodPlan] },
        { name: 'flag desconhecida', args: ['--projeto', goodProject, '--composition', goodComposition, '--beat-plan', goodPlan] },
        { name: 'flag repetida', args: ['--project', goodProject, '--project', goodProject, '--composition', goodComposition, '--beat-plan', goodPlan] },
        { name: '--json repetido', args: ['--project', goodProject, '--composition', goodComposition, '--beat-plan', goodPlan, '--json', '--json'] },
        { name: 'argumento sem flag', args: [goodProject, '--composition', goodComposition, '--beat-plan', goodPlan] },
        { name: 'projeto inexistente', args: ['--project', missing, '--composition', goodComposition, '--beat-plan', goodPlan] },
        { name: 'composicao inexistente', args: ['--project', goodProject, '--composition', missing, '--beat-plan', goodPlan] },
        { name: 'plano inexistente', args: ['--project', goodProject, '--composition', goodComposition, '--beat-plan', missing] },
        { name: 'projeto malformado', args: ['--project', malformed, '--composition', goodComposition, '--beat-plan', goodPlan] },
        { name: 'composicao malformada', args: ['--project', goodProject, '--composition', malformed, '--beat-plan', goodPlan] },
        { name: 'plano malformado', args: ['--project', goodProject, '--composition', goodComposition, '--beat-plan', malformed] },
    ]

    for (const caseItem of usageCases) {
        const result = run(caseItem.args)
        assert.equal(result.status, 2, `${caseItem.name}: stdout=${result.stdout} stderr=${result.stderr}`)
        assert.equal(result.stdout, '', `${caseItem.name}: erro de uso nao pode imprimir relatorio`)
        assert.ok(result.stderr.length > 0, `${caseItem.name}: erro de uso precisa de diagnostico em stderr`)
        assert.ok(!result.stderr.includes(' at '), `${caseItem.name}: stderr com stack trace`)
        assert.ok(!result.stderr.includes('Error:'), `${caseItem.name}: stderr com classe de erro crua`)
    }

    for (const result of [run([]), run(['--project'])]) {
        assert.equal(result.status, 2)
        assert.match(result.stderr, /^Erro de uso: /)
        assert.match(result.stderr, /Uso: node dist\/src\/validate-beat-plan-cli\.js/)
    }

    const readErrors = [
        run(['--project', malformed, '--composition', goodComposition, '--beat-plan', goodPlan]),
        run(['--project', goodProject, '--composition', goodComposition, '--beat-plan', missing]),
    ]
    for (const result of readErrors) {
        assert.match(result.stderr, /^Erro: /)
    }
})

test('a saida e deterministica entre execucoes e nao expoe caminhos da maquina', () => {
    const args = [...triple(baseProject, baseComposition, beatPlanWith([baseBeat], { schemaVersion: 9 }), 'det'), '--json']

    const first = run(args)
    const second = run(args)
    assert.equal(first.status, 1)
    assert.equal(first.stdout, second.stdout, 'duas execucoes produziram JSON diferente')
    assert.equal(first.stderr, second.stderr)

    for (const output of [first.stdout, first.stderr]) {
        assert.ok(!output.includes(tempDir), 'a saida contem o caminho absoluto do arquivo temporario')
        assert.ok(!output.includes(moduleRoot), 'a saida contem o caminho absoluto do modulo')
        assert.ok(!/\d{4}-\d{2}-\d{2}T[\d:.]+Z/.test(output), 'a saida contem um timestamp ISO')
    }

    const report = JSON.parse(first.stdout) as BeatPlanValidationReport
    assert.deepEqual(Object.keys(report).sort(), [
        'beatCount',
        'beatPlanId',
        'compositionDurationMs',
        'compositionId',
        'compositionSceneCount',
        'errors',
        'metadataStatus',
        'narrationBeatCount',
        'onScreenTextBeatCount',
        'projectId',
        'referencedSceneCount',
        'schemaVersion',
        'summary',
        'totalDurationMs',
        'valid',
        'warnings',
    ])
    for (const item of [...report.errors, ...report.warnings]) {
        assert.deepEqual(Object.keys(item).sort(), ['code', 'message', 'path'])
        assert.ok(!item.path.includes(path.sep), `caminho logico com separador de sistema: ${item.path}`)
        assert.ok(!/^[A-Za-z]:[\\/]/.test(item.path), `caminho absoluto no path: ${item.path}`)
        assert.ok(!item.message.includes('\\'), `message com separador de sistema: ${item.message}`)
    }
})

test('a CLI le somente os tres arquivos informados e nao cria outputs nem os muta', () => {
    const caseDir = mkdtempSync(path.join(os.tmpdir(), 'beat-plan-cli-outputs-'))
    try {
        const projectPath = path.join(caseDir, 'p.project.json')
        const compositionPath = path.join(caseDir, 'c.composition.json')
        const planPath = path.join(caseDir, 'b.beat-plan.json')
        writeFileSync(projectPath, `${JSON.stringify(baseProject, null, 2)}\n`, 'utf8')
        writeFileSync(compositionPath, `${JSON.stringify(baseComposition, null, 2)}\n`, 'utf8')
        writeFileSync(planPath, `${JSON.stringify(beatPlanWith(), null, 2)}\n`, 'utf8')
        const before = [projectPath, compositionPath, planPath].map((file) => readFileSync(file, 'utf8'))

        const result = run(['--project', projectPath, '--composition', compositionPath, '--beat-plan', planPath, '--json'])
        assert.equal(result.status, 0, result.stderr)
        assert.deepEqual(
            readdirSync(caseDir).sort(),
            ['b.beat-plan.json', 'c.composition.json', 'p.project.json'],
            'a CLI nao pode criar arquivos alem dos tres informados',
        )
        assert.deepEqual(
            [projectPath, compositionPath, planPath].map((file) => readFileSync(file, 'utf8')),
            before,
            'a CLI nao pode mutar os arquivos validados',
        )
    } finally {
        rmSync(caseDir, { recursive: true, force: true })
    }
})
