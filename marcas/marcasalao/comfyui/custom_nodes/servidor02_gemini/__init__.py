import io
import math
from .client import generate


class GeminiText:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'pedido': ('STRING', {'multiline': True, 'default': 'Escreva um título curto em português brasileiro.'}),
            'orientacoes': ('STRING', {'multiline': True, 'default': 'Não invente funcionalidades, preços ou resultados. Responda em português brasileiro.'}),
        }}

    RETURN_TYPES = ('STRING',)
    RETURN_NAMES = ('texto',)
    FUNCTION = 'run'
    CATEGORY = 'Servidor02/Gemini API'
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Cada execução explícita representa uma nova solicitação à API.
        return math.nan

    def run(self, pedido, orientacoes):
        text, _ = generate(pedido, 'texto', orientacoes)
        return {'ui': {'text': [text]}, 'result': (text,)}


class GeminiImage(GeminiText):
    REFERENCE = None
    RETURN_TYPES = ('IMAGE', 'STRING')
    RETURN_NAMES = ('imagem', 'texto')
    OUTPUT_NODE = False

    def run(self, pedido, orientacoes):
        import numpy as np
        import torch
        from PIL import Image, UnidentifiedImageError
        from pathlib import Path
        reference = (Path(__file__).parent / 'assets' / self.REFERENCE).read_bytes() if self.REFERENCE else None
        text, data = generate(pedido, 'imagem', orientacoes, reference=reference)
        try:
            with Image.open(io.BytesIO(data)) as source:
                image = source.convert('RGB')
                pixels = np.array(image).astype(np.float32) / 255.0
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
            raise RuntimeError('O provedor retornou uma imagem que não pode ser aberta com segurança.') from None
        return torch.from_numpy(pixels).unsqueeze(0), text


NODE_CLASS_MAPPINGS = {'Servidor02GeminiTexto': GeminiText, 'Servidor02GeminiImagem': GeminiImage}
NODE_DISPLAY_NAME_MAPPINGS = {'Servidor02GeminiTexto': 'Gemini API direta · Texto', 'Servidor02GeminiImagem': 'Gemini API direta · Imagem'}


class MarcaSalaoBrief:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'campanha': ('STRING', {'default': 'agenda-organizada'}),
            'tema': ('STRING', {'default': 'Gestão do salão'}),
            'titulo': ('STRING', {'multiline': True, 'default': 'Sua agenda, mais organizada'}),
            'texto': ('STRING', {'multiline': True, 'default': 'Agenda organizada | Atendimento com clareza | Gestão do salão'}),
            'legenda_facebook': ('STRING', {'multiline': True, 'default': 'Organize a rotina do seu salão com o Marca Salão.'}),
            'legenda_instagram': ('STRING', {'multiline': True, 'default': 'Organize a rotina do seu salão com o Marca Salão.'}),
            'direcao_visual': ('STRING', {'multiline': True, 'default': 'Cenário realista de salão, mármore branco, planta lateral, espelho dourado e agenda menta no canto inferior direito.'}),
            'link_bio_confirmado': ('BOOLEAN', {'default': False}),
        }}

    RETURN_TYPES = ('STRING', 'MS_BRIEF')
    RETURN_NAMES = ('pedido_imagem', 'brief_validado')
    FUNCTION = 'run'
    CATEGORY = 'Marca Salão'

    def run(self, **kwargs):
        from .brand import prepare_brief, image_prompt
        brief = prepare_brief(**kwargs)
        return image_prompt(brief), brief


class MarcaSalaoPackage:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'brief': ('MS_BRIEF',), 'imagem': ('IMAGE',),
                             'origem': (['gemini', 'imagem_local'],)}}

    RETURN_TYPES = ('STRING',)
    RETURN_NAMES = ('manifest_json',)
    FUNCTION = 'run'
    CATEGORY = 'Marca Salão'
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return math.nan

    def run(self, brief, imagem, origem):
        import json
        from pathlib import Path
        import numpy as np
        from PIL import Image
        import folder_paths
        from .brand import export_bundle
        if len(imagem.shape) != 4 or imagem.shape[0] != 1:
            raise ValueError('Use uma única imagem de apoio por pacote.')
        pixels = np.clip(imagem[0].cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
        manifest = export_bundle(brief, Image.fromarray(pixels), Path(folder_paths.get_output_directory()), origem)
        previews = [{'filename': item['file'], 'subfolder': manifest['bundle'], 'type': 'output'} for item in manifest['images']]
        text = json.dumps(manifest, ensure_ascii=False, indent=2)
        return {'ui': {'images': previews, 'text': [text]}, 'result': (text,)}


NODE_CLASS_MAPPINGS.update({'MarcaSalaoBrief': MarcaSalaoBrief, 'MarcaSalaoPackage': MarcaSalaoPackage})
NODE_DISPLAY_NAME_MAPPINGS.update({'MarcaSalaoBrief': 'Marca Salão · Brief e texto', 'MarcaSalaoPackage': 'Marca Salão · Compor e exportar pacote'})


class MarcaSalaoScene(GeminiImage):
    REFERENCE = 'referencia-financeiro.png'
    CATEGORY = 'Marca Salão'


NODE_CLASS_MAPPINGS['MarcaSalaoGeminiCenario'] = MarcaSalaoScene
NODE_DISPLAY_NAME_MAPPINGS['MarcaSalaoGeminiCenario'] = 'Marca Salão · Cenário Gemini com referência aprovada'
