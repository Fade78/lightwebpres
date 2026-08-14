# Proposition — Refonte de l'interface en ligne de commande

> **Statut :** proposition de conception, non normative.
> **Périmètre :** l'interface en ligne de commande de `lightwebpres`
> (commandes, options, vocabulaire, hiérarchie). Ne touche ni au format
> d'article `.md`, ni à `series.json`, ni au moteur de rendu.
> **Références :** `specifications.md` §2.4, §11, §13.5 ; `GUIDE.md` ;
> `README.md` ; le code (`main()`, `parse_cli_options()`, `print_help()`).
> **Approche retenue :** sous-commandes imbriquées (modèle `git`/`docker`),
> avec des raccourcis à la racine pour les commandes les plus fréquentes.
> En interne, la structure en nœuds est préservée pour l'extensibilité.
>
> **Avertissement —** `DECISION-CLI.md` arbitre plusieurs points de cette
> proposition. Les sections suivantes sont **dépassées** et gardées pour
> historique ; voir DECISION pour la décision finale :
> - §4.3, §5.11, §8.4 : `theme set` n'a **pas** de raccourci racine.
> - §4.2, §4.3, §8.1, §8.4 : `series template` (lecture) est **abandonné**,
>   remplacé par un filtre `--templates` sur `audit`.
> - §5.8, §7.1 : `--clean` sur `build` est **abandonné**.
> - §5.11, §12.3 : `--name` est **rejeté**, on garde `--theme`.
> - §5.7 : `--no-serve` (opt-out) est **inversé** en `--serve` (opt-in).
> - §6.2 : la liste des globales est **incomplète** (voir DECISION §2 pour
>   la liste finale de 8 options, incluant `--no-color`, `--dry-run`,
>   `--timestamp`).
> - §13 : toutes les questions ouvertes sont tranchées dans DECISION.

---

## 1. État des lieux

### 1.1 Les commandes actuelles

Le CLI est **plat** : toutes les commandes sont au même niveau, sans
groupement.

```
lightwebpres install [dir]
lightwebpres demo [dir]
lightwebpres build [dir]
lightwebpres check [dir]
lightwebpres audit [dir]
lightwebpres refresh-templates [dir]
lightwebpres themes [--filters]
lightwebpres theme-info <slug|dir>
lightwebpres set-theme [dir] --theme X
lightwebpres themes-gallery [path]
lightwebpres series-info [dir]
lightwebpres resolve [dir] <name>
lightwebpres help | --help | -h
```

Les trois formes d'aide (`help`, `--help`, `-h`) sont équivalentes ; sans
argument du tout, l'aide s'affiche aussi.

### 1.2 Les options actuelles

| Option | Commandes | Rôle |
|---|---|---|
| `--lang fr\|en` | install, demo, build, check, audit | langue (typo + chaînes UI) |
| `--output public/` | demo, build, check | répertoire de sortie |
| `--force` | install | procéder même si non vide |
| `--theme nom` | install, set-theme | appliquer une palette |
| `--polarity/--intensity/--hue` | themes | filtrer par facette |
| `--gitlab-ci` | install | écrire un `.gitlab-ci.yml` |
| `--language-file chemin` | build, check | pack de langue explicite |
| `--no-typography` | build, check | désactiver la typo |
| `--include-drafts` | build, check | construire les brouillons |
| `--only page` | build | reconstruire un seul article |
| `--nav-cache chemin` | build | chemin du cache d'empreinte |
| `--build-stamp` / `--build-stamp-minimal` | build | marqueur de fraîcheur |
| `--scaffold` | refresh-templates | régénérer la surface commentée |
| `--format text\|json` | theme-info, series-info, resolve | format de sortie |
| `--article fichier` | resolve | niveau article de la cascade |

### 1.3 Les variables d'environnement

```
LWP_SERIES_DIR    (défaut .)
LWP_ARTICLES_DIR  (défaut $LWP_SERIES_DIR/articles)
LWP_TEMPLATES_DIR (défaut $LWP_SERIES_DIR/templates)
LWP_LANGUAGE_DIR  (défaut $LWP_SERIES_DIR/language)
LWP_OUTPUT_DIR    (défaut $LWP_SERIES_DIR/public)
LWP_LANG          (défaut fr)
```

---

## 2. Problèmes identifiés

### 2.1 Incohérences de vocabulaire

| Problème | Exemple | Pourquoi c'est gênant |
|---|---|---|
| **`install` est un faux-ami** | `install my-series` | On ne *installe* pas un logiciel, on *initialise* un projet. `install` évoque `pip install` / `make install`. |
| **`check` est trop vague** | `check my-series` | `check` pourrait être n'importe quoi. `verify` dit ce qu'il fait : vérifier que le build est à jour. |
| **Groupe `theme` éparpillé** | `themes`, `theme-info`, `set-theme`, `themes-gallery` | Quatre commandes sur le même sujet, avec des préfixes incohérents (pluriel, singulier+tiret, verbe+nom, pluriel). |
| **`refresh-templates` est long** | `refresh-templates my-series` | 17 caractères pour une commande de maintenance rare. |
| **`series-info` est verbeux** | `series-info my-series` | `status` serait plus court et plus naturel. |
| **`--scaffold` est une sous-commande déguisée** | `refresh-templates --scaffold` | C'est une action distincte présentée comme une option. |

### 2.2 Problèmes structurels

