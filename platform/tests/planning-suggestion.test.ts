/**
 * Testes unitarios do validador puro PlanningSuggestion v1 ('briefing' e 'creative').
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'

import { validatePlanningSuggestion } from '../src/validate-planning-suggestion.js'
import { moduleRoot } from './contract-harness.js'

function loadProject(name: string): Record<string, unknown> {
    return JSON.parse(readFileSync(path.join(moduleRoot, 'examples', 'projects', name), 'utf8')) as Record<string, unknown>
}

function validBriefingSuggestion(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        stage: 'briefing',
        product: 'Agenda Marca Salao',
        objective: 'Demonstrar organizacao de horarios na agenda digital',
        audience: 'Gestores e donos de saloes de beleza',
        coreMessage: 'Visualize horarios por profissional e reduza erros na recepcao',
        supportEvidence: 'Tela real da agenda com filtros por profissional',
        cta: 'Conheca o Marca Salao',
        tone: 'Objetivo, pratico e claro',
        recommendedProfiles: ['instagram-reels-video', 'instagram-feed-image-square'],
        gaps: ['Confirmar se URL de destino final deve apontar para demonstracao'],
        questions: [
            {
                id: 'q-publico',
                dimension: 'audience',
                question: 'O foco principal e recepcao ou gestor do salao?',
                suggestedAnswer: 'Gestor e recepcao de saloes com 3 ou mais profissionais',
            },
        ],
        claims: [
            {
                id: 'c-agenda',
                statement: 'Visualizacao clara dos horarios em uma tela unica',
                status: 'confirmed',
                requiresConfirmation: false,
                evidenceMediaId: 'agenda',
            },
            {
                id: 'c-tempo',
                statement: 'Economia de tempo no fechamento do dia',
                status: 'pending_validation',
                requiresConfirmation: true,
                warning: 'Afirmacao comercial sem medicao anexada; validar antes de aprovar.',
            },
        ],
    }
}

function validCreativeSuggestion(): Record<string, unknown> {
    return {
        schemaVersion: 1,
        stage: 'creative',
        hookOptions: [
            { id: 'hook-1', text: 'Agenda cheia sem confusao na recepcao', angle: 'clareza' },
            { id: 'hook-2', text: 'Como organizar horarios de toda a equipe em segundos', angle: 'organizacao' },
        ],
        selectedHookId: 'hook-1',
        scriptSummary: 'Abertura com problema da recepcao, demonstracao na tela da agenda e fechamento neutro.',
        videoScenes: [
            {
                id: 'cena-abertura',
                objective: 'Apresentar dor de agenda confusa',
                narrativeFunction: 'hook',
                durationMs: 4000,
                titleOverlay: 'Agenda organizada em segundos',
                caption: 'Agenda cheia sem confusao na recepcao',
                narration: 'Quem cuida da recepcao sabe como um horario solto atrapalha o dia inteiro.',
                requiredMediaDescriptor: 'Tela de abertura com titulo de campanha',
                motionIntent: 'none',
            },
            {
                id: 'cena-agenda',
                objective: 'Mostrar blocos por profissional',
                narrativeFunction: 'demonstration',
                durationMs: 5000,
                titleOverlay: 'Horarios por profissional',
                caption: 'Veja cada profissional e servico com clareza',
                narration: 'No painel visual voce enxerga cada atendimento sem perder tempo.',
                requiredMediaDescriptor: 'Captura da agenda digital com slots visiveis',
                mediaId: 'agenda',
                motionIntent: 'none',
            },
        ],
        carouselCards: [
            {
                id: 'capa',
                role: 'cover',
                title: 'Agenda organizada sem confusao',
                body: 'Veja como estruturar o dia da equipe',
                requiredMediaDescriptor: 'Arte limpa de capa',
            },
            {
                id: 'conteudo-1',
                role: 'content',
                title: 'Visao por profissional',
                body: 'Blocos claros evitam conflitos de horario',
                mediaId: 'agenda',
            },
            {
                id: 'fechamento',
                role: 'cta',
                title: 'Conheca o Marca Salao',
                body: 'Acesse os detalhes no canal indicado',
            },
        ],
        channelCopies: [
            {
                profileId: 'instagram-reels-video',
                title: 'Agenda organizada sem confusao',
                postText: 'Mostramos como a visao por profissional ajuda a recepcao. Confira no link da bio.',
                cta: 'Acesse o link da bio',
                destinationUrl: 'https://marcasalao.com.br',
                hashtags: '#marcasalao #gestaodesalao',
                flags: ['Confirmar link ativo na bio antes da publicacao'],
            },
            {
                profileId: 'instagram-feed-image-square',
                title: 'Carrossel agenda organizada',
                postText: 'Deslize para ver os passos principais de organizacao da agenda.',
                cta: 'Confira no link da bio',
                destinationUrl: 'https://marcasalao.com.br',
                hashtags: '#marcasalao',
            },
        ],
        motionSuggestions: [
            {
                sceneId: 'cena-agenda',
                targetElement: 'Bloco principal da agenda do dia',
                suggestedColor: '#FFD700',
                suggestedStartMs: 500,
                suggestedEndMs: 3000,
                note: 'Destacar o bloco apos marcar a regiao manualmente no editor Motion.',
            },
        ],
    }
}

test('aceita etapas briefing e creative com ProjectManifest Marca Salao e Multitrack Hub', () => {
    const marcaSalao = loadProject('marca-salao-social.project.json')
    const multitrack = loadProject('multitrack-hub-social.project.json')

    const b1 = validatePlanningSuggestion(validBriefingSuggestion(), marcaSalao)
    assert.ok(b1.ok, b1.ok ? '' : b1.message)

    const c1 = validatePlanningSuggestion(validCreativeSuggestion(), marcaSalao)
    assert.ok(c1.ok, c1.ok ? '' : c1.message)

    const b2 = validatePlanningSuggestion(validBriefingSuggestion(), multitrack)
    assert.ok(b2.ok, b2.ok ? '' : b2.message)
})

test('rejeita perfil fora da allowlist do projeto ou inexistente no catalogo', () => {
    const multitrack = loadProject('multitrack-hub-social.project.json')

    const outOfProject = validBriefingSuggestion()
    outOfProject.recommendedProfiles = ['youtube-video-horizontal']
    const res1 = validatePlanningSuggestion(outOfProject, multitrack)
    assert.equal(res1.ok, false)
    if (!res1.ok) assert.equal(res1.failureCode, 'PLANNING_PROFILE_NOT_ALLOWED')

    const unknownCatalog = validCreativeSuggestion()
    ;(unknownCatalog.channelCopies as Array<Record<string, unknown>>)[0] = {
        profileId: 'rede-inexistente-9x16',
        title: 'Teste',
        postText: 'Texto teste',
        cta: 'CTA teste',
        destinationUrl: '',
        hashtags: '',
    }
    const res2 = validatePlanningSuggestion(unknownCatalog, multitrack)
    assert.equal(res2.ok, false)
    if (!res2.ok) assert.equal(res2.failureCode, 'PLANNING_PROFILE_NOT_ALLOWED')
})

test('rejeita campos desconhecidos, selectedHookId inexistente e motionSuggestions em cena com zoom', () => {
    const unknown = { ...validBriefingSuggestion(), extraField: true }
    const rUnknown = validatePlanningSuggestion(unknown)
    assert.equal(rUnknown.ok, false)
    if (!rUnknown.ok) assert.equal(rUnknown.failureCode, 'PLANNING_SUGGESTION_UNKNOWN_FIELD')

    const badHook = { ...validCreativeSuggestion(), selectedHookId: 'hook-inexistente' }
    const rHook = validatePlanningSuggestion(badHook)
    assert.equal(rHook.ok, false)
    if (!rHook.ok) assert.equal(rHook.failureCode, 'PLANNING_SELECTED_HOOK_UNKNOWN')

    const movingScene = validCreativeSuggestion()
    const scenes = movingScene.videoScenes as Array<Record<string, unknown>>
    scenes[1] = { ...scenes[1], motionIntent: 'slow-zoom' }
    const rMotion = validatePlanningSuggestion(movingScene)
    assert.equal(rMotion.ok, false)
    if (!rMotion.ok) assert.equal(rMotion.failureCode, 'PLANNING_MOTION_SCENE_MOVING')

    const unknownSceneMotion = validCreativeSuggestion()
    unknownSceneMotion.motionSuggestions = [{ sceneId: 'cena-ausente', targetElement: 'Botao' }]
    const rUnknownScene = validatePlanningSuggestion(unknownSceneMotion)
    assert.equal(rUnknownScene.ok, false)
    if (!rUnknownScene.ok) assert.equal(rUnknownScene.failureCode, 'PLANNING_MOTION_SCENE_UNKNOWN')

    const invertedWindow = validCreativeSuggestion()
    invertedWindow.motionSuggestions = [{
        sceneId: 'cena-agenda',
        targetElement: 'Bloco',
        suggestedStartMs: 2500,
        suggestedEndMs: 1000,
    }]
    const rInv = validatePlanningSuggestion(invertedWindow)
    assert.equal(rInv.ok, false)
    if (!rInv.ok) assert.equal(rInv.failureCode, 'PLANNING_MOTION_SUGGESTION_INVALID')
})
