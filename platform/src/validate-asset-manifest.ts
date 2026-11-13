/**
 * Validador puro do AssetManifest v1 contra o CreativeExecutionPackage e o caso.
 *
 * Garante:
 * - Pacote canonico valido (CreativeExecutionPackage v1);
 * - Estrutura fechada do inventario (sem campos desconhecidos);
 * - Correspondencia de caseId e packageId;
 * - Unicidade dos identificadores de assets;
 * - Caminhos relativos permitidos (regra lexica compartilhada) e extensao
 *   compativel com o tipo declarado (image ou video);
 * - Cobertura completa dos beats da timeline, sem duplicidade ou referencia invalida;
 * - Resolucao dos vinculos na ordem da timeline e delegacao para
 *   validateLocalRenderInput na associacao final e no recorte do adaptador.
 *
 * Sem I/O, sem rede, sem relogio, sem aleatoriedade, sem mutacao da entrada.
 */

import {
    ASSET_MANIFEST_BINDING_FIELDS,
    ASSET_MANIFEST_ENTRY_FIELDS,
    ASSET_MANIFEST_IMAGE_EXTENSIONS,
    ASSET_MANIFEST_SCHEMA_VERSION,
    ASSET_MANIFEST_TOP_LEVEL_FIELDS,
    ASSET_MANIFEST_TYPES,
    ASSET_MANIFEST_VIDEO_EXTENSIONS,
    KEBAB_CASE_PATTERN,
    SHA256_HEX_PATTERN,
    type AssetManifest,
    type AssetManifestBinding,
    type AssetManifestEntry,
    type AssetManifestFailureCode,
    type AssetManifestMediaType,
    type AssetManifestValidationResult,
    type ResolvedAssetBinding,
} from './asset-manifest-contract.js'
import type { CreativeExecutionPackage } from './creative-execution-package-contract.js'
import { LOCAL_RENDER_INPUT_SCHEMA_VERSION, type LocalRenderAssetAssociation } from './local-render-input-contract.js'
import { containsControlCharacter, inspectRelativePath } from './relative-path.js'
import { validateCreativeExecutionPackage } from './validate-creative-execution-package.js'
import { validateLocalRenderInput } from './validate-local-render-input.js'

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactFields(value: Record<string, unknown>, allowed: readonly string[]): boolean {
    const keys = Object.keys(value)
    return keys.length === allowed.length && allowed.every((field) => keys.includes(field))
}

function isNonEmptyControlFreeString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0 && !containsControlCharacter(value)
}

function fail(failureCode: AssetManifestFailureCode, subject: string | null): AssetManifestValidationResult {
    return { ok: false, failureCode, subject }
}

function extensionMatchesType(assetPath: string, type: AssetManifestMediaType): boolean {
    const lower = assetPath.toLowerCase()
    const allowed = type === 'image' ? ASSET_MANIFEST_IMAGE_EXTENSIONS : ASSET_MANIFEST_VIDEO_EXTENSIONS
    return (allowed as readonly string[]).some((ext) => lower.endsWith(ext))
}

function validateStructuralEntry(raw: unknown): AssetManifestEntry | null {
    if (!isPlainObject(raw) || !hasExactFields(raw, ASSET_MANIFEST_ENTRY_FIELDS)) {
        return null
    }
    if (
        typeof raw.id !== 'string'
        || !KEBAB_CASE_PATTERN.test(raw.id)
        || typeof raw.type !== 'string'
        || !(ASSET_MANIFEST_TYPES as readonly string[]).includes(raw.type)
        || !isNonEmptyControlFreeString(raw.path)
        || typeof raw.bytes !== 'number'
        || !Number.isSafeInteger(raw.bytes)
        || raw.bytes < 1
        || typeof raw.sha256 !== 'string'
        || !SHA256_HEX_PATTERN.test(raw.sha256)
        || !isNonEmptyControlFreeString(raw.origin)
        || !isNonEmptyControlFreeString(raw.license)
    ) {
        return null
    }

    return {
        id: raw.id,
        type: raw.type as AssetManifestMediaType,
        path: raw.path,
        bytes: raw.bytes,
        sha256: raw.sha256,
        origin: raw.origin.trim(),
        license: raw.license.trim(),
    }
}

function validateStructuralBinding(raw: unknown): AssetManifestBinding | null {
    if (!isPlainObject(raw) || !hasExactFields(raw, ASSET_MANIFEST_BINDING_FIELDS)) {
        return null
    }
    if (
        typeof raw.beatId !== 'string'
        || !KEBAB_CASE_PATTERN.test(raw.beatId)
        || typeof raw.assetId !== 'string'
        || !KEBAB_CASE_PATTERN.test(raw.assetId)
    ) {
        return null
    }
    return {
        beatId: raw.beatId,
        assetId: raw.assetId,
    }
}

