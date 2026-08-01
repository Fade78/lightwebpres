# LightWebPres — Spécifications du framework

## 1. Objectif

LightWebPres est un framework de génération de pages web autonomes à partir de
fichiers Markdown étendus. Il produit des pages HTML contenant une suite de
fiches (slides) scrollables suivies d'un article de fond, avec une navigation
inter-articles. Le résultat est un ensemble de fichiers HTML **autonomes** (CSS
inline, JS inline, aucune dépendance externe), déployables sur n'importe quel
serveur statique.

Le framework est conçu pour un public rédacteur (auteur d'une série d'articles)
et un public lecteur (adolescents en lecture autonome sur mobile ou desktop).

Il est utilisable à la fois en édition manuelle (un humain édite les fichiers
Markdown) et en édition par LLM (un modèle de langue génère ou modifie les
fichiers Markdown puis lance le build).

---

## 2. Architecture générale

### 2.1 Exécutable unique

Le framework est un **fichier exécutable unique** (`lightwebpres`), script
Python 3 avec shebang `#!/usr/bin/env python3`. Il ne dépend d'aucune librairie
externe (Python 3 standard library uniquement). Il peut être installé
system-wide (`/usr/local/bin/lightwebpres`) ou utilisé localement
(`./lightwebpres`).

L'exécutable contient en interne :

