/**
 * Codigos de falha do preflight local de TEMPORAL-02 (TEMPORAL-02-02).
 *
 * Fonte unica e imutavel para os tres codigos da Via A (rejeicao de preflight
 * antes do start). Os quatro codigos posteriores de start, Activity e Workflow
 * pertencem a etapas futuras e nao sao declarados nesta fatia.
 */

export const COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES = Object.freeze({
    inputInvalid: 'TEMPORAL_COMPOSITION_INPUT_INVALID',
    inputTooLarge: 'TEMPORAL_COMPOSITION_INPUT_TOO_LARGE',
    sensitiveInput: 'TEMPORAL_COMPOSITION_SENSITIVE_INPUT',
} as const)

export type CompositionValidationPreflightFailureCode =
    (typeof COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES)[keyof typeof COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES]

export const COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST = Object.freeze([
    COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid,
    COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge,
    COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput,
] as const)

const PREFLIGHT_CODE_SET: ReadonlySet<string> = new Set(COMPOSITION_VALIDATION_PREFLIGHT_CODE_LIST)

export function isCompositionValidationPreflightFailureCode(
    value: unknown,
): value is CompositionValidationPreflightFailureCode {
    return typeof value === 'string' && PREFLIGHT_CODE_SET.has(value)
}

export const COMPOSITION_VALIDATION_PREFLIGHT_MESSAGES: Readonly<
    Record<CompositionValidationPreflightFailureCode, string>
> = Object.freeze({
    [COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputInvalid]:
        'Composition validation input is invalid.',
    [COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.inputTooLarge]:
        'Composition validation input exceeds the allowed size.',
    [COMPOSITION_VALIDATION_PREFLIGHT_FAILURE_CODES.sensitiveInput]:
        'Composition validation input contains prohibited content.',
})
