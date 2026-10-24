#!/usr/bin/env python3
import os,sys
from pathlib import Path
REAL='/home/swn/.local/share/hermes-postiz-cli/2.0.25/node_modules/postiz/dist/index.js'
a=sys.argv[1:]
home=os.environ.get('HERMES_HOME','')
text=' '.join(a)
other=('/profiles/' in home and home!='/home/swn/.hermes') or '/marcas/multitrackhub/' in text
marca=not other and (home=='/home/swn/.hermes' or '/marcas/marcasalao/' in text or 'cmvbegwql0001msbhvdpjy0in' in text or 'cmvbeq3100003msbhihu2dm4z' in text)
if marca and a and a[0] in ('upload','posts:create'):
 print('Marca Salão: envio direto bloqueado. Use o validador marcasalao_media_guard.py upload com pacote e prompt_id do ComfyUI08. Criação de DRAFT usa a mídia validada pelo MCP; revisão reutiliza IDs.',file=sys.stderr)
 sys.exit(2)
os.execv(REAL,[REAL,*a])
