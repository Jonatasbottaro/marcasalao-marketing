import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'custom_nodes'))
sys.path.insert(0,str(ROOT))
from servidor02_gemini import artwork, brand
import marcasalao_export as exporter
from PIL import Image

class SharedSquareTests(unittest.TestCase):
    def setUp(self):
        self.brief=json.loads((ROOT/'exemplo-brief.json').read_text())

    def test_shared_art_has_neutral_cta_and_forbids_other_ratios(self):
        prompt=artwork.full_prompt(self.brief,'compartilhado','quadrado')
        self.assertIn('Conheça o Marca Salão',prompt)
        self.assertNotIn('Acesse o link na bio',prompt)
        self.assertNotIn('Acesse o link da descrição',prompt)
        with self.assertRaises(ValueError): artwork.full_prompt(self.brief,'compartilhado','stories')

    def test_one_physical_square_with_distinct_captions_and_safe_download(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest=brand.export_bundle(self.brief,None,temp,'imagem_local',shared_image=Image.new('RGB',(1080,1080),'#123456'))
            folder=Path(temp)/manifest['bundle']
            self.assertEqual(len(list(folder.glob('*.png'))),1)
            self.assertEqual(len(manifest['images']),1)
            self.assertEqual(manifest['images'][0]['network'],'compartilhado')
            self.assertEqual(manifest['postiz']['media_by_network'],{'facebook':'arte-compartilhada-quadrado.png','instagram':'arte-compartilhada-quadrado.png'})
            self.assertIn('https://marcasalao.com.br',manifest['captions']['facebook']['text'])
            self.assertIn('link na bio',manifest['captions']['instagram']['text'])
            self.assertFalse(manifest['publication_authorized'])
            self.assertFalse(manifest['postiz']['drafts_created'])
            with Image.open(folder/manifest['images'][0]['file']) as image:
                self.assertEqual(image.getpixel((500,500)),(18,52,86))
            result=exporter.download_bundle(manifest,Path(temp)/'download',lambda item:(folder/item['file']).read_bytes())
            self.assertEqual(len(list(result.glob('*.png'))),1)
            manifest['postiz']['media_by_network']['instagram']='imagem-inexistente.png'
            with self.assertRaises(ValueError): exporter.download_bundle(manifest,Path(temp)/'unsafe',lambda item:self.fail('Manifesto inválido não deve baixar'))

if __name__=='__main__': unittest.main()