1. La logique de build (parseur, convertisseur, moteur d'inclusion)
2. Les templates par défaut (CSS, JS, HTML) — écrits en string Python, extraits
   par la commande `install`
3. Les règles typographiques par défaut (`fr` et `en`) — écrites en string
   Python, extraites par la commande `install`
4. Le générateur de démo (crée des articles d'exemple)
5. Le CLI (`install`, `demo`, `build`, `check`, `--help`)

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
└── .gitlab-ci.yml                 # Pipeline CI
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
lightwebpres install [répertoire] [--lang fr] [--force]
lightwebpres demo [répertoire] [--lang fr]
lightwebpres build [répertoire] [--lang fr] [--output public/] [--language-file chemin.json]
lightwebpres check [répertoire] [--lang fr] [--output public/] [--language-file chemin.json]
lightwebpres audit [répertoire] [--lang fr]
lightwebpres --help
```

- `[répertoire]` : le chemin du répertoire de série (défaut : `.`, ou `$LWP_SERIES_DIR`)
- `--lang` : la langue — règles typographiques et chaînes d'interface (défaut : `fr`, ou `$LWP_LANG`)
- `--output` : le répertoire de sortie (défaut : `public/`, ou `$LWP_OUTPUT_DIR`)
- `--language-file` : fichier de langue explicite, priorité max sur toute autre source (§19.5)
- `--force` : `install` seulement — procède même si le répertoire cible n'est pas vide

---

## 3. Niveaux d'objets

Le système gère trois niveaux d'objets :

### 3.1 Niveau série (le site)

La série est l'ensemble des articles. Elle est décrite par `series.json` qui
contient, pour chaque article, deux catégories de champs bien distinctes
(détail complet en §20) :

- **Structurels — toujours dans `series.json`**, aucune autre source
  possible : `file` (nom du fichier HTML de sortie, ex. `snapchat.html`) et
  `source` (nom du fichier Markdown source, ex. `snapchat.md`).
- **D'affichage — surcharge optionnelle** d'une valeur par défaut lue dans
  le bloc meta de l'article lui-même (§20.3.1) : `series_title`/`series_desc`
  (titre et description courts, navigation et index), `card_title`/`card_desc`
  (spécifiques à la carte d'index, si différents des précédents),
  `card_label` (étiquette libre sur la carte d'index — texte, pas un
  numéro).

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

Générée à partir des champs `tag:` et `# Titre` (h1) de la fiche `cover`
elle-même, et de son `summary:` — ces champs vivent uniquement dans le
`.md`, jamais dans `series.json` (§3.1). Le numéro de slide est calculé
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
    <p class="fact-content">Le four doit être préchauffé avant d'enfourner...</p>
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

1. **`---`** (seul sur une ligne, entouré de lignes vides) sépare les fiches
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
file: tarte-aux-pommes.html
h1: La tarte aux pommes<br>Ce que la pâte brisée change vraiment
series_title: La tarte aux pommes
series_desc: Pâte brisée, cuisson et dressage
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
doivent être rendus comme deux `<p class="fact-content">` distincts (§6.1).

### 4.3 Champs d'une fiche standard

| Champ           | HTML généré                              | Obligatoire |
|-----------------|------------------------------------------|-------------|
| `tag`           | `<span class="slide-tag">VALEUR</span>`  | Non         |
| `h2` ou `## `   | `<h2>VALEUR</h2>`                        | Non         |
| `summary`        | `<p class="summary">VALEUR</p>`          | Non         |
| `fact-label`     | `<div class="fact-label">VALEUR</div>`   | Non         |
| `source`         | `<p class="source">Source : VALEUR</p>` | Non         |
| `highlight`         | `<span class="highlight-figure">VALEUR</span>` | Non     |
| `highlight-caption` | `<span class="highlight-caption">VALEUR</span>` | Non  |

Le texte libre après les champs est placé dans la `fact-content` si un
`fact-label` est présent, sinon dans un paragraphe `<p>`. Ce texte libre peut
contenir plusieurs paragraphes Markdown (séparés par une ligne vide, voir
§6.1) ; chaque champ `clé: valeur`, à l'inverse, tient toujours sur une seule
ligne physique (§4.1).

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
| `[texte](url)`    | `<a href="url">texte</a>`              |
| Paragraphe        | `<p>texte</p>`                         |

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

### 6.3 Espacement et indentation

Le convertisseur est insensible à l'indentation (tabs et espaces supprimés en
début de ligne). Une ligne vide sépare deux paragraphes ; des lignes de texte
consécutives sans ligne vide entre elles sont fusionnées dans le même
paragraphe (voir §6.1).

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
défaut — infobulles de navigation, bouton « copier le lien », libellés de la
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
| `full_article_tag`           | Étiquette de la fiche `full-article`                |
| `source_label`               | Préfixe avant la valeur de `source`                  |
| `copy_link`                  | Texte du bouton « copier le lien » d'une fiche       |
| `copy_link_aria`             | `aria-label` du bouton « copier le lien »            |
| `copy_link_done`             | Texte affiché après la copie                         |
| `copy_prompt`                | Texte du repli `prompt()` (navigateurs sans presse-papiers) |

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

---

## 8. Pages calculées

### 8.1 Page d'index

Générée depuis `series.json`. La page d'index contient :

1. Le `<head>` avec `<meta>`, `<title>`, le CSS inline
2. Un en-tête (titre de la série, sous-titre)
3. Une introduction (texte libre, défini dans `series.json` ou un fichier
   `index.md`)
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
3. Une liste numérotée des articles (`series_title` — `series_desc`,
   résolus comme en §20.3.1), chacun lié vers son fichier HTML construit
   (chemin relatif depuis le répertoire de série jusqu'à `--output`)

---

## 9. Templates personnalisables

La structure HTML des pages (page d'article, page d'index, bloc de
navigation de série) est **fixe** — ce n'est pas un template éditable. Ce
qui se personnalise :

- Le **vocabulaire et les libellés** de l'interface (boutons de navigation,
  « Copier le lien », etc.) : via le fichier de langue, pas via du HTML —
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

### 9.2 JS (`nav.js`)

Le JavaScript de navigation gère :
- Le scroll entre slides (flèches, PageUp/PageDown)
- Les boutons prev/next/home
- Les nav-dots (points de navigation)
- La détection de la slide courante au scroll
- Le bouton « Copier le lien » de chaque fiche

Éditable de la même façon que `style.css`, via `templates/nav.js`.

### 9.3 Extension de la page d'index (`index_extra.html`)

La structure de la page d'index reste fixe, mais un site migré ou une
fonctionnalité maison (bouton, modale, script tiers...) peut avoir besoin
d'un point d'ancrage que `style.css`/`nav.js` ne couvrent pas (`nav.js` ne
s'applique qu'aux pages d'article, pas à l'index). Si
`templates/index_extra.html` existe, son contenu est inséré tel quel
(HTML, CSS inline, `<script>`... — aucune transformation) juste avant
`</body>` de la page d'index générée. Absent par défaut : `install` ne
crée pas ce fichier, contrairement à `style.css`/`nav.js`.

---

## 10. Pipeline GitLab CI

Le `.gitlab-ci.yml` créé par `install` :

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
lightwebpres install [répertoire] [--lang fr]
```

Crée la structure de travail dans `[répertoire]` :

1. Crée le répertoire s'il n'existe pas
2. Crée les sous-répertoires : `articles/`, `templates/`, `language/`,
   `public/`
3. Extrait les templates par défaut depuis l'exécutable (§9) :
   - `templates/style.css`
   - `templates/nav.js`
4. Extrait les packs de langue par défaut depuis l'exécutable :
   - `language/fr.json`
   - `language/en.json`
5. Crée un `series.json` vide (tableau vide `[]`)
6. Crée un `.gitlab-ci.yml` de base
7. Copie l'exécutable `lightwebpres` dans le répertoire (pour autonomie)

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

Refuse de s'exécuter si l'un des 6 fichiers de démo existe déjà dans
`articles/` (erreur fatale) — jamais d'écrasement silencieux d'un travail
en cours.

Crée trois articles d'exemple, un pour chaque position de la navigation de
série :

1. Crée `articles/first.md` + `articles/first_article.md` (position
   « first »)
2. Crée `articles/middle.md` + `articles/middle_article.md` (position
   « middle » ; démontre `highlight`/`highlight-caption`)
3. Crée `articles/last.md` + `articles/last_article.md` (position « last »)
4. Met à jour `series.json` avec ces trois articles (`series_meta` inclus)
5. Lance le build → génère `public/first.html`, `public/middle.html`,
   `public/last.html` et `public/index.html`
6. Affiche un message : « Demo site generated in public/. Open
   public/index.html in a browser. »

### 11.3 `build`

```bash
lightwebpres build [répertoire] [--lang fr] [--output public/]
```

Construit le site :

1. Lit `series.json` dans `[répertoire]`
2. Pour chaque article dans `series.json` :
   a. Lit le fichier `.md` source depuis `articles/`
   b. Parse le Markdown étendu (découpe les slides, extrait les métadonnées)
   c. Pour chaque slide :
      - Si `cover` : génère la slide de couverture
      - Si `standard` : génère la slide avec les champs et le contenu
      - Si `series-nav` : génère la navigation depuis `series.json`
      - Si `full-article` : lit le fichier `.md` inclus, le convertit
   d. Applique les règles typographiques (protégées des balises HTML, §7.2)
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

### 11.4 `check`

```bash
lightwebpres check [répertoire] [--lang fr]
```

Vérifie sans modifier :

1. Lance le build en mémoire (sans écrire les fichiers)
2. Compare le HTML généré avec le HTML existant dans `public/`
3. Pour chaque fichier différent, affiche `[DRIFT] fichier` suivi d'un diff ;
   pour chaque fichier absent de `public/`, affiche `[NEW] fichier` ; pour
   chaque fichier identique, affiche `[OK] fichier`
4. Affiche un résumé chiffré : « N file(s) OK, M file(s) different. »
5. Code de sortie non nul (1) si au moins un fichier diffère ou est absent —
   c'est ce qui permet d'utiliser `check` comme porte de vérification dans un
   script ou une CI (§10) ; code de sortie 0 et « All articles are up to
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
4. Affiche un résumé : « N avertissement(s) » ou « Aucun avertissement »

Le nombre et la position des fiches `cover` restent libres (§4.4, §22.13) :
`audit` ne fait qu'informer, la décision reste à l'auteur.

### 11.6 `--help`

Affiche l'aide avec la liste des commandes et options.

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
     a. source = read_file(répertoire/articles/{article.source})
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
     i. write_file(répertoire/public/{article.file}, html)

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
       html += '<p class="fact-content">{content}</p>'
       html += '</div>'
     ELSE:
       html += '<p>{content}</p>'
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

L'exécutable n'utilise que la bibliothèque standard de Python 3 (sys, os, json,
re, pathlib, glob, argparse, textwrap). Pas de `pip install`.

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

Effet de bord utile : un `series_meta.title`/`h1` contenant un fragment
qui casserait la structure de la page (par exemple un `</title>` orphelin
copié tel quel dans le corps visible, où le HTML brut est autorisé par
conception comme pour `<br>`) fait désormais échouer le build au lieu
d'être publié — cette vérification agit comme un filet de sécurité
générique, pas seulement contre les bugs de rendu.

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
# Le .gitlab-ci.yml (créé par install) fait :
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
- **Theming multiple** : un seul thème (le CSS par défaut, éditable)
- **Présentation orale** : pas de mode présentateur, pas de fullscreen
- **Multi-langue dans une même page** : une langue par build
- **Images inline** : les images restent en chemin relatif
- **Recherche full-text** : pas de moteur de recherche
- **Commentaires** : pas de système de commentaires
- **Analytics** : pas de tracking

---

## 16. Feuille de route de développement

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

### Phase 6 : v0.2 (pistes non planifiées)

Demandé le 2026-07-31, volontairement pas dans cette version — pas
bloquant, à faire en v0.2 :

20. **Syntaxe Markdown native pour les images** (`![alt](src)`) — n'existe
    pas aujourd'hui : une image ne peut être insérée que via une balise
    `<img>` HTML brute recopiée telle quelle dans le Markdown (§6.2), et
    `![alt](src)` produit actuellement un rendu cassé (le convertisseur de
    liens reconnaît `[alt](src)` et laisse le `!` en texte littéral devant).
21. **Légendes** pour les tableaux et les images — pas de mécanisme dédié
    aujourd'hui ; à concevoir (ex. une ligne de texte immédiatement après
    l'élément, ou une syntaxe d'attribut).
22. **Images cliquables** — pas de comportement par défaut aujourd'hui (ex.
    lien vers l'image en taille réelle, ou lightbox JS) ; à ajouter dans
    `nav.js` si lightbox, ou simplement envelopper l'`<img>` dans un `<a>`.
23. **Taille et justification des images réglables** — pas de mécanisme
    dédié aujourd'hui (l'auteur doit tout gérer lui-même en CSS/HTML inline
    s'il écrit du HTML brut) ; à concevoir (classes CSS prédéfinies ? syntaxe
    d'attribut sur `![alt](src)` ?).

Ces quatre points demandent des choix de syntaxe (comment un auteur exprime
une légende, une taille, un alignement en Markdown) qui n'ont pas encore été
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
- **Idempotence** : pas de variable non déterministe ✓
- **Pipeline GitLab CI** : Python 3.12, pas de dépendance externe ✓
- **Langue** : typographie + chaînes d'interface dans des fichiers JSON
  séparés par langue, `fr` et `en` intégrés par défaut, `en` en repli ultime ✓
- **Édition par LLM** : format Markdown lisible et modifiable ✓
- **Exécutable unique** : un seul fichier Python, pas de dépendance externe ✓
- **Install / Demo / Build / Check / Audit** : commandes séparées ✓
- **Variables d'environnement** : `LWP_SERIES_DIR`, `LWP_ARTICLES_DIR`, etc. ✓
- **Override** : `style.css`/`nav.js` et le fichier de langue sont éditables
  (§9, §7) ; la structure HTML des pages ne l'est pas ✓ (délibérément, §9)

### 17.6 Ce qui n'est PAS couvert (volontairement)

- **Live reload** : pas de serveur de développement ✓ (documenté)
- **Theming multiple** : un seul thème ✓ (documenté)
- **Présentation orale** : pas de mode présentateur ✓ (documenté)
- **Multi-langue dans une même page** : une langue par build ✓ (documenté)
- **Images inline** : les images restent en chemin relatif ✓ (documenté)
- **Recherche full-text** : pas de moteur de recherche ✓ (documenté)
- **Commentaires** : pas de système de commentaires ✓ (documenté)
- **Analytics** : pas de tracking ✓ (documenté)

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
<title>{{title}}</title>
<style>
{{css}}
</style>
</head>
<body>

<nav class="nav-dots"></nav>

<div class="nav-buttons">
  <div class="nav-btn" id="navPrev" title="{{str_nav_prev}}">&#8593;</div>
  <div class="nav-btn nav-btn-home" id="navHome" title="{{str_nav_home}}">&#127968;</div>
  <div class="nav-btn" id="navNext" title="{{str_nav_next}}">&#8595;</div>
</div>

{{slides}}

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
| `{{title}}` | Métadonnées `h1` du `.md` (sans balises HTML) | Titre de la page |
| `{{css}}` | `templates/style.css` | Le CSS inline |
| `{{slides}}` | Généré par le build | Toutes les `<section class="slide">` |
| `{{js_nav}}` | `templates/nav.js` | Le JS de navigation (scroll, boutons, copier le lien) |
| `{{str_KEY}}` | `language/{lang}.json` → `strings` | Chaîne d'interface (voir §7.3), remplacée dans `page.html` **et** dans `js_nav` une fois celui-ci chargé |

Il n'y a pas de fichier `share.js` séparé : le bouton « copier le lien » fait
partie de `nav.js`, ses propres textes sont des placeholders `{{str_*}}`
comme le reste.

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
<body>

{{header}}

{{intro}}

{{cards}}

<div class="nav-buttons">
  ...
</div>

<script>
{{js_index}}
</script>

</body>
</html>
```

Placeholders supplémentaires :

| Placeholder | Source | Description |
|-------------|--------|-------------|
| `{{header}}` | Métadonnées de `series.json` | En-tête avec titre, sous-titre, version |
| `{{intro}}` | Texte d'introduction (dans `series.json` ou un fichier) | Paragraphe d'intro de l'index |
| `{{cards}}` | Généré depuis `series.json` | Les cartes d'articles |
| `{{js_index}}` | Généré, intégré à l'exécutable | Le JS spécifique à l'index (scroll, copier le lien) — pas overridable (§9) |
| `{{str_KEY}}` | `language/{lang}.json` → `strings` | Infobulles `index_nav_up`/`index_nav_home`/`index_nav_down`, voir §7.3 |

### 18.3 Template `series-nav.html`

```html
<section class="slide" id="{{slide_id}}">
  <h2>{{str_series_nav_title}}</h2>
  <div class="series-list">
{{nav_items}}
  </div>
</section>
```

| Placeholder | Source | Description |
|-------------|--------|-------------|
| `{{slide_id}}` | Calculé (ex. `s9-series`) | ID de la slide de navigation |
| `{{nav_items}}` | Généré depuis `series.json` | Les items de navigation (liens + courant), chacun utilisant `series_read`/`series_current_status`/`series_back_to_index` (§7.3) |
| `{{str_series_nav_title}}` | `language/{lang}.json` → `strings` | Titre du bloc (« Cette série » / « This series ») |

### 18.4 Règles de remplacement

- Le remplacement est fait dans l'ordre : d'abord `{{css}}`, `{{js_nav}}`
  (contenu statique), puis `{{slides}}`, `{{title}}`, `{{lang}}` (contenu
  dynamique), puis les `{{str_KEY}}` (chaînes d'interface, §7.3) en dernier.
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
      "replacement": " $1",
      "flags": "g"
    },
    {
      "name": "nbsp_after_opening_quote",
      "description": "Espace insécable après «",
      "pattern": "(«) ",
      "replacement": "$1 ",
      "flags": "g"
    },
    {
      "name": "nbsp_before_percent",
      "description": "Espace insécable avant %",
      "pattern": " %",
      "replacement": " %",
      "flags": "g"
    }
  ],
  "strings": {
    "nav_prev": "Planche précédente",
    "copy_link": "Copier le lien"
  }
}
```

### 19.2 Champs

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| `lang` | string | oui | Code de langue (ex. `fr`, `en`) |
| `name` | string | non | Nom affichable (ex. « Français ») |
| `rules` | array | oui | Liste des règles à appliquer, dans l'ordre |
| `rules[].name` | string | non | Nom court de la règle (pour le debug) |
| `rules[].description` | string | non | Description humaine |
| `rules[].pattern` | string | oui | Regex Python (sans délimiteurs) |
| `rules[].replacement` | string | oui | Remplacement (avec `$1`, `$2` pour les groupes) |
| `rules[].flags` | string | non | Flags regex (ex. `g` pour global). Défaut : `g` |
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
      "file": "tarte-aux-pommes.html",
      "source": "tarte-aux-pommes.md"
    },
    {
      "file": "creme-patissiere.html",
      "source": "creme-patissiere.md",
      "card_label": "Article 2 : Les classiques (corrigé)"
    }
  ]
}
```