1. **Pas de groupement.** Toutes les commandes sont au même niveau ; rien
   ne signale visuellement qu'elles appartiennent à des familles
   (série, thème, template).
2. **`theme-info` a deux usages dans une seule commande.** `theme-info
   <slug>` (thème intégré) vs `theme-info [dir]` (thème effectif). Ça
   marche, mais c'est ambigu : le même mot d'ordre fait deux choses
   différentes selon la forme de l'argument.
3. **`--lang` est répété sur 5 commandes.** C'est une préférence globale
   qui devrait pouvoir se placer une fois, avant la commande.
4. **`--theme` est redondant dans `set-theme`.** `set-theme --theme X`
   répète le mot « theme » deux fois.
5. **Pas de commande de prévisualisation.** Pour voir le résultat, il
   faut `build` puis ouvrir le fichier à la main. Un `watch` (surveillance
   + reconstruction + serveur local) manque.
6. **Pas de commande de nettoyage.** `build` est additif par conception
   (§11.3) : les fichiers orphelins restent dans `public/`. Aucune
   commande ne permet de les purger.
7. **Pas de `--version`.** Le numéro de version n'est visible que dans
   l'en-tête de `--help`.

---

## 3. Principes directeurs de la proposition

La refonte doit respecter la philosophie du projet, qui est déjà très
forte :

1. **Vocabulaire fermé.** Comme les conventions de nommage des champs
   (§20.0), le vocabulaire des commandes doit être un ensemble fini de
   verbes, jamais inventé au cas par cas.
2. **Un mot, un sens.** Chaque commande fait exactement une chose, et son
   nom le dit.
3. **Cohérence par objet.** Toute commande vit sous l'objet qu'elle
   manipule (`series`, `theme`). C'est la **forme canonique**. En
   interne, la structure en nœuds est préservée pour l'extensibilité —
   un nouvel objet s'ajoute sans casser les raccourcis existants.
4. **Raccourcis en couche.** Les verbes courts à la racine sont une
   couche de confort surajoutée, jamais la source de vérité. On peut les
   ajouter/retirer sans toucher à la structure. La forme canonique reste
   `series <verbe>` dans la documentation et les scripts.
5. **Zéro dépendance.** Le parseur est fait à la main (§13.4). La
   refonte doit rester implémentable en stdlib.
6. **Compatibilité.** La refonte est une **proposition** ; si elle est
   adoptée, elle doit prévoir une période de transition (alias) pour ne
   pas casser les scripts existants.
7. **Usage scripté et LLM.** Toute commande reste non-interactive, avec
   un code de sortie signifiant (0 = succès, non-nul = échec ; voir
   §2.4 et §11.4 de `specifications.md`).
8. **`audit` reste `audit`.** Le mot `lint` appartient à l'écosystème
   développeur (ESLint, flake8) et évoque du code. `audit` vérifie des
   conventions éditoriales (pas de cover, pas de description, scaffold
   désynchronisé) — c'est de l'édition, pas du code. Le projet s'adresse
   à un public rédacteur. `audit` est conservé.

---

## 4. Proposition : deux objets, des raccourcis

### 4.1 Le principe

On regroupe les commandes sous des **objets** (`series`, `theme`),
chacun étant un **vrai nœud** de l'arbre de commandes — pas un simple
préfixe cosmétique. Chaque nœud a son propre `--help`, et l'aide racine
ne liste que les raccourcis et le nœud `theme`.

L'objet `series` étant dominant (13 commandes sur 17), presque toutes
ses commandes ont un **raccourci à la racine**. L'expérience quotidienne
est plate : on tape `build`, `watch`, `audit` directement. La forme
canonique `series <verbe>` reste la source de vérité pour les scripts
et la documentation.

### 4.2 L'arbre interne (forme canonique)

```
lightwebpres
├── series      (une série : créer, construire, vérifier, lire, modifier)
│   ├── init
│   ├── demo
│   ├── build
│   ├── verify
│   ├── audit
│   ├── status
│   ├── watch
│   ├── clean
│   ├── resolve <name>
│   ├── theme              (lire le thème effectif)
│   └── theme set <slug>   (changer le thème)
├── theme       (le catalogue : lister, décrire, galerie)
│   ├── list
│   ├── show <slug> [<slug>…]
│   └── gallery [<slug>…]
└── --version
```

> **Note —** `series template` (lecture) était dans la proposition
> initiale. Il est **abandonné** (DECISION-CLI.md §3) : deux commandes
> qui répondent partiellement à la même question sont deux endroits à
> tenir synchronisés. Remplacé par un filtre `--templates` sur `audit`.
> `series template update` (ex-`refresh-templates`) est conservé, mais
> sans nœud `template` de lecture ; le raccourci racine `template update`
> reste (voir §4.3).

### 4.3 L'arbre vu par l'utilisateur (raccourcis)

```
lightwebpres
├── init [dir]              → series init
├── demo [dir]              → series demo
├── build [dir]             → series build
├── verify [dir]            → series verify
├── audit [dir]             → series audit
├── status [dir]            → series status
├── watch [dir]             → series watch
├── clean [dir]             → series clean
├── resolve [dir] <name>    → series resolve
├── template update [dir]   → series template update
├── theme list              (catalogue)
├── theme show <slug>       (catalogue)
├── theme gallery           (catalogue)
├── series theme [dir]      (canonique, pas de raccourci)
├── series theme set [dir] <slug>  (canonique, pas de raccourci)
└── --version
```

