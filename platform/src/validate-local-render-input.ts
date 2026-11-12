/**
 * Validador puro da entrada do adaptador de render local de prova.
 *
 * Reutiliza validateCreativeExecutionPackage para o pacote e aplica o
 * contrato de associacao de assets e o recorte inicial de configuracao.
 * A existencia fisica dos assets e a contencao real de caminhos sao
 * responsabilidade da camada de ferramentas, que resolve o sistema de
 * arquivos; aqui a verificacao de caminho e apenas lexica.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import type { CreativeExecutionPackage } from './creative-execution-package-contract.js'
import {
    LOCAL_RENDER_ASPECT_RATIO,
    LOCAL_RENDER_ASSET_EXTENSIONS,
    LOCAL_RENDER_FPS,
    LOCAL_RENDER_INPUT_SCHEMA_VERSION,
    LOCAL_RENDER_MOTION_INTENTS,
    LOCAL_RENDER_TRANSITIONS_IN,
    LOCAL_RENDER_TRANSITIONS_OUT,
    type LocalRenderAssetAssociation,
    type LocalRenderInputFailureCode,
    type LocalRenderInputValidationResult,
} from './local-render-input-contract.js'
import { inspectRelativePath } from './relative-path.js'
import { validateCreativeExecutionPackage } from './validate-creative-execution-package.js'

const ASSOCIATION_FIELDS = ['schemaVersion', 'packageId', 'assets'] as const
const BINDING_FIELDS = ['beatId', 'path'] as const

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0
}

function fail(failureCode: LocalRenderInputFailureCode, subject: string | null): LocalRenderInputValidationResult {
    return { ok: false, failureCode, subject }
}

function hasExactFields(value: Record<string, unknown>, allowed: readonly string[]): boolean {
    const keys = Object.keys(value)
    return keys.length === allowed.length && allowed.every((field) => keys.includes(field))
}

function assetExtensionSupported(assetPath: string): boolean {
    const lower = assetPath.toLowerCase()
    return LOCAL_RENDER_ASSET_EXTENSIONS.some((extension) => lower.endsWith(extension))
}

function configurationSupported(pkg: CreativeExecutionPackage): string | null {
    const output = pkg.output
    if (output.aspectRatio !== LOCAL_RENDER_ASPECT_RATIO) return 'output.aspectRatio'
    if (output.fps !== LOCAL_RENDER_FPS) return 'output.fps'
    if (!Number.isSafeInteger(output.width) || output.width <= 0 || output.width % 2 !== 0) return 'output.width'
    if (!Number.isSafeInteger(output.height) || output.height <= 0 || output.height % 2 !== 0) return 'output.height'
    if (output.plannedContainer !== undefined && output.plannedContainer !== 'mp4') return 'output.plannedContainer'

    const lastIndex = pkg.timeline.length - 1
    for (const [index, step] of pkg.timeline.entries()) {
        if (!(LOCAL_RENDER_MOTION_INTENTS as readonly string[]).includes(step.motionIntent)) {
            return `${step.beatId}.motionIntent`
        }
        if (!(LOCAL_RENDER_TRANSITIONS_IN as readonly string[]).includes(step.transitionIn)) {
            return `${step.beatId}.transitionIn`
        }
        if (!(LOCAL_RENDER_TRANSITIONS_OUT as readonly string[]).includes(step.transitionOut)) {
            return `${step.beatId}.transitionOut`
        }
        if (step.transitionOut === 'fade' && index !== lastIndex) {
            return `${step.beatId}.transitionOut`
        }
    }
    return null
}

/**
 * Valida pacote e associacao em conjunto. A ordem das verificacoes e fixa:
 * pacote, estrutura da associacao, eco do packageId, cobertura de beats,
 * caminhos, extensoes e recorte de configuracao.
 */
export function validateLocalRenderInput(
    packageInput: unknown,
    associationInput: unknown,
): LocalRenderInputValidationResult {
    const packageReport = validateCreativeExecutionPackage(packageInput)
    if (!packageReport.valid) {
        return fail('PACKAGE_INVALID', null)
    }
    const pkg = packageInput as CreativeExecutionPackage

    if (!isPlainObject(associationInput)
        || !hasExactFields(associationInput, ASSOCIATION_FIELDS)
        || associationInput.schemaVersion !== LOCAL_RENDER_INPUT_SCHEMA_VERSION
        || !isNonEmptyString(associationInput.packageId)
        || !Array.isArray(associationInput.assets)) {
        return fail('ASSOCIATION_INVALID', null)
    }
    for (const binding of associationInput.assets) {
        if (!isPlainObject(binding)
            || !hasExactFields(binding, BINDING_FIELDS)
            || !isNonEmptyString(binding.beatId)
            || !isNonEmptyString(binding.path)) {
            return fail('ASSOCIATION_INVALID', null)
        }
    }
    const association = associationInput as unknown as LocalRenderAssetAssociation

    if (association.packageId !== pkg.packageId) {
        return fail('PACKAGE_ID_MISMATCH', association.packageId)
    }

    const timelineBeatIds = pkg.timeline.map((step) => step.beatId)
    const known = new Set(timelineBeatIds)
    const seen = new Set<string>()
    for (const binding of association.assets) {
        if (!known.has(binding.beatId)) {
            return fail('UNKNOWN_BEAT_REFERENCE', binding.beatId)
        }
        if (seen.has(binding.beatId)) {
            return fail('BEAT_ASSET_DUPLICATE', binding.beatId)
        }
        seen.add(binding.beatId)
    }
    for (const beatId of timelineBeatIds) {
        if (!seen.has(beatId)) {
            return fail('BEAT_ASSET_MISSING', beatId)
        }
    }

    for (const binding of association.assets) {
        if (inspectRelativePath(binding.path).length > 0) {
            return fail('ASSET_PATH_INVALID', binding.path)
        }
        if (!assetExtensionSupported(binding.path)) {
            return fail('ASSET_EXTENSION_UNSUPPORTED', binding.path)
        }
    }

    const unsupported = configurationSupported(pkg)
    if (unsupported !== null) {
        return fail('RENDER_CONFIGURATION_UNSUPPORTED', unsupported)
    }

    return { ok: true, package: pkg, association }
}
