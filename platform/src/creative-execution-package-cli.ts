/**
 * CLI interna de geracao de pacotes de execucao (`content:build-execution-packages`).
 *
 * Uso:
 *   node dist/src/creative-execution-package-cli.js --manifest <cases-manifest.json> --output-dir <diretorio> [--root <raiz>] [--json]
 *
 * O manifesto de casos declara `{ schemaVersion: 1, id?, cases: [...] }` com
 * caminhos de manifestos de caso relativos ao diretorio do proprio manifesto.
 * A raiz de confinamento e `--root` quando informado, ou o diretorio do
 * manifesto. O output-dir precisa estar estritamente dentro da raiz (lexical
 * e apos realpath), e so e criado depois de todas as validacoes.
 *
 * Geracao transacional: carregar todos os casos -> validar -> criar pacotes
 * em memoria -> validar pacotes -> serializar -> escrever em staging ->
 * validar bytes escritos -> promover com rename -> preservar a saida
 * anterior em qualquer falha. Nenhum pacote parcial e promovido.
 *
 * Exit codes:
 *   0 — todos os pacotes gerados;
 *   1 — um ou mais casos invalidos;
 *   2 — uso, path, manifesto, arquivo ou JSON invalido;
 *   3 — falha de geracao ou validacao do pacote;
 *   4 — falha de escrita ou promocao.
 *
 * stdout contem somente o relatorio; stderr somente erro sanitizado.
 * Zero stack trace, zero caminho absoluto da maquina em mensagens.
 */

import {
    copyFileSync,
    existsSync,
    mkdirSync,
    readFileSync,
    realpathSync,
    renameSync,
    rmSync,
    statSync,
    writeFileSync,
} from 'node:fs'
import path from 'node:path'

import { EXIT_INVALID, EXIT_USAGE, EXIT_VALID, parseFlags, readJsonFile } from './cli-input.js'
import {
    aggregateCreativeExecutionPackageResults,
    createCreativeExecutionPackageFromCase,
    type CreativeExecutionPackagesReport,
} from './creative-execution-packages.js'
import { serializeCreativeExecutionPackage } from './serialize-creative-execution-package.js'
import { KEBAB_CASE_PATTERN } from './project-contract.js'

const EXIT_GENERATION = 3
const EXIT_WRITE = 4

const VALUE_FLAGS = ['--manifest', '--output-dir', '--root'] as const

const USAGE = 'Uso: node dist/src/creative-execution-package-cli.js --manifest <cases-manifest.json> --output-dir <diretorio> [--root <raiz>] [--json]'

const STAGING_DIR_NAME = '.staging-execution-packages'

function usageError(reason: string): void {
    console.error(`Erro de uso: ${reason}`)
    console.error(USAGE)
}

interface CasesManifest {
    readonly schemaVersion: 1
    readonly id?: string
    readonly cases: readonly string[]
}

function readCasesManifest(manifestPath: string): { readonly value: CasesManifest } | { readonly error: string } {
    const file = readJsonFile(manifestPath)
    if ('error' in file) {
        return { error: 'Erro: manifesto de casos nao encontrado, ilegivel ou com JSON malformado' }
    }
    const value = file.value
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        return { error: 'Erro de uso: manifesto de casos deve ser um objeto JSON' }
    }
    const record = value as Record<string, unknown>
    for (const field of Object.keys(record)) {
        if (field !== 'schemaVersion' && field !== 'id' && field !== 'cases') {
            return { error: `Erro de uso: campo desconhecido no manifesto de casos: ${field}` }
        }
    }
    if (record.schemaVersion !== 1) {
        return { error: 'Erro de uso: schemaVersion do manifesto de casos deve ser 1' }
    }
    if (record.id !== undefined && (typeof record.id !== 'string' || !KEBAB_CASE_PATTERN.test(record.id))) {
        return { error: 'Erro de uso: id do manifesto de casos deve ser kebab-case' }
    }
    if (
        !Array.isArray(record.cases)
        || record.cases.length === 0
        || record.cases.some((item) => typeof item !== 'string' || item.trim().length === 0)
    ) {
        return { error: 'Erro de uso: cases deve ser uma lista nao vazia de caminhos' }
    }
    if (record.cases.some((item) => path.isAbsolute(item as string))) {
        return { error: 'Erro de uso: caminhos de casos devem ser relativos ao diretorio do manifesto' }
    }
    return { value: { schemaVersion: 1, id: record.id as string | undefined, cases: record.cases as string[] } }
}

/** Confinamento do output-dir: lexical + realpath do ancestral existente mais proximo. */
function confineOutputDir(outputDirValue: string, rootDir: string): { readonly ok: true; readonly dir: string } | { readonly ok: false } {
    const root = path.resolve(rootDir)
    const dir = path.resolve(outputDirValue)
    const relative = path.relative(root, dir)
    if (relative === '' || relative.startsWith('..') || path.isAbsolute(relative)) {
        return { ok: false }
    }
    let probe = dir
    while (!existsSync(probe)) {
        const parent = path.dirname(probe)
        if (parent === probe) return { ok: false }
        probe = parent
    }
    try {
        const rootReal = realpathSync(root)
        const probeReal = realpathSync(probe)
        const realRelative = path.relative(rootReal, probeReal)
        if (realRelative.startsWith('..') || path.isAbsolute(realRelative)) {
            return { ok: false }
        }
    } catch {
        return { ok: false }
    }
    if (existsSync(dir) && !statSync(dir).isDirectory()) {
        return { ok: false }
    }
    return { ok: true, dir }
}

