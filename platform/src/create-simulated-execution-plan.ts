/**
 * Compilador puro do SimulatedExecutionPlan v1.
 *
 * Recebe um CreativeExecutionPackage, valida-o com o validador de referencia
 * e compila a timeline em etapas simuladas ordenadas. Nao acessa filesystem,
 * rede, relogio, aleatoriedade ou variaveis de ambiente; nao importa Temporal;
 * nao gera midia; nao muta o pacote. O mesmo pacote produz sempre o mesmo
 * plano, serializavel e byte a byte estavel.
 *
 * Cada entrada da timeline gera quatro etapas na ordem fixa:
 * prepare-scene -> apply-text -> apply-motion -> finalize-scene.
 * Textos, intencoes e IDs sao preservados sem alteracao; nenhuma instrucao
 * de renderizacao, comando de ferramenta ou prompt generativo e criado.
 */

import type { CreativeExecutionPackage } from './creative-execution-package-contract.js'
import { EXECUTION_PACKAGE_SCHEMA_VERSION } from './creative-execution-package-contract.js'
import {
    deriveSimulatedExecutionId,
    SIMULATED_PLAN_SCHEMA_VERSION,
    SIMULATED_STEP_OPERATIONS,
    SIMULATION_ADAPTER,
    type SimulatedExecutionPlan,
    type SimulatedExecutionPlanCreationResult,
    type SimulatedExecutionStep,
    type SimulatedStepInputs,
    type SimulatedStepOperation,
} from './simulated-execution-plan-contract.js'
import { validateCreativeExecutionPackage } from './validate-creative-execution-package.js'

const EXECUTION_ID_PATTERN = /^simulation-[a-z0-9]+(-[a-z0-9]+)*$/
const EXECUTION_HASH_ID_PATTERN = /^simulation-v1-[0-9a-f]{64}$/

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function inputsFor(
    operation: SimulatedStepOperation,
    entry: CreativeExecutionPackage['timeline'][number],
): SimulatedStepInputs {
    if (operation === 'prepare-scene') {
        return {
            sceneId: entry.sceneIds[0] as string,
            startMs: entry.startMs,
            durationMs: entry.durationMs,
            endMs: entry.endMs,
        }
    }
    if (operation === 'apply-text') {
        return {
            ...(entry.onScreenText !== undefined ? { onScreenText: entry.onScreenText } : {}),
            ...(entry.narrationText !== undefined ? { narrationText: entry.narrationText } : {}),
        }
    }
    if (operation === 'apply-motion') {
        return {
            motionIntent: entry.motionIntent,
            transitionIn: entry.transitionIn,
            transitionOut: entry.transitionOut,
        }
    }
    return {}
}

function expectedArtifactIdsFor(
    operation: SimulatedStepOperation,
    entry: CreativeExecutionPackage['timeline'][number],
    isLastEntry: boolean,
): string[] {
    if (operation === 'apply-text') {
        return [
            ...(entry.onScreenText !== undefined ? ['captions'] : []),
            ...(entry.narrationText !== undefined ? ['narration-script'] : []),
        ]
    }
    if (operation === 'finalize-scene') {
        return ['primary-output', ...(isLastEntry ? ['execution-report'] : [])]
    }
    return []
}

/**
 * Pre-checagem da timeline sobre o documento bruto: produz TIMELINE_INVALID
 * quando a janela temporal esta quebrada, antes da validacao estrutural do
 * pacote. Devolve 'skip' quando o documento nao tem forma avaliavel (a
 * validacao do pacote decide nesse caso).
 */
function timelinePrecheck(input: Record<string, unknown>): 'ok' | 'invalid' | 'skip' {
    const timeline = input.timeline
    const output = input.output
    if (!Array.isArray(timeline) || timeline.length === 0 || !isPlainObject(output)) return 'skip'
    if (typeof output.durationMs !== 'number') return 'skip'
    let expectedStartMs = 0
    for (let index = 0; index < timeline.length; index++) {
        const entry = timeline[index]
        if (!isPlainObject(entry)) return 'skip'
        if (
            typeof entry.order !== 'number'
            || typeof entry.startMs !== 'number'
            || typeof entry.durationMs !== 'number'
            || typeof entry.endMs !== 'number'
            || !Array.isArray(entry.sceneIds)
        ) {
            return 'skip'
        }
        if (
            entry.order !== index + 1
            || entry.startMs !== expectedStartMs
            || entry.endMs !== entry.startMs + entry.durationMs
            || entry.sceneIds.length === 0
        ) {
            return 'invalid'
        }
        expectedStartMs = entry.endMs
    }
    return expectedStartMs === output.durationMs ? 'ok' : 'invalid'
}

