#!/usr/bin/env node
/**
 * Ponte interna entre a camada de ferramentas (Python) e o validador puro da
 * platform. Le o pacote e a associacao de assets, executa
 * validateLocalRenderInput e imprime o veredito JSON em stdout.
 *
 * Nao renderiza nada, nao acessa rede e nao resolve caminhos fisicos: a
 * contencao real e a existencia dos assets ficam com tools/render_local.py.
 * Requer o build da platform (npm run build em platform/).
 *
 * Exit codes: 0 entrada valida; 2 uso ou JSON ilegivel; 3 entrada invalida.
 */

import { readFileSync } from 'node:fs'

import { validateLocalRenderInput } from '../platform/dist/src/validate-local-render-input.js'

const [packagePath, associationPath] = process.argv.slice(2)
if (!packagePath || !associationPath) {
    console.error('uso: node tools/render_bridge.mjs <package.json> <assets.json>')
    process.exit(2)
}

let packageInput
let associationInput
try {
    packageInput = JSON.parse(readFileSync(packagePath, 'utf8'))
    associationInput = JSON.parse(readFileSync(associationPath, 'utf8'))
} catch {
    console.error('erro: arquivo de entrada ilegivel ou JSON invalido')
    process.exit(2)
}

const result = validateLocalRenderInput(packageInput, associationInput)
console.log(JSON.stringify(result))
process.exit(result.ok ? 0 : 3)
