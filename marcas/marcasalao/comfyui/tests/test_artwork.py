import base64
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'custom_nodes'))
try:
    from servidor02_gemini import artwork
except ImportError:
    artwork = None

class ArtworkTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(artwork, 'Fluxo de arte integral IA ainda não implementado')
        self.brief=json.loads((Path(__file__).resolve().parents[1]/'exemplo-brief.json').read_text())

    def test_full_art_prompt_uses_current_copy_and_network_cta(self):
        self.brief['titulo']='Sua rotina com mais clareza'
        self.brief['texto']='Agenda organizada | Atendimento com clareza'
        p=artwork.full_prompt(self.brief,'facebook','vertical')
        self.assertIn('Sua rotina com mais clareza',p)
        self.assertIn('Agenda organizada',p)
        self.assertIn('Acesse o link da descrição',p)
        self.assertNotIn('Mais clareza nas finanças',p)
        self.assertNotIn('Ticket médio',p)
        p=artwork.full_prompt(self.brief,'instagram','stories')
        self.assertIn('Acesse o link na bio',p)
        self.brief['link_bio_confirmado']=False
        self.assertNotIn('Acesse o link na bio',artwork.full_prompt(self.brief,'instagram','quadrado'))

    def test_completed_generation_is_reused_without_second_provider_call(self):
        data=io.BytesIO();Image.new('RGB',(1024,1024),'#246669').save(data,'PNG')
        body={'candidates':[{'content':{'parts':[{'inlineData':{'mimeType':'image/png','data':base64.b64encode(data.getvalue()).decode()}}]}}]}
        captured=[]
        def send(req,timeout):
            captured.append(json.loads(req.data));return io.BytesIO(json.dumps(body).encode())
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{'GEMINI_API_KEY':'fixture','GEMINI_IMAGE_MODEL':'gemini-test'}), patch('urllib.request.urlopen',send):
            first,meta=artwork.generate_artwork(self.brief,'facebook','quadrado',Path(temp))
            again,meta2=artwork.generate_artwork(self.brief,'facebook','quadrado',Path(temp))
        self.assertEqual(len(captured),1)
        self.assertEqual(first.tobytes(),again.tobytes())
        self.assertEqual(meta['sha256'],meta2['sha256'])
        self.assertTrue(meta2['reused'])
        self.assertEqual(captured[0]['generationConfig']['imageConfig'],{'aspectRatio':'1:1','imageSize':'2K'})

    def test_uncertain_previous_request_blocks_a_second_paid_call(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{'GEMINI_API_KEY':'fixture'}), patch('urllib.request.urlopen',side_effect=TimeoutError) as send:
            with self.assertRaises(RuntimeError): artwork.generate_artwork(self.brief,'facebook','quadrado',Path(temp))
            with self.assertRaises(ValueError): artwork.generate_artwork(self.brief,'facebook','quadrado',Path(temp))
            self.assertEqual(send.call_count,1)

    def test_revision_requests_only_an_explicit_new_generation(self):
        data=io.BytesIO();Image.new('RGB',(1024,1024),'#246669').save(data,'PNG')
        body={'candidates':[{'content':{'parts':[{'inlineData':{'mimeType':'image/png','data':base64.b64encode(data.getvalue()).decode()}}]}}]}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{'GEMINI_API_KEY':'fixture'}), patch('urllib.request.urlopen',side_effect=lambda *a,**k:io.BytesIO(json.dumps(body).encode())) as send:
            artwork.generate_artwork(self.brief,'facebook','quadrado',Path(temp),revision=1)
            artwork.generate_artwork(self.brief,'facebook','quadrado',Path(temp),revision=1)
            artwork.generate_artwork(self.brief,'facebook','quadrado',Path(temp),revision=2)
            self.assertEqual(send.call_count,2)

    def test_wrong_aspect_ratio_is_rejected_instead_of_cropping_complete_art(self):
        with self.assertRaises(ValueError): artwork.prepare_image(Image.new('RGB',(1024,1024)),'stories')
        src=Image.new('RGB',(1600,2000),'#123456')
        self.assertEqual(artwork.prepare_image(src,'vertical').size,(1080,1350))

    def test_full_art_export_preserves_pixels_without_local_text_overlay(self):
        from servidor02_gemini import brand
        brief=brand.prepare_brief(**self.brief)
        images={(n,f):Image.new('RGB',size,'#123456') for n in brand.INTEGRATIONS for f,size in brand.FORMATS.items()}
        with tempfile.TemporaryDirectory() as temp:
            m=brand.export_bundle(brief,None,Path(temp),'gemini',artworks=images)
            for item in m['images']:
                with Image.open(Path(temp)/m['bundle']/item['file']) as image:
                    self.assertEqual(image.getpixel((540,100)),(18,52,86))
                    self.assertEqual(image.getpixel((120,600)),(18,52,86))
            self.assertEqual(m['visual_standard'],'arte-integral-ia-v3')
            self.assertFalse(m['publication_authorized'])
            images.pop(('instagram','stories'))
            with self.assertRaises(ValueError): brand.export_bundle(brief,None,Path(temp),'gemini',artworks=images)

if __name__=='__main__': unittest.main()
