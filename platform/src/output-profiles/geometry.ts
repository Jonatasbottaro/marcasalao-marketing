import type { GeometryPreset } from './types.js'

/**
 * Geometrias reaproveitaveis do catalogo.
 *
 * Cada preset e uma **escolha interna** de producao, nao uma exigencia da rede:
 * a condicao oficial, quando existe, mora nas regras (`rules.ts`) e pode ser
 * mais ampla que a proporcao exata do preset (Shorts aceita quadrada **ou**
 * vertical; o preset do catalogo e 1080x1920).
 */

/** Reduz a proporcao pelo maximo divisor comum, na forma "W:H". */
function aspectRatio(width: number, height: number): string {
    const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b))
    const divisor = gcd(width, height)
    return `${width / divisor}:${height / divisor}`
}

/**
 * Constroi um preset garantindo que a proporcao declarada bate com a geometria.
 * A relacao e calculada em tempo de modulo, entao divergencia entre dimensao e
 * `aspectRatio` e impossivel por construcao.
 */
function preset(width: number, height: number): GeometryPreset {
    return { width, height, aspectRatio: aspectRatio(width, height) }
}

/** Quadrado 1080x1080 (1:1), usado em feed de imagem e em arte compartilhada. */
export const GEOMETRY_SQUARE_1080: GeometryPreset = preset(1080, 1080)

/** Retrato 1080x1350 (4:5), geometrica de feed em proporcao vertical moderada. */
export const GEOMETRY_PORTRAIT_4_5: GeometryPreset = preset(1080, 1350)

/** Vertical 1080x1920 (9:16), reaproveitada por Stories, Reels e Shorts. */
export const GEOMETRY_VERTICAL_9_16: GeometryPreset = preset(1080, 1920)

/** Horizontal 1920x1080 (16:9), proporcao padrao de desktop do YouTube. */
export const GEOMETRY_LANDSCAPE_16_9: GeometryPreset = preset(1920, 1080)

/** Frame rate preset interno dos perfis de video deste catalogo. */
export const DEFAULT_VIDEO_FPS = 30
