/**
 * Camada de I/O transacional da execucao simulada v1.
 *
 * Filesystem permitido somente aqui e na CLI. Fluxo: serializar todos os
 * arquivos em memoria -> criar staging interno ao destino -> escrever ->
 * reler -> validar bytes e hashes -> backup dos alvos existentes -> promover
 * com rename -> reverter em falha -> remover staging/backup apos sucesso.
 * Zero promocao parcial; destino anterior intacto em qualquer falha.
 *
 * Confinamento: o destino precisa estar estritamente dentro da raiz
 * declarada (lexical e apos realpath do ancestral existente mais proximo);
 * caminho absoluto, escape por `..`, symlink externo e arquivo no lugar de
 * diretorio sao rejeitados antes de qualquer escrita.
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
import { createHash } from 'node:crypto'

import type { SimulatedExecutionPlan } from './simulated-execution-plan-contract.js'
import type { SimulatedExecutionReport } from './simulated-execution-report-contract.js'
import {
    serializeSimulatedExecutionEvents,
    serializeSimulatedExecutionPlan,
    serializeSimulatedExecutionReport,
    serializeSimulatedHashes,
} from './serialize-simulated-execution.js'
import type { SimulatedArtifactFile } from './simulated-execution-runner.js'

export const SIMULATED_STAGING_DIR_NAME = '.staging-simulated-execution'

export interface SimulatedExecutionWriteInput {
    readonly plan: SimulatedExecutionPlan
    readonly report: SimulatedExecutionReport
    readonly artifacts: readonly SimulatedArtifactFile[]
}

export type SimulatedExecutionWriteResult =
    | { readonly ok: true }
    | { readonly ok: false; readonly stage: 'confine' | 'write' | 'verify' | 'promote' }

/** Confinamento do destino: lexical + realpath; nunca cria nada. */
export function confineSimulatedOutputDir(outputDirValue: string, rootDir: string): { readonly ok: true; readonly dir: string } | { readonly ok: false } {
    if (path.isAbsolute(outputDirValue)) {
        return { ok: false }
    }
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

/** Monta o mapa completo de arquivos relativos -> conteudo textual. */
export function buildSimulatedExecutionFiles(input: SimulatedExecutionWriteInput): ReadonlyMap<string, string> {
    const files = new Map<string, string>()
    files.set('execution-plan.json', serializeSimulatedExecutionPlan(input.plan))
    files.set('execution-report.json', serializeSimulatedExecutionReport(input.report))
    files.set('events.json', serializeSimulatedExecutionEvents(input.report.events))
    for (const artifact of input.artifacts) {
        files.set(artifact.relativePath, artifact.content)
    }
    const hashes: Record<string, string> = {}
    for (const [relativePath, content] of files) {
        hashes[relativePath] = createHash('sha256').update(content, 'utf8').digest('hex')
    }
    files.set('hashes.json', serializeSimulatedHashes(hashes))
    return files
}

/**
 * Escreve a execucao de forma transacional. Em falha, os arquivos ja
 * promovidos sao revertidos a partir do backup e o destino anterior fica
 * intacto; o staging e preservado ate o diagnostico (a CLI o remove apos
 * emitir o erro sanitizado).
 */
export function writeSimulatedExecution(
    outputDir: string,
    input: SimulatedExecutionWriteInput,
): SimulatedExecutionWriteResult {
    const files = buildSimulatedExecutionFiles(input)
    const staging = path.join(outputDir, SIMULATED_STAGING_DIR_NAME)
    const backup = path.join(staging, '.backup')

    try {
        mkdirSync(outputDir, { recursive: true })
    } catch {
        return { ok: false, stage: 'write' }
    }

    try {
        rmSync(staging, { recursive: true, force: true })
        mkdirSync(backup, { recursive: true })

        // Escrita em staging.
        for (const [relativePath, content] of files) {
            const staged = path.join(staging, relativePath)
            try {
                mkdirSync(path.dirname(staged), { recursive: true })
                writeFileSync(staged, content, 'utf8')
            } catch {
                return { ok: false, stage: 'write' }
            }
        }

        // Releitura e verificacao de bytes e hashes.
        for (const [relativePath, content] of files) {
            const staged = path.join(staging, relativePath)
            let readBack: string
            try {
                readBack = readFileSync(staged, 'utf8')
            } catch {
                return { ok: false, stage: 'verify' }
            }
            if (readBack !== content) {
                return { ok: false, stage: 'verify' }
            }
            if (relativePath !== 'hashes.json') {
                const expected = createHash('sha256').update(content, 'utf8').digest('hex')
                const actual = createHash('sha256').update(readBack, 'utf8').digest('hex')
                if (actual !== expected) {
                    return { ok: false, stage: 'verify' }
                }
            }
        }

        // Backup dos alvos existentes e promocao com rename.
        const promoted: string[] = []
        try {
            for (const [relativePath] of files) {
                const target = path.join(outputDir, relativePath)
                if (existsSync(target)) {
                    mkdirSync(path.dirname(path.join(backup, relativePath)), { recursive: true })
                    copyFileSync(target, path.join(backup, relativePath))
                }
            }
            for (const [relativePath] of files) {
                const target = path.join(outputDir, relativePath)
                mkdirSync(path.dirname(target), { recursive: true })
                renameSync(path.join(staging, relativePath), target)
                promoted.push(relativePath)
            }
        } catch {
            for (const relativePath of promoted) {
                const backupFile = path.join(backup, relativePath)
                const target = path.join(outputDir, relativePath)
                try {
                    if (existsSync(backupFile)) {
                        renameSync(backupFile, target)
                    } else {
                        rmSync(target, { force: true })
                    }
                } catch {
                    // reversao best-effort; o erro tecnico e reportado pela CLI
                }
            }
            return { ok: false, stage: 'promote' }
        }

        rmSync(staging, { recursive: true, force: true })
        return { ok: true }
    } catch {
        return { ok: false, stage: 'write' }
    }
}

/** Remove o staging preservado para diagnostico, apos o erro sanitizado. */
export function removeSimulatedStaging(outputDir: string): void {
    try {
        rmSync(path.join(outputDir, SIMULATED_STAGING_DIR_NAME), { recursive: true, force: true })
    } catch {
        // limpeza best-effort
    }
}