/**
 * Escrita transacional: staging interno, verificacao dos bytes escritos,
 * backup dos alvos existentes e promocao com rename. Em qualquer falha,
 * os arquivos promovidos sao revertidos e a saida anterior e preservada.
 */
function writePackagesTransactional(dir: string, files: ReadonlyMap<string, string>): boolean {
    const staging = path.join(dir, STAGING_DIR_NAME)
    const backup = path.join(staging, '.backup')
    try {
        rmSync(staging, { recursive: true, force: true })
        mkdirSync(backup, { recursive: true })

        for (const [name, content] of files) {
            const staged = path.join(staging, name)
            writeFileSync(staged, content, 'utf8')
            if (readFileSync(staged, 'utf8') !== content) {
                throw new Error('staged bytes mismatch')
            }
        }

        const promoted: string[] = []
        try {
            for (const [name] of files) {
                const target = path.join(dir, name)
                if (existsSync(target)) {
                    copyFileSync(target, path.join(backup, name))
                }
            }
            for (const [name] of files) {
                renameSync(path.join(staging, name), path.join(dir, name))
                promoted.push(name)
            }
        } catch {
            for (const name of promoted) {
                const backupFile = path.join(backup, name)
                if (existsSync(backupFile)) {
                    renameSync(backupFile, path.join(dir, name))
                } else {
                    rmSync(path.join(dir, name), { force: true })
                }
            }
            throw new Error('promotion failed')
        }

        rmSync(staging, { recursive: true, force: true })
        return true
    } catch {
        try {
            rmSync(staging, { recursive: true, force: true })
        } catch {
            // limpeza best-effort do staging; a saida anterior ja foi preservada
        }
        return false
    }
}

function renderHuman(report: CreativeExecutionPackagesReport): string {
    const lines: string[] = [report.summary]
    for (const result of report.packages) {
        const label = result.caseId ?? '(sem id)'
        const packageId = result.package !== null ? ` ${result.package.packageId}` : ''
        lines.push(`  ${label}: ${result.status}${packageId}`)
        if (result.status !== 'generated') {
            lines.push(`    ${result.summary}`)
            if (result.failureCode !== null) {
                lines.push(`    failureCode: ${result.failureCode}`)
            }
            for (const error of result.packageErrors) {
                lines.push(`    ${error.code} @${error.path}: ${error.message}`)
            }
        }
    }
    return lines.join('\n')
}

function main(argv: string[]): number {
    const parsed = parseFlags(argv, VALUE_FLAGS)
    if (parsed.error !== null) {
        usageError(parsed.error)
        return EXIT_USAGE
    }

    const manifestPath = parsed.values.manifest
    const outputDirValue = parsed.values['output-dir']
    if (manifestPath === undefined || outputDirValue === undefined) {
        usageError('as flags --manifest e --output-dir sao obrigatorias')
        return EXIT_USAGE
    }

    const manifest = readCasesManifest(manifestPath)
    if ('error' in manifest) {
        console.error(manifest.error)
        return EXIT_USAGE
    }

    const manifestDir = path.dirname(path.resolve(manifestPath))
    const rootDir = parsed.values.root ?? manifestDir

    if (path.isAbsolute(outputDirValue)) {
        console.error('Erro: output-dir deve ser um caminho relativo')
        return EXIT_USAGE
    }

    const confined = confineOutputDir(outputDirValue, rootDir)
    if (!confined.ok) {
        console.error('Erro: output-dir invalido ou fora da raiz autorizada')
        return EXIT_USAGE
    }

    const casePaths = manifest.value.cases.map((casePath) => path.resolve(manifestDir, casePath))
    const results = casePaths.map((casePath) => createCreativeExecutionPackageFromCase(casePath, rootDir))
    const report = aggregateCreativeExecutionPackageResults(results)

    if (!report.valid) {
        console.log(parsed.json ? JSON.stringify(report, null, 2) : renderHuman(report))
        const generationFailure = results.some(
            (result) => result.status === 'generation-failed' || result.status === 'package-invalid',
        )
        return generationFailure ? EXIT_GENERATION : EXIT_INVALID
    }

    const files = new Map<string, string>()
    for (const result of results) {
        const executionPackage = result.package
        if (executionPackage === null) continue
        const fileName = `${executionPackage.packageId}.execution-package.json`
        if (files.has(fileName)) {
            console.error('Erro: packageIds duplicados entre os casos; nenhum pacote foi escrito')
            return EXIT_GENERATION
        }
        files.set(fileName, serializeCreativeExecutionPackage(executionPackage))
    }

    try {
        mkdirSync(confined.dir, { recursive: true })
    } catch {
        console.error('Erro: falha ao criar o output-dir; nenhum pacote foi escrito')
        return EXIT_WRITE
    }

    if (!writePackagesTransactional(confined.dir, files)) {
        console.error('Erro: falha de escrita ou promocao dos pacotes; saida anterior preservada')
        return EXIT_WRITE
    }

    console.log(parsed.json ? JSON.stringify(report, null, 2) : renderHuman(report))
    return EXIT_VALID
}

try {
    process.exitCode = main(process.argv.slice(2))
} catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(`Erro inesperado: ${message}`)
    process.exitCode = EXIT_USAGE
}
