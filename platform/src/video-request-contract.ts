/**
 * Contrato interno VideoRequest v1 — entrada unica de producao de video.
 *
 * Um pedido descreve, em um unico documento, o titulo do video, os perfis de
 * saida desejados, um cadastro de midia reutilizavel e cenas ordenadas. Cada
 * cena informa duracao, referencia a midia, legenda, narracao e titulo
 * sobreposto opcional. O compilador puro deriva os documentos existentes
 * (Composition, BeatPlan, OutputPlan, CreativeExecutionPackage, associacao de
 * midia e titulos) a partir deste pedido e de um ProjectManifest.
 *
 * Nucleo estritamente puro e deterministico: sem I/O, sem rede, sem relogio,
 * sem aleatoriedade, sem variaveis de ambiente e sem dependencia de marca.
 * Perfis sao resolvidos apenas pelo catalogo; nada aqui conhece um projeto
 * consumidor especifico.
 */

import { BEAT_NARRATIVE_FUNCTIONS, type BeatNarrativeFunction } from './beat-plan-contract.js'
import { KEBAB_CASE_PATTERN } from './project-contract.js'
import type { VisualStyle } from './visual-style-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const VIDEO_REQUEST_SCHEMA_VERSION = 1

/** Campos de topo conhecidos, em ordem fixa de verificacao. */
export const VIDEO_REQUEST_TOP_LEVEL_FIELDS = [
    'schemaVersion',
    'id',
    'project',
    'title',
    'locale',
    'profiles',
    'visualStyle',
    'media',
    'scenes',
] as const

/** Campos de topo obrigatorios (locale e visualStyle sao opcionais). */
export const VIDEO_REQUEST_REQUIRED_FIELDS = [
    'schemaVersion',
    'id',
    'project',
    'title',
    'profiles',
    'media',
    'scenes',
] as const

/** Campos conhecidos de cada material de midia, em ordem fixa. */
export const VIDEO_REQUEST_MEDIA_FIELDS = ['id', 'path', 'type', 'origin', 'license'] as const

/** Campos obrigatorios de cada material (license e opcional, padrao 'pending'). */
export const VIDEO_REQUEST_MEDIA_REQUIRED_FIELDS = ['id', 'path', 'type', 'origin'] as const

/** Campos conhecidos de cada cena, em ordem fixa. */
export const VIDEO_REQUEST_SCENE_FIELDS = [
    'id',
    'durationMs',
    'mediaId',
    'caption',
    'narration',
    'title',
    'narrativeFunction',
    'motionIntent',
] as const

/** Campos obrigatorios de cada cena (title, narrativeFunction e motionIntent sao opcionais). */
export const VIDEO_REQUEST_SCENE_REQUIRED_FIELDS = ['id', 'durationMs', 'mediaId', 'caption', 'narration'] as const

/** Tipos de midia aceitos no cadastro do pedido. */
export const VIDEO_REQUEST_MEDIA_TYPES = ['image', 'video'] as const

export type VideoRequestMediaType = (typeof VIDEO_REQUEST_MEDIA_TYPES)[number]

/** Intencoes de movimento suportadas pelo recorte local (espelha o adaptador). */
export const VIDEO_REQUEST_MOTION_INTENTS = ['none', 'slow-zoom'] as const

export type VideoRequestMotionIntent = (typeof VIDEO_REQUEST_MOTION_INTENTS)[number]

/** Funcoes narrativas neutras reutilizadas do BeatPlan. */
export const VIDEO_REQUEST_NARRATIVE_FUNCTIONS = BEAT_NARRATIVE_FUNCTIONS

/** Locale padrao aplicado pelo compilador quando o pedido omite o campo. */
export const VIDEO_REQUEST_DEFAULT_LOCALE = 'pt-BR'

/** Licenca padrao aplicada pelo compilador quando o material omite o campo. */
export const VIDEO_REQUEST_DEFAULT_LICENSE = 'pending'

export { KEBAB_CASE_PATTERN }

/** Material de midia cadastrado uma vez e vinculavel a varias cenas. */
export interface VideoRequestMedia {
    readonly id: string
    readonly path: string
    readonly type: VideoRequestMediaType
    readonly origin: string
    readonly license?: string
}

/** Cena ordenada do pedido: duracao, midia, legenda, narracao e titulo opcional. */
export interface VideoRequestScene {
    readonly id: string
    readonly durationMs: number
    readonly mediaId: string
    readonly caption: string
    readonly narration: string
    readonly title?: string
    readonly narrativeFunction?: BeatNarrativeFunction
    readonly motionIntent?: VideoRequestMotionIntent
}

/** Pedido de video v1: entrada unica suficiente para preparar todos os documentos. */
export interface VideoRequest {
    readonly schemaVersion: 1
    readonly id: string
    readonly project: string
    readonly title: string
    readonly locale?: string
    readonly profiles: readonly string[]
    readonly visualStyle?: VisualStyle
    readonly media: readonly VideoRequestMedia[]
    readonly scenes: readonly VideoRequestScene[]
}

/** Codigos de falha estaveis; a automacao confia no codigo, nao na mensagem. */
export type VideoRequestFailureCode =
    | 'VIDEO_REQUEST_INVALID'
    | 'VIDEO_REQUEST_SCHEMA_VERSION_UNSUPPORTED'
    | 'VIDEO_REQUEST_ID_INVALID'
    | 'VIDEO_REQUEST_PROJECT_INVALID'
    | 'VIDEO_REQUEST_TITLE_INVALID'
    | 'VIDEO_REQUEST_LOCALE_INVALID'
    | 'VIDEO_REQUEST_PROFILES_INVALID'
    | 'VIDEO_REQUEST_PROFILE_DUPLICATE'
    | 'VIDEO_REQUEST_MEDIA_INVALID'
    | 'VIDEO_REQUEST_MEDIA_ID_INVALID'
    | 'VIDEO_REQUEST_MEDIA_ID_DUPLICATE'
    | 'VIDEO_REQUEST_MEDIA_PATH_INVALID'
    | 'VIDEO_REQUEST_MEDIA_TYPE_INVALID'
    | 'VIDEO_REQUEST_MEDIA_ORIGIN_INVALID'
    | 'VIDEO_REQUEST_MEDIA_LICENSE_INVALID'
    | 'VIDEO_REQUEST_SCENES_INVALID'
    | 'VIDEO_REQUEST_SCENE_ID_INVALID'
    | 'VIDEO_REQUEST_SCENE_ID_DUPLICATE'
    | 'VIDEO_REQUEST_SCENE_DURATION_INVALID'
    | 'VIDEO_REQUEST_SCENE_MEDIA_REFERENCE_INVALID'
    | 'VIDEO_REQUEST_SCENE_CAPTION_INVALID'
    | 'VIDEO_REQUEST_SCENE_NARRATION_INVALID'
    | 'VIDEO_REQUEST_SCENE_TITLE_INVALID'
    | 'VIDEO_REQUEST_SCENE_NARRATIVE_FUNCTION_INVALID'
    | 'VIDEO_REQUEST_SCENE_MOTION_INTENT_INVALID'
    | 'VIDEO_REQUEST_VISUAL_STYLE_INVALID'
    | 'VIDEO_REQUEST_UNKNOWN_FIELD'

export type VideoRequestValidationResult =
    | { readonly ok: true; readonly request: VideoRequest }
    | { readonly ok: false; readonly failureCode: VideoRequestFailureCode; readonly subject: string | null }