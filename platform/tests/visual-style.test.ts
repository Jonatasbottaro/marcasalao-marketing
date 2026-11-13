/**
 * Testes unitarios do VisualStyle v1 (contrato, validacao pura e serializacao).
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { serializeVisualStyle } from '../src/serialize-visual-style.js'
import { validateVisualStyle } from '../src/validate-visual-style.js'
import type { VisualStyle } from '../src/visual-style-contract.js'

test('validacao semantica: rejeita entrada nao-objeto ou nula', () => {
    assert.deepEqual(validateVisualStyle(null), { ok: false, failureCode: 'STYLE_INVALID', subject: null })
    assert.deepEqual(validateVisualStyle('texto'), { ok: false, failureCode: 'STYLE_INVALID', subject: null })
    assert.deepEqual(validateVisualStyle([]), { ok: false, failureCode: 'STYLE_INVALID', subject: null })
})

test('validacao semantica: rejeita campos desconhecidos no objeto de topo', () => {
    const invalid = {
        schemaVersion: 1,
        id: 'estilo-padrao',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 160,
            marginHorizontal: 60,
        },
        extraField: true,
    }
    assert.deepEqual(validateVisualStyle(invalid), { ok: false, failureCode: 'STYLE_INVALID', subject: null })
})

test('validacao semantica: rejeita schemaVersion diferente de 1', () => {
    const invalid = {
        schemaVersion: 2,
        id: 'estilo-padrao',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 160,
            marginHorizontal: 60,
        },
    }
    assert.deepEqual(validateVisualStyle(invalid), { ok: false, failureCode: 'STYLE_INVALID', subject: 'schemaVersion' })
})

test('validacao semantica: rejeita id ausente ou nao kebab-case', () => {
    const invalidId = {
        schemaVersion: 1,
        id: 'Estilo Invalido',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 160,
            marginHorizontal: 60,
        },
    }
    assert.deepEqual(validateVisualStyle(invalidId), { ok: false, failureCode: 'STYLE_ID_INVALID', subject: 'Estilo Invalido' })

    const emptyId = {
        schemaVersion: 1,
        id: '',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 160,
            marginHorizontal: 60,
        },
    }
    assert.deepEqual(validateVisualStyle(emptyId), { ok: false, failureCode: 'STYLE_ID_INVALID', subject: '' })
})

test('validacao semantica: rejeita secao title com campos desconhecidos ou faltantes', () => {
    const missingField = {
        schemaVersion: 1,
        id: 'estilo-padrao',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 160,
        },
    }
    assert.deepEqual(validateVisualStyle(missingField), { ok: false, failureCode: 'STYLE_TITLE_INVALID', subject: null })

    const extraTitleField = {
        schemaVersion: 1,
        id: 'estilo-padrao',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 160,
            marginHorizontal: 60,
            shadowColor: '#000000',
        },
    }
    assert.deepEqual(validateVisualStyle(extraTitleField), { ok: false, failureCode: 'STYLE_TITLE_INVALID', subject: null })
})

test('validacao semantica: rejeita cores hexadecimais invalidas', () => {
    const invalidTextColor = {
        schemaVersion: 1,
        id: 'estilo-padrao',
        title: {
            textColor: '#ZZZZZZ',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 160,
            marginHorizontal: 60,
        },
    }
    assert.deepEqual(validateVisualStyle(invalidTextColor), { ok: false, failureCode: 'STYLE_COLOR_INVALID', subject: 'title.textColor' })

    const invalidOutlineColor = {
        schemaVersion: 1,
        id: 'estilo-padrao',
        title: {
            textColor: '#FFFFFF',
            outlineColor: 'black',
            fontSize: 42,
            marginTop: 160,
            marginHorizontal: 60,
        },
    }
    assert.deepEqual(validateVisualStyle(invalidOutlineColor), { ok: false, failureCode: 'STYLE_COLOR_INVALID', subject: 'title.outlineColor' })
})

test('validacao semantica: rejeita fontSize fora dos limites ou nao-inteiro', () => {
    const tooSmall = {
        schemaVersion: 1,
        id: 'estilo-padrao',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 10,
            marginTop: 160,
            marginHorizontal: 60,
        },
    }
    assert.deepEqual(validateVisualStyle(tooSmall), { ok: false, failureCode: 'STYLE_FONT_SIZE_INVALID', subject: 'title.fontSize' })

    const notInteger = {
        schemaVersion: 1,
        id: 'estilo-padrao',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42.5,
            marginTop: 160,
            marginHorizontal: 60,
        },
    }
    assert.deepEqual(validateVisualStyle(notInteger), { ok: false, failureCode: 'STYLE_FONT_SIZE_INVALID', subject: 'title.fontSize' })
})

test('validacao semantica: rejeita margens fora dos limites', () => {
    const topTooBig = {
        schemaVersion: 1,
        id: 'estilo-padrao',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 800,
            marginHorizontal: 60,
        },
    }
    assert.deepEqual(validateVisualStyle(topTooBig), { ok: false, failureCode: 'STYLE_MARGIN_INVALID', subject: 'title.marginTop' })

    const horizontalTooBig = {
        schemaVersion: 1,
        id: 'estilo-padrao',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 160,
            marginHorizontal: 450,
        },
    }
    assert.deepEqual(validateVisualStyle(horizontalTooBig), { ok: false, failureCode: 'STYLE_MARGIN_INVALID', subject: 'title.marginHorizontal' })
})

test('serializacao canonica e deterministica com normalizacao de cores hex', () => {
    const input = {
        schemaVersion: 1,
        id: 'marca-salao-ouro',
        title: {
            textColor: '#ffd700',
            outlineColor: '#1a1a1a',
            fontSize: 48,
            marginTop: 180,
            marginHorizontal: 80,
        },
    }
    const result = validateVisualStyle(input)
    assert.ok(result.ok)

    const expectedStyle: VisualStyle = {
        schemaVersion: 1,
        id: 'marca-salao-ouro',
        title: {
            textColor: '#FFD700',
            outlineColor: '#1A1A1A',
            fontSize: 48,
            marginTop: 180,
            marginHorizontal: 80,
        },
    }
    assert.deepEqual(result.style, expectedStyle)

    const serialized = serializeVisualStyle(result.style)
    const expectedJson = [
        '{',
        '  "schemaVersion": 1,',
        '  "id": "marca-salao-ouro",',
        '  "title": {',
        '    "textColor": "#FFD700",',
        '    "outlineColor": "#1A1A1A",',
        '    "fontSize": 48,',
        '    "marginTop": 180,',
        '    "marginHorizontal": 80',
        '  }',
        '}',
        '',
    ].join('\n')

    assert.strictEqual(serialized, expectedJson)
})

test('reuso entre casos: um mesmo VisualStyle nao depende de caseId', () => {
    const styleData = {
        schemaVersion: 1,
        id: 'shared-brand-style',
        title: {
            textColor: '#FFFFFF',
            outlineColor: '#000000',
            fontSize: 42,
            marginTop: 160,
            marginHorizontal: 60,
        },
    }
    const result = validateVisualStyle(styleData)
    assert.ok(result.ok)
    assert.strictEqual(result.style.id, 'shared-brand-style')
    // O contrato do VisualStyle nao contem caseId, podendo ser utilizado em qualquer caso de pipeline.
    assert.strictEqual('caseId' in (result.style as unknown as Record<string, unknown>), false)
})
