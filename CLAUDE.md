# Regras do projeto Marca Salão Marketing

> **Entrada de IDE.** Este arquivo encaminha para as mesmas fontes canônicas carregadas por
> outras IDEs; não mantém versão independente das regras. Contrato operacional completo:
> [AGENTS.md](AGENTS.md). Índice central da documentação: [docs/README.md](docs/README.md).
> Fluxo de marketing: [WORKFLOW.md](WORKFLOW.md). Estado técnico e retomada:
> [docs/contexto/README.md](docs/contexto/README.md). As regras abaixo são um resumo
> essencial; em caso de divergência, prevalece `AGENTS.md`.

## Regra de produção: vídeo sem áudio

- Gerar vídeos com legendas visíveis e sincronizadas às cenas.
- Não preservar o áudio original das gravações.
- Não gerar nem inserir narração, música, efeitos sonoros ou qualquer outro áudio no editor.
- Entregar o texto de narração separado em `04-legendas/`, em português brasileiro, organizado por cenas e tempos, pronto para copiar para uma ferramenta externa.
- Entregar também o arquivo `.srt` correspondente às legendas do vídeo.
- O usuário gera o áudio fora do editor de vídeo; essa etapa não é requisito para entregar o vídeo legendado.
- Preferir exportação sem faixa de áudio; não confundir faixa silenciosa com narração gerada.
- Só mudar essa política mediante pedido explícito do usuário.
- Os vídeos existentes de demonstração/teste não devem ser apresentados como campanhas finais aprovadas.

### Aplicação às ferramentas

Esta regra específica do Marca Salão orienta o uso das skills e templates genéricos: não seguir etapas de TTS, música ou preservação de áudio nesses fluxos. Nas composições, manter vídeos mudos e não adicionar elementos de áudio. Na exportação com FFmpeg, mapear somente vídeo e usar `-an`.

### Verificação da entrega

- Conferir as legendas, legibilidade e correspondência com as cenas.
- Conferir a duração do vídeo, do SRT e dos tempos indicados no roteiro.
- Conferir com `ffprobe` se há faixas de áudio; a exportação preferida não contém nenhuma.
- Entregar vídeo legendado + SRT + texto de narração separado, sem gerar áudio.

Consulte `WORKFLOW.md` para o fluxo completo.

## Elephant-Goldfish Model (EGM)

EGM artifact directory: .workspace/tmp/egm

- Pacote canônico do EGM neste repositório: `.agents/plugins/egm/` (skills em `.agents/plugins/egm/skills/egm-*/SKILL.md`, personas em `.agents/plugins/egm/agents/*.md`, padrões em `.agents/plugins/egm/resources/document_standards/*.md` e guias em `.agents/plugins/egm/docs/*.md`).
- Especificações aprovadas ficam em `docs/designs/`; rascunhos, briefs intermediários e relatórios de revisão Goldfish ficam em `.workspace/tmp/egm/`.
- Revisões Goldfish exigem subagentes em contexto limpo (sem histórico da conversa principal); nunca simular Goldfish no mesmo contexto.
- Guia multi-harness e verificação: `docs/designs/GUIA-EGM.md` e `python tools/verify_egm_install.py`.
