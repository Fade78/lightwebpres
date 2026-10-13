"""Guard the internal names documented as consumed by the separate GUI."""

import ast
import inspect
from pathlib import Path
import unittest

if __package__:
    from .test_lightwebpres import load_lightwebpres_module
else:
    from test_lightwebpres import load_lightwebpres_module


ROOT = Path(__file__).resolve().parents[1]


class GuiConsumerContract(unittest.TestCase):
    def test_vendored_executable_keeps_its_gui_entry_points(self):
        # The GUI vendors this executable, but its repository is not part of
        # this suite. Protect the effective contract documented in the spec.
        lwp = load_lightwebpres_module()
        for name in ('build_article', 'load_language', 'TypoEngine'):
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(lwp, name, None)), name)
        self.assertIsInstance(lwp.THEMES, dict)
        self.assertTrue(lwp.THEMES)
        self.assertEqual(
            list(inspect.signature(lwp.build_article).parameters)[:8],
            ['source_path', 'sources_dir', 'series_data', 'current_file',
             'css', 'nav_js', 'typo_engine', 'strings'])
        self.assertIn('strings', lwp.load_language(None, 'en'))

    def test_vendored_git_glue_keeps_the_archive_locator(self):
        # Importing this file in CPython would require Pyodide. An AST check
        # catches a renamed or newly required argument without a fake runtime.
        module = ast.parse((ROOT / 'web' / 'git_sync.py').read_text(encoding='utf-8'))
        locator = next((node for node in module.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == '_find_series_dir_in_archive'), None)
        self.assertIsNotNone(locator)
        positional = locator.args.posonlyargs + locator.args.args
        self.assertEqual(len(positional) - len(locator.args.defaults), 1,
                         'GUI passes one required positional archive root')


if __name__ == '__main__':
    unittest.main()
