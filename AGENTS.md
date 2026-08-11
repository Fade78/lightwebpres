# AGENTS.md — Guide pour agents (humains, IA, LLM) travaillant sur ce dépôt

## Commandes essentielles

### Tests (obligatoire avant et après chaque changement)
```bash
python3 -m unittest tests.test_lightwebpres          # 683 tests, ~3 min
python3 -m unittest tests.test_lightwebpres -v 2>&1 | tail -5   # résumé
```

### Vérification compilation
```bash
python3 -m py_compile lightwebpres                    # doit afficher OK (silencieux)
```

### Lancer l'outil
```bash
python3 lightwebpres --help                           # aide
python3 lightwebpres <command> [dir] [options]        # usage général
eval "$(python3 lightwebpres completion --shell bash)" # completion tab (optionnel)
```

## Structure du dépôt

- `lightwebpres` — le code (un seul fichier Python, ~12 000 lignes). Pas de dépendances externes (stdlib uniquement, Python 3.8+).
- `tests/test_lightwebpres.py` — 683 tests, black-box (subprocess). Helper `run(*args)` lance `lightwebpres <args>`.
- `specifications.md` — spécification normative du format (référence).
- `GUIDE.md`, `README.md` — documentation utilisateur.
- `newargs/` — specs de la refonte CLI en cours (non suivies par git) :
  - `PROPOSITION-CLI.md` — intention de conception
  - `DECISION-CLI.md` — arbitrages normatifs (référence pour les décisions)
  - `PLAN-CLI.md` — plan d'implémentation par phase
- `theme gallery.html` — généré par `lightwebpres theme gallery` (artefact).

## Conventions

- **Parseur CLI fait main** (pas d'argparse) — `parse_cli_options()` + tables `_COMMAND_OPTIONS`, `_VALUE_OPTIONS`.
- **Tests black-box** : chaque test lance l'exécutable comme un utilisateur. Pas d'import direct des fonctions internes dans les tests.
- **Versionnage sémantique** (spec §13.9) : MAJOR = incompatible, MINOR = rétrocompatible.
- **Style de commit** : voir `git log --oneline -10` pour le style en vigueur.
- **Pas de push** : l'agent n'a pas les droits. Commit local uniquement.

## Refonte CLI en cours

Le plan d'implémentation est dans `newargs/PLAN-CLI.md`. Trois phases :
1. **Phase 1** — vocabulaire (renommages, alias, `--version`, sous-commandes)
2. **Phase 2** — lecture (`log()`, globales `--quiet`/`--verbose`/`--no-color`/`--timestamp`, `--strict`, `series theme`)
3. **Phase 3** — écriture (`--dry-run`, `clean`, `watch`, `--no-nav`/`--no-index`/`--no-readme`, `--open`)

Les décisions normatives sont dans `newargs/DECISION-CLI.md`. En cas de conflit avec `PROPOSITION-CLI.md`, c'est DECISION qui gagne.