# AGENTS.md — Guide pour agents (humains, IA, LLM) travaillant sur ce dépôt

Document normatif du dépôt (`specifications.md` §1.1) : il oblige qui
modifie ce dépôt. Il ne dit rien du format lui-même.

À ne pas confondre avec `agent/skills/lightwebpres/SKILL.md`, qui décrit
le **format** à qui écrit un article. Les deux s'adressent à un agent et
ne parlent pas du même métier : ici, comment travailler **sur** l'outil ;
là-bas, ce que l'outil **accepte**.

### Agent Workspace Boundary

Keep all filesystem investigation and work inside this repository. Do not
read, search, write or create agent artifacts outside it, including under
`/opt`, `/tmp`, `/etc`, other repositories or another user's directories.
Do not follow a repository symlink to inspect an external target. An absolute
path mentioned in documentation or returned by a tool is not permission to
access it.

Use repository-local `work/` for agent working material, with `work/tmp/` for
disposable builds, captures and diagnostics. Create `work/tmp/` if needed and
set `TMPDIR="$PWD/work/tmp"` from the repository root before running commands
that allocate temporary files. Explicitly direct captures, profiles and other
tool-specific scratch output there too. Never remove another agent's work.
Keep working material out of commits.

Invoke available tools through the supplied environment or `PATH`; do not
search external installations, install dependencies, change permissions or
request wider filesystem access to complete a check. If a tool cannot run
within these boundaries, stop that check and report it as unverified. Only an
explicit owner instruction can authorize an exception.

Every delegated agent must receive this boundary in its task prompt, including
the repository path, the `work/` scratch requirement and the instruction to
report a blocked check rather than explore outside the workspace. The parent
agent remains responsible for the scope it delegates.

## Commandes essentielles

### Tests (obligatoire avant et après chaque changement)
```bash
python3 tests/run_tests.py                              # obligatoire : parallèle, tous les vCPU (niced +5)
python3 tests/run_tests.py --workers 4                  # override explicite
python3 -m unittest tests.test_lightwebpres              # diagnostic séquentiel : fichier principal seul
python3 -m unittest tests.test_lightwebpres -v          # diagnostic verbeux séquentiel
```

### Vérification compilation
```bash
python3 -m py_compile lightwebpres                    # silencieux = OK
```

### Lancer l'outil
```bash
python3 lightwebpres --help                           # aide : registre live + texte de référence maintenu à la main
python3 lightwebpres <command> [dir] [options]        # usage général
eval "$(python3 lightwebpres completion --shell bash)" # completion tab (optionnel)
```

## Structure du dépôt

### Code et tests
- `lightwebpres` — le code, un seul fichier Python. Pas de dépendances
  externes (stdlib uniquement, Python 3.8+).
- `tests/test_lightwebpres.py` — la suite principale ;
  `tests/run_tests.py` en découvre davantage, dont les volets navigateur.
  Deux registres y cohabitent, voir Conventions : `run(*args)` lance
  l'exécutable en sous-processus, `load_lightwebpres_module()` importe le
  module pour mesurer ce qu'une sortie ne montre pas.
  Les comptes ne sont pas écrits ici : ils changent à chaque lot et un
  nombre faux dans un guide de travail est pire que pas de nombre. Pour
  l'avoir, lancer la suite.

### Documentation permanente (fait foi)
- `specifications.md` — spécification normative du format (référence).
- `GLOSSARY.md` — contrat de vocabulaire partagé (avec `lightwebpres-gui`).
- `README.md`: the English product entry point and quickstart.
- `GUIDE.md`: the English operational manual, with six user routes: Create
  content; Organize a documentary collection; Design and compose identities;
  Read, present and share; Publish and maintain; Integrate and automate.
  These routes cover product use, not engine contribution.
- `DECISIONS.md` — registre pérenne des décisions et des dettes, sur
  six états. Le fichier s'appelait `BACKLOG.md` ; une entrée qui
  s'avérait ne demander aucun travail n'avait alors aucun état où aller.
- `CHANGELOG.md` — ce qui a changé d'une version à l'autre, dans les
  mots de l'annonce. L'entrée **est** le corps de la release GitHub.
