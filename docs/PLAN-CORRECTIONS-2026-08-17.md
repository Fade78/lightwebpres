# Plan de corrections — audit multi-axes du 2026-08-17

Fait suite à un audit six axes sur `main` @ `0d495aa` (`v0.33.3`), postérieur
à la refonte CLI et aux versions v0.23 → v0.33.

- **Périmètre** : l'exécutable, les tests, la documentation pérenne, les
  artefacts générés, le rendu navigateur. `to-be-deleted/` hors périmètre.
- **Méthode** : six axes conduits en parallèle — sécurité, chemins
  d'écriture, contrat CLI, qualité des tests par mutation, dérive
  documentaire, rendu mesuré au navigateur. Chaque constat listé ici a été
  **reproduit par exécution**, jamais seulement lu.
- **Référence** : la suite complète est verte au départ — **742 tests**,
  deux workers, ~90 s. Tout ce qui suit est donc un défaut que la suite
  actuelle **ne détecte pas**. C'est le résultat le plus important de
  l'audit.
- **Règle d'accompagnement** : un correctif n'est clos que lorsque son test
  a été **prouvé mordant par mutation** — casser le comportement, voir le
  test échouer, restaurer.

## Ordonnancement

Trois critères, dans cet ordre : ce qui **détruit ou divulgue** des données ;
ce qui **ment** (un drapeau qui annonce l'inverse de ce qu'il fait est pire
que son absence) ; ce qui **dérive**. Les lots regroupent par cause racine,
pas par symptôme.

| Lot | Contenu | Version cible | État |
|---|---|---|---|
| 0 | Fuite et perte de données | v0.33.4, seule | à faire |
| 5.1 | Hiérarchie typographique inversée | v0.34.0, en tête | à faire |
| 5.2–5.4 | Clavier, contraste 1.00:1, page fantôme | v0.34.0 | à faire |
| 1 | Le contrat CLI qui ment | v0.34.0 | à faire |
| 4 | Les dix tests morts | avec chaque correctif | à faire |
| 2, 5.5–5.8 | Robustesse du build, alignement, longueurs | v0.34.x | à faire |
| 3 | Documentation et artefacts générés | continu | à faire |

---

## Lot 0 — Urgent : fuite et perte de données

Cible **v0.33.4**, patch, à sortir seule.

### 0.1 — `--inline-images` lit n'importe quel fichier du disque

`lightwebpres:9096` (`_encode_inline_image`), atteint depuis `:7269` et `:7724`.

```python
img_path = articles_dir / src      # src vient du Markdown, non validé
data = img_path.read_bytes()
```

L'extracteur (`:7293`, `[^)\s"\[(]+`) autorise `..` et un `/` initial, or
`Path(a) / '/etc/passwd'` écrase la partie gauche. **Seul site de lecture de
fichier du programme qui n'appelle ni `_is_safe_relative_filename` ni
`_resolve_contained`.** Contourne aussi le garde-fou anti-symlink de
`copy_images`, dont le commentaire nomme précisément cette menace.

Reproduit : un article contenant `![](../../secret/id_rsa)`, construit avec
`build --inline-images`, produit dans `public/` un `data:` URI qui décode en
`ROOT-SECRET-CLE-PRIVEE-12345`. Même série, même symlink : `build` refuse
avec un avertissement, `build --inline-images` encode la clé.

**Correctif** : faire passer le chemin par `_is_safe_relative_filename` puis
`_resolve_contained`, comme tous les autres sites de lecture.

**Test qui doit mordre** : `![](../../x)` et `![](/etc/hostname)` rendent le
build fatal ; un symlink sortant est refusé, pas encodé.

### 0.2 — `clean` ignore `--dry-run`

`lightwebpres:10120`. Le `p.unlink()` est le seul appel destructeur du
programme et le seul à ne pas passer par la couche
`_write_file`/`_mkdir`/`_copy`.

