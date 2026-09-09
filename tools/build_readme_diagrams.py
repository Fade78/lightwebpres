#!/usr/bin/env python3
"""Generate the README's self-contained SVG diagrams, or check their bytes."""

import argparse
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAVY = "#0e2a43"
AMBER = "#ffc857"
TEAL = "#167d8d"
PAPER = "#f7f4ec"


class SVG:
    def __init__(self, width, height, title, description):
        self.parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="{}" height="{}" viewBox="0 0 {} {}" '
            'role="img" aria-labelledby="diagram-title diagram-desc">'.format(
                width, height, width, height),
            '<title id="diagram-title">{}</title>'.format(escape(title)),
            '<desc id="diagram-desc">{}</desc>'.format(escape(description)),
            '<defs><marker id="arrow" viewBox="0 0 10 10" '
            'refX="9" refY="5" markerWidth="8" markerHeight="8" '
            'orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
            '<path d="M 1 1 L 9 5 L 1 9 Z" fill="{}"/>'
            '</marker></defs>'.format(TEAL),
        ]
        self.rect(0, 0, width, height, PAPER, radius=0)

    def rect(self, x, y, width, height, fill, stroke="none", radius=14):
        self.parts.append(
            '<rect x="{}" y="{}" width="{}" height="{}" rx="{}" '
            'fill="{}" stroke="{}" stroke-width="2"/>'.format(
                x, y, width, height, radius, fill, stroke))

    def label(self, x, y, text, size=22, bold=False, color=NAVY):
        self.parts.append(
            '<text x="{}" y="{}" font-family="Arial, Helvetica, sans-serif" '
            'font-size="{}" font-weight="{}" fill="{}">{}</text>'.format(
                x, y, size, 700 if bold else 400, color, escape(text)))

    def icon(self, kind, x, y, color=NAVY):
        shapes = {
            "person": '<circle cx="14" cy="7" r="5"/>'
                      '<path d="M 3 28 V 23 C 3 12 25 12 25 23 V 28"/>',
            "chip": '<rect x="5" y="5" width="20" height="20" rx="3"/>'
                    '<rect x="10" y="10" width="10" height="10" rx="1"/>'
                    '<path d="M 10 0 V 5 M 20 0 V 5 M 10 25 V 30 '
                    'M 20 25 V 30 M 0 10 H 5 M 0 20 H 5 '
                    'M 25 10 H 30 M 25 20 H 30"/>',
            "file": '<path d="M 5 1 H 19 L 27 9 V 29 H 5 Z '
                    'M 19 1 V 9 H 27 M 10 15 H 22 M 10 21 H 22"/>',
            "page": '<rect x="1" y="3" width="28" height="24" rx="2"/>'
                    '<path d="M 1 10 H 29 M 6 16 H 23 M 6 21 H 19"/>',
        }
        self.parts.append(
            '<g transform="translate({} {})" fill="none" stroke="{}" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true">{}</g>'.format(x, y, color, shapes[kind]))

    def card(self, node, box, title, lines, icon, dark=False, accent=False):
        x, y, width, height = box
        self.parts.append('<g id="{}" data-node="{}">'.format(node, node))
        self.rect(x, y, width, height, NAVY if dark else "#ffffff",
                  NAVY if dark else TEAL)
        self.rect(x + 18, y + 15, 104 if icon == "person-agent" else 38, 38,
                  AMBER if accent else PAPER, radius=8)
        if icon == "person-agent":
            self.icon("person", x + 22, y + 19)
            self.label(x + 60, y + 42, "+", bold=True)
            self.icon("chip", x + 86, y + 19)
        else:
            self.icon(icon, x + 22, y + 19)
        color = PAPER if dark else NAVY
        self.label(x + 18, y + 79, title, size=24, bold=True, color=color)
        for index, line in enumerate(lines):
            self.label(x + 18, y + 113 + index * 29, line, color=color)
        self.parts.append('</g>')

    def edge(self, source, target, points, kind="resource"):
        path = "M " + " L ".join("{} {}".format(x, y) for x, y in points)
        self.parts.append(
            '<path data-from="{}" data-to="{}" data-kind="{}" d="{}" '
            'fill="none" stroke="{}" stroke-width="2.5" '
            '{}stroke-linejoin="round" marker-end="url(#arrow)"/>'.format(
                source, target, kind, path, TEAL,
                'stroke-dasharray="7 6" ' if kind == "orchestration" else ""))

    def finish(self):
        return ("\n".join(self.parts + ["</svg>"]) + "\n").encode("utf-8")


