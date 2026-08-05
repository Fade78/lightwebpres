# Third-party code in lightwebpres

`lightwebpres` is a single file, so third-party code inside it is not
obvious from a directory listing. This is the exhaustive list.

## QR Code Generator for JavaScript — Kazuhiko Arase, MIT

The QR encoder that draws the share code — `qrEncode` and the `QR*`
helpers it closes over — is derived from Kazuhiko Arase's QR Code
Generator for JavaScript (<http://www.d-project.com/>,
<https://github.com/kazuhikoarase/qrcode-generator>), Copyright (c) 2009
Kazuhiko Arase, licensed under the MIT license.

It lives inside the `TEMPLATE_NAV_JS` template, and the MIT notice is
embedded in that template rather than kept here alongside it. That is
deliberate: MIT requires the copyright and permission notice to travel
with every copy, and this code is copied into every series scaffolded by
`lightwebpres install` (as `templates/nav.js`) and into every page a
build writes. A notice that lived only in this file would be left behind
by the very act of using the tool.

If you edit `TEMPLATE_NAV_JS`, do not remove that comment block, and do
not move it out of the template.

"QR Code" is a registered trademark of DENSO WAVE INCORPORATED.

## Nothing else

Everything else in `lightwebpres` — the page, index and series-nav
templates, the layout skeleton, the theme property registry and its
catalogue, the navigation and index scripts other than the encoder above,
the Markdown conversion, the typography engine and the language packs —
is original to this project.

The web front end under `web/` vendors Pyodide; see the notices in
`web/vendor/`.
