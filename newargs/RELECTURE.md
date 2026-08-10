# Rapport de relecture — Refonte CLI v0.23.0

> Fichier de travail pour la relecture post-implémentation.
> Rempli au fil de l'eau. Chaque section = un fichier à relire.
> Statuts: [ ] à faire — [~] en cours — [OK] vérifié — [!] correction needed

---

## Critères de cohérence

### Cohérence interne (au sein de chaque fichier)
1. **Vocabulaire**: aucun ancien nom de commande (install, check, themes, theme-info, set-theme, themes-gallery, series-info, refresh-templates) utilisé comme commande active (hors contexte historique/alias)
2. **Options**: les noms d'options correspondent à ceux du code (`--theme` pas `--name`, `--serve` pas `--no-serve`, etc.)
3. **Exemples**: les exemples utilisent les nouveaux noms et sont exécutables tels quels
4. **Tables/listes**: les tables de commandes/options sont complètes et cohérentes avec le code
5. **Cross-references**: les références internes (§X.Y) pointent vers le bon contenu

### Cohérence globale (entre fichiers)
6. **Noms de commandes**: identiques entre code, tests, specs, et docs
7. **Noms d'options**: identiques entre code, help, et docs
8. **Comportements**: les descriptions correspondent à l'implémentation réelle
9. **Artefacts**: les fichiers générés (themes-gallery.html, guide.html) reflètent les nouveaux noms
10. **Specs vs code**: DECISION-CLI.md est respectée par le code

---

## A. Fichiers de spécification (newargs/)

### A.1 DECISION-CLI.md
- [OK] 1. Vocabulaire: aucun ancien nom en commande active
- [OK] 2. Options: `--theme` (pas `--name`), `--serve` (pas `--no-serve`), `--port`, `--dry-run`, `--timestamp`
- [OK] 3. Exemples: utilisent les nouveaux noms
- [OK] 4. Tables: 8 globales listées en §2, phasage §1 cohérent
- [OK] 5. Cross-refs: §1→§2→§3→§4→§5→§6 cohérentes
- [OK] 6. Global: DECISION respectée par le code (vérifier chaque arbitrage)
- **Notes**: Corrigé: "7e globale" → "listée ci-dessus parmi les huit" (redondance). Corrigé: "premier subprocess" → "webbrowser.open() pas de subprocess". DECISION respectée par le code: --theme partout, --serve opt-in, --dry-run globale + clean dry-run par défaut, --no-index/--no-readme arbitrées, --all/slugs conservés.

### A.2 PLAN-CLI.md
- [OK] 1. Vocabulaire: aucun ancien nom en commande active
- [OK] 2. Options: cohérent avec DECISION
- [OK] 3. Exemples: nouveaux noms
- [OK] 4. Tables: livrables par phase complets, _GLOBAL_OPTIONS count correct
- [OK] 5. Cross-refs: phases 1→2→3, dépendances §3
- [OK] 6. Global: PLAN reflète ce qui a été implémenté (livrables cochés)
- [!] 7. Spécifique: NewCliOptions corrigé (OK), --dry-run en Phase 3 (OK), --port présent (OK). MANQUE: test AST "aucune écriture nue" non implémenté (livrable Phase 3 non coché)
- **Notes**: Livrables cochés. 1 livrable non coché: test qui vérifie qu'aucune écriture nue n'existe (helpers existent, test AST à écrire).

### A.3 PROPOSITION-CLI.md
- [OK] 1. Vocabulaire: avertissement en tête, sections dépassées marquées
- [OK] 2. Options: §6.2 liste corrigée (8 globales), §8.3 table mise à jour
- [OK] 3. Exemples: §10 utilisent les nouveaux noms
- [OK] 4. Tables: §8.4 raccourcis = 10 (pas 12), §4.2/4.3 arbres mis à jour
- [OK] 5. Cross-refs: §13 questions ouvertes toutes tranchées
- [OK] 6. Global: PROPOSITION cohérente avec DECISION (les notes signalent les divergences)
- **Notes**: Avertissement en tête présent. 14 occurrences d'anciens patterns (--no-serve, --clean sur build, theme set raccourci) toutes dans des notes "abandonné/dépassé". Cohérent.

---

## B. Code (lightwebpres)

