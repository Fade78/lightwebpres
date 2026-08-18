# AGENTS.md — Guide pour agents (humains, IA, LLM) travaillant sur ce dépôt

Ce fichier **ne fait pas partie du contrat du projet** (`specifications.md`
§1.1). Il n'oblige que celui qui le lit : le dépôt fonctionne à l'identique
sans lui, et rien dans le produit n'en dépend. Ce sont des conventions de
travail, pas une spécification.

À ne pas confondre avec `agent/skills/lightwebpres/SKILL.md`, qui est
normatif : il décrit le **format** à qui écrit un article. Ici on dit
comment travailler *sur* l'outil ; là-bas, ce que l'outil *accepte*.

## Commandes essentielles

### Tests (obligatoire avant et après chaque changement)
```bash
python3 tests/run_tests.py                              # obligatoire : parallèle, CPUs disponibles - 2
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
- `tests/test_lightwebpres.py` — la suite principale, black-box
  (subprocess) ; `tests/run_tests.py` en découvre davantage, dont les
  volets navigateur. Helper `run(*args)` lance `lightwebpres <args>`.
  Les comptes ne sont pas écrits ici : ils changent à chaque lot et un
  nombre faux dans un guide de travail est pire que pas de nombre. Pour
  l'avoir, lancer la suite.

### Documentation permanente (fait foi)
- `specifications.md` — spécification normative du format (référence).
- `GLOSSARY.md` — contrat de vocabulaire partagé (avec `lightwebpres-gui`).
- `README.md`, `GUIDE.md` — documentation utilisateur.
- `BACKLOG.md` — registre pérenne des dettes et décisions différées.
- `agent/skills/` — les skills (format LWP, méthode éditoriale) + index.
- `AGENTS.md` — ce document.
- `THIRD-PARTY-NOTICES.md` — licences de ce qui est embarqué.

### Relevés datés (consultables, non normatifs)
- `docs/AUDIT-*.md` — les audits, avec leurs mesures et leurs conditions.
  Les nombres qu'ils portent disent l'état du jour de la mesure : ils ne
  se périment pas, et ne se lisent pas comme des affirmations présentes.

### Outillage
- `docs/guide-deck.md` — deck source du guide (se compile via
  `tools/build_guide.py`, qui assemble `GUIDE.md` comme article). Entrée
  de build, pas documentation : se corrige comme du code.

### Artefacts régénérables
- `themes-gallery.html` — généré par `lightwebpres theme gallery` (le test
  `test_the_committed_gallery_is_byte_identical_to_a_fresh_one` vérifie qu'il
  est à jour).
- `docs/guide/` — build output du guide (`tools/build_guide.py`).

### Documents d'étape (consultables, hors arborescence active)
- `delete-before-1.0/` — miroir de la racine. Ce qui y entre reste
  consultable mais quitte l'arborescence active : mémoire de travail,
  relevés dont le raisonnement est versé ailleurs, et documents de
  conception absorbés (sous `docs/`). git en conserve l'historique ; la
  suppression effective se fera avant la 1.0, ce que son nom dit.

  **Avant d'y envoyer un document, vérifier ce qu'il porte encore.** Un
  plan livré contient souvent une décision que personne n'a prise et qui
  ne vit nulle part ailleurs ; elle va au `BACKLOG.md` avec sa mesure
  avant que le document ne sorte. Sans ce geste, ranger revient à perdre
  (`specifications.md` §1.1).

## Conventions

- **Parseur CLI fait main** (pas d'argparse) — `parse_cli_options()` + tables
  `_COMMAND_OPTIONS`, `_VALUE_OPTIONS`, `_GLOBAL_OPTIONS`. L'aide (`--help`)
  est un template maintenu à la main ; un test la verrouille contre les
  tables d'options pour qu'elle ne puisse pas dériver en silence.
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
