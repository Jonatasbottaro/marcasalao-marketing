// tenant.mjs — carga de identidade/guardrails do tenant e validacao textual.
// Parte do adaptador HyperFrames (HF-001, F5/F6). Fontes canonicas por tenant:
//   tenants/<id>/frame.md      (frontmatter normativo: cores, tipografia, headerOverlay, audio/captions)
//   tenants/<id>/brand-kit.json (tokens de marca consumidos pela fabrica/Studio)
//   tenants/<id>/guardrails.json (alegacoes proibidas, politica de audio)
// O frontmatter do frame.md e a verdade de marca para VIDEO; o brand-kit continua
// sendo o contrato de token da fabrica. Nenhum arquivo e alterado aqui.

import { readFileSync } from 'node:fs'
import path from 'node:path'

/** Extrai o bloco de frontmatter (entre os dois primeiros '---') do frame.md. */
export function extractFrontmatter(text) {
    const lines = text.split(/\r?\n/)
    if (lines[0] !== '---') return null
    const end = lines.indexOf('---', 1)
    if (end === -1) return null
    return lines.slice(1, end)
}

/** Converte valor literal do frontmatter: aspas, numero, booleano; comentarios apos # sao descartados. */
function parseScalar(raw) {
    let value = raw.trim()
    const hash = findCommentStart(value)
    if (hash !== -1) value = value.slice(0, hash).trim()
    if (value === '') return null
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        return value.slice(1, -1)
    }
    if (value === 'true') return true
    if (value === 'false') return false
    if (/^-?\d+(\.\d+)?$/.test(value)) return Number(value)
    return value
}

/** '#' so e comentario quando precedido de espaco (para nao cortar hex '#F5C107'). */
function findCommentStart(value) {
    for (let i = 1; i < value.length; i++) {
        if (value[i] === '#' && value[i - 1] === ' ') return i
    }
    return -1
}

/**
 * Parser simples de frontmatter YAML do frame.md: suporta 'key: valor' e um nivel
 * de indentacao (2 espacos). Suficiente para o bloco normativo conhecido; nao e
 * um parser YAML geral e rejeita estruturas mais profundas com valor em vez de erro.
 */
export function parseFrontmatter(text) {
    const lines = extractFrontmatter(text)
    if (!lines) return null
    const tree = {}
    let currentTop = null
    for (const line of lines) {
        if (line.trim() === '' || line.trim().startsWith('#')) continue
        const indented = /^ {2}(\S.*)$/.exec(line)
        const top = /^(\S[^:]*):\s*(.*)$/.exec(line)
        if (indented && currentTop) {
            const m = /^(\S[^:]*):\s*(.*)$/.exec(indented[1])
            if (!m) continue
            const value = parseScalar(m[2])
            if (value !== null) tree[currentTop][m[1]] = value
            continue
        }
        if (top) {
            const key = top[1].trim()
            if (top[2].trim() === '') {
                tree[key] = {}
                currentTop = key
            } else {
                const value = parseScalar(top[2])
                tree[key] = value === null ? {} : value
                currentTop = typeof tree[key] === 'object' && !Array.isArray(tree[key]) ? key : null
            }
        }
    }
    return tree
}

/** Carrega identidade + guardrails do tenant. Falha (throw) se qualquer pilar ausir. */
export function loadTenant(root, tenantId) {
    if (!/^[a-z0-9-]+$/.test(tenantId)) {
        throw new Error(`TENANT_ID_INVALID: ${tenantId}`)
    }
    const tenantDir = path.resolve(root, 'tenants', tenantId)
    const framePath = path.join(tenantDir, 'frame.md')
    const kitPath = path.join(tenantDir, 'brand-kit.json')
    const guardrailsPath = path.join(tenantDir, 'guardrails.json')
    let frameText
    let brandKit
    let guardrails
    try {
        frameText = readFileSync(framePath, 'utf8')
        brandKit = JSON.parse(readFileSync(kitPath, 'utf8'))
        guardrails = JSON.parse(readFileSync(guardrailsPath, 'utf8'))
    } catch {
        throw new Error(`TENANT_FILES_MISSING: ${tenantId} (frame.md/brand-kit.json/guardrails.json)`)
    }
    const frame = parseFrontmatter(frameText)
    if (!frame || typeof frame !== 'object') {
        throw new Error(`FRAME_FRONTMATTER_INVALID: ${tenantId}`)
    }
    return { tenantId, tenantDir, frame, brandKit, guardrails }
}