Le premier article n'a que les deux champs structurels : `series_title`,
`series_desc`, `card_title`, `card_desc`, `card_label` sont lus depuis le
bloc meta de `tarte-aux-pommes.md` (§20.3.1). Le second illustre une
surcharge : `card_label` prend le pas sur celui du bloc meta de
`creme-patissiere.md` sans y toucher — les autres champs d'affichage de cet
article restent lus depuis son propre bloc meta.

### 20.2 Champs des articles

| Champ | Type | Obligatoire dans `series.json` | Utilisé par | Description |
|-------|------|-------------|------------|-------------|
| `file` | string | oui | build, index, nav | Nom du fichier HTML de sortie |
| `source` | string | oui | build | Nom du fichier `.md` source dans `articles/` |
| `series_title` | string | non | nav, index | Titre court ; surcharge celui du bloc meta de l'article (valeur finale obligatoire, §20.3.1) |
| `series_desc` | string | non | nav, index | Description courte ; surcharge celle du bloc meta (valeur finale obligatoire, §20.3.1) |
| `card_title` | string | non | index | Titre de la carte d'index si différent de `series_title` ; surcharge celui du bloc meta (§20.3.1) |
| `card_desc` | string | non | index | Description de la carte d'index si différente de `series_desc` ; surcharge celle du bloc meta (§20.3.1) |
| `card_label` | string | non | index | Étiquette libre sur la carte d'index — texte, pas un numéro ; surcharge celle du bloc meta (§20.3.1) |