def authoring_workflow(mobile=False):
    title = "From source to browser"
    svg = SVG(600 if mobile else 1200, 1500 if mobile else 760, title,
              "Three alternatives, not sequential roles: a human writes, a human "
              "steers an external agent, or an autonomous external agent works "
              "from a brief or task. All write the same editable LWP Markdown, "
              "images and series.json configuration. LightWebPres builds these "
              "files through its CLI or browser interface, using the same "
              "executable, into HTML and assets to read, present and share. "
              "Agents are source authors, not native product features.")
    svg.label(32, 50, title, size=32, bold=True)
    svg.label(32, 86, "Three alternative ways to author.")
    svg.label(32, 116, "Agents are external to LightWebPres.")
    actors = [
        ("human", "Human writes", ["Write and revise", "the source."], "person"),
        ("steered-agent", "Human steers an agent",
          ["Brief, review and revise", "with an external agent."], "person-agent"),
        ("autonomous-agent", "Autonomous agent",
         ["An external brief or task;", "the agent writes the source."], "chip"),
    ]
    boxes = {node: (32, 150 + i * 202, 480 if mobile else 320, 164)
             for i, (node, _, _, _) in enumerate(actors)}
    if mobile:
        boxes.update({"source": (80, 788, 440, 224),
                      "build": (80, 1060, 440, 160),
                      "document": (80, 1268, 440, 194)})
    else:
        boxes.update({"source": (406, 322, 252, 224),
                      "build": (698, 342, 210, 184),
                      "document": (944, 342, 224, 184)})
    # Each alternative has its own semantic edge; their common bus is not
    # a sequence connecting one author to the next.
    for node, _, _, _ in actors:
        x, y, width, height = boxes[node]
        points = ([(x + width, y + height / 2), (552, y + height / 2),
                   (552, 758), (300, 758), (300, 788)] if mobile else
                  [(x + width, y + height / 2), (380, y + height / 2),
                   (380, 434), (406, 434)])
        svg.edge(node, "source", points, kind="alternative")
    for source, target in [("source", "build"), ("build", "document")]:
        x, y, width, height = boxes[source]
        tx, ty, tw, th = boxes[target]
        svg.edge(source, target,
                 [(x + width / 2, y + height), (tx + tw / 2, ty)] if mobile
                 else [(x + width, y + height / 2), (tx, ty + th / 2)])
    for node, heading, lines, icon in actors:
        svg.card(node, boxes[node], heading, lines, icon, accent=True)
    for y in (340, 542):
        svg.label(32, y, "OR", bold=True, color=TEAL)
    svg.card("source", boxes["source"], "Same editable files",
             ["LWP Markdown", "+ images", "series.json", "(series config)"], "file")
    svg.card("build", boxes["build"], "LightWebPres",
             ["CLI or browser", "Same executable"], "chip", dark=True, accent=True)
    svg.card("document", boxes["document"], "Your document",
             ["HTML + assets", "Read and present;", "share the files."], "page")
    return svg.finish()


