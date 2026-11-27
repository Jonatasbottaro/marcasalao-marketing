# Guia rápido do Video Studio (painel local)

Manual curto para o titular produzir imagens, carrosséis e Reels pelo painel, **sem FFmpeg manual e sem
depender de um agente por criativo**. Tudo roda local, em `127.0.0.1`; nada é publicado.

## Como abrir

```bash
python tools/video_studio.py --port 8765
# abra http://127.0.0.1:8765/
```

O painel mostra "Ambiente pronto ✓" quando o FFmpeg local e as dependências estão disponíveis. Use
"Reverificar ambiente" se algo mudar.

## O fluxo em uma frase

**Nova campanha → escolher formato → criar/importar imagens → editar → visualizar → exportar → revisar.**

## Passo a passo

1. **Criar ou abrir um trabalho.** Em "Trabalhos & Projetos", use "Demonstração guiada" para ver o fluxo
   completo em 1 clique, "Criar a partir de modelo" para o seu conteúdo, ou "Reabrir" um trabalho existente.
   Tudo é persistente: feche e reabra sem perder rascunhos, mídias e entregas.
2. **Escolher o formato.** Cada trabalho oferece destinos por tipo:
   - **Vídeo/Reel** vertical 9:16 (1080×1920).
   - **Carrossel/Imagem** quadrado 1:1 (1080×1080) e retrato 4:5 (1080×1350).
   - **Motion** sobre perfis verticais.
3. **Criar ou importar imagens** (aba **Mídias**):
   - **Importação manual** (não exige chave): gere a arte em ferramenta autorizada e importe o arquivo.
   - **IA (Gemini)**: só funciona com `GEMINI_API_KEY` configurada **fora do código**. Sem a chave, o painel
     indica indisponível e você usa a importação manual.
   - **Simulador**: apenas para teste/demonstração; **nunca** use como arte comercial final.
4. **Editar.** Ajuste cenas, textos e enquadramento nos módulos correspondentes. Vídeo e Motion usam
   enquadramento; carrossel usa cards (título + corpo + imagem).
5. **Vídeo limpo (MKT-VIDEO-002).** Marque a caixa **"Vídeo limpo (sem legendas/SRT)"** para entregar o MP4
   **sem legenda queimada e sem SRT**, com o **roteiro de narração em TXT separado**. Desmarcada, mantém o
   modo legado (legenda queimada + SRT). Nenhum modo gera ou embute áudio — a locução é feita fora do editor.
6. **Visualizar.** Use as prévias do painel e a aba **Revisão & Entrega** (storyboard, texto de narração,
   hashes quando houver).
7. **Exportar.** A produção gera os arquivos de entrega (imagem por perfil; carrossel com ZIP + manifest;
   vídeo MP4). Nada é publicado: todo pacote nasce com `autoPublish: false`.
8. **Revisar e ajustar.** Se algo não agradar, ajuste e gere de novo. Para publicar, a decisão e o envio são
   sempre manuais e fora deste painel.

## Regras que o painel respeita

- **Sem áudio.** Os tenants `-an` (inclui Marca Salão) entregam MP4 sem faixa de áudio.
- **Sem publicação automática.** O painel não publica, agenda nem cria rascunho.
- **Arte comercial ≠ simulador.** O simulador existe para teste; a arte final é original, captura real ou
  provider autorizado.
- **Proveniência.** Mídia do fluxo ComfyUI passa pelo validador (`marcasalao_media_guard.py`); não contorne o gate.
- **Portabilidade.** Tudo dentro do checkout; auxiliares em `<RAIZ>/.workspace/`; alinhamento por Git.

## Onde ficam os arquivos

- Trabalhos: `.workspace/studio/works/<id>/` (documento do trabalho, rascunhos, mídias).
- Entregas: subpastas de `deliveries/` do próprio trabalho.
- Nada em diretórios temporários externos.

## Quando usar IA x importação manual

| Situação | Caminho |
| --- | --- |
| Quero gerar no painel | Gemini (exige `GEMINI_API_KEY` fora do código) |
| Não tenho chave / quero controle total da arte | Importação manual |
| Só quero testar o fluxo | Simulador (marcado como simulado) |
| Arte oficial de marca no ComfyUI | Fluxo ComfyUI + `marcasalao_media_guard.py` |
