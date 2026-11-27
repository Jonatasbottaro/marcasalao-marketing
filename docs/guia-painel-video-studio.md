# Guia de uso diário do Video Studio (painel local)

Manual curto para o titular produzir imagens, carrosséis e Reels pelo painel, **sem FFmpeg manual e sem
depender de um agente por criativo**. Tudo roda local, em `127.0.0.1`; nada é publicado.

## Como abrir

```bash
python tools/video_studio.py --prepare --port 8765
# abra http://127.0.0.1:8765/
```

O painel mostra "Ambiente pronto ✓" quando o FFmpeg local e as dependências estão disponíveis. Use
"Reverificar ambiente" se algo mudar. Para só conferir, sem subir o painel:
`python tools/video_studio.py --check --json`.

## Os 9 passos do uso diário

**Nova campanha → escolher formato → criar/importar imagens → montar → visualizar → exportar → revisar.**

1. **Abrir o Studio.** Rode o comando acima e confira "Ambiente pronto". Se aparecer FFmpeg/FFprobe
   ausente, veja "O que se repete em outro computador" abaixo.
2. **Criar uma campanha (trabalho).** Em "Trabalhos & Projetos", use "Demonstração guiada" para ver o fluxo
   completo em 1 clique, "Criar a partir de modelo" para o seu conteúdo, ou "Reabrir" um trabalho existente.
   Cada trabalho é persistente: feche e reabra sem perder rascunhos, mídias e entregas.
3. **Criar ou importar imagens** (aba **Mídias**), escolhendo o formato/destino primeiro:
   - **Vídeo/Reel** vertical 9:16 (1080×1920); **Carrossel/Imagem** quadrado 1:1 (1080×1080) e retrato 4:5 (1080×1350).
   - **Importação manual** (não exige chave): gere a arte em ferramenta autorizada e importe o arquivo.
   - **IA (Gemini)**: só funciona com `GEMINI_API_KEY` configurada **fora do código**. Sem a chave, o painel
     indica indisponível e você usa a importação manual.
   - **Simulador**: apenas para teste/demonstração; **nunca** use como arte comercial final.
4. **Montar a peça (editar).** Ajuste cenas, textos e enquadramento. Vídeo e Motion usam enquadramento;
   carrossel usa cards (título + corpo + imagem). Marque **"Vídeo limpo (sem legendas/SRT)"** para entregar
   MP4 **sem legenda queimada e sem SRT**, com o roteiro de narração em TXT separado (política MKT-VIDEO-002).
   Desmarcada, mantém o modo legado (legenda queimada + SRT). Nenhum modo gera ou embute áudio.
5. **Visualizar.** Use as prévias do painel e a aba **Revisão & Entrega** (storyboard, texto de narração,
   hashes quando houver).
6. **Exportar.** A produção gera os arquivos de entrega (imagem por perfil; carrossel com ZIP + manifest;
   vídeo MP4; Motion). Nada é publicado: todo pacote nasce com `autoPublish: false`.
7. **Revisar e ajustar.** Se algo não agradar, ajuste e gere de novo. Para publicar, a decisão e o envio são
   sempre manuais e fora deste painel.
8. **Encontrar os arquivos.** Trabalhos e entregas ficam no próprio checkout (ver "Onde ficam os arquivos").
9. **Encerrar e retomar.** Feche a aba do painel e pare o servidor com `Ctrl+C`. Reabra depois com o mesmo
   comando e use "Reabrir" no trabalho: rascunhos, mídias, fila e entregas continuam lá.

## Regras que o painel respeita

- **Sem áudio.** Os tenants `-an` (inclui Marca Salão) entregam MP4 sem faixa de áudio.
- **Sem publicação automática.** O painel não publica, agenda nem cria rascunho.
- **Arte comercial ≠ simulador.** O simulador existe para teste; a arte final é original, captura real ou
  provider autorizado.
- **Proveniência.** Mídia do fluxo ComfyUI passa pelo validador (`marcasalao_media_guard.py`); não contorne o gate.
- **Portabilidade.** Tudo dentro do checkout; auxiliares em `<RAIZ>/.workspace/`; alinhamento por Git.

## Onde ficam os arquivos

- Trabalhos: `<RAIZ>/.workspace/studio/works/<id>/` (documento do trabalho, rascunhos, mídias).
- Entregas: subpastas de `deliveries/` do próprio trabalho (imagens, `carousel.zip`, MP4, `manifest.json`).
- Nada em diretórios temporários externos. `.workspace/` é local e não vai para o Git.

## Quando usar IA x importação manual

| Situação | Caminho |
| --- | --- |
| Quero gerar no painel | Gemini (exige `GEMINI_API_KEY` fora do código) |
| Não tenho chave / quero controle total da arte | Importação manual |
| Só quero testar o fluxo | Simulador (marcado como simulado) |
| Arte oficial de marca no ComfyUI | Fluxo ComfyUI + `marcasalao_media_guard.py` |

## O que se repete em outro computador

O **conteúdo versionado** (código e documentação) alinha por Git. Já o **ambiente local não sincroniza** —
`.workspace/` é ignorado pelo Git e cada estação tem o seu. Ao trocar de computador, configure de novo:

| Item | O que fazer na nova estação |
| --- | --- |
| FFmpeg/FFprobe portáteis | Coloque os binários em `<RAIZ>/.workspace/tools/ffmpeg/` (não versionados) ou exponha no PATH. |
| Node.js | Instale Node 24+ (o painel e o bridge TS usam Node). |
| Build da platform | `cd platform && npm ci && npm run build` (gera `platform/dist/`). |
| Chave Gemini (opcional) | Configure `GEMINI_API_KEY` **fora do código** e reinicie o Studio. Só é necessária para gerar por IA. |
| Trabalhos e entregas | Vivem em `.workspace/studio/works/` e **não** são versionados: para levá-los a outra estação, copie a pasta do trabalho manualmente para o novo `.workspace/studio/works/`. |

Passos que **não** precisam repetir: criar trabalho, montar peça, exportar e revisar são operações do próprio
painel, iguais em qualquer estação, desde que o ambiente acima esteja pronto.
