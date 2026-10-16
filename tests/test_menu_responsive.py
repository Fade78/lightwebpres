"""Presenter menu labels must remain readable on phones and high-resolution screens."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

if __package__:
    from .test_lightwebpres import run
else:
    from test_lightwebpres import run

ROOT = Path(__file__).resolve().parents[1]


class MenuResponsiveLayout(unittest.TestCase):
    def test_controls_reflow_with_viewport_and_type_size_in_both_locales(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp', prefix='menu-layout-') as temporary:
            root = Path(temporary)
            (root / 'sources').mkdir()
            (root / 'series.json').write_text(json.dumps({
                'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
            (root / 'sources/a.md').write_text(
                '<!-- lwp:meta -->\n---\n\n<!-- lwp:slide:cover -->\nslug: cover\n# Menu layout\n', encoding='utf-8')
            env = {**os.environ, 'TMPDIR': str(ROOT / 'work/tmp'),
                   'LWP_THEMES_DIR': str(root / 'themes'),
                   'LWP_COMMONS_DIR': str(root / 'commons'),
                   'LWP_IDENTITY_KITS_DIR': str(root / 'kits')}
            urls = []
            for lang in ('en', 'fr'):
                output = root / lang
                built = run('build', root, '--output', output, '--lang', lang, env=env)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                urls.append((output / 'a.html').as_uri())
            try:
                checked = subprocess.run(
                    ['node', str(ROOT / 'tests/menu_responsive_e2e.cjs'), *urls],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
            except FileNotFoundError:
                self.skipTest('Node unavailable in supplied environment')
            if checked.returncode == 77:
                self.skipTest(checked.stderr.strip())
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            for engine in ('chromium', 'firefox'):
                self.assertIn(engine + ': responsive presenter menu checks passed', checked.stdout)