def publishing_roles(mobile=False):
    title = "More roles, one build"
    svg = SVG(600 if mobile else 1200, 1990 if mobile else 960, title,
              "Document architects configure content and series.json; theme "
              "and kit makers supply selected appearance resources. Kit compose "
              "selects files into a self-contained kit with own or builtin "
               "references, not live dependencies on other kits. Integrators "
               "orchestrate builds and check "
              "outputs. Solid arrows carry resources or results; dashed arrows "
              "denote orchestration. A configured LightWebPres build produces "
              "HTML and assets for readers, presenters and publishers. Browser "
              "printing can produce PDF; publishing and hosting are separate "
               "actions. People or external agents can fill these roles. "
               "Commons is a collection, not an identity.")
    svg.label(32, 50, title, size=32, bold=True)
    svg.label(32, 86, "Solid: resources / results")
    svg.label(32, 116, "Dashed: build orchestration")
    inputs = [
        ("architects", "Document architects",
         ["Articles, order, tags, languages", "series.json: series config"], "file"),
        ("makers", "Theme & kit makers",
         ["Themes, layouts, presets", "kit compose: selected files",
          "into a self-contained kit.", "Own or builtin references;",
          "no live links to other kits."], "file"),
        ("integrators", "Integrators",
          ["People or external agents", "run CLI / CI / browser builds",
           "and check outputs."], "chip"),
    ]
    outputs = [
        ("readers", "Readers", ["Follow sources;", "choose reading views."], "person"),
        ("presenters", "Presenters", ["Navigate and zoom;", "browser print / PDF."], "person"),
        ("publishers", "Publishers", ["Share files or deploy", "a static site yourself."], "page"),
    ]
    if mobile:
        boxes = {"architects": (32, 160, 480, 166),
                 "makers": (32, 378, 480, 248),
                 "integrators": (32, 678, 480, 184),
                 "configured-build": (80, 936, 440, 252),
                 "readers": (32, 1262, 480, 160),
                 "presenters": (32, 1474, 480, 160),
                 "publishers": (32, 1686, 480, 160)}
        for node in ("architects", "makers"):
            x, y, width, height = boxes[node]
            svg.edge(node, "configured-build",
                     [(x + width, y + height / 2), (552, y + height / 2),
                      (552, 1062), (520, 1062)])
        svg.edge("integrators", "configured-build",
                 [(272, 862), (272, 936)], kind="orchestration")
        for node, _, _, _ in outputs:
            x, y, width, height = boxes[node]
            svg.edge("configured-build", node,
                     [(300, 1188), (300, 1224), (552, 1224),
                      (552, y + height / 2), (x + width, y + height / 2)])
    else:
        boxes = {"architects": (32, 160, 390, 166),
                 "makers": (32, 368, 390, 248),
                 "integrators": (32, 658, 390, 184),
                 "configured-build": (474, 374, 252, 252),
                 "readers": (810, 192, 358, 160),
                 "presenters": (810, 420, 358, 160),
                 "publishers": (810, 648, 358, 160)}
        svg.edge("architects", "configured-build",
                 [(422, 243), (448, 243), (448, 444), (474, 444)])
        svg.edge("makers", "configured-build", [(422, 492), (474, 492)])
        svg.edge("integrators", "configured-build",
                 [(422, 750), (600, 750), (600, 626)], kind="orchestration")
        for node, _, _, _ in outputs:
            _, y, _, height = boxes[node]
            svg.edge("configured-build", node,
                     [(726, 500), (768, 500), (768, y + height / 2),
                      (810, y + height / 2)])
    for node, heading, lines, icon in inputs + outputs:
        svg.card(node, boxes[node], heading, lines, icon)
    svg.card("configured-build", boxes["configured-build"], "LightWebPres",
             ["Build configured", "content + appearance", "into HTML + assets.",
              "CLI or browser"], "chip", dark=True, accent=True)
    footer = 1894 if mobile else 888
    for index, line in enumerate([
            "Commons is a collection, not an identity.",
            "People or agents can fill these roles.",
            "Hosting is a separate step."]):
        svg.label(32, footer + 30 * index, line)
    return svg.finish()


def render_diagrams():
    return {
        "authoring-workflow.svg": authoring_workflow(),
        "authoring-workflow-mobile.svg": authoring_workflow(mobile=True),
        "publishing-roles.svg": publishing_roles(),
        "publishing-roles-mobile.svg": publishing_roles(mobile=True),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="compare all four committed SVGs without writing")
    args = parser.parse_args()
    stale = []
    for name, data in render_diagrams().items():
        path = ROOT / "generated" / name
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                stale.append(name)
        else:
            path.write_bytes(data)
    if stale:
        parser.exit(1, "Stale or missing README diagrams: {}. "
                    "Run python3 tools/build_readme_diagrams.py\n".format(
                        ", ".join(stale)))
    print("README diagrams {} (4 SVGs).".format("match" if args.check else "generated"))


if __name__ == "__main__":
    main()