/**
 * Tokens de video efetivos: frame.md manda; brand-kit cobre lacunas.
 * Exige o minimo para compor (cores de fundo/texto e headerOverlay).
 */
export function resolveVideoTokens(tenant) {
    const frame = tenant.frame
    const kit = tenant.brandKit
    const colors = frame.colors ?? {}
    const header = frame.components?.headerOverlay ?? kit.headerOverlay ?? {}
    const tokens = {
        background: colors.background ?? kit.palette?.background ?? '#121620',
        surface: colors.surface ?? kit.palette?.surface ?? '#222C40',
        primary: colors.primary ?? kit.palette?.primary ?? '#F5C107',
        secondary: colors.secondary ?? kit.palette?.secondary ?? '#4F8CFF',
        accent: colors.accent ?? kit.palette?.accent ?? '#28B463',
        textPrimary: colors.textPrimary ?? kit.palette?.textPrimary ?? '#F5F7FA',
        textMuted: colors.textMuted ?? kit.palette?.textMuted ?? '#B4C0D2',
        fontFamily: frame.typography?.fontFamily ?? kit.typography?.fontFamily ?? 'Arial',
        titleWeight: frame.typography?.titleWeight ?? kit.typography?.titleWeight ?? 'bold',
        bodyWeight: frame.typography?.bodyWeight ?? kit.typography?.bodyWeight ?? 'bold',
        headerHeight: frame.spacing?.headerHeight ?? header.height ?? 170,
        header: {
            enabled: header.enabled ?? true,
            label: header.label ?? kit.displayTitle ?? 'MARCA SALAO',
            badge: header.badge ?? header.badgeText ?? kit.tagline ?? '',
            bg: header.bg ?? header.bgColor ?? '#0E121C',
            text: header.text ?? header.textColor ?? '#F5F7FA',
        },
        audio: frame.audio ?? { allowAudioTrack: false },
        captions: frame.captions ?? { standard: 'clean' },
    }
    if (tokens.audio.allowAudioTrack === true) {
        throw new Error(`AUDIO_POLICY_VIOLATION: frame.md do tenant ${tenant.tenantId} permite faixa de audio; o adaptador so produz VIDEO CLEAN`)
    }
    return tokens
}

function normalizeText(value) {
    return String(value ?? '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
}

/**
 * Valida textos do pedido contra as alegacoes proibidas do guardrails.json.
 * Varre caption (texto em tela), title (titulo sobreposto) e narration (roteiro
 * externo): todos sao comunicacao publica da campanha.
 * Retorna lista de violacoes {term, field, sceneId, text}; vazio = ok.
 */
export function validateGuardrails(tenant, beats) {
    const forbidden = (tenant.guardrails.forbiddenClaims ?? []).map((term) => ({
        term,
        needle: normalizeText(term),
    })).filter((entry) => entry.needle.length > 0)
    const violations = []
    for (const beat of beats) {
        const fields = [
            ['caption', beat.caption],
            ['title', beat.title],
            ['narration', beat.narration],
        ]
        for (const [field, raw] of fields) {
            const haystack = normalizeText(raw)
            if (!haystack) continue
            for (const { term, needle } of forbidden) {
                if (haystack.includes(needle)) {
                    violations.push({ term, field, sceneId: beat.beatId, text: String(raw) })
                }
            }
        }
    }
    return violations
}
