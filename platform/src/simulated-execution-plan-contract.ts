/**
 * Contrato interno SimulatedExecutionPlan v1 — plano executavel simulado,
 * compilado exclusivamente de um CreativeExecutionPackage v1 valido.
 *
 * O plano descreve a execucao futura simulada: etapas ordenadas por beat da
 * timeline, operacoes neutras e artefatos esperados. NAO e renderizacao:
 * nenhuma operacao gera midia, nenhuma instrucao de ferramenta de video,
 * nenhum fornecedor,
 * nenhum prompt generativo. O adaptador `simulation` e uma ferramenta de
 * verificacao do contrato, nunca um renderer.
 *
 * Nucleo estritamente puro e deterministico: sem timestamp, sem aleatoriedade,
 * sem I/O, sem variaveis de ambiente, sem PID, sem caminho de maquina.
 */

import { createHash } from 'node:crypto'

/** Unica versao de schema suportada nesta fatia. */
export const SIMULATED_PLAN_SCHEMA_VERSION = 1

/** Limite do executionId legivel; acima dele usa-se a forma canonica com hash. */
export const SIMULATED_EXECUTION_ID_MAX_LENGTH = 128

/** Prefixo da forma canonica com hash (versionada, sem timestamp nem caminho). */
export const SIMULATED_EXECUTION_HASH_PREFIX = 'simulation-v1-'

/** Adaptador interno desta fatia: verificacao de contrato, nao renderizador. */
export const SIMULATION_ADAPTER = 'simulation'

/** Operacoes neutras da execucao simulada, em ordem fixa por beat. */
export const SIMULATED_STEP_OPERATIONS = [
    'prepare-scene',
    'apply-text',
    'apply-motion',
    'finalize-scene',
] as const

export type SimulatedStepOperation = (typeof SIMULATED_STEP_OPERATIONS)[number]

/** Campos de topo do plano, em ordem canonica de serializacao. */
export const SIMULATED_PLAN_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'executionId',
    'packageId',
    'caseId',
    'adapter',
    'output',
    'steps',
    'expectedArtifacts',
] as const

/** Saida consolidada do plano: eco dos dados ja validados do pacote. */
export interface SimulatedExecutionOutput {
    readonly profileId: string
    readonly mediaKind: 'video'
    readonly width: number
    readonly height: number
    readonly aspectRatio: string
    readonly fps: number
    readonly durationMs: number
}

/**
 * Inputs de uma etapa: somente dados ja presentes no pacote, por operacao.
 * `prepare-scene` carrega a cena e a janela temporal; `apply-text` carrega os
 * textos canonicos quando existem; `apply-motion` carrega intencoes neutras;
 * `finalize-scene` nao carrega inputs. Nenhum texto e criado ou alterado.
 */
export interface SimulatedStepInputs {
    readonly sceneId?: string
    readonly startMs?: number
    readonly durationMs?: number
    readonly endMs?: number
    readonly onScreenText?: string
    readonly narrationText?: string
    readonly motionIntent?: string
    readonly transitionIn?: string
    readonly transitionOut?: string
}

export interface SimulatedExecutionStep {
    readonly stepId: string
    readonly order: number
    readonly beatId: string
    readonly sceneId: string
    readonly startMs: number
    readonly durationMs: number
    readonly endMs: number
    readonly operation: SimulatedStepOperation
    readonly inputs: SimulatedStepInputs
    readonly expectedArtifactIds: readonly string[]
}

/** Artefato esperado do plano: eco logico do artefato declarado no pacote. */
export interface SimulatedExpectedArtifact {
    readonly id: string
    readonly kind: string
    readonly required: boolean
    readonly logicalName: string
    readonly contentType: string
}

export interface SimulatedExecutionPlan {
    readonly schemaVersion: 1
    readonly executionId: string
    readonly packageId: string
    readonly caseId: string | null
    readonly adapter: 'simulation'
    readonly output: SimulatedExecutionOutput
    readonly steps: readonly SimulatedExecutionStep[]
    readonly expectedArtifacts: readonly SimulatedExpectedArtifact[]
}

/** Codigos de falha da compilacao do plano: estaveis, sem mensagens variaveis. */
export type SimulatedExecutionPlanFailureCode =
    | 'PACKAGE_INVALID'
    | 'PACKAGE_VERSION_UNSUPPORTED'
    | 'TIMELINE_INVALID'
    | 'ARTIFACT_REFERENCE_INVALID'
    | 'EXECUTION_ID_INVALID'
    | 'INTERNAL_INVARIANT_FAILED'

export type SimulatedExecutionPlanCreationResult =
    | { readonly ok: true; readonly plan: SimulatedExecutionPlan }
    | { readonly ok: false; readonly failureCode: SimulatedExecutionPlanFailureCode }

/**
 * Deriva o executionId deterministico: `simulation-<packageId>` enquanto
 * couber no limite; acima dele, canonicalizacao explicita (JSON com chave
 * fixa, sem espacos) + SHA-256 com prefixo versionado `simulation-v1-`.
 * Sem timestamp, sem aleatoriedade, sem caminho, maquina, usuario, PID ou
 * variavel de ambiente.
 */
export function deriveSimulatedExecutionId(packageId: string): string {
    const readable = `simulation-${packageId}`
    if (readable.length <= SIMULATED_EXECUTION_ID_MAX_LENGTH) {
        return readable
    }
    const canonical = JSON.stringify({ packageId })
    const digest = createHash('sha256').update(canonical, 'utf8').digest('hex')
    return `${SIMULATED_EXECUTION_HASH_PREFIX}${digest}`
}

export const SIMULATED_PLAN_VALID_SUMMARY = 'Simulated execution plan is valid.'

export function simulatedPlanInvalidSummary(errorCount: number): string {
    return `Simulated execution plan is invalid: ${errorCount} error(s).`
}
