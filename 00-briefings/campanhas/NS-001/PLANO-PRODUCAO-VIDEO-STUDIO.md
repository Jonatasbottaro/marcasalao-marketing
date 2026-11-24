# Plano de produção no Video Studio + qualidade audiovisual — NS-001 (24/11/2026)

Natureza: **pré-produção**. Nenhum render publicitário final, nenhuma aprovação técnica registrada como editorial, nenhuma fixture transformada em campanha. Comandos confirmados contra o código atual antes da execução.

## 1. Validação de ambiente (executada, somente diagnóstico)

`python tools/video_studio.py --check --json` → exit 0, `ready: true`:
- Python 3.13.15 ok; Node v24.19.0 ok; build da platform (TypeScript) ok; FFmpeg/FFprobe 9.1-essentials ok (cópia portátil em `.workspace/tools/ffmpeg/`).
- `frontendBuild.ok: false` (manifest Vite ausente nesta estação) — não bloqueia `--plan-only` nem a produção por CLI; registrar para build do painel se a UI for usada.
- Evidência: `.workspace/tmp/ns-001-etapa2/studio-check.json`.

`python tools/produce_video.py --input tools/produce/examples/marca-salao-ns-001-p001.video-request.json --plan-only --json` → exit 0, `status: preview`:
- requestId `marca-salao-ns-001-p001`; 7 mídias de cena (`cena-01-hook` … `cena-07-cta`); 3 perfis: `instagram-reels-video`, `facebook-reels-video`, `youtube-shorts`, 30 fps, **30 000 ms** cada.
- Evidência: `.workspace/tmp/ns-001-etapa2/plan-p001.json`.
- O template é referência técnica (prova P001 sintética). **Não** será publicado nem tratado como campanha.

## 2. Pedido de produção previsto (proposta, não criado)

- Identificador estável da peça: **NS-001-P001**, variante `v1`.
- requestId proposto: `marca-salao-ns-001-p001-editorial-v1` (kebab-case, VideoRequest v1).
- Divergência de tempo registrada: template técnico = 30 s; storyboard editorial proposto = **47 s** (leitura cronometrada). O novo pedido usará os tempos abaixo; o template permanece intacto.

| Cena | mediaId proposto | durationMs | sourceStartMs | Conteúdo |
| --- | --- | --- | --- | --- |
| 1 | ns001-c1-abertura | 5000 | 0 | Arte de fundo + pergunta (H15 revisado) |
| 2 | ns001-c2-situacao | 11000 | 0 | Ilustração condicional de fontes espalhadas |
| 3 | ns001-c3-visoes | 8500 | a definir na gravação | Gravação real Dia→Semana→Mês |
| 4 | ns001-c4-filtros | 6500 | a definir | Filtros + busca |
| 5 | ns001-c5-detalhes | 7500 | a definir | Modal de detalhes |
| 6 | ns001-c6-confirmar | 5500 | a definir | Confirmação manual + persistência |
| 7 | ns001-c7-cta | 3000 | 0 | Arte de CTA neutra + domínio |

- Perfis de saída: os três existentes do catálogo (sem perfis paralelos).
- Mídias necessárias: 4 gravações reais (cenas 3–6, fixture editorial) + 3 artes (1, 2, 7). Todas **pendentes** de aprovação e produção.
- Estilo visual: conforme recomendação da auditoria de identidade (opção A), pendente de decisão.
- Transições: corte seco / crossfade ≤ 0,3 s; `framingByProfile` para derivados 1:1/16:9.
- Regras de texto: textos de tela do storyboard; legendas queimadas do SRT aprovado; Arial bold conforme contrato ASS; áreas seguras declaradas.
- Plano de SRT: `04-legendas/ns001_roteiro_001.srt` preliminar → recalculado contra a gravação real → validado (ferramenta de SRT do projeto) antes do render.
- Plano de narração externa: `04-legendas/ns001_roteiro_001_narracao.txt` entregue ao titular; áudio gerado fora do editor; composição final **sem faixa de áudio** (`-an`).
- Local de exportação: `.workspace/` da estação (deliveries por perfil com manifestos, `index.json`, hashes); pacote ZIP só após revisão humana.
- Verificações de qualidade: seção 3 abaixo + `delivery_verify` + `ffprobe` (0 faixas de áudio).
- Política de aprovação: nada renderiza como peça final antes de briefing+hook+roteiro+textos aprovados; aprovação técnica de pacote ≠ aprovação editorial.

## 3. Plano de qualidade audiovisual (critérios; executar só o compatível com o estado atual)

### Imagem
- [ ] Formato conforme perfil (1080×1920, 30 fps, H.264).
- [ ] Enquadramento 9:16 sem corte de conteúdo essencial; recorte exclui sidebar "Meu Salão" até decisão de nome.
- [ ] Controles da interface legíveis a 1080×1920.
- [ ] Texto sem sobreposição; fora das áreas de UI social (topo ~150 px, direita ~120 px, base ~250 px).
- [ ] Marca consistente com a identidade decidida.
- [ ] Capturas sem informações sensíveis; sem identificadores E2E; sem preço de R$ 12.000,00.

### Vídeo
- [ ] Duração coerente com o roteiro aprovado (47 s propostos; conferir contra montagem).
- [ ] Transições não excessivas; cadência clara; sem telas em branco, duplicação de cenas, congelamentos ou mudança de proporção.
- [ ] Sem efeitos que distorçam o funcionamento real do produto.

### Áudio
- [ ] **Zero faixas de áudio** na exportação (`ffprobe`); proibido substituir por faixa silenciosa.
- [ ] Narração apenas como texto separado; nenhum TTS/música/efeito gerado no editor.

### Legendas
- [ ] Sem sobreposições; ≤ 2 linhas por cue; linhas ≤ ~45 caracteres.
- [ ] Sincronizadas com o vídeo final (recálculo pós-gravação).
- [ ] Pontuação correta; contraste adequado; terminologia consistente; SRT válido.

### Entrega
- [ ] MP4 + SRT + narração TXT + manifestos + hashes + pacote ZIP + evidência de validação + estado editorial registrados.
- [ ] `delivery_verify` aprovado; revisão humana antes de qualquer publicação manual.

## 4. QA editorial automatizado (FASE 12 — executado sem alterar regras)

`python tools/editorial_qa.py --strict --json` → exit 0, `ok: true`, **14 campanhas auditadas, 0 problemas**, incluindo `marca-salao/camp-saas-demo-ns001-agenda-001`. Evidência: `.workspace/tmp/ns-001-etapa2/editorial-qa.json`.

Alcance do QA: contratos JSON de campanha dos tenants. Os documentos editoriais novos desta rodada foram auditados manualmente (auditoria editorial + matriz de veracidade); achados classificados:

| Achado | Severidade |
| --- | --- |
| Ausência de aprovações editoriais (briefing/hook/roteiro/textos/CTA/identidade) | Bloqueante (decisão do titular) |
| Capturas técnicas impróprias como frames; fixture editorial inexistente; produto sem revalidação | Necessita ajuste (antes da gravação) |
| Texto de tela da cena 2 longo; narração da cena 5 em frase única | Recomendação (propostas rastreáveis no storyboard) |
| READMEs com formulação absoluta antiga sobre lembretes | Informação (pendência já registrada no briefing §14; fora do escopo) |

Nenhuma regra de validação foi alterada. Contradições entre documentos registradas, não "corrigidas" silenciosamente.