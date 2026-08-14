# AGENTS.md — Guide pour agents (humains, IA, LLM) travaillant sur ce dépôt

## Commandes essentielles

### Tests (obligatoire avant et après chaque changement)
```bash
python3 -m unittest tests.test_lightwebpres          # 720 tests, ~6 min
python3 -m unittest tests.test_lightwebpres -v 2>&1 | tail -5   # résumé
```

### Vérification compilation
```bash
python3 -m py_compile lightwebpres                    # silencieux = OK
```

### Lancer l'outil
```bash
python3 lightwebpres --help                           # aide (lit les tables en live)
python3 lightwebpres <command> [dir] [options]        # usage général
eval "$(python3 lightwebpres completion --shell bash)" # completion tab (optionnel)
```

## Structure du dépôt

### Code et tests
- `lightwebpres` — le code (un seul fichier Python, ~12 800 lignes). Pas de
  dépendances externes (stdlib uniquement, Python 3.8+).
- `tests/test_lightwebpres.py` — 720 tests, black-box (subprocess). Helper
  `run(*args)` lance `lightwebpres <args>`.

### Documentation permanente (fait foi)
- `specifications.md` — spécification normative du format (référence).
- `GLOSSARY.md` — contrat de vocabulaire partagé (avec `lightwebpres-gui`).
- `README.md`, `GUIDE.md` — documentation utilisateur.
- `BACKLOG.md` — registre pérenne des dettes et décisions différées.
- `agent/skills/` — deux skills (format LWP + méthode éditoriale) + index.
- `docs/guide-deck.md` — deck source du guide (se compile via
  `tools/build_guide.py`, qui assemble `GUIDE.md` comme article).

### Artefacts régénérables
- `themes-gallery.html` — généré par `lightwebpres theme gallery` (le test
  `test_the_committed_gallery_is_byte_identical_to_a_fresh_one` vérifie qu'il
  est à jour).
- `docs/guide/` — build output du guide (`tools/build_guide.py`).

### Documents d'étape (consultables, hors arborescence active)
- `to-be-deleted/` — miroir de la racine. Contient les transitoires et
  relevés absorbés : `JOURNAL-1.0.md`, `ETUDE-VIEWPORT.md`,
  `REVISION-THEMES.md`, `ANTERIORITE-THEMES.md`, `newargs/` (refonte CLI,
  terminée et absorbée), `themes-revision/` (blocs B9). git en conserve
  l'historique ; la suppression définitive se fera plus tard.

## Conventions

- **Parseur CLI fait main** (pas d'argparse) — `parse_cli_options()` + tables
  `_COMMAND_OPTIONS`, `_VALUE_OPTIONS`, `_GLOBAL_OPTIONS`. L'aide (`--help`)
  est générée depuis ces tables, donc reste synchrone avec le code.
- **Tests black-box** : chaque test lance l'exécutable comme un utilisateur.
  Pas d'import direct des fonctions internes dans les tests.
- **Versionnage sémantique** (spec §13.9) : MAJOR = incompatible, MINOR =
  rétrocompatible. La constante `VERSION` est dans `lightwebpres`.
- **Style de commit** : voir `git log --oneline -10` pour le style en vigueur
  (préfixes `feat:`, `Docs:`, `Chore:`, ou `vX.Y.Z:` pour les versions).
- **Push contrôlé** : après un commit substantiel, pousser vers le remote
  `newargs` si le workflow de la session le demande ; jamais de push forcé.

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
  pas un thème accessible — il le *juge* (mesures de contraste, `audit`).
  L'expertise accessibilité (atteindre AA sur un palette donné) est externe ;
  le BACKLOG porte les dettes ouvertes (B5, B6, B17, B18).
- `series article add/remove/set` est **exclu** du périmètre CLI actuel
  (BACKLOG C2).