- `agent/skills/`: English agent guidance and its index. Keep product
  workflows, exact format mechanics and optional editorial methods distinct.
  Repository contribution rules stay here in `AGENTS.md`, not in a user route.
- `AGENTS.md` — ce document.
- `THIRD-PARTY-NOTICES.md` — licences de ce qui est embarqué.

Write newly authored documentation in English. Translate existing passages
when revising them, but do not expand a targeted correction into a wholesale
translation of the French specification.

### Active Model Redesign

Before changing logical-unit vocabulary, selectors, cascade resolution or the
combined-HTML CLI, read **DECISIONS.md, B67**. Its first increment is implemented:
`--single-html [FILE]`, logical selection scopes and unit indexes. The owner
authorized the physical-output rename in this first lot and explicitly ruled
out legacy handling; preserve that decision, with no alias or migration handler.
`specifications.md` and `GLOSSARY.md` describe the current contract. Persisted
`articles[]`, `page_source`, `page_dest` and related fields remain canonical,
not aliases. Broader wire vocabulary and publication-filter replacement remain
open in B67. Keep its delivery checklist synchronized and disposable probes
under `work/tmp/`; never infer that a proposed follow-up is already available.

### Relevés datés (hors arborescence active)
- Les audits datés et autres relevés sont conservés localement, hors de
  l'arborescence active et de la repo publique, avec leurs mesures et leurs
  conditions. Les nombres qu'ils portent disent l'état du jour de la mesure :
  ils ne se périment pas, et ne se lisent pas comme des affirmations présentes.

### Outillage
- `tools/guide-deck.md` — deck source du guide, à côté du script qui le
  lit (`tools/build_guide.py`, qui assemble `GUIDE.md` comme article).
  Entrée de build, pas documentation : se corrige comme du code.
- `examples/kits/` — source suivie des kits d'identité de
  démonstration. Le kit utilisé par le guide officiel y reste inspectable et
  versionné ; il n'est ni une seconde source du guide ni une sortie générée.
- `examples/first-article/`: tracked article and series sources used by the
  guide and visual comparisons. Build disposable copies, not this source tree.
- `examples/kit-composition/`: three independent source kits and an explicit
  recipe for the self-contained Field Notes kit. The example owns its resource
  selection and licensing explanation; do not replace it with mock output.
- `tools/screenshot-documentation.cjs`: builds the real examples and captures
  the appearance comparison and composition diagram. Regeneration is below.
- `tools/build_readme_diagrams.py`: generates the English authoring and role
  workflow diagrams in desktop and mobile SVG layouts. Run
  `TMPDIR="$PWD/work/tmp" python3 tools/build_readme_diagrams.py`; `--check`
  verifies exact output bytes. Edit the generator, never its four SVG outputs.
  `tests/readme_diagrams_e2e.cjs` checks the README picture selection and SVG
  text bounds in the supplied browser environment, with captures in `work/tmp/`.
- **Deux blocs de ces documents sont générés** et se réécrivent au lieu
  de s'éditer. Chacun a sa garde dans la suite, donc une édition à la
  main ne survit ni au script ni au test :
  - `tools/spec_index.py` — le sommaire de `specifications.md`, dérivé
    des titres. Conscient des blocs de code : §4.2 contient un article
    d'exemple dont les titres de fiche sont des `##`.
  - `tools/decisions_index.py` — l'index de `DECISIONS.md`, dérivé des
    lignes de champs.
- `tools/check_refs.py` — vérifie que chaque `§N.N` du dépôt pointe sur
  une section qui existe. Ne génère rien ; c'est une garde.

### Artefacts régénérables — `generated/`
Sortie de build committée. **Rien ne s'y édite à la main** : la
correction se fait à la source, puis on régénère. Les trois artefacts
HTML ont leur garde de fraîcheur dans la suite, qui compare octet pour
octet ; la planche-contact PNG n'en a pas — c'est une capture d'écran,
pas reproductible à l'octet, à refaire à la main quand la galerie change.
- `generated/themes-gallery.html` — `lightwebpres theme gallery
  generated/themes-gallery.html` (garde :
  `test_the_committed_gallery_is_byte_identical_to_a_fresh_one`).
