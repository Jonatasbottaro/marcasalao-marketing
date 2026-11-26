# Guia operacional — finalização audiovisual externa (CapCut / Canva)

- Data: 26/11/2026 (Operação RESULTADO 15)
- Padrão vigente: [MKT-VIDEO-002 — VIDEO CLEAN / narração separada](decisoes/MKT-VIDEO-002-video-clean-narracao-separada.md)
- Primeiro caso: NS-001 Studio Bella v2.8 (pacote em `<RAIZ>/.workspace/tmp/ns001-studio-bella-finalizacao/`)
- Documento reutilizável: o fluxo vale para qualquer campanha produzida no modo clean.

## Princípio

A fábrica entrega o **master visual limpo** (sem áudio, sem legendas queimadas,
sem SRT) + **roteiro de narração TXT**. O titular gera a voz em ferramenta
externa e finaliza no editor de sua escolha (CapCut, Canva ou outro). O pacote
de finalização dá a ele tudo para sincronizar e exportar sem tocar no código
do projeto nem no master.

Três versões finais possíveis, todas escolha do titular no editor:

1. narração, sem legendas;
2. narração + legendas criadas no editor;
3. completamente silencioso.

O vídeo final do titular **terá faixa de áudio** — isso é esperado e não
altera a regra de que o master gerado pela fábrica permanece sem áudio.

## Estrutura do pacote de finalização

Pasta local em `<RAIZ>/.workspace/tmp/<campanha>-finalizacao/` (não versionada;
mídias nunca vão ao Git):

| Arquivo | Conteúdo |
| --- | --- |
| `LEIA-ME.md` | Índice, fluxo em 5 passos, regra do master único |
| `<campanha>-master.mp4` | Cópia byte-idêntica do master (um só, se os perfis forem idênticos) |
| roteiro final de narração (TXT) | Cópia do arquivo versionado em `04-legendas/` |
| `TABELA-SINCRONIZACAO.md` | Janelas por cena, texto final, eventos visuais internos, colocação recomendada da voz |
| `GUIA-CAPCUT.md` | Passos manuais reais (desktop + notas mobile) |
| `GUIA-CANVA.md` | Passos manuais reais (editor de vídeo web) |
| `INSTRUCOES-EXPORTACAO.md` | Parâmetros alvo, nomes, conferência pós-export |
| `CHECKLIST-QUALIDADE.md` | 8 grupos de conferência (sincronização, clareza, textos editoriais, legendas duplicadas, celular, identidade, CTA, exportação) |
| `MANIFESTO.json` | Inventário com proveniência, hashes e regras |
| `checksums.txt` | SHA-256 de todos os arquivos |
| ZIP portátil | Empacotamento da pasta, com teste de integridade |

Evidências de verificação do master (ffprobe, uniformidade da antiga banda de
legendas) ficam em `qc/` ao lado do pacote.

## Regras do pacote

- **Não gerar áudio, voz, música, legendas ou SRT** no pacote; não modificar o
  master; não criar projetos nativos falsos de CapCut/Canva — documentar os
  passos manuais reais.
- **Master único** quando os perfis são byte-idênticos (comparar SHA-256 antes
  de deduplicar); explicar o uso nos três canais.
- Guias em pt-BR, com nomes de menu reais e ressalva de variação por versão;
  nada de simular integração.
- Caminhos em documentos versionados: `<RAIZ>` ou formulação estrutural,
  nunca caminho literal de máquina.

## Parâmetros de referência

- Exportação: MP4, H.264, 1080×1920, 30 fps, 10–15 Mbps; áudio AAC 48 kHz
  192–320 kbps quando houver narração; duração exata do master.
- Voz: ~135–145 palavras por minuto; picos ≤ -3 dBFS; loudness ~-14 LUFS;
  fades curtos (~0,05–0,1 s) nas emendas; sem música (padrão da campanha).
- Ritmo: estimar duração por contagem de palavras (120–150 ppm) antes de
  aprovar o roteiro; nunca exigir fala acelerada para caber na cena.

## Áreas seguras e legendas do editor

- Conteúdo essencial do master deve permanecer dentro das áreas seguras da
  composição (no caso NS-001 v2.8: até y ≈ 1204 px de 1920).
- Faixa livre para legendas adicionadas no editor: antiga banda de legendas
  (no NS-001 v2.8: y ≈ 1450–1650 px), fonte ≥ 48 px, contraste alto.
- Evitar os ~200 px inferiores e a lateral direita (interface das plataformas).
- O master clean não tem legenda queimada → não há duplicação vinda do vídeo;
  se o titular usar legendas automáticas + textos manuais, remover a camada
  redundante.

## Fluxo do titular (resumo)

1. Gerar a voz a partir da seção **TEXTO CORRIDO** do roteiro final.
2. Criar projeto 9:16 no editor; importar master e voz.
3. Alinhar pelas âncoras da tabela (cortes de cena); ajustar pausas, não a
   velocidade da fala.
4. Decidir sobre legendas; posicionar na faixa livre.
5. Exportar com os parâmetros alvo; conferir com o checklist; master original
   intacto.

## Verificações objetivas antes de entregar o pacote

- `ffprobe`: resolução/fps/duração/codec esperados; **0 faixas de áudio**;
  SHA-256 do master igual ao da entrega aprovada.
- Antiga banda de legendas uniforme (ex.: `crop` + `signalstats`, YMIN=YMAX
  nos pontos médios das cenas) — prova de ausência de legenda queimada.
- ZIP com `testzip` OK; checksums de todos os arquivos; manifesto com
  proveniência (commit do roteiro, origem do master).

## Referências

- Roteiro final do primeiro caso: [../04-legendas/ns001_roteiro_001_v28_studio_bella_narracao_final.txt](../04-legendas/ns001_roteiro_001_v28_studio_bella_narracao_final.txt) (commit `ee09b57`).
- Composição e pedido: `02-reels-shorts/ns-001-reels-organizacao-agenda/editorial-v28/`.
- Estado e continuidade: [contexto/ESTADO-ATUAL.md](contexto/ESTADO-ATUAL.md).
