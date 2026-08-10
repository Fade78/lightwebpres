# Plan — Refonte CLI v0.24.0

> État des lieux code vs spec, et chemin vers la prochaine version.
> Références : `PROPOSITION-CLI.md` (intention), `DECISION-CLI.md` (décisions),
> `specifications.md` (normatif), le code (`lightwebpres`).

## 1. État actuel du code (commit HEAD)

Le CLI est **plat**, sans sous-commandes, sans options globales :

```
install [dir] [--lang] [--force] [--theme] [--gitlab-ci]
demo [dir] [--lang] [--output]
build [dir] [--lang] [--output] [--no-typography] [--include-drafts] [--only] [--nav-cache] [--build-stamp|--build-stamp-minimal]
check [dir] [--lang] [--output] [--no-typography] [--include-drafts]
audit [dir] [--lang]
refresh-templates [dir] [--scaffold]
themes [--polarity] [--intensity] [--hue]
theme-info <slug>|[dir] [--format]
series-info [dir] [--format]
resolve [dir] <name> [--format] [--article]
set-theme [dir] --theme
themes-gallery [path]
help | --help | -h
```

**Absent du code :**
- `--version`
- `--quiet`, `--verbose`, `--dry-run`, `--no-color`
- `--no-nav`, `--no-index`, `--no-readme`, `--drafts-only`, `--clean`, `--open`
- `--strict` (audit)
- `--timestamp`
- `watch`, `clean`, `series theme`, `series template`
- Toute la structure de sous-commandes (`series <verbe>`, `theme <verbe>`)
- Les alias de transition
- La fonction `log()` / `configure_logging()`

**Présent dans le code :**
- 630 tests, tous verts
- Les fonctions `cmd_*` appelées par le dispatch de `main()`
  (le GUI appelle le CLI comme un utilisateur humain, pas les
  fonctions `cmd_*` par leur nom Python — les renommages internes
  sont donc libres, mais non requis : le dispatch fait la table
  de correspondance)
- `build_article` sans paramètre `include_nav`
- `cmd_build` sans `dry_run`, `verbose`, `quiet`, `include_nav`

## 2. Écart code ↔ spec (PROPOSITION-CLI.md + DECISION-CLI.md)

### Phase 1 — Vocabulaire seul (aucun comportement nouveau)

| Changement | Code actuel | Cible | Risque |
|---|---|---|---|
| `install` → `init` | `cmd_install` | alias `install` → `series init`, raccourci `init` | Messages d'erreur, `.gitlab-ci.yml`, `themes-gallery.html` |
| `check` → `verify` | `cmd_check` | alias `check` → `series verify`, raccourci `verify` | Aucun (le GUI appelle le CLI, pas `cmd_*`) |
| `themes` → `theme list` | `cmd_themes` | `theme list` | Aucun |
| `theme-info <slug>` → `theme show` | `cmd_theme_info` | `theme show <slug>` | Split slug/répertoire : `theme-info [dir]` → `series theme [dir]` |
| `set-theme` → `theme set` | `cmd_set_theme` | `series theme set` (pas de raccourci racine) | Garder `--theme`, pas `--name` |
| `themes-gallery` → `theme gallery` | `cmd_themes_gallery` | `theme gallery` | Aucun |
| `series-info` → `status` | `cmd_series_info` | `series status` + raccourci `status` | Aucun (le GUI appelle le CLI, pas `cmd_*`) |
| `refresh-templates` → `template update` | `cmd_refresh_templates` | `series template update` + raccourci `template update` | Aucun |
| `resolve` → `series resolve` | `cmd_resolve` | `series resolve` + raccourci `resolve` | Aucun |
| `--version` | absent | `lightwebpres --version` → `LightWebPres v0.24.0` | Aucun |
| Alias de transition | absent | chaque ancien nom → `[WARN]` sur stderr + nouveau nom | 138 appels dans les tests |

### Phase 2 — Lecture seule

