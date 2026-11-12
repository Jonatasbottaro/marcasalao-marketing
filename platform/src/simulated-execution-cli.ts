/**
 * CLI interna do executor local simulado (`content:simulate-execution`).
 *
 * Uso:
 *   node dist/src/simulated-execution-cli.js --package <arquivo> --output-dir <dir> [--root <raiz>] [--json]
 *   node dist/src/simulated-execution-cli.js --packages-dir <dir> --output-dir <dir> [--root <raiz>] [--json]
 *
 * Flags de teste controlado (somente do executor simulado):
 *   --fail-step <stepId>        falha controlada na etapa indicada;
 *   --cancel-after <sequence>   cancelamento deterministico apos N eventos;
 *   --resume-from <report.json> retomada a partir de relatorio anterior
 *                               (somente com --package).
 *
 * Exit codes:
 *   0 — todas as execucoes concluidas;
 *   1 — uma ou mais execucoes nao concluidas (falha de step ou cancelamento);
 *   2 — uso, path, arquivo ou JSON invalido;
 *   3 — pacote ou plano invalido;
 *   4 — falha de escrita, promocao ou hash;
 *   5 — retomada incompativel.
 *
 * stdout contem somente o relatorio; stderr somente erro sanitizado.
 * Zero stack trace, zero caminho absoluto da maquina. O executor nao produz
 * midia: apenas plano, eventos, relatorio, artefatos textuais e hashes.
 */

import { readdirSync } from 'node:fs'
import path from 'node:path'

import { EXIT_INVALID, EXIT_USAGE, EXIT_VALID, parseFlags, readJsonFile } from './cli-input.js'
import { createSimulatedExecutionPlan } from './create-simulated-execution-plan.js'
import type { SimulatedExecutionPlan } from './simulated-execution-plan-contract.js'
import {
    aggregateSimulatedExecutions,
    type SimulatedExecutionCaseResult,
    type SimulatedExecutionsReport,
} from './simulated-execution-multicase.js'
import {
    checkSimulatedResume,
    resumeSimulatedExecution,
    runSimulatedExecution,
    validateRunResult,
    type SimulatedExecutionOptions,
    type SimulatedExecutionRunResult,
} from './simulated-execution-runner.js'
import type { SimulatedExecutionReport } from './simulated-execution-report-contract.js'
import {
    confineSimulatedOutputDir,
    removeSimulatedStaging,
    writeSimulatedExecution,
} from './simulated-execution-writer.js'

const EXIT_PLAN = 3
const EXIT_WRITE = 4
const EXIT_RESUME = 5

const VALUE_FLAGS = [
    '--package',
    '--packages-dir',
    '--output-dir',
    '--root',
    '--fail-step',
    '--cancel-after',
    '--resume-from',
] as const

const USAGE = 'Uso: node dist/src/simulated-execution-cli.js --package <arquivo> | --packages-dir <dir> --output-dir <dir> [--root <raiz>] [--fail-step <stepId>] [--cancel-after <sequence>] [--resume-from <report.json>] [--json]'

const PACKAGE_SUFFIX = '.execution-package.json'

function usageError(reason: string): void {
    console.error(`Erro de uso: ${reason}`)
    console.error(USAGE)
}

/** Descoberta deterministica de pacotes; symlinks ignorados. */
function discoverPackages(rootDir: string): { readonly ok: true; readonly paths: readonly string[] } | { readonly ok: false } {
    const found: { readonly relative: string; readonly absolute: string }[] = []
    function walk(directory: string, prefix: string): void {
        const entries = readdirSync(directory, { withFileTypes: true })
            .slice()
            .sort((left, right) => (left.name < right.name ? -1 : left.name > right.name ? 1 : 0))
        for (const entry of entries) {
            if (entry.isSymbolicLink()) continue
            const relative = prefix ? `${prefix}/${entry.name}` : entry.name
            const absolute = path.join(directory, entry.name)
            if (entry.isDirectory()) {
                walk(absolute, relative)
            } else if (entry.isFile() && entry.name.endsWith(PACKAGE_SUFFIX)) {
                found.push({ relative, absolute })
            }
        }
    }
    try {
        walk(path.resolve(rootDir), '')
    } catch {
        return { ok: false }
    }
    found.sort((left, right) => (left.relative < right.relative ? -1 : left.relative > right.relative ? 1 : 0))
    return { ok: true, paths: found.map((item) => item.absolute) }
}

function renderHuman(report: SimulatedExecutionsReport): string {
    const lines: string[] = [report.summary]
    for (const execution of report.executions) {
        const id = execution.executionId !== null ? ` ${execution.executionId}` : ''
        lines.push(`  ${execution.sourceName}: ${execution.status}${id}`)
        if (execution.failureCode !== null) {
            lines.push(`    failureCode: ${execution.failureCode}`)
        }
        if (execution.status !== 'completed') {
            lines.push(`    ${execution.summary}`)
        }
    }
    return lines.join('\n')
}

interface PreparedPackage {
    readonly sourceName: string
    readonly plan: SimulatedExecutionPlan
}