### 20.3 Règles de validation

- Le tableau `articles` est **ordonné** : l'ordre des entrées définit l'ordre
  des articles dans la navigation et l'index.
- `file` doit être unique dans le tableau (pas de doublons) — erreur fatale
  sinon.
- `file` et `source` sont **obligatoires** et doivent être non vides sur
  chaque entrée — erreur fatale sinon, avec le champ et l'index de l'entrée
  en cause. Aucun autre champ n'est obligatoire *dans `series.json`* —
  `series_title`/`series_desc`/`card_title`/`card_desc`/`card_label` se
  résolvent selon §20.3.1.
- `file` et `source` doivent être de simples noms de fichier, sans séparateur
  de chemin ni `..` — erreur fatale sinon. `series.json` est une donnée
  éditable par un LLM ou une CI non surveillée (§13.5) ; sans cette
  validation, une valeur comme `/etc/passwd` ou `../../.ssh/id_rsa` serait
  jointe telle quelle au répertoire attendu (`Path(dir) / valeur` ignore
  silencieusement `dir` quand `valeur` est un chemin absolu) et permettrait
  une lecture ou une écriture de fichier arbitraire hors de `articles/`/`public/`.
- `source` doit se terminer par `.md` (insensible à la casse) et `file` par
  `.html` ou `.htm` (insensible à la casse) — erreur fatale sinon, avec le
  même traitement que le contrôle de sécurité ci-dessus : sans ça, une
  valeur comme `"file": "a.md"` construit sans avertissement un
  `public/a.md` contenant du HTML rendu, une extension de sortie
  incohérente qu'aucun choix éditorial ne justifie. `.htm` est accepté au
  même titre que `.html` : extension standard, toujours utile sur les
  systèmes de fichiers limités à trois lettres (FAT 8.3 et dérivés,
  certains hébergements ou environnements embarqués) ; la restreindre à
  `.html` seul briserait cet usage sans apport de sécurité, le risque visé
  (extension de sortie incohérente) étant identique pour toute extension
  qui n'est ni l'une ni l'autre.
