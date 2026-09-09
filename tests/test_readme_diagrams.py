"""Renderer-independent contracts for the README's generated diagrams."""

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "build_readme_diagrams.py"
NS = {"s": "http://www.w3.org/2000/svg"}
OUTPUTS = {
    "authoring-workflow.svg": (1200, 760),
    "authoring-workflow-mobile.svg": (600, 1500),
    "publishing-roles.svg": (1200, 960),
    "publishing-roles-mobile.svg": (600, 1990),
}


class ReadmeDiagramTests(unittest.TestCase):
    def test_desktop_and_mobile_pictures_keep_text_inside_the_diagram(self):
        try:
            result = subprocess.run(
                ['node', str(ROOT / 'tests/readme_diagrams_e2e.cjs')],
                cwd=ROOT, env={**os.environ, 'TMPDIR': str(ROOT / 'work/tmp')},
                capture_output=True, text=True, timeout=120)
        except FileNotFoundError:
            self.skipTest('Node unavailable on supplied PATH')
        if result.returncode == 77 or "Executable doesn't exist" in result.stderr:
            self.skipTest('Playwright/Chromium unavailable in supplied environment')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_committed_diagrams_are_exact_fresh_output(self):
        spec = importlib.util.spec_from_file_location("readme_diagram_generator", SCRIPT)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        rendered = generator.render_diagrams()
        self.assertEqual(set(rendered), set(OUTPUTS))
        self.assertEqual(rendered, generator.render_diagrams())
        for name, data in rendered.items():
            with self.subTest(name=name):
                self.assertEqual((ROOT / "generated" / name).read_bytes(), data)
        result = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_labels_and_relationships_preserve_alternatives_and_roles(self):
        expected = {
            "authoring-workflow": {
                ("human", "source", "alternative"),
                ("steered-agent", "source", "alternative"),
                ("autonomous-agent", "source", "alternative"),
                ("source", "build", "resource"),
                ("build", "document", "resource"),
            },
            "publishing-roles": {
                ("architects", "configured-build", "resource"),
                ("makers", "configured-build", "resource"),
                ("integrators", "configured-build", "orchestration"),
                ("configured-build", "readers", "resource"),
                ("configured-build", "presenters", "resource"),
                ("configured-build", "publishers", "resource"),
            },
        }
        required_labels = {
            "authoring-workflow": {
                "Human writes", "Human steers an agent", "Autonomous agent",
                "An external brief or task;", "Same editable files", "LWP Markdown",
                "+ images", "series.json", "(series config)", "LightWebPres",
                "CLI or browser", "Same executable", "HTML + assets",
                "Agents are external to LightWebPres.", "Your document",
                "Read and present;", "share the files.",
            },
            "publishing-roles": {
                "Document architects", "Articles, order, tags, languages",
                "series.json: series config", "Theme & kit makers",
                "Themes, layouts, presets", "kit compose: selected files",
                "into a self-contained kit.", "Own or builtin references;",
                "no live links to other kits.", "Integrators",
                "People or external agents", "run CLI / CI / browser builds",
                "and check outputs.", "Build configured", "content + appearance",
                "LightWebPres", "CLI or browser", "into HTML + assets.",
                "Readers", "Follow sources;", "choose reading views.",
                "Presenters", "Navigate and zoom;", "browser print / PDF.",
                "Publishers", "Share files or deploy", "a static site yourself.",
                "Commons is a collection, not an identity.",
                "People or agents can fill these roles.",
                "Hosting is a separate step.",
            },
        }
        for scene, relations in expected.items():
            desktop_labels = None
            for suffix in ("", "-mobile"):
                with self.subTest(scene=scene, suffix=suffix):
                    root = ET.parse(ROOT / "generated" / (scene + suffix + ".svg")).getroot()
                    labels = [node.text for node in root.findall(".//s:text", NS)]
                    self.assertTrue(required_labels[scene].issubset(labels))
                    if desktop_labels is None:
                        desktop_labels = labels
                    self.assertEqual(labels, desktop_labels)
                    if scene == "authoring-workflow":
                        self.assertEqual(labels.count("OR"), 2)
                    edges = root.findall(".//s:path[@data-from]", NS)
                    self.assertEqual(len(edges), len(relations))
                    self.assertEqual({(e.get("data-from"), e.get("data-to"),
                                       e.get("data-kind")) for e in edges}, relations)
                    nodes = {n.get("id") for n in root.findall(".//s:g[@data-node]", NS)}
                    for edge in edges:
                        self.assertIn(edge.get("data-from"), nodes)
                        self.assertIn(edge.get("data-to"), nodes)
                        self.assertEqual(edge.get("marker-end"), "url(#arrow)")
                        self.assertEqual("stroke-dasharray" in edge.attrib,
                                         edge.get("data-kind") == "orchestration")

    def test_svg_integrity_accessibility_and_embedded_references(self):
        allowed = {"svg", "title", "desc", "defs", "marker", "path", "rect",
                   "circle", "g", "text"}
        for name, (width, height) in OUTPUTS.items():
            with self.subTest(name=name):
                data = (ROOT / "generated" / name).read_bytes()
                self.assertNotIn(b"<!DOCTYPE", data)
                self.assertNotIn(b"<!ENTITY", data)
                self.assertNotIn(b"Fileshed", data)
                root = ET.fromstring(data)
                self.assertEqual(root.tag, "{" + NS["s"] + "}svg")
                self.assertEqual(root.get("width"), str(width))
                self.assertEqual(root.get("height"), str(height))
                self.assertEqual(root.get("viewBox"), "0 0 {} {}".format(width, height))
                self.assertEqual(root.get("role"), "img")
                ids = [n.get("id") for n in root.iter() if "id" in n.attrib]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual(root.get("aria-labelledby"), "diagram-title diagram-desc")
                for tag in ("title", "desc"):
                    element = root.find("s:" + tag, NS)
                    self.assertIsNotNone(element)
                    self.assertEqual(element.get("id"), "diagram-" + tag)
                    self.assertTrue(element.text.strip())
                for node in root.iter():
                    self.assertIn(node.tag.split("}", 1)[-1], allowed)
                    for attr, value in node.attrib.items():
                        self.assertFalse(attr.lower().startswith("on"))
                        self.assertNotIn("href", attr.lower())
                        self.assertNotEqual(attr, "style")
                        if "url(" in value:
                            self.assertRegex(value, r"^url\(#[\w-]+\)$")
                            self.assertIn(re.fullmatch(r"url\(#([\w-]+)\)", value)[1], ids)
                    if node.tag == "{" + NS["s"] + "}text":
                        self.assertGreaterEqual(float(node.get("font-size")), 22)
                        self.assertGreaterEqual(float(node.get("x")), 0)
                        self.assertLess(float(node.get("x")), width)
                        self.assertGreaterEqual(float(node.get("y")), 22)
                        self.assertLess(float(node.get("y")), height)


if __name__ == "__main__":
    unittest.main()