### B.1 Structure CLI (main, _resolve_command, parse_cli_options, tables)
- [OK] 1. _SHORTCUTS: 10 raccourcis, cohérent avec DECISION §3
- [OK] 2. _LEGACY_ALIASES: tous les anciens noms présents avec [WARN]
- [OK] 3. _GLOBAL_OPTIONS: 8 options, --dry-run incluse
- [OK] 4. _SERIES_VERBS / _THEME_VERBS: cohérents avec l'arbre §4.2
- [OK] 5. _resolve_command: series theme set géré, theme set rejeté, template seul rejeté
- [OK] 6. parse_cli_options: global_opts mergées, précédence nearest-wins
- [OK] 7. print_help: nouveaux noms, alias mentionnés, --version, globales documentées
- [OK] 8. Module docstring (lignes 24-45): nouveaux noms
- **Notes**: `template` dans _SHORTCUTS/_SERIES_VERBS est du code mort (shadowed par test ligne 11375). Cosmétique.

### B.2 log() + configure_logging()
- [OK] 1. log(): 3 niveaux (info/verbose/error), prefixes [INFO]/[DEBUG]/[ERROR]
- [OK] 2. configure_logging(): 5 paramètres (quiet/verbose/no_color/timestamp/dry_run)
- [!] 3. ~66 print(..., file=sys.stderr) restants hors log() (validateurs, cmd_*, parseur)
- [!] 4. ~57 print(f'[ERROR] ...') directs hors log() — --quiet/--timestamp sans effet sur ces messages
- **Notes**: Phase 2 log() définie et câblée mais la grande majorité des sites d'erreur existants n'a pas été convertie. log() est utilisé sur quelques points isolés (build --only fallback, theme_info, clean, watch, resolve) mais les validateurs (validate_slides, validate_series, resolve_article_fields, load_language) et plusieurs cmd_* bypassent log().

### B.3 Helpers _write_file/_mkdir/_copy/_copytree
- [OK] 1. Tous les write_text/mkdir/copy hors helper → helpers
- [OK] 2. --dry-run journalise sans écrire
- [!] 3. .mkdir bare ligne 10842 (cmd_demo img/) + shutil.copytree ligne 7847 (copy_images) + shutil.copy2 ligne 9300 (cmd_install exe) contournent les helpers
- **Notes**: cmd_demo img/.mkdir(exist_ok=True) bypass _mkdir. copy_images shutil.copytree bypass _copytree. cmd_install shutil.copy2 a un guard dry_run manuel mais viole la convention. chmod ligne 9301 non journalisé en dry-run.

### B.4 cmd_build + _cmd_build_only
- [OK] 1. include_nav paramètre présent, --no-nav respecté
- [OK] 2. --no-index skip build_index, --no-readme skip build_readme
- [OK] 3. --drafts-only filtre + implique --include-drafts
- [OK] 4. --open: webbrowser.open après build
- [OK] 5. Manifeste .lwp-manifest.json écrit en fin de build
- [OK] 6. _cmd_build_only: respecte --no-nav (via ctx.args)
- [!] 7. _cmd_build_only n'appelle pas _write_manifest (fast path ne rafraîchit pas le manifeste)
- **Notes**: Mineur: le fast path --only ne met pas à jour le manifeste. clean se fie au manifeste, donc un build --only suivi d'un clean pourrait mal identifier les orphans.

### B.5 cmd_audit + --strict
- [OK] 1. --strict: exit 1 si warnings > 0
- [OK] 2. --strict: exit 0 si warnings == 0
- [OK] 3. --strict dans _COMMAND_OPTIONS['audit']
- **Notes**:

### B.6 cmd_theme_info + cmd_series_theme
- [OK] 1. cmd_theme_info: accepte positional (liste), --all, slugs multiples
- [OK] 2. cmd_theme_info: rejette les répertoires (redirige vers series-theme via main)
- [OK] 3. cmd_series_theme: branche répertoire extraite, --format text/json
- [OK] 4. JSON: liste quand >1 slug, objet quand 1 seul
- [OK] 5. Slugs inconnus: erreur fatale listant les valides
- **Notes**:

### B.7 cmd_themes_gallery
- [OK] 1. --output option, --all, slugs positionnels
- [OK] 2. Legacy: single non-slug positional = output path
- [OK] 3. Slugs inconnus: erreur fatale
- **Notes**:

### B.8 cmd_clean
- [OK] 1. Lit .lwp-manifest.json, refuse sans manifeste
- [OK] 2. Dry-run par défaut (liste), --force supprime
- [OK] 3. Ne supprime que les orphans (pas les fichiers déclarés)
- **Notes**:

### B.9 cmd_watch
- [OK] 1. Build initial avant polling
- [OK] 2. --serve opt-in, 127.0.0.1 uniquement, --port configurable
- [OK] 3. --open: webbrowser.open
- [OK] 4. Ctrl-C (SIGINT) → exit 0
- [OK] 5. Polling: os.stat mtimes, pas de watchdog
- **Notes**:

