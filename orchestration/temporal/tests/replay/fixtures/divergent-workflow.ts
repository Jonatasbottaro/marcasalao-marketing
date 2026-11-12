/**
 * Workflow exclusivamente de teste: mesmo nome do Workflow integrado, mas
 * diverge de proposito (duas chamadas de Activity em vez de uma) para provar
 * que o replay formal falha por nao-determinismo frente a historia gravada.
 * Nao e registrado por nenhum Worker de aplicacao.
 */
import { proxyActivities, type ActivityOptions } from '@temporalio/workflow'

import type * as compositionValidationActivities from '../../../src/activities/composition-validation-activity.js'
import type { CompositionValidationWorkflowInput } from '../../../src/composition-validation/composition-validation-input.js'

const options: ActivityOptions = {
    startToCloseTimeout: '5 seconds',
    retry: { maximumAttempts: 2 },
}

const { validateCompositionActivity } = proxyActivities<typeof compositionValidationActivities>(options)

export async function validateCompositionWorkflow(input: CompositionValidationWorkflowInput): Promise<unknown> {
    const first = await validateCompositionActivity({ project: input.project, composition: input.composition })
    const second = await validateCompositionActivity({ project: input.project, composition: input.composition })
    return { first, second }
}