import base64
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'custom_nodes'))
sys.path.insert(0,str(ROOT))
try:
 from servidor02_gemini.multitrackhub import brand
except ImportError:
 brand=None

class MultitrackTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(brand,'Fluxo Multitrack ainda ausente')
  self.brief={'campanha':'teste-multitrack','tema':'Preparação musical','titulo':'Organize o próximo ensaio.','texto':'Confira o repertório | Combine os detalhes | Prepare seu estudo','legenda_facebook':'Uma rotina de preparação para músicos.\n\nComo você se organiza?\n\n#MultitrackHub','legenda_instagram':'Uma rotina de preparação para músicos.\n\nComo você se organiza?\n\n#MultitrackHub','direcao_visual':'Pistas de áudio turquesa e detalhes discretos de estúdio.','link_bio_confirmado':False,'destino':'site'}
 def test_prompt_uses_multitrack_identity_and_current_copy(self):
  p=brand.full_prompt(self.brief)
  for text in ['Multitrack Hub','#00FFFF','#09090B','Organize o próximo ensaio.','Combine os detalhes','sete pistas']:self.assertIn(text,p)
  for text in ['Marca Salão','marcasalao.com.br','Ticket médio','mármore']:self.assertNotIn(text,p)
 def test_rejects_foreign_brief_before_output_or_paid_call(self):
  for change in [{'brand':'marcasalao'},{'campanha':'../marcasalao'},{'titulo':'Conheça o Marca Salão'},{'destino':'https://marcasalao.com.br'}]:
   with self.assertRaises(ValueError):brand.prepare_brief(**(self.brief|change))
 def test_one_generation_is_cached_in_multitrack_directory(self):
  data=io.BytesIO();Image.new('RGB',(1024,1024),'#123456').save(data,'PNG')
  body={'candidates':[{'content':{'parts':[{'inlineData':{'mimeType':'image/png','data':base64.b64encode(data.getvalue()).decode()}}]}}]}
  captured=[]
  def send(req,timeout):captured.append(json.loads(req.data));return io.BytesIO(json.dumps(body).encode())
  with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'GEMINI_API_KEY':'fixture'}),patch('urllib.request.urlopen',send):
   a,meta=brand.generate_artwork(self.brief,temp)
   b,meta2=brand.generate_artwork(self.brief|{'legenda_instagram':'Legenda revisada.'},temp)
   self.assertTrue((Path(temp)/meta['file']).is_file())
   self.assertTrue(meta['file'].startswith('multitrackhub/geracoes-ia/'))
  self.assertEqual(len(captured),1);self.assertEqual(a.tobytes(),b.tobytes());self.assertTrue(meta2['reused'])
  self.assertEqual(captured[0]['generationConfig']['imageConfig'],{'aspectRatio':'1:1','imageSize':'2K'})
  self.assertEqual(base64.b64decode(captured[0]['contents'][0]['parts'][1]['inlineData']['data']),(brand.ASSETS/'referencia-apresentacao.png').read_bytes())
 def test_uncertain_generation_blocks_repeat(self):
  with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'GEMINI_API_KEY':'fixture'}),patch('urllib.request.urlopen',side_effect=TimeoutError) as send:
   with self.assertRaises(RuntimeError):brand.generate_artwork(self.brief,temp)
   with self.assertRaises(ValueError):brand.generate_artwork(self.brief,temp)
   self.assertEqual(send.call_count,1)
 def test_package_has_only_one_image_and_only_multitrack_channels(self):
  with tempfile.TemporaryDirectory() as temp:
   m=brand.export_bundle(self.brief,Image.new('RGB',(1080,1080),'#123456'),temp,'imagem_local')
   p=Path(temp)/m['bundle'];self.assertEqual(m['brand'],'multitrackhub');self.assertEqual(len(list(p.glob('*.png'))),1)
   self.assertEqual(m['postiz']['integrations'],{'facebook':'cmvbss5fn0005msbhhbdy6ing','instagram':'cmvbsudg50007msbh2j4734i4'})
   self.assertEqual(m['postiz']['media_by_network'],{'facebook':'arte-compartilhada-quadrado.png','instagram':'arte-compartilhada-quadrado.png'})
   self.assertIn('https://multitrackhub.com.br',m['captions']['facebook']['text']);self.assertNotIn('link na bio',m['captions']['instagram']['text'])
   self.assertFalse(m['publication_authorized']);self.assertFalse(m['postiz']['drafts_created'])
   with Image.open(p/m['images'][0]['file']) as image:self.assertEqual(image.getpixel((500,500)),(18,52,86))
 def test_downloader_rejects_other_brand_or_mixed_channels(self):
  import multitrackhub_export as exporter
  with tempfile.TemporaryDirectory() as temp:
   m=brand.export_bundle(self.brief,Image.new('RGB',(1080,1080)),temp,'imagem_local');p=Path(temp)/m['bundle']
   out=exporter.download_bundle(m,Path(temp)/'download',lambda item:(p/item['file']).read_bytes());self.assertTrue((out/'arte-compartilhada-quadrado.png').is_file())
   for field in ['brand','channels','bundle']:
    wrong=copy.deepcopy(m)
    if field=='brand':wrong['brand']='marcasalao'
    elif field=='channels':wrong['postiz']['integrations']['facebook']='cmvbegwql0001msbhvdpjy0in'
    else:wrong['bundle']='marcasalao/campanha/run'
    with self.assertRaises(ValueError):exporter.download_bundle(wrong,Path(temp)/field,lambda item:self.fail('Contrato misto não deve baixar'))
 def test_non_square_input_is_not_cropped(self):
  with self.assertRaises(ValueError):brand.prepare_image(Image.new('RGB',(1080,1920)))

if __name__=='__main__':unittest.main()
