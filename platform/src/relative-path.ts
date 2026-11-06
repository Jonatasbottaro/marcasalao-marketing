/**
 * Validacao lexica compartilhada de caminhos relativos: usada pelo ProjectManifest
 * (`assetRoot`) e pela Composition (`content.asset.path`).
 *
 * Pureza: recebe uma string e devolve as violacoes encontradas, em ordem fixa. Nao le
 * arquivos, nao acessa rede, nao verifica existencia fisica e nao conhece nenhum
 * projeto. Cada contrato traduz as violacoes para os proprios codigos e caminhos de
 * erro, entao o mesmo problema produz PROJECT_ASSET_ROOT_* ou COMPOSITION_ASSET_PATH_*.
 *
 * Os nomes sensiveis sao comparados por segmento, nome e extensao (nunca por substring
 * do caminho inteiro): "assets/secretaria" e "assets/secretaria.png" sao caminhos
 * comuns e validos, enquanto ".env", ".env.local", ".git", chaves privadas e
 * credenciais continuam proibidos.
 */

export type RelativePathViolation =
    | 'CONTROL_CHARACTER'
    | 'ABSOLUTE'
    | 'URL'
    | 'TRAVERSAL'
    | 'SENSITIVE'

const CONTROL_CHARACTER_PATTERN = /[\u0000-\u001F\u007F]/
const WINDOWS_DRIVE_PATTERN = /^[A-Za-z]:[\\/]/
const URL_SCHEME_PATTERN = /^[A-Za-z][A-Za-z0-9+.-]*:/
const TRAVERSAL_SEGMENT = '..'

/** Nomes pontados proibidos como segmento inteiro (ou prefixo de ".nome.extensao"). */
const PROTECTED_DOT_NAMES = ['.env', '.git'] as const

/** Nomes de segmento que identificam chave ou credencial (comparacao exata, minuscula). */
const PROTECTED_SEGMENT_NAMES = [
    'privatekey',
    'serviceaccount',
    'credential',
    'credentials',
    'secret',
    'secrets',
    'password',
    'passwords',
] as const

/** Extensoes de chave privada/certificado. */
const PROTECTED_EXTENSIONS = ['.pem', '.key', '.p12', '.pfx'] as const

/** Prefixos de nome de chave SSH previstos no contrato. */
const PROTECTED_KEY_PREFIXES = ['id_rsa', 'id_ecdsa', 'id_ed25519'] as const

/** Segmentos separados por qualquer um dos dois separadores suportados. */
export function pathSegments(value: string): string[] {
    return value.split(/[\\/]/).filter((segment) => segment.length > 0)
}

export function containsControlCharacter(value: string): boolean {
    return CONTROL_CHARACTER_PATTERN.test(value)
}

/** Nome do segmento sem a ultima extensao, em minusculas. */
function segmentBaseName(segment: string): string {
    const lower = segment.toLowerCase()
    const dot = lower.lastIndexOf('.')
    return dot > 0 ? lower.slice(0, dot) : lower
}

function isProtectedName(name: string): boolean {
    if ((PROTECTED_SEGMENT_NAMES as readonly string[]).includes(name)) return true
    return name
        .split(/[._-]/)
        .some((token) => token.length > 0 && (PROTECTED_SEGMENT_NAMES as readonly string[]).includes(token))
}

function isSensitiveSegment(segment: string): boolean {
    const lower = segment.toLowerCase()

    for (const dotName of PROTECTED_DOT_NAMES) {
        if (lower === dotName || lower.startsWith(`${dotName}.`)) return true
    }
    if (PROTECTED_EXTENSIONS.some((extension) => lower.endsWith(extension))) return true
    if (PROTECTED_KEY_PREFIXES.some((prefix) => lower.startsWith(prefix))) return true

    const base = segmentBaseName(segment)
    return isProtectedName(base) || isProtectedName(base.replace(/[._-]/g, ''))
}

/**
 * Classificacao lexica de um caminho relativo. ABSOLUTE e URL sao mutuamente
 * exclusivos e avaliados nesta ordem: protocol-relative (`//`), absoluto POSIX,
 * barras invertidas/UNC e letra de unidade Windows antes de qualquer protocolo.
 */
export function inspectRelativePath(value: string): RelativePathViolation[] {
    const violations: RelativePathViolation[] = []

    if (containsControlCharacter(value)) violations.push('CONTROL_CHARACTER')

    if (value.startsWith('//')) {
        violations.push('URL')
    } else if (value.startsWith('/') || value.startsWith('\\') || WINDOWS_DRIVE_PATTERN.test(value)) {
        violations.push('ABSOLUTE')
    } else if (URL_SCHEME_PATTERN.test(value)) {
        violations.push('URL')
    }

    const segments = pathSegments(value)
    if (segments.some((segment) => segment === TRAVERSAL_SEGMENT)) violations.push('TRAVERSAL')
    if (segments.some((segment) => isSensitiveSegment(segment))) violations.push('SENSITIVE')

    return violations
}
