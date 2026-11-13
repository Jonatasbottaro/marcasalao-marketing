/**
 * Contrato interno AssetManifest v1 — inventario versionado e rastreavel dos
 * materiais de midia usados por um CreativeExecutionPackage.
 *
 * Separa o cadastro do arquivo fisico (assets com id, tipo, caminho relativo,
 * bytes, SHA-256, origem e licenca) do vinculo por beat (bindings beatId -> assetId),
 * permitindo que varios beats reutilizem o mesmo material sem duplicacao.
 *
 * Nucleo estritamente puro e deterministico: sem I/O, sem rede, sem relogio,
 * sem aleatoriedade, sem mutacao da entrada.
 */

import type { CreativeExecutionPackage } from './creative-execution-package-contract.js'
import type { LocalRenderAssetAssociation, LocalRenderInputFailureCode } from './local-render-input-contract.js'
import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const ASSET_MANIFEST_SCHEMA_VERSION = 1

/** Campos de topo conhecidos, em ordem fixa. */
export const ASSET_MANIFEST_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'caseId',
    'packageId',
    'assets',
    'bindings',
] as const

/** Campos conhecidos de cada item do inventario, em ordem fixa. */
export const ASSET_MANIFEST_ENTRY_FIELDS = [
    'id',
    'type',
    'path',
    'bytes',
    'sha256',
    'origin',
    'license',
] as const

/** Campos conhecidos de cada vinculo beat -> asset, em ordem fixa. */
export const ASSET_MANIFEST_BINDING_FIELDS = [
    'beatId',
    'assetId',
] as const

/** Tipos de midia suportados no inventario v1. */
export const ASSET_MANIFEST_TYPES = ['image', 'video'] as const

export type AssetManifestMediaType = (typeof ASSET_MANIFEST_TYPES)[number]

/** Extensoes aceitas por tipo de midia (minusculas, com ponto). */
export const ASSET_MANIFEST_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp'] as const
export const ASSET_MANIFEST_VIDEO_EXTENSIONS = ['.mp4', '.mov'] as const

/** Valor padrao quando a licenca ainda nao foi declarada. */
export const ASSET_LICENSE_PENDING = 'pending'

/** Padrao hexadecimal SHA-256 em minusculas (64 caracteres). */
export const SHA256_HEX_PATTERN = /^[0-9a-f]{64}$/

/** Entrada declarativa de um material de midia no inventario. */
export interface AssetManifestEntry {
    readonly id: string
    readonly type: AssetManifestMediaType
    readonly path: string
    readonly bytes: number
    readonly sha256: string
    readonly origin: string
    readonly license: string
}

/** Vinculo explicito entre um beat do pacote e um asset cadastrado. */
export interface AssetManifestBinding {
    readonly beatId: string
    readonly assetId: string
}

/** Inventario versionado de midia AssetManifest v1. */
export interface AssetManifest {
    readonly schemaVersion: 1
    readonly caseId: string
    readonly packageId: string
    readonly assets: readonly AssetManifestEntry[]
    readonly bindings: readonly AssetManifestBinding[]
}

/** Vinculo resolvido na ordem da timeline, com metadados do asset e tempos do pacote. */
export interface ResolvedAssetBinding {
    readonly beatId: string
    readonly assetId: string
    readonly type: AssetManifestMediaType
    readonly path: string
    readonly bytes: number
    readonly sha256: string
    readonly origin: string
    readonly license: string
    readonly startMs: number
    readonly endMs: number
    readonly durationMs: number
}

/** Codigos de falha estaveis para validacao do inventario de midia. */
export type AssetManifestFailureCode =
    | LocalRenderInputFailureCode
    | 'ASSET_MANIFEST_INVALID'
    | 'CASE_ID_MISMATCH'
    | 'ASSET_ID_DUPLICATE'
    | 'UNKNOWN_ASSET_REFERENCE'

export type AssetManifestValidationResult =
    | {
        readonly ok: true
        readonly package: CreativeExecutionPackage
        readonly manifest: AssetManifest
        readonly association: LocalRenderAssetAssociation
        readonly resolvedBindings: readonly ResolvedAssetBinding[]
    }
    | {
        readonly ok: false
        readonly failureCode: AssetManifestFailureCode
        readonly subject: string | null
    }

export { KEBAB_CASE_PATTERN }
