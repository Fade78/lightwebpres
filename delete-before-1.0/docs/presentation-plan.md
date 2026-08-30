# Plan de la présentation LightWebPres

Matière pour une série d'articles / un deck LWP présentant l'outil.
Document d'étape (à supprimer ou absorber une fois la série faite).

---

## 1. Avantages par rôle (exhaustif)

| Rôle | Besoin | Avantage / fonction | Où |
|---|---|---|---|
| **Auteur / rédacteur** | Écrire sans apprendre un framework | Markdown étendu, pas de CSS/JS à écrire ; 3 niveaux (série → article → fiche) | spec §4, skill, GUIDE §3 |
| Auteur | Structure claire | 4 types de fiche (cover, standard, series-nav, full-article) fermés et validés | spec §3.3, skill |
| Auteur | Champs auto-descriptifs | Cascade de champs (series.json > meta > contenu) ; tout retombe sur un défaut dérivé du contenu | spec §20.3, skill, GUIDE §4 |
| Auteur | Ne pas perdre de contenu | Switch champs → texte libre unidirectionnel et permanent dans une fiche ; champ dupliqué = dernier gagne (override) | skill, spec §22.2 |
| Auteur | Figure clé mise en avant | `highlight` + `highlight-caption` (figure + légende) | spec §3.3.2 |
| Auteur | Encadré factuel | `fact-label` + `fact-variant` (warning…) | spec §3.3.2, §6.4 |
| Auteur | Citer sa source | champ `source` (emplacement stylé dédié, pas de citation inline) | skill, spec §3.3.2 |
| Auteur | Notes de bas de page | Notes Markdown standard `[^x]` ; numérotation par position, pas par label | spec §6.5, skill |
| Auteur | Notes du conférencier | `note:` (multi-ligne, jamais rendue, panneau présentateur N) | spec §6.5.2, GUIDE §9 |
| Auteur | Placement des notes | `notes_placement: local\|page` + `notes_tooltip: on\|off` (cascade) | spec §6.5.1, skill |
| Auteur | Long-form inclus | `full-article` (fichier `.md` externe, conversion complète) | spec §3.3.4, skill |
| Auteur | Tableaux comparatifs | `comparison-table` + verdicts `.yes/.no/.partial` + `col-signal/col-snap` | spec §6.1, skill |
| Auteur | Images | Figure centrée si seule sur sa ligne (+ légende), inline sinon ; lien cliquable wrap | spec §6.1 |
| Auteur | Typographie automatique | Espaces insécables (FR) avant `;:!?»` `%` milliers unités `×≈` ; désactivable par article | spec §17, GUIDE §lang |
| Auteur | Styling ponctuel | Tags d'instance `{color} {font} {sc} {strike} {u} {mono} {align}` | spec §6.4, skill |
| Auteur | Restyler une page | `style.*` dans le bloc meta (mêmes propriétés que settings.conf) | spec §9.6.1, skill |
| Auteur | Vérifier en écrivant | `audit` (non bloquant) + `verify` (gate) ; `resolve` pour comprendre une valeur | GUIDE §6 |
| Auteur | Démarrage rapide | `init` + `demo` (3 articles d'exemple) | GUIDE §2 |
| Auteur | Simple quand même | Skill embarqué : un agent fait intermédiaire (premier niveau d'accès) | agent/skills/, README |
| **Orateur / présentateur** | Présenter live | Mode présentation plein écran : clavier (↑↓ Home F B/W/T), souris (clic avance/retour, double-clic fullscreen, molette exit), tactile (swipe) | spec §18, GUIDE §9, README |
| Orateur | Réorienter l'attention | B/W/T : écrans qui cachent la fiche pour ramener l'attention sur l'orateur (T = couleur de fond du thème) | spec §18, GUIDE §9 |
| Orateur | Se repérer | Compteur `X / N` bas-gauche (toujours affiché) + saut par numéro (tape un numéro, Entrée) | GUIDE §9, spec §18 |
| Orateur | Lire en avance | Panneau présentateur (N) : `note:` courant + titre de la fiche suivante | spec §18, GUIDE §9 |
| Orateur | Numéro gravé | `--slides-page-numbers on` / `slide_page_numbers` (opt-in, cascade, défaut off) | spec §3.3.5, README |
| Orateur | Imprimer/PDF | Une fiche par feuille (Ctrl/Cmd+P), chrome de nav retiré, couleurs du thème conservées | GUIDE §9, spec §18 |
| Orateur | Plein écran sans surprise | Neutralise l'économie d'énergie OS ; curseur masqué après 1s, revient après 250ms continu | README, spec §18 |
| Orateur | Navigation fluide | Boutons de nav qui s'estomp après 3s (1s en fullscreen) ; souris = télécommande | README, GUIDE §9 |
| **Intégrateur / DevOps** | CI gate | `verify` : rebuild en mémoire, diff vs `public/`, exit non-zero sur drift | GUIDE §8, spec §11 |
| Intégrateur | Sorties optionnelles | `--no-index`/`--no-readme`/`--no-nav`/`--drafts-only` | README Options, spec §12 |
| Intégrateur | Aperçu brouillons | `--include-drafts` (build+verify) ; bannière « preview » sur la page | spec §11, GUIDE |
| Intégrateur | Reconstruction ciblée | `--only file.html` (retombe sur build complet si index/nav changé) | spec §11.3.1, README |
| Intégrateur | Pas d'écriture accidentelle | `--dry-run` globale (helpers `_write_file`/`_mkdir`) | DECISION §4, spec |
| Intégrateur | Nettoyage sûr | `clean` (manifeste `.lwp-manifest.json`, dry-run par défaut, `--force`) | README, DECISION |
| Intégrateur | Serveur de dev | `watch` (`--serve` opt-in, `--port`, `127.0.0.1` uniquement) | README, GUIDE |
| Intégrateur | Logs horodatés | `--timestamp` (RFC 3339), `--quiet`/`--verbose` | README Options |
| Intégrateur | Config par env | `LWP_SERIES_DIR`, `LWP_OUTPUT_DIR`, `LWP_LANG`, `LWP_TEMPLATES_DIR`… | README, spec |
| Intégrateur | CI prêt à l'emploi | `.gitlab-ci.yml` généré (`init --gitlab-ci`, opt-in) | GUIDE §8 |
| Intégrateur | Exit codes significatifs | Toute commande : exit non-zero sur erreur ; `audit` non bloquant sauf `--strict` | README, GUIDE §8 |
| Intégrateur | Reproductibilité | stdlib only, pas de réseau au build, pas de wheel/lockfile | README, AGENTS |
| Intégrateur | Completion shell | `completion --shell bash\|zsh` (tab sur commandes/options) | README, GUIDE §10 |
| Intégrateur | Alias legacy | Anciens noms acceptés 1 version MAJEURE + `[WARN]` (scripts existants ne cassent pas) | spec §11.16, README |
| **Auteur / curateur de thème** | Appliquer un thème sans CSS | Propriétés typées (`component.axis: value`), 5 couches (défaut → thème → settings.conf → style.* → instance) | spec §9, GUIDE §5 |
| Curateur | Catalogue fourni | 34 thèmes intégrés, rendus et mesurés ; la construction des palettes reste éditoriale | `theme list`, spec §9.5 |
| Curateur | Inspecter visuellement | `theme gallery` (HTML auto-contenu, 4 panneaux : cover/card+note/notes/full-article, filtres facets) | README, spec §11.7 |
| Curateur | Mesurer un thème | `theme show <slug>` (palette, fonts, facets, contrastes mesurés par catégorie, `--format json`) ; rapport seulement | README, GUIDE §5 |
| Curateur | Thème effectif | `series theme [dir]` (après les pins de settings.conf) | README |
| Curateur | Sélectionner un thème | `series theme set --theme X` (réécrit la ligne `theme:`, pins conservés) | GUIDE §5, spec §11.10 |
| Auteur | Personnaliser finement | `templates/settings.conf` (propriétés) + `templates/custom.css` (règles) | GUIDE §5, spec §9.4 |
| Auteur | Comprendre une valeur | `resolve <name>` (cascade + niveaux perdants ; forme du nom = type de cascade) | GUIDE §6, spec §11.12 |
| Mainteneur | Auditer les templates | `audit --templates` (dérive scaffold, variables retirées) ; pas une correction de palette | README, DECISION |
| Curateur | Lire les mesures d'accessibilité | `theme show` / `series theme` ; verdicts forme+couleur (WCAG 1.4.1) | spec §9.5, BACKLOG |
| Auteur | Énumérer les instances | `audit` compte les tags d'instance par article | skill, spec §9.6.3 |
| **Agent IA** | Format lisible | Markdown + champs one-line ; commentaires `lwp:` namespacés | skill, spec §4 |
| Agent | CLI non-interactif | Jamais de prompt bloquant ; tout en flags/exit codes | README, AGENTS |
| Agent | Auto-vérification | `audit`/`verify`/`resolve` pour valider ce qu'il écrit | skill, GUIDE §6 |
| Agent | Sortie machine | `--format json` (resolve, status, theme show, series theme) | README Options |
| Agent | Skill embarqué | `agent/skills/lightwebpres/SKILL.md` (format) + `sourced-presentation/SKILL.md` (méthode) | agent/skills/ |
| Agent | Orientation dépôt | `AGENTS.md` (commandes, structure, conventions, licence) | AGENTS.md |
| Agent | Intermédiaire pour l'auteur | Skill = premier niveau d'accès (l'agent écrit le LWP pour celui qui veut « juste écrire ») | README, skills |
| **Lecteur / audience** | Auto-contenu | 1 fichier `.html` par page (CSS+JS inline), s'ouvre depuis disque ou tout hébergement statique | README, spec §18 |
| Lecteur | Portabilité | `file://` ou statique ; pas de serveur, pas de runtime | README |
| Lecteur | Accessibilité | Verdicts forme+couleur (dichromatisme), contrastes mesurés, AA visé | spec §9.5 |
| Lecteur | Navigation inter-articles | Bloc `series-nav` généré depuis series.json (retour à la série) | spec §3.3.3 |
| Lecteur | Index de série | `index.html` généré (cartes d'articles) | spec §11.3 |
| Lecteur | Partage 1 clic | Lien/QR code, 3 portées (série / article / fiche courante), côté client | README, GUIDE §9 |
| Lecteur | Lisibilité | Mesure `ch` viewport-invariante (45–67 car./ligne), type fluide avec plancher | spec §9, ETUDE |
| **Utilisateur navigateur (web/)** | Sans installation | `web/` : un onglet dépose un zip à construire, l'autre tire/build/pousse vers GitLab | README, web/ |
| Utilisateur navigateur | Même moteur | Tourne sous Pyodide avec l'exécutable `lightwebpres` tel quel (pas de réimplémentation) | web/app.py, spec §23 |
| Utilisateur navigateur | Push GitLab | `web/git_sync.py` (pull/build/push via API v4) | web/ |
| **Éditeur avancé (lightwebpres-gui)** | Édition en ligne | Projet séparé : navigateur de fichiers + CodeMirror + bouton build | lightwebpres-gui (dépôt distinct) |
| Éditeur avancé | Stockage persistant | OPFS, hors-ligne (PWA, Service Worker cache-first) | lightwebpres-gui |
| Éditeur avancé | Chiffrement au repos | AES-GCM-256 + Argon2id, code de récupération | lightwebpres-gui |
| Éditeur avancé | Import/export | zip + GitLab pull/push | lightwebpres-gui |
| Éditeur avancé | Preview live | Édition `settings.conf`/`custom.css`/`nav.js` avec rendu `build_article()` en direct | lightwebpres-gui |
| **Extendeur / contributeur** | Modifier/redistribuer | GPL v3 : extension ouverte | COPYING, AGENTS |
| Extendeur | Diffuser ses présentations | Output Exception : la sortie est sous la licence de l'auteur du texte, pas celle du logiciel (sauf si l'œuvre est elle-même un générateur) | COPYING.EXCEPTION, AGENTS |
| Extendeur | Intégrer | Intégration verticale (un outil toute la chaîne) + horizontale (web/ léger + GUI lourd sous Pyodide) | AGENTS, spec §1.2/§23 |
| **Mainteneur** | Code unique | Single-file Python, stdlib only, ~13 300 lignes | AGENTS, spec |
| Mainteneur | Tests black-box | 742 tests en découverte (729 dans test_lightwebpres) + 13 tests navigateur Playwright | AGENTS, tests/ |
| Mainteneur | Aide synchrone | `--help` maintenu à la main mais verrouillé par test contre les tables d'options | AGENTS, spec §11 |
| Mainteneur | Versionnage | Semver (spec §13.9) ; VERSION dans l'exécutable | AGENTS, spec |
| Mainteneur | Push contrôlé | Commit substantiel puis push vers `newargs`, sans push forcé | AGENTS |

---

## 2. Découpage proposé (un deck par angle)

1. **Vue d'ensemble** — « Markdown in, présentation auto-contenue out » (l'idée unificatrice).
2. **Écrire** — le format LWP, les 4 types de fiche, la cascade de champs (rôle auteur).
3. **Présenter** — mode orateur, B/W/T réorientation, panneau N, compteur, impression (rôle orateur).
4. **Appliquer et inspecter les thèmes** — propriétés typées, 5 couches, 34 thèmes, galerie, accessibilité mesurée (rôle auteur/curateur ; la direction artistique est externe).
5. **Automatiser** — CI gate, verify, clean, watch, env vars, exit codes (rôle DevOps).
6. **Étendre** — GPL + Output Exception, intégrations verticale/horizontale, web/ + GUI (rôle extendeur).
7. **Agents & accessibilité** — skills, CLI non-interactif, `--format json` ; accessibilité « juge pas concepteur ».

---

## 3. Variantes dans un seul fichier — tags + kicker (design final)

Objectif : une présentation **multilangue / multi-niveau** dans **un seul
fichier HTML** auto-contenu ; appui sur une touche → menu des tags
configurés ; bascule à l'exécution, sans rechargement. La langue n'est qu'un
usage d'un pattern plus général de **variantes filtrables**.

### Deux concepts séparés (le mot « tag » se scinde)

| Concept | Champ | Rendu HTML | Rôle |
|---|---|---|---|
| Label visible en haut du slide | **`kicker:`** (ex. « Recette ») | `<span class="slide-kicker">` | Étiquette éditoriale au-dessus du titre |
| Filtrage runtime (variantes) | **`tags:`** (ex. `fr fr-expert`) | `data-tags="fr fr-expert"` sur `<section>` | Pilote le menu et l'affichage conditionnel |

L'ancien champ `tag:` devient `kicker:`. Le composant thème `tag` devient
`kicker` (`tag.fg` → `kicker.fg`, `cover.tag` → `cover.kicker`, etc.). Le CSS
`.slide-tag` → `.slide-kicker`. Renommage transverse (code + tests + docs).

### Champ `tags:` — syntaxe et validation

- **Suite de mots séparés par des espaces** : `tags: fr fr-expert longversion`.
- **Case-insensitive** (normalisés en minuscules au build).
- **Caractères autorisés** : caractères de mot Unicode, chiffres, `-`, `_`.
- **Interdit** de commencer par `_` (réservé aux tags internes futurs).
- Après `casefold()`, le premier caractère doit être un caractère de mot autre
  que `_`; les suivants sont des caractères de mot ou `-`.
- Valeur invalide → erreur de build fatale nommant la fiche et le tag fautif.

### Tags système

| Tag | Effet |
|---|---|
| `default` | Tag **automatique** attribué à toute slide qui n'a pas de `tags:`. Une slide sans `tags:` est visible quand `default` est sélectionné. `default` est **toujours dans le menu**. À noter : une slide portant `default` (implicite ou écrit explicitement) apparaît sous **tout** tag sélectionné, pas seulement `default` — l'écrire (`tags: default fr`) ne la borne pas à deux variantes. |
| `excluded` | La slide **n'est pas compilée** — absente du HTML final. C'est une exclusion au build, pas un filtre runtime. Permet de commenter une slide dans la source sans la supprimer. |

### Comportement runtime (nav.js)

- Touche **`L`** → ouvre un menu (popover) listant tous les tags trouvés dans
  l'article (collectés depuis les `data-tags` des `<section>`), hors `excluded`
  (absent du HTML). `default` est toujours présent.
- Sélection d'un tag → seules les slides portant ce tag + les slides `default`
  (sans tags, contenu commun) sont visibles. Les autres passent en
  `display: none`.
- **Le compteur `X / N` se recalcule** sur les slides visibles (N devient
  dynamique). Le saut par numéro, les flèches, le panneau N, les ancres `#sN`
  opèrent sur le sous-ensemble filtré.
- Persistance : `localStorage['lwp-active-tag']`. Au chargement, tag actif =
  valeur persistée, sinon `default`.
- Le menu ne s'ouvre que si ≥ 2 tags sont présents (sinon : mono-variante,
  comportement inchangé).

### CSS

```css
/* Filtrage : une slide est visible si elle porte le tag actif
   ou si elle n'a pas de tags (default/commun). */
.slide[data-tags] { /* géré par JS via display */ }
```
Le JS pose `section.style.display = 'none'/'block'` selon le tag actif — pas
de règle CSS statique par tag (les tags sont dynamiques, non énumérables à
l'avance).

### Typographie par slide (changement de portée du moteur)

Aujourd'hui la typographie (espaces insécables FR, etc.) s'applique au niveau
de la **page** (`--lang fr` au build). Avec les variantes, une même page
contient des slides `fr` et `en` — la typographie doit s'appliquer **par
slide** selon son tag de langue.

- `series_meta.lang_tags: {"fr": "fr", "en": "en"}` dans `series.json`
  déclare quels tags sont des **tags de langue** et quel pack ils utilisent.
  Le tag `fr` utilise le pack de typo FR,
  le tag `en` le pack EN. Un tag non déclaré (ex. `expert`, `longversion`)
  n'est pas un tag de langue : il n'affecte pas la typo.
- Une slide sans tag de langue utilise la **langue par défaut** du build
  (`--lang` ou `LWP_LANG`).
- **Plusieurs engines typo** instanciés au build (un par langue déclarée) ;
  `apply_typo` reçoit l'engine correspondant au tag de langue de la slide.
- `audit` signale : un tag déclaré dans `lang_tags` qui n'a pas de pack de
  langue correspondant ; une slide portant un tag de langue sans pack.

### Source (authoring) — un seul fichier, variantes adjacentes

```markdown
<!-- lwp:slide:cover -->
kicker: Guide
tags: fr
## LightWebPres — le guide
summary: Markdown in, HTML auto-contenu out.

---

<!-- lwp:slide:cover -->
kicker: Guide
tags: en
## LightWebPres — the guide
summary: Markdown in, self-contained HTML out.

---

<!-- lwp:slide -->
kicker: Démonstration
## Une démo (pas de tags — commun à toutes les variantes)
...
```

Les versions fr/en d'une même slide sont **côte à côte** dans le même `.md` :
le manuel corrige l'un en voyant l'autre. C'est l'inverse du one-file-per-
language, qui éloigne les textes.

### Portée version

Pas de rétrocompatibilité requise (client unique). Le renommage `tag` →
`kicker` est un **breaking change** (MAJOR). Les fonctionnalités `tags` +
filtrage + typo par slide sont des ajouts (inclus dans le même MAJOR).

### Livrables

**Chantier A — renommage `tag` → `kicker`** (breaking) :
1. Code : parser, renderer, theme component, contrast sites, CSS skeleton,
   demo content, gallery mock, help text, lang packs, comments.
2. Tests : tous les refs à `tag`/`slide-tag`/`tag.fg`/`tag.font`/`tag.weight`/
   `tag.size`/`tag.tracking`/`cover.tag.fg`.
3. Docs : spec, GLOSSARY, README, GUIDE, skill, guide-deck, BACKLOG.

**Chantier B — `tags` + variantes + typo par slide** :
4. Parser : champ `tags:`, validation (regex, pas `_` initial, case).
5. Tags système : `default` (auto), `excluded` (skip au build).
6. Renderer : `data-tags` sur `<section>`, `excluded` = pas de HTML.
7. Typo par slide : multi-engine selon `lang_tags`, default lang pour slides
   sans tag de langue.
8. nav.js : touche `L`, menu, filtrage, recalcul compteur X/N, saut, ancres.
9. Audit : tags invalides, `lang_tags` sans pack de langue.
10. Tests : kicker (renommage), tags (filtrage, excluded, default, validation),
    typo par slide, e2e menu runtime.
11. Docs : spec, GLOSSARY, README, GUIDE, skill, guide-deck, BACKLOG (C3),
    AGENTS.

### Statut au 14 août 2026

Le chantier A (`tag` → `kicker`) est terminé et vérifié. Le chantier B
(`tags` + variantes) a maintenant ses livrables 4 à 9 implémentés :
parsing/validation, tags système, rendu `data-tags`, moteurs typographiques
par slide, filtrage runtime et audit non bloquant. Le menu est masqué lorsqu'un
article ne porte qu'une seule variante.

Le livrable 10 est couvert par 742 tests en découverte (tags, exclusion,
validation, menu généré, typographie par slide et audit) ; le test
navigateur du changement de variante est exécuté depuis le 2026-08-15
(Playwright installé). Le
livrable 11 est terminé : les contrats permanents, le guide source,
`docs/guide/` et l'entrée BACKLOG C3 sont à jour.

### Statut au 15 août 2026 (post-audit)

L'audit de cohérence d'août 2026 a trouvé un défaut bloquant sur le filtrage
visuel des variantes (règle CSS `[hidden]` battue par `display: flex`) et
un lot de dérives docs/code. La release `v0.33.0` corrige l'ensemble :
règle `.slide[hidden], .nav-btn[hidden]`, échappement HTML des chaînes de
pack, validation de `--lang`, options de `watch` alignées sur la doc,
`--help` complet, compteurs remesurés (34 thèmes, 246 propriétés,
13/21/17/17/11), et documentation mise en cohérence (spec, README, GUIDE,
SKILL, GLOSSARY, AGENTS).