> **Note —** `template` (lecture) et `theme set` en raccourcis racine
> sont **retirés** (DECISION-CLI.md §3). `series template` n'existe plus
> (lecture abandonnée). `theme set` reste sous `series theme set`
> uniquement — le nœud `theme` ne touche jamais à une série.

### 4.4 Pourquoi `series theme` n'a pas de raccourci

`series theme [dir]` (lecture du thème effectif d'une série) est
ambiguë avec le nœud `theme` du catalogue :

```
lightwebpres theme          → ??? catalogue ou série ?
lightwebpres theme .         → le slug "." ou le répertoire "." ?
```

C'est exactement l'ambiguïté de l'ancien `theme-info` qu'on voulait
résoudre. Cette commande-là reste sous `series` :

```
lightwebpres series theme [dir]         ← lecture, pas de raccourci
lightwebpres series theme set [dir] X   ← modification, pas de raccourci (DECISION §3)
lightwebpres theme list                 ← catalogue (pas de conflit)
lightwebpres theme show <slug>          ← catalogue (pas de conflit)
lightwebpres theme gallery              ← catalogue (pas de conflit)
```

> **Note —** `theme set` en raccourci racine était dans la proposition
> initiale. Il est **retiré** (DECISION-CLI.md §3) : le nœud `theme`
> ne touche jamais à une série. La forme canonique
> `lightwebpres series theme set [dir] --theme X` est la seule.

### 4.5 Règle de placement des raccourcis

La forme canonique est toujours sous l'objet. Le raccourci racine est
un confort, décidé *après* — jamais un critère de placement. Une
nouvelle commande `publish` va sous `series publish`, et on décide
ensuite si un raccourci `publish` vaut le coup.

**Règle d'extension :** si un jour un nouvel objet apparaît (par exemple
`plugin`), il s'ajoute comme nouveau nœud sans casser les raccourcis
existants. La structure interne en nœuds est la garantie que l'arbre
reste propre même si le nombre de familles augmente.

### 4.6 Le vocabulaire fermé des verbes

| Verbe | Sens | Exemples |
|---|---|---|
| `init` | créer la structure initiale | `series init` |
| `demo` | générer un exemple | `series demo` |
| `build` | générer la sortie | `series build` |
| `verify` | vérifier sans modifier | `series verify` |
| `audit` | avertir sans bloquer | `series audit` |
| `status` | décrire l'état | `series status` |
| `watch` | surveiller et servir | `series watch` |
| `clean` | purger les orphelins | `series clean` |
| `list` | énumérer | `theme list` |
| `show` | décrire un élément | `theme show` |
| `set` | modifier une valeur | `theme set` |
| `gallery` | générer une galerie | `theme gallery` |
| `update` | mettre à jour des fichiers | `series template update` |
| `resolve` | déterminer une valeur effective | `series resolve` |

Ce vocabulaire est **fermé** : toute nouvelle commande doit utiliser un
de ces verbes, jamais en inventer un nouveau.

### 4.7 Table de correspondance

| Actuel | Canonique | Raccourci | Justification |
|---|---|---|---|
| `install` | `series init` | `init` | `init` = créer la structure d'un projet (comme `git init`) |
| `demo` | `series demo` | `demo` | inchangé, groupé |
| `build` | `series build` | `build` | le plus fréquent |
| `check` | `series verify` | `verify` | `verify` dit ce qu'il fait |
| `audit` | `series audit` | `audit` | conservé (voir §3.8) |
| `refresh-templates` | `series template update` | `template update` | plus court, groupé |
| `themes` | `theme list` | — | verbe `list` |
| `theme-info <slug>` | `theme show <slug>` | — | verbe `show` |
| `theme-info [dir]` | `series theme [dir]` | — | relocalisé sous `series` |
| `set-theme` | `series theme set` | `theme set` | verbe `set` |
| `themes-gallery` | `theme gallery` | — | verbe `gallery` |
| `series-info` | `series status` | `status` | verbe `status` |
| `resolve` | `series resolve` | `resolve` | inchangé, raccourci |
| `--help` | `--help` | — | inchangé |

---

## 5. Détail des commandes

### 5.1 `series init` (ex-`install`)

```bash
lightwebpres series init [dir] [--lang fr] [--theme X] [--gitlab-ci] [--force]
lightwebpres init [dir]                              # raccourci
```

`--force` est conservé : procède même si le répertoire cible n'est pas
vide (§11.1).

Identique à `install` actuel. Le mot `init` est choisi parce qu'on
**initialise** un projet, on n'installe pas un logiciel. C'est aussi le
mot de `git init`, familier.

### 5.2 `series demo`

```bash
lightwebpres series demo [dir] [--lang fr] [--output public/]
lightwebpres demo [dir]                               # raccourci
```

Inchangé, groupé.

### 5.3 `series build`

```bash
lightwebpres series build [dir] [--lang fr] [--output public/]
    [--language-file chemin] [--no-typography] [--include-drafts]
    [--only page] [--nav-cache chemin]
    [--build-stamp | --build-stamp-minimal]
lightwebpres build [dir]                               # raccourci
```

Inchangé, groupé.

### 5.4 `series verify` (ex-`check`)

```bash
lightwebpres series verify [dir] [--lang fr] [--output public/]
    [--language-file chemin] [--no-typography] [--include-drafts]
lightwebpres verify [dir]                             # raccourci
```