Reproduit dans les deux ordres — `--dry-run clean s --force` et
`clean s --force --dry-run` — les fichiers sont réellement supprimés,
code 0, aucune mention de dry-run dans la sortie. Le parseur autorise
explicitement la combinaison (`:12889`).

**Correctif** : helper `_remove()` honorant `_LOG_STATE['dry_run']`.

**Test qui doit mordre** : `--dry-run clean --force` ne modifie aucune
empreinte du répertoire.

### 0.3 — `clean` efface tout ce qui n'est pas déclaré

`lightwebpres:10105-10121`. Le manifeste `public/.lwp-manifest.json` existe,
mais la règle appliquée est « supprimer tout le non-déclaré », l'**inverse**
de ce que la spec (`specifications.md:4086`) et le message d'erreur du code
(`lightwebpres:10097`) affirment tous deux.

Reproduit : `CNAME`, `.nojekyll`, `robots.txt`, `404.html`, une feuille de
style écrite à la main et un `.git/` complet supprimés. `rglob('*')` ne
saute pas les fichiers cachés. Incohérence : un fichier fait main **survit**
dans `img/`, parce que `_write_manifest:10077` re-bénit ce qui s'y trouve.

**Correctif** : inverser la règle en `manifeste_précédent − manifeste_courant`.
Le manifeste conserve sa liste précédente :
`{"files": [...], "previous": [...]}`. Un fichier jamais déclaré par aucun
build n'est jamais candidat.

**Test qui doit mordre** : `CNAME`, `.nojekyll`, `robots.txt`, `404.html`,
`.git/` survivent ; un article retiré est purgé.

### 0.4 — `LWP_OUTPUT_DIR` sur la racine détruit les sources

`lightwebpres:10092`. `build --output <racine de la série>` est accepté sans
avertissement, ce qui place un manifeste à la racine. Ensuite :

```
$ LWP_OUTPUT_DIR=<racine> lightwebpres clean s --force
Cleaned 24 orphan file(s)
```

Reproduit : tous les `articles/*.md`, `series.json`, les trois fichiers de
`templates/`, les deux packs de langue, `README.md`, `COPYING`, et
**l'exécutable `lightwebpres` embarqué**. `init` refuse un répertoire non
vide sans `--force` ; `clean` n'a aucun garde-fou équivalent.

**Correctif** : refuser de nettoyer un répertoire contenant `series.json`,
`articles/` ou `templates/`. En grande partie couvert par 0.3, mais à
garder en ceinture et bretelles.

**Test qui doit mordre** : `clean` sur une racine de série sort en erreur
sans rien toucher.

### 0.5 — La garde AST n'a aucun verbe de suppression

`tests/test_lightwebpres.py:2235-2244`. `test_no_bare_filesystem_write_outside_helpers`
ne vérifie que `write_text`, `mkdir` et `shutil.{copy,copy2,copyfile,copytree}`.
Absents : `unlink`, `remove`, `rmtree`, `rename`, `replace`, `write_bytes`,
`touch`, `makedirs`, `open(..., 'w')`.

**C'est ce qui a laissé passer 0.2**, et la correction la plus rentable du
lot : une commande qui *efface* traversait une garde conçue pour ce qui
*écrit*.

**Test qui doit mordre** : réintroduire un `p.unlink()` nu fait échouer la
garde.

---

## Lot 5.1 — Hiérarchie typographique inversée (critique)

Les tailles écrites **en dur dans le squelette** n'ont pas reçu l'échelle
donnée aux 35 propriétés du registre. Mesuré sur une page construite :

| | 1920 | 3840 |
|---|---|---|
| `h2` de fiche | 50,8 | 101,5 |
| `.summary` | 29,2 | 58,3 |
| `.full-article p` | 20,3 | 40,5 |
| `.full-article h2` | **22** | **22 — figé** |

