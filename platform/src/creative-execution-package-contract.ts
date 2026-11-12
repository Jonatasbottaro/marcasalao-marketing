/**
 * Contrato interno CreativeExecutionPackage v1 — especificacao tecnica
 * imutavel da execucao futura, derivada exclusivamente de um pipeline
 * criativo valido (ProjectManifest -> Composition -> OutputPlan ->
 * compatibilidade -> BeatPlan -> ContentPipelineValidationReport).
 *
 * O pacote NAO executa nada: nao renderiza, nao gera midia, nao cria
 * arquivos fisicos, nao acessa rede e nao conhece fornecedor, Temporal,
 * Worker ou fila. Renderizadores, Workers e adaptadores futuros poderao
 * consumi-lo; nenhum deles existe nesta fatia.
 *
 * Nucleo estritamente puro e deterministico: sem timestamp, sem valores
 * aleatorios, sem I/O, sem variaveis de ambiente. O packageId e um
 * identificador tecnico do pacote — nunca um Workflow ID, e nunca o
 * contentHash do Temporal (que permanece fora desta fatia).
 */

import { createHash } from 'node:crypto'

import type {
    BeatMotionIntent,
    BeatNarrativeFunction,
    BeatTransition,
} from './beat-plan-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const EXECUTION_PACKAGE_SCHEMA_VERSION = 1

/** Limite do packageId legivel; acima dele usa-se a forma canonica com hash. */
export const EXECUTION_PACKAGE_ID_MAX_LENGTH = 128

/** Prefixo da forma canonica com hash (versionada, sem timestamp nem caminho). */
export const EXECUTION_PACKAGE_HASH_PREFIX = 'execution-v1-'

/** Campos de topo conhecidos, em ordem canonica de serializacao. */
export const EXECUTION_PACKAGE_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'packageId',
    'projectId',
    'compositionId',
    'outputPlanId',
    'beatPlanId',
    'output',
    'timeline',
    'expectedArtifacts',
    'source',
] as const

/** Artefatos logicos esperados da execucao futura, em ordem fixa. */
export const EXPECTED_ARTIFACT_KINDS = [
    'primary-output',
    'captions',
    'narration-script',
    'execution-report',
] as const

export type ExpectedArtifactKind = (typeof EXPECTED_ARTIFACT_KINDS)[number]

/**
 * Saida consolidada: somente dados ja validados pelo pipeline. `mediaKind`
 * e restrito a video na v1 porque a compatibilidade Composition x OutputPlan
 * compara planos de video. `plannedContainer` so existe quando o perfil do
 * catalogo o declara; codec, bitrate e fornecedor nao existem no contrato e
 * nao sao inventados.
 */
export interface CreativeExecutionOutput {
    readonly profileId: string
    readonly mediaKind: 'video'
    readonly width: number
    readonly height: number
    readonly aspectRatio: string
    readonly fps: number
    readonly plannedContainer?: 'mp4' | 'webm'
    readonly rendererAdapter: string
    readonly durationMs: number
}

/**
 * Etapa da timeline: traducao direta de um beat validado, sem conteudo novo.
 * `sceneIds` preserva a relacao muitos-para-muitos entre beats e cenas;
 * `endMs` e derivado (`startMs + durationMs`). Textos entram somente quando
 * existem no beat e nunca sao alterados.
 */
export interface CreativeExecutionStep {
    readonly order: number
    readonly beatId: string
    readonly sceneIds: readonly string[]
    readonly startMs: number
    readonly durationMs: number
    readonly endMs: number
    readonly narrativeFunction: BeatNarrativeFunction
    readonly motionIntent: BeatMotionIntent
    readonly transitionIn: BeatTransition
    readonly transitionOut: BeatTransition
    readonly onScreenText?: string
    readonly narrationText?: string
}

/**
 * Artefato logico esperado: declaracao do que a execucao futura devera
 * produzir, sem caminho absoluto e sem arquivo fisico nesta fatia.
 * `contentType` e logico (mediaKind ou tipo textual), nunca codec.
 */
export interface ExpectedArtifact {
    readonly id: string
    readonly kind: ExpectedArtifactKind
    readonly required: boolean
    readonly logicalName: string
    readonly contentType: string
}

/** Referencias de origem: somente IDs e versoes, nunca documentos completos. */
export interface CreativeExecutionSourceReferences {
    readonly projectId: string
    readonly compositionId: string
    readonly outputPlanId: string
    readonly beatPlanId: string
    readonly projectSchemaVersion: number
    readonly compositionSchemaVersion: number
    readonly outputPlanSchemaVersion: number
    readonly beatPlanSchemaVersion: number
}

export interface CreativeExecutionPackage {
    readonly schemaVersion: 1
    readonly packageId: string
    readonly projectId: string
    readonly compositionId: string
    readonly outputPlanId: string
    readonly beatPlanId: string
    readonly output: CreativeExecutionOutput
    readonly timeline: readonly CreativeExecutionStep[]
    readonly expectedArtifacts: readonly ExpectedArtifact[]
    readonly source: CreativeExecutionSourceReferences
}

/** Codigos de falha da geracao: estaveis, sem mensagens tecnicas variaveis. */
export type CreativeExecutionPackageFailureCode =
    | 'PIPELINE_INVALID'
    | 'PIPELINE_STAGE_BLOCKED'
    | 'REQUIRED_ID_UNAVAILABLE'
    | 'UNSUPPORTED_OUTPUT_CONFIGURATION'
    | 'DURATION_MISMATCH'
    | 'INTERNAL_INVARIANT_FAILED'

export type CreativeExecutionPackageCreationResult =
    | { readonly ok: true; readonly package: CreativeExecutionPackage }
    | { readonly ok: false; readonly failureCode: CreativeExecutionPackageFailureCode }

/** Identificadores de origem usados na derivacao do packageId. */
export interface PackageSourceIds {
    readonly projectId: string
    readonly compositionId: string
    readonly outputPlanId: string
    readonly beatPlanId: string
}

/**
 * Deriva o packageId deterministico. Preferencia: ID legivel
 * `execution-<projectId>-<compositionId>-<outputPlanId>-<beatPlanId>`
 * enquanto couber no limite. Acima do limite, canonicalizacao explicita
 * (JSON com chaves em ordem fixa, sem espacos) + SHA-256 com prefixo
 * versionado `execution-v1-`. Sem timestamp, sem aleatoriedade, sem caminho
 * e sem depender da ordem de propriedades do objeto original.
 */
export function deriveExecutionPackageId(ids: PackageSourceIds): string {
    const readable = `execution-${ids.projectId}-${ids.compositionId}-${ids.outputPlanId}-${ids.beatPlanId}`
    if (readable.length <= EXECUTION_PACKAGE_ID_MAX_LENGTH) {
        return readable
    }
    const canonical = JSON.stringify({
        projectId: ids.projectId,
        compositionId: ids.compositionId,
        outputPlanId: ids.outputPlanId,
        beatPlanId: ids.beatPlanId,
    })
    const digest = createHash('sha256').update(canonical, 'utf8').digest('hex')
    return `${EXECUTION_PACKAGE_HASH_PREFIX}${digest}`
}

export const EXECUTION_PACKAGE_VALID_SUMMARY = 'Execution package is valid.'

export function executionPackageInvalidSummary(errorCount: number): string {
    return `Execution package is invalid: ${errorCount} error(s).`
}