- `source` doit pointer vers un fichier qui existe dans `articles/` — sinon
  cette entrée est ignorée (avertissement, pas d'arrêt du build).

#### 20.3.1 Résolution des champs d'affichage (surcharge)

`series_title`, `series_desc`, `card_title`, `card_desc`, `card_label` ne
sont jamais requis dans `series.json` lui-même : leur valeur par défaut est
lue dans le bloc meta de l'article correspondant (même nom de champ — ex.
`card_title:` dans le `.md`, §4.2), et `series.json` ne sert qu'à la
corriger pour un article donné, sans toucher au fichier source. Ordre de
résolution, pour chaque champ, du plus prioritaire au moins prioritaire :

1. **`series.json`**, l'entrée de l'article dans `articles[]`, si le champ y
   est présent et non vide.
2. **Le bloc meta de l'article**, le champ de même nom, si présent et non
   vide.
3. **Repli**, selon le champ, si absent des deux niveaux précédents :
   - `series_title` / `series_desc` : **la valeur finale doit être non
     vide** — erreur fatale sinon (même sévérité que les champs
     structurels), avec le fichier et le champ en cause. Contrairement à
     `file`/`source`, cette erreur ne peut être détectée qu'après lecture
     du bloc meta de l'article, pas seulement de `series.json` : c'est le
     seul contrôle de cette section qui dépend du contenu de l'article.
   - `card_title` : reprend la valeur déjà résolue de `series_title`
     (comportement inchangé).
   - `card_desc` : reprend celle de `series_desc`, pareillement.
   - `card_label` : aucune étiquette n'est affichée sur la carte — ce n'est
     pas une erreur, c'est un champ purement décoratif sans repli plus loin.