`verify` dit exactement ce qu'il fait : vérifier que le build est à jour
avec les sources. C'est le terme du CI/CD (« verify stage »).

### 5.5 `series audit`

```bash
lightwebpres series audit [dir] [--lang fr]
lightwebpres audit [dir]                               # raccourci
```

Conservé. `audit` vérifie des conventions éditoriales non bloquantes
(pas de cover, pas de description, scaffold désynchronisé). C'est de
l'édition, pas du code — `lint` aurait été un mauvais import.

### 5.6 `series status` (ex-`series-info`)

```bash
lightwebpres series status [dir] [--format text|json]
lightwebpres status [dir]                              # raccourci
```

`status` est plus court et plus naturel : on demande « quel est l'état
de ma série ? ».

### 5.7 `series watch` (NOUVEAU)

```bash
lightwebpres series watch [dir] [--lang fr] [--output public/]
    [--port 8000] [--serve] [--open]
lightwebpres watch [dir]                               # raccourci
```

**Nouvelle commande.** Surveille les fichiers sources (`articles/*.md`,
`series.json`, `templates/settings.conf`, `templates/custom.css`) et
reconstruit automatiquement à chaque modification. Pensé pour l'édition
répétée : on édite, on regarde le navigateur, on édite encore.

> **Note —** La proposition initiale avait `--no-serve` (opt-out, serveur
> inclus par défaut). DECISION-CLI.md §3 **inverse** la sémantique :
> `--serve` est opt-in. Sans l'option, `watch` reconstruit seulement.

- `--serve` : active le serveur HTTP local. Les pages construites sont
  servies sur `http://127.0.0.1:8000/` (écoute sur `127.0.0.1`
  uniquement, jamais `0.0.0.0`). Sans l'option, `watch` surveille et
  reconstruit sans servir (utile si on a déjà un serveur, ou en CI).
- `--port N` : port du serveur HTTP local (défaut 8000).
- `--open` : ouvre le navigateur au démarrage (`webbrowser.open()`,
  déjà utilisé dans le code — pas de `subprocess`).
- **Implémentation stdlib :** `watchdog` n'est pas stdlib, mais une
  boucle de polling simple (`os.stat` sur les mtimes, toutes les ~0,5 s)
  l'est. `http.server` est stdlib. C'est suffisant pour un outil d'édition.
- **Comportement :** reconstruit la série entière à chaque changement,
  ou seulement l'article modifié si `--only` est passé. Affiche
  `[INFO] rebuilt in X ms` à chaque passe.
- **Code de sortie :** tourne indéfiniment ; `Ctrl-C` (SIGINT) sort avec
  le code 0.

### 5.8 `series clean` (NOUVEAU)

```bash
lightwebpres series clean [dir] [--dry-run] [--force]
lightwebpres clean [dir]                               # raccourci
```

> **Note —** DECISION-CLI.md §3 change la sémantique : `clean` est en
> `--dry-run` **par défaut** (affiche ce qui serait supprimé sans rien
> écrire). `--force` supprime réellement. L'option globale `--dry-run`
> reste applicable (redondante avec le défaut, mais cohérente).