- `generated/themes-featured.png`: `TMPDIR="$PWD/work/tmp" node
  tools/screenshot-gallery.cjs --featured` captures three actual landscape
  themes. Use the supplied Node/Playwright environment; do not search external
  installations when it is unavailable. No byte-identity guard applies.
- `generated/themes-gallery.png`: `TMPDIR="$PWD/work/tmp" node
  tools/screenshot-gallery.cjs` generates the compact theme contact sheet.
- `generated/guide/` — `python3 tools/build_guide.py`, y compris les assets
  publiés par le kit de démonstration (garde :
  `test_the_committed_guide_is_the_guide_the_tool_makes`, qui compare tout
  l'arbre hors manifestes `.lwp-*`).
- `generated/product-responsive.png` et `generated/product-captures.json` —
  `node tools/screenshot-product.cjs`, depuis `examples/first-article/`.
  Playwright installé résolu par Node (au besoin
  `NODE_PATH="$(npm root -g)"`), Chromium de son cache par défaut ou
  `PW_CHROMIUM_PATH`. Le script vérifie les limites du texte dans les deux
  vrais viewports puis les compose en une comparaison Nebula ; `--check` et la
  suite vérifient les empreintes des entrées et de l’image, pas une identité
  des pixels entre plateformes. Inspecter l’image puis régénérer le guide.
- `generated/appearance-choices.png`, `generated/identity-composition.png`
  and `generated/documentation-captures.json`: regenerate from the repository
  root with `TMPDIR="$PWD/work/tmp" node tools/screenshot-documentation.cjs`.
  Create `work/tmp/` first. Node must resolve an existing Playwright install
  (use `NODE_PATH="$(npm root -g)"` if needed); Chromium comes from its cache
  or `PW_CHROMIUM_PATH`. `PYTHON` can select the Python executable. The script
  builds copies of the first article with native, documentation and Field Notes
  presets and selected source-kit presets, then checks visible text, images,
  overflow and browser errors. The diagram also previews the source compass SVG.
  Run `node tools/screenshot-documentation.cjs --check` to verify input hashes,
  PNG dimensions and output hashes, not pixel identity across platforms.
  Inspect both images, then run
  `TMPDIR="$PWD/work/tmp" python3 tools/build_guide.py` to publish their copies.
  Never edit the PNGs, capture manifest or generated guide copies manually.
- `generated/golden-demo/` — la série démo (`init --theme pop-lemon` +
  `demo` + `build`) committée comme garde d'identité de rendu : tout
  changement de sortie échoue
  (`test_the_committed_golden_demo_is_what_the_tool_builds`). Un
  changement intentionnel se régénère et se commet — le diff **est**
  l'aveu, là où quatre tables de drift tenaient ce rôle à la main et
  ont prouvé leur coût.

### Historical working documents

The former `delete-before-1.0/` tree was removed in the bounded cleanup of
2026-09-09. Its originals were preserved exactly in the ignored local
`work/archive-before-1.0/` before deletion; earlier Git revisions also retain
them. That local copy is not a shipped replacement tree. Older source archives
included the tracked documents: removal from the current tree does not erase
history or previously distributed archives.

**Before removing a working document, retain its reasoning.** A delivered
plan may still contain an undecided question found nowhere else. Record it
in `DECISIONS.md`, with its evidence and uncertainty, before removing the
source. The cleanup dispositions are recorded there; do not recreate a tracked
holding directory or mistake a historical measurement for a current guarantee
(`specifications.md` §1.1). Keep new working material under `work/`.

## Conventions

- **Identity / Preset / Theme** : l'identité est déduite de l'unique référence
  `series_meta.presentation_preset` (`builtin/standard`, `commons/id` ou
  `id@version/preset`). Le label d'identité est fixe ; le défaut désigne une
  sélection, pas une identité. Les kits autonomes suivent
  `lightwebpres.identity-kit/1`, sous `kits/` ou `templates/kits/`, avec
  `LWP_IDENTITY_KITS_DIR`. Commons garde les thèmes dans `themes/`
  (`LWP_THEMES_DIR`) et les presets dans `commons/presets/` (`LWP_COMMONS_DIR`).
  Les origines sont calculées par les chargeurs, jamais déclarées. Pas
  d'extension ni de dépendance entre kits ; `kit compose` produit un kit final
  autonome depuis une recette explicite. Les contrats et exemples sont en
  `specifications.md` §9.9 ; la sortie des assets reste sous
  `public/assets/presentations/`.

- **Parseur CLI fait main** (pas d'argparse) — `parse_cli_options()` + tables
  `_COMMAND_OPTIONS`, `_VALUE_OPTIONS`, `_GLOBAL_OPTIONS`. L'aide (`--help`)
  est un template maintenu à la main ; un test la verrouille contre les
  tables d'options pour qu'elle ne puisse pas dériver en silence.
- **Deux registres de test, et il faut les deux.** Le registre *boîte
  noire* lance l'exécutable en sous-processus (`run(*args)`) et vérifie ce
  qu'un utilisateur obtient : sortie, code de retour, fichiers écrits.
  C'est le registre par défaut pour tout ce qui a une surface CLI.

  Le registre *par introspection* importe le module
  (`load_lightwebpres_module()`, puis `self.lwp.…`) pour mesurer ce qu'une
  sortie ne montre pas : le registre de propriétés, les palettes résolues,
  les ratios de contraste, l'AST de l'exécutable. Une garde qui mesure
  le catalogue ne peut pas le faire en construisant un site par thème.

  Cette convention disait « pas d'import direct des fonctions internes » ;
  c'était faux et cela aurait empêché d'écrire la moitié des gardes de ce
  dépôt. Le vrai critère n'est pas l'import, c'est **ce qu'on affirme** :
  un comportement visible se vérifie par la sortie, une propriété interne
  se mesure par le module.
- **Versionnage sémantique** (spec §13.9) : MAJOR = incompatible, MINOR =
  rétrocompatible. La constante `VERSION` est dans `lightwebpres`.
- **Bumper `VERSION`, c'est ouvrir une section du `CHANGELOG.md`** dans le
  même commit, sous le titre `## Unreleased — X.Y.Z`. Une garde
  (`test_the_version_it_announces_has_a_changelog_entry`) refuse la suite
  si le numéro annoncé n'a pas de section, donc les deux ne peuvent pas
  diverger en silence. La section se remplit au fil du travail, pas le
  jour de la release : c'est ce texte-là, tel quel, qui accompagne la
  release GitHub, et le titre devient `## vX.Y.Z` quand le tag de release est
  créé — sans date, la date vit sur le tag. Un texte, un endroit — un second
  récit du même changement s'écarte du premier en quelques mois.
- **Deux forges, deux rôles.** Le développement se fait en privé sur
  GitLab (`origin`), et le projet est publié de temps en temps sur GitHub
  (`https://github.com/Fade78/lightwebpres`). Les releases publiques sont
  créées sur GitHub, avec le texte de la section correspondante du
  CHANGELOG.
- **Release GitHub sur demande du propriétaire.** Sans demande explicite,
  l'agent ne crée ni tag ni release. Quand le propriétaire demande une
  release, l'agent crée le tag `vX.Y.Z`, le pousse sur `origin`, puis crée la
  release GitHub avec le texte de la section correspondante.
- **Style de commit** : un sujet en phrase, qui dit ce que le changement
  fait — **aucun préfixe**, pas même pour une release. Le corps n'est pas
  replié à 72 colonnes et explique le *pourquoi*, avec les mesures quand
  il y en a.

  Cette ligne annonçait `feat:` / `Docs:` / `Chore:` / `vX.Y.Z:`, et ce
  n'était pas faux à l'écriture : la convention a bel et bien été
  `vX.Y.Z:` jusqu'au 15 août 2026, puis elle a changé sans que ce document
  suive. Depuis, aucun sujet ne porte de préfixe. C'est le mode de
  décomposition à connaître ici — une convention citée de mémoire survit
  à la pratique qu'elle décrit — d'où la règle : **lire le style plutôt
  que ce paragraphe**, avec `git log --format=%s -20`.
- **Un renvoi `§N.N` est une adresse, et trois règles la tiennent.**
  Une garde (`tools/check_refs.py`) les fait respecter.
  - **Sans qualificatif, c'est `specifications.md`.** C'est l'usage de
    tout le dépôt. Cinq renvois à une section 9.2.1 avaient survécu à la
    refonte du §9 qui a déplacé la matrice de partage en §9.3.4.
  - **Un renvoi qualifié doit nommer ce que son lecteur peut atteindre.**
    The executable is a single-file deliverable. It once carried 31
    citations of CLI design documents formerly tracked under
    `delete-before-1.0/`. Those documents accompanied older source archives,
    not the standalone executable. The adjacent comments already explained
    the reasoning, so only the unreachable addresses were removed.
  - **Un renvoi mort s'écrit sans le signe.** `§` veut dire « va voir »,
    et une section supprimée ne mène nulle part : on écrit le numéro nu,
    `9.2.1`. Sans cette règle, un document ne pourrait plus nommer ce
    qu'il vient de corriger — et la garde ne peut pas non plus citer la
    forme qu'elle interdit, ce qu'on découvre en essayant.
- **Push** : `git push -u origin main`. Il n'y a qu'un remote, `origin`, et
  qu'une branche de travail, `main` — pas de branche de fonctionnalité.
  Une release demandée pousse aussi son tag `vX.Y.Z` sur ce remote. Jamais de
  push forcé.

## Licence et extension

- `lightwebpres` est sous **GPL v3** (`COPYING`). L'**Output Exception**
  (`COPYING.EXCEPTION`) permet aux présentations générées d'être diffusées
  sous la licence que choisit l'auteur du texte, pas celle du logiciel —
  sauf si l'œuvre diffusée est elle-même un générateur utilisant la sortie
  comme modèles.
- L'**intégration verticale** : un seul outil couvre toute la chaîne (écriture
  → build → thèmes → CI → présentation).
- L'**intégration horizontale** se décline en deux niveaux :
  - **`web/` dans l'arborescence** — un outil navigateur léger (deux onglets :
    déposer un zip à construire, ou tirer/build/pousser vers un dépôt GitLab).
    Tourne sous Pyodide en réutilisant l'exécutable `lightwebpres` tel quel,
    sans le réimplémenter (`web/app.py`, `web/git_sync.py`, `web/index.html`).
  - **`lightwebpres-gui`** (projet séparé, dépôt distinct hors de celui-ci) —
    un éditeur complet : navigateur de fichiers, éditeur Markdown (CodeMirror),
    bouton build, stockage persistant OPFS, PWA hors-ligne, chiffrement au repos
    (AES-GCM-256 + Argon2id), import/export GitLab. Tourne aussi sous Pyodide
    avec l'exécutable vendorisé.
  Le contrat est unidirectionnel : `lightwebpres` est la source de vérité, le
  GUI suit (spec §1.2).