À 3840, le titre de section de l'article long fait **22 px sous son propre
corps de texte à 40,5 px**. L'inversion commence à 1920. Également figés :
`.full-article h1/h3`, ses `table`/`blockquote`/`pre`, et **tout
`.slide-body`** (16 px sous un titre à 101,5 px). Conséquence visible :
`####`, défini comme *plus faible* qu'un titre, devient le plus grand titre
de la page ; et le même paragraphe rend à 16 px ou 47,5 px selon qu'un
`fact-label:` le précède.

20 sélecteurs sur 67 sondés ne bougent pas entre 1920 et 3840.

**Correctif** : donner à ces éléments des propriétés de registre en
`max(px, N vmin)`, plancher conservé.

**Test qui doit mordre** : voir « instrument 1 » ci-dessous.

---

## Lot 5.2–5.4 — Barrières

### 5.2 — Le filtre de variantes est inutilisable au clavier (WCAG 2.1.1)

5 × Tab laissent le focus sur `BODY`. Les boutons *sont* focusables et
Entrée applique bien le filtre : la barrière est le handler global, qui
`preventDefault()` sur tout sauf Échap/L (`~:5424`), ce qui annule le
déplacement du focus. `toggleTagMenu()` (`~:5130`) ne déplace jamais le
focus, donc le `role="dialog"` n'est jamais annoncé.

**Correctif** : déplacer le focus dans `.tag-menu` à l'ouverture, piéger Tab
à l'intérieur, rendre le focus à `#navTags` à la fermeture.

### 5.3 — Compteur d'orateur invisible sur 15 thèmes sur 34

Contraste **exactement 1.00:1** : sur un thème clair, `page.fg` et
`cover.bg.from` valent tous deux `color.ink`. La bordure du pastille est en
`currentColor`, elle disparaît aussi. Thèmes touchés : high-contrast,
newsprint, pop-lemon, vaporwave, nord, solarized, gruvbox, catppuccin,
rose-pine, blueprint, monochrome, crimson, sage, sprout (+1).

Cause : `.slide-counter { background: none; color: inherit }` — tous ses
voisins (`.presenter-panel`, `.tag-menu`, `.help-overlay`) sont en
`background: inherit` et passent AA.

Invisible au rapport de `theme show` par construction : `.slide-counter` est
un élément de squelette **sans propriété de registre**. Le rapport existant
est juste là où il regarde (4,1626:1 annoncé sur monokai, 4,17 mesuré au
navigateur) ; c'est son champ de vision qui est en cause.

À noter aussi : les points de navigation de `pop-tangerine` mesurent
**2,19:1** sur la couverture, sous le minimum de 3:1 (WCAG 1.4.11).

**Correctif** : `.slide-counter { background: inherit }`.

### 5.4 — Une page imprimée de trop, systématiquement

`document.querySelector('.slide:last-child')` est **`null`** sur toutes les
pages : le dernier enfant du body est un `<script>`, précédé du
`<footer class="page-footer">` (90 px, `display:block` en impression). Le
dernier slide garde donc `page-break-after: always` et le pied de page part
sur une feuille à lui. Mesuré : 6 slides → 7 pages, 4 → 5, sur quatre pages
de deux corpus.

Mutation vers `.slide:last-of-type` : 6 → 6, 4 → 4. Aucun contenu coupé ni
tronqué par ailleurs ; toute la chrome est correctement masquée à
l'impression.

**Correctif** : `.slide:last-child` → `.slide:last-of-type`.

---

## Lot 1 — Le contrat CLI ment

Cause racine commune à 1.1–1.3 : il n'existe **pas de niveau `warn`** dans
`log()`, et la progression du build n'y passe pas.

