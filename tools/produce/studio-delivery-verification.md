# Verificação do pacote ZIP de entrega

O Studio gera um pacote ZIP de entrega em **Revisão & Entrega** com o
manifesto `package-manifest.json`. A verificação técnica é **somente leitura**
e usa esse mesmo manifesto — não cria um segundo manifesto nem altera o ZIP.

Ela responde: o ZIP abre, o manifesto é válido, os arquivos declarados existem,
os tamanhos e SHA-256 conferem, e as peças registram aprovação para entrega
local. A aprovação editorial continua no fluxo existente; esta verificação é
técnica.

## Pelo painel

1. Gere o ZIP em **Revisão & Entrega** (botão **Gerar ZIP de entrega**).
2. Clique em **Verificar pacote ZIP**, ao lado do link de download.
3. O painel mostra o resumo (peças, canais, arquivos) e, em caso de falha, o
   primeiro problema acionável.

A verificação fica vinculada ao trabalho e ao `packageId` do pacote. Ao trocar
de trabalho ou gerar um novo ZIP, o resultado anterior é descartado.

## Pela linha de comando

```bash
# Saída legível
python tools/delivery_verify.py .workspace/studio/works/<id>/deliveries/package/delivery-package.zip

# Saída estruturada
python tools/delivery_verify.py caminho/do.zip --json

# Comparação com o SHA-256 mostrado pelo Studio
python tools/delivery_verify.py caminho/do.zip --expected-sha256 <sha256>
```

- Código de saída `0` quando o pacote é válido; diferente de zero quando há
  arquivo ausente, SHA-256 divergente, manifesto inválido ou ZIP ilegível.
- `--expected-sha256` informa nos resultados se a comparação foi feita
  (`zipSha256.compared`) e se confere (`zipSha256.match`).
- Pacotes antigos sem `sha256` no manifesto são aceitos com **limitação
  explícita**; campos de versão/decisão ausentes também são reportados como
  limitação, não como aprovação completa.

## Exemplo de sucesso

```bash
$ python tools/delivery_verify.py caminho/do.zip
Verificação do pacote ZIP de entrega
=====================================
Pacote: entrega-pkg-1234567890
Trabalho: Campanha de exemplo (entrega-1)
Modalidades: video
Destinos: instagram-reels-video
...
Resultado: VÁLIDO
Pacote entrega-pkg-1234567890 íntegro: 1 peça(s), 0 canal(is), 3 arquivo(s) conferido(s).
```

## Exemplo de falha

```bash
$ python tools/delivery_verify.py caminho/do.zip --json
{
  "ok": false,
  "packageId": "entrega-pkg-1234567890",
  "errors": [
    {"field": "files.sha256", "file": "video/instagram-reels-video/primary-output.mp4", "message": "SHA-256 divergente"}
  ],
  ...
}
```

## Contrato

- Usa `package-manifest.json` (schemaVersion 1) e os arquivos declarados em
  `files`, `pieces[].files` e `channels[].files`.
- Não modifica o ZIP e não exige o Studio em execução para a CLI.
- O resumo (`pieces`, `channels`, `deliveryVersionId`, `reviewedDecision`) só é
  apresentado quando o manifesto registra esses campos.