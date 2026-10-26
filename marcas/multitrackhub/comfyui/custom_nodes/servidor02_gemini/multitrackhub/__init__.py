"""Nós exclusivos Multitrack Hub; MS_BRIEF não é aceito nas conexões."""
import json
import math
from . import brand

class MultitrackHubBrief:
 @classmethod
 def INPUT_TYPES(cls):
  return {'required':{'campanha':('STRING',{'default':'novo-conteudo-multitrackhub'}),'tema':('STRING',{'default':'Preparação musical'}),'titulo':('STRING',{'multiline':True,'default':'Sua música. Novas possibilidades.'}),'texto':('STRING',{'multiline':True,'default':'Multitracks | Playbacks | Rateios'}),'legenda_facebook':('STRING',{'multiline':True,'default':'Conheça as possibilidades da Multitrack Hub.'}),'legenda_instagram':('STRING',{'multiline':True,'default':'Conheça as possibilidades da Multitrack Hub.'}),'direcao_visual':('STRING',{'multiline':True,'default':'Pistas de áudio turquesa sobre fundo preto, sem telas fictícias.'}),'link_bio_confirmado':('BOOLEAN',{'default':False}),'destino':(['site','rateios'],)}}
 RETURN_TYPES=('STRING','MHH_BRIEF')
 RETURN_NAMES=('pedido_imagem','brief_multitrackhub')
 FUNCTION='run'
 CATEGORY='Multitrack Hub'
 def run(self,**kwargs):
  b=brand.prepare_brief(**kwargs);return brand.full_prompt(b),b

class MultitrackHubArteIA:
 @classmethod
 def INPUT_TYPES(cls):return {'required':{'brief':('MHH_BRIEF',),'revisao':('INT',{'default':1,'min':1,'max':999})}}
 RETURN_TYPES=('IMAGE','STRING')
 RETURN_NAMES=('arte_completa','geracao_json')
 FUNCTION='run'
 CATEGORY='Multitrack Hub'
 @classmethod
 def IS_CHANGED(cls,**kwargs):return math.nan
 def run(self,brief,revisao=1):
  import numpy as np
  import torch
  import folder_paths
  image,meta=brand.generate_artwork(brief,folder_paths.get_output_directory(),revision=revisao)
  text=json.dumps(meta,ensure_ascii=False)
  return {'ui':{'text':[text]},'result':(torch.from_numpy(np.array(image).astype(np.float32)/255).unsqueeze(0),text)}

class MultitrackHubPacoteIA:
 @classmethod
 def INPUT_TYPES(cls):return {'required':{'brief':('MHH_BRIEF',),'imagem':('IMAGE',),'origem':(['gemini','imagem_local'],)}}
 RETURN_TYPES=('STRING',)
 RETURN_NAMES=('manifest_json',)
 FUNCTION='run'
 CATEGORY='Multitrack Hub'
 OUTPUT_NODE=True
 @classmethod
 def IS_CHANGED(cls,**kwargs):return math.nan
 def run(self,brief,imagem,origem='gemini'):
  import numpy as np
  from PIL import Image
  import folder_paths
  if len(imagem.shape)!=4 or imagem.shape[0]!=1:raise ValueError('Uma única arte quadrada por campanha Multitrack Hub.')
  pixels=np.rint(np.clip(imagem[0].cpu().numpy(),0,1)*255).astype(np.uint8)
  m=brand.export_bundle(brief,Image.fromarray(pixels),folder_paths.get_output_directory(),origem);text=json.dumps(m,ensure_ascii=False,indent=2)
  return {'ui':{'images':[{'filename':i['file'],'subfolder':m['bundle'],'type':'output'} for i in m['images']],'text':[text]},'result':(text,)}

NODE_CLASS_MAPPINGS={'MultitrackHubBrief':MultitrackHubBrief,'MultitrackHubArteIA':MultitrackHubArteIA,'MultitrackHubPacoteIA':MultitrackHubPacoteIA}
NODE_DISPLAY_NAME_MAPPINGS={'MultitrackHubBrief':'Multitrack Hub · Brief e legendas','MultitrackHubArteIA':'Multitrack Hub · Uma arte Gemini 2K','MultitrackHubPacoteIA':'Multitrack Hub · Uma imagem e duas legendas'}