| # | Constat | Correctif |
|---|---|---|
| 1.1 | `--quiet` supprime les avertissements et garde la progression. Mesuré : sans → 1 warning / 645 o de progression ; avec → **0 warning / 645 o**. Direction dangereuse en CI | Router la progression par `log('info', …)` ; ajouter un niveau `warn` que `--quiet` ne supprime jamais |
| 1.2 | Les dépréciations sortent en `[ERROR]` sur un run à code 0 ; les vrais avertissements en `[INFO]`. `grep '^\[ERROR\]'` matche donc des succès | `_warn_legacy` passe sur le niveau `warn` |
| 1.3 | `--verbose` : **0 site d'appel** (`grep "log('verbose'"`). `--no-color` : écrit `:106`, jamais relu ; l'ANSI est retiré inconditionnellement | Implémenter `--no-color` (trois lignes) ; **décision à prendre** : implémenter ou retirer `--verbose` de `--help` |
| 1.4 | Tout positionnel après le premier est jeté en silence. `init A B` ne crée que `A`, sans un mot. Idem `status ec p1 nonsense`, `theme list junk`, `build ec -x`. `resolve` possède déjà le contrôle | Généraliser le contrôle d'arité de `resolve` |
| 1.5 | `<commande> --help` est **fatal** : `build --help`, `theme show --help`, `series --help` → exit 1. Aucune aide par nœud | Honorer `--help` en toute position |
| 1.6 | 8 commandes canoniques sur 13 nomment l'alias déprécié dans leurs erreurs (`status --strict` → « not an option of `series-info` ») | Table clé de dispatch → nom canonique |
| 1.7 | `theme gallery <répertoire>` sort en traceback Python | Attraper, émettre `[ERROR]` |
| 1.8 | Globales fatales en postfixe, acceptées et ignorées en préfixe. Incohérent dans les deux sens | Une règle unique |
| 1.9 | `--lang xx` passe : `<html lang="xx">`, exit 0, aucun avertissement | Valider que le pack se résout |
| 1.10 | Pas de marqueur `--` de fin d'options | L'ajouter |
| 1.11 | `theme show <dir> <slug> <slug>` jette les slugs, exit 0 | Erreur fatale, comme la spec l'exige |

Point ouvert : `audit --strict` sort à 0 sur une série dont le `build` émet
un `[WARNING]`, cet avertissement vivant dans le chemin de build. Trou de
couverture si `--strict` est censé être la barrière CI complète.

---

## Lot 4 — Tests qui ne mordent pas

13 mutations exécutées, 19 comportements couverts, 6 contre la suite
complète.

| # | Test | Mutation | Résultat |
|---|---|---|---|
| 4.1 | `test_no_nav_leaves_empty_container` (:1904) | `if include_nav:` → `if True:` | **742/742 vert**. Le test découpe sur la 1re occurrence de `series-list`, qui est **dans le `<style>`** : il inspecte 17 370 caractères de CSS et y cherche `<a href` |
| 4.2 | `test_watch_is_a_known_command` (:2125), `…output_switches` (:2166) | boucle de reconstruction vidée, `--serve` désactivé | **suite verte**. Seul le build initial est prouvé. `--port`/`--serve` : 0 occurrence dans l'arbre de tests |
| 4.3 | `SlideTags` (:179) + `test_web.SlideTagsRuntime` (:181) | chaîne assertée intacte, neutralisée par `.slide[hidden]{display:flex}` | **vert**. Les fiches filtrées seraient visibles. Le e2e lit `section.hidden`, jamais le style calculé. **§12 à l'identique** |
| 4.4 | `test_open_opens_browser_after_build` (:1988) | `if args.get('--open'):` → `if False:` | **vert**. Seule assertion : `returncode == 0` |
| 4.5 | Impression une fiche par feuille | `page-break-after: always` → `auto` | **aucun test**. Seuls les canaris d'octets réagissent |
| 4.6 | Panneau présentateur | le panneau ne lit plus la note | **aucun test**. « presenter » n'apparaît que dans 3 commentaires |
| 4.7 | `test_version_prints_version_and_exits_zero` (:1624) | version → `v0.0.0-wrong` | **vert**. `assertIn('LightWebPres v', …)` ne distingue rien |
| 4.8 | `test_completion_zsh_generates_valid_script` (:2263) | script zsh vidé | **vert**. Et le zsh émis est le corps **bash** verbatim |
| 4.9 | `test_custom_nav_js_is_used` (:3932) | le `nav.js` auteur s'ajoute au lieu de remplacer | classes ciblées vertes ; écouteurs liés deux fois |
| 4.10 | Deux tests à itération vide (:9527, :9778) | retirer les clés `.size` de `high-contrast` | passent à vide. `high-contrast` est le seul thème concerné |

