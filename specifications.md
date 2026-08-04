# LightWebPres — Spécifications du framework

## 1. Objectif

LightWebPres est un framework de génération de pages web autonomes à partir de
fichiers Markdown étendus. Il produit des pages HTML contenant une suite de
fiches (slides) scrollables de différents types, optionnellement suivies d'un
texte long (qui n'est pas forcément un article sourcé — le format est né d'un
besoin de fiches documentées mais ne s'y cantonne pas), avec une navigation
inter-articles. Le résultat est un ensemble de fichiers HTML **autonomes**
(CSS inline, JS inline, aucune dépendance externe), déployables sur n'importe
quel serveur statique.

Le framework est conçu pour un public rédacteur (auteur d'une série
d'articles). Il n'y a pas de public lecteur cible : les utilisateurs
consultent le contenu produit sur mobile ou sur ordinateur, quel que soit le
sujet de la série.

Il est utilisable à la fois en édition manuelle (un humain édite les fichiers
Markdown) et en édition par LLM (un modèle de langue génère ou modifie les
fichiers Markdown puis lance le build).

### 1.1 Documents du projet

La documentation fait partie du contrat interne entre les composants du
projet, au même titre que le code. Les documents normatifs et leur rôle :

- **`specifications.md`** (ce document, français) — la spécification
  comportementale de référence ; en cas de divergence avec un autre
  document, c'est elle qui est soit appliquée, soit corrigée
  explicitement, jamais ignorée.
- **`GLOSSARY.md`** (anglais) — l'index de tous les champs `clé: valeur`
  du format : portée, chaîne de repli, rendu, et les conventions de
  nommage gelées.
- **`README.md`** (anglais) — présentation et démarrage rapide.
- **`GUIDE.md`** (anglais) — le parcours complet côté utilisateur
  (installer, écrire, vérifier, publier).
- **`agent/skills/lightwebpres/SKILL.md`** (anglais) — la référence du
  format à destination d'un agent LLM qui écrit ou modifie des articles.

Le fichier de travail `JOURNAL-1.0.md`, transitoire, ne fait **pas**
partie de ce contrat : il est supprimé du dépôt juste avant la 1.0 et
n'est jamais référencé par un document pérenne.

### 1.2 Contrat avec `lightwebpres-gui`

`lightwebpres-gui` est un **projet séparé** (dépôt distinct, hors du
périmètre de version de celui-ci) : une interface graphique qui édite des
séries et pilote des builds. Il **consomme** ce projet ; le contrat entre
les deux est explicite et unidirectionnel (le GUI suit, `lightwebpres`
est la source de vérité) :

- **Vocabulaire.** `GLOSSARY.md` est le contrat de vocabulaire partagé :
  tout champ que le GUI présente, valide ou génère porte le nom, la
  portée et la casse qui y sont figés (§2.5 des conventions de nommage).
  Le générique est « field », jamais « tag »/« balise ».
- **Format et comportement.** `specifications.md` (ce document) et
  `SKILL.md` décrivent le format et le rendu que le GUI doit produire à
  l'identique — un build lancé depuis le GUI et un build en ligne de
  commande donnent le **même** HTML (la page navigateur exécute d'ailleurs
  l'exécutable `lightwebpres` tel quel via Pyodide, §23.1).
- **Version vendorisée.** Le GUI **épingle une version exacte** de
  l'exécutable `lightwebpres` (il en vendorise une copie) et affiche
  laquelle ; il ne suit jamais une version « au fil de l'eau ». La montée
  de version est une action explicite côté GUI, vérifiée par ses propres
  tests.
- **Stabilité promise.** À partir de la 1.0, les noms de champs gelés
  (§2.5) et le format d'entrée (`series.json`, article `.md`) sont
  stables au sens de la politique de versionnage (§13.9) : le GUI peut
  s'y fier sans qu'un patch les casse.

Réciproquement, les fonctionnalités propres au GUI (édition assistée,
chiffrement au repos, aperçu, synchronisation Git…) sont **hors** de ce
document : elles vivent dans le dépôt `lightwebpres-gui` et n'imposent
rien à l'exécutable.

---

## 2. Architecture générale

### 2.1 Exécutable unique

Le framework est un **fichier exécutable unique** (`lightwebpres`), script
Python 3 avec shebang `#!/usr/bin/env python3`. Il ne dépend d'aucune librairie
externe (Python 3 standard library uniquement). **Version minimale :
Python 3.8** — vérifiée à l'import avec un message clair (le source
lui-même reste analysable jusqu'à 3.6, précisément pour que ce contrôle
s'exécute au lieu d'une erreur incompréhensible plus tard). Sous Windows,
où le shebang ne s'applique pas, lancer `python lightwebpres <commande>` ;
les liens du README généré utilisent toujours `/` (jamais le séparateur de
l'OS), et une collision de `page_dest` insensible à la casse est une
erreur fatale partout (deux noms distincts pour une URL peuvent être le
même fichier sur un système de fichiers Windows/macOS). Il peut être installé
system-wide (`/usr/local/bin/lightwebpres`) ou utilisé localement
(`./lightwebpres`).

L'exécutable contient en interne :

1. La logique de build (parseur, convertisseur, moteur d'inclusion)
2. Les templates par défaut (CSS, JS, HTML) — écrits en string Python, extraits
   par la commande `install`
3. Les règles typographiques par défaut (`fr` et `en`) — écrites en string
   Python, extraites par la commande `install`
4. Le générateur de démo (crée des articles d'exemple)
5. Le CLI (`install`, `demo`, `build`, `check`, `audit`, `refresh-templates`,
   `themes`, `set-theme`, `themes-gallery`, `--help`)

### 2.2 Le répertoire de série

L'unité de travail est le **répertoire de série**. C'est lui qui contient tout
ce qui est particulier à une série d'articles : les sources, les templates, la
typographie, la configuration, et le output.

Structure créée par `install` :

```
ma-serie/                          # Le répertoire de la série (l'unité de travail)
├── series.json                    # La liste des articles + métadonnées de la série
├── articles/                      # Les fichiers .md des articles (un par page)
│   ├── avant_propos.md
│   ├── snapchat.md
│   ├── snapchat_article.md       # L'article de fond inclus par snapchat.md
│   ├── instagram.md
│   ├── instagram_article.md
│   └── ...
├── templates/                     # style.css et nav.js de cette série (override, §9)
│   ├── style.css                  # Le CSS (le look)
│   └── nav.js                     # Le JS de navigation
├── language/                       # Règles typographiques + vocabulaire d'interface (override)
│   ├── fr.json
│   └── en.json
├── public/                        # Le HTML généré (output du build)
│   ├── index.html
│   ├── avant_propos.html
│   ├── snapchat.html
│   └── img/                       # Images copiées depuis articles/
│       └── ...
├── README.md                      # Généré par build depuis series.json (§8.3)
├── lightwebpres                   # Copie de l'exécutable (installée par install, §11.1)
├── .gitlab-ci.yml                 # Pipeline CI (optionnel — install --gitlab-ci, §11.1)
└── .lwp-cache/nav.json            # Empreinte de navigation pour build --only (§11.3.1)
```

### 2.3 Variables d'environnement

L'exécutable utilise des variables d'environnement pour localiser les
fichiers. Toutes ont des valeurs par défaut relatives au répertoire de la
série.

| Variable              | Défaut                    | Description                          |
|-----------------------|---------------------------|--------------------------------------|
| `LWP_SERIES_DIR`      | `.` (le répertoire courant) | Le répertoire de la série           |
| `LWP_ARTICLES_DIR`    | `$LWP_SERIES_DIR/articles`  | Les fichiers `.md` des articles     |
| `LWP_TEMPLATES_DIR`   | `$LWP_SERIES_DIR/templates` | Les templates HTML/CSS/JS           |
| `LWP_LANGUAGE_DIR`    | `$LWP_SERIES_DIR/language`  | Règles typographiques + chaînes d'interface (.json) |
| `LWP_OUTPUT_DIR`      | `$LWP_SERIES_DIR/public`    | Le répertoire de sortie du build    |
| `LWP_LANG`            | `fr`                        | La langue (`fr`, `en`, ou toute autre avec un fichier `language/{lang}.json`) |

### 2.4 Options en ligne de commande

Les options en ligne de commande **override** les variables d'environnement.

```bash
lightwebpres install [répertoire] [--lang fr] [--force] [--theme nom] [--gitlab-ci]
lightwebpres demo [répertoire] [--lang fr]
lightwebpres build [répertoire] [--lang fr] [--output public/] [--language-file chemin.json] [--no-typography] [--include-drafts] [--only page] [--nav-cache chemin] [--build-stamp | --build-stamp-minimal]
lightwebpres check [répertoire] [--lang fr] [--output public/] [--language-file chemin.json] [--no-typography] [--include-drafts]
lightwebpres audit [répertoire] [--lang fr]
lightwebpres refresh-templates [répertoire]
lightwebpres themes [--polarity light|dark] [--intensity sober|vivid|mono] [--hue teinte]
lightwebpres set-theme [répertoire] --theme nom [--force]
lightwebpres themes-gallery [chemin]
lightwebpres --help
```

- `[répertoire]` : le chemin du répertoire de série (défaut : `.`, ou `$LWP_SERIES_DIR`)
- `--lang` : la langue — règles typographiques et chaînes d'interface (défaut : `fr`, ou `$LWP_LANG`)
- `--output` : le répertoire de sortie (défaut : `public/`, ou `$LWP_OUTPUT_DIR`)
- `--language-file` : fichier de langue explicite, priorité max sur toute autre source (§19.5)
- `--force` : `install` — procède même si le répertoire cible n'est pas vide ; `set-theme` — rethème un `style.css` non standard, au risque d'un résultat partiellement recoloré (§11.10)
- `--theme` : `install`/`set-theme` — applique une palette prédéfinie (§9.5)
- `--polarity` / `--intensity` / `--hue` : `themes` seulement — restreint la liste par facette (§9.5.3, §11.9)
- `--gitlab-ci` : `install` seulement — écrit aussi un `.gitlab-ci.yml` (opt-in, §11.1)
- `--no-typography` : `build`/`check` seulement — désactive entièrement le moteur de typographie pour ce lancement (§19.6)
- `--include-drafts` : `build`/`check` seulement — construit aussi les articles marqués `draft: true` (§20.6), avec bandeau « Brouillon »
- `--only` : `build` seulement — ne reconstruit qu'une page (§11.3.1)
- `--nav-cache` : `build` seulement — chemin du cache d'empreinte de navigation (§11.3.1)
- `--build-stamp` / `--build-stamp-minimal` : `build` seulement — horodatage de build dans l'en-tête des pages (§11.3.2)

Les variables d'environnement `LWP_SERIES_DIR`/`LWP_LANG`/`LWP_OUTPUT_DIR`
sont honorées par toute commande qui opère sur un répertoire de série —
`LWP_SERIES_DIR` est résolu une seule fois dans `main()`, avant l'aiguillage,
donc `install`, `demo` et `set-theme` l'honorent aussi. Seules `themes` et
`themes-gallery` y échappent : la première n'interroge que la table `THEMES`
intégrée, la seconde ne prend qu'un chemin de sortie. `themes` et `themes-gallery` ne lisent aucun répertoire de
série : la première n'interroge que la table `THEMES` intégrée, la
seconde ne prend qu'un chemin de sortie.

L'aide s'obtient par `help`, `--help` ou `-h` (les trois formes sont
équivalentes) ; sans argument du tout, l'aide s'affiche aussi. Une
commande inconnue affiche l'aide et sort avec le code 1.

**Analyse stricte des options.** Le parseur connaît, par commande, les
options acceptées et lesquelles prennent une valeur :

- Une option inconnue — faute de frappe ou option d'une autre commande
  (`build --force`) — est une **erreur fatale**, jamais un no-op
  silencieux.
- La forme GNU `--option=valeur` est acceptée, équivalente à
  `--option valeur` (la valeur peut elle-même contenir `=`).
- Une option à valeur sans valeur (`--lang` en fin de ligne) est une
  erreur fatale ; une option booléenne avec `=valeur` aussi.
- Un flag booléen n'avale jamais l'argument positionnel qui le suit :
  `build --no-typography mon-repertoire` construit bien
  `mon-repertoire`.

---

## 3. Niveaux d'objets

Le système gère trois niveaux d'objets :

### 3.1 Niveau série (le site)

La série est l'ensemble des articles. Elle est décrite par `series.json` qui
contient, pour chaque article, deux catégories de champs bien distinctes
(détail complet en §20) :

- **Structurel — toujours dans `series.json`**, aucune autre source
  possible : `page_source` (nom du fichier Markdown source, ex.
  `snapchat.md`). C'est le seul champ qu'une entrée `articles[]` doit
  réellement porter — un article est auto-décrit (§20.3.1).
- **D'affichage/éditorial — surcharge optionnelle** d'une valeur par
  défaut lue dans le bloc meta de l'article lui-même, ou à défaut
  extrapolée de son contenu ou héritée de `series_meta` (§20.3.1) :
  `page_dest` (nom du fichier HTML de sortie, déduit de `page_source` si
  absent), `page_title` (titre de la page HTML de l'article), `page_desc`
  (description de la page, `<meta name="description">`), `card_title`/
  `card_desc`/`card_label` (carte de la page d'index), `nav_title`/
  `nav_desc` (carte de navigation affichée dans la page d'un *autre*
  article), `author`/`license`/`date` (champs éditoriaux affichés,
  §20.3.1), `draft` (statut brouillon, §20.6).

Le contenu d'une fiche `cover` (tag, titre, summary) vient exclusivement des
champs de la fiche elle-même dans le `.md` (§3.3.1) — `series.json` ne porte
jamais de contenu de page, seulement les champs structurels et les
surcharges d'affichage ci-dessus.

Le fichier de série est la **source de vérité** pour l'ordre des articles,
la page d'index (page calculée), le bloc de navigation « Cette série »
inclus dans chaque article, et le README (page calculée) — mais pour les
champs d'affichage listés ci-dessus, c'est le bloc meta de chaque article
qui fait foi par défaut ; `series.json` ne sert qu'à corriger un cas
particulier sans toucher au fichier de l'article (§20.3.1).

### 3.2 Niveau article (la page)

Chaque article est décrit par un fichier Markdown étendu (ex. `snapchat.md`).
Ce fichier contient :

1. **Un bloc de métadonnées** en haut (`<!-- lwp:meta -->` ... `---`) qui porte
   les valeurs d'affichage par défaut de cet article — `series.json` ne les
   répète que pour en surcharger une (§20.3.1).
2. **Une suite de fiches** (slides) séparées par `---`.
3. **Une fiche spéciale `series-nav`** qui déclenche la génération de la
   navigation inter-articles (calculée depuis le fichier de série).
4. **Une fiche spéciale `full-article`** qui inclut un fichier Markdown
   externe (l'article de fond).

La page HTML générée contient :
- Le `<head>` avec `<meta>`, `<title>`, le CSS inline
- Les slides (fiches) en HTML
- La navigation de série (bloc calculé)
- L'article de fond (inclus et converti)
- Le JavaScript de navigation inline

### 3.3 Niveau fiche (slide)

Chaque fiche est une `<section class="slide">` dans le HTML final. Les types de
fiches sont :

#### 3.3.1 Fiche de couverture (`cover`)

```html
<section class="slide slide-cover" id="s1">
  <span class="slide-num">01 / 12</span>
  <span class="slide-tag">Recette</span>
  <h1>La tarte aux pommes</h1>
  <p class="summary">Neuf repères pour réussir une tarte aux pommes maison, de la pâte à la cuisson...</p>
</section>
```

Générée à partir des champs `tag:` et `# Titre` (`slide_title`, rendu
`<h1>` — GLOSSARY.md) de la fiche `cover` elle-même, et de son `summary:`
— ces champs vivent uniquement dans le `.md`, jamais dans `series.json`
(§3.1). Le numéro de slide est calculé
automatiquement (`01 / NN` où NN est le nombre total de slides).

#### 3.3.2 Fiche standard

```html
<section class="slide" id="s2">
  <span class="slide-num">02 / 12</span>
  <span class="slide-tag">Cuisson</span>
  <h2>La température change tout</h2>
  <p class="summary">Un four trop chaud cuit la surface avant que le centre ne soit prêt...</p>
  <div class="highlight">
    <span class="highlight-figure">180 °C</span>
    <span class="highlight-caption">température de cuisson recommandée...</span>
  </div>
  <div class="fact-box">
    <div class="fact-label">Le repère</div>
    <div class="fact-content">
      <p>Le four doit être préchauffé avant d'enfourner...</p>
    </div>
  </div>
  <p class="source">Source : Guide de pâtisserie, édition 2024.</p>
</section>
```

#### 3.3.3 Fiche de navigation de série (`series-nav`)

```html
<section class="slide" id="sN-series">
  <h2>Cette série</h2>
  <div class="series-list">
    <!-- généré depuis series.json -->
    <a href="snapchat.html" class="series-item series-link">...</a>
    <a href="instagram.html" class="series-item series-link">...</a>
    <div class="series-item series-current">...</div>
    <a href="index.html" class="series-item series-link">...</a>
  </div>
</section>
```

Générée depuis `series.json`. L'article courant est marqué `series-current`.

#### 3.3.4 Fiche d'article complet (`full-article`)

```html
<section class="slide full-article" id="sN">
  <span class="slide-num">NN / NN</span>
  <span class="slide-tag">Article complet</span>
  <!-- contenu converti depuis le fichier .md inclus -->
  <h1>Titre de l'article</h1>
  <h2>Introduction</h2>
  <p>...</p>
  <h2>Références</h2>
  <p><sup>[^1]</sup>: ...</p>
</section>
```

Le contenu est inclus depuis un fichier Markdown externe pointé par la
directive `article:` dans le Markdown étendu.

---

## 4. Format Markdown étendu

### 4.1 Syntaxe générale

Un fichier `.md` étendu mélange deux grammaires distinctes, qu'il ne faut pas
confondre : la **structure LWP** (les conventions numérotées ci-dessous) et
le **texte Markdown standard** (le contenu libre, régi par la section 6).

La structure LWP n'est reconnue que sous ces formes précises :

1. **`---`** (seul sur une ligne — les lignes vides autour sont d'usage
   mais pas exigées, voir §12.2) sépare les fiches
2. **`<!-- lwp:meta -->`** marque le début du bloc de métadonnées (avant le premier
   `---`)
3. **`<!-- lwp:slide:TYPE -->`** marque le type d'une fiche (défaut : standard)
4. **`clé: valeur`** (en tête de bloc meta ou de fiche) définit un champ

Les commentaires HTML portent le préfixe `lwp:` (et non un mot générique
comme `meta`) délibérément : un commentaire HTML est déjà invisible pour
n'importe quel outil qui se contente d'afficher le Markdown tel quel, mais
un préfixe namespacé permet en plus à un autre outil qui, lui, *lirait* ces
commentaires (générateur de statique concurrent, script de post-traitement)
de reconnaître sans ambiguïté qu'ils appartiennent à LWP et de les ignorer
explicitement, plutôt que de risquer une collision avec sa propre
convention `<!-- meta -->` ou `<!-- slide -->`.

Chaque élément LWP — instruction ou champ — tient sur **une seule ligne
physique**, quelle que soit sa longueur : il n'y a pas de valeur étalée sur
plusieurs lignes. Si un éditeur replie visuellement une ligne trop longue
(word-wrap), c'est un effet d'affichage de l'éditeur ; le fichier ne contient
toujours qu'une seule ligne logique à cet endroit.

**Le texte libre** (5. — ni `clé: valeur`, ni `<!-- -->`, ni `---`) : tout ce
qui n'est reconnu ni comme commentaire LWP ni comme champ `clé: valeur`
valide devient, à partir de cette ligne et jusqu'au `---` suivant, du texte
Markdown standard — le contenu de la fact-box, ou le corps entier d'un
fichier `*_article.md` inclus. Ce texte suit les règles Markdown ordinaires
de la section 6, notamment la fusion des lignes consécutives en paragraphes
(§6.1) : c'est l'inverse de la règle « une ligne = une valeur » qui
s'applique aux champs LWP.

**La bascule champ → texte libre est à sens unique.** Dès qu'une ligne d'une
fiche n'est pas reconnue comme un champ LWP, le parseur cesse définitivement
de chercher des champs pour le reste de la fiche (voir §22.2) : tout le
reste, y compris une ligne qui ressemblerait à un champ (`tag: ...`), est
traité comme du texte Markdown.

### 4.2 Exemple complet

```markdown
<!-- lwp:meta -->
page_title: La tarte aux pommes<br>Ce que la pâte brisée change vraiment
nav_title: La tarte aux pommes
nav_desc: Pâte brisée, cuisson et dressage
card_label: Article 1 : Les classiques
card_title: La tarte aux pommes
card_desc: Température de cuisson, temps de repos de la pâte, et astuces de dressage
---

<!-- lwp:slide:cover -->
tag: Recette
# La tarte aux pommes
summary: Neuf repères pour réussir une tarte aux pommes maison, de la pâte brisée à la cuisson, en passant par le choix des pommes et le dressage.

---

<!-- lwp:slide -->
tag: Cuisson
## La température change tout
summary: Un four trop chaud cuit la surface avant que le centre ne soit prêt : c'est le piège le plus courant de la tarte maison.
fact-label: Le repère
highlight: 180 °C
highlight-caption: température de cuisson recommandée pour une pâte brisée
source: Guide de pâtisserie, édition 2024.

Le four doit être **préchauffé** avant d'enfourner. Une chaleur tournante cuit plus uniformément qu'une chaleur statique.

Le temps de cuisson varie ensuite selon l'**épaisseur** des pommes et la hauteur du moule : ceci est un second paragraphe distinct du premier, séparé par une ligne vide.

---

<!-- lwp:slide:series-nav -->

---

<!-- lwp:slide:full-article -->
article: tarte-aux-pommes_article.md
```

Chaque champ (`summary:`, `tag:`, etc.) reste sur sa seule ligne physique,
même long — c'est la règle LWP de §4.1. En revanche, le texte libre de la
seconde fiche ci-dessus contient volontairement **deux paragraphes Markdown**
séparés par une ligne vide (« Le four doit être préchauffé... » et « Le
temps de cuisson varie... ») : c'est le cas normal d'usage, et les deux
doivent être rendus comme deux `<p>` distincts à l'intérieur du même
`<div class="fact-content">` (§6.1).

### 4.3 Champs d'une fiche standard

| Champ           | HTML généré                              | Obligatoire |
|-----------------|------------------------------------------|-------------|
| `tag`           | `<span class="slide-tag">VALEUR</span>`  | Non         |
| `## `           | `<h2>VALEUR</h2>`                        | Non         |
| `summary`        | `<p class="summary">VALEUR</p>`          | Non         |
| `fact-label`     | `<div class="fact-label">VALEUR</div>`   | Non         |
| `source`         | `<p class="source">Source : VALEUR</p>` | Non         |
| `highlight`         | `<span class="highlight-figure">VALEUR</span>` | Non     |
| `highlight-caption` | `<span class="highlight-caption">VALEUR</span>` | Non  |
| `comment`        | Aucun — jamais rendu (§4.6)               | Non         |

Le texte libre après les champs est placé dans un `<div class="fact-content">`
si un `fact-label` est présent, sinon dans un `<div class="slide-body">`.
Ce texte libre suit le convertisseur Markdown générique (§6.1) : plusieurs
paragraphes (séparés par une ligne vide), des titres (`#`/`##`/`###`), des
listes, etc. sont tous autorisés. Les titres du corps reçoivent un style
dédié **plus petit** que le grand titre de la slide (`.fact-content
h1/h2/h3` dans un fact-box, `.slide-body h1/h2/h3` sinon), pour rester
proportionnés — sans wrapper, un `#` de corps aurait la taille d'un titre
de cover, plus grosse que le `##` de la slide. Le `<div class="slide-body">`
ne porte aucune taille de police propre : un paragraphe ordinaire y rend
exactement comme avant. Un titre ouvrant directement le corps (sans
paragraphe avant) ne redéfinit pas le titre de la slide — voir §22.2 pour
la règle exacte.
Chaque champ `clé: valeur`, à l'inverse, tient toujours sur une seule ligne
physique (§4.1).

**Champ dupliqué : le dernier gagne.** Si la même clé apparaît deux fois
dans l'en-tête d'une fiche (ou d'un bloc meta), la dernière occurrence
l'emporte, sans erreur ni avertissement. C'est une **sémantique de
surcharge volontaire**, comme CSS, Make ou les fichiers INI : elle permet
d'assembler un `.md` par concaténation de fragments (un fragment de base,
puis un fragment qui surcharge certains champs) — un système de build
peut produire une fiche par couches. Les **titres** (`#`/`##`) suivent
une autre règle, qui n'est pas une incohérence : seule la première
occurrence du niveau attendu est capturée comme titre de la fiche, les
suivantes **tombent dans le contenu** (§22.2) — rien n'est perdu, alors
qu'un champ écrasé l'est ; c'est précisément pour ça que l'écrasement de
champ est défini comme une surcharge assumée.

### 4.4 Types de slides

| Marqueur                     | Type        | Description                           | Nombre par article | Position |
|------------------------------|-------------|----------------------------------------|---------------------|----------|
| `<!-- lwp:slide:cover -->`      | cover       | Slide de couverture (fond sombre)     | 0 à N (libre)       | libre    |
| `<!-- lwp:slide -->`             | standard    | Fiche standard (défaut)                | 0 à N (libre)       | libre    |
| `<!-- lwp:slide:series-nav -->` | series-nav  | Navigation de série (calculée)        | 0 ou 1              | libre    |
| `<!-- lwp:slide:full-article -->`| full-article | Article complet (include `.md`)     | 0 ou 1              | libre    |

`cover` est un **style de mise en page**, pas un marqueur structurel unique :
un article long peut tout à fait avoir plusieurs fiches `cover` pour marquer
plusieurs parties. Le moteur n'impose ni présence, ni unicité, ni position —
c'est la responsabilité éditoriale de l'auteur. De même, aucun ordre global
n'est imposé entre les types de fiches : le moteur rend les fiches
strictement dans l'ordre où elles apparaissent dans le fichier, quel que
soit cet ordre. Seules les cardinalités « 0 ou 1 » de `series-nav` et
`full-article` sont vérifiées (§22.8, §22.9) ; voir §22.13 pour le cas
`cover`.

En pratique, le corpus existant place toujours `cover` en première fiche,
puis les fiches `standard`, puis `series-nav`, puis `full-article` en
dernier — c'est une convention d'usage recommandée, pas une règle imposée
par le moteur.

### 4.5 Désactiver la typographie automatique pour un article

Le moteur de typographie (§7/§19) **modifie le contenu généré** : il insère
des espaces insécables aux endroits qu'il reconnaît (voir §7.5 pour la
liste). C'est un comportement par défaut, pas neutre, donc réversible —
trois champs du bloc `<!-- lwp:meta -->` de l'article (aucun effet ailleurs,
y compris dans `series.json`, §20.2) permettent de le retirer, en tout ou
en partie, pour cet article et sa propre page uniquement :

| Champ | Effet quand la valeur est `off` |
|-------|----------------------------------|
| `typo-units: off` | Désactive uniquement les règles nombre/unité et opérateur/nombre (`nbsp_before_unit`, `nbsp_after_operator`, §7.5) |
| `typo-thousands: off` | Désactive uniquement la règle de séparateur de milliers (`nbsp_thousands_separator`, §7.5) |
| `typo: off` | Désactive **toutes** les règles pour cet article — y compris les trois règles historiques (guillemets, ponctuation haute, %), pas seulement les deux ci-dessus |

Seule la valeur `off` (insensible à la casse) désactive une règle ; toute
autre valeur, ou l'absence du champ, la laisse active (comportement par
défaut, inchangé). `typo: off` équivaut, pour cet article seul, à lancer
tout le build avec `--no-typography` (§11.3/§19.6) : aucune règle ne
s'exécute sur sa page, pas seulement celles nommées explicitement — une
future règle ajoutée au moteur serait donc, elle aussi, couverte sans
modification de cette section.

Portée : ces trois champs n'affectent que la page de **cet** article
(titre, fiches, article complet inclus). Les fragments de cet article
réutilisés ailleurs — sa carte et sa description dans l'index, son entrée
dans le bloc « Cette série » d'un autre article — restent soumis aux règles
normales, puisqu'ils sont générés par `build_index`/`build_series_nav`, pas
par le rendu de la page de l'article lui-même.

### 4.6 Notes de relecture (`comment`)

`comment` est reconnu à chaque niveau (`series.json` — entrée d'article ou
`series_meta` —, bloc meta de l'article, en-tête d'une fiche de **tout**
type : `cover`, standard, `series-nav`, `full-article`) mais n'est
**jamais lu par aucun moteur de rendu** : le
parseur le reconnaît comme un champ valide (pas de bascule vers le texte
libre, pas d'erreur fatale sur une fiche `cover`), stocke sa valeur, puis
ne la relit jamais — elle n'atteint donc ni le HTML publié, ni même son
code source brut. C'est la différence avec un commentaire HTML
(`<!-- note -->`) placé dans du texte libre : celui-ci est préservé tel
quel par le passthrough HTML brut (§6.2) et reste donc présent — invisible
à l'écran, mais visible dans le code source de la page publiée. `comment`
n'a aucune contrainte de contenu et aucun effet sur le build ; il sert
uniquement à laisser une note de relecture (à vérifier, TODO, remarque
éditoriale) directement dans la source, sans qu'elle soit jamais publiée.

---

## 5. Inclusions

### 5.1 Inclusion de fichier Markdown (`.md`)

Dans une fiche `full-article` :

```
<!-- lwp:slide:full-article -->
article: snapchat_article.md
```

Le fichier `snapchat_article.md` est lu depuis `LWP_ARTICLES_DIR`, converti en
HTML (voir section 6), et inséré dans la slide.

### 5.2 Inclusion indirecte (référence par nom)

Au lieu de donner le contenu d'un objet directement dans le Markdown, on peut
dire au moteur que l'objet est décrit ailleurs et ne donner que le nom du
fichier. C'est ce que fait `article: snapchat_article.md` : on ne donne pas le
contenu de l'article dans le fichier source, on donne le nom du fichier qui le
contient.

Ce principe s'applique aussi au CSS, au JS de navigation et à la typographie :
ce sont des fichiers séparés, référencés par nom (§9, §7), pas inline dans
l'exécutable au moment du build.

### 5.3 Inclusion de fichiers CSS, JS

- **CSS** : lu depuis `templates/style.css` s'il existe, inséré dans `<style>` dans le `<head>`
- **JS** : lu depuis `templates/nav.js` s'il existe, inséré dans `<script>` à la fin du `<body>`
- La structure HTML elle-même n'est pas lue depuis un fichier : elle est
  fixe, intégrée à l'exécutable (§9), seuls ses placeholders sont remplacés

---

## 6. Convertisseur Markdown → HTML

### 6.1 Conventions de conversion

| Markdown          | HTML                                    |
|-------------------|-----------------------------------------|
| `# Titre`         | `<h1>Titre</h1>`                        |
| `## Titre`        | `<h2>Titre</h2>`                        |
| `### Titre`       | `<h3>Titre</h3>`                        |
| `**gras**`        | `<strong>gras</strong>`                |
| `*italique*`      | `<em>italique</em>`                    |
| `[^N]`            | `<sup>[^N]</sup>`                      |
| `[^N]: def`       | `<p><sup>[^N]</sup>: def</p>`          |
| `1. item`         | `<li>item</li>` (regroupés en `<ol>`)  |
| `- item`          | `<li>item</li>` (regroupés en `<ul>`)  |
| `| a | b |`       | `<table>` avec thead/tbody             |
| `---` (seul)      | séparateur de slides (pas de `<hr>`)  |
| `[texte](url)`    | lien — voir ci-dessous                 |
| `![alt](src)`     | image — voir ci-dessous                |
| Paragraphe        | `<p>texte</p>`                         |

**Liens.** Seules les URL **http(s)** sont converties : `[texte](url)`
devient `<a href="url" target="_blank" rel="noopener">texte</a>` — tout
lien s'ouvre dans un nouvel onglet. Un lien vers une cible relative
(`[autre](autre.html)`) reste du texte littéral : c'est voulu (les pages
générées sont autonomes et la seule cible relative légitime, une image,
a sa propre syntaxe ci-dessous). Pour un lien interne malgré tout, passer
par du HTML brut (§6.2).

**Titres.** Seuls trois niveaux existent (`#`, `##`, `###`) ; `####` et
au-delà ne sont pas reconnus et restent du texte de paragraphe littéral.

**Tableaux.** Chaque `<table>` généré porte `class="comparison-table"`
— c'est le crochet de style du CSS par défaut (et donc un point de
personnalisation documenté). La ligne séparatrice accepte les deux-points
d'alignement CommonMark (`|:---|---:|`) mais ils sont **ignorés** (aucun
alignement émis). Le nombre de cellules par ligne n'est pas validé : une
ligne plus courte ou plus longue que l'en-tête est émise telle quelle.

**Verdicts colorés dans un tableau comparatif.** Le Markdown n'a pas de
syntaxe pour qualifier une cellule, et il n'est pas prévu qu'il en ait
une : la voie **documentée** est le HTML inline (§6.2), en posant l'une
des classes que la feuille par défaut style déjà —

| Classe | Usage | Rendu par défaut |
|---|---|---|
| `yes` | le critère est rempli | `--positive`, gras |
| `no` | il ne l'est pas | `--ink-muted`, atténué |
| `partial` | partiellement | `--accent`, demi-gras |
| `col-signal` | mettre en valeur toute une colonne | fond creusé, demi-gras |
| `col-snap` | une seconde colonne à distinguer | fond creusé + filet `--marker` |

soit `<td class="yes">Oui</td>`, ou `<span class="yes">Oui</span>` à
l'intérieur d'une cellule Markdown. Les couleurs viennent de la palette,
donc un thème (§9.5) les restyle comme le reste, et
`print-color-adjust` conserve la distinction à l'impression, où la
couleur saute souvent.

Ces classes existaient dans la feuille par défaut depuis l'origine sans
être documentées **ni atteignables autrement** : `lightwebpres` livrait
donc des crochets de style que son propre format ne savait pas produire.
Deux étaient en outre inutilisables telles quelles — `yes` et `partial`
portaient des déclarations identiques (trois verdicts, deux
apparences), et `no` était le seul mis en valeur, en vert gras, à
rebours de la lecture naturelle. Corrigé, documenté, figé par test.

**Images.** `![alt](src)` **seule sur sa ligne** devient un bloc figure :
`<figure class="figure"><img src="src" alt="alt"></figure>`. Un titre
Markdown standard après le chemin — `![alt](src "Légende")` — ajoute
`<figcaption class="figure-caption">Légende</figcaption>` sous l'image ;
la légende passe par le rendu inline (gras, liens...) et par la
typographie, et le style par défaut l'affiche petite, centrée et grise
(`var(--ink-muted)`, donc adaptée à chaque thème). Une image **au milieu d'un
paragraphe** devient un simple `<img>` inline, **sans légende** : une
légende est un élément de bloc et cette image-là est au fil de la
phrase. Le titre y est malgré tout accepté et devient un attribut
`title` (une infobulle), jamais un `<figcaption>` — il n'est passé ni
par le rendu inline ni par la typographie, qui produisent l'un des
balises et l'autre des insécables, sans objet dans une valeur
d'attribut. Avant la v0.12.0, ce cas ne rendait pas du tout : le motif
inline n'acceptait pas de titre, donc `![alt](src "Titre")` au milieu
d'un paragraphe survivait tel quel dans la page (et la typographie
prenait ensuite le `!` de `![alt]` pour une ponctuation haute et
glissait une insécable devant). Dans les
deux cas la `src` peut être un chemin relatif — contrairement aux liens,
restreints à http(s) — car les images vivent dans `articles/img/`,
copié vers `public/img/` au build (§11.3). Une ligne-image n'est jamais
fusionnée dans le paragraphe qui la précède : c'est un démarreur de
bloc, comme un titre ou une liste.

**Fusion des paragraphes.** Un paragraphe peut être écrit sur plusieurs
lignes physiques consécutives : tant qu'aucune ligne vide ne les sépare, ces
lignes appartiennent au même paragraphe et doivent être fusionnées en un
seul `<p>` (le saut de ligne interne devient un simple espace). Seule une
ligne réellement vide fait démarrer un nouveau paragraphe. C'est le
comportement Markdown standard (CommonMark), et c'est ce qui permet à un
paragraphe d'être replié visuellement dans un éditeur (word-wrap) sans que
ça change le rendu final — voir §4.1 pour la distinction avec les champs
LWP, qui eux ne tolèrent pas de continuation.

### 6.2 HTML inline autorisé

Le Markdown peut contenir du HTML inline directement (`<strong>`,
`<br>`, `<a>`, `<sup>`, etc.). Ce HTML est préservé tel quel dans la
conversion.

Une ligne qui **commence** par une balise détermine son propre
traitement : si la balise est de bloc (`<div>`, `<table>`, `<figure>`,
`<section>`...), la ligne est passée telle quelle sans passer par la
fusion de paragraphes (§6.1) — c'est un bloc HTML autonome. Si la balise
est de type inline (`<strong>`, `<em>`, `<a>`, `<sup>`, `<span>`, `<code>`,
etc.), la ligne reste un paragraphe Markdown ordinaire (fusion avec les
lignes suivantes comprise) : une phrase qui commence par un mot en gras
(`<strong>Mot</strong> commence la phrase.`) n'est pas traitée
différemment d'une phrase qui commence par du texte normal.

**Esperluettes et entités.** Dans le texte Markdown ordinaire, tout `&`
est échappé en `&amp;` — une entité HTML écrite à la main (`&rarr;`,
`&nbsp;`...) y est donc neutralisée et s'affiche littéralement
(`&rarr;`). Pour utiliser une entité, il faut être dans un **bloc** HTML
brut (ligne commençant par une balise de bloc, ou bloc multi-lignes
ouvert par une balise non refermée), où les lignes passent verbatim.
Dans une ligne-paragraphe ordinaire, écrire le caractère Unicode
directement (`→`, ` `) — tout le pipeline est UTF-8 natif (§13.1).

### 6.3 Citations et code

| Markdown                 | HTML                                                |
|---------------------------|------------------------------------------------------|
| `> texte`                 | `<blockquote><p>texte</p></blockquote>`               |
| `` `code` ``               | `<code>code</code>`                                   |
| ` ``` ` ... ` ``` `          | `<pre><code>...</code></pre>`                         |
| ` ```lang ` ... ` ``` `      | `<pre><code class="language-lang">...</code></pre>`   |

**Citation (`>`).** Une ligne commençant par `>` en tout début de ligne
(sans indentation tolérée, comme le reste de ce convertisseur) ouvre une
citation ; les lignes `>` consécutives suivantes fusionnent dans le même
paragraphe, exactement comme la fusion de paragraphes ordinaire (§6.1).
Une ligne qui n'est pas préfixée par `>` (y compris une ligne vide) ferme
la citation. Une seule citation d'un seul paragraphe à la fois : les
citations multi-paragraphes ou imbriquées ne sont volontairement pas
supportées (§15) — un besoin réel les justifierait, mais rien ne l'a
motivé jusqu'ici.

**Code inline (`` ` ``).** Une paire de backticks délimite un span de
code sur la même ligne. Contrairement au reste du convertisseur — qui ne
touche jamais `<`/`>`, précisément pour laisser passer le HTML brut
(§6.2) —, le contenu entre deux backticks EST échappé (`<`, `>`, `&`) :
c'est le seul endroit du moteur où du texte devient toujours visible tel
quel, jamais interprété comme du HTML, y compris si l'auteur y écrit
littéralement une balise. Le contenu d'un span de code n'est jamais
retraité par les autres règles inline (gras, italique, lien) : `` `**pas
en gras**` `` reste littéral.

**Bloc de code (` ``` `).** Une ligne composée uniquement de trois
backticks ouvre un bloc de code ; une ligne identique le referme. Un nom
de langage optionnel peut suivre directement les trois backticks
d'ouverture, sans espace (` ```python `), et devient
`class="language-python"` sur la balise `<code>` — purement informatif,
aucune coloration syntaxique n'est appliquée par le moteur. Entre les
deux délimiteurs, chaque ligne est reproduite verbatim (échappée, jamais
interprétée comme Markdown) — y compris une ligne vide ou une ligne de
tirets qui, ailleurs, aurait un sens structurel. Un bloc ouvert sans être
refermé avant la fin du fichier produit une balise non refermée dans le
HTML généré, détectée comme n'importe quelle autre erreur de structure
par la vérification de balisage qui précède l'écriture de chaque page
(§13) — le build échoue au lieu de publier une page tronquée.

**Protection contre la typographie automatique.** Le contenu d'un span
ou d'un bloc de code ne doit jamais voir son espacement altéré par les
règles de typographie automatique (§7) — une espace insécable insérée
silencieusement dans une commande ou une URL citée en exemple casserait
l'exemple. Le moteur de typographie (`TypoEngine`, §19.3), qui protège
déjà la syntaxe des balises HTML elle-même en scindant le texte sur les
balises, étend cette protection au *contenu* de `<code>`/`<pre>` : les
segments de texte compris entre une balise ouvrante et sa fermante parmi
ces deux noms ne reçoivent aucune règle, quelle que soit leur imbrication.
Une citation (`<blockquote>`), à l'inverse, reste du texte ordinaire et
continue de recevoir la typographie automatique normalement — c'est une
vraie citation en prose, pas un extrait technique à préserver au
caractère près.

**Échappement.** Un `\` immédiatement avant un `>` en tout début de
ligne, ou avant une ligne de trois backticks isolée, rend ce délimiteur
littéral (le backslash est retiré, le caractère qui suit s'affiche tel
quel) plutôt que d'ouvrir une citation ou un bloc de code — c'est le
seul mécanisme d'échappement que ce convertisseur reconnaît, ciblé
précisément sur ces deux nouveaux délimiteurs, pas un échappement
générique façon CommonMark pour toute la ponctuation. Un backtick isolé
ailleurs dans le texte, précédé d'un `\`, s'affiche de la même façon
sans ouvrir de span de code. Un `>` ou un backtick qui n'est de toute
façon pas en position de déclencher l'une de ces deux constructions (un
`>` au milieu d'une phrase, par exemple) n'a jamais eu besoin d'être
échappé et continue de s'afficher tel quel sans backslash. Précision :
la séquence `\>` (comme `` \` ``) est nettoyée **où qu'elle apparaisse**
dans la ligne — le backslash est retiré, le caractère reste — pas
seulement en début de ligne ; un `\>` écrit au milieu d'une phrase rend
donc `>` et non `\>`.

### 6.4 Espacement et indentation

Le convertisseur **ne tolère aucune indentation** (cohérent avec §6.3) :
les espaces et tabulations de fin de ligne sont supprimés, mais ceux de
**début** de ligne sont préservés — une ligne `  # Titre` ou `  - item`
indentée n'est ni un titre ni une liste, c'est un paragraphe ordinaire.
Une ligne vide sépare deux paragraphes ; des lignes de texte consécutives
sans ligne vide entre elles sont fusionnées dans le même paragraphe
(voir §6.1).

---

## 7. Langue (typographie et interface)

Un **fichier de langue** (`language/{lang}.json`) regroupe tout ce qui dépend
de la langue choisie (`--lang`) : les règles typographiques (§7.2) et le
vocabulaire de l'interface (§7.3) — plutôt que deux mécanismes séparés, un
seul fichier par langue.

### 7.1 Fichier de langue

Les fichiers de langue sont des fichiers JSON séparés, un par langue.
L'exécutable contient par défaut les packs pour le français (`fr`) et
l'anglais (`en`) — l'anglais sert aussi de **repli ultime** pour toute
langue demandée via `--lang` qui n'a ni pack intégré ni fichier
`language/{lang}.json`.

Fichier `language/fr.json` (exemple) :

```json
{
  "lang": "fr",
  "name": "Français",
  "rules": [
    {
      "name": "insécable_avant_ponctuation_double",
      "pattern": "([\\s])([;:!?])",
      "replacement": "\\u00a0\\2",
      "description": "Espace insécable avant ; : ! ?"
    },
    {
      "name": "insécable_dans_guillemets",
      "pattern": "«\\s+",
      "replacement": "«\\u00a0",
      "description": "Espace insécable après «"
    },
    {
      "name": "insécable_dans_guillemets_fin",
      "pattern": "\\s+»",
      "replacement": "\\u00a0»",
      "description": "Espace insécable avant »"
    },
    {
      "name": "insécable_devant_pourcent",
      "pattern": "([0-9])(\\s)(%)",
      "replacement": "\\1\\u00a0\\3",
      "description": "Espace insécable entre le nombre et le %"
    }
  ],
  "strings": {
    "nav_prev": "Planche précédente",
    "nav_home": "Retour à l'index (touche Home)",
    "nav_next": "Planche suivante"
  }
}
```

### 7.2 Règles typographiques

Les règles (`rules`) sont appliquées **au build** sur tout le contenu textuel
généré (titres, summaries, fact-boxes, articles complets, sources). Elles
sont appliquées après la conversion Markdown → HTML.

**Frontière de confiance.** `pattern` est compilé tel quel par le moteur
d'expressions régulières Python (`re`), qui n'a pas de protection contre le
temps d'exécution catastrophique d'un motif pathologique (ReDoS). Un fichier
de langue (`language/*.json` ou `--language-file`) est donc une donnée
**de confiance**, du même niveau que le code de l'exécutable lui-même ou
qu'un fichier de configuration qu'on merge dans son propre dépôt — pas une
donnée à traiter comme du contenu arbitraire non fiable. Une revue de code
normale sur un `pattern` proposé dans une merge request suffit à écarter ce
risque ; il n'y a pas de garde-fou automatique côté moteur.

### 7.3 Chaînes d'interface (strings)

Le bloc `strings` fournit le vocabulaire fixe utilisé par les templates par
défaut — infobulles de navigation, bouton de partage, libellés de la
navigation de série, etc. Chaque valeur est injectée dans les templates via
un placeholder `{{str_CLÉ}}` (§9, §18).

| Clé                        | Usage                                              |
|-----------------------------|----------------------------------------------------|
| `nav_prev`                  | Infobulle du bouton « planche précédente »          |
| `nav_home`                  | Infobulle du bouton retour à l'index (page article) |
| `nav_next`                  | Infobulle du bouton « planche suivante »            |
| `nav_dot_fallback`          | Préfixe du point de navigation sans titre (« Fiche 3 ») |
| `index_nav_up`               | Infobulle « remonter » (page d'index)               |
| `index_nav_home`             | Infobulle « haut de page » (page d'index)           |
| `index_nav_down`             | Infobulle « descendre » (page d'index)              |
| `series_nav_title`           | Titre de la fiche `series-nav` (« Cette série »)     |
| `series_read`                | Texte du lien vers un article (nav de série + carte d'index) |
| `series_current_status`      | Statut de l'article courant dans la nav de série     |
| `series_back_to_index`       | Texte du lien de retour à l'index (nav de série)     |
| `series_untitled_fallback`   | Titre de secours si `series_meta.title` est absent   |
| `draft_banner`               | Texte du bandeau brouillon (`--include-drafts`, §11.3/§20.6) |
| `full_article_tag`           | Étiquette de la fiche `full-article`                |
| `source_label`               | Préfixe avant la valeur de `source`                  |
| `copy_link`                  | Libellé de la ligne « copier le lien » de la matrice de partage |
| `copy_link_done`             | Retour visuel transitoire après une copie            |
| `copy_prompt`                | Texte du repli `prompt()` (navigateurs sans presse-papiers) |
| `share_button`               | Infobulle du bouton de partage (page article)        |
| `share_button_aria`          | `aria-label` du bouton de partage                    |
| `share_action_qr`            | Libellé de la ligne « afficher le QR code » de la matrice de partage |
| `share_scope_series`         | En-tête de colonne « Série » de la matrice de partage |
| `share_scope_article`        | En-tête de colonne « Article » de la matrice de partage |
| `share_scope_fiche`          | En-tête de colonne « Fiche » de la matrice de partage |
| `qr_modal_title`             | Titre de la fenêtre modale affichant le QR code      |
| `qr_modal_close`             | Texte du bouton de fermeture de la fenêtre modale QR |

### 7.4 Override et repli

L'utilisateur peut créer `language/fr.json`, `language/en.json`, ou tout
autre `language/{lang}.json`, dans son répertoire de série pour override le
pack par défaut. Le comportement diffère entre les deux blocs :

- **`rules`** : remplacement total. Si le fichier existe, ses `rules`
  remplacent entièrement les règles intégrées (l'ordre et les interactions
  entre règles comptent, un remplacement partiel n'aurait pas de sens).
- **`strings`** : repli clé par clé. Les clés absentes du fichier retombent
  sur le pack intégré de la **même langue** — un override peut ne redéfinir
  qu'une seule clé sans avoir à recopier tout le vocabulaire.
- Si `--lang` désigne une langue sans pack intégré (ni `fr` ni `en`) et sans
  fichier `language/{lang}.json`, le pack **anglais** intégré est utilisé
  comme base.

### 7.5 Règles insécables par défaut (`fr`)

Le pack `fr` intégré contient six règles, appliquées dans cet ordre
(§19.3). Les trois premières existaient déjà ; les trois dernières
insèrent une espace insécable entre un nombre et ce qui le complète —
un cas que les précédentes ne couvraient pas, car aucune d'elles ne
regarde ce qui suit un nombre :

| `name` | Avant | Après |
|--------|-------|-------|
| `nbsp_before_double_punctuation` | `Vraiment ?` | `Vraiment ?` |
| `nbsp_after_opening_quote` | `« bonjour »` | `« bonjour »` |
| `nbsp_before_percent` | `50 %` | `50 %` |
| `nbsp_thousands_separator` | `170 000 vues` | `170 000 vues` |
| `nbsp_before_unit` | `170 millions`, `20 dollars`, `5 $` | `170 millions`, `20 dollars`, `5 $` |
| `nbsp_after_operator` | `≈ 5`, `× 4` | `≈ 5`, `× 4` |

`nbsp_thousands_separator` ne fait qu'**upgrader une espace déjà présente**
entre deux groupes de 3 chiffres consécutifs — elle ne regroupe jamais un
nombre écrit sans espaces (`170000` reste `170000`) : décider si et comment
regrouper un nombre reste un choix éditorial de l'auteur, pas une
transformation automatique du moteur. Un nombre à 4 chiffres collé
(`2024`, une année typique) n'est jamais concerné, faute d'espace à
upgrader.

`nbsp_before_unit` couvre volontairement une liste courte et précise
(`million(s)`, `milliard(s)`, `dollar(s)`, `$`) plutôt qu'un mot quelconque
suivant un nombre : un mot ordinaire comme « likes » dans « 68 likes »
n'est pas une unité typographique reconnue — l'ajouter à la liste
casserait la distinction avec un nombre suivi d'un nom commun ordinaire
(« 5 personnes »). Cette liste, comme les cinq autres règles, reste
éditable dans `language/fr.json` (§7.4, §19.2) pour qui veut l'étendre.

Ces règles ne font **jamais** que remplacer une espace normale (U+0020)
déjà présente par une espace insécable (U+00A0) : elles n'insèrent ni
espace ni regroupement de chiffres qui n'existait pas dans la source, et
une espace insécable déjà présente dans la source traverse tout le
pipeline sans modification (§4.5, §7.6).

Aucune de ces six règles n'existe dans le pack `en` intégré (`"rules": []`,
§7.4) : ce sont des conventions typographiques françaises, sans équivalent
anglais codifié de la même façon.

### 7.6 Préservation d'une espace insécable déjà présente dans la source

Toute espace insécable (U+00A0) déjà tapée par l'auteur dans le Markdown
source — au milieu d'une valeur ou à son extrémité — doit atteindre le
HTML généré strictement inchangée, que la typographie automatique soit
active ou non (§4.5, §11.3). C'est une propriété structurelle du moteur,
pas seulement l'absence de règle qui la supprimerait :

- Les six règles de §7.5 ne remplacent jamais que des espaces normales
  (U+0020) — leur `pattern` ne reconnaît jamais U+00A0, donc une espace
  insécable déjà présente ne peut pas correspondre à un `pattern` et n'est
  jamais retouchée, y compris en cas d'application répétée (§19.3).
- Le découpage du Markdown (bloc meta, champs de fiche, contenu libre
  d'une fact-box, article complet inclus) ne doit rogner que les
  espaces/retours à la ligne ordinaires laissés par le découpage
  ligne-par-ligne du fichier — jamais U+00A0, qu'un `str.strip()`/
  `str.rstrip()` Python nu confondrait pourtant avec de l'espace
  ordinaire (`'\xa0'.isspace()` vaut `True`). Le moteur utilise pour cela
  un jeu de caractères de trim explicite (espace, tabulation, retours à la
  ligne) partout où une valeur d'auteur est extraite, jamais un trim par
  défaut.

---

## 8. Pages calculées

### 8.1 Page d'index

Générée depuis `series.json`. La page d'index contient :

1. Le `<head>` avec `<meta>`, `<title>`, le CSS inline
2. Un en-tête (titre de la série, sous-titre)
3. Une introduction (texte libre : `series_meta.intro` de `series.json`,
   seule source)
4. Les cartes d'articles (une par article, dans l'ordre de `series.json`)
5. Le JavaScript de navigation

Chaque carte d'article :

```html
<a href="tarte-aux-pommes.html" class="article-card">
  <div class="article-number">Article 1 : Les classiques</div>
  <div class="article-title">La tarte aux pommes</div>
  <div class="article-desc">Température de cuisson, temps de repos de la pâte, et astuces de dressage</div>
  <div class="article-cta">→ Lire l'article</div>
</a>
```

### 8.2 Navigation de série

Générée depuis `series.json`. Le bloc inclus dans chaque article :

```html
<section class="slide" id="sN-series">
  <h2>Cette série</h2>
  <div class="series-list">
    <a href="introduction.html" class="series-item series-link">
      <div class="series-title">Avant de commencer</div>
      <div class="series-desc">Le matériel et les bases communes à toutes les recettes</div>
      <div class="series-status">→ Lire l'article</div>
    </a>
    <div class="series-item series-current">
      <div class="series-title">La tarte aux pommes</div>
      <div class="series-desc">Pâte brisée, cuisson et dressage</div>
      <div class="series-status">▶ En cours de lecture</div>
    </div>
    <a href="index.html" class="series-item series-link" style="text-align: center;">
      <div class="series-title">← Retour à l'index</div>
    </a>
  </div>
</section>
```

### 8.3 README

Régénéré à chaque `build`, à la racine du **répertoire de série** (là où
vit `series.json` — pas nécessairement la racine du dépôt git si le
répertoire de série est imbriqué). Contient, dans l'ordre :

1. Le titre de la série (`series_meta.title`, ou « Article series » si absent)
2. Le sous-titre et l'intro (`series_meta.subtitle`, `series_meta.intro`),
   s'ils sont présents
3. Un titre de section fixe `## Articles` (non localisé), puis une liste
   numérotée des articles (`nav_title` — `nav_desc`, résolus comme en
   §20.3.1), chacun lié vers son fichier HTML construit (chemin relatif
   depuis le répertoire de série jusqu'à `--output`, toujours avec des
   `/` même sous Windows)

---

## 9. Templates personnalisables

La structure HTML des pages (page d'article, page d'index, bloc de
navigation de série) est **fixe** — ce n'est pas un template éditable. Ce
qui se personnalise :

- Le **vocabulaire et les libellés** de l'interface (boutons de navigation,
  matrice de partage, etc.) : via le fichier de langue, pas via du HTML —
  voir §7.
- **L'apparence** (`style.css`) et le **comportement de navigation**
  (`nav.js`) : deux des trois fichiers du répertoire `templates/` que
  `build` relit réellement s'ils existent, en remplacement des versions
  intégrées à l'exécutable.
- **Un point d'extension libre pour la page d'index** (`index_extra.html`),
  le troisième fichier — voir §9.3.

### 9.1 CSS (`style.css`)

Le CSS par défaut est le look actuel de la série. Il est éditable par
l'utilisateur ; `build` le relit depuis `templates/style.css` s'il existe,
sinon utilise la version intégrée à l'exécutable.

Le CSS par défaut expose six variables CSS qui pilotent son apparence.
`install --theme <nom>` en substitue les valeurs par une palette
prédéfinie au moment de la création du site — voir §9.5.

**Chacune porte le nom de son rôle**, dans l'ordre où un lecteur
rencontre la page :

| Variable | Rôle |
|---|---|
| `--page` | le fond de page |
| `--ink` | le texte courant ; et le fond de couverture sur un thème clair |
| `--ink-muted` | les textes secondaires : résumé, légende, source, verdict « non » |
| `--marker` | les filets et repères : filet de fact-box, tag de couverture, soulignement d'en-tête, point de nav actif, colonne mise en avant |
| `--accent` | appel de note (`sup`), verdict « partiel », flèche de chiffre-clé, contour de focus. **Pas les liens** : le corps de texte n'a aucune règle de lien, ils prennent donc le bleu par défaut du navigateur — voir BACKLOG B3 |
| `--positive` | le verdict « oui » d'un tableau comparatif (§6.1) |

Une couleur de palette **ne peut pas** porter un nom de composant, parce
qu'elle en sert plusieurs : `--marker` dessine à la fois le filet d'une
fact-box, le tag d'une couverture et le point de navigation actif. Les
variables qui, elles, appartiennent à un composant existent séparément et
gardent leur propre nom (`--cover-bg`, `--fact-strong-*`, `--surface`,
`--sunken`… — §9.5.2).

**Renommage de la v0.12.0.** Ces six variables s'appelaient auparavant
`--yellow`, `--dark`, `--grey`, `--light`, `--accent` et `--green` :
elles avaient été nommées d'après les valeurs qu'elles portaient dans le
tout premier thème. Ces noms mentaient dès qu'un thème s'en éloignait —
`--yellow` portait un brun-olive sur Pop Lemon, faute de quoi le repère
aurait été invisible sur un fond déjà jaune ; `--light` portait un
presque-noir sur tout thème sombre, pendant que `--dark` y portait la
couleur du texte. Un nom qu'il faut désapprendre pour s'en servir ne vaut
pas mieux que pas de nom.

**Aucun alias n'a été conservé.** `var(--yellow)` ne se replie donc sur
rien : la déclaration est invalide et la propriété garde sa valeur
héritée, sans que ni le navigateur ni le build ne le signalent. C'est la
commande `audit` (§11.5) qui rend la rupture audible : elle inspecte la
section personnelle de `templates/style.css` (après le marqueur de §9.4)
et nomme chaque ancienne variable encore référencée, avec son
remplaçant. La partie intégrée au-dessus du marqueur, elle, migre seule
au premier `refresh-templates` — l'y signaler enverrait un auteur éditer
un fichier qu'il ne doit pas éditer.

`themes-gallery` (§11.7) présente chaque pastille par son **rôle**
d'abord et son nom de variable ensuite : lire « yellow · #7A6A00 » sans
autre indication n'apprenait rien à personne.

Six variables supplémentaires pilotent, sur quatre axes indépendants
les uns des autres, le rendu visuel du gras Markdown (`**texte**` → `<strong>`)
**à l'intérieur d'une fact-box** (`.fact-content strong`) — le marquage
sémantique ne change pas, seule sa présentation par défaut devient
paramétrable :

- `--fact-strong-weight` (`bold` par défaut) — la graisse : `bold` ou
  `normal`.
- `--fact-strong-style` (`normal` par défaut) — l'italique : `normal` ou
  `italic`. Combinable librement avec la graisse (gras, italique,
  gras+italique, ou ni l'un ni l'autre).
- `--fact-strong-highlight` (`var(--marker)` par défaut) — le fond
  coloré façon `<mark>` (à ne pas confondre avec un `overline`, un axe
  visuel différent) : n'importe quelle couleur CSS, ou `transparent`
  pour le désactiver entièrement. Référencer une des six variables
  ci-dessus (`var(--accent)`, `var(--positive)`...) plutôt qu'une couleur
  en dur permet à une surcharge ultérieure de cette variable de continuer
  à s'appliquer.
- `--fact-strong-decoration` (`none` par défaut) — le soulignement :
  `underline` ou `none`. Quatrième axe, indépendant des trois autres :
  il renforce *à la place* d'un surlignage, ou *en plus*.
- `--fact-strong-decoration-color` (`currentColor` par défaut) — la
  couleur du trait ; `currentColor` reprend celle du texte, une
  `var(--rôle)` la détache. L'épaisseur et le décalage, eux, ne sont
  **pas** paramétrables : ils sont fixés dans la règle, parce qu'un trait
  fin collé à la ligne de base est précisément ce qui rend un texte
  souligné pénible à lire, et que ce n'est pas un choix qui mérite d'être
  offert. Attention au registre : un texte souligné, non gras et en
  `var(--accent)` se lit comme un lien.
- `--fact-strong-ink` (`var(--ink)` par défaut) — la couleur du **texte
  posé sur ce fond**. Sans elle, la règle ne posait qu'un fond, ce qui
  présupposait un texte foncé sur un marqueur vif : vrai sur un thème
  clair, faux sur un thème sombre où `--ink` porte justement la couleur
  claire du texte — rapport de contraste mesuré à 1,00, c'est-à-dire un
  surlignage invisible. Vaut `inherit` quand il n'y a pas de fond
  (`fact_highlight` valant explicitement `None` — une clé *absente*, elle,
  retombe sur le défaut du moteur, `marker`) : sans marqueur, le texte garde la couleur du
  corps.

Ces six variables se personnalisent exactement comme les six
premières : une surcharge dans `templates/style.css`, après le marqueur
de personnalisation (§9.4). Cinq d'entre elles sont aussi des clés de `THEMES` (§9.5) — un thème
prédéfini choisit donc ses propres valeurs plutôt que de se limiter aux
couleurs. `--fact-strong-ink` fait exception : elle n'est jamais déclarée
dans une entrée, elle est **dérivée** de `fact_highlight` et de
`dark_background`, précisément pour qu'un thème ne puisse pas se donner
une encre illisible sur son propre marqueur.

**Indépendantes veut dire indépendantes.** Les combinaisons ne sont pas
un menu fermé : « gras sans aucun surlignage » se dit
`--fact-strong-highlight: transparent`, et « non gras avec un
surlignage vert » se dit `--fact-strong-weight: normal` +
`--fact-strong-highlight: var(--positive)`, et « souligné et rien
d'autre » se dit `--fact-strong-decoration: underline` avec un
`--fact-strong-highlight: transparent`. Neuf combinaisons distinctes
existent d'ailleurs parmi les thèmes intégrés.

Les deux thèmes qui emploient le soulignement sont `monochrome` et
`graphite`, et ce n'est pas un choix arbitraire : ce sont les deux
palettes qui s'interdisent la teinte (« tout repose sur la clarté et la
forme »), et un soulignement est justement une forme, pas une teinte.
Elles couvrent les deux façons d'employer l'axe — `monochrome` cumule
surlignage **et** soulignement, `graphite` souligne **à la place** d'un
surlignage — sur les deux polarités de fond.

Un `--marker` fait pour servir de fond de surlignage est souvent trop
pâle pour servir de trait : mesuré à 1,23:1 contre le fond de page sur
`newsprint` et 1,49:1 sur `blueprint`. D'où le trait en `currentColor`
sur `monochrome`, et en `var(--marker)` sur `graphite` seulement parce
que ce thème est sombre, où le même gris ressort à 11,3:1.

Deux conséquences pratiques, apprises en constatant que rien ne les
disait :

- **Le fond et l'encre vont par paire.** Changer
  `--fact-strong-highlight` sans revoir `--fact-strong-ink` peut tomber
  sous le seuil de lisibilité : un vert `--positive` sous l'encre par
  défaut mesure 3,14:1 sur High Contrast et 2,14:1 sur Pop Lemon, deux
  échecs AA. La règle ne pose pas seulement un fond, elle pose aussi le
  texte — c'est exactement pourquoi `--fact-strong-ink` existe (§9.5.2).
- **Le mécanisme doit être trouvable.** Il ne l'était pas : absent de
  `--help`, absent du README, présent seulement ici. Trois choses le
  disent désormais — la section PALETTE AND EMPHASIS de `--help`, un
  bloc de commentaire avec cinq recettes prêtes à coller dans le
  `templates/style.css` généré, et la ligne « Gras en fact-box » de
  chaque carte de `themes-gallery` (§11.7).

Le bloc de recettes est placé **avant** le marqueur de personnalisation,
donc dans la partie régénérée : après le marqueur, `refresh-templates`
le concaténerait à la copie de l'auteur et le dupliquerait à chaque
passage.

### 9.2 JS (`nav.js`)

Le JavaScript de navigation gère :
- Le scroll entre slides (flèches, PageUp/PageDown)
- Les boutons prev/next/home
- Les nav-dots (points de navigation)
- La détection de la slide courante au scroll
- Le bouton de partage et sa matrice (§9.2.1)
- Le parcours clavier complet (flèches Haut/Bas) : fiche par fiche, puis
  carte par carte sur la fiche series-nav, puis défilement par
  incréments sur une fiche plus grande que l'écran (§9.2.2)

Éditable de la même façon que `style.css`, via `templates/nav.js` — un
override remplace `nav.js` **en bloc**, y compris le bouton de partage : il
n'y a pas de mécanisme pour ne remplacer qu'une partie du comportement de
navigation.

#### 9.2.1 Bouton de partage

Un bouton unique (icône) dans le cluster `.nav-buttons`, à côté de
prev/home/next — **page d'article uniquement**, absent de l'index (« Série »
y suffit à elle seule, et il n'y a ni article ni fiche courants à partager
depuis cette page). Il ouvre une pop-up flottante contenant une matrice de
6 boutons : 2 actions (copier le lien / afficher le QR code) × 3 portées
(série, article, fiche) :

|                        | Série | Article | Fiche |
|------------------------|-------|---------|-------|
| **Copier le lien**     | lien vers `index.html` | lien vers la page courante | lien vers la fiche courante (`#sN`) |
| **Afficher le QR code**| idem  | idem    | idem  |

- « Fiche » désigne la slide actuellement affichée (même détection que les
  nav-dots, §9.2). Elle n'a de sens que pour une slide standard ou
  `full-article` munie d'un ancrage propre (`id="sN"`) — pas pour la
  slide `cover` (qui se confond avec l'article lui-même) ni pour la slide
  `series-nav` (dont l'ancrage `sN-series` n'identifie pas un point de
  lecture précis). Sur ces deux cas, la colonne « Fiche » est grisée et
  désactivée, pas masquée : la matrice garde sa forme, seule l'action est
  indisponible. La décision se fait par **type** de slide (classe
  `slide-cover`), jamais par position — l'ordre des fiches étant libre
  (§4.4), une cover en plein milieu est désactivée et une fiche standard
  en première position est partageable.
- « Copier le lien » utilise le presse-papiers (`navigator.clipboard`),
  avec repli sur `prompt()` si l'API est indisponible (ou si l'écriture
  échoue). Après une copie réussie, le bouton affiche « ✓ » et son
  infobulle devient la chaîne `copy_link_done` pendant **1600 ms**,
  puis les deux reviennent à leur état initial.
- Fermetures : la touche **Échap** ferme la pop-up de partage et la
  modale QR ; un clic **hors** de la pop-up la ferme (un clic à
  l'intérieur ne la ferme pas) ; la modale QR se ferme par un clic sur
  son fond ou sur sa croix.
- « Afficher le QR code » ouvre une fenêtre modale avec le QR code en SVG
  vectoriel, généré **entièrement côté client** par un encodeur JS
  embarqué dans `nav.js` — pas d'appel à un service tiers de génération
  d'image, cohérent avec la contrainte d'autonomie du §13.4 (aucune
  dépendance réseau au runtime).

#### 9.2.2 Parcours clavier (flèches Haut/Bas)

Un appui sur une flèche avance ou recule dans un parcours naturel à
trois niveaux, chacun ne s'activant qu'une fois le niveau précédent
épuisé — jamais tous en même temps :

1. **Fiche par fiche** (comportement de base, déjà existant) —
   `goTo(current ± 1)`, avec un défilement `smooth`.
2. **Carte par carte sur la fiche series-nav** — les cartes (`.series-
   list a.series-link`, y compris le lien « retour à l'index ») reçoivent
   le focus clavier une par une, dans l'ordre du document ; un appui sur
   Entrée sur une carte focalisée saute vers l'article correspondant
   (comportement natif du navigateur sur un `<a>` focalisé, aucun code
   dédié nécessaire). Volontairement différent de Tab : Tab fonctionne
   partout et peut faire sortir la sélection de la page, alors que les
   flèches restent dans ce parcours à trois niveaux.
3. **Défilement par incréments sur une fiche plus grande que l'écran** —
   une fiche ne dépasse la hauteur de la fenêtre que par son propre
   contenu (`.slide` ne fixe qu'un `min-height: 100vh`, jamais une
   hauteur figée) ; le cas courant est un `full-article` (article
   complet inclus) suffisamment long, typiquement en fin de série, mais
   la détection ne dépend que de la hauteur réelle mesurée, jamais du
   type ou de la position de la fiche.

Ordre exact d'un appui sur Bas : s'il reste une carte non visitée sur la
fiche courante, focus sur la carte suivante ; sinon, si la fiche dépasse
l'écran et n'est pas encore défilée jusqu'en bas, défiler d'un incrément
(90 % de la hauteur de fenêtre) ; sinon, passer à la fiche suivante. Bas
est le miroir exact de Haut. Ce même mécanisme sert aussi de garde-fou
pour la détection de fiche courante au scroll (`detectCurrent`, utilisée
pour les nav-dots au scroll à la molette) : elle ne peut plus se fier à
« quelle fiche a son centre le plus proche du centre de l'écran » dès
qu'une fiche est nettement plus grande que les autres (son centre reste
alors loin de l'écran même quand on est en train de la lire) — elle
retient plutôt la fiche dont l'intervalle `[haut, bas]` contient le
milieu vertical de la fenêtre, correct quelle que soit la hauteur d'une
fiche.

**Cooldown de 150 ms entre deux pas (`STEP_COOLDOWN_MS`)** — bug réel
trouvé après coup (retour utilisateur : « ça continue d'aller vers le
bas, mais ça ne passe pas par la sélection des cartes ») : maintenir une
flèche enfoncée déclenche l'auto-répétition native du clavier, qui tire
des `keydown` bien plus vite (souvent 20-30 ms d'écart) que ce qu'un
humain peut percevoir. Sans limite, chaque répétition rappelait
`stepForward()`/`stepBackward()` immédiatement — `current` étant déjà mis
à jour de façon synchrone par l'appel précédent, la suite s'enchaînait
directement à travers toutes les cartes et jusqu'à la fiche suivante en
une fraction de seconde, avant qu'aucun état intermédiaire (une carte
focalisée) n'ait pu être vu, encore moins choisi. Corrigé par
`runStepped()`, une garde à part de `isScrolling` (qui ne protège que
l'animation de défilement de `goTo()` elle-même) : traite un pas, puis
ignore tout nouvel appel pendant 150 ms — invisible pour un appui isolé
(qui ne se répète jamais dans cette fenêtre), perceptible seulement
maintenue enfoncée, où le rythme redevient un pas à la fois au lieu de la
vitesse brute de répétition du système. Testé (`tests/keyboard_nav_e2e.cjs`,
quatrième scénario) : rafale de pressions à ~30 ms d'écart sur une série
dédiée dont la fiche series-nav n'est *pas* la dernière fiche (nécessaire
pour que « a foncé jusqu'au bout » et « le cooldown n'a laissé avancer
que partiellement » produisent des états finaux différents et donc
observables) — vérifié que le test échoue bien sans le cooldown avant
d'être validé avec.

Testé Playwright (`tests/keyboard_nav_e2e.cjs` /
`tests/test_keyboard_nav.py`) : défilement incrémental réel d'une fiche
`full-article` surchargée avant l'avancée à la fiche suivante, parcours
avant et arrière carte par carte sur une fiche series-nav (ordre exact
des cartes, la fiche courante ne change pas pendant le parcours des
cartes), épuisement des cartes sur la dernière fiche (reste en place,
focus nettoyé), saut réel vers l'article via Entrée sur une carte
focalisée, et non-régression du cooldown sous rafale de pressions.

### 9.3 Extension de la page d'index (`index_extra.html`)

La structure de la page d'index reste fixe, mais un site migré ou une
fonctionnalité maison (bouton, modale, script tiers...) peut avoir besoin
d'un point d'ancrage que `style.css`/`nav.js` ne couvrent pas (`nav.js` ne
s'applique qu'aux pages d'article, pas à l'index). Si
`templates/index_extra.html` existe, son contenu est inséré tel quel
(HTML, CSS inline, `<script>`... — aucune transformation) juste avant
`</body>` de la page d'index générée. Absent par défaut : `install` ne
crée pas ce fichier, contrairement à `style.css`/`nav.js`.

### 9.4 Mettre à jour `style.css`/`nav.js` après une mise à jour de l'exécutable

Un override (§9.1/§9.2) remplace le fichier **en bloc** : une fois
`templates/style.css` ou `templates/nav.js` créé (par `install`, ou copié à
la main), `build` ne lit plus jamais la version intégrée à l'exécutable
pour ce fichier — y compris après une mise à jour de l'exécutable qui
change le CSS/JS par défaut. Un site déjà installé reste donc figé sur
l'ancien rendu tant que ces fichiers ne sont pas rafraîchis à la main, même
si l'exécutable a évolué.

`refresh-templates` (§11.6) automatise ce rafraîchissement sans écraser une
personnalisation locale :

- **`style.css`** : le fichier installé par défaut se termine par un
  commentaire marqueur (`/* === Personnalisations locales : ... === */`).
  Tout ce que l'auteur ajoute **après** cette ligne est sa personnalisation ;
  tout ce qui précède est la partie intégrée à l'exécutable.
  `refresh-templates` retrouve ce marqueur (**première** occurrence dans le
  fichier : tout ce qui suit le premier marqueur appartient à l'auteur, y
  compris un second marqueur qu'il aurait collé dans ses propres règles.
  Chercher la dernière perdait toutes les règles situées entre les deux), reconstruit le fichier comme `CSS intégré à jour +
  marqueur + tout ce qui suivait le marqueur dans l'ancien fichier`, et
  laisse cette partie personnalisée totalement intacte.

  Le marqueur délimite la coupure par une ligne dédiée plutôt que par le
  nom d'une règle CSS reconnaissable (ex. deviner où commence le
  personnalisé en cherchant la première occurrence d'un sélecteur qu'on
  sait avoir été ajouté par l'auteur) : un sélecteur ajouté par l'auteur à
  une version de l'outil peut légitimement être repris tel quel dans le CSS
  par défaut d'une version ultérieure, ce qui rendrait cette
  reconnaissance ambiguë.

  Si le marqueur est absent (fichier antérieur à cette fonctionnalité, ou
  marqueur supprimé par erreur), `refresh-templates` ne devine pas où
  couper : il laisse le fichier inchangé, signale l'absence du marqueur
  (code de sortie non nul) et indique la ligne exacte à ajouter à la main
  avant la personnalisation existante, pour que le prochain passage puisse
  s'appuyer dessus.

- **`nav.js`** : pas de mécanisme de coupure équivalent (le JS n'est pas
  conçu pour être personnalisé par ajout en fin de fichier).
  `refresh-templates` sauvegarde l'ancien fichier en
  `templates/nav.js.bak` puis le remplace intégralement par la version
  intégrée à l'exécutable — à charge pour l'auteur de reporter à la main
  une éventuelle personnalisation depuis la sauvegarde.

Dans les deux cas, un fichier déjà identique à la version intégrée à
l'exécutable est laissé tel quel (rapporté « already up to date »), sans
réécriture inutile.

### 9.5 Thèmes de couleurs prédéfinis

Une table `THEMES`, embarquée dans l'exécutable, associe un nom court
(« slug ») à une palette complète : les six couleurs de §9.1 (`--page
--ink --ink-muted --marker --accent --positive`), plus les propriétés de
rendu du gras en fact-box (`fact_weight`/`fact_style`/`fact_highlight`/
`fact_decoration`/`fact_decoration_color`, §9.1) — un thème n'est donc pas qu'une recoloration, il peut aussi
choisir un traitement typographique différent (ex. italique sans fond
coloré plutôt que gras surligné) — plus un drapeau de polarité
(`dark_background`, §9.5.2) et une intensité déclarée (`intensity`,
§9.5.3), et enfin des métadonnées purement
éditoriales (étiquette affichable, source, remarque) qui ne servent qu'à
`themes-gallery` (§11.7) — jamais à `install --theme`. `fact_highlight`
vaut le nom d'un des six rôles de couleur ci-dessus (résolu en
`var(--rôle)`) ou `None` pour aucun fond ; `fact_weight`, `fact_style` et
`fact_highlight` sont toujours explicites dans chaque entrée, y compris
quand la valeur choisie est celle par défaut du moteur
(`bold`/`normal`/`marker`) — un choix délibéré consigné, pas un oubli.
Les deux clés de soulignement font exception : absentes, elles valent
« pas de soulignement », ce qui est le sens de « pas d'avis » pour un axe
ajouté après coup.

Les neuf premières entrées reprenaient des palettes d'éditeurs de code
connues (`nord`, `dracula`, `solarized`, `gruvbox`, `catppuccin`,
`tokyo-night`, `monokai`, `everforest`, `rose-pine`) ; le catalogue
s'est ensuite élargi à des thèmes propres au projet (`source:
'lightwebpres'`), notamment une famille à fond sombre et une famille
« pop » à fond franchement coloré. Le nombre exact d'entrées n'est pas
figé par cette spécification — c'est justement pourquoi §9.5.3 existe :
au-delà d'une trentaine de thèmes, une liste plate n'est plus un moyen
de choisir.

`THEMES` est la **seule** source de vérité pour ces couleurs : la
palette appliquée par `install --theme` et celle affichée par
`themes-gallery` viennent de la même donnée, elles ne peuvent pas diverger
l'une de l'autre par construction — contrairement au premier jet de
`themes-gallery.html` (une page écrite à la main), désormais remplacé par
un fichier généré depuis cette table (§11.7).

#### 9.5.1 Appliquer un thème à l'installation (`install --theme`)

`install [répertoire] --theme <slug>` (§11.1) substitue les vingt et une
variables du fichier `templates/style.css` généré par celles du thème
choisi — six couleurs, six propriétés de gras en fact-box (§9.1), et
neuf superpositions neutres (§9.5.2). Rien
d'autre dans le CSS par défaut n'est modifié. Le fichier obtenu se termine
toujours par le marqueur de personnalisation (§9.4), donc
`refresh-templates` continue de fonctionner normalement dessus ensuite.

Le slug appliqué est enregistré dans un second marqueur, dédié, en tout
début de fichier (juste après le commentaire d'en-tête) :

```css
/* lightwebpres-theme: nord */
```

Absent du CSS par défaut (aucun `--theme` fourni) ; toujours présent dès
qu'un thème a été appliqué — c'est ce qui permet à `refresh-templates`
(§9.5.4) de savoir quel thème réappliquer après une mise à jour de
l'exécutable, sans avoir à comparer des couleurs pour le deviner.

Un slug inconnu est une erreur fatale (code de sortie non nul), qui
liste les slugs valides.

#### 9.5.2 Polarité de fond et superpositions neutres

Les six couleurs de §9.1 ne suffisent pas à décrire une page. Entre
elles, la feuille de style a besoin de neutres : le filet sous un titre,
le fond légèrement décalé d'une carte, le creux d'un bloc de code, la
pastille ronde d'un bouton de navigation. Ces neutres ne sont pas des
gris fixes — ce sont des **superpositions translucides**, donc ils
teintent ce qui se trouve dessous et suivent la palette au lieu de la
contredire :

| Variable | Rôle |
|---|---|
| `--rule` | filet fin, séparateurs |
| `--rule-strong` | filet appuyé, bordure de carte |
| `--surface` | fond d'une carte, posé sur la page |
| `--sunken` | fond en creux (bloc de code, cellule d'en-tête) |
| `--cover-bg` | fond de la fiche de couverture |
| `--cover-fg` | texte de la couverture |
| `--cover-fg-faint` | texte secondaire de la couverture |
| `--control` | pastille d'un bouton flottant |
| `--control-soft` | même pastille, état discret |

Le **sens** de ces superpositions dépend du fond. Sur une page claire,
une surface est un voile blanc et un filet un voile noir ; sur une page
sombre c'est exactement l'inverse, et le même voile blanc transforme une
carte en bloc illisible. Un thème déclare donc `dark_background: True`
quand son `--page` n'est, de fait, pas clair, et reçoit le second des
deux jeux de valeurs — deux dictionnaires aux **clés identiques**, ce
qui permet de substituer l'un pour l'autre sans que le reste du code ait
à connaître la polarité.

Deux conséquences en découlent, toutes deux vérifiées par les tests :

- La couverture ne peut pas se contenter de `var(--ink)` comme fond. Sur
  un thème sombre cette variable porte la couleur du **texte** : l'utiliser
  en fond retournerait la couverture en panneau pâle. Le jeu sombre
  utilise un voile noir sur la page elle-même.
- Le surlignage du gras en fact-box a besoin d'une encre explicite,
  `--fact-strong-ink` (§9.1). La règle ne posait qu'un fond, ce qui
  présupposait un texte foncé sur un marqueur vif : vrai sur un thème
  clair, faux sur un thème sombre, où le rapport de contraste mesuré
  tombait à 1,00 — c'est-à-dire invisible.

Le drapeau s'appelle `dark_background` et non `dark` parce qu'à l'époque
cette seconde clé portait déjà la couleur foncée de la palette dans
chaque entrée (elle s'appelle `ink` depuis la v0.12.0, §9.1) : un drapeau ainsi nommé serait lu comme une chaîne de couleur,
donc toujours vrai, et tous les thèmes basculeraient silencieusement en
polarité sombre.

#### 9.5.3 Critères d'admission d'un thème, et facettes

**Admission.** Les neuf premières entrées citent leur origine ; celles
propres au projet (`source: 'lightwebpres'`) sont dessinées puis
**mesurées** avant d'être retenues, jamais retenues sur l'impression
qu'elles font :

- texte courant sur le fond : niveau AAA (rapport ≥ 7) ;
- textes secondaires et accents : niveau AA (≥ 4,5) ;
- filets et bordures : ≥ 3 ;
- verdicts d'un tableau comparatif (§6.1) : séparables en vision
  deutéranope et protanope — la couleur n'étant de toute façon jamais le
  seul porteur de l'information, puisque chaque verdict porte aussi son
  marqueur de forme (WCAG 1.4.1).

**Facettes.** Passé une douzaine de palettes, une galerie cesse d'être
un moyen de choisir et devient une chose à faire défiler. Trois facettes
décrivent donc chaque entrée ; `themes-gallery` (§11.7) les expose en
filtres, et la commande `themes` (§11.9) en options :

| Facette | Valeurs | Origine |
|---|---|---|
| polarity | `light`, `dark` | dérivée de `dark_background` (§9.5.2) |
| intensity | `sober`, `vivid`, `mono` | déclarée dans l'entrée ; absente, vaut `sober` — c'est le cas des neuf palettes d'éditeurs, reprises telles quelles |
| hue | `neutral`, `red`, `orange`, `yellow`, `green`, `cyan`, `blue`, `violet`, `magenta` | **calculée** à partir du fond |

Les noms de facettes et leurs valeurs sont en anglais, comme tout
identifiant que la ligne de commande accepte. La galerie est une page
française et affiche « Clair », « Sobre », « Teinte du fond » : elle
garde ses libellés d'affichage séparés des valeurs sur lesquelles elle
filtre. Une chaîne affichée et une clé ne sont pas la même chose, et les
confondre rendrait la CLI intraduisible.

Une même fonction, `theme_facets()`, alimente les deux surfaces. Un
sélecteur dans un terminal et un sélecteur dans un navigateur ne peuvent
donc pas diverger — propriété vérifiée par un test qui compare, pour
chaque combinaison, la sortie de `themes` aux attributs `data-*` des
cartes de la galerie.

L'intensité est déclarée parce que « à quel point est-ce criard » est un
jugement éditorial, pas une grandeur mesurable. La teinte, elle, est
calculée : une étiquette écrite à la main dérive dès que quelqu'un
retouche une couleur, et rien ne justifie de croire une prose plutôt que
la valeur qu'elle prétend décrire.

Le calcul se fait en **CIELAB**, pas en RVB. En RVB, une teinte est un
angle, et un crème pâle occupe le même angle qu'une orange pleine — ce
qui faisait nommer « orange » le papier de Solarized, ce qu'aucun
lecteur ne dirait. En CIELAB on dispose en plus du **chroma** : sous un
seuil (`NEUTRAL_CHROMA`), un fond se lit comme du papier ou de l'encre,
jamais comme une teinte, et la facette vaut `neutral`. Les bornes
d'angle ont été calibrées en mesurant des références connues plutôt que
de mémoire : les angles CIELAB ne sont pas ceux que l'intuition RVB
suggère — un bleu franc se situe vers 297°, pas 240°, et le cyan vers
227°.

La teinte est prise sur `--page`, c'est-à-dire **le fond de la page** :
c'est ce qu'un lecteur voit en premier, et ce qu'il désigne en disant
« un thème vert ». Sur un thème à polarité sombre, `--page` porte le
fond sombre, donc la même règle continue de s'appliquer sans cas
particulier.

Ces facettes ne changent rien au rendu : elles ne servent qu'à
présenter et à choisir. `install --theme` continue de ne connaître que
des slugs.

#### 9.5.4 Interaction avec `refresh-templates`

Avant de reconstruire la partie intégrée du fichier (§9.4),
`refresh-templates` cherche le marqueur de thème (§9.5.1) dans l'ancien
`templates/style.css` :

- Marqueur présent et slug toujours connu de `THEMES` : les variables de
  ce thème (§9.5.1) sont réappliquées au CSS par défaut à jour avant écriture —
  une mise à jour de l'exécutable ne fait donc jamais revenir
  silencieusement un site à la palette par défaut. Le marqueur de thème
  est réécrit à l'identique, pour survivre aux rafraîchissements suivants
  aussi.
- Marqueur présent mais slug disparu d'une version ultérieure de
  `THEMES` : repli sur le thème par défaut pour la partie intégrée,
  avec un avertissement (pas une erreur fatale — un nettoyage de
  catalogue de thèmes ne doit pas bloquer un build).
- Marqueur absent : comportement inchangé, thème par défaut (cas déjà
  couvert par §9.4).

---

## 10. Pipeline GitLab CI

Optionnel — `install` ne l'écrit que si `--gitlab-ci` est passé (§11.1) :
`install` seul ne présuppose jamais un déploiement GitLab, pour ne pas
rendre un projet dépendant de GitLab simplement parce qu'il a été
scaffoldé. Le `.gitlab-ci.yml` que `--gitlab-ci` crée :

```yaml
stages:
  - build

build:
  stage: build
  image: python:3.12-slim
  script:
    - python3 lightwebpres build .
  artifacts:
    paths:
      - public/
```

Le fichier `lightwebpres` est dans le dépôt, à la racine du répertoire de
série lui-même (`install` l'y copie, §11.1). Le pipeline n'a besoin que de
Python 3 (image `python:3.12-slim`), pas de `pip install`.

Rien n'empêche d'ajouter une étape `python3 lightwebpres check .` avant le
`build` : son code de sortie non nul en cas de différence (§11.4) en fait
une porte de vérification utilisable dans ce même pipeline, pour détecter
un `public/` non reconstruit avant de merge — pas fait par défaut par
`install`, à ajouter à la main si voulu.

---

## 11. Commandes de l'exécutable

### 11.1 `install`

```bash
lightwebpres install [répertoire] [--lang fr] [--theme nom] [--gitlab-ci]
```

Crée la structure de travail dans `[répertoire]` :

1. Crée le répertoire s'il n'existe pas
2. Crée les sous-répertoires : `articles/`, `templates/`, `language/`,
   `public/`
3. Extrait les templates par défaut depuis l'exécutable (§9) :
   - `templates/style.css` — avec les couleurs du thème par défaut, sauf
     si `--theme <nom>` est fourni, auquel cas les vingt et une variables
     de ce thème sont substituées (§9.5.1) ; `<nom>` inconnu de `THEMES` est une
     erreur fatale, qui liste les noms valides
   - `templates/nav.js`
4. Extrait les packs de langue par défaut depuis l'exécutable :
   - `language/fr.json`
   - `language/en.json`
5. Crée un `series.json` de départ : `series_meta` pré-rempli de
   valeurs génériques (`title`/`subtitle`/`version`/`intro`, plus
   `author`/`license` vides — présents pour faire connaître les champs,
   rien n'est rendu tant qu'ils sont vides) et un tableau `articles`
   vide
6. Crée un `.gitlab-ci.yml` de base, **mais seulement si `--gitlab-ci` est
   passé** — `install` seul ne présuppose jamais un déploiement GitLab
   (§10) ; par défaut, aucun fichier de CI n'est créé. La commande de
   build de ce fichier porte la langue choisie (`build . --lang <lang>`,
   `fr` par défaut)
7. Copie l'exécutable `lightwebpres` dans le répertoire (pour autonomie)

**`--lang` à l'install.** La langue n'est **pas** une propriété du projet
stockée quelque part : les deux packs (fr, en) sont toujours installés, et
la langue est un choix **par build** (`--lang` sur `build`/`demo`, ou
`$LWP_LANG`, `fr` par défaut — §7.1/§12.1). À l'install, `--lang` ne fait
qu'une chose : fixer la langue inscrite dans la commande de build du
`.gitlab-ci.yml` généré (donc utile surtout avec `--gitlab-ci`).

Si le répertoire existe déjà et contient déjà des fichiers, `install` refuse
et s'arrête (erreur, code de sortie non nul), sauf avec `--force` qui laisse
`install` procéder quand même. Pas d'invite interactive : l'outil est pensé
pour un usage scripté (LLM, CI, §13.5), une invite bloquerait ces usages en
attendant une entrée qui ne viendra jamais.

### 11.2 `demo`

```bash
lightwebpres demo [répertoire] [--lang fr]
```

Vérifie que `install` a été fait (présence de `templates/style.css`). Si
non, erreur fatale invitant à lancer `install` d'abord.

Refuse de s'exécuter si l'un des 7 fichiers de démo (6 `.md` +
`img/demo-figure.svg`) existe déjà dans `articles/`, **ou si
`series.json` liste déjà au moins un article** (erreur fatale dans les
deux cas) — jamais d'écrasement silencieux d'un travail en cours :
`demo` réécrit `series.json` entièrement, ce qui n'est inoffensif que
sur le boilerplate d'un `install` frais (liste d'articles vide).

Crée trois articles d'exemple, un pour chaque position de la navigation de
série :

1. Crée `articles/first.md` + `articles/first_article.md` (position
   « first » ; démontre chaque champ d'affichage explicitement, plus
   `date:` et `comment:` ; l'article long contient une image légendée
   `![alt](img/demo-figure.svg "…")` (§6.1) dont le SVG est écrit dans
   `articles/img/demo-figure.svg`)
2. Crée `articles/middle.md` + `articles/middle_article.md` (position
   « middle » ; démontre `highlight`/`highlight-caption`, et la surcharge
   d'un `card_label` depuis `series.json`)
3. Crée `articles/last.md` + `articles/last_article.md` (position
   « last » ; bloc meta vide — démontre la cascade complète §20.3.1)
4. Met à jour `series.json` avec ces trois articles (`series_meta`
   inclus, avec `author`/`license` de démonstration)
5. Lance le build → génère `public/first.html`, `public/middle.html`,
   `public/last.html` et `public/index.html`
6. Affiche un message : « Demo site generated in public/. Open
   public/index.html in a browser. »

### 11.3 `build`

```bash
lightwebpres build [répertoire] [--lang fr] [--output public/] [--no-typography] [--include-drafts]
```

Construit le site :

1. Lit `series.json` dans `[répertoire]`. Les articles marqués
   `draft: true` (§20.6) sont **entièrement exclus** — pas de page, pas
   de carte d'index, pas d'entrée dans les navigations des autres
   articles — sauf avec `--include-drafts` (build **et** check), qui les
   construit tous, chaque page brouillon portant alors un bandeau
   « Brouillon » (clé `draft_banner` du fichier de langue) affiché au
   centre de l'en-tête de page, entre l'éventuel build stamp (§11.3.2) et
   le numéro de fiche — un aperçu ne doit jamais être confondu avec une
   publication (style inline, comme le stamp, pour ne pas dépendre d'un
   `templates/style.css` antérieur à la fonctionnalité).
2. Pour chaque article dans `series.json` :
   a. Lit le fichier `.md` source depuis `articles/`
   b. Parse le Markdown étendu (découpe les slides, extrait les métadonnées)
   c. Pour chaque slide :
      - Si `cover` : génère la slide de couverture
      - Si `standard` : génère la slide avec les champs et le contenu
      - Si `series-nav` : génère la navigation depuis `series.json`
      - Si `full-article` : lit le fichier `.md` inclus, le convertit
   d. Applique les règles typographiques (protégées des balises HTML,
      §7.2), sauf avec `--no-typography` (aucune règle ne s'exécute pour
      aucun article de ce build, §4.5/§19.6) ou pour un article dont le
      bloc meta porte `typo: off` (même effet, mais pour cet article
      seul, §4.5)
   e. Assemble le HTML avec la structure de page fixe (§9), le CSS et le JS
   f. Écrit le fichier HTML dans `public/`
3. Génère la page d'index (`public/index.html`)
4. Génère le `README.md` à la racine du répertoire de série (§8.3)
5. Copie les images de `articles/img/` vers `public/img/` : fusionne avec
   l'existant, ne supprime **jamais** un fichier présent dans `public/img/`
   même s'il n'existe plus dans `articles/img/` — comme pour les pages HTML
   d'articles retirés de `series.json` (qui restent elles aussi dans
   `public/` sans être nettoyées), `build` est additif/à jour, jamais un
   miroir exact qui purge ce qui n'est plus source. Un `--output` mal typé
   ne peut donc jamais faire disparaître du contenu qui n'a pas été mis là
   par `build` lui-même. Un résidu (image ou page orpheline) reste possible
   après suppression d'un article ; à nettoyer à la main si besoin.
6. Écrit l'empreinte de navigation (§11.3.1) dans `.lwp-cache/nav.json`
   (ou le chemin donné par `--nav-cache`)

### 11.3.1 `build --only` : reconstruction d'un seul article

```bash
lightwebpres build [répertoire] --only fichier.html [--nav-cache chemin]
```

Reconstruit un seul article au lieu de toute la série — pensé pour un
usage d'édition répétée (typiquement un aperçu live pendant qu'on
travaille un seul article, voir la spec `lightwebpres-gui` §8.2), là où
reconstruire toute la série à chaque pause de frappe serait disproportionné
sur une série à beaucoup d'articles.

**Désignation de l'article** : la valeur de `--only` est comparée au
`page_dest` **ou** au `page_source` de chaque article — `--only a.html`
et `--only a.md` désignent le même article. Aucune correspondance →
erreur fatale (« matches no article »), de même qu'un `page_source`
correspondant mais dont le fichier n'existe pas. Les brouillons étant
exclus de la liste avant ce filtre, un article `draft: true` n'est
désignable par `--only` qu'avec `--include-drafts`.

**Le piège que ça doit éviter** : `build_index()` et `build_series_nav()`
utilisent tous les deux les champs d'affichage résolus par
`resolve_article_fields()` (`page_title`, `card_title`, `card_desc`,
`card_label`, `nav_title`, `nav_desc`, §20.3.1) — et `build_series_nav()`
est intégré dans la page de **chaque** article, pas seulement dans
`index.html`. Changer le titre de l'article A peut donc rendre obsolètes
les pages déjà construites de B, C, D..., pas seulement l'index.
Reconstruire uniquement le fichier demandé sans vérifier ça produirait un
site avec une navigation périmée.

**Le mécanisme de sécurité** : à chaque `build` (complet ou avec `--only`),
une empreinte est calculée pour chaque article — un hash SHA-256 des 6
champs ci-dessus concaténés, jamais leur contenu en clair (fichier de
cache petit et de taille constante, indépendant de la longueur des
résumés) — et écrite dans `.lwp-cache/nav.json` (racine du répertoire de
série, à côté de `articles/`/`templates/`/`public/`, jamais dans l'un de
ces deux derniers pour les garder tels quels — un artefact de build de
plus, comme `public/`, mais pas mélangé avec lui). `--nav-cache chemin`
change cet emplacement. `page_dest` n'entre pas dans ce hash : il sert de
*clé* à l'empreinte (une empreinte par `page_dest`), donc un `page_dest`
qui change — via une nouvelle valeur explicite ou une redéduction depuis
`page_source`/le bloc meta — change la clé elle-même et est détecté par
construction, sans avoir besoin d'entrer aussi dans le hash. Même
mécanisme pour `draft` : l'empreinte est calculée sur la liste *après*
filtrage des brouillons, donc basculer un article en brouillon (ou l'en
sortir) change l'ensemble des clés et force un build complet.

Au lancement de `build --only fichier`, l'empreinte est recalculée pour
**tous** les articles (rien de coûteux : ne fait que reparser les blocs
meta, jamais convertir un corps entier) et comparée à celle du cache :

- **Identique pour tous les articles** (y compris ceux autres que
  `fichier` — un article ajouté/retiré, ou les champs d'un autre article
  changés entre-temps, sont détectés de la même façon) → reconstruction
  du seul fichier demandé, plus `index.html`/`README.md`/images (bon
  marché, refaits systématiquement) — l'étape évitée est la seule
  vraiment coûteuse : reconvertir le corps Markdown de chaque *autre*
  article.
- **Cache absent, illisible, ou différent** → bascule silencieuse sur un
  `build` complet, jamais une erreur ni une page obsolète silencieuse ;
  un message `[INFO]` explique pourquoi.

### 11.3.2 `build --build-stamp` / `--build-stamp-minimal` : marqueur de fraîcheur

```bash
lightwebpres build [répertoire] --build-stamp
lightwebpres build [répertoire] --build-stamp-minimal
```

Deux options, toutes deux désactivées par défaut. Ajoutent sur **chaque**
page générée (chaque article et `index.html`) un marqueur discret, placé
dans l'en-tête même de la page — visible uniquement en haut de défilement,
comme n'importe quel autre contenu d'en-tête, jamais superposé au reste
de la page pendant la lecture (contrairement à un premier essai fixé au
viewport, corrigé après retour explicite : voir plus bas) :

```
Compiled at YYYY-MM-DD HH:MM:SS with lightwebpres vX.Y.Z.   ← --build-stamp
Compiled with lightwebpres.                                  ← --build-stamp-minimal
```

Le besoin réel : savoir d'un coup d'œil si un onglet resté ouvert, ou un
déploiement, correspond bien au dernier `build` — pas juste s'y fier de
mémoire. L'horodatage est calculé une seule fois par exécution de
`build` (pas une fois par fichier) : toutes les pages d'un même build
affichent exactement le même horodatage, cohérent avec « à quel moment
ce build a eu lieu », pas « à quelle microseconde ce fichier précis a
été écrit ».

**`--build-stamp-minimal`** : la date/heure de compilation est une
donnée qui peut ou non être sensible à publier (elle peut révéler quand
un document a été préparé) — cette variante l'omet entièrement, avec le
numéro de version aussi (pas une divulgation partielle). Si les deux
options sont passées ensemble, `--build-stamp-minimal` l'emporte
toujours : un choix de confidentialité explicite ne doit jamais être
silencieusement écrasé par l'option la plus riche.

**Jamais activé par défaut** : un horodatage vivant rend le build
non-reproductible à l'octet près d'une exécution à l'autre, une propriété
que `check` (§11.4) présuppose justement pour son diff exact.

**`check` ignore le marqueur, dans les deux sens, pour les deux
variantes** : le HTML généré en mémoire par `check` pour comparaison
n'inclut jamais de marqueur (ni la valeur de `--build-stamp` ni celle de
`--build-stamp-minimal` n'atteint son propre appel à `build_article`), et
le marqueur trouvé sur le fichier existant dans `public/` est retiré
avant comparaison (`strip_build_stamp()`, qui repère la `<div>` par sa
classe, indépendamment du texte qu'elle contient) — une série construite
avec l'une ou l'autre option reste donc normalement « checkable », sans
dérive systématique due au seul horodatage. Cette suppression ne touche
que le seul élément que `lightwebpres` génère lui-même
(`<div class="build-stamp" style="...">...</div>`), jamais un contenu
d'auteur.

**Style entièrement en ligne, jamais dans `style.css`** — bug réel trouvé
en testant à la main juste après la première version : une série avec
son propre `templates/style.css` (personnalisé, ou simplement scaffoldé
avant l'existence de cette option) n'a aucun moyen de récupérer une
nouvelle règle intégrée sans passer par `refresh-templates` (§9.4). La
première version du marqueur dépendait d'une règle `.build-stamp` dans
la feuille de style partagée — absente de ce genre de série, la `<div>`
se retrouvait sans style du tout : un bloc pleine largeur, texte de
couleur par défaut, poussant la première fiche vers le bas au lieu de se
superposer discrètement dans le coin (repéré visuellement, capture
d'écran à l'appui, avant d'être corrigé). Le style (couleur, taille,
`pointer-events: none`, positionnement) est maintenant entièrement porté
par l'attribut `style=""` de la `<div>` elle-même, jamais dépendant d'une
règle externe — y compris la couleur grise, qui utilise une valeur
hexadécimale fixe plutôt que `var(--ink-muted)` (même risque : une propriété
personnalisée définie dans le `style.css` intégré peut, elle aussi, être
absente d'un `style.css` ancien ou personnalisé).

**`position: absolute`, pas `fixed`** — deuxième itération, retour
explicite après la première version livrée : le marqueur doit apparaître
dans l'en-tête de la page, pas rester épinglé à la fenêtre du navigateur
pendant tout le défilement. Sans ancêtre positionné, `absolute` se
calcule par rapport au bloc englobant initial (ancré en haut du document,
pas de la fenêtre) : le marqueur défile normalement avec le reste du
contenu, exactement comme `fixed` l'aurait empêché de faire. Testé
(`tests/test_lightwebpres.py`, `BuildStamp.
test_stays_discreet_with_a_custom_style_css_lacking_the_rule`) : un
`templates/style.css` sur mesure sans aucune règle liée au marqueur, et
le marqueur reste correctement positionné ; `test_minimal_variant_*` et
`test_minimal_wins_if_both_flags_passed` couvrent `--build-stamp-minimal`
et sa priorité.

### 11.4 `check`

```bash
lightwebpres check [répertoire] [--lang fr] [--no-typography]
```

Vérifie sans modifier :

1. Lance le build en mémoire (sans écrire les fichiers) ; `--no-typography`
   a le même effet que sur `build` (§11.3), sur ce build en mémoire —
   utile pour vérifier un `public/` déjà généré sans typographie, pas pour
   ignorer une vraie différence de typographie sur un `public/` généré
   normalement (`check` comparerait alors deux HTML volontairement
   différents et signalerait un `[DRIFT]` correct, pas un faux positif)
2. Compare la sortie générée avec l'existant : **chaque page d'article**
   contre `public/`, plus **`index.html`** (contre `public/`) et
   **`README.md`** (contre la racine du répertoire de série) — un
   changement de `series_meta` (titre, intro, ordre des articles) ne
   modifie que ces deux derniers, et `check` restait vert dessus avant la
   v0.9.0 : c'était un trou dans la porte de CI
3. Pour chaque fichier différent, affiche `[DRIFT] fichier` suivi d'un diff ;
   pour chaque fichier absent, affiche `[NEW] fichier` ; pour
   chaque fichier identique, affiche `[OK] fichier`
4. Affiche un résumé chiffré : « N file(s) OK, M file(s) different. »
   (N + M = nombre d'articles + 2)
5. Code de sortie non nul (1) si au moins un fichier diffère ou est absent —
   c'est ce qui permet d'utiliser `check` comme porte de vérification dans un
   script ou une CI (§10) ; code de sortie 0 et « All files are up to
   date. » si tout est identique (M = 0)

### 11.5 `audit`

```bash
lightwebpres audit [répertoire] [--lang fr]
```

Vérifie des **conventions éditoriales non bloquantes**, sans jamais faire
échouer la commande ni modifier de fichier (contrairement à `check`, qui
compare le HTML généré à l'existant, §11.4) :

1. Pour chaque article, lit et parse le `.md` source
2. Avertit si l'article ne contient **aucune** fiche `cover`
3. Avertit si la **première** fiche de l'article n'est pas une `cover`
4. Avertit si l'article n'a de description **nulle part** (`page_desc`
   vide à tous les niveaux de la cascade §20.3.1 — la balise
   `<meta name="description">` serait omise)
5. Avertit si la **section personnelle** de `templates/style.css` (après
   le marqueur de §9.4) référence encore une variable de palette
   renommée en v0.12.0, en nommant chacune et son remplaçant. Voir §9.1 :
   aucun alias n'a été conservé, donc une telle déclaration est
   simplement invalide et cesse de s'appliquer sans que rien ne le
   signale — c'est le seul endroit du système qui rend cette rupture
   audible. La partie intégrée au-dessus du marqueur n'est pas
   inspectée : elle migre seule au premier `refresh-templates`, et la
   signaler enverrait un auteur éditer un fichier qu'il ne doit pas
   éditer.
6. Affiche un résumé (en anglais, non localisé) : « No warnings: all
   editorial conventions are respected. » ou « N warning(s). Reminder:
   audit never blocks... »

Le nombre et la position des fiches `cover` restent libres (§4.4, §22.13) :
`audit` ne fait qu'informer, la décision reste à l'auteur. Les brouillons
(§20.6) sont audités comme les autres articles, jamais exclus.

### 11.6 `refresh-templates`

```bash
lightwebpres refresh-templates [répertoire]
```

Met à jour la partie intégrée à l'exécutable de `templates/style.css` et
`templates/nav.js` sans écraser une personnalisation locale — voir §9.4
pour le mécanisme exact (marqueur pour `style.css`, sauvegarde
`nav.js.bak` pour `nav.js`). Si `style.css` porte le marqueur de thème de
§9.5.1, le thème identifié est réappliqué à la partie intégrée à jour
plutôt que de revenir au thème par défaut — voir §9.5.4 pour le détail.

1. Erreur fatale si `templates/` n'existe pas (`install` pas encore fait)
2. Pour chaque fichier présent, affiche s'il a été rafraîchi ou était déjà
   à jour
3. Pour `style.css` sans marqueur trouvé, affiche `[SKIP]` avec la ligne à
   ajouter à la main, et laisse le fichier inchangé
4. Code de sortie non nul si au moins un fichier a été « skipped » faute de
   marqueur ; 0 sinon

Ne relance pas `build` automatiquement : les fichiers HTML déjà générés
dans `public/` restent inchangés tant que `build` n'est pas relancé à la
main.

### 11.7 `themes-gallery`

```bash
lightwebpres themes-gallery [chemin]
```

Génère une page HTML autonome (aucune dépendance) documentant chaque
entrée de `THEMES` (§9.5) — un aperçu de son rendu sur un fragment de
fiche réel, ses six valeurs, et sa remarque éditoriale. Ne modifie aucun
`series.json` ni `templates/` : cette commande documente, elle n'installe
rien.

L'aperçu reçoit aussi les superpositions neutres du thème (§9.5.2), sans
quoi une palette à fond sombre s'afficherait avec les voiles d'une page
claire — c'est-à-dire pas telle qu'elle rendra réellement.

Sous chaque aperçu, une ligne « Gras en fact-box » **énonce** le
traitement du gras que le thème a choisi (§9.1) — « Gras, surligné
`--marker` », « Gras, sans surlignage », « Italique, surligné
`--positive` », « Gras, sans surlignage, souligné `--marker` »… La
galerie appliquait ces propriétés à sa maquette sans jamais les nommer :
neuf combinaisons distinctes existent parmi les thèmes intégrés et
aucune n'était lisible autrement qu'en scrutant deux lignes d'aperçu.
Le soulignement n'est mentionné que lorsqu'il est présent — en annoncer
l'absence sur chaque carte noierait les axes qui, eux, diffèrent.

**Fidélité de l'aperçu.** L'aperçu est une *miniature*, pas une capture
d'écran : ses tailles et ses espacements sont délibérément réduits. En
revanche la **correspondance variable → rôle** doit être identique à
celle de la feuille de style réelle, et aucune couleur ne doit y être
figée :

| Rôle | Aperçu | Feuille réelle | Variable |
|---|---|---|---|
| fond de page | `.preview` | `body` | `--page` |
| fond de couverture | `.preview-cover` | `.slide-cover` | `--cover-bg` |
| texte de couverture | `.preview-cover-title` | `.slide-cover h1` | `--cover-fg` |
| surface de carte | `.preview-factbox` | `.fact-box` | `--surface` |
| fond en creux | `.preview-cell--neutral` | `.comparison-table th` | `--sunken` |
| encre du surlignage | `.preview-factcontent strong` | `.fact-content strong` | `--fact-strong-ink` |
| couleur du soulignement | `.preview-factcontent strong` | `.fact-content strong` | `--fact-strong-decoration-color` |

Passer les variables du thème à l'aperçu ne suffit pas si l'aperçu les
ignore ensuite : c'est ce qui s'est produit. Le fond de couverture était
figé à `var(--ink)` et son texte à `#fff`, la fact-box à `#fff`. Sur un
thème à fond sombre, `--ink` porte la couleur du **texte** : Synthwave
s'affichait donc en panneau lavande pâle surmonté de texte blanc, au-dessus
d'une fact-box blanche dont le texte était presque invisible — exactement
les défauts corrigés dans la feuille réelle, toujours exposés dans la page
censée montrer ce que donnent les thèmes.

Deux conséquences moins évidentes, toutes deux vérifiées par les tests :

- L'aperçu doit porter **son propre fond de page** (`var(--page)`). Les
  neutres sont des superpositions translucides : `--cover-bg` vaut
  `rgba(0, 0, 0, 0.45)` sur un thème sombre, destiné à assombrir la page
  en dessous. Sans fond propre, ce voile se composait sur la carte claire
  de la galerie et la couverture ressortait simplement grise.
- Les cellules de verdict portent aussi leur **marqueur de forme**
  (§6.1). Un aperçu qui n'en montrerait que la couleur annoncerait une
  cellule que l'outil ne produit plus.

En tête de page, une barre de **facettes** (§9.5.3) filtre les aperçus
par polarité, intensité et teinte. Elle est produite en HTML statique
mais masquée par défaut, et révélée par le script inline de la page :
sans JavaScript, la galerie reste une liste complète et lisible plutôt
qu'une barre de boutons inertes. Le script affiche en permanence le
nombre d'aperçus visibles et **désactive** toute facette qui ne mènerait
à aucun résultat compte tenu des autres déjà actives — on ne peut donc
pas se retrouver devant une page vide sans comprendre pourquoi.

`chemin`, s'il est omis, vaut `themes-gallery.html` dans le répertoire
courant — c'est ainsi que le fichier à la racine du dépôt lightwebpres
lui-même est produit, et il n'a plus vocation à être modifié à la main
(§9.5) : toute correction sur un thème (couleur, remarque) se fait dans
`THEMES`, puis `themes-gallery` régénère le fichier.

Le texte d'exemple de chaque aperçu (« Chapitre 1 », « La température
change tout », etc.) est fixe, en français, non localisé par `--lang` —
c'est un choix éditorial pour cette page de référence, pas une limite du
moteur de fiches lui-même.

### 11.8 `--help`

Affiche l'aide avec la liste des commandes et options.

La section THEMES de cette aide **n'énumère plus les slugs**. À neuf
thèmes, la liste était un rappel utile ; passé la trentaine, c'est un mur
de noms qui ne dit rien de ce que chacun donne à l'écran — exactement le
problème que les facettes existent pour résoudre, simplement déplacé de
la galerie vers le terminal. L'aide renvoie donc aux deux commandes qui
savent répondre à « lequel je veux » : `themes` et `themes-gallery`.

### 11.9 `themes`

```bash
lightwebpres themes [--polarity light|dark] [--intensity sober|vivid|mono] [--hue <teinte>]
```

Liste les thèmes intégrés depuis le terminal, avec pour chacun son slug,
ses trois facettes (§9.5.3), son étiquette et sa remarque éditoriale.
Sans option, les liste tous ; chaque option restreint la liste, et les
options se combinent.

Cette commande existe parce que **lightwebpres doit pouvoir être utilisé
seul**. Les facettes n'ont d'abord vécu que dans le HTML produit par
`themes-gallery`, ce qui imposait un aller-retour par un navigateur pour
choisir un thème — inacceptable pour un outil en ligne de commande, et
d'autant plus que l'interface graphique est un projet séparé qui ne peut
rien garantir ici.

Le slug est mis en avant dans la sortie parce que c'est ce que
`install --theme` et `set-theme` attendent : ce qu'on lit est
directement ce qu'on retape.

Deux cas se distinguent volontairement :

- **Valeur de facette inconnue** (`--hue rouge`) : erreur fatale qui
  liste les valeurs valides. Répondre « aucun thème ne correspond »
  enverrait le lecteur chercher un thème qui existe pourtant, à une
  faute de frappe près.
- **Combinaison valide mais vide** (`--polarity dark --hue orange`) :
  succès, avec un message nommant la combinaison restée sans résultat.
  Ce n'est pas une erreur, c'est une réponse.

### 11.10 `set-theme`

```bash
lightwebpres set-theme [répertoire] --theme <slug> [--force]
```

Change le thème d'une série existante, en réécrivant les variables de
`templates/style.css` (§9.5.1). Avant cette commande, les seules voies
étaient de réinstaller la série ou d'éditer à la main le marqueur de
thème puis de lancer `refresh-templates` — un effet de bord du mécanisme
de survie aux mises à jour (§9.5.4), que rien ne documentait et que
personne ne devinerait.

Le fichier produit est **identique octet pour octet** à celui
qu'`install --theme <slug>` aurait écrit. Deux chemins vers le même état
ne doivent pas donner deux fichiers différents, sans quoi `check`
signalerait une dérive sur une série dont on a simplement changé le
thème.

**Le message nomme les deux thèmes**, celui qui part et celui qui
arrive :

```
Theme changed: nord -> evergreen
```

Un fichier sans marqueur est sur le thème par défaut, ce qui est une
réponse à « remplacé par quoi » et non une valeur manquante : il
s'affiche `default -> <slug>`. Un marqueur nommant un thème que cette
version ne connaît pas s'affiche `<slug> (unknown) -> <slug>`.

**`--force` et la notion de fichier standard.** La commande refuse un
`templates/style.css` dont la partie intégrée n'est pas exactement celle
que cet exécutable aurait écrite pour le thème qu'il porte. Trois cas
la rendent non standard :

1. la partie intégrée diffère (éditée à la main, ou écrite par une autre
   version de l'exécutable) ;
2. le marqueur de personnalisation (§9.4) est absent, donc le CSS
   intégré ne peut pas être distingué des règles de l'auteur ;
3. le marqueur de thème nomme un slug inconnu de `THEMES`.

Le motif du refus n'est pas la prudence de principe : la substitution
opère sur des motifs précis (`--<nom>: <valeur>;` dans `:root`). Une
déclaration réécrite en `rgb(...)`, ou déplacée hors de `:root`, ne
correspond plus au motif et **garderait silencieusement son ancienne
valeur** — une page à moitié recolorée, pire que pas de commande du
tout. `--force` passe outre, applique quand même, et **avertit** en
nommant le motif.

Un refus n'écrit rien.

Les règles ajoutées **après** le marqueur de personnalisation (§9.4) sont
préservées dans tous les cas et ne rendent jamais un fichier non
standard : c'est la façon prévue de personnaliser.

Enfin, demander le thème déjà en place n'écrit pas le fichier et le dit
(`Theme unchanged`), plutôt que de mettre à jour une date de
modification pour rien.

---

## 12. Algorithme du build

### 12.1 Étape par étape

```
build(répertoire):
  1. series = read_json(répertoire/series.json)
  2. lang = --lang OU $LWP_LANG OU "fr" (défaut)
  3. language = load_language(lang, --language-file)  # rules + strings, §19.5 pour l'ordre de priorité complet
  4. css = read_file(répertoire/templates/style.css) OR built-in default
  5. js = read_file(répertoire/templates/nav.js) OR built-in default
  # La structure de page (page_template) et d'index (index_template) est
  # fixe, intégrée à l'exécutable — pas lue depuis templates/ (§9)

  6. FOR each article IN series:
     a. source = read_file(répertoire/articles/{article.page_source})
     b. meta, slides = parse_markdown(source)
     c. html_slides = []
     d. slide_num = 0
     e. total_slides = count_slides(slides)

     f. FOR each slide IN slides:
        slide_num += 1
        IF slide.type == "cover":
          html = render_cover(slide, meta, slide_num, total_slides)
        ELIF slide.type == "series-nav":
          html = render_series_nav(series, article, slide_num, total_slides, language.strings)
        ELIF slide.type == "full-article":
          article_md = read_file(répertoire/articles/{slide.article})
          article_html = convert_markdown(article_md)
          article_html = apply_typography(article_html, language.rules)
          html = render_full_article(article_html, slide_num, total_slides, language.strings)
        ELSE:  # standard
          html = render_standard(slide, slide_num, total_slides, language)

        html_slides.append(html)

     g. title = extract_title(meta)
     h. html = fill_page_template({
          "lang": lang,
          "title": title,
          "css": css,
          "js_nav": js,
          "slides": "\n".join(html_slides)
        })  # fill_page_template uses the fixed, built-in page structure (§18.1)
     i. write_file(répertoire/public/{article.page_dest}, html)

  7. index_html = generate_index(series, css, js)  # fixed, built-in index structure (§18.2)
  8. write_file(répertoire/public/index.html, index_html)

  9. generate_readme(series, répertoire/README.md)
  10. copy_images(répertoire/articles/img/, répertoire/public/img/)  # merge, never wipe
```

### 12.2 Parseur Markdown étendu

```
parse_markdown(text):
  1. Split sur /^---$/m (lignes contenant uniquement ---)
  2. Le premier segment est le bloc meta (si il commence par <!-- lwp:meta -->)
  3. Pour chaque segment suivant :
     a. Chercher <!-- lwp:slide:TYPE --> (défaut: standard)
     b. Extraire les champs clé: valeur (lignes en début de segment)
     c. Le reste est le contenu Markdown
  4. Retourner (meta, slides)
```

### 12.3 Rendu d'une fiche standard

```
render_standard(slide, slide_num, total_slides, language):
  1. html = '<section class="slide" id="s{slide_num}">'
  2. html += '<span class="slide-num">{slide_num} / {total_slides}</span>'
  3. IF slide.tag:
     html += '<span class="slide-tag">{tag}</span>'
  4. IF slide.h2:
     html += '<h2>{h2}</h2>'
  5. IF slide.summary:
     html += '<p class="summary">{summary}</p>'
  6. IF slide.highlight:
     html += '<div class="highlight">'
     html += '<span class="highlight-figure">{highlight}</span>'
     IF slide.highlight_caption:
       html += '<span class="highlight-caption">{highlight_caption}</span>'
     html += '</div>'
  7. IF content:
     IF slide.fact_label:
       html += '<div class="fact-box">'
       html += '<div class="fact-label">{slide.fact_label}</div>'
       html += '<div class="fact-content">{content}</div>'
       html += '</div>'
     ELSE:
       html += '{content}'  # content is already full HTML (§6.1), not re-wrapped
  9. IF slide.source:
     html += '<p class="source">{language.strings.source_label} : {source}</p>'
  10. html += '</section>'
  11. Apply typography rules (language.rules) to all text values
  12. Return html
```

---

## 13. Contraintes

### 13.1 UTF-8

Tous les fichiers sont lus et écrits en UTF-8. Les chaînes Python sont en
Unicode. Les règles typographiques utilisent `\u00a0` pour l'espace insécable.

Deux comportements de lecture, valables pour **toutes** les sources
(articles, `series.json`, fichiers de langue, templates) :

- Un **BOM UTF-8** en tête de fichier est toléré et absorbé (lecture en
  `utf-8-sig`) — il n'apparaît jamais dans la sortie. (Historiquement, un
  BOM fuyait un U+FEFF dans le HTML publié et cassait le premier titre.)
- Un fichier qui n'est **pas de l'UTF-8 valide** produit une erreur
  fatale propre avec l'offset de l'octet fautif — jamais une traceback.

### 13.2 HTML autonome

Chaque fichier HTML généré est **autonome** :
- Le CSS est inline dans `<style>`
- Le JS est inline dans `<script>`
- Pas de lien vers des fichiers externes (sauf images en chemin relatif)
- Pas de CDN, pas de dépendance réseau

### 13.3 Idempotence

Le build est **idempotent** : relancer le build avec les mêmes sources produit
exactement les mêmes fichiers. Pas de timestamp, pas d'UUID, pas de variable
non déterministe.

### 13.4 Pas de dépendance externe

L'exécutable n'utilise que la bibliothèque standard de Python 3 — version
minimale 3.8 (§2.1) : sys, os, re, json, shutil, difflib, hashlib,
datetime, pathlib, types, html et html.parser. Pas de `pip install`.
Ni `argparse` (la ligne de commande est analysée à la main dans `main()`)
ni `glob`/`textwrap`.

### 13.5 Édition par LLM

Le format Markdown étendu est conçu pour être lisible et modifiable par un
LLM :
- Les métadonnées sont des lignes `clé: valeur` simples
- Les séparateurs `---` sont visibles
- Les marqueurs `<!-- lwp:slide:TYPE -->` sont explicites
- Le contenu est du Markdown standard
- Un LLM peut générer un fichier `.md` complet en une seule passe

### 13.6 Validation du HTML généré

Chaque page (article, index) est vérifiée juste avant d'être écrite : un
contrôleur basé sur `html.parser` (stdlib) rejoue le HTML produit et
vérifie que les balises sont bien équilibrées (chaque balise ouverte a sa
fermeture, dans le bon ordre, aucune fermeture surnuméraire ou orpheline).
Erreur fatale sinon — un bug dans un template ou dans `convert_markdown()`
ne doit jamais publier silencieusement une page structurellement cassée.

Ce n'est **pas** une conformité HTML5 complète (pas de vérification des
attributs, de l'imbrication sémantique autorisée par catégorie de contenu,
etc.) — seulement l'équilibrage des balises, qui est la classe de défaut
qu'un bug de rendu de ce projet peut réellement produire, et la seule
qu'un outil strictement stdlib puisse vérifier sans dépendance externe
(§13.4). Les éléments vides du HTML5 (`br`, `hr`, `img`, `meta`, `input`,
etc.) ne sont pas comptés comme devant être fermés ; le contenu de
`<script>`/`<style>` est traité comme texte brut par `html.parser`
lui-même, donc du JS contenant `<`/`>` (comparaisons, etc.) n'est jamais
pris pour une balise.

Effet de bord utile : un `series_meta.title`/`page_title` contenant un fragment
qui casserait la structure de la page (par exemple un `</title>` orphelin
copié tel quel dans le corps visible, où le HTML brut est autorisé par
conception comme pour `<br>`) fait désormais échouer le build au lieu
d'être publié — cette vérification agit comme un filet de sécurité
générique, pas seulement contre les bugs de rendu.

### 13.7 Modèle de menace et contenances

Le contenu source (`series.json`, `.md`) est **semi-fiable** : il peut
être édité par un LLM ou tiré d'un dépôt lors d'une CI non surveillée
(§13.5). Deux principes en découlent, et sont figés par des tests de
régression :

- **Contenance du système de fichiers.** Toute valeur qui devient un
  chemin réel — `page_source`, `page_dest`, le champ `article:` d'une
  fiche full-article, et le contenu de `articles/img/` — est confinée à
  son répertoire. Le contrôle de forme du nom (nom nu, ni `/` ni `..` ni
  `.` ni octet NUL) est doublé d'un contrôle **realpath** : un nom nu qui
  est en réalité un lien symbolique pointant hors de `articles/`
  (respectivement `articles/img/`) est **refusé**, jamais suivi — sinon
  un lien commité dans un dépôt exfiltrerait un fichier de l'hôte dans le
  site publié. Un lien symbolique interne (cible restant dans le
  répertoire) reste autorisé.
- **Contextes HTML échappés vs bruts.** Les valeurs qui atterrissent dans
  un **attribut** (`<meta name="author">`/`<meta name="description">`
  depuis `author`/`page_desc`, le `href` d'un lien Markdown, `src`/`alt`
  d'une image) sont **débalisées et/ou échappées** — un guillemet ou un
  chevron ne peut pas s'évader du contexte. Le `<title>` (RCDATA) est
  débalisé. Les rendus **visibles** (corps de fiche, `card_*`, pied de
  page `author`/`date`/`license`, `intro`, légendes) sont du HTML brut
  **par conception** (§6.2) : l'auteur y a délibérément la main. Le champ
  `license` accepte ainsi du HTML brut quelconque (typiquement un lien) ;
  ce n'est pas une élévation de privilège, c'est la même capacité que
  dans tout corps de fiche. Un intégrateur qui alimenterait `author`,
  `date` ou `license` depuis une source **moins** fiable doit donc les
  échapper lui-même en amont. Le contrôle d'équilibrage (§13.6) rattrape
  en dernier recours toute charge brute qui casserait la structure : elle
  fait échouer le build au lieu d'être publiée.
- **Complexité bornée.** Les expressions régulières — du convertisseur
  **comme** le débalisage des sinks `<title>`/`<meta>` — sont linéaires
  sur une entrée adverse (pas de retour arrière quadratique) : une ligne
  ou un champ pathologique ne peut pas geler un build (important pour
  l'exécution navigateur, mono-thread, §23). Les règles typographiques
  d'un **fichier de langue** restent hors de ce périmètre : un fichier de
  langue est du **code de confiance** (§7.2), au même niveau que
  l'exécutable.
- **Types validés, erreurs propres.** Une valeur de `series.json` ou d'un
  fichier de langue au mauvais type (un nombre/objet/liste là où une
  chaîne est attendue, un `series_meta` non-objet, un JSON trop imbriqué)
  produit un `[ERROR]` clair, jamais une traceback Python — la même
  garantie que §20.3/§19.2 posent pour le reste du format.
- **Placeholders non ré-injectables.** Les gabarits de page sont remplis
  en **une seule passe** : un jeton `{{…}}` écrit littéralement dans un
  champ d'auteur (par ex. `{{css}}` dans `page_title`) reste littéral, il
  n'est jamais substitué — ce qui fermait la seule voie par laquelle du
  contenu d'auteur pouvait contourner le débalisage de `<title>`/`<meta>`
  (§18.4).

### 13.8 Dépendance vendorisée (page navigateur)

La page `web/` embarque Pyodide (§23) — le seul tiers du projet. Ces
fichiers exécutent le code qui manipule la série de l'utilisateur (et,
sur l'onglet GitLab, son jeton), donc leur intégrité compte. Ils sont
**commités dans le dépôt** (toute modification est relue en diff) et
servis **en même origine** (aucun CDN au runtime). `web/vendor/pyodide/
SHA256SUMS` enregistre le SHA-256 de chaque fichier servi ; un test de la
suite vérifie que ce fichier reste synchrone, et la procédure de mise à
jour (`web/vendor/NOTICE.md`) épingle une version exacte et **vérifie le
hash amont avant de copier** — jamais `latest` sans contrôle.

### 13.9 Politique de versionnage

Le numéro de version (constante `VERSION` de l'exécutable, affichée par
`--help` et par le build stamp) suit le **versionnage sémantique**
`MAJEUR.MINEUR.CORRECTIF`. Ce que chaque incrément promet, à partir de la
1.0 :

- **CORRECTIF** (`x.y.Z`) : corrections de bugs, durcissements, sans
  changement d'API ni de format. Peut modifier le **HTML de sortie** (une
  correction de rendu, un ajustement de style) — ce n'est **pas** garanti
  stable à l'octet (voir ci-dessous).
- **MINEUR** (`x.Y.0`) : nouvelles fonctionnalités **rétrocompatibles** —
  un nouveau champ optionnel, une nouvelle option de commande, un nouveau
  thème. Une série valide pour `x.Y` le reste pour `x.Y+1`.
- **MAJEUR** (`X.0.0`) : changement **incompatible** du contrat d'entrée —
  renommer/supprimer un champ gelé (§2.5), changer la sémantique de la
  cascade (§20.3.1), retirer une commande ou une option. C'est exactement
  ce qui a motivé le gel de nomenclature avant la 1.0.

**Le contrat stable, c'est l'entrée, pas la sortie.** Sont garantis
stables au sein d'une même version MAJEURE : les noms et la portée des
champs (§2.5), la structure de `series.json`, le format de l'article
`.md`, les commandes et options de la CLI, les variables `LWP_*`. Le
**HTML produit**, lui, peut changer entre deux CORRECTIFs (amélioration de
style, de sémantique, d'accessibilité) : c'est pourquoi `check` (§11.4)
signale une dérive normale après une montée de version, jusqu'au prochain
`build` — ce n'est pas une régression, mais le comportement attendu. Un
build reste **reproductible à l'octet pour une version donnée** (§13.3),
ce dont `check` dépend ; la reproductibilité ne traverse pas les versions.

Avant la 1.0, toutes les releases sont des **préversions** : le format a
pu bouger d'une mineure à l'autre (c'est la phase de stabilisation qui
s'achève avec le gel §2.5). La 1.0 est le premier engagement de stabilité
au sens ci-dessus.

---

## 14. Parcours utilisateur

### 14.1 Parcours de création

```bash
# 1. Installer le framework
cp lightwebpres /usr/local/bin/  # ou utiliser ./lightwebpres

# 2. Créer une nouvelle série
lightwebpres install ma-serie

# 3. (Optionnel) Voir la démo
lightwebpres demo ma-serie

# 4. Créer ses articles (manuel ou par LLM)
# Éditer ma-serie/articles/snapchat.md
# Éditer ma-serie/articles/snapchat_article.md
# Éditer ma-serie/series.json

# 5. Construire
lightwebpres build ma-serie

# 6. Ouvrir le résultat
open ma-serie/public/index.html
```

### 14.2 Parcours de correction

```bash
# 1. Modifier un article
# Éditer ma-serie/articles/snapchat.md

# 2. Reconstruire
lightwebpres build ma-serie

# 3. Vérifier les changements
lightwebpres check ma-serie

# 4. Si le résultat convient, livrer
git add . && git commit && git push
```

### 14.3 Parcours d'édition par LLM

```bash
# 1. L'LLM reçoit une instruction : « Corrige le vocabulaire des fiches de
#    snapchat.md »
# 2. L'LLM lit ma-serie/articles/snapchat.md
# 3. L'LLM modifie le fichier
# 4. L'LLM lance : lightwebpres build ma-serie
# 5. L'LLM vérifie : lightwebpres check ma-serie
# 6. Si OK, l'LLM signale que la correction est faite
```

### 14.4 Parcours de pipeline CI

```bash
# Le .gitlab-ci.yml (créé par install --gitlab-ci, opt-in — §10/§11.1) fait :
#   python3 lightwebpres build .
#   artifacts: public/
#
# À chaque push :
# 1. GitLab CI lance le build
# 2. Le HTML généré est dans les artifacts
# 3. GitLab Pages peut servir le répertoire public/
```

---

## 15. Limites (volontairement non couvertes)

- **Live reload** : pas de serveur de développement (le build est un script)
- **Présentation orale** : pas de mode présentateur, pas de fullscreen
- **Multi-langue dans une même page** : une langue par build
- **Images inline** : les images restent en chemin relatif
- **Recherche full-text** : pas de moteur de recherche
- **Commentaires** : pas de système de commentaires de lecteurs (discussion
  publique sur un article publié) — à ne pas confondre avec le champ
  `comment` (§4.6), une note de relecture d'auteur, jamais publiée
- **Analytics** : pas de tracking
- **Citations imbriquées ou multi-paragraphes** (§6.3) : une seule
  citation, un seul paragraphe à la fois
- **Coloration syntaxique des blocs de code** (§6.3) : le nom de langage
  après ` ``` ` ne fait que poser une classe `language-xxx`, purement
  informative
- **Échappement générique façon CommonMark** (§6.3) : le `\` ne rend
  littéral que `>` en début de ligne et les backticks, pas toute la
  ponctuation ASCII

---

## 16. Feuille de route de développement

Les phases 1 à 5 ci-dessous sont **réalisées** (elles correspondent aux
versions 0.1 à 0.4) ; elles sont conservées comme trace de la
construction. Le développement ultérieur est tracé par les notes de
release du dépôt. Les pistes de la phase 6 restent **non planifiées** :
leur périmètre (1.0 ou post-1.0) n'est pas encore tranché.

### Phase 1 : Noyau (essentiel)

1. CLI avec `install`, `build`, `check`
2. Parseur Markdown étendu
3. Convertisseur Markdown → HTML
4. Rendu des 4 types de slides
5. Inclusion de fichiers `.md` (article complet)
6. Application des règles typographiques
7. Génération de la page HTML autonome

### Phase 2 : Série et navigation

8. Lecture de `series.json`
9. Génération de la navigation de série (`series-nav`)
10. Génération de la page d'index
11. Copie des images

### Phase 3 : Outils

12. Commande `demo` (génération d'articles d'exemple)
13. Commande `check` (comparaison)
14. Génération du README

### Phase 4 : CI et polish

16. `.gitlab-ci.yml` de base
17. Templates par défaut (CSS, JS)
18. Tests unitaires
19. Documentation

### Phase 5 : commande `audit` (implémentée)

Voir §11.5. Contrairement à `check` (qui compare le HTML généré à
l'existant, §11.4), `audit` vérifie des **conventions éditoriales non
bloquantes** — un article sans aucune fiche `cover`, ou dont la première
fiche n'est pas une `cover` — et n'émet que des avertissements informatifs,
sans jamais faire échouer le build ni contraindre l'auteur : la mise en page
(nombre et position des `cover`, voir §22.13) reste entièrement de son
ressort. D'autres vérifications éditoriales pourront s'y ajouter plus tard.

### Phase 6 : pistes non planifiées (périmètre à trancher — 1.0 ou post-1.0)

Demandées le 2026-07-31 :

20. **Syntaxe Markdown native pour les images** (`![alt](src)`) —
    IMPLÉMENTÉ (voir §6.1) : seule sur sa ligne, l'image devient un bloc
    `<figure>` ; au milieu d'un paragraphe, un `<img>` inline. La `src`
    peut être un chemin relatif (contrairement aux liens, restreints à
    http(s)) — c'est le cas d'usage `articles/img/` → `public/img/`.
21. **Légendes pour les images** — IMPLÉMENTÉ (voir §6.1) : le titre
    Markdown standard `![alt](src "Légende")` devient un `<figcaption>`
    affiché petit, centré et gris (`var(--ink-muted)`) sous l'image — le style
    par défaut suit donc automatiquement chacun des 9 thèmes. Les légendes
    de **tableaux** restent non planifiées.
22. **Images cliquables** — pas de comportement par défaut aujourd'hui (ex.
    lien vers l'image en taille réelle, ou lightbox JS) ; à ajouter dans
    `nav.js` si lightbox, ou simplement envelopper l'`<img>` dans un `<a>`.
23. **Taille et justification des images réglables** — pas de mécanisme
    dédié aujourd'hui (le style par défaut `.figure` centre l'image et la
    limite à la largeur du contenu ; au-delà, l'auteur passe par le CSS ou
    du HTML brut) ; à concevoir (classes CSS prédéfinies ? syntaxe
    d'attribut sur `![alt](src)` ?).

Les points 22 et 23 demandent des choix de syntaxe qui n'ont pas encore été
tranchés — à spécifier avant implémentation.

---

## 17. Vérification de cohérence

### 17.1 Tous les niveaux sont couverts

- **Série** : `series.json` + génération de l'index + génération de la navigation ✓
- **Article** : fichier `.md` + génération de la page HTML ✓
- **Fiche** : `---` comme séparateur + champs `clé: valeur` + contenu Markdown ✓

### 17.2 Tous les types de fiches sont couverts

- **Cover** : généré depuis les métadonnées ✓
- **Standard** : champs + contenu Markdown + fact-box + highlight ✓
- **Series-nav** : généré depuis `series.json` ✓
- **Full-article** : inclusion d'un fichier `.md` ✓

### 17.3 Toutes les inclusions sont couvertes

- **`.md`** : inclus, converti en HTML, typographié ✓
- **`.html`** : structure de page fixe (§9), pas un template lu depuis un
  fichier — seuls `.css` et `.js` le sont
- **`.css`** : inclus dans `<style>` ✓
- **`.js`** : inclus dans `<script>` ✓
- **`.json`** : `series.json` et `language/*.json` lus et parsés ✓

### 17.4 Toutes les pages calculées sont couvertes

- **Index** : généré depuis `series.json` + template ✓
- **Navigation de série** : générée depuis `series.json` ✓
- **README** : généré depuis `series.json` ✓

### 17.5 Toutes les contraintes sont couvertes

- **UTF-8** : lecture, traitement, écriture ✓
- **HTML autonome** : CSS inline, JS inline ✓
- **Idempotence** : pas de variable non déterministe ✓ (hors `--build-stamp`, opt-in et volontairement horodaté, §11.3.2)
- **Pipeline GitLab CI** : Python 3.12, pas de dépendance externe ✓
- **Langue** : typographie + chaînes d'interface dans des fichiers JSON
  séparés par langue, `fr` et `en` intégrés par défaut, `en` en repli ultime ✓
- **Édition par LLM** : format Markdown lisible et modifiable ✓
- **Exécutable unique** : un seul fichier Python, pas de dépendance externe ✓
- **Install / Demo / Build / Check / Audit / Refresh-templates / Themes-gallery** : commandes séparées ✓
- **Variables d'environnement** : `LWP_SERIES_DIR`, `LWP_ARTICLES_DIR`, etc. ✓
- **Override** : `style.css`/`nav.js` et le fichier de langue sont éditables
  (§9, §7) ; la structure HTML des pages ne l'est pas ✓ (délibérément, §9)

### 17.6 Ce qui n'est PAS couvert (volontairement)

- **Live reload** : pas de serveur de développement ✓ (documenté)
- **Présentation orale** : pas de mode présentateur ✓ (documenté)
- **Multi-langue dans une même page** : une langue par build ✓ (documenté)
- **Images inline** : les images restent en chemin relatif ✓ (documenté)
- **Recherche full-text** : pas de moteur de recherche ✓ (documenté)
- **Commentaires** : pas de système de commentaires de lecteurs (discussion
  publique sur un article publié) — à ne pas confondre avec le champ
  `comment` (§4.6), une note de relecture d'auteur, jamais publiée ✓ (documenté)
- **Analytics** : pas de tracking ✓ (documenté)
- **Citations imbriquées ou multi-paragraphes** ✓ (documenté, §6.3/§15)
- **Coloration syntaxique des blocs de code** ✓ (documenté, §6.3/§15)
- **Échappement générique façon CommonMark** ✓ (documenté, §6.3/§15)

---

## 18. Placeholders de templates

Les templates utilisent des placeholders simples au format `{{nom}}` (double
accolade). Pas de Jinja2, pas de logique conditionnelle, pas de boucles dans
les templates. Le remplacement est fait par `str.replace()` en Python.

### 18.1 Template `page.html`

```html
<!DOCTYPE html>
<html lang="{{lang}}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{{meta_head}}<title>{{title}}</title>
<style>
{{css}}
</style>
</head>
<body>

{{build_stamp}}{{draft_banner}}
<nav class="nav-dots"></nav>

<div class="nav-buttons">
  <div class="nav-btn" id="navPrev" title="{{str_nav_prev}}">&#8593;</div>
  <div class="nav-btn nav-btn-home" id="navHome" title="{{str_nav_home}}">&#127968;</div>
  <div class="nav-btn" id="navNext" title="{{str_nav_next}}">&#8595;</div>
  <div class="nav-btn" id="navShare" title="{{str_share_button}}" aria-label="{{str_share_button_aria}}"><svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 15V4"/><path d="M8 8l4-4 4 4"/><path d="M5 12v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/></svg></div>
</div>

<div class="share-popover" id="sharePopover">
  <!-- matrice 2×3 : copier le lien / afficher le QR code × série / article / fiche, §9.2.1 -->
</div>

<div class="share-qr-modal" id="shareQrModal">
  <!-- QR code SVG généré côté client, §9.2.1 -->
</div>

{{slides}}
{{page_footer}}
<script defer>
{{js_nav}}
</script>

</body>
</html>
```

Placeholders :

| Placeholder | Source | Description |
|-------------|--------|-------------|
| `{{lang}}` | `LWP_LANG` ou `--lang` | Langue de la page (ex. `fr`) |
| `{{title}}` | `page_title` résolu (§20.3.1, sans balises HTML) | Titre de la page |
| `{{css}}` | `templates/style.css` | Le CSS inline |
| `{{slides}}` | Généré par le build | Toutes les `<section class="slide">` |
| `{{js_nav}}` | `templates/nav.js` | Le JS de navigation (scroll, boutons, bouton de partage, encodeur QR) |
| `{{str_KEY}}` | `language/{lang}.json` → `strings` | Chaîne d'interface (voir §7.3), remplacée dans `page.html` **et** dans `js_nav` une fois celui-ci chargé |
| `{{meta_head}}` | `author`/`page_desc` résolus (§20.3.1) | Balises `<meta name="author">` et `<meta name="description">` (débalisées, échappées) — vides toutes deux = rien d'émis |
| `{{page_footer}}` | `author`/`date`/`license` résolus (§20.3.1) | Pied de page éditorial (`<footer class="page-footer">`) — tout absent = rien d'émis |
| `{{build_stamp}}` | `--build-stamp`/`--build-stamp-minimal` (§11.3.2) | Marqueur de fraîcheur du build, vide par défaut |
| `{{draft_banner}}` | `draft` + `--include-drafts` (§20.6) | Bandeau « Brouillon » centré dans l'en-tête, vide hors brouillon |

Il n'y a pas de fichier `share.js` séparé : le bouton de partage, sa matrice
et l'encodeur QR font partie de `nav.js`, leurs propres textes sont des
placeholders `{{str_*}}` comme le reste.

**Accessibilité des boutons ronds.** Les quatre boutons de navigation
(précédent, accueil, suivant, partage — et de même les trois de l'index)
sont des `<div class="nav-btn">` porteurs de `role="button"`,
`tabindex="0"`, d'un `aria-label` (en plus du `title`), et d'un style
`:focus-visible`. `nav.js` (et le JS de l'index) leur ajoute une
activation clavier Entrée/Espace équivalente au clic — sans quoi le
bouton de partage, qui n'a pas d'autre point d'entrée clavier, serait
inatteignable au clavier. Le parcours de lecture lui-même reste piloté
par les flèches au niveau document (§9.2.2).

### 18.2 Template `index.html`

```html
<!DOCTYPE html>
<html lang="{{lang}}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title>
<style>
{{css}}
</style>
</head>
<body style="padding: 60px 8vw; max-width: 1200px; margin: 0 auto;">

{{build_stamp}}
<div class="header">
  <h1>{{series_title}}</h1>
  <p class="subtitle">{{series_subtitle}}</p>
  <span class="version-tag">{{series_version}}</span>
</div>

<div class="intro">
  <p>{{series_intro}}</p>
</div>

{{cards}}
{{index_footer}}
<div class="nav-buttons">
  ...
</div>

<script>
{{js_index}}
</script>

{{index_extra}}
</body>
</html>
```

Placeholders supplémentaires :

| Placeholder | Source | Description |
|-------------|--------|-------------|
| `{{series_title}}` / `{{series_subtitle}}` / `{{series_version}}` | `series_meta` de `series.json` | En-tête de l'index (markup fixe, pas un placeholder unique). Sans `version`, le `<span class="version-tag">` entier est omis — pas de pastille vide |
| `{{series_intro}}` | `series_meta.intro` (seule source) | Paragraphe d'intro de l'index |
| `{{cards}}` | Généré depuis `series.json` | Les cartes d'articles |
| `{{index_footer}}` | `series_meta.author`/`series_meta.license` (§20.3.1) | Pied de page éditorial de la série — tout absent = rien d'émis |
| `{{js_index}}` | Généré, intégré à l'exécutable | Le JS spécifique à l'index (scroll) — pas overridable (§9). Pas de bouton de partage sur l'index (§9.2.1) |
| `{{index_extra}}` | `templates/index_extra.html` s'il existe | Fragment HTML libre inséré tel quel en fin de `<body>` |
| `{{build_stamp}}` | `--build-stamp`/`--build-stamp-minimal` (§11.3.2) | Marqueur de fraîcheur du build, vide par défaut |
| `{{str_KEY}}` | `language/{lang}.json` → `strings` | Infobulles `index_nav_up`/`index_nav_home`/`index_nav_down`, voir §7.3 |

### 18.3 Fragments de la slide series-nav

Il n'y a **pas** de template `series-nav.html` à placeholders `{{...}}` :
la `<section>` de navigation est produite par le rendu de slides avec un
marqueur interne littéral (`{SERIES_NAV_PLACEHOLDER}`), remplacé lors de
l'assemblage de la page par le bloc généré — c'est ce qui permet au bloc
d'être calculé par article (l'item « courant » diffère) sans re-rendre
les slides. Les items eux-mêmes sont des fragments internes au format
`str.format` Python (champs à **simple** accolade) :

| Fragment | Champs | Rôle |
|----------|--------|------|
| item lien | `{file}` `{label}` `{title}` `{desc}` `{read}` | Un autre article de la série (lien) |
| item courant | `{label}` `{title}` `{desc}` `{status}` | L'article en cours de lecture (pas un lien) |
| retour index | `{back}` | Lien « Retour à l'index » en fin de liste |

`label`/`title`/`desc` sont `card_label`/`nav_title`/`nav_desc` résolus
(§20.3.1) et typographiés ; `read`/`status`/`back` viennent des chaînes
`series_read`/`series_current_status`/`series_back_to_index` (§7.3).
Le `<div class="series-label">` d'un item est omis quand le
`card_label` résolu est vide (pas de div vide), comme le
`<div class="article-number">` des cartes d'index. Le titre du bloc
utilise la chaîne `series_nav_title`.

### 18.4 Règles de remplacement

- Les chaînes d'interface (`{{str_KEY}}`, §7.3) sont appliquées au
  **squelette seulement**, avant toute injection de contenu : au template
  de page/d'index d'abord, à `nav.js` et `index_extra.html` à leur
  chargement (ce sont des fichiers de template, pas du contenu). Un
  `{{str_KEY}}` écrit littéralement par un auteur dans son contenu
  (fiche, article de fond, `series_meta`) reste donc **littéral** dans la
  page publiée — la mécanique interne ne fuit jamais dans l'espace de
  contenu.
- Page article, ordre réel : chaînes sur le template, puis `{{lang}}`,
  `{{title}}`, `{{meta_head}}`, `{{css}}`, `{{slides}}`,
  `{{page_footer}}`, `{{js_nav}}`, `{{build_stamp}}`,
  `{{draft_banner}}`.
- Index, ordre réel : chaînes sur le template et sur `index_extra`, puis
  `{{lang}}`, `{{title}}`, `{{css}}`, `{{series_*}}`, `{{cards}}`,
  `{{index_footer}}`, `{{js_index}}`, `{{index_extra}}`,
  `{{build_stamp}}`.
- Si un placeholder n'est pas trouvé dans le template, il est ignoré (pas
  d'erreur). Cela permet d'avoir des templates plus simples sans tous les
  placeholders.
- Les placeholders sont sensibles à la casse : `{{title}}` ≠ `{{Title}}`.
- Pas d'échappement : le contenu remplacé est du HTML prêt à l'emploi.

---

## 19. Schéma du fichier de langue (`fr.json`)

Le fichier de langue décrit deux choses indépendantes pour une langue donnée
(§7) : les règles de remplacement de caractères à appliquer sur tout le
texte généré (`rules`, des **expressions régulières** Python), et le
vocabulaire fixe des templates par défaut (`strings`).

### 19.1 Structure du fichier

```json
{
  "lang": "fr",
  "name": "Français",
  "rules": [
    {
      "name": "nbsp_before_double_punctuation",
      "description": "Espace insécable avant : ; ! ? et »",
      "pattern": " ([!?;:»])",
      "replacement": " $1",
      "flags": "g"
    },
    {
      "name": "nbsp_after_opening_quote",
      "description": "Espace insécable après «",
      "pattern": "(«) ",
      "replacement": "$1 ",
      "flags": "g"
    },
    {
      "name": "nbsp_before_percent",
      "description": "Espace insécable avant %",
      "pattern": " %",
      "replacement": " %",
      "flags": "g"
    },
    {
      "name": "nbsp_thousands_separator",
      "description": "Espace insécable entre groupes de 3 chiffres d'un nombre déjà séparé par des espaces (§7.5)",
      "pattern": "(?<=\\d) (?=\\d{3}(?!\\d))",
      "replacement": " ",
      "flags": "g"
    },
    {
      "name": "nbsp_before_unit",
      "description": "Espace insécable entre un nombre et million(s)/milliard(s)/dollar(s)/$ (§7.5)",
      "pattern": "(?<=\\d) (?=(?:millions?|milliards?|dollars?)\\b|\\$)",
      "replacement": " ",
      "flags": "g"
    },
    {
      "name": "nbsp_after_operator",
      "description": "Espace insécable entre × ou ≈ et le nombre qui suit (§7.5)",
      "pattern": "(?<=[×≈]) (?=\\d)",
      "replacement": " ",
      "flags": "g"
    }
  ],
  "strings": {
    "nav_prev": "Planche précédente",
    "copy_link": "Copier le lien"
  }
}
```

Les six règles ci-dessus sont exactement celles du pack `fr` intégré (§7.5) —
contrairement à l'exemple de §7.1 (illustratif), celui-ci reflète le
contenu réel embarqué dans l'exécutable.

### 19.2 Champs

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| `lang` | string | non* | Code de langue (ex. `fr`, `en`) |
| `name` | string | non | Nom affichable (ex. « Français ») |
| `rules` | array | non* | Liste des règles à appliquer, dans l'ordre |

\* Aucun champ n'est exigé d'un fichier de **surcharge** : un fichier
chargé via `--language-file` ou `language/<lang>.json` est **fusionné**
avec le pack embarqué de base (sélectionné par `--lang`, anglais si la
langue n'est ni `fr` ni `en`). Sémantique : `rules` présent remplace les
règles de base **en bloc** (absent = règles de base) ; `strings` est
fusionné **clé par clé** par-dessus les chaînes de base (un fichier
partiel ne définit que ce qu'il change) ; `lang`/`name` absents
retombent sur le pack de base. Erreurs fatales : JSON invalide, racine
non-objet, `rules` non-liste, `strings` non-objet, `--language-file`
introuvable. Les packs embarqués, eux, portent évidemment tout.
| `rules[].name` | string | non | Nom court de la règle (pour le debug) |
| `rules[].description` | string | non | Description humaine |
| `rules[].pattern` | string | oui | Regex Python (sans délimiteurs) |
| `rules[].replacement` | string | oui | Remplacement (avec `$1`, `$2` pour les groupes) |
| `rules[].flags` | string | non | Flags regex, défaut `g`. Supportés : `g` (toutes les occurrences ; sans lui, seule la **première** occurrence par segment de texte est remplacée) et `i` (insensible à la casse). Tout autre caractère : erreur fatale |
| `strings` | object | non | Chaînes d'interface, clé → valeur (voir §7.3 pour la liste des clés) |

### 19.3 Règles d'application

- Les règles (`rules`) sont appliquées **dans l'ordre** du tableau.
- Elles sont appliquées **après** la conversion Markdown → HTML, sur le texte
  HTML final (y compris les balises).
- Les règles ne peuvent **pas** modifier les balises HTML ni les attributs :
  le moteur découpe le HTML en segments balise / texte (`<[^>]+>` vs le
  reste) avant d'appliquer les regex, et ne les applique que sur les
  segments de texte — structurellement, pas par accident de rédaction des
  règles actuelles.
- Les règles ne s'appliquent pas non plus au **contenu** de `<code>`/
  `<pre>` (§6.3) : le moteur suit la profondeur d'imbrication de ces deux
  balises et saute tout segment de texte compris à l'intérieur, pour
  qu'un exemple de code ou une commande citée ne voie jamais son
  espacement modifié silencieusement.
- L'application est **idempotente** : appliquer les règles deux fois ne change
  rien (les insécables déjà présentes ne sont pas doublées).
- Les chaînes d'interface (`strings`), elles, ne passent pas par ce moteur de
  règles : elles sont substituées telles quelles via les placeholders
  `{{str_KEY}}` (§18).

### 19.4 Fichier `en.json` (anglais)

L'anglais a des règles typographiques plus simples (pas d'insécables avant
la ponctuation, pas de guillemets français), mais un bloc `strings` tout
aussi complet que le français — c'est lui qui sert de repli ultime (§7.1,
§7.4) :

```json
{
  "lang": "en",
  "name": "English",
  "rules": [],
  "strings": {
    "nav_prev": "Previous slide",
    "copy_link": "Copy link"
  }
}
```

Le tableau `rules` est vide car l'anglais n'a pas de règles typographiques
spéciales à appliquer sur le texte généré.

### 19.5 Packs par défaut embarqués dans l'exécutable

L'exécutable contient en interne les packs `fr` et `en` (règles + chaînes)
sous forme de strings JSON. La commande `install` les extrait dans
`language/fr.json` et `language/en.json`. L'utilisateur peut ensuite les
modifier — en partie pour `strings` (§7.4).

Au moment du build, le moteur charge le pack de langue depuis :
1. `--language-file chemin/vers/fichier.json` (option CLI, priorité max) —
   erreur fatale si le fichier n'existe pas
2. `$LWP_LANGUAGE_DIR/$LWP_LANG.json` (variables d'environnement)
3. `$LWP_SERIES_DIR/language/$LWP_LANG.json` (défaut)
4. Le pack intégré à l'exécutable pour `$LWP_LANG` (`fr` ou `en`), ou le pack
   anglais intégré si `$LWP_LANG` ne correspond à aucun pack connu (repli
   ultime, §7.1)

### 19.6 Désactivation complète (`--no-typography`)

`--no-typography`, sur `build` et `check` (§11.3/§11.4), saute entièrement
le chargement d'un moteur de règles pour ce lancement — aucune règle,
qu'elle vienne du pack intégré ou d'un override (§7.4/§19.5), ne s'exécute
sur aucun article ni sur l'index, pour toute la durée de ce build. C'est
la portée la plus large des trois mécanismes de désactivation (§4.5) :
`typo-units`/`typo-thousands` ne visent qu'une paire de règles nommées,
`typo: off` vise déjà toutes les règles mais pour un seul article, `--no-
typography` les vise toutes pour tout le build — y compris toute règle qui
serait ajoutée plus tard, puisque le mécanisme ne construit simplement pas
de moteur du tout plutôt que d'énumérer des noms de règles à exclure.

---

## 20. Schéma formel de `series.json`

### 20.1 Structure

```json
{
  "series_meta": {
    "title": "Les classiques de la pâtisserie",
    "subtitle": "Une série d'articles sur les techniques, les proportions et les erreurs à éviter",
    "version": "v0.1",
    "intro": "« Une pâte trop travaillée devient élastique. » « Le sucre n'est pas qu'une question de goût. » ..."
  },
  "articles": [
    {
      "page_source": "tarte-aux-pommes.md"
    },
    {
      "page_source": "creme-patissiere.md",
      "card_label": "Article 2 : Les classiques (corrigé)"
    }
  ]
}
```

Un article est **auto-décrit** : à part `page_source`, aucun champ n'est
requis dans `series.json` — un article se suffit à lui-même. Le premier
article ci-dessus n'a que ce seul champ structurel : `page_dest` se déduit
de `tarte-aux-pommes.md` (→ `tarte-aux-pommes.html`), et `page_title`/
`page_desc`/`nav_title`/`nav_desc`/`card_title`/`card_desc`/`card_label`
sont lus depuis le bloc meta de `tarte-aux-pommes.md`, ou à défaut
extrapolés de son contenu (cover, §20.3.1). Le second illustre une
surcharge : `card_label` prend le pas sur celui du bloc meta de
`creme-patissiere.md` sans y toucher — les autres champs d'affichage de
cet article restent lus depuis son propre bloc meta ou son propre contenu.

Nommage (gel v1.0) : la famille `page_*` regroupe tout ce qui concerne la
page compilée — sa source (`page_source`), son fichier de destination
(`page_dest`), son titre (`page_title`), sa description (`page_desc`). Les
anciens noms `source`/`file` (avant v1.0) produisent une erreur explicite
de migration, pas un « champ manquant » incompréhensible. Le champ de
fiche `source` (citation, §4.3) est sans rapport et n'a pas changé.

### 20.2 Champs des articles

| Champ | Type | Obligatoire dans `series.json` | Utilisé par | Description |
|-------|------|-------------|------------|-------------|
| `page_source` | string | oui | build | Nom du fichier `.md` source dans `articles/` |
| `page_dest` | string | non | build, index, nav | Nom du fichier HTML de sortie ; déduit de `page_source` si absent (§20.3.1) |
| `page_title` | string | non | balise `<title>` de la page de l'article | Titre de la page HTML de l'article ; surcharge celui du bloc meta (§20.3.1) |
| `page_desc` | string | non | `<meta name="description">` de la page | Description de la page (SEO/aperçu de partage) ; surcharge celle du bloc meta (§20.3.1) — jamais affichée dans l'interface visible |
| `card_title` | string | non | index | Titre de la carte d'index ; surcharge celui du bloc meta (§20.3.1) |
| `card_desc` | string | non | index | Description de la carte d'index ; surcharge celle du bloc meta (§20.3.1) |
| `card_label` | string | non | index, nav | Étiquette libre sur la carte d'index et dans le bloc « Cette série » — texte, pas un numéro ; surcharge celle du bloc meta (§20.3.1) |
| `nav_title` | string | non | nav (carte de navigation intra-article) | Titre affiché quand cet article apparaît dans la navigation d'un autre article ; surcharge celui du bloc meta (§20.3.1) |
| `nav_desc` | string | non | nav | Description affichée dans ce même contexte ; surcharge celle du bloc meta (§20.3.1) |
| `author` | string | non | pied de page de l'article + `<meta name="author">` | Auteur de l'article ; surcharge le bloc meta, qui surcharge le défaut `series_meta.author` (§20.3.1) |
| `license` | string | non | pied de page de l'article | Licence du contenu ; même cascade que `author` (défaut `series_meta.license`) ; HTML brut autorisé (lien) |
| `date` | string | non | pied de page de l'article (signature) | Date affichée telle quelle (texte libre) ; surcharge le bloc meta ; jamais déduite du mtime (§20.3.1) |
| `draft` | bool/string | non | build/check | `true` = brouillon, exclu du build sauf `--include-drafts` (§20.6) |
| `comment` | string | non | aucun — jamais lu | Note de relecture ; ignorée par le build (§4.6) |

### 20.3 Règles de validation

- Le tableau `articles` est **ordonné** : l'ordre des entrées définit l'ordre
  des articles dans la navigation et l'index.
- Les anciens noms `source`/`file` (retirés au gel v1.0) produisent une
  **erreur fatale de migration explicite** (« renommé en page_source/
  page_dest à la v1.0 »), détectée avant toute autre validation.
- `page_dest` (une fois résolu, §20.3.1) doit être unique dans le tableau
  (pas de doublons) — erreur fatale sinon.
- `page_source` est **obligatoire** et doit être non vide sur chaque entrée —
  erreur fatale sinon, avec l'index de l'entrée en cause. `page_dest` ne
  l'est **pas** : absent, il se déduit de `page_source` (§20.3.1). Aucun
  autre champ n'est obligatoire *dans `series.json`* — les champs
  d'affichage et éditoriaux se résolvent selon §20.3.1.
- `page_source` doit être un simple nom de fichier, sans séparateur de
  chemin ni `..` — erreur fatale sinon. Même règle pour `page_dest` quand
  il est donné explicitement (dans `series.json` ou le bloc meta de
  l'article) — `series.json` est une donnée éditable par un LLM ou une CI
  non surveillée (§13.5) ; sans cette validation, une valeur comme
  `/etc/passwd` ou `../../.ssh/id_rsa` serait jointe telle quelle au
  répertoire attendu (`Path(dir) / valeur` ignore silencieusement `dir`
  quand `valeur` est un chemin absolu) et permettrait une lecture ou une
  écriture de fichier arbitraire hors de `articles/`/`public/`.
- `page_source` doit se terminer par `.md` (insensible à la casse) et
  `page_dest` (une fois résolu, qu'il soit explicite ou déduit) par `.html`
  ou `.htm` (insensible à la casse) — erreur fatale sinon, avec le même
  traitement que le contrôle de sécurité ci-dessus : sans ça, une valeur
  comme `"page_dest": "a.md"` construit sans avertissement un `public/a.md`
  contenant du HTML rendu, une extension de sortie incohérente qu'aucun
  choix éditorial ne justifie. `.htm` est accepté au même titre que
  `.html` : extension standard, toujours utile sur les systèmes de fichiers
  limités à trois lettres (FAT 8.3 et dérivés, certains hébergements ou
  environnements embarqués) ; la restreindre à `.html` seul briserait cet
  usage sans apport de sécurité, le risque visé (extension de sortie
  incohérente) étant identique pour toute extension qui n'est ni l'une ni
  l'autre.
- `page_source` doit pointer vers un fichier qui existe dans `articles/` —
  sinon **erreur fatale**, pour `build` comme pour `check`, vérifiée en
  amont avant toute écriture (aucune sortie partielle). Un article
  volontairement absent du build a son mécanisme dédié : `draft: true`
  (§20.6). `audit`, non bloquant par contrat, signale le fichier
  manquant et continue.

#### 20.3.1 Résolution des champs (surcharge et déduction de contenu)

À part `page_source`, aucun champ n'est jamais requis dans `series.json`
lui-même : chacun a une valeur par défaut, lue dans le bloc meta de
l'article correspondant (même nom de champ — ex. `card_title:` dans le
`.md`, §4.2), et `series.json` ne sert qu'à la corriger pour un article
donné, sans toucher au fichier source. Quand le bloc meta ne le précise
pas non plus, chaque champ retombe sur une valeur **extrapolée du contenu
déjà écrit** par l'auteur (ou, pour les champs éditoriaux, héritée de
`series_meta`), plutôt que d'exiger une saisie redondante :

```
page_dest   : series.json  >  meta (page_dest:)     >  page_source, .md → .html
page_title  : series.json  >  meta (page_title:)    >  slide_title de la fiche cover  >  page_dest (résolu)
page_desc   : series.json  >  meta (page_desc:)     >  summary de la fiche cover  >  balise omise
card_title  : series.json  >  meta (card_title:)    >  page_title (résolu)
card_desc   : series.json  >  meta (card_desc:)      >  summary de la fiche cover
card_label  : series.json  >  meta (card_label:)     >  '' (rien à en extrapoler)
nav_title   : series.json  >  meta (nav_title:)      >  card_title (résolu)
nav_desc    : series.json  >  meta (nav_desc:)       >  card_desc (résolu)
author      : series.json  >  meta (author:)         >  series_meta.author   >  '' (rien d'affiché)
license     : series.json  >  meta (license:)        >  series_meta.license  >  '' (rien d'affiché)
date        : series.json  >  meta (date:)           >  '' (rien d'affiché — jamais le mtime)
```

Ordre de résolution, pour chaque champ, du plus prioritaire au moins
prioritaire :

1. **`series.json`**, l'entrée de l'article dans `articles[]`, si le champ y
   est présent et non vide.
2. **Le bloc meta de l'article**, le champ de même nom, si présent et non
   vide.
3. **Repli**, selon le tableau ci-dessus, si absent des deux niveaux
   précédents. Rien dans cette chaîne n'est une erreur fatale : chaque
   champ finit toujours par se résoudre à quelque chose, au pire le nom de
   fichier lui-même ou une valeur vide (rendu alors simplement omis).
   `audit` (§11.5) signale un article dont `page_desc` reste vide partout
   (page publiée sans `<meta name="description">`) — avertir plutôt que
   substituer.

La chaîne des titres se chaîne (nav_title → card_title → page_title →
contenu de la fiche cover) parce qu'elle reflète des contextes d'affichage
réellement distincts, pas une redondance : `card_title`/`card_desc`
pilotent la carte de la page d'index, `nav_title`/`nav_desc` la carte de
navigation affichée **dans la page d'un autre article** — un lecteur peut
donc voir un texte différent selon qu'il découvre l'article depuis l'index
ou depuis la navigation d'un article voisin, sans avoir à ressaisir la
même information deux fois si la distinction n'est pas utile.

**Les descriptions, elles, ne se chaînent PAS entre elles — asymétrie
intentionnelle.** `page_desc` et `card_desc` sont deux branches parallèles
issues du même summary de cover, jamais l'une de l'autre : `page_desc` est
une métadonnée invisible (SEO, aperçu de partage), `card_desc` de
l'interface visible. Chaîner `card_desc` sur `page_desc` ferait fuiter un
texte optimisé pour le référencement sur les cartes d'index visibles. Ne
pas « corriger » cette asymétrie.

**Champs éditoriaux (`author`/`license`/`date`) et leurs rendus.** Nouveau
motif de cascade : l'article se replie sur un défaut *de série*
(`series_meta.author`/`series_meta.license` — pas de défaut de série pour
`date`, propre à chaque article). Contrairement aux champs d'affichage
ci-dessus, ils sont rendus hors des fiches :

- `author` + `date` : signature discrète en pied de la page de l'article
  (`<footer class="page-footer">`, « Auteur — date ») ; `author` alimente
  aussi `<meta name="author">` (débalisé et échappé — contexte attribut).
- `license` : mention en pied de la page de l'article ; HTML brut autorisé
  (un lien vers la licence, §6.2).
- La page d'index porte son propre pied de page avec les valeurs **de
  série** (`series_meta.author`/`series_meta.license`) — les valeurs par
  article restent sur les pages des articles.
- `date` est affichée **telle quelle** (texte libre) et n'est jamais
  déduite du mtime du fichier : le build resterait sinon non reproductible
  octet par octet, ce sur quoi `check` (§11.4) repose.
- Ces champs traversent le moteur typographique comme tout contenu visible ;
  absents partout, aucun pied de page n'est émis (pas de bloc vide).

### 20.4 Métadonnées de la série (`series_meta`)

Le fichier `series.json` peut contenir un objet `series_meta` (optionnel)
qui décrit la série elle-même (pour l'index et le README) :

Si `series_meta` est présent, le fichier a deux clés : `series_meta` (objet) et
`articles` (tableau). Si `series_meta` est absent, le fichier est un tableau
direct (rétrocompatible avec un format de série déjà utilisé).

### 20.5 Champs de `series_meta`

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| `title` | string | non | Titre de la série sur la page d'index ; replié sur `strings.series_untitled_fallback` (« Article series » / « Série d'articles », §7.3) si absent — jamais une erreur, `series_meta` lui-même étant optionnel |
| `subtitle` | string | non | Sous-titre sur la page d'index |
| `version` | string | non | Version affichée (ex. `v0.13`) |
| `intro` | string | non | Paragraphe d'introduction de l'index |
| `author` | string | non | Auteur par défaut de toute la série (§20.3.1) ; affiché en pied de la page d'index, et sur chaque article qui ne le surcharge pas |
| `license` | string | non | Licence par défaut de toute la série (§20.3.1) ; même affichage que `author` ; HTML brut autorisé (lien) |
| `comment` | string | non | Note de relecture sur la série entière ; ignorée par le build (§4.6) |

Le template d'index enveloppe `intro` dans un unique `<p>` fixe
(`<p>{{series_intro}}</p>`) : pour plusieurs paragraphes, insérer
`</p>\n<p>` dans la valeur — HTML brut passthrough, cohérent avec le
reste (§6.2).

### 20.6 Statut brouillon (`draft`)

`draft: true` (booléen JSON ou chaîne `"true"`, insensible à la casse ;
**toute autre valeur = pas brouillon**) marque un article comme brouillon.
Posable dans l'entrée `series.json` ou le bloc meta de l'article ;
`series.json` prioritaire — y compris avec une valeur explicitement
fausse : `"draft": false` dans `series.json` l'emporte sur un
`draft: true` resté dans le bloc meta.

Par défaut, un article brouillon est **entièrement exclu** du build : pas
de page générée, pas de carte d'index, pas d'entrée dans le bloc « Cette
série » des autres articles — comme s'il n'était pas listé (un message
informatif `[draft] x.html skipped` le rappelle). `--include-drafts`
(build **et** check) construit tout, chaque page brouillon portant alors
le bandeau décrit en §11.3. `audit`, lui, n'exclut jamais les brouillons :
c'est un outil d'écriture, le travail en cours est précisément ce qu'il
doit regarder.

---

## 21. Cas de validation informel (contenu privé, hors dépôt)

Un cas de validation réel est disponible en local dans
`lightwebpres/private/series/` — **le répertoire `private/` n'est pas
versionné** (voir `.gitignore`) : c'est du vrai contenu éditorial personnel,
pas une fixture de test destinée au dépôt public. `private/` ne contient pas
directement les fichiers de la série : il héberge un répertoire de série à
part entière, au sens de §2.2 (`serie/`, avec ses propres `series.json`,
`articles/`, `public/`) — ce qui laisse la place, si besoin, à d'autres
contenus privés sans les mélanger à la racine.

- `private/series/series.json` — une entrée (YouTube) avec `series_meta`
- `private/series/articles/youtube.md` — l'article au format Markdown étendu
  (8 fiches + navigation + article complet)
- `private/series/articles/youtube_article.md` — l'article de fond inclus

Ce contenu sert de **vérité terrain informelle** pour valider le moteur de
build en local. Le build doit produire un HTML équivalent au `youtube.html`
actuel (à la typographie près, qui peut varier légèrement selon les règles
appliquées). Ce n'est pas la suite de régression du projet — celle-ci vit
dans `tests/` (fixtures génériques, versionnées, voir §11). À terme, une
fois la commande `demo` fiabilisée, elle pourra remplacer ce contenu privé
comme procédure de validation de référence.

Le cas test n'est pas un template : c'est un fichier réel, avec du vrai
contenu, qui exerce tous les types de slides (cover, standard avec highlight,
standard sans highlight, series-nav, full-article), tous les champs (tag, summary,
fact-label, source, highlight, highlight-caption), et l'inclusion d'un article
complet avec footnotes (`[^N]`), tableaux, listes, gras et italique.

---

## 22. Cas limites du parseur

### 22.1 Séparateur `---` dans le corps d'une fact-box

Si `---` apparaît seul sur une ligne dans le texte d'une fact-box, c'est un
séparateur de slide (thematic break Markdown). Pour inclure un trait
horizontal dans le texte, utiliser `<hr>` en HTML inline.

### 22.2 `tag:` dans le texte d'une fact-box

Les métadonnées (`tag:`, `summary:`, `fact-label:`, `source:`, `highlight:`,
`highlight-caption:`, `article:`) ne sont reconnues que **dans l'en-tête** de la
slide (les premières lignes avant le premier paragraphe de contenu). Une fois
que le parseur a rencontré une ligne de contenu (paragraphe, liste, titre), il
cesse de chercher des métadonnées.

Cette règle s'applique aussi aux titres `# `/`## ` (`slide_title`,
GLOSSARY.md) : un `## Sous-titre` qui apparaît **après** le début du
contenu (donc dans le corps de la fact-box, pas dans l'en-tête de la
slide) est du texte de contenu — un titre Markdown normal dans le rendu
de la fact-box — et non une nouvelle valeur pour le titre de la slide.

Deux précisions sur ce qui compte comme « avant tout contenu », toutes deux
là pour permettre à un fact-box de **commencer directement** par un titre
sans que celui-ci soit avalé comme titre de la slide :

- **Un seul `#`/`## ` peut définir le titre d'une slide donnée.** Une fois
  que `slide.h1` (cover) ou `slide.h2` (non-cover) a déjà été assigné une
  première fois, un second `#`/`## ` rencontré avant tout autre contenu
  bascule immédiatement en texte de contenu, au lieu d'écraser
  silencieusement le titre déjà défini.
- **Le niveau qui ne correspond pas au type de la slide ne définit jamais de
  titre.** `#` ne définit un titre que sur une fiche `cover` ; `## ` ne
  définit un titre que sur une fiche non-`cover` (`render_slide()` traite
  tout `slide_type` autre que `cover` comme standard, y compris un type
  inconnu — non validé, §11.5 — donc le parseur suit la même règle). Un
  `## ` sur une fiche `cover`, ou un `#` sur une fiche non-`cover`, bascule
  donc immédiatement en contenu dès sa première occurrence — sans cette
  règle, un tel titre serait capturé dans un attribut que le rendu ne lit
  jamais pour ce type de fiche, et disparaîtrait silencieusement au lieu de
  devenir un titre visible dans le fact-box.

### 22.3 Slide sans `tag:`

Autorisé. Le tag est omis dans le HTML (pas de `<span class="slide-tag">`).

### 22.4 Slide `cover` sans `summary:`

Autorisé. Le summary est omis dans le HTML.

### 22.5 Fichier `.md` sans `<!-- lwp:slide:full-article -->`

Autorisé. La page ne contient que des fiches, sans article de fond.

### 22.6 Fichier `.md` avec `<!-- lwp:slide:full-article -->` mais sans `article:`

Erreur fatale. Le build s'arrête avec un message indiquant le fichier et le
numéro de slide. Même chose si `article:` est présent mais n'est pas un
simple nom de fichier (séparateur de chemin ou `..` détecté) — même risque
de lecture de fichier arbitraire que pour `page_dest`/`page_source` dans
`series.json` (§20.3).

### 22.7 Contenu avant `<!-- lwp:meta -->` (y compris un `---`)

Erreur fatale. Le fichier doit commencer par `<!-- lwp:meta -->` ; seules
des lignes vides peuvent précéder le marqueur (un BOM est absorbé à la
lecture, §13.1). Le message d'erreur cite le début du contenu fautif.

### 22.8 Plusieurs `<!-- lwp:slide:full-article -->` dans le même fichier

Erreur fatale. Un article ne peut inclure qu'un seul article de fond.
Le fichier référencé par `article:` doit exister — sinon erreur fatale
aussi (la page serait sinon publiée avec le texte littéral du
placeholder à la place de l'article).

### 22.9 Plusieurs `<!-- lwp:slide:series-nav -->` dans le même fichier

Erreur fatale. Un article ne peut contenir qu'une seule navigation de série.

### 22.9.1 Contenu non reconnu dans une fiche `series-nav` ou `full-article`

Erreur fatale. Ces deux types de fiche ne rendent **aucun** contenu
propre : leurs seules lignes reconnues sont leurs directives —
`article:` (fiche `full-article` uniquement) et `comment:` (§4.6,
reconnu sur tout type, jamais rendu). Toute autre ligne non vide
(du texte, un champ de fiche standard, un `article:` sur une
`series-nav`...) arrête le build avec un message citant le début de la
ligne fautive, plutôt que de disparaître silencieusement du rendu.

### 22.10 Fichier `.md` vide (aucune slide)

Erreur fatale. Le fichier doit contenir au moins une slide.

### 22.11 Retour à la ligne sans ligne vide à l'intérieur d'un paragraphe

Autorisé, et non significatif : les lignes concernées appartiennent au même
paragraphe et sont fusionnées (§6.1). Ce n'est ni une nouvelle fiche, ni un
nouveau paragraphe, ni une erreur — c'est le comportement Markdown standard.
Ne pas confondre avec un champ LWP (`summary:`, `tag:`...), qui lui ne
tolère aucune continuation (§4.1) : une ligne suivant un champ sans être
elle-même un champ reconnu bascule immédiatement en texte libre.

### 22.12 Contenu inattendu après les champs reconnus d'une fiche `cover`

Erreur fatale. Une fiche `cover` n'a pas de fact-box : `tag`, `slide_title`
(écrit `# Titre`), `summary` et `comment` (§4.6, jamais rendu) sont ses
seuls champs. Si du texte suit ces champs sans être lui-même un champ
reconnu, le build s'arrête avec un message indiquant le fichier et le
numéro de fiche, plutôt que d'ignorer silencieusement ce texte.

Cas voisin, traité plus doucement : les **champs** de fiche standard
posés sur une cover (`fact-label`, `source`, `highlight`,
`highlight-caption`) sont parsés mais jamais rendus — **avertissement**
au build, pas d'erreur. Basculer une fiche entre standard et cover
pendant l'écriture est un aller-retour normal ; l'avertissement signale
la perte d'affichage sans casser la source.

### 22.13 Nombre et position des fiches `cover`

Libre, volontairement non validé par `build`. `cover` est un style de mise
en page, pas un repère structurel : 0, 1 ou plusieurs fiches `cover` sont
autorisées, dans n'importe quelle position (voir §4.4). `build` ne signale
ni l'absence de `cover`, ni une position autre que la première — cette
vérification, purement éditoriale et non bloquante, est du ressort de la
commande `audit` (§11.5), pas du `build`.

### 22.14 Bloc HTML brut multi-lignes ouvert par une balise inline

Une ligne qui ouvre une balise inline (`<a>`, `<span>`...) sans la refermer
sur cette même ligne — par exemple une carte cliquable faite main,
`<a href="..." class="card">` suivie de plusieurs lignes (`<img>`,
légende...) avant `</a>` — reste un bloc HTML brut multi-lignes : §6.2
s'applique par profondeur de balise, pas ligne par ligne. Concrètement,
toute ligne à l'intérieur d'un tel bloc encore ouvert est passée telle
quelle, même si elle a l'air, prise isolément, d'un usage inline
autonome (`<span class="caption">...</span>` sur sa propre ligne, par
exemple) — la profondeur d'imbrication du bloc en cours prime sur
l'apparence de chaque ligne individuelle.

### 22.15 Bloc de code ouvert sans être refermé

Une ligne ` ``` ` sans ` ``` ` fermante avant la fin du fichier : tout ce
qui suit, y compris le reste du fichier, est absorbé comme contenu de
code au lieu d'être interprété (§6.3) — pas de détection anticipée de
fin de fichier dans le convertisseur lui-même. La balise `<pre><code>`
ouverte sans fermeture correspondante est détectée comme n'importe quelle
autre balise non refermée par la vérification de balisage qui précède
l'écriture de la page (§13), qui fait échouer le build — le même filet
de sécurité générique, pas un cas spécial.

### 22.16 `>` qui n'est pas en tout début de ligne

`>` n'a de sens de citation qu'en toute première position d'une ligne
(§6.3). Ailleurs dans une phrase — « la valeur est > 10 », par exemple —
il n'a jamais été un déclencheur et s'affiche tel quel, sans qu'aucun
échappement ne soit nécessaire.

### 22.17 Backtick isolé (sans backtick fermant sur la même ligne)

Un seul backtick sur une ligne, sans second backtick pour former une
paire, ne déclenche pas de span de code (§6.3) : la regex de
correspondance exige les deux délimiteurs sur la même ligne logique.
Le backtick s'affiche tel quel, sans échappement nécessaire — seul un
backtick qui *formerait* effectivement une paire, mais qu'on veut
littéral, a besoin d'un `` \` ``.

---

## 23. Version navigateur (`web/`)

En plus de l'exécutable console, une seule page statique, `web/index.html`,
permet de construire une série **entièrement dans le navigateur**, sans
rien installer, sous deux onglets qui couvrent chacun un flux complet :
« Upload a zip » (dépose un zip de la série, récupère un zip de `public/`)
et « Sync with GitLab » (pull → build → push directement contre un dépôt,
§23.9). Un serveur HTTP minimal reste nécessaire pour ouvrir la page
elle-même — voir §23.6.

### 23.1 Principe

`web/index.html` charge [Pyodide](https://pyodide.org) (CPython compilé en
WebAssembly) une seule fois, au chargement de la page, quel que soit
l'onglet actif, et y exécute le fichier `lightwebpres` **tel quel** —
aucune duplication de logique, `lightwebpres` reste l'unique source de
vérité, il n'en existe donc pas de copie versionnée dans `web/` — puis les
deux scripts de colle des deux onglets, `web/app.py` (dézippe un zip
envoyé, appelle `cmd_build()`, rezippe `public/`) et `web/git_sync.py`
(§23.9), chargés tous les deux dès le départ pour que passer d'un onglet à
l'autre soit instantané, sans rechargement. `lightwebpres` est cherché à
deux emplacements conventionnels relatifs à la page, `./lightwebpres` puis
`../lightwebpres` (§23.8) — c'est à qui déploie d'en placer une copie dans
l'un des deux.

Les deux scripts de colle partagent le même espace de noms Python (celui
où `cmd_build()` a été défini) : leurs seuls noms de niveau module qui se
ressemblaient — le répertoire de travail temporaire, la fonction qui
localise `series.json` dans une arborescence extraite — sont préfixés
distinctement (`ZIP_WORK_DIR`/`_find_series_dir_in_zip` pour `app.py`,
`GIT_WORK_DIR`/`_find_series_dir_in_archive` pour `git_sync.py`) pour ne
jamais s'écraser l'un l'autre une fois chargés ensemble.

### 23.2 Confidentialité

Le zip envoyé ne quitte jamais l'onglet du navigateur : tout le traitement
(dézippage, build, rezippage) a lieu dans le système de fichiers virtuel de
Pyodide, en mémoire, côté client. Aucune requête réseau ne transporte le
contenu de la série.

Le runtime Pyodide lui-même est **vendoré** dans `web/vendor/pyodide/`
(fichiers tiers non modifiés, voir `web/vendor/NOTICE.md` pour la licence et
la procédure de mise à jour) plutôt que chargé depuis un CDN : la page ne
dépend d'aucun tiers au moment de l'exécution, uniquement de son propre
hébergeur.

### 23.3 Ce que ça change (et ne change pas) pour l'exécutable

`lightwebpres` reste sans dépendance externe, stdlib uniquement (§13.4) —
c'est justement ce qui le rend directement compatible avec Pyodide, sans
adaptation. La page web est un artefact **séparé et additif** : sa
dépendance à Pyodide n'entre pas dans le périmètre de cette contrainte, qui
porte sur l'exécutable console.

### 23.4 Fichiers

```
web/
├── index.html              # La page : les deux onglets (zip et GitLab)
├── app.py                  # Colle Python de l'onglet zip : zip → cmd_build() → zip
├── git_sync.py              # Colle Python de l'onglet GitLab : API GitLab v4 <-> cmd_build() (§23.9)
├── lwp_banner.svg           # Bannière du projet (utilisée aussi par le README du dépôt)
├── lwp_logo_icon.svg        # Icône/logo de la page
├── .htaccess                # Types MIME Apache pour vendor/pyodide/ (§23.7)
└── vendor/
    ├── NOTICE.md            # Provenance, licence, procédure de mise à jour
    └── pyodide/              # Runtime Pyodide vendoré (MPL-2.0)
```

### 23.5 Test

`tests/test_web.py` fait tourner un vrai navigateur (Chromium headless via
Playwright) contre la page servie localement, envoie un zip de test sur
l'onglet « Upload a zip », et vérifie le zip téléchargé — un test de bout
en bout du livrable réel, pas une simulation. `tests/test_git_sync.py`
fait de même sur l'onglet « Sync with GitLab » (§23.9), face à un **mock**
des trois endpoints GitLab utilisés (§23.13). Les deux nécessitent Node.js
et le paquet `playwright` ; ils sont ignorés proprement (skip) si l'un des
deux est absent, plutôt que de faire échouer toute la suite — c'est une
dépendance propre à ces tests, pas à l'exécutable.

### 23.6 Ne fonctionne pas ouvert directement (`file://`)

Le geste le plus naturel avec une page HTML autonome — la télécharger puis
l'ouvrir en double-cliquant dessus — ne fonctionne **pas** : les navigateurs
(Chromium en particulier) bloquent, sous l'origine `file://`, à la fois le
`fetch()` des ressources de Pyodide (`pyodide-lock.json`, le `.wasm`, le zip
de la stdlib) et l'`import()` dynamique de `pyodide.asm.mjs`, par politique
CORS (origine `null`). Ce n'est pas contournable côté page : il faut un
serveur HTTP, même minimal et local, puis ouvrir la page via une url
`http://` ou `https://`.

Deux pièges à éviter dans la commande à donner à l'utilisateur, tous deux
la rendraient incomplète ou fausse :

- **Servir le bon répertoire, explicitement.** La page dépend de fichiers
  frères — `web/vendor/pyodide/`, `web/app.py` et `web/git_sync.py`
  (chargés tous les deux, quel que soit l'onglet ouvert), et l'exécutable
  `lightwebpres` un niveau au-dessus de `web/` (le
  `fetchText('../lightwebpres')` du script). Un `python3 -m http.server`
  lancé sans argument sert le répertoire courant du terminal — souvent le
  mauvais (un dossier de téléchargements quelconque) — et le lancer
  *depuis* `web/` casse `../lightwebpres`, hors du répertoire servi. Il faut
  servir la racine du dépôt (le dossier qui contient à la fois
  `lightwebpres` et `web/`), explicitement, avec `--directory`, plutôt que
  de compter sur le répertoire courant.
- **Ne jamais présenter le fichier seul comme suffisant.** Sans ses
  fichiers frères, aucune commande de serveur ne suffit — le rappeler
  évite de faire croire qu'un serveur à lui seul résout tout.

`web/index.html` détecte le cas `file://` dès le début de `init()`
(`location.protocol === 'file:'`) et affiche un message d'erreur qui
calcule la commande exacte à partir du chemin réel du fichier ouvert
(`location.pathname`, dont `/web/index.html` est retranché pour obtenir
la racine du dépôt) — `python3 -m http.server 8000 --directory
"<racine calculée>"` — affichée dans un bloc `<code>` dédié avec son propre
bouton « Copy » (presse-papier via `navigator.clipboard`, repli sur
`prompt()` si l'API est indisponible) : une commande qu'il faut retaper à
la main depuis un message d'erreur est une source connue de fautes de
frappe, en particulier sur un chemin de fichier. Le tout plutôt que de
laisser Pyodide échouer avec une erreur de navigateur brute et peu
compréhensible (`ReferenceError: loadPyodide is not defined` si le script
lui-même est intercepté avant exécution, ou une `TypeError` de fetch selon
l'endroit exact où le blocage intervient — le point de blocage précis
varie, la cause est toujours la même). Testé par
`tests/test_web.py::FileProtocolGuard`.

### 23.7 Auto-hébergement sur un vrai serveur web : type MIME de `.mjs`

Un `python3 -m http.server` local (le module `mimetypes` de la stdlib
Python connaît `.mjs`) sert ces pages sans souci, mais un serveur web
« générique » (Apache, nginx, la plupart des configurations par défaut)
peut ne pas savoir associer `.mjs` à un type MIME JavaScript — cette
extension est plus récente que leurs tables par défaut, spécifique aux
modules ES. Résultat, `pyodide.asm.mjs` est servi en
`application/octet-stream` (ou similaire), et le navigateur refuse de le
charger comme module (`import()` dynamique impose une vérification stricte
du type MIME, contrairement à un `<script src>` classique) : erreur
`TypeError: [...] loading dynamically imported module:
.../pyodide.asm.mjs`, sans lien avec `file://` cette fois — la page peut
très bien être servie en `https://`.

À vérifier : `curl -sI https://exemple/chemin/vers/pyodide.asm.mjs | grep
-i content-type` doit renvoyer `text/javascript` ou
`application/javascript`, jamais `application/octet-stream` ni
`text/plain`.

**Apache** : `web/.htaccess` (versionné, déployé avec le reste du dossier)
corrige déjà ça automatiquement — `AddType text/javascript .mjs` — à
condition que l'hébergement autorise les surcharges par `.htaccess`
(`AllowOverride FileInfo` ou `All`), ce qui est le cas par défaut sur la
plupart des hébergements mutualisés (c'est justement le scénario que
`.htaccess` cible : un déploiement sans accès à la config Apache
principale). Si `AllowOverride None` est forcé pour le répertoire, il faut
ajouter la même ligne dans la config du site :

```apache
AddType text/javascript .mjs
```

**nginx** ignore silencieusement les fichiers `.htaccess` (aucun
équivalent par répertoire) : aucun correctif possible depuis le dépôt,
seule la config du site permet de le corriger (bloc `http` ou `server`) :

```nginx
types {
  text/javascript mjs;
}
```

Comme pour le CORS de l'API GitLab (§23.10), le cas nginx (et Apache sans
`.htaccess` autorisé) reste un réglage côté serveur, hors du périmètre de
ce que la page peut corriger elle-même.

### 23.8 Où chercher l'exécutable `lightwebpres`

La page a besoin du fichier `lightwebpres` (§23.1 : jamais dupliqué dans
`web/`, `lightwebpres` reste l'unique source de vérité) et le cherche à
deux emplacements conventionnels relatifs à elle-même, dans cet ordre :

1. `./lightwebpres` — à côté du contenu de `web/`. C'est le cas d'un site
   qui sert `web/` lui-même comme racine de son propre chemin d'URL, sans
   segment de chemin supplémentaire pour un dossier parent qui n'aurait
   d'autre rôle que d'y loger l'exécutable.
2. `../lightwebpres` — un niveau au-dessus de `web/`, la disposition du
   dépôt telle quelle, pour un déploiement qui se contente de dupliquer le
   dépôt sans réarranger sa structure.

`fetchLightwebpresSource()` essaie le premier, puis le second si le
premier échoue. Si les deux échouent — cas réel : le contenu de `web/`
copié seul vers une racine de site plate, sans l'exécutable nulle part à
proximité — la page l'explique au lieu de laisser remonter le message
brut `Failed to fetch ../lightwebpres: 404`, distinct des cas `file://`
(§23.6) et MIME (§23.7) puisque tout le reste (Pyodide compris) a déjà
chargé avec succès à ce stade. Testé par
`tests/test_web.py::MissingSiblingExecutableGuard` (aucun des deux
emplacements) et `FlatDeploymentFindsCurrentDirExecutable` (`./lightwebpres`
seul, sans copie au niveau parent, doit suffire).

---

### 23.9 Onglet GitLab : synchronisation depuis le navigateur

Le second onglet de `web/index.html` : au lieu du couple zip-à-envoyer /
zip-à-télécharger de l'onglet « Upload a zip », un cycle
**pull → build → push** directement contre un dépôt GitLab, toujours
entièrement dans l'onglet du navigateur.

Pyodide et `lightwebpres` sont déjà chargés au moment où cet onglet devient
actif (même bootstrap partagé, §23.1) ; ce qui lui est propre est
`web/git_sync.py`, chargé en même temps, qui parle à l'API REST v4 d'une
instance GitLab via
`pyodide.http.pyfetch` — un simple habillage de la fonction `fetch()` du
navigateur : les mêmes règles CORS s'appliquent, aucune requête ne transite
par un tiers. Trois actions indépendantes, déclenchées par trois boutons :

1. **Pull** — télécharge l'archive du dépôt pour une branche
   (`GET /projects/:id/repository/archive.zip?sha=branche`) et l'extrait.
   GitLab enveloppe systématiquement le contenu dans un répertoire
   `{projet}-{ref}-{sha}/` : c'est la même forme (zip à racine unique)
   qu'accepte déjà `_find_series_dir_in_zip()` côté `web/app.py`, mais avec
   sa propre fonction, `_find_series_dir_in_archive()` — même règle
   d'acceptation, nom distinct pour ne pas entrer en collision une fois les
   deux scripts chargés ensemble (§23.1).
2. **Build** — appelle `cmd_build()` telle quelle sur le répertoire extrait,
   comme l'onglet « Upload a zip ».
3. **Push** — compare le contenu local (sources **et** `public/` généré à
   l'étape précédente) à l'arborescence distante
   (`GET /projects/:id/repository/tree?recursive=true`), et pousse un seul
   commit (`POST /projects/:id/repository/commits`) avec une action
   `create` pour chaque fichier absent du dépôt distant et `update` pour
   chaque fichier déjà présent. Le commit est scindé en plusieurs appels si
   le nombre de fichiers dépasse 100 (pas de limite documentée côté GitLab,
   mais on reste prudent).

### 23.10 CORS : condition nécessaire, hors du périmètre de cette page

Une instance GitLab auto-hébergée standard (Omnibus) **n'envoie pas**
`Access-Control-Allow-Origin` sur les réponses de son API par défaut : sans
ça, le navigateur bloque toute requête de cette page, quel que soit le
token fourni. C'est un réglage côté serveur, à la charge de qui administre
l'instance GitLab visée — pas quelque chose que cette page puisse
contourner (utiliser un proxy CORS tiers réintroduirait exactement la
dépendance externe qu'on refuse ici, voir §23.2). Extrait nginx à ajouter à
la configuration de GitLab (`gitlab.rb`,
`nginx['custom_gitlab_server_config']`) pour l'emplacement `/api/` :

```nginx
location /api/ {
  add_header 'Access-Control-Allow-Origin' '*' always;
  add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, PRIVATE-TOKEN' always;
  if ($request_method = OPTIONS) { return 204; }
}
```

### 23.11 Jeton d'accès personnel

Scopes nécessaires : **`read_api` + `write_repository`**, pas `api`. Le pull
(`repository/archive.zip`, `repository/tree`) relève de la « Repositories
API » de GitLab, qui n'accepte pas le scope `read_repository` — une
limitation encore ouverte côté GitLab (ticket `read_repository` scope for
Repositories API, #28324) — d'où `read_api` (accès lecture à toute l'API,
plus étroit que `api` mais plus large que `read_repository`). Le push
(`repository/commits`, l'API Commits) accepte en revanche bien
`write_repository`, pas besoin de `api` pour cette partie. Un jeton limité
à `read_repository`/`write_repository` seuls (sans `read_api`/`api`) ne
suffit donc pas aujourd'hui : le pull échouera avec une erreur
d'insuffisance de scope. Si une instance GitLab plus ancienne échoue même
avec `read_api`, `api` reste le repli à essayer.

Le jeton est saisi dans un champ de la page, jamais passé en
paramètre d'URL (ça finirait dans l'historique du navigateur et les logs du
serveur). Il est toujours répercuté dans `sessionStorage` (survit à un
rechargement de l'onglet, disparaît à sa fermeture) ; une case à cocher
« Remember this token on this device », explicitement non cochée par
défaut, le duplique en plus dans `localStorage` (survit à la fermeture de
l'onglet, en clair sur le disque, jusqu'à décocher la case ou vider le
stockage) — un avertissement s'affiche tant que la case est cochée.

### 23.12 Ce que push ne fait jamais : supprimer

`push` ne pousse que des actions `create` et `update` : un fichier présent
dans le dépôt distant mais absent du répertoire local (article supprimé,
image retirée) n'est **jamais** supprimé côté distant par cette page — zéro
risque de perte de contenu déclenchée par une erreur locale (zip incomplet,
mauvais dossier). Pour supprimer un fichier du dépôt, passer par GitLab
directement. Autre conséquence de cette simplicité volontaire : `push` ne
compare pas le contenu distant à l'avant-poussée (seule l'existence du
chemin est vérifiée, pas le contenu), donc pousser sans changement réel
produit tout de même un commit (vide en diff, mais bien réel) plutôt que de
ne rien faire.

### 23.13 Test de l'onglet GitLab

`tests/test_git_sync.py` (§23.5) fait tourner un vrai navigateur face à un
**mock** des trois endpoints GitLab utilisés (pas de vrai serveur GitLab
dans la boucle de test) — servi sur un port distinct pour que le
navigateur traverse réellement une frontière d'origine et exerce pour de
vrai les en-têtes CORS dont cet onglet dépend (§23.10). Le test vérifie le
cycle complet pull → build → push, que `create`/`update` sont correctement
choisis par fichier, et que le contenu poussé pour `public/a.html` est
bien le HTML **construit** (pas la source) — pas une simulation du
résultat.
