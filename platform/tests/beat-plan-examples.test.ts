/**
 * Exemplos versionados de BeatPlan: o que esta em `examples/beat-plans/` precisa
 * executar nas tres camadas, contra os pares de Composition e ProjectManifest que
 * ja existem no repositorio.
 *
 * As camadas separam-se de proposito: o **schema** confere a forma, o **core**
 * confere as regras entre documentos (ids, locale, existencia de cena, timeline)
 * e a **CLI** confere o processo e o stdout byte a byte. Os exemplos nunca sao a
 * prova de uma camada delegada para outra.
 *
 * Line endings tambem sao contrato: o gate roda em windows-latest e em Ubuntu, e
 * os dois precisam ler os mesmos bytes. Da a regra `eol=lf` no `.gitattributes` e
 * a leitura em binario aqui, que nao aceita um CR nem newline final duplicada.
 */
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import AjvModule, { type AnySchemaObject } from 'ajv'

import { BEAT_PLAN_SCHEMA_VERSION } from '../src/beat-plan-contract.js'
import { validateBeatPlan } from '../src/validate-beat-plan.js'
import { validateComposition } from '../src/validate-composition.js'
import { validateProjectManifest } from '../src/validate-project.js'
import type { BeatPlanValidationReport } from '../src/validation-report.js'
import { moduleRoot, readCompositionExample, readProjectExample } from './contract-harness.js'

const beatPlansDir = path.join(moduleRoot, 'examples', 'beat-plans')
const beatPlanCli = path.join(moduleRoot, 'dist', 'src', 'validate-beat-plan-cli.js')
const schemaPath = path.join(moduleRoot, 'schemas', 'beat-plan.schema.json')

/** Um exemplo versionado e os dois fixtures que ele precisa referenciar. */
const VERSIONED_BEAT_PLANS: readonly {
    file: string
    composition: string
    project: string
    locale: string
    beatPlanId: string
}[] = [
    {
        file: 'marca-salao-pilot.beat-plan.json',
        composition: 'marca-salao-pilot.composition.json',
        project: 'marca-salao.project.json',
        locale: 'pt-BR',
        beatPlanId: 'pilot-beat-plan',
    },
    {
        file: 'fixture-project-pilot.beat-plan.json',
        composition: 'fixture-project-pilot.composition.json',
        project: 'fixture-project.project.json',
        locale: 'en-US',
        beatPlanId: 'pilot-beat-plan',
    },
]

// O espelho draft-07 e compilado aqui, como no teste de schema: contract-harness.ts
// traz apenas os schemas que a main ja tinha e nao exporta o motor.
// strict desligado porque o espelho usa so o vocabulario draft-07; o pacote e
// CommonJS, entao o construtor chega pela propriedade `default` do modulo.
const ajv = new AjvModule.default({ allErrors: true, strict: false })

/** Bytes do exemplo como estao no repositorio, sem normalizacao de linha. */
function readExampleBytes(file: string): Buffer {
    return readFileSync(path.join(beatPlansDir, file))
}

function readExampleText(file: string): string {
    return readExampleBytes(file).toString('utf8')
}

function readBeatPlanExample(file: string): Record<string, unknown> {
    return JSON.parse(readExampleText(file)) as Record<string, unknown>
}

function issueLines(report: BeatPlanValidationReport): string {
    return [...report.errors, ...report.warnings]
        .map((item) => `${item.code} @${item.path}: ${item.message}`)
        .join(' | ')
}

/** Executa a CLI com caminhos relativos ao modulo: nada aqui depende da maquina. */
function runBeatPlanCli(caseItem: (typeof VERSIONED_BEAT_PLANS)[number]): {
    status: number | null
    stdout: string
    stderr: string
} {
    const args = [
        beatPlanCli,
        '--project', path.join('examples', 'projects', caseItem.project),
        '--composition', path.join('examples', 'compositions', caseItem.composition),
        '--beat-plan', path.join('examples', 'beat-plans', caseItem.file),
        '--json',
    ]
    const result = spawnSync(process.execPath, args, { cwd: moduleRoot, encoding: 'utf8' })
    return { status: result.status, stdout: result.stdout ?? '', stderr: result.stderr ?? '' }
}

test('a pasta de exemplos contem exatamente os dois beat plans versionados', () => {
    assert.deepEqual(readdirSync(beatPlansDir).sort(), VERSIONED_BEAT_PLANS.map((caseItem) => caseItem.file).sort())
})

