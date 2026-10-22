# Workflow Marca Salão — uma arte quadrada compartilhada v4

Padrão atual aprovado em 22/10/2026: workflow08, brief → UMA arte completa Gemini 2K em 1:1 → UM PNG RGB 1080×1080 compartilhado no Facebook e Instagram + DUAS legendas adaptadas + manifesto. CTA neutra na imagem “Conheça o Marca Salão”. Chamadas por rede nas legendas. Não redesenhar textos/logo nem recortar a arte completa.

Workflow09/--square-art reutiliza UMA arte completa existente sem Gemini. Exportador marcasalao_export.py usa08 por padrão; --resume consulta execução existente sem repetir geração. Cache com SHA válido impede nova chamada da mesma arte; estado incerto bloqueia repetição. Primeira arte inédita consome até UMA chamada de imagem, sem retries automáticos; refazer exige revisão consciente. Formatos extras só mediante pedido. Workflows06/07 (seis variantes) e04/05 (composição local) ficam históricos.

Consulte HERMES-POSTIZ.md para execução, contrato media_by_network, legendas, retomada e revisão. Nenhum modelo local nem segredo no fonte. Configurar/gerar prévia não faz upload nem cria rascunhos/publicação/agendamento no Postiz. Esses passos exigem pedido específico. Preservar conteúdos anteriores e não tocar Multitrack Hub.
