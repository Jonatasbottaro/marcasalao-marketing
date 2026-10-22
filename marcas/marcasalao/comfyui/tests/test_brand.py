import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'custom_nodes' / 'servidor02_gemini'))
try:
    import brand
except ImportError:
    brand = None


class BrandTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(brand, 'Composição Marca Salão ainda não implementada')
        self.fields = dict(campanha='teste-agenda', tema='Organização do dia',
                           titulo='Sua agenda, mais organizada',
                           texto='Conheça o agendamento do Marca Salão.',
                           legenda_facebook='Conheça o Marca Salão.',
                           legenda_instagram='Conheça o Marca Salão.',
                           direcao_visual='Fundo abstrato suave, sem pessoas.',
                           link_bio_confirmado=False)

    # Retirar validação permitiria escapar da pasta de saída ou consumir API
    # com uma entrada que não pode ser composta depois.
    def test_rejects_path_escape_and_unrenderable_copy_before_generation(self):
        for changes in [dict(campanha='../escape'), dict(titulo='A' * 500),
                        dict(texto=''), dict(titulo='X' * 90)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                brand.prepare_brief(**(self.fields | changes))

    def test_bio_cta_requires_confirmed_link(self):
        unconfirmed = brand.prepare_brief(**self.fields)
        confirmed = brand.prepare_brief(**(self.fields | {'link_bio_confirmado': True}))
        self.assertNotIn('link na bio', unconfirmed['legendas']['instagram'].lower())
        self.assertIn('link na bio', confirmed['legendas']['instagram'].lower())
        self.assertIn('https://marcasalao.com.br', confirmed['legendas']['facebook'])

    # Pacote incompleto, SHA incorreto, CTA trocado ou formato inválido
    # precisam ser detectados pelo consumidor Hermes.
    def test_exports_six_valid_images_with_real_hashes_and_caption_files(self):
        brief = brand.prepare_brief(**self.fields)
        with tempfile.TemporaryDirectory() as temp:
            manifest = brand.export_bundle(brief, Image.new('RGB', (512, 700), '#668888'), Path(temp), 'imagem_local')
            directory = Path(temp) / manifest['bundle']
            self.assertEqual(len(manifest['images']), 6)
            self.assertEqual(manifest['status'], 'prepared')
            self.assertFalse(manifest['publication_authorized'])
            self.assertTrue(manifest['review_required'])
            seen = set()
            for item in manifest['images']:
                seen.add((item['network'], item['format']))
                p = directory / item['file']
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), item['sha256'])
                with Image.open(p) as im:
                    self.assertEqual(im.mode, 'RGB')
                    self.assertEqual(im.size, {'quadrado': (1080, 1080), 'vertical': (1080, 1350), 'stories': (1080, 1920)}[item['format']])
                caption = (directory / manifest['captions'][item['network']]['file']).read_text()
                if item['network'] == 'facebook':
                    self.assertIn('https://marcasalao.com.br', caption)
                    self.assertIn('descrição', item['cta'])
                else:
                    self.assertNotIn('link na bio', item['cta'].lower())
            self.assertEqual(len(seen), 6)
            self.assertEqual(json.loads((directory / 'manifest.json').read_text()), manifest)
            self.assertEqual(manifest['postiz']['mode'], 'draft_only')
            self.assertEqual(set(manifest['postiz']['integrations']), {'facebook', 'instagram'})
            self.assertTrue((directory / 'README.md').is_file())

    def test_benefits_keep_separate_lines_and_reject_more_than_three(self):
        brief = brand.prepare_brief(**(self.fields | {'texto': 'Receita por período | Ticket médio | Transações recentes'}))
        self.assertEqual(brief['beneficios'], ['Receita por período', 'Ticket médio', 'Transações recentes'])
        with self.assertRaises(ValueError):
            brand.prepare_brief(**(self.fields | {'texto': 'Um | Dois | Três | Quatro'}))

    def test_cta_precedes_question_and_hashtags_without_duplicate_link(self):
        body = 'Mais clareza. 💚\n\n💰 RECEITA\nConsulte atendimentos concluídos.\n\nVocê acompanha seus números?\n\n#MarcaSalão #GestãoDeSalão'
        brief = brand.prepare_brief(**(self.fields | {'legenda_facebook': body, 'legenda_instagram': body}))
        caption = brief['legendas']['facebook']
        self.assertLess(caption.index('https://marcasalao.com.br'), caption.index('Você acompanha'))
        self.assertTrue(caption.endswith('#MarcaSalão #GestãoDeSalão'))
        self.assertEqual(caption.count('https://marcasalao.com.br'), 1)

    def test_long_benefit_word_shrinks_instead_of_rejecting_valid_input(self):
        brief = brand.prepare_brief(**(self.fields | {'texto': 'OrganizaçãoFinanceira'}))
        self.assertEqual(brief['beneficios'], ['OrganizaçãoFinanceira'])

    def test_single_newline_question_hashtags_and_existing_cta(self):
        body = 'Mais clareza.\nVocê acompanha seus números?\n#MarcaSalão'
        brief = brand.prepare_brief(**(self.fields | {'legenda_facebook': body}))
        caption = brief['legendas']['facebook']
        self.assertLess(caption.index('https://marcasalao.com.br'), caption.index('Você acompanha'))
        body = 'Conheça o sistema: https://marcasalao.com.br\n\nVocê já conhece?\n\n#MarcaSalão'
        brief = brand.prepare_brief(**(self.fields | {'legenda_facebook': body}))
        self.assertEqual(brief['legendas']['facebook'].count('https://marcasalao.com.br'), 1)

    def test_title_balances_three_lines_without_single_word_orphan(self):
        face, wrapped, size = brand.title_layout('Mais clareza nas finanças do seu salão.')
        self.assertEqual(' '.join(wrapped), 'Mais clareza nas finanças do seu salão.')
        self.assertEqual(len(wrapped), 3)
        self.assertTrue(all(len(line.split()) >= 2 for line in wrapped))
        self.assertLess(max(face.getlength(line) for line in wrapped) - min(face.getlength(line) for line in wrapped), 200)

    def test_repeated_campaign_preserves_previous_bundle(self):
        brief = brand.prepare_brief(**self.fields)
        with tempfile.TemporaryDirectory() as temp:
            image = Image.new('RGB', (100, 100))
            first = brand.export_bundle(brief, image, Path(temp), 'imagem_local')
            original = (Path(temp) / first['bundle'] / 'manifest.json').read_bytes()
            second = brand.export_bundle(brief, image, Path(temp), 'imagem_local')
            self.assertNotEqual(first['bundle'], second['bundle'])
            self.assertEqual((Path(temp) / first['bundle'] / 'manifest.json').read_bytes(), original)

    def test_rejects_tampered_brief_before_export(self):
        brief = brand.prepare_brief(**self.fields)
        brief['campanha'] = '../escape'
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
            brand.export_bundle(brief, Image.new('RGB', (100, 100)), Path(temp), 'imagem_local')


if __name__ == '__main__':
    unittest.main()
