import base64
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'custom_nodes' / 'servidor02_gemini'))
try:
    import client
except ImportError:
    client = None


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(client, 'Cliente Gemini direto ainda não implementado')

    def test_missing_key_never_sends_request(self):
        with patch.dict(os.environ, {}, clear=True), patch('urllib.request.urlopen') as send:
            with self.assertRaisesRegex(RuntimeError, 'GEMINI_API_KEY'):
                client.generate('teste', 'texto', '')
            send.assert_not_called()

    def test_header_key_and_text_response(self):
        response = {'candidates': [{'content': {'parts': [{'text': 'Olá'}]}}]}
        captured = []
        def send(request, timeout):
            captured.append((request, timeout))
            return io.BytesIO(json.dumps(response).encode())
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'fixture-private-value', 'GEMINI_TEXT_MODEL': 'gemini-test'}), patch('urllib.request.urlopen', send):
            text, image = client.generate('Agenda', 'texto', 'Use pt-BR')
        self.assertEqual(text, 'Olá')
        self.assertIsNone(image)
        request, timeout = captured[0]
        self.assertNotIn('fixture-private-value', request.full_url)
        self.assertNotIn('fixture-private-value', request.data.decode())
        self.assertEqual(request.get_header('X-goog-api-key'), 'fixture-private-value')
        payload = json.loads(request.data)
        self.assertEqual(payload['contents'][0]['parts'][0]['text'], 'Agenda')
        self.assertEqual(payload['systemInstruction']['parts'][0]['text'], 'Use pt-BR')
        self.assertLessEqual(timeout, 180)

    def test_image_response(self):
        response = {'candidates': [{'content': {'parts': [{'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(b'png-fixture').decode()}}]}}]}
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'fixture'}), patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())):
            text, image = client.generate('Fundo', 'imagem', '')
        self.assertEqual(image, b'png-fixture')

    def test_quota_error_hides_provider_body(self):
        error = HTTPError('https://google.invalid', 429, 'fixture-private-value', {}, io.BytesIO(b'fixture-private-value'))
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'fixture-private-value'}), patch('urllib.request.urlopen', side_effect=error) as send:
            with self.assertRaises(RuntimeError) as caught:
                client.generate('teste', 'texto', '')
        self.assertIn('429', str(caught.exception))
        self.assertNotIn('fixture-private-value', str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(send.call_count, 1)

    def test_invalid_model_cannot_change_api_host_or_path(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'fixture', 'GEMINI_TEXT_MODEL': '../other?key=value'}), patch('urllib.request.urlopen') as send:
            with self.assertRaisesRegex(RuntimeError, 'modelo'):
                client.generate('teste', 'texto', '')
            send.assert_not_called()

    def test_empty_candidate_is_actionable(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'fixture'}), patch('urllib.request.urlopen', return_value=io.BytesIO(b'{}')):
            with self.assertRaisesRegex(RuntimeError, 'conteúdo'):
                client.generate('teste', 'texto', '')


if __name__ == '__main__':
    unittest.main()
