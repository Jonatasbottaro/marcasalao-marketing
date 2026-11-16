import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest

import video_studio


class StudioAstryxFrontendTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        ws_tmp = os.path.join(self.repo_root, '.workspace', 'tmp')
        os.makedirs(ws_tmp, exist_ok=True)
        self.temp_dir = tempfile.mkdtemp(prefix='studio-astryx-test-', dir=ws_tmp)
        os.makedirs(os.path.join(self.temp_dir, 'studio'), exist_ok=True)
        self.studio_dir = os.path.join(self.temp_dir, 'studio')
        shutil.copy2(os.path.join(self.repo_root, 'tools', 'studio', 'index.html'), os.path.join(self.studio_dir, 'index.html'))

        self.server, self.studio = video_studio.make_server(self.repo_root, 0, auto_start_queue=False)
        self.studio.studio_dir = self.studio_dir
        self.port = self.server.server_address[1]
        self.studio.port = self.port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _get(self, path):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('GET', path, headers={'Host': f'127.0.0.1:{self.port}'})
        resp = conn.getresponse()
        body = resp.read()
        headers = dict(resp.getheaders())
        conn.close()
        return resp.status, headers, body

    def test_index_fallback_without_frontend_dist(self):
        status, headers, body = self._get('/')
        self.assertEqual(status, 200)
        html = body.decode('utf-8')
        self.assertIn('id="home-legacy-root"', html)
        self.assertIn('id="home-astryx-root"', html)
        self.assertIn('id="queue-legacy-root"', html)
        self.assertIn('id="queue-astryx-root"', html)
        self.assertIn('id="review-package-legacy-root"', html)
        self.assertIn('id="review-package-astryx-root"', html)
        self.assertNotIn('/static/frontend/', html)

    def test_index_injects_manifest_and_serves_assets_when_dist_exists(self):
        dist_dir = os.path.join(self.studio_dir, 'frontend', 'dist')
        assets_dir = os.path.join(dist_dir, 'assets')
        vite_dir = os.path.join(dist_dir, '.vite')
        os.makedirs(assets_dir, exist_ok=True)
        os.makedirs(vite_dir, exist_ok=True)

        js_name = 'main-test123.js'
        css_name = 'main-test123.css'
        with open(os.path.join(assets_dir, js_name), 'w', encoding='utf-8') as f:
            f.write('console.log("astryx-pilot");\n')
        with open(os.path.join(assets_dir, css_name), 'w', encoding='utf-8') as f:
            f.write('.astryx-home-pilot { display: flex; }\n')
        with open(os.path.join(vite_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
            json.dump({
                'src/main.jsx': {
                    'file': f'assets/{js_name}',
                    'css': [f'assets/{css_name}'],
                    'isEntry': True,
                }
            }, f)

        status, _, body = self._get('/')
        self.assertEqual(status, 200)
        html = body.decode('utf-8')
        self.assertIn(f'<link rel="stylesheet" href="/static/frontend/assets/{css_name}">', html)
        self.assertIn(f'<script type="module" src="/static/frontend/assets/{js_name}"></script>', html)

        st_js, hdr_js, body_js = self._get(f'/static/frontend/assets/{js_name}')
        self.assertEqual(st_js, 200)
        self.assertIn('application/javascript', hdr_js.get('Content-Type', ''))
        self.assertIn(b'astryx-pilot', body_js)

        st_css, hdr_css, body_css = self._get(f'/static/frontend/assets/{css_name}')
        self.assertEqual(st_css, 200)
        self.assertIn('text/css', hdr_css.get('Content-Type', ''))
        self.assertIn(b'.astryx-home-pilot', body_css)

        st_bad, _, _ = self._get('/static/frontend/../../index.html')
        self.assertEqual(st_bad, 404)


if __name__ == '__main__':
    unittest.main()
