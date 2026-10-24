#!/usr/bin/env python3
"""Validação de proveniência ComfyUI e gate de ferramentas do perfil Marca Salão."""
import argparse,hashlib,json,os,re,shlex,subprocess,sys,urllib.request,urllib.error
from pathlib import Path
BASE='http://127.0.0.1:8188'
POSTIZ='http://127.0.0.1:4007'
HOME=Path('/home/swn/.hermes')
REGISTRY=HOME/'integrations/postiz/comfyui-media-validada'
CHANNELS={'cmvbegwql0001msbhvdpjy0in','cmvbeq3100003msbhihu2dm4z'}
HELPER='/dados/aplicacoes/comfyui-servidor02/marcasalao_media_guard.py'

def get(path,binary=False):
 with urllib.request.urlopen(BASE+path,timeout=15) as r:data=r.read(32*1024*1024+1)
 if len(data)>32*1024*1024:raise ValueError('Resposta excede limite')
 return data if binary else json.loads(data)

def validate_package(package,prompt_id,fetch=get):
 package=Path(package).resolve()
 if not re.fullmatch(r'[a-f0-9-]{36}',prompt_id):raise ValueError('prompt_id ComfyUI inválido')
 m=json.loads((package/'manifest.json').read_text());h=fetch('/history/'+prompt_id).get(prompt_id,{})
 if h.get('status',{}).get('status_str')!='success':raise ValueError('Sem execução ComfyUI concluída: não enviar imagem manual')
 graph=h.get('prompt',[None,None,{}])[2]
 if graph.get('2',{}).get('class_type')!='MarcaSalaoArteIA' or graph['2']['inputs'].get('rede')!='compartilhado' or graph['2']['inputs'].get('formato')!='quadrado':raise ValueError('Exige geração integral workflow08 compartilhada')
 if m!=json.loads(h['outputs']['3']['text'][0]):raise ValueError('Manifesto local difere do ComfyUI')
 if m.get('visual_standard')!='quadrado-compartilhado-ia-v4' or m.get('publication_authorized') is not False or len(m.get('images',[]))!=1 or set(m.get('captions',{}))!={'facebook','instagram'}:raise ValueError('Pacote não segue padrão obrigatório')
 item=m['images'][0]
 if item.get('format')!='quadrado' or (item.get('width'),item.get('height'))!=(1080,1080) or Path(item['file']).name!=item['file']:raise ValueError('Imagem quadrada inválida')
 image=package/item['file'];raw=image.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Arte alterada após geração ComfyUI')
 from urllib.parse import urlencode
 served=fetch('/view?'+urlencode({'filename':item['file'],'subfolder':m['bundle'],'type':'output'}),True)
 if raw!=served:raise ValueError('Imagem local não corresponde à saída do ComfyUI')
 for cap in m['captions'].values():
  if Path(cap['file']).name!=cap['file'] or hashlib.sha256((package/cap['file']).read_bytes()).hexdigest()!=cap['sha256']:raise ValueError('Legenda alterada sem atualizar pacote')
 return {'image_path':str(image),'sha256':item['sha256'],'prompt_id':prompt_id,'package':str(package),'standard':m['visual_standard']}

def registered(url):
 p=REGISTRY/(hashlib.sha256(url.encode()).hexdigest()+'.json')
 if not p.is_file():return False
 r=json.loads(p.read_text())
 return r.get('media',{}).get('path')==url and r.get('standard')=='quadrado-compartilhado-ia-v4' and hashlib.sha256(Path(r['image_path']).read_bytes()).hexdigest()==r['sha256']

def duplicate(channel,url):
 key=(HOME/'secrets/postiz/api-key').read_text().strip()
 req=urllib.request.Request(POSTIZ+'/api/public/v1/posts?startDate=2020-01-01T00:00:00Z&endDate=2100-01-01T00:00:00Z',headers={'Authorization':key})
 with urllib.request.urlopen(req,timeout=10) as r:posts=json.load(r)['posts']
 path=url.split('/uploads/',1)[-1]
 for p in posts:
  if p.get('state') not in ('DRAFT','QUEUE') or p.get('integration',{}).get('id')!=channel:continue
  with urllib.request.urlopen(POSTIZ+'/p/'+p['id']+'?share=true',timeout=10) as response:page=response.read(8*1024*1024).decode()
  if any(path in tag for tag in re.findall(r'<img\b[^>]+>',page)):return True
 return False

def block(message):return {'action':'block','message':message}