test('as referencias dos exemplos apontam para fixtures que existem e validam', () => {
    for (const caseItem of VERSIONED_BEAT_PLANS) {
        const compositionPath = path.join(moduleRoot, 'examples', 'compositions', caseItem.composition)
        const projectPath = path.join(moduleRoot, 'examples', 'projects', caseItem.project)
        assert.ok(existsSync(compositionPath), `fixture de composicao ausente: ${caseItem.composition}`)
        assert.ok(existsSync(projectPath), `fixture de projeto ausente: ${caseItem.project}`)

        // A prova das camadas delegadas vem antes: se o fixture do par nao vale,
        // o exemplo jamais alcancaria a checagem do beat plan.
        const project = readProjectExample(caseItem.project)
        const composition = readCompositionExample(caseItem.composition)
        const projectReport = validateProjectManifest(project)
        assert.deepEqual(projectReport.errors, [], `${caseItem.project}: ${projectReport.errors[0]?.message ?? ''}`)
        const compositionReport = validateComposition(composition, project)
        assert.deepEqual(compositionReport.errors, [], `${caseItem.composition}: ${compositionReport.errors[0]?.message ?? ''}`)

        const beatPlan = readBeatPlanExample(caseItem.file)
        assert.equal(beatPlan.schemaVersion, BEAT_PLAN_SCHEMA_VERSION, `${caseItem.file}: unica versao de schema suportada`)
        assert.equal(beatPlan.projectId, project.id, `${caseItem.file}: projectId nao ecoa o manifesto do par`)
        assert.equal(beatPlan.compositionId, composition.id, `${caseItem.file}: compositionId nao ecoa a composicao do par`)
        assert.equal(beatPlan.locale, caseItem.locale, `${caseItem.file}: locale explicito do caso`)
        assert.equal(beatPlan.locale, project.locale, `${caseItem.file}: locale divergente do manifesto`)
        assert.equal(beatPlan.locale, composition.locale, `${caseItem.file}: locale divergente da composicao`)

        // Todo sceneId dos exemplos precisa existir na composicao do par; o core
        // da mesma garantia, mas aqui a referencia e conferida no disco.
        const sceneIds = new Set((composition.scenes as { id: string }[]).map((scene) => scene.id))
        for (const beat of beatPlan.beats as Record<string, unknown>[]) {
            for (const sceneId of beat.sceneIds as string[]) {
                assert.ok(sceneIds.has(sceneId), `${caseItem.file}: sceneId "${sceneId}" nao existe em ${caseItem.composition}`)
            }
        }
    }
})

test('cada exemplo passa no espelho draft-07 do schema', () => {
    const schema = JSON.parse(readFileSync(schemaPath, 'utf8')) as AnySchemaObject
    for (const caseItem of VERSIONED_BEAT_PLANS) {
        const validate = ajv.compile(schema)
        const valid = validate(readBeatPlanExample(caseItem.file)) === true
        const failures = (validate.errors ?? []).map(
            (error) => `${error.instancePath || '#'} ${error.keyword}: ${error.message ?? ''}`.trim(),
        )
        assert.ok(valid, `${caseItem.file} rejeitado pelo motor: ${failures.join(' | ')}`)
    }
})

test('cada exemplo valida no core com zero erros e zero avisos', () => {
    for (const caseItem of VERSIONED_BEAT_PLANS) {
        const beatPlan = readBeatPlanExample(caseItem.file)
        const composition = readCompositionExample(caseItem.composition)
        const project = readProjectExample(caseItem.project)

        const report = validateBeatPlan(beatPlan, composition, project)
        assert.equal(report.valid, true, `${caseItem.file}: ${issueLines(report)}`)
        assert.deepEqual(report.errors, [], `${caseItem.file}: ${issueLines(report)}`)
        assert.deepEqual(report.warnings, [], `${caseItem.file}: exemplo versionado nao pode depender de aviso: ${issueLines(report)}`)
        assert.equal(report.summary, 'Beat plan is valid.')
        assert.equal(report.beatPlanId, caseItem.beatPlanId)
        assert.equal(report.projectId, project.id)
        assert.equal(report.compositionId, composition.id)
        assert.equal(report.schemaVersion, BEAT_PLAN_SCHEMA_VERSION)

        // Contadores estruturais: a timeline termina exatamente na duracao da
        // composicao e todo cena do par e referenciada por algum beat.
        const compositionReport = validateComposition(composition, project)
        assert.equal(report.totalDurationMs, compositionReport.totalDurationMs, `${caseItem.file}: fim da timeline`)
        assert.equal(report.compositionDurationMs, compositionReport.totalDurationMs)
        assert.equal(report.beatCount, (beatPlan.beats as unknown[]).length)
        assert.equal(report.referencedSceneCount, compositionReport.sceneCount, `${caseItem.file}: cena sobrando`)

        const beats = beatPlan.beats as Record<string, unknown>[]
        assert.equal(report.narrationBeatCount, beats.filter((beat) => beat.narration !== undefined).length)
        assert.equal(report.onScreenTextBeatCount, beats.filter((beat) => beat.onScreenText !== undefined).length)
    }
})

