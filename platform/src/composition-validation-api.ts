/**
 * Fronteira publica minima da platform para validacao de Composition v1 contra
 * ProjectManifest (TEMPORAL-02-01).
 *
 * Reexporta a funcao de referencia `validateComposition(composition, project)` e
 * apenas os tipos publicos necessarios ao consumidor externo, sem duplicar
 * contratos, sem expor CLIs ou helpers internos e sem dependencia de runtime.
 */

export { validateComposition } from './validate-composition.js'
export type { Composition } from './composition-contract.js'
export type { ProjectManifest } from './project-contract.js'
export type { CompositionValidationReport } from './validation-report.js'