def check_tool(payload,registered_fn=registered,duplicate_fn=duplicate,_seen=None):
 if _seen is None:_seen=set()
 if payload.get('profile','default')!='default':return {}
 name=payload.get('tool_name','');args=payload.get('tool_input') or {}
 if isinstance(args,str):args=json.loads(args)
 if name in ('tool_call','execute_code') and isinstance(args.get('calls'),list):
  for c in args['calls']:
   result=check_tool({'profile':'default','tool_name':c.get('name'),'tool_input':c.get('arguments',{})},registered_fn,duplicate_fn,_seen)
   if result:return result
 if name in ('terminal','execute_code','write_file','patch'):
  text=json.dumps(args,ensure_ascii=False)
  if 'ImageDraw' in text:return block('Marca Salão: criação manual Pillow bloqueada. Use workflow08 ComfyUI; não substituir a arte aprovada.')
  if re.search(r'postiz(?:\\?"|\s)+(?:upload|posts:create)',text) and HELPER not in text:return block('Use marcasalao_media_guard.py upload --package PACOTE --prompt-id ID --state NOVO.json; upload sem proveniência ComfyUI bloqueado.')
  if name=='terminal':
   command=args.get('command','')
   try:
    for token in shlex.split(command):
     p=Path(token)
     if p.suffix=='.py' and p.is_file() and p.resolve()!=Path(HELPER) and 'ImageDraw' in p.read_text():return block('Script de composição manual bloqueado. Use ComfyUI workflow08.')
   except (OSError,ValueError):pass
 if name.endswith('integrationSchedulePostTool'):
  posts=args.get('socialPost',[])
  if isinstance(posts,str):posts=json.loads(posts)
  if isinstance(posts,dict):posts=[posts]
  for post in posts:
   channel=post.get('integrationId')
   if channel not in CHANNELS or post.get('type')!='draft':continue
   groups=post.get('postsAndComments',[])
   urls=[u for g in groups for u in g.get('attachments',[])]
   if len(urls)!=1 or not isinstance(urls[0],str) or not registered_fn(urls[0]):return block('DRAFT Marca Salão exige uma mídia validada pelo ComfyUI08. Execute o validador/upload; não crie imagem local substituta.')
   pair=(channel,urls[0])
   if pair in _seen:return block('Criação repetida no mesmo lote: um rascunho por canal e mídia.')
   _seen.add(pair)
   if duplicate_fn(channel,urls[0]):return block('Já existe rascunho dessa mídia neste canal. Reutilize/atualize o ID existente; não crie duplicata.')
 return {}

def upload(package,prompt_id,state):
 proof=validate_package(package,prompt_id)
 state=Path(state)
 if state.exists():
  prior=json.loads(state.read_text())
  if prior.get('status')=='complete' and prior.get('sha256')==proof['sha256']:return prior
  raise ValueError('Upload anterior incerto: consulte a mídia antes de repetir')
 REGISTRY.mkdir(mode=0o700,parents=True,exist_ok=True)
 for record_file in REGISTRY.glob('*.json'):
  prior=json.loads(record_file.read_text())
  if prior.get('status')=='complete' and prior.get('sha256')==proof['sha256']:
   if not registered(prior['media']['path']):raise ValueError('Registro anterior inválido; conferir mídia sem reenviar')
   state.parent.mkdir(parents=True,exist_ok=True)
   with state.open('x') as f:json.dump(prior,f,ensure_ascii=False,indent=2)
   state.chmod(0o600)
   return prior
 state.parent.mkdir(parents=True,exist_ok=True)
 with (REGISTRY/(proof['sha256']+'.pending')).open('x') as reservation:json.dump({'status':'submitting','sha256':proof['sha256'],'state':str(state)},reservation)
 with state.open('x') as f:json.dump({**proof,'status':'submitting'},f)
 process=subprocess.run(['/home/swn/.local/share/hermes-postiz-cli/2.0.25/node_modules/postiz/dist/index.js','upload',proof['image_path']],capture_output=True,text=True,timeout=120,env={**os.environ,'POSTIZ_API_KEY':(HOME/'secrets/postiz/api-key').read_text().strip(),'POSTIZ_API_URL':POSTIZ+'/api'})
 if process.returncode:raise ValueError('Upload falhou; estado preservado, conferir biblioteca antes de repetir')
 text=process.stdout;start=text.find('{')
 media=json.JSONDecoder().raw_decode(text[start:])[0]
 if not isinstance(media.get('path'),str) or not media.get('id'):raise ValueError('Resposta de mídia inválida; conferir estado')
 proof.update({'media':media,'status':'complete'})
 REGISTRY.mkdir(mode=0o700,parents=True,exist_ok=True)
 p=REGISTRY/(hashlib.sha256(media['path'].encode()).hexdigest()+'.json');p.write_text(json.dumps(proof,ensure_ascii=False,indent=2));p.chmod(0o600)
 state.write_text(json.dumps(proof,ensure_ascii=False,indent=2));state.chmod(0o600)
 return proof

def main():
 if len(sys.argv)>1 and sys.argv[1]=='hook':
  try:result=check_tool(json.load(sys.stdin))
  except Exception:result=block('Validação Marca Salão indisponível. Pare e confira o pacote/estado; não ignorar o guard.')
  print(json.dumps(result,ensure_ascii=False));return
 p=argparse.ArgumentParser();p.add_argument('action',choices=['validate','upload']);p.add_argument('--package',required=True,type=Path);p.add_argument('--prompt-id',required=True);p.add_argument('--state',type=Path);a=p.parse_args()
 if a.action=='upload' and not a.state:p.error('--state obrigatório')
 print(json.dumps(upload(a.package,a.prompt_id,a.state) if a.action=='upload' else validate_package(a.package,a.prompt_id),ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except Exception as e:print('Validação/envio bloqueado: '+str(e),file=sys.stderr);sys.exit(1)