**Diagnostic transversal** : les deux tests d'identité d'octets réagissent à
tout changement de CSS/JS, mais leur remède documenté est « régénérer ». Ce
sont des **détecteurs de changement, pas des gardes de comportement**, et ils
masquent l'absence de couverture derrière une impression de couverture.

**Ce qui mord** (à ne pas toucher) : `--no-index`, `--no-readme`,
`--drafts-only`, `--dry-run`, `--strict`, `clean --force`, les alias
dépréciés, et `ThemeEngineStaged.test_the_skeleton_and_the_registry_never_drive_the_same_thing`
— vraie garde structurelle contre §12 côté thèmes. Zéro `expectedFailure`,
zéro `except: pass`, les quatre harnais navigateur tournent réellement.

---

## Lot 2 — Robustesse du build

| # | Constat | Correctif |
|---|---|---|
| 2.1 | Écritures en place, sans temp+rename. Un build planté laisse une sortie mi-ancienne mi-nouvelle et une traceback Python brute, alors que tout le reste du fichier émet `[ERROR]` | Au minimum la ligne `[ERROR]` ; idéalement temp + `os.replace` |
| 2.2 | Le manifeste s'écrit en dernier (`:10331`) : après un build planté, `clean` désigne la **seule page à jour** comme orpheline. Reproduit | Écrire au fil de l'eau, ou refuser `clean` si le manifeste est plus vieux que la sortie |
| 2.3 | Une image supprimée reste publiée pour toujours : `_write_manifest:10077` rescanne `output/img` et re-bénit le fichier périmé | Construire la liste d'images depuis la **source** |

En partie couvert par 0.3 — à traiter après, pas avant.

---

## Lot 5.5–5.8 — Rendu, suite

| # | Constat |
|---|---|
| 5.5 | Panneau présentateur : aucun `role`, aucun `aria-live`, **Échap ne le ferme pas** (seul overlay dans ce cas), contenu non atteignable au Tab, et **15,2 px sur un vidéoprojecteur 4K** |
| 5.6 | `.slide-num` positionné contre la fiche et non contre la colonne : écart +29 px à 768, +121 px à 1920, **+275 px à 3840** ; le signe s'inverse sur téléphone. Sa taille, elle, monte correctement |
| 5.7 | Longueurs encore figées « contre le glyphe » : soulignement des liens (1 px / 3 px sous un texte à 40,5 px), six propriétés `*.tracking` en px (0,167 em → 0,062 em), paddings de `code`, `.fact-box`, `.series-item`, cellules de tableau, `pre`, `blockquote` |
| 5.8 | `nav-btn.size` monte de 20 à 54 px mais le bouton reste 44×44 : **le glyphe déborde de son cercle de 16 px** à 4K. `.nav-btn-home` figé à 17 px, 3,2× plus petit que ses voisins. Toute la chrome (compteur, menu, panneau, aide) est figée |
| 5.9 | Les variantes de fiche **ne peignent rien** par conception ; rien ne garantit qu'une variante définie par l'auteur passe AA |

**Réfutations mesurées, au crédit du code** — les petits écrans n'ont pas
empiré : 375×667 → 3/8 cartes qui débordent, pire cas +223 px, contre 3/8 et
225 px avant tout le travail d'échelle ; 768×1024 → 0/8. Les nouveaux
composants coûtent **0 px de hauteur**. Le centrage §12/§13 tient à **0,0 px**
aux trois largeurs, y compris pour les fiches taguées et à variantes.

---

## Lot 3 — Documentation et artefacts générés