test('a CLI com cada exemplo sai 0 e o stdout e exatamente o relatorio do core', () => {
    for (const caseItem of VERSIONED_BEAT_PLANS) {
        const result = runBeatPlanCli(caseItem)
        assert.equal(result.status, 0, `${caseItem.file}: ${result.stderr}`)
        assert.equal(result.stderr, '', `${caseItem.file}: sucesso nao escreve em stderr`)

        const report = JSON.parse(result.stdout) as BeatPlanValidationReport
        assert.deepEqual(
            report,
            validateBeatPlan(readBeatPlanExample(caseItem.file), readCompositionExample(caseItem.composition), readProjectExample(caseItem.project)),
            `${caseItem.file}: a CLI divergiu do validador em memoria`,
        )

        // Saida canonica do pacote: dois espacos e uma unica newline final, sem CR.
        assert.equal(result.stdout, `${JSON.stringify(report, null, 2)}\n`, `${caseItem.file}: formato canonico do stdout`)
        assert.ok(!result.stdout.includes('\r'), `${caseItem.file}: stdout com CR`)
        assert.equal(report.valid, true)
    }
})

test('os exemplos gravados usam somente LF e uma unica newline final', () => {
    for (const caseItem of VERSIONED_BEAT_PLANS) {
        const bytes = readExampleBytes(caseItem.file)
        assert.equal(bytes.includes(0x0d), false, `${caseItem.file} contem CR; exemplos BeatPlan usam exclusivamente LF`)
        assert.equal(bytes[bytes.length - 1], 0x0a, `${caseItem.file} precisa terminar com newline`)
        assert.notEqual(bytes[bytes.length - 2], 0x0a, `${caseItem.file} precisa de exatamente uma newline final`)
    }
})

test('o .gitattributes fixa LF nos exemplos BeatPlan sem tocar na regra dos OutputPlans', () => {
    const attributes = readFileSync(path.join(moduleRoot, '.gitattributes'), 'utf8').split(/\r?\n/)

    assert.ok(
        attributes.includes('examples/beat-plans/*.json text eol=lf'),
        'a regra explicita dos exemplos BeatPlan precisa existir',
    )
    // A regra da R001 e a unica fonte de LF dos planos de saida: copi-la para um
    // padrao mais amplo mudaria o checkout de arquivos de outra fatia.
    assert.ok(attributes.includes('examples/output-plans/*.json text eol=lf'), 'a regra dos OutputPlans precisa continuar intacta')
    assert.ok(attributes.includes('*.sh text eol=lf'), 'a regra dos scripts do gate precisa continuar intacta')

    // "text" sem eol=lf deixaria o checkout sujeito ao core.eol do runner Windows,
    // e uma regra mais ampla conversaria os exemplos de outra fatia: toda regra
    // deste arquivo precisa fixar LF na propria linha.
    for (const line of attributes.filter((item) => item.trim() !== '' && !item.startsWith('#'))) {
        assert.ok(!line.includes('text') || line.includes('eol=lf'), `regra sem eol=lf: ${line}`)
    }
})

test('nem os exemplos nem a saida da CLI expoe caminho, separador ou timestamp de maquina', () => {
    for (const caseItem of VERSIONED_BEAT_PLANS) {
        const example = readExampleText(caseItem.file)
        const result = runBeatPlanCli(caseItem)

        for (const output of [example, result.stdout, result.stderr]) {
            assert.ok(!output.includes('\\'), 'saida com separador de caminho do Windows')
            assert.ok(!/[A-Za-z]:[\\/]/.test(output), 'saida com caminho absoluto de unidade')
            assert.ok(!output.includes(moduleRoot), 'saida com o caminho absoluto do modulo')
            assert.ok(!output.includes('C:/') && !output.includes('C:\\'), 'saida com caminho da maquina')
            assert.ok(!/\d{4}-\d{2}-\d{2}T[\d:.]+Z/.test(output), 'saida com timestamp ISO')
        }

        assert.equal(result.status, 0)
    }
})
