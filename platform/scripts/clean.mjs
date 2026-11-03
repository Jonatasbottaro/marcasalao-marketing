/**
 * Remove o artefato de build local (dist/).
 * Script Node portatil: sem rm -rf, sem rimraf, sem dependencias.
 */
import { rmSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const moduleRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

rmSync(path.join(moduleRoot, 'dist'), { recursive: true, force: true })