| # | Où | Quoi |
|---|---|---|
| 3.1 | `GUIDE.md:462-477` | Le `.gitlab-ci.yml` documenté (deux étapes, `verify` puis `build`) n'est pas celui qui est écrit (`lightwebpres:6109`, une étape). La spec est correcte et dit que c'est délibéré. **Décision** : corriger le GUIDE |
| 3.2 | `lightwebpres:3008` | Chaque `settings.conf` généré enseigne `set-theme` et `refresh-templates`. Seul artefact généré encore sur les anciens noms — invisible à un grep sur `"lightwebpres "` |
| 3.3 | `lightwebpres:9997-9999` | La complétion propose `theme set` (refusé par l'outil) et liste `theme` deux fois, alors que GUIDE et spec promettent qu'elle est dérivée des tables |
| 3.4 | `lightwebpres:9763` | Message nommant `custom.js`, fichier inexistant — affiché au moment précis où l'utilisateur décide si `template update` est sans risque |
| 3.5 | `lightwebpres:31-45` | La docstring du module ignore `clean`, `watch`, `completion`. `print_help()`, lui, est complet (38 options vérifiées) |
| 3.6 | `README.md:373`, `GUIDE.md:190`, `README.md:560`, `README.md:326` | Trois violations de « on ne dit jamais *ce n'est plus* » |
| 3.7 | `specifications.md` §2.4 | Le document normatif ne connaît **aucune** option globale — ni `--quiet`, ni `--dry-run`, ni `--version`. Le plus structurel |
| 3.8 | `specifications.md` §11.9.1, `--help` | `theme show` documenté à un seul slug ; `--help` contient encore *install*, *check*, *set-theme* dans sa prose, et cite `DECISION-CLI §3`, rangé dans `to-be-deleted/` |

**Sans dérive** : `SKILL.md` — tous les champs, les restrictions par type de
fiche, les niveaux de titre, les balises d'instance correspondent exactement
au code. Mais son test de garde ne lit **jamais `SLIDE_TYPES`** : les quatre
noms de types et la répartition des champs par type ne sont couverts par
aucune assertion.

---

## Trois instruments à ajouter

Trois audits successifs ont trouvé la même chose sous trois costumes, et à
chaque fois **l'instrument n'avait pas la colonne** : §9 « les composants
sont-ils d'accord entre eux », §11 « combien y a-t-il de tailles », §13
« cette longueur est-elle dessinée contre le texte », et aujourd'hui
« combien de littéraux échappent au registre ».

1. **Un test comptant les tailles rendues identiques entre 1920 et 3840.**
   Aurait attrapé 5.1 et 5.8 d'une seule requête — 20 sélecteurs sur 67 sont
   plats. Mesure, pas opinion.
2. **Une passe de contraste mesurant la page rendue, pas le registre.**
   Aurait attrapé 5.3, invisible au rapport actuel par construction.
3. **L'alphabet complet de verbes dans la garde AST** (0.5). Aurait attrapé
   0.2 et empêche la récidive.

---

## Hors lots

- **Branche `newargs`** : destruction sûre, vérifiée — 0 commit propre, tête
  = `339ef0b` (`v0.31.0`) présente dans `main`, aucun tag orphelin, aucune
  pull request. `git push origin --delete newargs`.
- **`to-be-deleted/`** : `--help` pointe encore dedans (3.8).
- **Releases** : tags jusqu'à `v0.33.3`, dernière release publiée `v0.22.0`.
  Onze versions taguées sans release.
- **GUI** : moteur embarqué figé à `v0.19.0`. Les fonctions `cmd_*` ont
  survécu à la refonte CLI (`cmd_check`, `cmd_install`, `cmd_series_info`,
  `cmd_set_theme`, `cmd_refresh_templates`, `cmd_build`, `cmd_demo`,
  `cmd_audit` existent toujours), donc une revendorisation reste possible —
  mais elle traverserait le lot 0, donc après.