/**
 * Compila o pacote em plano simulado. A ordem de verificacao e fixa:
 * forma/versao -> timeline -> validade do pacote -> artefatos -> executionId.
 * `caseId` e metadado opcional do consumidor; nao altera a compilacao.
 */
export function createSimulatedExecutionPlan(
    input: unknown,
    caseId: string | null = null,
): SimulatedExecutionPlanCreationResult {
    if (!isPlainObject(input)) {
        return { ok: false, failureCode: 'PACKAGE_INVALID' }
    }
    if (typeof input.schemaVersion === 'number' && input.schemaVersion !== EXECUTION_PACKAGE_SCHEMA_VERSION) {
        return { ok: false, failureCode: 'PACKAGE_VERSION_UNSUPPORTED' }
    }
    if (timelinePrecheck(input) === 'invalid') {
        return { ok: false, failureCode: 'TIMELINE_INVALID' }
    }

    const packageReport = validateCreativeExecutionPackage(input)
    if (!packageReport.valid) {
        return { ok: false, failureCode: 'PACKAGE_INVALID' }
    }
    const executionPackage = input as unknown as CreativeExecutionPackage

    const timeline = executionPackage.timeline
    if (timeline.length === 0) {
        return { ok: false, failureCode: 'TIMELINE_INVALID' }
    }
    let expectedStartMs = 0
    for (let index = 0; index < timeline.length; index++) {
        const entry = timeline[index] as CreativeExecutionPackage['timeline'][number]
        if (
            entry.order !== index + 1
            || entry.startMs !== expectedStartMs
            || entry.endMs !== entry.startMs + entry.durationMs
            || entry.sceneIds.length === 0
        ) {
            return { ok: false, failureCode: 'TIMELINE_INVALID' }
        }
        expectedStartMs = entry.endMs
    }
    if (expectedStartMs !== executionPackage.output.durationMs) {
        return { ok: false, failureCode: 'TIMELINE_INVALID' }
    }

    const artifactIds = new Set(executionPackage.expectedArtifacts.map((artifact) => artifact.id))
    const referenced = new Set<string>()
    const steps: SimulatedExecutionStep[] = []
    for (let entryIndex = 0; entryIndex < timeline.length; entryIndex++) {
        const entry = timeline[entryIndex] as CreativeExecutionPackage['timeline'][number]
        const isLastEntry = entryIndex === timeline.length - 1
        for (const operation of SIMULATED_STEP_OPERATIONS) {
            const expectedArtifactIds = expectedArtifactIdsFor(operation, entry, isLastEntry)
            for (const artifactId of expectedArtifactIds) {
                if (!artifactIds.has(artifactId)) {
                    return { ok: false, failureCode: 'ARTIFACT_REFERENCE_INVALID' }
                }
                referenced.add(artifactId)
            }
            steps.push({
                stepId: `${entry.beatId}-${operation}`,
                order: steps.length + 1,
                beatId: entry.beatId,
                sceneId: entry.sceneIds[0] as string,
                startMs: entry.startMs,
                durationMs: entry.durationMs,
                endMs: entry.endMs,
                operation,
                inputs: inputsFor(operation, entry),
                expectedArtifactIds,
            })
        }
    }
    for (const artifactId of artifactIds) {
        if (!referenced.has(artifactId)) {
            return { ok: false, failureCode: 'ARTIFACT_REFERENCE_INVALID' }
        }
    }

    const executionId = deriveSimulatedExecutionId(executionPackage.packageId)
    if (!EXECUTION_ID_PATTERN.test(executionId) && !EXECUTION_HASH_ID_PATTERN.test(executionId)) {
        return { ok: false, failureCode: 'EXECUTION_ID_INVALID' }
    }

    const plan: SimulatedExecutionPlan = {
        schemaVersion: SIMULATED_PLAN_SCHEMA_VERSION,
        executionId,
        packageId: executionPackage.packageId,
        caseId,
        adapter: SIMULATION_ADAPTER,
        output: {
            profileId: executionPackage.output.profileId,
            mediaKind: executionPackage.output.mediaKind,
            width: executionPackage.output.width,
            height: executionPackage.output.height,
            aspectRatio: executionPackage.output.aspectRatio,
            fps: executionPackage.output.fps,
            durationMs: executionPackage.output.durationMs,
        },
        steps,
        expectedArtifacts: executionPackage.expectedArtifacts.map((artifact) => ({
            id: artifact.id,
            kind: artifact.kind,
            required: artifact.required,
            logicalName: artifact.logicalName,
            contentType: artifact.contentType,
        })),
    }

    return { ok: true, plan }
}
