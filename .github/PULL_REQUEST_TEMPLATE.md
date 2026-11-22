# Pull Request — marcasalao-marketing

Preencha todas as seções. PR sem checklist completo não entra em revisão. As regras
permanentes estão em [AGENTS.md](../AGENTS.md); o índice documental em
[docs/README.md](../docs/README.md); a política de manutenção em
[docs/governanca/DOCUMENTACAO.md](../docs/governanca/DOCUMENTACAO.md); o mapa de CI e gates
em [docs/governanca/CI-E-PRS.md](../docs/governanca/CI-E-PRS.md).

## 1. Resumo e objetivo

- O que muda e por quê (1–3 frases):
- Frente afetada (marque uma): [ ] Editorial (00–06) · [ ] Fábrica/Tools · [ ] Video Studio ·
  [ ] Platform (núcleo TS) · [ ] Temporal · [ ] Documentação/Governança · [ ] Integrações de marca
- Issue/autorização do titular relacionada (se houver):

## 2. Conformidade com regras permanentes

- [ ] Nenhum arquivo criado ou mantido fora de `<RAIZ>` (`git rev-parse --show-toplevel`);
      auxiliares somente em `<RAIZ>/.workspace/<categoria>/<tarefa>`.
- [ ] Vídeo sem áudio preservado: MP4 `-an` (0 faixas conferidas por FFprobe), `.srt`
      sincronizado e `<slug>_narracao.txt` separado; nenhuma narração/música/efeito gerado
      no editor. Exceção apenas para tenants com `allowAudioTrack: true`.
- [ ] `autoPublish: false` em toda a cadeia; nada publica, agenda ou cria rascunho remoto
      sem autorização específica registrada.
- [ ] Isolamento multi-tenant: métricas, benchmarks e relatórios escopados por `tenant_id`;
      nenhuma comparação entre nichos.
- [ ] Nenhum caminho absoluto de estação/servidor introduzido em arquivo versionado
      (`C:/`, `D:/`, `/home/`, `/dados/`, `%TEMP%`); usar `<RAIZ>` ou caminho relativo.
- [ ] Nenhuma credencial, token, cookie ou dado pessoal adicionado.
- [ ] Conteúdo editorial (briefings, hooks, roteiros, aprovações) não alterado sem
      autorização própria; registros históricos não reescritos retroativamente.

## 3. Sincronização documental obrigatória

- [ ] `docs/contexto/ESTADO-ATUAL.md` atualizado quando o estado técnico muda
      (implementado × proposto × integrado × só-em-branch), com SHA e data.
- [ ] `docs/contexto/PROXIMOS-PASSOS.md` atualizado quando a conclusão altera a próxima tarefa.
- [ ] `docs/governanca/MAPA-DOCUMENTAL.md` atualizado para documentos criados/movidos/classificados.
- [ ] READMEs e guias afetados atualizados (raiz, `docs/arquitetura-fabrica.md`,
      `docs/guia-operacional-titular.md`, `tools/produce/README.md`, `tools/render/README.md`,
      `platform/README.md`, `orchestration/temporal/README.md`), incluindo contagens e comandos.
- [ ] Schemas, exemplos e fixtures alterados junto com o contrato correspondente.
- [ ] Links relativos conferidos; âncoras e consumidores de código de caminho verificados
      antes de mover qualquer documento.

## 4. Verificações executadas (evidência literal)

Cole a saída resumida e indique SHA da base, ambiente e data. Marque o que rodou:

- [ ] `python tools/release_check.py --skip-ts --json` (ou completo, com `platform/` compilado)
- [ ] `python tools/verify_egm_install.py`
- [ ] `python tools/tenant_validator.py --all --json`
- [ ] `python tools/workspace_doctor.py --check`
- [ ] Testes específicos da mudança (nomear módulos e resultado):
- [ ] Gates de render/CI acompanhados no SHA do PR (quando toca `tools/`, `platform/`, mídia):
- [ ] Nada foi executado (PR documental puro): confirmar que a alteração é somente documentação
      e que contagens citadas foram conferidas por leitura, com base indicada.

## 5. Riscos e limitações

- O que esta mudança **não** verifica ou não autoriza:
- Pendências deixadas para o titular (autorizações, decisões editoriais, integrações):

## 6. Handoff

- Base (branch + SHA completo):
- Worktree/isolamento utilizado:
- Arquivos alterados (lista):
- Próxima ação segura após o merge: