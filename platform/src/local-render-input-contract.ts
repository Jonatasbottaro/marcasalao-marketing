/**
 * Contrato interno da entrada do adaptador de render local de prova.
 *
 * Une o CreativeExecutionPackage v1 (especificacao tecnica imutavel) a uma
 * associacao explicita de assets locais por beat. O pacote continua sem
 * executar nada; este contrato apenas descreve e delimita a entrada que a
 * camada de ferramentas pode consumir. A execucao da ferramenta de video
 * vive fora do nucleo, em tools/.
 *
 * Nucleo estritamente puro e deterministico: sem I/O, sem rede, sem relogio,
 * sem aleatoriedade, sem variaveis de ambiente. O recorte inicial cobre as
 * duas fixtures verticais versionadas; configuracoes fora dele recebem
 * codigo de falha estavel, nunca uma aproximacao silenciosa.
 */

import type { CreativeExecutionPackage } from './creative-execution-package-contract.js'

/** Unica versao de schema suportada nesta fatia. */
export const LOCAL_RENDER_INPUT_SCHEMA_VERSION = 1

/** Extensoes de asset aceitas pelo recorte inicial (minusculas, com ponto). */
export const LOCAL_RENDER_ASSET_EXTENSIONS = [
    '.png',
    '.jpg',
    '.jpeg',
    '.webp',
    '.mp4',
    '.mov',
] as const

/** Intencoes de movimento suportadas pelo recorte inicial. */
export const LOCAL_RENDER_MOTION_INTENTS = ['none', 'slow-zoom'] as const

/** Transicoes de entrada suportadas: corte seco ou nenhuma. */
export const LOCAL_RENDER_TRANSITIONS_IN = ['none', 'cut'] as const

/** Transicoes de saida suportadas: corte seco ou fade (somente no ultimo beat). */
export const LOCAL_RENDER_TRANSITIONS_OUT = ['cut', 'fade'] as const

/** Parametros fixos do recorte inicial de prova. */
export const LOCAL_RENDER_FPS = 30
export const LOCAL_RENDER_ASPECT_RATIO = '9:16'

/** Ligacao explicita de um beat a um asset local, por caminho relativo. */
export interface LocalRenderAssetBinding {
    readonly beatId: string
    readonly path: string
}

/**
 * Associacao de assets: exatamente uma ligacao por beat da timeline, sem
 * beats desconhecidos, sem duplicidade. O packageId deve ecoar o pacote.
 */
export interface LocalRenderAssetAssociation {
    readonly schemaVersion: 1
    readonly packageId: string
    readonly assets: readonly LocalRenderAssetBinding[]
}

/** Codigos de falha estaveis; a automacao confia no codigo, nao na mensagem. */
export type LocalRenderInputFailureCode =
    | 'PACKAGE_INVALID'
    | 'ASSOCIATION_INVALID'
    | 'PACKAGE_ID_MISMATCH'
    | 'BEAT_ASSET_MISSING'
    | 'BEAT_ASSET_DUPLICATE'
    | 'UNKNOWN_BEAT_REFERENCE'
    | 'ASSET_PATH_INVALID'
    | 'ASSET_EXTENSION_UNSUPPORTED'
    | 'RENDER_CONFIGURATION_UNSUPPORTED'

export type LocalRenderInputValidationResult =
    | {
        readonly ok: true
        readonly package: CreativeExecutionPackage
        readonly association: LocalRenderAssetAssociation
    }
    | {
        readonly ok: false
        readonly failureCode: LocalRenderInputFailureCode
        readonly subject: string | null
    }
