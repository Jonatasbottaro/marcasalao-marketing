/**
 * Serializacao canonica do VisualStyle v1.
 *
 * JSON com indentacao estavel de dois espacos, ordem de propriedades definida
 * explicitamente pelo contrato (nunca pela ordem do objeto original), LF,
 * newline final unica, UTF-8 sem BOM.
 *
 * Funcao pura: sem I/O, sem relogio, sem aleatoriedade, sem mutacao.
 */

import type { VisualStyle } from './visual-style-contract.js'

/**
 * Serializa a direcao visual na forma canonica deterministica.
 */
export function serializeVisualStyle(style: VisualStyle): string {
    const canonical = {
        schemaVersion: style.schemaVersion,
        id: style.id,
        title: {
            textColor: style.title.textColor,
            outlineColor: style.title.outlineColor,
            fontSize: style.title.fontSize,
            marginTop: style.title.marginTop,
            marginHorizontal: style.title.marginHorizontal,
        },
    }
    return `${JSON.stringify(canonical, null, 2)}\n`
}