### B.10 cmd_install / cmd_demo / cmd_refresh_templates / cmd_set_theme
- [OK] 1. cmd_install: utilise _write_file/_mkdir (mais shutil.copy2 ligne 9300 bypass _copy)
- [!] 2. cmd_demo: ligne 10842 .mkdir bare (img/) bypass _mkdir
- [OK] 3. cmd_refresh_templates: utilise _write_file
- [OK] 4. cmd_set_theme: utilise _write_file, --theme (pas --name)
- [!] 5. Messages d'erreur: ligne 9366 dit encore "Run install (or refresh-templates...)", ligne 10634 dit encore "has not been installed"
- **Notes**: 2 messages non migrés: cmd_refresh_templates --scaffold (ligne 9366) et cmd_demo (ligne 10634 "has not been installed"). shutil.copy2 ligne 9300 a un guard dry_run manuel mais viole la convention helpers.

---

## C. Tests (tests/test_lightwebpres.py)

### C.1 Migration des appels
- [OK] 1. Aucun run('install'/run('check'/etc restant (hors tests d'alias legacy)
- [OK] 2. run('theme-info' accepté comme alias legacy (7 occurrences, pas migrées)
- [OK] 3. Two-word shortcuts passés en args séparés: run('theme','list') pas run('theme list')
- [OK] 4. Assertions stderr: 'init' au lieu de 'install' dans les messages d'erreur
- [!] 5. subprocess.run([..., 'install', ...]) lignes 9974, 10618 non migré (mineur)
- **Notes**: 46 méthodes test_ dans CliVersionAndShortcuts. subprocess.run direct avec 'install' dans 2 tests (alias fonctionne mais non migré).

### C.2 Nouveaux tests (CliVersionAndShortcuts)
- [OK] 1. --version: imprime version, exit 0
- [OK] 2. Alias: [WARN] sur stderr + exit 0
- [OK] 3. Raccourcis: pas de [WARN]
- [OK] 4. Formes canoniques: series build, theme list/gallery, status, template update, series theme set
- [OK] 5. theme set rejeté comme raccourci racine
- [OK] 6. template seul rejeté
- [OK] 7. Globales: --lang avant commande, nearest-wins
- [OK] 8. --quiet, --timestamp, --no-color, --verbose
- [OK] 9. --strict audit (fail + pass)
- [OK] 10. series theme (text + json)
- [OK] 11. theme show --all/multiple/unknown/no-args
- [OK] 12. theme gallery restrict/--output
- [OK] 13. --no-nav, --no-index, --no-readme, --drafts-only, --open
- [OK] 14. --dry-run (build, init, theme gallery)
- [OK] 15. clean (dry-run, --force, no manifest, no orphans)
- [OK] 16. watch (initial build + SIGINT)
- **Notes**: 46 méthodes test_ au total. Couverture complète.

### C.3 Tests existants modifiés
- [OK] 1. test_a_lone_article... : ignore .lwp-manifest.json dans iterdir
- [OK] 2. test_a_built_page_byte_identical... : expectedFailure documenté
- [OK] 3. CONTRAST_CALLERS: cmd_series_theme ajouté
- [OK] 4. Assertions [INFO]: stdout → stderr
- **Notes**:

---

## D. Documentation

### D.1 README.md
- [!] 1. Vocabulaire: ligne 193 `install` dans table, ligne 196 `check`, ligne 427 `install --theme`, ligne 514 "install, build"
- [!] 2. Exemples: exécutables (init, build, verify, etc.)
- [!] 3. Table des commandes: mélange anciens/nouveaux noms (lignes 193-204)
- [OK] 4. Options: --theme (pas --name), --serve (pas --no-serve)
- [OK] 5. Global: cohérent avec specifications.md et GUIDE.md
- **Notes**: Table des commandes ligne 193 `install` → `init`, ligne 196 `check` → `verify`. Ligne 427 `install --theme` → `init --theme`. Ligne 514 "install, build" → "init, build".

### D.2 GUIDE.md
- [!] 1. Vocabulaire: ligne 376 `install --gitlab-ci`, ligne 450 `install . --force`, ligne 189 "at install time"
- [OK] 2. Exemples: exécutables
- [OK] 3. Walkthrough: parcours complet avec nouveaux noms
- [OK] 4. Global: cohérent avec README
- **Notes**: 3 occurrences de `install` restantes: ligne 376 (--gitlab-ci), ligne 450 (. --force), ligne 189 ("at install time").

### D.3 specifications.md
- [!] 1. Vocabulaire: lignes 183-184, 1889, 1996, 2186, 3183, 4169 `install` restant; lignes 2691, 4871 `check` restant; lignes 1665, 1693, 1896, 2628, 2631 "à l'install"
- [OK] 2. Sections §11.1-§11.11: titres et contenu avec nouveaux noms
- [OK] 3. Tables d'options: cohérentes avec _COMMAND_OPTIONS
- [OK] 4. Exemples: nouveaux noms
- [OK] 5. Cross-refs: §X.Y pointent vers le bon contenu
- [OK] 6. Global: cohérent avec le code (options, comportements)
- **Notes**: ~15 occurrences d'anciens noms restantes dans le texte (hors titres §11 qui sont OK). Principalement "install" dans commentaires d'arbre, titres de sous-sections, et "à l'install" dans le texte. "check" dans "build et check" et "build/check/status".

### D.4 AGENTS.md
- [OK] 1. Vocabulaire: nouveaux noms
- [OK] 2. Commandes essentielles: correctes
- [OK] 3. Structure du dépôt: à jour
- [OK] 4. Refonte CLI en cours: phases décrites correctement
- **Notes**:

### D.5 docs/guide-deck.md
- [OK] 1. Vocabulaire: nouveaux noms
- [OK] 2. Exemples: exécutables
- **Notes**:

### D.6 docs/guide/guide.html (régénéré)
- [ ] 1. Aucun ancien nom de commande
- [ ] 2. Contenu cohérent avec GUIDE.md
- **Notes**:

### D.7 GLOSSARY.md
- [OK] 1. set-theme → series theme set
- [!] 2. ligne 161 "install, write, verify, ship" → "init, write, verify, ship"
- **Notes**:

### D.8 THIRD-PARTY-NOTICES.md
- [OK] 1. install → init
- **Notes**:

### D.9 COPYING.EXCEPTION
- [OK] 1. install → init
- **Notes**:

### D.10 BACKLOG.md
- [OK] 1. themes → theme list (si applicable)
- [OK] 2. Pas de correction nécessaire sur les références conceptuelles
- **Notes**:

### D.11 JOURNAL-1.0.md
- [OK] 1. LAISSÉ TEL QUEL (journal historique figé)
- [OK] 2. Vérifier qu'aucun processus automatique ne lit ce fichier
- **Notes**:

---

## E. Artefacts générés

### E.1 themes-gallery.html
- [OK] 1. Aucun ancien nom de commande (install, themes-gallery)
- [OK] 2. "init my-series --theme" présent (33 occurrences)
- [OK] 3. Pied de page: "Generated by lightwebpres theme gallery"
- **Notes**:

### E.2 themes-gallery.png
- [OK] 1. Non affecté par le renommage (image)
- **Notes**:

---

## F. Outils et scripts

### F.1 tools/gallery_screenshot.py
- [OK] 1. themes-gallery → theme gallery dans le message
- **Notes**:

### F.2 tools/screenshot-gallery.cjs
- [OK] 1. themes-gallery → theme gallery dans le message
- [OK] 2. Noms de fichiers themes-gallery.html/.png = artefacts (pas des commandes)
- **Notes**:

### F.3 tools/build_guide.py
- [OK] 1. Vérifier qu'il n'utilise pas d'anciens noms en interne
- **Notes**:

### F.4 web/app.py
- [OK] 1. check → verify dans le commentaire
- **Notes**:

---

## G. Skill

### G.1 agent/skills/lightwebpres/SKILL.md
- [OK] 1. check → verify
- [OK] 2. Vérifier les autres références CLI (aucun ancien nom trouvé)
- [OK] 3. Global: le skill guide l'agent vers les bons noms
- **Notes**:

---

## H. Synthèse globale

### H.1 Cohérence des noms de commandes
- [OK] 1. Code ↔ tests: mêmes noms
- [OK] 2. Code ↔ --help: mêmes noms
- [!] 3. Code ↔ README: README table des commandes mélange anciens/nouveaux (lignes 193, 196)
- [!] 4. Code ↔ GUIDE: 3 occurrences "install" restantes (lignes 189, 376, 450)
- [!] 5. Code ↔ specifications.md: ~15 occurrences "install"/"check" restantes dans le texte
- [OK] 6. Code ↔ DECISION: mêmes noms

### H.2 Cohérence des options
- [OK] 1. _COMMAND_OPTIONS ↔ --help: mêmes options par commande
- [OK] 2. _GLOBAL_OPTIONS ↔ --help: mêmes globales
- [OK] 3. --theme partout (pas --name)
- [OK] 4. --serve partout (pas --no-serve)
- [OK] 5. --dry-run globale + clean dry-run par défaut

### H.3 Cohérence des comportements
- [OK] 1. Alias: [WARN] + exit correct (code ↔ tests)
- [OK] 2. --strict: exit 1 si warnings (code ↔ tests)
- [OK] 3. --dry-run: rien écrit (code ↔ tests)
- [OK] 4. clean: manifeste requis (code ↔ tests)
- [OK] 5. watch: --serve opt-in, 127.0.0.1 (code ↔ DECISION)

### H.4 Artefacts
- [OK] 1. themes-gallery.html régénéré avec nouveaux noms
- [OK] 2. guide.html régénéré avec nouveaux noms
- [OK] 3. .gitlab-ci.yml template: build reste build (vérifié)

### H.5 Points d'attention restants
- [OK] 1. JOURNAL-1.0.md: laissé tel quel (historique) — confirmé OK
- [OK] 2. expectedFailure du test byte-identical: documenté, à retirer next release
- [!] 3. docs/guide/.lwp-manifest.json: accidentellement commité (artefact de build)
- [!] 4. test_lightwebpres.py: subprocess.run avec 'install' lignes 9974, 10618 (mineur)
- [!] 5. ~66 print(file=stderr) hors log() — Phase 2 incomplète
- [!] 6. 2 messages "install" restants dans le code (lignes 9366, 10634)
- [!] 7. 3 écritures bypass helpers (cmd_demo mkdir, copy_images copytree, cmd_install copy2)

---

## Corrections planifiées

| # | Fichier | Problème | Priorité | Statut |
|---|---|---|---|---|
| 1 | lightwebpres:9366 | cmd_refresh_templates --scaffold dit "Run install" au lieu de "Run init" | haute | à faire |
| 2 | lightwebpres:10634 | cmd_demo dit "has not been installed" au lieu de "has not been init'd" | haute | à faire |
| 3 | lightwebpres:10842 | cmd_demo .mkdir bare (img/) bypass _mkdir → --dry-run contourne | haute | à faire |
| 4 | lightwebpres:7847 | copy_images shutil.copytree bypass _copytree → --dry-run contourne | haute | à faire |
| 5 | lightwebpres:9300 | cmd_install shutil.copy2 bypass _copy (guard manuel mais convention violée) | moyenne | à faire |
| 6 | lightwebpres:~66 sites | print(..., file=sys.stderr) hors log() → --quiet/--timestamp sans effet | haute | à faire |
| 7 | lightwebpres _cmd_build_only | fast path --only n'appelle pas _write_manifest | moyenne | à faire |
| 8 | tests | test AST "aucune écriture nue hors helper" non écrit (PLAN livrable P3) | moyenne | à faire |
| 9 | lightwebpres _SHORTCUTS | entrée `template` morte (shadowed par test ligne 11375) | basse | à faire |
| 10 | README.md:193,196 | Table des commandes: `install`→`init`, `check`→`verify` | haute | à faire |
| 11 | README.md:427,514 | `install --theme`→`init --theme`, "install, build"→"init, build" | haute | à faire |
| 12 | GUIDE.md:189,376,450 | 3 occurrences "install" restantes | haute | à faire |
| 13 | specifications.md:~15 | "install"/"check"/"à l'install" restants dans le texte | haute | à faire |
| 14 | GLOSSARY.md:161 | "install, write, verify, ship"→"init, write, verify, ship" | moyenne | à faire |
| 15 | docs/guide/.lwp-manifest.json | Artefact de build accidentellement commité | basse | à faire |
| 16 | tests:9974,10618 | subprocess.run avec 'install' au lieu de 'init' (mineur, alias fonctionne) | basse | à faire |

---

## Validation finale

- [ ] `python3 -m py_compile lightwebpres` → OK
- [ ] `python3 -m unittest tests.test_lightwebpres` → 674 tests OK (1 expectedFailure)
- [ ] `python3 lightwebpres --version` → v0.23.0
- [ ] `python3 lightwebpres --help` → nouveaux noms
- [ ] `python3 lightwebpres init /tmp/test && rm -rf /tmp/test` → fonctionne
- [ ] `python3 lightwebpres install /tmp/test` → [WARN] + fonctionne
- [ ] `python3 lightwebpres theme list` → fonctionne
- [ ] `python3 lightwebpres theme show nord` → fonctionne
- [ ] `python3 lightwebpres theme show nord dracula` → compare
- [ ] `python3 lightwebpres theme show --all` → tous
- [ ] `python3 lightwebpres series theme /tmp/test` → thème effectif
- [ ] `python3 lightwebpres --dry-run init /tmp/test` → nothing written
- [ ] `python3 lightwebpres --version` → v0.23.0