- L'**extension** (GPL) : quiconque peut modifier et redistribuer, sous les
  conditions de la GPL. L'Output Exception est la soupape qui distingue
  « utiliser l'outil » de « redistribuer l'outil ».

## Ce qui n'est pas dans ce dépôt

- La création de thème est un **objectif séparé** : les thèmes livrés
  rendent des couleurs et des propriétés typées, mais l'outil ne *conçoit*
  pas un thème accessible. Il **mesure** (`theme show`, `series theme` :
  un niveau WCAG par catégorie, jamais un verdict) et il **avertit**
  (`audit` : la feuille résolue d'une série, sur trois défauts qui ne sont
  pas affaire de goût — un contrôle invisible, du texte de la couleur de
  son fond, une taille sous le plancher). Il ne refuse jamais un thème sur
  son apparence, et les seuils de l'avertissement sont dérivés du
  catalogue livré, jamais choisis : la règle est en `specifications.md`
  §9.5.6, à lire avant d'en déplacer un. L'expertise accessibilité
  (atteindre AA sur une palette donnée) est externe. Les dettes ouvertes sont au `DECISIONS.md` ; elles ne sont pas
  énumérées ici, parce qu'une liste de numéros dans un second fichier se
  périme sans que rien ne le signale — celle qui était là citait quatre
  entrées, toutes closes depuis.
- `series article add/remove/set` est **exclu** du périmètre CLI actuel
  (BACKLOG C2).
