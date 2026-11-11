/**
 * Entrada compartilhada das CLIs de saida sociais (`content:profiles` e
 * `content:plan-output`).
 *
 * So ha aqui o que as duas CLIs realmente fazem juntas: ler flags, ler um JSON
 * do disco e formatar um diagnostico. Decisao de catalogo, de plano ou de
 * compatibilidade nunca mora neste arquivo — quem precisa de regra nova continua
 * nas funcoes puras, e a CLI apenas apresenta o resultado delas.
 */

import { readFileSync } from 'node:fs'

import {
    OUTPUT_MEDIA_KINDS,
    OUTPUT_NETWORKS,
    OUTPUT_PUBLICATIONS,
    RULE_CONTEXTS,
} from './output-profiles/types.js'
import type {
    OutputMediaKind,
    OutputNetwork,
    OutputPublication,
    RuleContext,
} from './output-profiles/types.js'
import type { ValidationIssue } from './validation-report.js'

/** Exit codes do pacote: 0 valido, 1 documento legivel porem incompativel, 2 uso. */
export const EXIT_VALID = 0
export const EXIT_INVALID = 1
export const EXIT_USAGE = 2

export interface ParsedFlags {
    /** Valores recebidos, por nome de flag sem o prefixo `--`. */
    readonly values: Record<string, string>
    readonly json: boolean
    /** Motivo sanitizado do erro de uso; `null` quando a entrada e utilizavel. */
    readonly error: string | null
}

/**
 * Le `--flag valor` e `--json`. Enum desconhecido e valor invalido sao da CLI
 * que chama (ela conhece os proprios filtros); aqui a entrada e estrutura:
 * flag repetida, flag estranha, valor solto e valor ausente viram erro de uso.
 */
export function parseFlags(argv: readonly string[], valueFlags: readonly string[]): ParsedFlags {
    const values: Record<string, string> = {}
    let json = false

    for (let index = 0; index < argv.length; index++) {
        const arg = argv[index] as string

        if (arg === '--json') {
            if (json) return { values, json, error: `flag duplicada: ${arg}` }
            json = true
            continue
        }

        if (!arg.startsWith('--')) {
            return { values, json, error: `argumento sem flag: ${arg}` }
        }

        if (!(valueFlags as readonly string[]).includes(arg)) {
            return { values, json, error: `flag desconhecida: ${arg}` }
        }

        const name = arg.slice(2)
        if (values[name] !== undefined) {
            return { values, json, error: `flag duplicada: ${arg}` }
        }

        const value = argv[index + 1]
        if (value === undefined || value.startsWith('--')) {
            return { values, json, error: `valor ausente para a flag: ${arg}` }
        }

        values[name] = value
        index++
    }

    return { values, json, error: null }
}

export type JsonFileRead = { value: unknown } | { error: string }
/** Le e interpreta um JSON sem deixiar vazar stack trace nem conteudo do arquivo. */
export function readJsonFile(filePath: string): JsonFileRead {
    let rawContent: string
    try {
        rawContent = readFileSync(filePath, 'utf8')
    } catch {
        return { error: `Erro: arquivo nao encontrado ou ilegivel: ${filePath}` }
    }

    try {
        return { value: JSON.parse(rawContent) as unknown }
    } catch {
        return { error: `Erro: JSON malformado em: ${filePath}` }
    }
}

/** Lista de enum para mensagem: `"instagram", "facebook", "youtube"`. */
export function enumLabel(values: readonly string[]): string {
    return values.map((value) => `"${value}"`).join(', ')
}

/** Filtros de catalogo e de contexto, ja validados contra os enums de runtime. */
export interface CliFilters {
    readonly network: OutputNetwork | null
    readonly publication: OutputPublication | null
    readonly mediaKind: OutputMediaKind | null
    readonly ruleContext: RuleContext | null
}

/**
 * Os filtros das duas CLIs sao lidos uma so vez, aqui: valor fora do enum e erro
 * de uso (a pessoa digitou uma opcao que nao existe), nunca um filtro silencioso
 * que devolveria uma lista menor. `ruleContext` so existe na CLI de plano; sem
 * `--rule-context` o contexto fica nulo, que e "ausente", jamais "sem contexto"
 * como string.
 */
export function readFilters(values: Record<string, string>, withRuleContext: boolean): CliFilters | { error: string } {
    const network = readEnum('network', '--network', values, OUTPUT_NETWORKS)
    if ('error' in network) return network

    const publication = readEnum('publication', '--publication', values, OUTPUT_PUBLICATIONS)
    if ('error' in publication) return publication

    const mediaKind = readEnum('media', '--media', values, OUTPUT_MEDIA_KINDS)
    if ('error' in mediaKind) return mediaKind

    if (!withRuleContext) {
        return { network: network.value, publication: publication.value, mediaKind: mediaKind.value, ruleContext: null }
    }

    if (values['rule-context'] !== undefined && !(RULE_CONTEXTS as readonly string[]).includes(values['rule-context'] as string)) {
        return { error: `--rule-context deve ser um de ${enumLabel(RULE_CONTEXTS)}` }
    }

    return {
        network: network.value,
        publication: publication.value,
        mediaKind: mediaKind.value,
        ruleContext: values['rule-context'] === undefined ? null : values['rule-context'] as RuleContext,
    }
}

/** `value` e o filtro estreitado (ou `null` quando ausente); `error` e a mensagem de uso. */
type EnumRead<T extends string> = { value: T | null } | { error: string }

function readEnum<T extends string>(
    key: string,
    flag: string,
    values: Record<string, string>,
    allowed: readonly T[],
): EnumRead<T> {
    if (values[key] === undefined) return { value: null }
    if (!(allowed as readonly string[]).includes(values[key] as string)) {
        return { error: `${flag} deve ser um de ${enumLabel(allowed)}` }
    }
    return { value: values[key] as T }
}

/** Um diagnostico por linha, com o caminho logico do campo. */
export function formatIssue(item: ValidationIssue): string {
    return `  ${item.code} @${item.path}: ${item.message}`
}