**Nouvelle commande.** Purge `public/` des fichiers qui ne sont plus
produits par le build (pages d'articles retirés, images supprimées).

- **Sécurité :** ne supprime que ce que `build` a lui-même produit
  (fichiers `.html` d'articles, `index.html`, `README.md`, `img/`),
  via un manifeste `.lwp-manifest.json` écrit par `build` dans `public/`.
  Jamais un fichier que l'auteur a mis à la main dans `public/`. Sans
  manifeste, `clean` refuse (exit 1 avec message).
- **Relation avec `build` :** `--clean` sur `build` était un raccourci
  équivalent à `series clean && series build`. Il est **abandonné**
  (DECISION-CLI.md §3) : cacher une suppression dans une commande de
  construction est le pire endroit pour la cacher. Utiliser
  `series clean && series build` explicitement.

### 5.9 `series resolve` (ex-`resolve`)

```bash
lightwebpres series resolve [dir] <name> [--article fichier] [--format text|json]
lightwebpres resolve [dir] <name]                       # raccourci
```

Inchangé. C'est la commande la plus aboutie du CLI actuel. On ne la
touche pas, on la relocalise sous `series` avec un raccourci racine.

### 5.10 `series theme` (ex-`theme-info [dir]`)

```bash
lightwebpres series theme [dir] [--format text|json]
```

**Nouvelle localisation.** Lit le thème **effectif** d'une série — sa
palette, ses fonts, ses facets, et le niveau de contraste WCAG qu'il
atteint réellement, après les valeurs épinglées dans
`templates/settings.conf`. C'est l'ancien `theme-info [dir]`,
relocalisé sous `series` pour résoudre l'ambiguïté avec le catalogue.

Pas de raccourci racine — `theme` seul est ambigu avec le nœud
`theme` du catalogue.

### 5.11 `series theme set` (ex-`set-theme`)

```bash
lightwebpres series theme set [dir] --theme X
```

Change le thème d'une série existante.

> **Note —** La proposition initiale renommait `--theme` en `--name` et
> offrait un raccourci racine `theme set`. DECISION-CLI.md §2 **rejette
> `--name`** : la même valeur porte `--theme` partout dans le CLI
> (`install --theme`, `theme set --theme`) pour la cohérence.
> DECISION-CLI.md §3 **retire le raccourci racine** : le nœud `theme`
> ne touche jamais à une série. La forme canonique
> `lightwebpres series theme set [dir] --theme X` est la seule.

### 5.12 `series template` (lecture) — ABANDONNÉ

> **Abandonné** (DECISION-CLI.md §3). Remplacé par un filtre
> `--templates` sur `audit` : deux commandes qui répondent partiellement
> à la même question sont deux endroits à tenir synchronisés. La
> commande de lecture dédiée est retirée. Voir §5.13 pour
> `series template update` (conservé).

### 5.13 `series template update` (ex-`refresh-templates`)

```bash
lightwebpres series template update [dir] [--scaffold]
lightwebpres template update [dir] [--scaffold]        # raccourci
```

Met à jour ce qui, dans `templates/`, appartient à l'outil (`nav.js`,
et création des fichiers manquants). `--scaffold` régénère la surface
commentée de `settings.conf` aux valeurs du thème courant, en
conservant les lignes épinglées.

### 5.14 `theme list` (ex-`themes`)

```bash
lightwebpres theme list [--polarity light|dark] [--intensity sober|vivid|mono] [--hue teinte]
```

Liste les thèmes intégrés depuis le terminal. Inchangé, groupé sous
`theme`. C'est la commande de **découverte** par facettes.

### 5.15 `theme show` (ex-`theme-info <slug>`)

```bash
lightwebpres theme show <slug> [<slug>…] [--format text|json]
lightwebpres theme show --all [--format text|json]
```

Décrit **un ou plusieurs** thèmes intégrés sans rien installer : palette,
fonts, facets, et niveau de contraste WCAG mesuré. C'est la commande de
**comparaison**.

- Un slug : décrit ce thème.
- Plusieurs slugs : décrit chacun, dans l'ordre donné.
- `--all` : décrit tous les thèmes intégrés (équivalent à lister tous
  les slugs).
- Slugs inconnus : erreur fatale qui liste les slugs valides.

**Ne prend plus de répertoire** — le thème effectif d'une série est
`series theme [dir]` (§5.10). L'ambiguïté de l'ancien `theme-info` est
résolue.

### 5.16 `theme gallery` (ex-`themes-gallery`)

```bash
lightwebpres theme gallery [--output chemin] [<slug>…]
lightwebpres theme gallery --all [--output chemin]
```

Génère une page HTML autonome documentant chaque thème — un thème par
ligne, quatre panneaux en colonnes. C'est la commande de **rendu
visuel**.

- Sans argument : tous les thèmes (comportement actuel).
- Un ou plusieurs slugs : ne génère la galerie que pour ces thèmes.
- `--all` : tous (explicite, équivalent au défaut).
- `--output chemin` : chemin de sortie (défaut `themes-gallery.html`).
  Le chemin passe en option pour libérer les positionnels pour les slugs.
- Slugs inconnus : erreur fatale qui liste les slugs valides.

**Les facettes ne sont pas sur `theme gallery`.** Les filtres par
caractéristique (polarité, intensité, teinte) restent sur `theme list`,
qui est la commande de découverte. La galerie se sélectionne par **nom**,
pas par facette — on génère un sous-ensemble intentionnel, pas un filtre
dynamique. Les filtres côté client de la galerie restent intacts dans
le fichier généré.

### 5.17 `--version` (NOUVEAU)

```bash
lightwebpres --version
# LightWebPres v0.24.0
```

Affiche le numéro de version et sort. Actuellement, la version n'est
visible que dans l'en-tête de `--help`. C'est une option standard que
tout outil en ligne de commande devrait avoir.

---

## 6. Options globales

### 6.1 Le problème

`--lang` est répété sur 5 commandes (`install`, `demo`, `build`, `check`,
`audit`). C'est une préférence globale qui devrait pouvoir se placer une
fois.

### 6.2 Proposition

On autorise les options **globales** avant la commande, comme dans `git` :

```bash
lightwebpres --lang en build my-series
lightwebpres --lang en init my-series
```

Les options globales sont (DECISION-CLI.md §2) : `--lang`, `--quiet`,
`--verbose`, `--no-color`, `--dry-run`, `--timestamp`, `--version`,
`--help`. Elles peuvent aussi rester placées après la commande
(compatibilité).

> **Note —** La proposition initiale listait aussi `--output` et
> `--format` comme globales. DECISION-CLI.md §2 les **rejette** :
> `--output` désigne un répertoire pour build/demo/verify/watch et un
> chemin de fichier pour `theme gallery` — une option, deux types,
> l'ambiguïté que la refonte voulait tuer. `--format` ne concerne que
> 4 commandes sur 17. Les deux restent spécifiques à leurs commandes.
> `--no-color`, `--dry-run`, `--timestamp` (ajoutées par DECISION) sont
> ajoutées à la liste finale des 8 globales.

**Règle de précédence** (du plus fort au plus faible) :
1. option globale avant la commande
2. option après la commande
3. variable d'environnement `LWP_*`
4. défaut

### 6.3 `--quiet` / `--verbose` (NOUVEAU)

```bash
lightwebpres --quiet build my-series
lightwebpres --verbose build my-series
```

- `--quiet` : ne produit aucune sortie sur stdout, sauf les erreurs
  fatales sur stderr. Utile en CI.
- `--verbose` : affiche plus de détails (chaque fichier écrit, chaque
  étape). Utile pour le débogage.

### 6.4 `--dry-run` (NOUVEAU)

```bash
lightwebpres build my-series --dry-run
```

Exécute la commande sans rien écrire sur disque. Affiche ce qui *serait*
fait. C'est un mode de sécurité pour `build`, `init`, `theme set`,
`template update`, `clean`.

### 6.5 `--no-color` (NOUVEAU)

```bash
lightwebpres build my-series --no-color
```

Désactive les codes de couleur ANSI dans la sortie. Utile pour les
journaux CI et les captures.

---

## 7. Nouvelles options proposées

Au-delà du regroupement, voici des options que le programme **pourrait**
offrir et qui n'existent pas aujourd'hui.

### 7.1 `--clean` sur `series build` — ABANDONNÉ

> **Abandonné** (DECISION-CLI.md §3) : cacher une suppression dans une
> commande de construction est le pire endroit pour la cacher.
> `series clean` existe ; utiliser `series clean && series build`
> explicitement.

### 7.2 `--no-index` / `--no-readme` / `--no-nav` sur `series build` (NOUVEAU)

```bash
lightwebpres build my-series --no-index
lightwebpres build my-series --no-readme
lightwebpres build my-series --no-nav
```

- `--no-index` : ne génère pas `index.html` (pour une série d'un seul
  article, ou quand l'index est géré ailleurs).
- `--no-readme` : ne génère pas le `README.md`.
- `--no-nav` : ne génère pas les blocs de navigation inter-articles.

Ces options donnent un contrôle fin sur ce que le build produit, sans
toucher au format.

### 7.3 `--drafts-only` sur `series build` (NOUVEAU)

```bash
lightwebpres build my-series --drafts-only
```

Construit **uniquement** les articles `status: draft`, pour un aperçu
rapide des brouillons sans reconstruire toute la série. Complémentaire
de `--include-drafts` (qui construit tout, brouillons compris).

### 7.4 `--strict` sur `series audit` (NOUVEAU)

```bash
lightwebpres audit my-series --strict
```

`audit` ne bloque jamais par conception. `--strict` le fait échouer
(code de sortie non nul) dès qu'un avertissement est émis. Utile pour
imposer des conventions éditoriales en CI.

### 7.5 `--open` sur `series build` (NOUVEAU)

```bash
lightwebpres build my-series --open
```

Ouvre automatiquement le navigateur sur le résultat (`xdg-open` sur
Linux, `open` sur macOS) après le build.

### 7.6 `--slides-page-numbers on|off` sur `series build` / `series watch` (NOUVEAU, IMPLÉMENTÉ)

```bash
lightwebpres build my-series --slides-page-numbers on
```

Numéro de slide gravé en haut à droite (`<span class="slide-num">NN / NN</span>`),
**opt-in, défaut `off`**. Se compose avec la clé de front-matter
`slide_page_numbers: true|false` et la clé `series_meta.slide_page_numbers`
de `series.json` ; précédence (la plus spécifique gagne) :
front-matter article > `--slides-page-numbers` > `series_meta` > défaut
`off`. Toute valeur hors `true`/`false` (front-matter) ou `on`/`off` (CLI)
est une erreur de build fatale nommant l'origine. Distinct du compteur
live bas-gauche (`.slide-counter`, toujours affiché). Voir
`specifications.md` §3.3.5 et `DECISION-CLI.md` §`--slides-page-numbers`.

---

## 8. Grouper le vocabulaire : le tableau complet

### 8.1 Les objets

| Objet | Membres | Rôle |
|---|---|---|
| `series` | `init`, `demo`, `build`, `verify`, `audit`, `status`, `watch`, `clean`, `resolve`, `theme`, `theme set`, `template update` | tout ce qui concerne une série |
| `theme` | `list`, `show`, `gallery` | le catalogue de thèmes intégrés |

> **Note —** `template` (lecture) est retiré de `series` (abandonné,
> DECISION-CLI.md §3). `template update` reste.

### 8.2 Les verbes fermés

| Verbe | Objets qui l'utilisent |
|---|---|
| `init` | series |
| `demo` | series |
| `build` | series |
| `verify` | series |
| `audit` | series |
| `status` | series |
| `watch` | series |
| `clean` | series |
| `list` | theme |
| `show` | theme |
| `set` | series (theme set) |
| `gallery` | theme |
| `update` | series (template update) |
| `resolve` | series |

### 8.3 Les options par objet

| Option | Objets |
|---|---|
| `--lang` | globale, series |
| `--output` | series (build/demo/verify/watch), theme gallery |
| `--format` | series (theme, status, resolve), theme (show) |
| `--quiet` / `--verbose` | globale |
| `--dry-run` | globale (build, init, theme set, template update, clean) |
| `--no-color` | globale |
| `--timestamp` | globale |
| `--theme` | series init, series theme set |
| `--polarity/--intensity/--hue` | theme list |
| `--scaffold` | series template update |
| `--only`, `--nav-cache`, `--build-stamp*` | series build |
| `--include-drafts`, `--drafts-only` | series build |
| `--no-index`, `--no-readme`, `--no-nav` | series build |
| `--strict` | series audit |
| `--port`, `--serve`, `--open` | series watch |
| `--open` | series build |
| `--force` | series clean |
| `--article` | series resolve |
| `--all` | theme show, theme gallery |

> **Note —** `--name` (proposition initiale) est remplacé par `--theme`
> (DECISION-CLI.md §2). `--clean` sur `series build` (proposition
> initiale) est retiré (DECISION-CLI.md §3). `--no-serve` (opt-out) est
> inversé en `--serve` (opt-in, DECISION-CLI.md §3). `--timestamp` est
> ajouté (DECISION-CLI.md §2). `--output` et `--format` ne sont pas
> globales (DECISION-CLI.md §2).

### 8.4 Les raccourcis racine

| Raccourci | Canonique | Conflit avec `theme` ? |
|---|---|---|
| `init` | `series init` | non |
| `demo` | `series demo` | non |
| `build` | `series build` | non |
| `verify` | `series verify` | non |
| `audit` | `series audit` | non |
| `status` | `series status` | non |
| `watch` | `series watch` | non |
| `clean` | `series clean` | non |
| `resolve` | `series resolve` | non |
| `template update` | `series template update` | non |
| `series theme` | (canonique) | **oui** — pas de raccourci |
| `series theme set` | (canonique) | **oui** — pas de raccourci (DECISION §3) |

> **Note —** La proposition initiale listait 12 raccourcis (avec
> `template`, `theme set`). DECISION-CLI.md §3 retire `theme set`
> (le nœud `theme` ne touche jamais une série) et abandonne
> `series template` (lecture, §5.12) — son raccourci `template`
> disparaît. La liste finale est de **10 raccourcis**.

---

## 9. Compatibilité et transition

### 9.1 Le problème

La refonte casse les scripts existants. Le projet a une politique de
versionnage stricte (§13.9) : les noms de champs gelés ne changent qu'en
MAJOR. Les commandes CLI ne sont pas explicitement gelées, mais casser
les scripts est coûteux.

### 9.2 Proposition : alias de transition

Pendant une période de transition (au moins une version MAJOR), les
anciennes commandes restent acceptées comme **alias** :

| Ancien | Nouveau |
|---|---|
| `install` | `init` (ou `series init`) |
| `demo` | `demo` (ou `series demo`) |
| `build` | `build` (ou `series build`) |
| `check` | `verify` (ou `series verify`) |
| `audit` | `audit` (ou `series audit`) |
| `refresh-templates` | `template update` |
| `themes` | `theme list` |
| `theme-info <slug>` | `theme show <slug>` |
| `theme-info [dir]` | `series theme [dir]` |
| `set-theme` | `series theme set` (pas de raccourci racine) |
| `themes-gallery` | `theme gallery` |
| `series-info` | `status` (ou `series status`) |
| `resolve` | `resolve` (ou `series resolve`) |

Chaque alias affiche un `[WARN]` sur stderr : « `install` is deprecated,
use `init` or `series init` ». Le code de sortie reste correct.

### 9.3 Fin de transition

À la MAJOR suivante, les alias sont retirés. Les scripts ont eu une
version entière pour migrer.

---

## 10. Exemples d'usage

### 10.1 Le parcours complet

```bash
# Avant
./lightwebpres install my-series --theme evergreen
./lightwebpres demo my-series --lang en
./lightwebpres build my-series --lang en
./lightwebpres check my-series
./lightwebpres audit my-series

# Après (raccourcis)
./lightwebpres init my-series --theme evergreen
./lightwebpres demo my-series --lang en
./lightwebpres build my-series --lang en
./lightwebpres verify my-series
./lightwebpres audit my-series

# Après (forme canonique)
./lightwebpres series init my-series --theme evergreen
./lightwebpres series demo my-series --lang en
./lightwebpres series build my-series --lang en
./lightwebpres series verify my-series
./lightwebpres series audit my-series
```

### 10.2 L'édition répétée

```bash
# Avant : il faut build + ouvrir à la main, à chaque fois
./lightwebpres build my-series
xdg-open my-series/public/index.html

# Après : une seule commande, qui surveille, reconstruit et sert
./lightwebpres watch my-series --open
```

### 10.3 Le pipeline CI

```bash
# Avant
python3 lightwebpres check .
python3 lightwebpres build .

# Après
python3 lightwebpres --quiet verify .
python3 lightwebpres --quiet build .
```

### 10.4 Le choix d'un thème

```bash
# Avant
./lightwebpres themes --polarity dark --intensity sober
./lightwebpres theme-info evergreen
./lightwebpres set-theme my-series --theme evergreen

# Après
./lightwebpres theme list --polarity dark --intensity sober
./lightwebpres theme show evergreen
./lightwebpres series theme set my-series --theme evergreen
```

> **Note —** `theme set` n'a pas de raccourci racine (DECISION-CLI.md
> §3) et garde `--theme` (DECISION-CLI.md §2).

### 10.5 La comparaison de thèmes (NOUVEAU)

```bash
# Trouver par caractéristiques
./lightwebpres theme list --polarity dark --intensity sober
# → nord, graphite, tokyo-night, terminal, evergreen…

# Comparer les infos des candidats
./lightwebpres theme show nord graphite terminal --format json

# Voir les candidats rendus
./lightwebpres theme gallery nord graphite terminal --output comparison.html
```

### 10.6 Le thème effectif d'une série

```bash
# Avant (ambigu : slug ou répertoire ?)
./lightwebpres theme-info my-series

# Après (sans ambiguïté)
./lightwebpres series theme my-series
```

### 10.7 Les raccourcis vs la forme canonique

```bash
# La forme canonique (source de vérité, pour les scripts)
./lightwebpres series build my-series

# Le raccourci (même chose, pour l'usage quotidien)
./lightwebpres build my-series
```

### 10.8 Le nettoyage

```bash
# Purger les orphelins (dry-run par défaut, --force pour supprimer)
./lightwebpres clean my-series
./lightwebpres clean my-series --force

# Nettoyer puis reconstruire (deux commandes explicites)
./lightwebpres clean my-series --force && ./lightwebpres build my-series
```

> **Note —** `build --clean` (proposition initiale) est abandonné
> (DECISION-CLI.md §3). On utilise `clean && build` explicitement.

---

## 11. Ce qui ne change pas

Pour être explicite sur le périmètre :

- **Le format d'article `.md`** ne change pas.
- **`series.json`** ne change pas.
- **Le moteur de rendu** ne change pas.
- **`resolve`** ne change pas (relocalisé, mais comportement identique).
- **Les variables d'environnement `LWP_*`** ne changent pas.
- **Les codes de sortie** ne changent pas (0 = succès, non-nul = échec).
- **L'analyse stricte des options** (§2.4) est conservée : option
  inconnue = erreur fatale, `--opt=value` accepté, flag booléen qui
  n'avale jamais le positionnel suivant.
- **`audit` est conservé** — pas de renommage en `lint`.

---

## 12. Récapitulatif des nouveautés

### 12.1 Nouvelles commandes

| Commande | Rôle |
|---|---|
| `series watch` | surveille, reconstruit et sert à la volée |
| `series clean` | purge les orphelins de `public/` (dry-run par défaut, `--force` pour supprimer) |
| `series theme` | lit le thème effectif d'une série (ex-`theme-info [dir]`) |
| `--version` | affiche la version |

> **Note —** `series template` (lecture) est abandonné (DECISION §3),
> remplacé par filtre `--templates` sur `audit`.

### 12.2 Nouvelles options

| Option | Commande | Rôle |
|---|---|---|
| `--no-index` | series build | ne génère pas `index.html` |
| `--no-readme` | series build | ne génère pas `README.md` |
| `--no-nav` | series build | ne génère pas la navigation |
| `--drafts-only` | series build | construit seulement les brouillons |
| `--strict` | series audit | fait échouer sur avertissement |
| `--serve` | series watch | active le serveur HTTP (opt-in) |
| `--port` | series watch | port du serveur (défaut 8000) |
| `--open` | series watch, series build | ouvre le navigateur |
| `--slides-page-numbers` | series build, series watch | numéro de slide gravé en haut à droite (opt-in, défaut off) |
| `--quiet` / `--verbose` | globale | contrôle la verbosité |
| `--dry-run` | globale | ne rien écrire sur disque |
| `--no-color` | globale | désactive les couleurs ANSI |
| `--timestamp` | globale | préfixe RFC 3339 sur les logs |
| `--force` | series clean | supprime réellement (sinon dry-run par défaut) |
| `--templates` | series audit | filtre sur l'état des templates (remplace `series template`) |
| `--all` | theme show, theme gallery | tous les thèmes |
| slugs positionnels | theme show, theme gallery | sélection par nom |
| `--output` | theme gallery | chemin de sortie (ex-positionnel) |

### 12.3 Renommages

| Ancien | Nouveau |
|---|---|
| `install` | `init` / `series init` |
| `check` | `verify` / `series verify` |
| `refresh-templates` | `template update` / `series template update` |
| `themes` | `theme list` |
| `theme-info <slug>` | `theme show <slug>` |
| `theme-info [dir]` | `series theme [dir]` |
| `set-theme` | `series theme set` (pas de raccourci racine) |
| `themes-gallery` | `theme gallery` |
| `series-info` | `status` / `series status` |
| `--theme` (dans `set-theme`) | `--theme` (dans `series theme set`, conservé — DECISION §2) |

### 12.4 Relocalisations

| Ancien | Nouveau | Raison |
|---|---|---|
| `resolve` | `series resolve` (+ raccourci) | interroge une série |
| `set-theme` | `series theme set` (pas de raccourci) | modifie une série |
| `refresh-templates` | `series template update` (+ raccourci) | opère sur une série |

---

## 13. Questions ouvertes — toutes tranchées (DECISION-CLI.md)

1. **`--clean` vs `series clean`.** **Tranché (DECISION §3) :**
   `--clean` sur `build` est **abandonné**. `series clean` reste
   (dry-run par défaut, `--force` pour supprimer).
2. **Faut-il un `series new` distinct de `series init` ?** **Tranché
   (PLAN §7) :** rejeté, hors périmètre de cette version.
3. **Le `--name` de `theme set`.** **Tranché (DECISION §2) :** `--name`
   est **rejeté**, on garde `--theme` partout pour la cohérence.
4. **Quels raccourcis racine supplémentaires ?** **Tranché (DECISION §3) :**
   `theme set` et `template` (lecture) sont retirés. La liste finale
   est de **10 raccourcis** (voir §8.4).
5. **`theme gallery --output` vs positionnel.** **Tranché (DECISION §2) :**
   `--output` reste spécifique à `theme gallery` (chemin de fichier),
   pas globale. L'alias de transition `themes-gallery` devrait accepter
   l'ancien forme positionnelle.
6. **Gestion des articles.** **Tranché (PLAN §7) :** hors périmètre,
   nécessite son propre cahier des charges.