function main(argv: string[]): number {
    const parsed = parseFlags(argv, VALUE_FLAGS)
    if (parsed.error !== null) {
        usageError(parsed.error)
        return EXIT_USAGE
    }

    const packagePath = parsed.values.package
    const packagesDir = parsed.values['packages-dir']
    const outputDirValue = parsed.values['output-dir']
    const resumeFrom = parsed.values['resume-from']

    if ((packagePath === undefined) === (packagesDir === undefined)) {
        usageError('informe exatamente um modo: --package <arquivo> ou --packages-dir <dir>')
        return EXIT_USAGE
    }
    if (outputDirValue === undefined) {
        usageError('a flag --output-dir e obrigatoria')
        return EXIT_USAGE
    }
    if (resumeFrom !== undefined && packagePath === undefined) {
        usageError('--resume-from so pode ser usado junto com --package')
        return EXIT_USAGE
    }

    const options: SimulatedExecutionOptions = {
        ...(parsed.values['fail-step'] !== undefined ? { failAtStepId: parsed.values['fail-step'] } : {}),
        ...(parsed.values['cancel-after'] !== undefined ? { cancelAfterSequence: Number(parsed.values['cancel-after']) } : {}),
    }
    if (options.cancelAfterSequence !== undefined && (!Number.isInteger(options.cancelAfterSequence) || options.cancelAfterSequence < 1)) {
        usageError('--cancel-after deve ser um inteiro maior ou igual a 1')
        return EXIT_USAGE
    }

    const rootDir = parsed.values.root
        ?? (packagePath !== undefined ? path.dirname(path.resolve(packagePath)) : path.resolve(packagesDir as string))

    const confined = confineSimulatedOutputDir(outputDirValue, rootDir)
    if (!confined.ok) {
        console.error('Erro: output-dir invalido ou fora da raiz autorizada')
        return EXIT_USAGE
    }

    // Coleta dos pacotes.
    let packagePaths: readonly string[]
    if (packagePath !== undefined) {
        packagePaths = [path.resolve(packagePath)]
    } else {
        const discovery = discoverPackages(packagesDir as string)
        if (!discovery.ok) {
            console.error('Erro: diretorio de pacotes inexistente ou ilegivel')
            return EXIT_USAGE
        }
        if (discovery.paths.length === 0) {
            console.error('Erro de uso: nenhum pacote *.execution-package.json encontrado sob o diretorio informado')
            console.error(USAGE)
            return EXIT_USAGE
        }
        packagePaths = discovery.paths
    }

    // Leitura de todos os JSON antes de qualquer escrita.
    const values: Array<{ sourceName: string; value: unknown }> = []
    for (const filePath of packagePaths) {
        const file = readJsonFile(filePath)
        if ('error' in file) {
            console.error('Erro: pacote nao encontrado, ilegivel ou com JSON malformado')
            return EXIT_USAGE
        }
        values.push({ sourceName: path.basename(filePath), value: file.value })
    }

    // Compilacao dos planos; qualquer plano invalido encerra antes da escrita.
    const prepared: PreparedPackage[] = []
    const planFailures: SimulatedExecutionCaseResult[] = []
    for (const item of values) {
        const creation = createSimulatedExecutionPlan(item.value)
        if (!creation.ok) {
            planFailures.push({
                sourceName: item.sourceName,
                packageId: null,
                executionId: null,
                status: 'plan-invalid',
                report: null,
                failureCode: creation.failureCode,
                summary: `Execution plan compilation failed: ${creation.failureCode}.`,
            })
            continue
        }
        prepared.push({ sourceName: item.sourceName, plan: creation.plan })
    }
    if (planFailures.length > 0) {
        const report = aggregateSimulatedExecutions(planFailures)
        console.log(parsed.json ? JSON.stringify(report, null, 2) : renderHuman(report))
        return EXIT_PLAN
    }

    // Retomada (somente pacote unico): compatibilidade antes de qualquer escrita.
    let priorReport: SimulatedExecutionReport | null = null
    if (resumeFrom !== undefined) {
        const priorFile = readJsonFile(resumeFrom)
        if ('error' in priorFile) {
            console.error('Erro: relatorio anterior nao encontrado, ilegivel ou com JSON malformado')
            return EXIT_USAGE
        }
        const plan = prepared[0]?.plan as SimulatedExecutionPlan
        const check = checkSimulatedResume(plan, priorFile.value)
        if (!check.ok) {
            console.error(`Erro: retomada incompativel: ${check.code}`)
            return EXIT_RESUME
        }
        priorReport = priorFile.value as SimulatedExecutionReport
    }

    // Execucao em memoria e validacao dos relatorios.
    const runs: Array<{ prepared: PreparedPackage; run: SimulatedExecutionRunResult }> = []
    for (const item of prepared) {
        const run = priorReport !== null
            ? resumeSimulatedExecution(item.plan, priorReport, options)
            : runSimulatedExecution(item.plan, options)
        if (!validateRunResult(run)) {
            console.error('Erro: relatorio de execucao invalido produzido pelo executor')
            return EXIT_PLAN
        }
        runs.push({ prepared: item, run })
    }

    // Escrita transacional: pacote unico no proprio output-dir; multicase em
    // subdiretorio por executionId.
    const results: SimulatedExecutionCaseResult[] = []
    for (const { prepared: item, run } of runs) {
        const destination = packagePath !== undefined
            ? confined.dir
            : path.join(confined.dir, run.report.executionId)
        const write = writeSimulatedExecution(destination, {
            plan: item.plan,
            report: run.report,
            artifacts: run.artifacts,
        })
        if (!write.ok) {
            removeSimulatedStaging(destination)
            console.error(`Erro: falha de escrita, promocao ou hash (${write.stage}); saida anterior preservada`)
            return EXIT_WRITE
        }
        results.push({
            sourceName: item.sourceName,
            packageId: run.report.packageId,
            executionId: run.report.executionId,
            status: run.report.status,
            report: run.report,
            failureCode: run.report.failureCode,
            summary: run.report.summary,
        })
    }

    const report = aggregateSimulatedExecutions(results)
    console.log(parsed.json ? JSON.stringify(report, null, 2) : renderHuman(report))
    return report.valid ? EXIT_VALID : EXIT_INVALID
}

try {
    process.exitCode = main(process.argv.slice(2))
} catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(`Erro inesperado: ${message}`)
    process.exitCode = EXIT_USAGE
}