export function validateAssetManifest(
    packageInput: unknown,
    expectedCaseId: string | null | undefined,
    manifestInput: unknown,
): AssetManifestValidationResult {
    const packageReport = validateCreativeExecutionPackage(packageInput)
    if (!packageReport.valid) {
        return fail('PACKAGE_INVALID', null)
    }
    const pkg = packageInput as CreativeExecutionPackage

    if (
        !isPlainObject(manifestInput)
        || !hasExactFields(manifestInput, ASSET_MANIFEST_TOP_LEVEL_FIELDS)
        || manifestInput.schemaVersion !== ASSET_MANIFEST_SCHEMA_VERSION
        || typeof manifestInput.caseId !== 'string'
        || !KEBAB_CASE_PATTERN.test(manifestInput.caseId)
        || typeof manifestInput.packageId !== 'string'
        || !KEBAB_CASE_PATTERN.test(manifestInput.packageId)
        || !Array.isArray(manifestInput.assets)
        || manifestInput.assets.length === 0
        || !Array.isArray(manifestInput.bindings)
        || manifestInput.bindings.length === 0
    ) {
        return fail('ASSET_MANIFEST_INVALID', null)
    }

    const parsedAssets: AssetManifestEntry[] = []
    for (const rawEntry of manifestInput.assets) {
        const entry = validateStructuralEntry(rawEntry)
        if (!entry) {
            return fail('ASSET_MANIFEST_INVALID', null)
        }
        parsedAssets.push(entry)
    }

    const parsedBindings: AssetManifestBinding[] = []
    for (const rawBinding of manifestInput.bindings) {
        const binding = validateStructuralBinding(rawBinding)
        if (!binding) {
            return fail('ASSET_MANIFEST_INVALID', null)
        }
        parsedBindings.push(binding)
    }

    if (expectedCaseId !== null && expectedCaseId !== undefined && manifestInput.caseId !== expectedCaseId) {
        return fail('CASE_ID_MISMATCH', manifestInput.caseId)
    }

    if (manifestInput.packageId !== pkg.packageId) {
        return fail('PACKAGE_ID_MISMATCH', manifestInput.packageId)
    }

    const assetMap = new Map<string, AssetManifestEntry>()
    for (const asset of parsedAssets) {
        if (assetMap.has(asset.id)) {
            return fail('ASSET_ID_DUPLICATE', asset.id)
        }
        if (inspectRelativePath(asset.path).length > 0) {
            return fail('ASSET_PATH_INVALID', asset.path)
        }
        if (!extensionMatchesType(asset.path, asset.type)) {
            return fail('ASSET_EXTENSION_UNSUPPORTED', asset.path)
        }
        assetMap.set(asset.id, asset)
    }

    const timelineStepMap = new Map<string, (typeof pkg.timeline)[number]>()
    for (const step of pkg.timeline) {
        timelineStepMap.set(step.beatId, step)
    }

    const bindingByBeat = new Map<string, AssetManifestBinding>()
    for (const binding of parsedBindings) {
        if (!timelineStepMap.has(binding.beatId)) {
            return fail('UNKNOWN_BEAT_REFERENCE', binding.beatId)
        }
        if (bindingByBeat.has(binding.beatId)) {
            return fail('BEAT_ASSET_DUPLICATE', binding.beatId)
        }
        if (!assetMap.has(binding.assetId)) {
            return fail('UNKNOWN_ASSET_REFERENCE', binding.assetId)
        }
        bindingByBeat.set(binding.beatId, binding)
    }

    const orderedBindings: AssetManifestBinding[] = []
    const resolvedBindings: ResolvedAssetBinding[] = []
    const derivedAssociationAssets: { beatId: string; path: string }[] = []

    for (const step of pkg.timeline) {
        const binding = bindingByBeat.get(step.beatId)
        if (!binding) {
            return fail('BEAT_ASSET_MISSING', step.beatId)
        }
        const asset = assetMap.get(binding.assetId)!
        orderedBindings.push(binding)
        resolvedBindings.push({
            beatId: step.beatId,
            assetId: asset.id,
            type: asset.type,
            path: asset.path,
            bytes: asset.bytes,
            sha256: asset.sha256,
            origin: asset.origin,
            license: asset.license,
            startMs: step.startMs,
            endMs: step.endMs,
            durationMs: step.durationMs,
        })
        derivedAssociationAssets.push({
            beatId: step.beatId,
            path: asset.path,
        })
    }

    const derivedAssociation: LocalRenderAssetAssociation = {
        schemaVersion: LOCAL_RENDER_INPUT_SCHEMA_VERSION,
        packageId: pkg.packageId,
        assets: derivedAssociationAssets,
    }

    const renderValidation = validateLocalRenderInput(pkg, derivedAssociation)
    if (!renderValidation.ok) {
        return fail(renderValidation.failureCode, renderValidation.subject)
    }

    const canonicalManifest: AssetManifest = {
        schemaVersion: 1,
        caseId: manifestInput.caseId,
        packageId: manifestInput.packageId,
        assets: parsedAssets,
        bindings: orderedBindings,
    }

    return {
        ok: true,
        package: pkg,
        manifest: canonicalManifest,
        association: renderValidation.association,
        resolvedBindings,
    }
}
