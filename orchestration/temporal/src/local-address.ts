/**
 * Guarda de endereco local do piloto TEMPORAL-01.
 *
 * Toda entrada de endereco vem de linha de comando e passa por aqui. O piloto
 * so fala com um servidor local: sem Temporal Cloud, sem producao, sem staging.
 * A recusa nomeia o host recebido, nunca um valor de manifesto.
 */
export const DEFAULT_PILOT_ADDRESS = '127.0.0.1:7233'

const LOCAL_HOSTS = new Set(['127.0.0.1', 'localhost', '::1', '[::1]'])

export type AddressResult = { ok: true; address: string } | { ok: false; message: string }

export function checkLocalAddress(value: string): string | null {
    const separator = value.lastIndexOf(':')
    if (separator <= 0 || separator === value.length - 1) {
        return 'O endereco deve ter a forma host:porta e apontar para localhost (por exemplo 127.0.0.1:7233).'
    }
    const host = value.slice(0, separator)
    const port = Number(value.slice(separator + 1))
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
        return 'A porta deve ser um numero entre 1 e 65535; o piloto so roda contra um servidor local.'
    }
    if (!LOCAL_HOSTS.has(host)) {
        return `O host ${host} nao e localhost: o piloto so roda contra um servidor local.`
    }
    return null
}

/** Aceita zero argumentos ou exatamente --address <host:porta>; qualquer outra forma e recusada. */
export function resolveAddressArgument(argv: readonly string[]): AddressResult {
    if (argv.length === 0) return { ok: true, address: DEFAULT_PILOT_ADDRESS }
    if (argv.length === 2 && argv[0] === '--address' && !argv[1]?.startsWith('--')) {
        const problem = checkLocalAddress(argv[1] as string)
        return problem === null ? { ok: true, address: argv[1] as string } : { ok: false, message: problem }
    }
    return { ok: false, message: `Argumentos nao reconhecidos: ${argv.join(' ')}. A unica flag e --address <host:porta>.` }
}
