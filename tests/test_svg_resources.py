"""Static SVG images keep their bytes and explain bounded resource findings."""

import base64
import contextlib
import io
import os
import re
import tempfile
import unittest
from unittest import mock
from xml.parsers import expat

if __package__:
    from . import test_lightwebpres as fixtures
else:
    import test_lightwebpres as fixtures


class SvgResources(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(
            dir=fixtures.EXECUTABLE.parent / 'work' / 'tmp')
        self.addCleanup(temporary.cleanup)
        self.root = fixtures.scaffold(
            temporary.name, fixtures.IdentityKitFixtures._article()
            + '\n![Diagram](img/diagram.svg)\n')
        self.image = self.root / 'sources' / 'img' / 'diagram.svg'
        self.image.parent.mkdir()

    def _svg(self, body):
        return ('<svg xmlns="http://www.w3.org/2000/svg" '
                'xmlns:xlink="http://www.w3.org/1999/xlink">\n'
                + body + '\n</svg>\n').encode('utf-8')

    def _build(self, data, verbose=True):
        self.image.write_bytes(data)
        options = ('--verbose',) if verbose else ()
        result = fixtures.run('build', str(self.root), '--inline-images', *options)
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (self.root / 'public' / 'a.html').read_text(encoding='utf-8')
        payloads = re.findall(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)', html)
        self.assertIn(data, [base64.b64decode(value) for value in payloads])
        self.assertNotIn('<svg xmlns=', html)
        return result

    def _reference(self, url, in_paragraph=False):
        image = '![Diagram](' + url + ')'
        if in_paragraph:
            image = 'See ' + image + ' here.'
        (self.root / 'sources' / 'a.md').write_text(
            fixtures.IdentityKitFixtures._article() + '\n' + image + '\n',
            encoding='utf-8')

    def test_ampersand_filename_is_unescaped_before_build_and_audit_read_it(self):
        self.image = self.image.with_name('chart&legend.svg')
        for in_paragraph in (False, True):
            with self.subTest(in_paragraph=in_paragraph):
                self._reference('img/chart&legend.svg', in_paragraph)
                built = self._build(self._svg('<image href="nested.png"/>'))
                self.assertIn(str(self.image) + ':2:', built.stderr)
                audited = fixtures.run('audit', str(self.root), '--verbose')
                self.assertEqual(audited.returncode, 0, audited.stderr)
                self.assertIn(str(self.image) + ':2:', audited.stderr)

    def test_query_and_percent_encoded_filename_use_the_local_file(self):
        for in_paragraph in (False, True):
            with self.subTest(in_paragraph=in_paragraph):
                self._reference('img/%64iagram.svg?v=2&theme=dark', in_paragraph)
                built = self._build(self._svg('<image href="nested.png"/>'))
                self.assertIn(str(self.image) + ':2:', built.stderr)
                audited = fixtures.run('audit', str(self.root), '--verbose')
                self.assertEqual(audited.returncode, 0, audited.stderr)
                self.assertIn(str(self.image) + ':2:', audited.stderr)

    def test_svg_fragments_survive_data_uri_encoding_and_audit(self):
        for fragment, emitted in (
                ('detail', 'detail'),
                ('svgView%28viewBox%280,0,10,10%29%29',
                 'svgView(viewBox(0,0,10,10))'),
                ('detail%22%26%23', 'detail%22%26%23')):
            for in_paragraph in (False, True):
                with self.subTest(fragment=fragment, in_paragraph=in_paragraph):
                    self._reference('img/diagram.svg?v=2#' + fragment, in_paragraph)
                    data = self._svg('<view id="detail" viewBox="0 0 10 10"/>\n'
                                     '<image href="nested.png"/>')
                    built = self._build(data)
                    self.assertIn(str(self.image) + ':3:', built.stderr)
                    html = (self.root / 'public' / 'a.html').read_text(encoding='utf-8')
                    self.assertIn('data:image/svg+xml;base64,'
                                  + base64.b64encode(data).decode('ascii')
                                  + '#' + emitted + '"', html)
                    audited = fixtures.run('audit', str(self.root), '--verbose')
                    self.assertEqual(audited.returncode, 0, audited.stderr)
                    self.assertIn(str(self.image) + ':3:', audited.stderr)

    def test_nonlocal_and_decoded_unsafe_urls_do_not_read_files(self):
        lwp = fixtures.load_lightwebpres_module()
        for url in ('https://example.invalid/image.svg', '//example.invalid/image.svg',
                    'file:///image.svg', 'data:image/svg+xml;base64,PHN2Zy8+', '#detail',
                    'img/%2e%2e/%2e%2e/private.svg', '%2Fprivate.svg',
                    '%5C%5Cserver%5Cimage.svg', 'C%3A/image.svg',
                    'img/diagram.svg%00', 'img/diagram.svg#%0A', 'img/%FF.svg',
                    'img/di\nagram.svg'):
            for inspect_only in (False, True):
                with self.subTest(url=url, inspect_only=inspect_only), \
                        mock.patch.object(type(self.image), 'read_bytes') as read_bytes, \
                        mock.patch.object(type(self.image), 'open') as open_file, \
                        contextlib.redirect_stderr(io.StringIO()):
                    self.assertIsNone(lwp._encode_inline_image(
                        url, self.root / 'sources', inspect_only=inspect_only))
                    read_bytes.assert_not_called()
                    open_file.assert_not_called()

    def test_external_image_explains_image_mode_not_just_offline_failure(self):
        result = self._build(self._svg('<image href="https://example.invalid/map.png"/>'))
        self.assertIn('SVG-as-image: not self-contained', result.stderr)
        self.assertIn('external subresources are blocked even online', result.stderr)
        self.assertIn(str(self.image) + ':2:', result.stderr)
        self.assertIn("blocked subresource 'https://example.invalid/map.png'", result.stderr)
        self.assertIn('embed it as a data URI', result.stderr)

    def test_normal_output_is_a_summary_not_a_resource_dump(self):
        result = self._build(self._svg('<image href="https://example.invalid/map.png"/>'),
                             verbose=False)
        self.assertIn('SVG-as-image: not self-contained', result.stderr)
        self.assertIn('--verbose', result.stderr)
        self.assertNotIn('example.invalid', result.stderr)

    def test_local_nested_image_is_blocked_even_if_the_file_exists(self):
        (self.image.parent / 'nested.png').write_bytes(b'not read by the diagnostic')
        result = self._build(self._svg('<image xlink:href="nested.png"/>'))
        self.assertIn("blocked subresource 'nested.png'", result.stderr)
        self.assertIn('even online', result.stderr)

    def test_fragments_data_uris_and_documentary_links_are_not_dependencies(self):
        data = self._svg(
            '<defs><path id="shape" d="M0 0h1"/></defs>\n'
            '<use href="#shape"/><rect fill="url(#paint)"/>\n'
            '<image href="data:image/png;base64,aGVsbG8="/>\n'
            '<a xlink:href="https://example.invalid/document"><text>Source</text></a>\n'
            '<style>.shape { fill: url("#paint"); } '
            '/* url(ignored.png) */ .label { content: "url(also-ignored.png)"; }</style>')
        result = self._build(data)
        self.assertNotIn('SVG-as-image', result.stderr)

    def test_css_urls_imports_attributes_and_src_are_reported(self):
        result = self._build(self._svg(
            '<style>\n@import "palette.css";\n'
            '@import url("more.css");\n'
            '.a { fill: url(texture.svg#paint); }\n</style>\n'
            '<rect style="filter: url(blur.svg#blur)"/>\n'
            '<rect fill="url (paint.svg#paint)"/>\n'
            '<image src="photo.png"/>'))
        for resource in ('palette.css', 'more.css', 'texture.svg#paint',
                         'blur.svg#blur', 'paint.svg#paint', 'photo.png'):
            self.assertIn("blocked subresource '" + resource + "'", result.stderr)
        self.assertIn(str(self.image) + ':3:', result.stderr)
        self.assertIn(str(self.image) + ':5:', result.stderr)

    def test_xml_stylesheet_processing_instruction_reports_the_dependency(self):
        data = (b'<?xml version="1.0"?>\n'
                b'<?xml-stylesheet type="text/css" href="palette.css?v=2&amp;mode=dark"?>\n'
                + self._svg('<text>Static</text>'))
        built = self._build(data)
        self.assertIn(str(self.image) + ':2:', built.stderr)
        self.assertIn("blocked subresource 'palette.css?v=2&mode=dark'", built.stderr)
        audited = fixtures.run('audit', str(self.root), '--verbose')
        self.assertEqual(audited.returncode, 0, audited.stderr)
        self.assertIn(str(self.image) + ':2:', audited.stderr)
        self.assertIn("blocked subresource 'palette.css?v=2&mode=dark'", audited.stderr)

    def test_processing_instructions_ignore_data_fragments_and_documentary_text(self):
        for pi in (b'<?xml-stylesheet href="data:text/css,.a%7Bfill:red%7D"?>',
                   b'<?xml-stylesheet href="#embedded-style"?>',
                   b'<?xml-stylesheet title="Example href=\'not-a-resource.css\'"?>',
                   b'<?documentation href="not-a-stylesheet.css"?>'):
            with self.subTest(pi=pi):
                built = self._build(pi + self._svg('<text>Static</text>'))
                self.assertNotIn('SVG-as-image', built.stderr)

    def test_scripts_and_event_handlers_explain_static_export_remediation(self):
        result = self._build(self._svg(
            '<script>drawLogo()</script>\n<rect onclick="changeColor()"/>'))
        self.assertIn("'<script>' cannot execute in SVG-as-image", result.stderr)
        self.assertIn("'onclick' cannot execute in SVG-as-image", result.stderr)
        self.assertIn('export a static logo/diagram', result.stderr)
        self.assertNotIn('not self-contained', result.stderr)

    def test_malformed_and_unknown_encoding_inputs_do_not_crash_or_change_bytes(self):
        for data in (b'<svg><image href="nested.png"/>', b'<svg>\xff</svg>',
                     b'<?xml version="1.0" encoding="not-an-encoding"?><svg/>'):
            with self.subTest(data=data):
                result = self._build(data)
                self.assertIn('inspection incomplete:', result.stderr)

    def test_unicode_source_resource_and_svg_bytes_survive(self):
        self.image = self.image.with_name('diagram-\u00e9.svg')
        source = self.root / 'sources' / 'a.md'
        source.write_text(source.read_text(encoding='utf-8').replace(
            'diagram.svg', self.image.name), encoding='utf-8')
        data = self._svg('<text>\u00c9t\u00e9 \u65e5\u672c</text>\n<image href="carte-\u00e9.png"/>')
        result = self._build(data)
        self.assertIn(str(self.image) + ':3:', result.stderr)
        self.assertIn('carte-\u00e9.png', result.stderr)

    def test_utf16_svg_is_inspected_without_transcoding_the_output(self):
        data = ('<?xml version="1.0" encoding="UTF-16"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg">\n'
                '<image href="photo.png"/></svg>').encode('utf-16')
        result = self._build(data)
        self.assertIn(str(self.image) + ':3:', result.stderr)
        self.assertIn("blocked subresource 'photo.png'", result.stderr)

    def test_doctype_is_not_expanded_and_incomplete_inspection_is_explicit(self):
        result = self._build(
            b'<!DOCTYPE svg [<!ENTITY image "nested.png">]>'
            b'<svg><image href="&image;"/></svg>')
        self.assertIn('DTD inspection is not supported', result.stderr)
        self.assertIn('no offline proof is made', result.stderr)

    def test_inspection_has_byte_and_finding_limits(self):
        for data, message in (
                (self._svg('<image href="nested.png"/>\n' * 40),
                 '32-finding inspection limit reached'),
                (b'<svg><!--' + b'x' * (2 * 1024 * 1024) + b'--></svg>',
                 '2 MiB inspection limit exceeded')):
            with self.subTest(message=message):
                result = self._build(data)
                self.assertIn(message, result.stderr)
                for inspection in result.stderr.split('[WARNING]'):
                    self.assertLessEqual(inspection.count('blocked subresource'), 32)

    def test_inspection_only_hook_returns_no_replacement_and_warns(self):
        self.image.write_bytes(self._svg('<image href="nested.png"/>'))
        lwp = fixtures.load_lightwebpres_module()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            value = lwp._encode_inline_image(
                'img/diagram.svg', self.root / 'sources', inspect_only=True)
        self.assertIsNone(value)
        self.assertIn('SVG-as-image: not self-contained', stderr.getvalue())

    def test_diagnostics_are_memoized_only_inside_an_explicit_warning_scope(self):
        self.image.write_bytes(self._svg('<image href="nested.png"/>'))
        lwp = fixtures.load_lightwebpres_module()
        with contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.object(expat, 'ParserCreate', wraps=expat.ParserCreate) as parse:
            for unused in range(2):
                with lwp.collect_warnings() as sink:
                    first = lwp._encode_inline_image('img/diagram.svg', self.root / 'sources')
                    second = lwp._encode_inline_image('img/diagram.svg', self.root / 'sources')
                    self.assertEqual(first, second)
                    self.assertEqual(len(sink.messages), 1)
            self.assertEqual(parse.call_count, 2)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                for unused in range(2):
                    lwp._encode_inline_image('img/diagram.svg', self.root / 'sources')
            self.assertEqual(stderr.getvalue().count('SVG-as-image:'), 2)
            self.assertEqual(parse.call_count, 4)

    def test_memoization_detects_byte_changes_even_with_restored_stat_metadata(self):
        first = self._svg('<image href="first.png"/>')
        second = self._svg('<image href="other.png"/>')
        self.assertEqual(len(first), len(second))
        self.image.write_bytes(first)
        stat = self.image.stat()
        lwp = fixtures.load_lightwebpres_module()
        with contextlib.redirect_stderr(io.StringIO()), lwp.collect_warnings() as sink:
            before = lwp._encode_inline_image('img/diagram.svg', self.root / 'sources')
            self.image.write_bytes(second)
            os.utime(self.image, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            after = lwp._encode_inline_image('img/diagram.svg', self.root / 'sources')
            self.assertEqual(len(sink.messages), 2)
        self.assertEqual(base64.b64decode(before.split(',', 1)[1]), first)
        self.assertEqual(base64.b64decode(after.split(',', 1)[1]), second)

    def test_diagnostic_cache_bounds_entries_key_bytes_and_excludes_large_images(self):
        lwp = fixtures.load_lightwebpres_module()
        for name_size in (1, 1024):
            with self.subTest(name_size=name_size), \
                    contextlib.redirect_stderr(io.StringIO()), lwp.collect_warnings() as sink:
                for index in range(140):
                    lwp._diagnose_svg_image(self._svg(''),
                                            str(self.image) + 'x' * name_size + str(index))
                cache = sink._svg_diagnostics
                self.assertLessEqual(len(cache['keys']), 128)
                self.assertLessEqual(cache['bytes'], 64 * 1024)
                self.assertEqual(cache['bytes'], sum(
                    len(source.encode('utf-8')) + len(digest)
                    for source, digest, verbose in cache['keys']))
                self.assertTrue(all(len(key[1]) == 32 for key in cache['keys']))
                entries = len(cache['keys'])
                lwp._diagnose_svg_image(b'x' * (2 * 1024 * 1024 + 1), self.image)
                self.assertEqual(len(cache['keys']), entries)

    def test_unterminated_css_urls_do_not_cause_backtracking_or_change_bytes(self):
        for css in ('url(' * 16000, 'url(' + ' ' * 64000 + '!'):
            with self.subTest(length=len(css)):
                self._build(self._svg('<style>' + css + '</style>'))

    def test_kit_svg_warns_in_inline_build_and_normal_audit(self):
        fixture = fixtures.IdentityKitFixtures()
        root, identity_kit = fixture._selected_series(self.root)
        image = identity_kit / 'assets' / 'mark.svg'
        data = self._svg('<image href="nested.png"/>')
        image.write_bytes(data)
        built = fixtures.run('build', str(root), '--inline-images', '--verbose')
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertIn(str(image) + ':2:', built.stderr)
        html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn('data:image/svg+xml;base64,'
                      + base64.b64encode(data).decode('ascii'), html)
        audited = fixtures.run('audit', str(root), '--verbose')
        self.assertEqual(audited.returncode, 0, audited.stderr)
        self.assertIn(str(image) + ':2:', audited.stderr)
        self.assertIn("blocked subresource 'nested.png'", audited.stderr)
        self.assertNotIn('No warnings', audited.stdout)


if __name__ == '__main__':
    unittest.main()