`file` et `source` ne suivent **pas** ce mécanisme : champs structurels,
toujours requis directement dans `series.json` (§20.3) — voir §3.1 pour la
distinction.

### 20.4 Métadonnées de la série (`series_meta`)

Le fichier `series.json` peut contenir un objet `series_meta` (optionnel)
qui décrit la série elle-même (pour l'index et le README) :

Si `series_meta` est présent, le fichier a deux clés : `series_meta` (objet) et
`articles` (tableau). Si `series_meta` est absent, le fichier est un tableau
direct (rétrocompatible avec un format de série déjà utilisé).

### 20.5 Champs de `series_meta`

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| `title` | string | oui | Titre de la série sur la page d'index |
| `subtitle` | string | non | Sous-titre sur la page d'index |
| `version` | string | non | Version affichée (ex. `v0.13`) |
| `intro` | string | non | Paragraphe d'introduction de l'index |

Le template d'index enveloppe `intro` dans un unique `<p>` fixe
(`<p>{{series_intro}}</p>`) : pour plusieurs paragraphes, insérer
`</p>\n<p>` dans la valeur — HTML brut passthrough, cohérent avec le
reste (§6.2).

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

Cette règle s'applique aussi aux titres `# `/`## ` : un `## Sous-titre` qui
apparaît **après** le début du contenu (donc dans le corps de la fact-box, pas
dans l'en-tête de la slide) est du texte de contenu — un titre Markdown normal
dans le rendu de la fact-box — et non une nouvelle valeur pour le `h2` de la
slide. Seul un `# `/`## ` rencontré avant tout contenu définit le titre de la
slide.

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
de lecture de fichier arbitraire que pour `file`/`source` dans `series.json`
(§20.3).

### 22.7 `---` au tout début du fichier (avant `<!-- lwp:meta -->`)

Erreur fatale. Le fichier doit commencer par `<!-- lwp:meta -->`.

### 22.8 Plusieurs `<!-- lwp:slide:full-article -->` dans le même fichier

Erreur fatale. Un article ne peut inclure qu'un seul article de fond.

### 22.9 Plusieurs `<!-- lwp:slide:series-nav -->` dans le même fichier

Erreur fatale. Un article ne peut contenir qu'une seule navigation de série.

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

Erreur fatale. Une fiche `cover` n'a pas de fact-box : `tag`, `h1` (ou `#
Titre`) et `summary` sont ses seuls champs. Si du texte suit ces champs sans
être lui-même un champ reconnu, le build s'arrête avec un message indiquant
le fichier et le numéro de fiche, plutôt que d'ignorer silencieusement ce
texte.

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

---

## 23. Version navigateur (`web/`)

En plus de l'exécutable console, une page statique permet de construire une
série **entièrement dans le navigateur**, sans rien installer : on dépose un
zip de la série, on récupère un zip de `public/`. Un serveur HTTP minimal
reste nécessaire pour ouvrir la page elle-même — voir §23.6.

### 23.1 Principe

`web/index.html` charge [Pyodide](https://pyodide.org) (CPython compilé en
WebAssembly), y exécute le fichier `lightwebpres` **tel quel** — aucune
duplication de logique, `lightwebpres` reste l'unique source de vérité,
il n'en existe donc pas de copie versionnée dans `web/` — puis un petit
script de colle (`web/app.py`) qui dézippe le zip envoyé, appelle
`cmd_build()`, et rezippe `public/` pour le téléchargement. `lightwebpres`
est cherché à deux emplacements conventionnels relatifs à la page,
`./lightwebpres` puis `../lightwebpres` (§23.8) — c'est à qui déploie d'en
placer une copie dans l'un des deux.

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
├── index.html              # La page : upload, sélection de langue, build, download
├── app.py                  # Colle Python : zip → cmd_build() → zip
├── .htaccess                # Types MIME Apache pour vendor/pyodide/ (§23.7)
└── vendor/
    ├── NOTICE.md            # Provenance, licence, procédure de mise à jour
    └── pyodide/              # Runtime Pyodide vendoré (MPL-2.0)
```

### 23.5 Test

`tests/test_web.py` fait tourner un vrai navigateur (Chromium headless via
Playwright) contre la page servie localement, envoie un zip de test, et
vérifie le zip téléchargé — un test de bout en bout du livrable réel, pas
une simulation. Il nécessite Node.js et le paquet `playwright` ; il est
ignoré proprement (skip) si l'un des deux est absent, plutôt que de faire
échouer toute la suite — c'est une dépendance propre à ce test, pas à
l'exécutable.

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
  frères — `web/vendor/pyodide/`, `web/app.py` ou `web/git_sync.py`, et
  l'exécutable `lightwebpres` un niveau au-dessus de `web/` (le
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

`index.html` et `git-sync.html` détectent le cas `file://` dès le début de
`init()` (`location.protocol === 'file:'`) et affichent un message d'erreur
qui calcule la commande exacte à partir du chemin réel du fichier ouvert
(`location.pathname`, dont `/web/{index,git-sync}.html` est retranché pour
obtenir la racine du dépôt) — `python3 -m http.server 8000 --directory
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

Comme pour le CORS de l'API GitLab (§24.2), le cas nginx (et Apache sans
`.htaccess` autorisé) reste un réglage côté serveur, hors du périmètre de
ce que la page peut corriger elle-même.

### 23.8 Où chercher l'exécutable `lightwebpres`

Les deux pages ont besoin du fichier `lightwebpres` (§23.1 : jamais
dupliqué dans `web/`, `lightwebpres` reste l'unique source de vérité) et
le cherchent à deux emplacements conventionnels relatifs à elles-mêmes,
dans cet ordre :

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

## 24. Synchronisation git depuis le navigateur (`web/git-sync.html`)

Un troisième livrable, indépendant des deux premiers (l'exécutable console
et `web/index.html`) : une page qui remplace le couple zip-à-envoyer /
zip-à-télécharger de `web/index.html` par un cycle **pull → build → push**
directement contre un dépôt GitLab, toujours entièrement dans l'onglet du
navigateur.

### 24.1 Principe

`web/git-sync.html` charge Pyodide et `lightwebpres` exactement comme
`web/index.html` (même mécanisme, §23.1), puis un script de colle dédié
(`web/git_sync.py`) qui parle à l'API REST v4 d'une instance GitLab via
`pyodide.http.pyfetch` — un simple habillage de la fonction `fetch()` du
navigateur : les mêmes règles CORS s'appliquent, aucune requête ne transite
par un tiers. Trois actions indépendantes, déclenchées par trois boutons :

1. **Pull** — télécharge l'archive du dépôt pour une branche
   (`GET /projects/:id/repository/archive.zip?sha=branche`) et l'extrait.
   GitLab enveloppe systématiquement le contenu dans un répertoire
   `{projet}-{ref}-{sha}/` : c'est exactement la forme déjà acceptée par
   `_find_series_dir()` (zip à racine unique, voir `web/app.py`), donc
   aucune adaptation n'a été nécessaire de ce côté.
2. **Build** — appelle `cmd_build()` telle quelle sur le répertoire extrait,
   comme `web/index.html`.
3. **Push** — compare le contenu local (sources **et** `public/` généré à
   l'étape précédente) à l'arborescence distante
   (`GET /projects/:id/repository/tree?recursive=true`), et pousse un seul
   commit (`POST /projects/:id/repository/commits`) avec une action
   `create` pour chaque fichier absent du dépôt distant et `update` pour
   chaque fichier déjà présent. Le commit est scindé en plusieurs appels si
   le nombre de fichiers dépasse 100 (pas de limite documentée côté GitLab,
   mais on reste prudent).

### 24.2 CORS : condition nécessaire, hors du périmètre de cette page

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

### 24.3 Jeton d'accès personnel

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

### 24.4 Ce que push ne fait jamais : supprimer

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

### 24.5 Fichiers

```
web/
├── git-sync.html            # La page : connexion, pull, build, push
└── git_sync.py               # Colle Python : API GitLab v4 <-> cmd_build()
```

### 24.6 Test

`tests/test_git_sync.py` fait tourner un vrai navigateur (Chromium headless
via Playwright, même mécanisme que §23.5) contre la page servie localement,
mais face à un **mock** des trois endpoints GitLab utilisés (pas de vrai
serveur GitLab dans la boucle de test) — servi sur un port distinct pour
que le navigateur traverse réellement une frontière d'origine et exerce
pour de vrai les en-têtes CORS dont cette page dépend (§24.2). Le test
vérifie le cycle complet pull → build → push, que `create`/`update` sont
correctement choisis par fichier, et que le contenu poussé pour
`public/a.html` est bien le HTML **construit** (pas la source) — pas une
simulation du résultat.