| Changement | Code actuel | Cible | Risque |
|---|---|---|---|
| `--quiet` | absent | supprime progression, pas la valeur demandée | `resolve --format json` doit rester sur stdout |
| `--verbose` | absent | `[INFO]` supplémentaire via `log()` | Format de sortie testé par nouveaux tests à écrire |
| `--no-color` | absent | no-op (pas de codes ANSI aujourd'hui) | Aucun |
| `--timestamp` | absent | préfixe RFC 3339 via `log()` | Ajouté à `_GLOBAL_OPTIONS` |
| `--strict` (audit) | absent | exit 1 si warnings | Simple |
| `series theme [dir]` | dans `cmd_theme_info` | extraire la branche répertoire | Split propre |
| Fonction `log()` | absente | `log(level, msg)` → stdout/stderr selon niveau | Remplacer tous les `print()` de log |
| `configure_logging()` | absente | appelée dans `main()` après parse | Une ligne |

### Phase 3 — Écriture et processus

| Changement | Code actuel | Cible | Risque |
|---|---|---|---|
| `--no-nav` | absent | `include_nav=False` → placeholder vide | Interaction avec fiche series-nav |
| `--no-index` | absent | sauter `build_index()` | Simple |
| `--no-readme` | absent | sauter `build_readme()` | Simple |
| `--drafts-only` | absent | filtrer `ctx.articles` sur `status: draft` | Index pointe vers pages non construites |
| `--dry-run` | absent | retour avant `mkdir`/`write_text` | Helper unique + test qui mord |
| `--open` sur `build` | absent | `webbrowser.open()` après build | Simple |
| `watch` | absent | polling + serveur HTTP | `127.0.0.1` uniquement, `--serve` en opt-in, `--port N` (défaut 8000) |
| `clean` | absent | purge avec manifeste | `--dry-run` par défaut, `--force` pour supprimer |
| `series template` | abandonné | remplacer par filtre sur `audit` | Décision DECISION-CLI.md |

## 3. Dépendances entre les changements

```
Phase 1 (vocabulaire)
├── Structure de sous-commandes (_resolve_command, _SHORTCUTS, _LEGACY_ALIASES)
├── Alias + [WARN] sur stderr
├── --version
└── Messages d'erreur : install → init

Phase 2 (lecture) — dépend de Phase 1
├── log() + configure_logging()
├── --quiet, --verbose, --no-color, --timestamp (globales)
├── --strict (audit)
├── --all + slugs multiples sur theme show / theme gallery
└── series theme [dir]

Phase 3 (écriture) — dépend de Phase 2
├── --no-nav, --no-index, --no-readme
├── --drafts-only
├── --dry-run (globale + helpers d'écriture, dépend de log())
├── --open sur build
├── watch (avec --serve, --port)
└── clean (dépend du manifeste écrit par build)
```

## 4. Points d'attention par phase

### Phase 1

- **Fonctions `cmd_*`.** Le GUI (Pyodide) appelle le CLI comme un utilisateur humain, pas les fonctions `cmd_*` par leur nom Python. Les renommages internes sont donc libres, mais non requis : le dispatch dans `main()` fait la table de correspondance (ex: `'series init': cmd_install`).
- **Messages d'erreur.** Quatre messages disent `Run install first` : `cmd_demo`, `cmd_refresh_templates`, `cmd_theme_info`, `cmd_set_theme`. → `Run init first`. Les tests qui vérifient `assertIn('install', result.stderr)` doivent être migrés manuellement.
- **`.gitlab-ci.yml`.** Le template généré contient `lightwebpres build . --lang {lang}` — le verbe `build` ne change pas, aucune action sur le template. Le message de sortie d'`install` dit `3. Run: lightwebpres build {td}` — `build` reste `build`, pas changé non plus.
- **`themes-gallery.html`.** 33 occurrences de `lightwebpres install my-series --theme {slug}`. → `lightwebpres init my-series --theme {slug}`. Régénérer le fichier.
- **138 appels de test.** Migration mécanique : `run('install'` → `run('init'`, etc. **Ne pas** remplacer les `assertIn('install', ...)` qui vérifient les messages d'erreur — ceux-là doivent être mis à jour manuellement.

### Phase 2

- **`log()`.** Remplacer tous les `print(..., file=sys.stderr)` par `log('error', ...)`, tous les `print(f'[INFO] ...')` par `log('info', ...)`. Les `print()` de sortie utilisateur normale (ex: `print(f'Build: {ctx.sd}')`) restent en `print()`.
- **`--quiet` et `resolve`/`theme show`.** `log('info', ...)` est supprimé par `--quiet`, mais `print()` ne l'est pas. `resolve --format json` fait `print(json.dumps(...))` → pas affecté. ✅
- **`series theme [dir]`.** Extraire la branche répertoire de `cmd_theme_info` dans `cmd_series_theme`. Le dispatch : `'series theme': cmd_series_theme`.

### Phase 3

- **Manifeste pour `clean`.** `build` écrit `.lwp-manifest.json` dans `public/` listant chaque fichier produit. `clean` lit ce manifeste, compare avec le build courant, supprime les orphelins. Sans manifeste, `clean` refuse (exit 1 avec message). `clean` est en `--dry-run` par défaut ; `--force` supprime réellement.
- **`--dry-run`.** Créer un helper `_write_file(path, content, dry_run)` et un helper `_mkdir(path, dry_run)`. Remplacer tous les `write_text()`, `mkdir()`, `shutil.copytree()` par ces helpers. Un test vérifie qu'aucun `open(…, 'w')` / `write_text` / `mkdir` / `copytree` n'est appelé hors helper. `--dry-run` est globale (sur build/init/theme set/template update/clean).
- **`watch`.** `127.0.0.1` uniquement. `--serve` en opt-in (pas `--no-serve`). `--port N` (défaut 8000) fixe le port du serveur. Pas de `subprocess` pour `--open` — utiliser `webbrowser.open()` qui est déjà dans le code.
- **`--open` sur `build`.** `webbrowser.open()` après le build. Opt-in.

## 5. Stratégie de test

### Avant chaque phase
```bash
python3 -m unittest tests.test_lightwebpres  # doit être vert (630 tests)
```

### Après Phase 1
- 138 appels migrés vers les nouveaux noms
- Tests d'alias : chaque ancien nom → `[WARN]` sur stderr + exit 0
- Tests des nouveaux noms : comportement identique à l'ancien
- `--version` : sortie contient `LightWebPres v`

### Après Phase 2
- Nouveaux tests à écrire : `--quiet`, `--verbose`, `--timestamp`, `--strict`
- `--quiet` : stdout vide pour `build --quiet`
- `--verbose` : stdout plus long que sans
- `--timestamp` : chaque ligne commence par `YYYY-MM-DDTHH:MM:SS±HH:MM`
- `--strict` : `audit --strict` avec warning → exit 1
- `--all` et slugs multiples : `theme show a b` décrit a puis b ; `theme show --all` décrit tous ; slugs inconnus → exit 1 listant les valides

### Après Phase 3
- `--dry-run` : aucun fichier écrit
- `--no-nav` : pas de `class="series-link"` dans le HTML
- `--no-index` : pas d'`index.html` ; `--no-readme` : pas de `README.md`
- `--open` sur build : navigateur ouvert (mock `webbrowser.open`)
- `clean` : avec manifeste, supprime les orphelins ; sans manifeste, exit 1 ; `--dry-run` par défaut, `--force` pour supprimer
- `watch` : test d'intégration (lancement, modification, reconstruction) ; `--serve` opt-in, `--port` configurable, `127.0.0.1` uniquement

## 6. Livrables par phase

### Phase 1
- [x] Structure de sous-commandes dans `main()` + `_resolve_command()`
- [x] Tables `_SHORTCUTS`, `_LEGACY_ALIASES`, `_COMMAND_OPTIONS` (nouveau format)
- [x] `_GLOBAL_OPTIONS` définie (Phase 1 accepte `--lang`, `--version`, `--help` ; `--quiet`, `--verbose`, `--no-color`, `--timestamp` acceptées en no-op jusqu'en Phase 2 ; `--dry-run` ajoutée en Phase 3)
- [x] `parse_cli_options()` adapté
- [x] `_warn_legacy()` sur stderr
- [x] `--version`
- [x] Messages `install` → `init` dans `cmd_demo`, `cmd_refresh_templates`, `cmd_theme_info`, `cmd_set_theme`
- [x] `.gitlab-ci.yml` : `build` reste `build` (pas changé)
- [x] `themes-gallery.html` régénéré avec `init`
- [x] 138 appels de test migrés
- [x] Tests d'alias ajoutés
- [x] 630 tests verts

### Phase 2
- [x] `log()` + `configure_logging()`
- [x] `--quiet`, `--verbose`, `--no-color`, `--timestamp` dans `_GLOBAL_OPTIONS`
- [x] `--strict` dans `cmd_audit`
- [x] `--all` + slugs multiples sur `theme show` / `theme gallery`
- [x] `series theme [dir]` extrait de `cmd_theme_info`
- [x] Nouveaux tests `--quiet`, `--verbose`, `--timestamp`, `--strict` à écrire
- [x] 630+ tests verts

### Phase 3
- [x] `include_nav` dans `build_article` + `cmd_build`
- [x] `--no-index`, `--no-readme`, `--no-nav`, `--drafts-only`, `--open` sur `build`
- [x] `--dry-run` ajoutée à `_GLOBAL_OPTIONS` + helpers `_write_file`, `_mkdir`
- [ ] Test qui vérifie qu'aucune écriture nue n'existe (non implémenté — les helpers existent mais le test AST n'a pas été écrit)
- [x] Manifeste `.lwp-manifest.json` écrit par `build`
- [x] `clean` avec manifeste (`--dry-run` par défaut, `--force` pour supprimer)
- [x] `watch` avec `--serve` en opt-in, `--port`, `127.0.0.1`
- [x] Tests pour chaque nouvelle option/commande
- [x] 630+ tests verts

## 7. Ce qui est exclu de cette version

- `series article add/remove/set` — hors périmètre, nécessite son propre cahier des charges
- `series new` — rejeté (DECISION-CLI.md)
- `series template` (lecture) — abandonné, remplacé par filtre `--templates` sur `audit`
- `theme set` en raccourci racine — rejeté (DECISION-CLI.md)
- `--name` — rejeté, on garde `--theme` partout
- `--clean` sur `build` — rejeté (DECISION-CLI.md) : cacher une suppression dans un build est le pire endroit
- `--no-serve` (opt-out) — inversé en `--serve` (opt-in) (DECISION-CLI.md)
