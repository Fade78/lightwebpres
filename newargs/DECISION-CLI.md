# Décisions — Refonte CLI

> Suite à la revue de PROPOSITION-CLI.md. Ce document capture
> les décisions d'implémentation ; la proposition reste la référence
> pour l'intention et la structure générale.

## 1. Phasage

La refonte est livrée en trois phases, pas en une :

- **Phase 1 — vocabulaire seul.** Renommages, alias, `--version`.
  Aucun comportement nouveau, aucune écriture nouvelle.
- **Phase 2 — lecture.** `series theme`, `--quiet`/`--verbose`/`--no-color`/
  `--timestamp`, `--strict` sur audit, `--all` et slugs multiples sur
  `theme show`/`theme gallery`. Rien qui écrive.
- **Phase 3 — écriture.** `clean` (avec manifeste), `--dry-run` (avec
  helper unique), `watch`, `--no-index`/`--no-readme`/`--no-nav`,
  `--open` sur `build` et `watch`, `--port` sur `watch`. Une commande à la fois.

## 2. Règles d'implémentation

### Noms de fonctions internes
Le GUI (Pyodide) appelle le CLI **comme un utilisateur humain** — il
invoque `lightwebpres` par ses arguments, pas les fonctions `cmd_*`
par leur nom Python. Les fonctions `cmd_*` peuvent donc être renommées
librement si cela aide la maintenance ; le contrat avec le GUI est
l'interface en ligne de commande, pas les noms internes.

### Globales restreintes
Huit options sont globales (acceptées avant la commande) :
`--lang`, `--quiet`, `--verbose`, `--no-color`, `--dry-run`,
`--timestamp`, `--version`, `--help`.

`--output` et `--format` restent spécifiques à leurs commandes :
`--output` désigne un répertoire pour build/demo/verify/watch et un
chemin de fichier pour `theme gallery` — une option, deux types,
l'ambiguïté que la refonte voulait tuer. `--format` ne concerne que
4 commandes sur 17.

### `--dry-run` est globale
`--dry-run` est une option **globale**, applicable à toute commande
qui écrit (`build`, `init`, `theme set`, `template update`, `clean`).
C'est la 7e globale. Voir §4 pour le mécanisme (helper unique).

### Précédence
L'option la plus proche de la commande gagne (conforme à git, docker) :
`lightwebpres --lang en build --lang fr` → `fr`.

### `--theme`, pas `--name`
`theme set` garde `--theme`. La redondance `set-theme --theme X` est
moins grave qu'une incohérence où la même valeur porte deux noms
d'option différents dans le même CLI (`--theme` sur `init`, `--name`
sur `theme set`).

### Messages d'erreur et artefacts générés
Les messages d'erreur qui recommandent une commande (`Run first:
lightwebpres install {td}`) et les artefacts générés qui contiennent
des noms de commandes (`.gitlab-ci.yml`, `themes-gallery.html`) sont
mis à jour dans la phase 1. Un message qui recommande une commande
dépréciée annule l'intérêt de la dépréciation.

## 3. Commandes modifiées ou abandonnées

### `clean` → nécessite un manifeste
`build` écrit `.lwp-manifest.json` dans `public/` listant tout ce
qu'il a produit. `clean` refuse de fonctionner sans ce fichier.
`--dry-run` par défaut, `--force` pour supprimer réellement.

### `watch` → `--serve` en opt-in
Écoute sur `127.0.0.1` uniquement (jamais `0.0.0.0`). `--serve`
active le serveur HTTP ; sans l'option, `watch` reconstruit seulement.
`--port N` (défaut 8000) fixe le port du serveur HTTP local. `--open`
ouvre le navigateur (premier `subprocess` de l'outil, surface de
confiance à documenter).

### `theme set` → pas de raccourci racine
`theme set` reste sous `series theme set` uniquement. Le nœud
`theme` ne touche jamais à une série. La forme canonique est
`lightwebpres series theme set [dir] --theme X`.

### `series template` → abandonné
Remplacé par un filtre `--templates` sur `audit`. Deux commandes qui
répondent partiellement à la même question, c'est deux endroits à
tenir synchronisés.

### `--clean` sur `build` → abandonné
`series clean` existe. Cacher une suppression dans une commande de
construction est le pire endroit pour la cacher.

## 4. Interactions spécifiées

### `--quiet`
Supprime la progression (articles en cours, résumé final), jamais la
valeur demandée. `resolve` et `theme show --format json` produisent
leur réponse sur stdout même avec `--quiet`.

### `--no-nav`
Si l'article contient une fiche `series-nav`, le placeholder
`{SERIES_NAV_PLACEHOLDER}` est remplacé par une chaîne vide. Le
conteneur (le `<h2>` et le `<div class="series-list">`) reste dans
le HTML, vide. Pas d'erreur.

### `--no-index` / `--no-readme`
`--no-index` saute `build_index()` : aucun `index.html` généré. Pour
une série d'un seul article, ou quand l'index est géré ailleurs.
`--no-readme` saute `build_readme()` : aucun `README.md` généré.
Aucun effet de bord : ce sont des fichiers indépendants.

### `--open` sur `build`
Ouvre le navigateur (`webbrowser.open()`, déjà utilisé dans le code)
sur le résultat après le build. Opt-in : sans l'option, pas
d'ouverture.

### `--all` et slugs multiples sur `theme show` / `theme gallery`
`theme show <slug> [<slug>…]` décrit un ou plusieurs thèmes dans
l'ordre donné. `theme show --all` décrit tous les thèmes intégrés.
`theme gallery [<slug>… | --all]` restreint ou génère la galerie.
Slugs inconnus → erreur fatale qui liste les slugs valides.

### `--drafts-only`
L'index et la navigation inter-articles pointent vers des pages non
construites. Accepté : c'est un aperçu, pas une publication.

### `--dry-run`
Toute écriture (fichier, répertoire) passe par un helper unique.
Un test vérifie qu'aucun `open(…, 'w')`, `write_text`, `mkdir`,
`shutil.copy` n'existe hors de ce helper. Si `--dry-run` est actif,
le helper journalise l'action sans l'exécuter.

## 5. Artefacts à migrer (phase 1)

| Artefact | Occurrences | Action |
|---|---|---|
| `themes-gallery.html` | 33 × `install my-series --theme` | Régénérer avec `lightwebpres theme gallery` |
| `.gitlab-ci.yml` (template) | 1 × `build . --lang {lang}` | Le template est corrigé ; les fichiers déjà générés chez les utilisateurs restent valides (l'alias `build` survit) |
| Messages d'erreur | 4 × `Run install first` | Remplacer `install` → `init`, `check` → `verify`, etc. dans `cmd_demo`, `cmd_refresh_templates`, `cmd_theme_info`, `cmd_set_theme` |
| Sortie de fin d'`install` | 1 × `lightwebpres build {td}` | Corrigé |
| `--help` | 1 | Régénéré automatiquement (lit les tables live) |

## 6. Tests

Les 138 appels utilisant les anciens noms de commandes dans la suite
de tests sont migrés vers les formes canoniques dans la phase 1.
Les assertions qui vérifient le contenu de `stderr` (messages d'erreur)
sont adaptées aux nouveaux noms.

## Références

- `PROPOSITION-CLI.md` — proposition d'origine
- `specifications.md` — spécification normative du format
- `GUIDE.md` — guide utilisateur
