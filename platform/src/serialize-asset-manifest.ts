/**
 * Serializacao canonica do AssetManifest v1.
 *
 * JSON com indentacao estavel de dois espacos, ordem de propriedades definida
 * explicitamente pelo contrato, LF, uma newline final, UTF-8 sem BOM.
 *
 * Funcao pura: sem I/O, sem relogio, sem aleatoriedade, sem mutacao.
 */

import type { AssetManifest, AssetManifestBinding, AssetManifestEntry } from './asset-manifest-contract.js'

function canonicalEntry(entry: AssetManifestEntry): Record<string, unknown> {
    return {
        id: entry.id,
        type: entry.type,
        path: entry.path,
        bytes: entry.bytes,
        sha256: entry.sha256,
        origin: entry.origin,
        license: entry.license,
    }
}

function canonicalBinding(binding: AssetManifestBinding): Record<string, unknown> {
    return {
        beatId: binding.beatId,
        assetId: binding.assetId,
    }
}

/**
 * Serializa o inventario de midia na forma canonica.
 */
export function serializeAssetManifest(manifest: AssetManifest): string {
    const canonical = {
        schemaVersion: manifest.schemaVersion,
        caseId: manifest.caseId,
        packageId: manifest.packageId,
        assets: manifest.assets.map(canonicalEntry),
        bindings: manifest.bindings.map(canonicalBinding),
    }
    return `${JSON.stringify(canonical, null, 2)}\n`
}
