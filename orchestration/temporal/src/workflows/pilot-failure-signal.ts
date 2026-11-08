/**
 * Traducao de falha da SDK para o sinal neutro do piloto.
 *
 * Unica camada do piloto que conhece as classes de falha do Temporal. O sinal
 * carrega apenas classe, codigo estavel e a flag de nao retry: nunca mensagem,
 * detalhe, causa ou stack, para que o resultado e o registro continuem
 * sanitizados quando vierem de uma falha externa.
 */
import { ApplicationFailure, TemporalFailure, TimeoutFailure } from '@temporalio/workflow'

import type { PilotFailureSignal } from '../pilot-core/pilot-outcome.js'

/** Desce a cadeia de causas ate a falha que explica o que aconteceu. */
function innermost(error: Error): Error {
    let current = error
    while (current instanceof TemporalFailure && current.cause instanceof Error) {
        current = current.cause
    }
    return current
}

export function signalOf(error: unknown): PilotFailureSignal {
    if (!(error instanceof Error)) return { kind: 'unknown' }

    const cause = innermost(error)
    if (cause instanceof TimeoutFailure) return { kind: 'timeout' }
    if (cause instanceof ApplicationFailure) {
        return { kind: 'application', code: cause.type ?? '', nonRetryable: cause.nonRetryable === true }
    }
    return { kind: 'unknown' }
}
