/**
 * Contrato Composition v1 — segunda fatia do nucleo modular da Content Factory.
 *
 * Composition e um contrato declarativo: nao e roteiro, nao e BeatPlan, nao e
 * renderizacao. O texto canonico permanece estruturado; assets sao referenciados,
 * nunca gerados; o renderizador pode permanecer "undecided".
 *
 * O nucleo NAO conhece nenhum projeto especifico: a composicao e sempre validada
 * contra um ProjectManifest informado explicitamente.
 *
 * Ver docs/decisoes/MKT-VIDEO-001-producao-modular.md,
 * docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md e
 * docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md.
 */

import { KEBAB_CASE_PATTERN } from './project-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const COMPOSITION_SCHEMA_VERSION = 1

/** Tipos de cena suportados na v1, em ordem fixa de documentacao. */
export const COMPOSITION_SCENE_TYPES = ['text', 'image', 'video', 'cta'] as const

export type CompositionSceneType = (typeof COMPOSITION_SCENE_TYPES)[number]

/** Status de metadata permitidos; "approved" aqui e tecnico, nao editorial. */
export const COMPOSITION_METADATA_STATUSES = ['draft', 'review', 'approved', 'archived'] as const

export type CompositionMetadataStatus = (typeof COMPOSITION_METADATA_STATUSES)[number]

/** Faixa de fps aceita na v1: inteiros entre estes limites, inclusive. */
export const COMPOSITION_FPS_MIN = 1
export const COMPOSITION_FPS_MAX = 120

/** Limite documentado de tags em metadata. */
export const COMPOSITION_MAX_TAGS = 8

/** Campos de topo conhecidos, em ordem fixa de verificacao. */
export const COMPOSITION_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'projectId',
    'id',
    'title',
    'locale',
    'format',
    'scenes',
    'renderer',
    'metadata',
] as const

export { KEBAB_CASE_PATTERN }

/** Formato de saida da composicao: intencao de profile, nao imposicao de resolucao. */
export interface CompositionFormat {
    /** Identificador kebab-case que deve existir em ProjectManifest.outputProfiles. */
    profile: string
    width: number
    height: number
    fps: number
}

/**
 * Referencia minima de asset: apenas id e caminho relativo seguro.
 * Nao substitui o futuro AssetManifest: hash, licenca, origem, provider, prompt,
 * dimensoes e duracao pertencem a uma fatia futura. A existencia fisica NAO e
 * verificada nesta fatia.
 */
export interface AssetReference {
    id: string
    path: string
}

/** Conteudo de cena; a forma fechada depende do tipo (ver validador e schema). */
export interface CompositionSceneContent {
    text?: string
    href?: string
    alt?: string
    accessibilityLabel?: string
    asset?: AssetReference
}

export interface CompositionScene {
    id: string
    type: CompositionSceneType
    /** Inteiro maior que zero, em milissegundos. */
    durationMs: number
    content: CompositionSceneContent
}

/** Adaptador de renderizacao; nenhum adapter precisa estar instalado. */
export interface CompositionRenderer {
    adapter: string
}

/** Metadata opcional e pequena; "approved" nao concede autorizacao editorial. */
export interface CompositionMetadata {
    status?: CompositionMetadataStatus
    description?: string
    tags?: string[]
}

/** Composicao declarativa vinculada a um projeto por projectId. */
export interface Composition {
    schemaVersion: number
    projectId: string
    id: string
    title: string
    locale: string
    format: CompositionFormat
    scenes: CompositionScene[]
    renderer: CompositionRenderer
    metadata?: CompositionMetadata
}
