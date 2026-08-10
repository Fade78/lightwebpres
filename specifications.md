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
- **`BACKLOG.md`** (anglais) — le registre *pérenne* des manques relevés
  et des décisions différées : ce qui doit rester trouvable « plus tard »
  y va, et y reste au travers des releases. Référencé par cette
  spécification (B3, B5, B9).

Les autres fichiers `.md` de la racine ne font **pas** partie de ce
contrat, et se répartissent en deux familles :

- **transitoire** — `JOURNAL-1.0.md`, la mémoire de travail de la 1.0 :
  supprimée du dépôt juste avant la release, jamais référencée par un
  document pérenne. Ses renvois internes en `§x.y` ne sont pas tenus à
  jour et peuvent pointer dans le vide.
- **relevés** — `ETUDE-VIEWPORT.md` (mesures de viewport, rattachées à B7
  et B13), `REVISION-THEMES.md` (mesures du catalogue, plus un registre
  ouvert de limites du moteur, rattaché à B5 et B9) et
  `ANTERIORITE-THEMES.md` (ce qui a été trouvé ailleurs avant la refonte
  du système de thèmes). Ils portent ce qu'une spec normative ne peut pas
  absorber : des mesures avec leurs conditions, les hypothèses qu'elles
  ont tuées, et une enquête datée. Ils n'obligent rien ; en cas de
  divergence, ce document fait foi.

  **Un document de conception, lui, ne survit pas à son absorption.** Une
  fois son raisonnement versé ici — raisonnement compris, pas seulement
  ses règles — il est supprimé plutôt que gelé : git le conserve, et un
  bandeau « document historique » est une invitation à le lire quand
  même. Un document, un métier, nommé d'après ce métier.

### 1.2 Contrat avec `lightwebpres-gui`

`lightwebpres-gui` est un **projet séparé** (dépôt distinct, hors du
périmètre de version de celui-ci) : une interface graphique qui édite des
séries et pilote des builds. Il **consomme** ce projet ; le contrat entre
les deux est explicite et unidirectionnel (le GUI suit, `lightwebpres`
est la source de vérité) :

- **Vocabulaire.** `GLOSSARY.md` est le contrat de vocabulaire partagé :
  tout champ que le GUI présente, valide ou génère porte le nom, la
  portée et la casse qui y sont figés (conventions de nommage :
  `GLOSSARY.md` § « Naming conventions »). Le générique est « field »,
  jamais « tag »/« balise ».
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
  (`GLOSSARY.md` § « Naming conventions », liste gelée en §20.2) et le
  format d'entrée (`series.json`, article `.md`) sont stables au sens de la politique de versionnage (§13.9) : le GUI peut
  s'y fier sans qu'un patch les casse.

- **Licence.** Ce projet est sous GPLv3 ou ultérieure, avec la
  *LightWebPres Output Exception* (`COPYING`, `COPYING.EXCEPTION`). Le GUI
  en vendorise une copie : il doit donc être distribué sous une licence
  compatible, et il l'est — GPLv3 ou ultérieure lui aussi, **sans**
  exception propre, parce qu'il n'écrit rien de lui-même dans une série.
  Ce que le GUI produit est produit par cet exécutable, et hérite donc de
  l'exception d'ici. Les fichiers de licence doivent voyager avec toute
  redistribution, y compris dans l'arborescence déployée du GUI.
- **Surface interne consommée.** Au-delà de `cmd_*`, le GUI dépend de six
  symboles internes que la surface commande n'expose pas :
  `build_article()`, `load_language()`, `TypoEngine`, `strings`, `THEMES`
  et `_find_series_dir_in_archive()`. La dépendance existe, écrite ou non ;
  l'écrire évite qu'un renommage la casse en silence, puisque la suite de
  tests d'ici ne la voit pas. Les renommer est un changement cassant pour
  le GUI même si rien ne rougit de ce côté-ci — voir la spec
  `lightwebpres-gui` §2.3, qui tient la liste à jour.

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
même fichier sur un système de fichiers Windows/macOS) — la collision
avec l'index de série relevant d'une règle distincte, §11.3.3. Il peut être installé
system-wide (`/usr/local/bin/lightwebpres`) ou utilisé localement
(`./lightwebpres`).

L'exécutable contient en interne :

1. La logique de build (parseur, convertisseur, moteur d'inclusion)
2. Le moteur de thèmes (registre de propriétés typées, §9) et les templates
   par défaut (JS de navigation, HTML) — le scaffold de `settings.conf` et
   `nav.js` sont extraits par la commande `init` ; la feuille de style,
   elle, est composée en mémoire à chaque build, jamais installée (§9.3)
3. Les règles typographiques par défaut (`fr` et `en`) — écrites en string
   Python, extraites par la commande `init`
4. Le générateur de démo (crée des articles d'exemple)
5. Le CLI (`init`, `demo`, `build`, `verify`, `audit`, `template update`,
   `theme list`, `series theme set`, `theme gallery`, `--help`)

### 2.2 Le répertoire de série

L'unité de travail est le **répertoire de série**. C'est lui qui contient tout
ce qui est particulier à une série d'articles : les sources, les templates, la
typographie, la configuration, et le output.

Structure créée par `init` :

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
├── templates/                     # La surface de personnalisation de cette série (§9)
│   ├── settings.conf              # Les propriétés typées (le look) — scaffold complet commenté
│   ├── custom.css                 # Les règles CSS libres de l'auteur (ajoutées en dernier)
│   └── nav.js                     # Le JS de navigation (override)
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
├── lightwebpres                   # Copie de l'exécutable (installée par init, §11.1)
├── .gitlab-ci.yml                 # Pipeline CI (optionnel — init --gitlab-ci, §11.1)
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
lightwebpres init [répertoire] [--lang fr] [--force] [--theme nom] [--gitlab-ci]
lightwebpres demo [répertoire] [--lang fr] [--output public/]
lightwebpres build [répertoire] [--lang fr] [--output public/] [--language-file chemin.json] [--no-typography] [--include-drafts] [--only page] [--nav-cache chemin] [--build-stamp | --build-stamp-minimal]
lightwebpres verify [répertoire] [--lang fr] [--output public/] [--language-file chemin.json] [--no-typography] [--include-drafts]
lightwebpres audit [répertoire] [--lang fr]
lightwebpres template update [répertoire] [--scaffold]
lightwebpres theme list [--polarity light|dark] [--intensity sober|vivid|mono] [--hue teinte]
lightwebpres series theme set [répertoire] --theme nom
lightwebpres theme gallery [chemin]
lightwebpres --help
```

- `[répertoire]` : le chemin du répertoire de série (défaut : `.`, ou `$LWP_SERIES_DIR`)
- `--lang` : la langue — règles typographiques et chaînes d'interface (défaut : `fr`, ou `$LWP_LANG`)
- `--output` : `demo` / `build` / `verify` — le répertoire de sortie
  (défaut : `public/`, ou `$LWP_OUTPUT_DIR`) ; un chemin **relatif** est
  résolu depuis le répertoire courant, pas depuis `[répertoire]`
- `--scaffold` : `template update` seulement — régénère la surface
  commentée de `settings.conf` aux valeurs du thème courant, en
  conservant les lignes épinglées (§9.4.3)
- `--language-file` : fichier de langue explicite, priorité max sur toute autre source (§19.5)
- `--force` : `init` seulement — procède même si le répertoire cible n'est pas vide (`series theme set` n'a plus de `--force` : il ne réécrit que la ligne `theme:` de `settings.conf`, il n'y a plus rien à forcer — §11.10)
- `--theme` : `init`/`series theme set` — applique une palette prédéfinie (§9.5)
- `--polarity` / `--intensity` / `--hue` : `theme list` seulement — restreint la liste par facette (§9.5.2, §11.9)
- `--gitlab-ci` : `init` seulement — écrit aussi un `.gitlab-ci.yml` (opt-in, §11.1)
- `--no-typography` : `build`/`verify` seulement — désactive entièrement le moteur de typographie pour ce lancement (§19.6)
- `--include-drafts` : `build`/`verify` seulement — construit aussi les articles marqués `status: draft` (§20.6), avec bandeau « Brouillon ». Sans effet sur `status: ignored`, qui n'est jamais construit
- `--only` : `build` seulement — ne reconstruit qu'une page (§11.3.1)
- `--nav-cache` : `build` seulement — chemin du cache d'empreinte de navigation (§11.3.1)
- `--build-stamp` / `--build-stamp-minimal` : `build` seulement — horodatage de build dans l'en-tête des pages (§11.3.2)

Les variables d'environnement `LWP_SERIES_DIR`/`LWP_LANG`/`LWP_OUTPUT_DIR`
sont honorées par toute commande qui opère sur un répertoire de série —
`LWP_SERIES_DIR` est résolu une seule fois dans `main()`, avant l'aiguillage,
donc `init`, `demo` et `series theme set` l'honorent aussi. Seules `theme list` et
`theme gallery` y échappent : la première n'interroge que la table `THEMES`
intégrée, la seconde ne prend qu'un chemin de sortie. `theme list` et `theme gallery` ne lisent aucun répertoire de
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
  §20.3.1), `status` (§20.6).

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
  <div class="notes-local">
    <ol class="note-body">
      <li id="note-article-1" role="doc-footnote">
        <span class="note-num">1</span>...<a class="note-back"
        href="#noteref-article-1" role="doc-backlink">↩</a></li>
    </ol>
  </div>
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

**La liste est fermée.** Ces quatre types sont écrits une seule fois, dans
le registre `SLIDE_TYPES` de l'exécutable, qui porte pour chacun son
marqueur de titre (`#`, `##`, ou aucun), les champs qu'il accepte, ce que
devient le texte libre, et une ligne de description. La validation (§22.9.2)
et `--help` lisent ce registre, et un consommateur extérieur peut le lire
aussi — c'est de là que `lightwebpres-gui` tire son bandeau d'assistance,
plutôt que d'écrire une seconde fois une grammaire qui dériverait de
celle-ci. Un jeton hors de cette liste est une erreur fatale, pas une fiche
standard silencieuse.

### 4.5 Désactiver la typographie automatique pour un article

Le moteur de typographie (§7/§19) **modifie le contenu généré** : il insère
des espaces insécables aux endroits qu'il reconnaît (voir §7.5 pour la
liste). C'est un comportement par défaut, pas neutre, donc réversible —
trois champs du bloc `<!-- lwp:meta -->` de l'article (aucun effet ailleurs,
y compris dans `series.json`, §20.2) permettent de le retirer, en tout ou
en partie, pour cet article et sa propre page uniquement :

| Champ | Effet quand la valeur est `off` |
|-------|----------------------------------|
| `typo_units: off` | Désactive uniquement les règles nombre/unité et opérateur/nombre (`nbsp_before_unit`, `nbsp_after_operator`, §7.5) |
| `typo_thousands: off` | Désactive uniquement la règle de séparateur de milliers (`nbsp_thousands_separator`, §7.5) |
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

Ce principe s'applique aussi à la surface de personnalisation et à la
typographie : ce sont des fichiers séparés, référencés par nom (§9, §7),
pas inline dans l'exécutable au moment du build.

### 5.3 Inclusion des fichiers de présentation

- **CSS** : la feuille est **composée en mémoire** (§9.3) — défauts,
  thème et propriétés lus depuis `templates/settings.conf`, règles libres
  de `templates/custom.css` ajoutées en dernier — puis insérée dans
  `<style>` dans le `<head>` de chaque page
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
| `[^label]`        | appel de note — voir §6.5              |
| `[^label]: corps` | corps de note — voir §6.5              |
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
| `yes` | le critère est rempli | `verdict.yes.*` — `affirm`, gras |
| `no` | il ne l'est pas | `verdict.no.*` — `ink-quiet`, non gras |
| `partial` | partiellement | `verdict.partial.*` — `call`, gras |
| `col-signal` | mettre en valeur toute une colonne | `table.col-signal.*` — fond creusé, gras |
| `col-snap` | une seconde colonne à distinguer | `table.col-snap.*` — fond creusé + filet `mark` |

soit `<td class="yes">Oui</td>`, ou `<span class="yes">Oui</span>` à
l'intérieur d'une cellule Markdown. Chaque verdict a ses propres
propriétés (encre, graisse, marqueur de forme — §9.1), dont les défauts
pointent vers la palette : un thème (§9.5) les restyle comme le reste
sans les confondre, et `print-color-adjust` conserve la distinction à
l'impression, où la couleur saute souvent.

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
(propriétés `caption.*`, l'encre à `ink-quiet` par défaut — donc adaptée
à chaque thème, §9.1). Une image **au milieu d'un
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

**Figure cliquable.** La même ligne enveloppée d'un lien Markdown —
`[![alt](src "Légende")](https://…)`, seule sur sa ligne — reste une
figure, et l'image devient cliquable :
`<figure class="figure"><a href="…" target="_blank" rel="noopener"><img …></a><figcaption>…</figcaption></figure>`.
La cible est restreinte à http(s) comme tout lien (§6.3), puisqu'elle
atterrit dans un attribut.

Le lien enveloppe **l'image seule, jamais la légende**. Sémantiquement
on clique l'image et la légende est un texte à son propos ; et
techniquement, n'envelopper que l'`<img>` laisse le **nom accessible** du
lien être le seul texte alternatif. Légende comprise, un lecteur d'écran
annoncerait la phrase entière comme intitulé du lien.

C'est un élargissement de la règle « seule sur sa ligne », pas un
mécanisme de plus : cette règle distingue déjà la figure de l'image au
fil de la phrase. Un champ dédié aurait introduit une couche de
propriétés dans le corps long-forme, qui est du Markdown pur, pour dire
ce que Markdown exprime déjà.

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

### 6.5 Notes

Une note a deux parties, nommées séparément parce qu'elles ne vivent pas
au même endroit : l'**appel** (`[^label]`), le repère dans le texte
courant, et le **corps** (`[^label]: texte`), la note elle-même. La
syntaxe est celle du Markdown standard ; rien n'est inventé.

L'appel devient un lien vers le corps, le corps porte un lien de retour
vers l'appel, et les rôles DPUB-ARIA (`doc-noteref`, `doc-footnote` ou
`doc-endnote`, `doc-backlink`) sont posés. Le lien de retour n'est pas un
agrément : sans lui, un lecteur qui a sauté depuis la fiche 3 n'a d'autre
issue que la barre de défilement, et un utilisateur de lecteur d'écran
n'en a aucune. **Le label de l'auteur
n'atteint jamais la page** : c'est une clé, rien d'autre, ce qui explique
qu'il puisse être n'importe quoi (`[^1]`, `[^kwh]`, `[^a]`) et que la
numérotation ne soit pas une réécriture de ce que l'auteur a écrit.

#### 6.5.1 Emplacement (`notes_placement`)

Deux valeurs, et l'emplacement est la **seule** décision de structure :

- `local` (défaut) — le corps s'affiche au pied de l'unité qui l'appelle :
  pied de la fiche pour un appel en fiche, fin de l'article pour un appel
  dans l'article de fond. Un principe, deux structures : *aussi près de
  l'appel que la structure le permet*.
- `page` — tous les corps de la page se rassemblent dans une section de
  notes en fin de page, avec son propre titre, sa propre ancre et son
  propre point de navigation. Une « page de notes séparée » n'est pas
  hors du document : c'est une section de la même page, ce qui est aussi
  ce qui la rend réalisable dans un fichier autonome unique.

**À qui `page` s'adresse**, faute de quoi il se lit comme une seconde
option arbitraire : aux fiches destinées à être projetées, ou lues comme
une suite propre, où un bloc de notes au pied d'une diapositive est du
bruit. C'est un besoin réel, et c'est à l'auteur de le déclarer.

**Une troisième valeur a été envisagée puis écartée** : « à la fin de
l'article, spécifiquement ». Pour un appel fait dans l'article, elle est
identique à `local` ; pour un appel fait dans une fiche, elle est
identique à `page`. Elle ne nommerait aucun comportement distinct. C'est
le seul choix rejeté de toute la conception des notes, et c'est la
question qu'un lecteur reposera — d'où sa présence ici.

Sur le nom `local`, qui recouvre deux positions différentes : l'article
de fond est l'exact opposé de la fiche — un défilement continu, où le
bloc rassemblé en fin de texte est ce que tout lecteur attend déjà, et
où le saut-retour est le geste normal. Un seul mot nomme honnêtement les
deux parce qu'il nomme le même **principe**, pas la même position.

`local` est le défaut parce qu'une fiche est **adressable
individuellement** : le bouton de partage distribue des liens vers des
fiches précises, donc un lecteur peut arriver en fiche 5 sans avoir lu
les quatre premières. S'il clique un appel et se retrouve projeté à la
fin d'un document qu'il n'a pas lu, la note lui a coûté sa place pour
rien — le corps pouvait être six lignes plus bas.

Une conséquence mesurée, à dire franchement : des notes au pied d'une
fiche prennent de la place sur un écran déjà court (`ETUDE-VIEWPORT.md`).
Une fiche portant cinq notes défilera. C'est un signal d'écriture plus
qu'un défaut de rendu, mais un auteur qui choisit `local` doit le savoir.

#### 6.5.2 Numérotation

**Continue, et elle redémarre avec l'unité qui porte les corps.** Une
seule règle, conséquence de l'emplacement plutôt que seconde décision :

| emplacement | unité portant les corps | numérotation |
|---|---|---|
| `local`, appel en fiche | cette fiche | redémarre à 1 dans chaque fiche |
| `local`, appel dans l'article | l'article | continue dans tout l'article |
| `page` | la page | continue sur toute la page |

L'argument est l'adressabilité, pas la symétrie : une note numérotée 7
dans une fiche où le lecteur vient d'arriver directement ne lui dit rien,
il cherchera les six premières. La numérotation doit être portée à la
même échelle que l'adressage. C'est aussi ce que fait l'imprimé — les
notes redémarrent par page, et ici la fiche *est* l'analogue de la page.

**Le numéro affiché n'est pas l'identifiant d'ancre.** HTML exige des
`id` uniques dans le document, donc l'ancre reste portée par sa localité
(`note-s3-1` : fiche 3, note 1) pendant que le lecteur voit `1`. Sans
cela, deux fiches portant chacune une note émettraient deux
`id="note-1"` et chaque lien de retour tomberait sur la mauvaise.

**Un label appelé deux fois donne un corps et deux liens de retour** —
dupliquer le corps donnerait deux numéros à une seule référence.

#### 6.5.3 Info-bulle (`notes_tooltip`)

Ce n'est pas un emplacement mais un **agrément sur l'appel**, et il se
compose avec les deux emplacements : `notes_tooltip: on` porte aussi le
texte du corps sur l'appel, sans le déplacer.

**Ce n'est jamais le seul porteur, et cela ne peut pas le devenir.** Une
info-bulle n'existe pas sur un écran tactile, n'existe pas à l'impression
et ne fait pas partie de l'ordre de lecture. Une note qui n'y vivrait que
serait perdue pour une large part des lecteurs — et perdre la référence
est le pire endroit où cet outil puisse économiser. Le corps est toujours
dans le document ; l'info-bulle ne fait qu'épargner un saut. Sa valeur
est donc maximale avec `page` et minimale avec `local`. Elle est à `off`
par défaut.

#### 6.5.4 La cascade, et pourquoi il y en a deux

**La structure et l'apparence ne cascadent pas par les mêmes couches, et
la raison est mécanique, pas esthétique.** Le moteur de thèmes compose du
CSS et rien d'autre. Le CSS ne peut pas déplacer un élément d'un
conteneur vers un autre. Donc `notes_placement` **ne peut pas** être une
propriété de thème : non parce que ce serait inélégant, mais parce qu'un
thème serait physiquement incapable de l'honorer.

| | ce qui est décidé | cascade |
|---|---|---|
| **structure** | `notes_placement`, `notes_tooltip` | défaut → `series_meta` → bloc meta de l'article |
| **apparence** | corps du texte, filet, couleur, numéro | le registre de propriétés (§9) : défauts → thème → `settings.conf` → `style.*` → balise d'instance |

La cascade de structure reprend la forme qu'`author` / `license` / `date`
ont déjà : déclarée pour la série dans `series_meta`, redéfinie par
article dans son propre bloc meta. Une valeur inconnue est une erreur de
build qui nomme l'article — retomber silencieusement sur le défaut
laisserait un auteur devant une page qui ignore ce qu'il a demandé, sans
rien pour le lui dire.

Côté apparence, le registre porte **trois** composants, parce que les
deux emplacements ne sont pas la même surface : `note` (les valeurs
partagées : couleur, interligne, lien de retour), `note.local` (le bloc
au pied d'une fiche — du mobilier compact *dans* une fiche) et
`note.page` (la section de fin de page — une **section**, comme celle de
l'article : elle veut un fond, un titre et un filet). `footnote-call`
(`sup`) existait déjà et garde son nom : il habille l'appel, qui est le
même objet où que le corps atterrisse.

Trois et non un, pour une raison de principe et pas de commodité : leur
donner un composant unique forcerait un thème à habiller de la même
valeur un bloc au pied d'une fiche et une section entière — c'est
exactement l'erreur que la réécriture §9 a été faite pour arrêter, un nom
portant deux sens, si bien qu'aucun des deux ne peut bouger sans
entraîner l'autre.

**Une note au pied d'une unité est écrite plus petite qu'une note dans
sa propre section**, et l'échelle de la fiche le dictait déjà : son corps
est à 15 px, son propre appareil — `source`, `fact-label` — à 12 px. Une
note à `note.size` (14 px) sortait à 93 % du corps qu'elle annote, donc
lue comme du texte de plus, et **plus grande** que le bloc `.refs` trois
lignes plus bas, qui est exactement le même rôle.

`note.local.size` et `refs.size` sont donc tous deux à **12 px**, le
plancher du design : aucune des 244 propriétés n'est en dessous. Une note
sert à *détailler*, et sur une fiche le détail est de la place que le
reste n'a pas ; mais en dessous il n'y a rien à gagner. Mesuré, passer de
13 à 12 px fait gagner 3 px sur une fiche de 617 — 0,5 % — et à 11 px la
référence, la seule chose que cet outil existe pour rendre atteignable,
deviendrait le plus petit élément de la fiche, sous le numéro de fiche
(13 px) et sous l'étiquette (12 px).

**Ce qui remplace la taille comme moyen de s'effacer**, ce sont le ton
(`note.fg`), la graisse (`note.weight`) et l'italique (`note.style`) : un
thème rend une note discrète par la couleur ou par la forme, jamais en la
rapetissant encore. Le ton a un plancher que la suite de tests mesure —
4,5:1 sur les trois fonds où un corps peut atterrir — donc « plus
discret » ne peut pas devenir « illisible ».

`refs.fg` référence `note.fg` plutôt que d'avoir son propre ton : les
deux blocs sont le même rôle, à la même taille, sur la même page, donc un
thème qui a rendu ses notes discrètes l'a dit pour ses références aussi.
Cela ferme au passage un défaut antérieur aux notes et jamais mesuré :
`ink-quiet` y était **sous AA sur 12 thèmes sur 33** (solarized à
2,61:1), pour la même raison que sur les notes — ce gris a été dessiné
pour du texte secondaire à 15-22 px, pas pour de l'appareil à 12.

Dans la section de notes, la note *est* le contenu, lue en défilement, et
garde `note.size`.

Le sélecteur de `note.local.size` est `.notes-local .note-body`, à
(0,2,0), et cette spécificité est portante : `article.size` pilote
`.full-article ol` à (0,1,1), qui battait un `.note-body` nu à (0,1,0).
Une taille de note énoncée pour les notes de l'article de fond — là où
l'emplacement par défaut les met — était donc simplement ignorée :
déclarée 14 px, calculée 15 px, et le bloc héritait au passage d'un
retrait de 24 px et de ses puces. C'est la même classe de défaut que
l'alignement d'instance (§9.6) : **un axe émis mais perdant est pire
qu'un axe absent**, puisque `settings.conf` le liste et qu'`audit` le
compte. Il n'est pas tranchable sur le papier — `.fact-content h2` bat
`.note-back` par spécificité et ne peut jamais le sélectionner — donc la
vérification se fait dans un navigateur, valeur déclarée contre valeur
calculée, dans les trois contextes.

#### 6.5.5 Les trois défauts qu'`audit` nomme

Aucun n'est fatal — le contrat d'entrée ne se casse pas sur une bévue
éditoriale — donc c'est `audit` qui les fait remonter, et il suit
l'emplacement en vigueur (un appel en fiche 3 vers un corps en fiche 2
est un défaut sous `local` et parfaitement correct sous `page`) :

- **un appel sans corps** — une affirmation qui cite une source absente.
  Le repère s'affiche et garde son numéro, mais sans lien.
- **un corps que rien n'appelle** — un reste. Il s'affiche quand même,
  numéroté à la suite et sans lien de retour : perdre du texte écrit par
  l'auteur sur une bévue serait pire.
- **une définition dans un bloc HTML brut** — le HTML brut est reproduit
  verbatim par construction, donc `[^1]: texte` part tel quel dans la
  page. C'est ainsi que la combinaison de `.refs` et des notes, toutes
  deux documentées séparément, produisait une sortie cassée en exit 0.

---

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

## 9. Thèmes et personnalisation : les propriétés typées

La structure HTML des pages (page d'article, page d'index, bloc de
navigation de série) est **fixe** — ce n'est pas un template éditable. Ce
qui se personnalise :

- Le **vocabulaire et les libellés** de l'interface (boutons de
  navigation, matrice de partage, etc.) : via le fichier de langue, pas
  via du HTML — voir §7.
- **L'apparence** : par des **propriétés typées**, écrites dans
  `templates/settings.conf` (des valeurs, §9.3.1), complétées par
  `templates/custom.css` (des règles CSS libres, §9.3.2), par des
  propriétés d'article et par des balises d'instance (§9.6). Il n'y a
  **plus de `templates/style.css`** : la feuille de style est composée en
  mémoire à chaque build et inlinée dans chaque page via `{{css}}`
  (§18.1). Voir §9.8 pour la migration.
- **Le comportement de navigation** (`templates/nav.js`) — inchangé par
  la refonte des thèmes, §9.3.3.
- **Un point d'extension libre pour la page d'index**
  (`templates/index_extra.html`) — §9.3.6.

#### Ce que le moteur de rendu ne fait pas

Une frontière, et elle est normative parce que c'est elle qui empêche ce
§9 de grossir jusqu'à devenir autre chose.

**Le moteur ne calcule aucune couleur.** Résoudre une clarté pour rendre
une teinte lisible, mapper un gamut, séparer deux teintes pour un
dichromate — c'est de l'**ingénierie de thème**, pas du rendu. Le moteur
prend les valeurs qu'on lui donne, les résout, les compose et les émet.

Ce document traite du système qui rend un thème. Il ne traite pas de la
construction d'un thème cohérent, qui relève d'un savoir éditorial et
artistique. Les mêler produirait un moteur qui **juge ses entrées au lieu
de les traiter** — et un auteur ne pourrait plus obtenir la couleur qu'il
a demandée, seulement celle que l'outil aurait jugée acceptable.

C'est la frontière à laquelle se rattachent les entrées de `BACKLOG.md`
qui parlent de gamut et de séparabilité : ce sont des travaux de
catalogue, pas des fonctionnalités du moteur. `theme show` (§11.9.1) ne
la franchit pas non plus — il **mesure** et rapporte, il ne corrige rien.

### 9.1 Le principe et le vocabulaire

**Le vocabulaire d'écriture est une liste plate de propriétés typées ; le
CSS n'est qu'un format d'émission.** Personne n'écrit de CSS pour
paramétrer, personne ne lit le CSS produit pour savoir ce qui existe.
Trois conséquences, et ce sont elles qui justifient tout le reste :

- **La sortie cesse d'être une interface.** L'ancien `style.css` était à
  moitié source, à moitié sortie — d'où tout un appareillage (marqueur de
  personnalisation, marqueur de thème, vérification d'identité octet pour
  octet, `--force` de `series theme set`), et d'où le gel de sa forme, puisque
  des auteurs l'éditaient. La feuille émise n'étant plus qu'un artefact,
  sa structure est libre de changer à chaque version : renommer une
  classe ou réorganiser des règles n'est plus un changement de contrat.
- **Une erreur devient nommée au lieu d'être silencieuse.** Une clé
  inconnue, une valeur hors énumération, une unité inconnue : autant
  d'erreurs localisées à la génération, avec le fichier (et la ligne
  quand elle est connue) dans le message. Le scénario le plus coûteux de
  l'ancienne surface — une variable mal choisie qui ne fait rien, sans un
  mot — devient impossible.
- **Il n'y a plus qu'un seul niveau dans ce qui circule.** La
  superposition existe à l'écriture (cinq couches, §9.3), la fusion la
  résout, et le CSS émis est plat : ce qui peut être résolu à la
  construction l'est ; seul ce qui vise une instance reste dans la page
  sous forme de cascade (§9.6).

Le vocabulaire — fixé aussi, en anglais, par `GLOSSARY.md`
(« Presentation vocabulary »), qui est le contrat de vocabulaire partagé
avec le projet GUI :

| Terme | Définition |
|---|---|
| **propriété** | Un réglage typé, nommé `composant.axe` (`tag.fg`, `cover.bg.angle`). Le seul vocabulaire qu'un auteur écrit. |
| **composant** | Une chose que le format nomme et que la page rend — `tag`, `summary`, `verdict.partial`. Les propriétés appartiennent aux composants. |
| **axe** | Le dernier segment d'une clé : ce qu'elle règle (`fg`, `size`, `weight`, `shadow.blur`). L'axe fixe le type, le type fixe l'espace de recherche des renvois (§9.2). |
| **valeur partagée** | Une couleur (`color.*`) ou une pile de polices (`font.*`) fournie par le thème et référencée par les propriétés. Jamais lue directement par une règle émise. |
| **couche** | Un dictionnaire de propriétés dans la cascade (§9.3) : défauts, thème, settings, article, instance. |
| **mobilier** | Famille descriptive, pas un mécanisme : les propriétés qui peignent l'appareil de la page plutôt que son contenu — filets, voiles de surface, fonds en creux, pastilles de contrôle, voile de modale. Des propriétés ordinaires ; le mot permet seulement d'en parler collectivement. |
| **squelette** | Le CSS statique de mise en page qu'aucune propriété ne pilote : flex, grid, espacements, media queries. Pas une surface éditable. |

**Pas de couche sémantique.** Une propriété porte le nom du **composant**
qu'elle peint, repris du vocabulaire que le format fixe déjà — `tag`,
`summary`, `highlight`, `fact-label`, `source`, les verdicts, la
couverture. Ce sont des faits, pas des jugements : on peut pointer la
chose du doigt. Aucune catégorie intermédiaire n'est inventée : le seul
groupement de l'ancien système — `--accent` pour l'appel de note, le
verdict « partiellement » et l'anneau de focus — était un accident, pas
un besoin. La coordination ne disparaît pas pour autant : elle se loge
dans le **défaut** de chaque propriété, qui pointe vers une valeur
partagée du thème. Le piège inverse — un jeton par occurrence
(`footnote-marker-hover-color`) — est écarté par une raison solide : la
liste des composants est close et déjà spécifiée ailleurs.

**Ce que l'antériorité dit de ce choix**, parce qu'un accident local ne
suffit pas à fonder une architecture. Enquête menée avant la refonte, sur
les systèmes de jetons et les catalogues de thèmes existants :

- La norme de l'industrie est **deux niveaux** de jetons, pas trois. Le
  troisième — le niveau *composant* — est celui que tout le monde
  regrette. Les générateurs comparables en ont deux (reveal.js, Quarto,
  mkdocs-material) ou zéro (Hugo, Zola, Eleventy).
- Le seuil de rentabilité d'une couche sémantique se situe au **troisième
  ou quatrième thème**. Ce catalogue en compte trente-trois : elle
  serait rentable ici, si elle n'était pas d'abord un troisième niveau.
- La trajectoire **base16 → base17 → Tinted** est le précédent le plus
  proche, et il est allé à son terme : seize emplacements à sémantique
  figée remplis par des palettes tierces, puis des critiques documentées
  de rigidité et de lisibilité — dont « deux sens distincts partagent un
  emplacement et ne peuvent plus être séparés » —, puis une réécriture
  d'un coup (base17) **abandonnée**, ses mainteneurs préférant enrichir
  par étapes. La leçon d'ingénierie n'est pas « faites une couche
  sémantique », c'est **séparez palette et usage, et faites-le par
  étapes**. C'est la direction suivie ici.
- `contrast-color()` en CSS natif, disponible partout depuis avril 2026,
  **ne répond pas au besoin** : il ne rend que du noir ou du blanc. À
  savoir avant de le redécouvrir.
- Le standard DTCG (Design Tokens Community Group) n'est **pas** suivi —
  brouillon d'un groupe communautaire, JSON plus résolveur d'alias plus
  détection de cycles plus gestion de types, pour un outil qui n'échange
  de jetons avec personne. Trois idées en sont retenues quand même : un
  alias est une valeur légitime, une dépréciation porte un message qui
  explique, et **les cycles doivent être détectés** — ce dernier point est
  implémenté (§9.2 les détecte et les nomme).

**Les valeurs partagées.** Six couleurs et quatre piles de polices,
fournies par un thème et consommées par les défauts des propriétés de
composant :

| Valeur | Sert de défaut à (entre autres) |
|---|---|
| `color.page` | fond de page (`page.bg`), encre de couverture sur thème clair (`cover.fg`), fond des contrôles de partage |
| `color.ink` | texte courant (`page.fg`), **résumé de fiche (`summary.fg`)**, contenu d'encadré, titres du corps, tête de tableau, trait des liens (`link.decoration-color`) |
| `color.ink-quiet` | tag, numéro de fiche, étiquette d'encadré, source, pied de page, citation, légende, références, verdict « non », libellés et descriptions de cartes |
| `color.mark` | filet d'encadré (`fact.rule-fg`), tag de couverture, fond du gras d'encadré (`fact.strong.bg`), filet d'en-tête d'index, point de navigation actif, colonne `col-snap` |
| `color.call` | appel de note, verdict « partiellement », anneaux de focus |
| `color.affirm` | verdict « oui » |
| `font.text` | le corps (`page.font`) ; `font.display` y renvoie par défaut — `font.ui` est une pile sans distincte depuis B9 (§9.5.1) |
| `font.display` | titres (`title1.font`, `title2.font`), chiffre-clé, en-tête d'index |
| `font.ui` | tags, étiquettes, sources, pieds de page — le petit appareil textuel |
| `font.mono` | code, pastille de version — la seule pile monospace correcte, écrite une fois |

Deux précisions, chacune corrigeant une erreur qui a coûté cher :

- **Le résumé de fiche (`summary.fg`) est peint par `ink`, pas par
  `ink-quiet`.** Quatre surfaces de documentation ont affirmé le
  contraire pendant plusieurs versions ; qui suivait la doc pour foncer
  ses résumés redéclarait `--ink-muted` et obtenait zéro effet sur sa
  cible et vingt effets hors cible, dont le verdict « non ». La table
  ci-dessus est dérivée du registre, pas rédigée de mémoire.
- **Chaque emploi est une propriété distincte dont la valeur partagée
  n'est que le défaut.** Modifier un sens ne déplace plus les autres :
  `verdict.partial.fg: #8A4B00` recolore le verdict « partiellement »
  sans toucher à l'appel de note ni aux anneaux de focus, qui ne
  partagent avec lui qu'un défaut, pas une variable.

**La règle de complétude.** *Une propriété non exposée est une décision
confisquée au thème.* C'est le critère de qualité du système, vérifié
par construction : l'émission du CSS est dérivée du registre des
propriétés, donc toute valeur qu'une règle émise consomme est une
propriété, et réciproquement. Le coût assumé est une surface large — une
cinquantaine de composants sur une dizaine d'axes ; une liste longue
reste lisible là où une hiérarchie profonde ne l'est plus. Le **nombre**
de propriétés n'est jamais écrit à la main dans une surface de
documentation : il est **dérivé du registre** (`len(PROPERTY_REGISTRY)`)
et affiché par `--help` — le décompte de l'ancien système a dérivé
(« vingt et une variables » pour vingt-deux substituées) précisément
parce qu'il était rédigé.

La contrepartie de la complétude est la **rigidité** : l'auteur ne peut
exprimer que ce que le vocabulaire admet. Elle est bornée par
`custom.css` (§9.3.2), qui est du CSS complet et sans sous-ensemble. La
rigidité n'est jamais un mur, seulement un aiguillage — soit c'est un
réglage et il est typé, soit c'est une règle et elle est libre.

### 9.2 Les types et les renvois

Une propriété s'écrit `composant.axe: valeur`, dans l'idiome
`clé: valeur` que le format d'article emploie déjà. Chaque axe a un type,
et le type est vérifié à la génération :

| Type | Exemple | Vérifié |
|---|---|---|
| couleur | `#E8A33D`, `#E8A33DFF`, `transparent` | forme hexadécimale `#RGB`/`#RGBA`/`#RRGGBB`/`#RRGGBBAA`, normalisée en **ARGB huit chiffres** majuscules (`#RRGGBBAA`) ; `transparent` ≡ `#00000000` |
| longueur | `4px`, `1.5rem`, `0`, `auto`, `clamp(1rem, 2vw, 1.375rem)` | unité connue (`px rem em ch vw vh % pt`) ; les fonctions `clamp`/`calc`/`min`/`max` passent telles quelles |
| ratio | `1.5` | nombre **sans unité**. Délibérément distinct d'une longueur : un `line-height` sans unité est hérité comme facteur et remultiplié par la taille de chaque descendant ; `1.5rem` est hérité comme longueur figée et casse dès qu'un enfant change de taille — invisible jusqu'au jour où ça mord, ce qui est exactement ce que le typage existe à prévenir |
| angle | `200deg` | unité connue (`deg rad turn grad`) |
| pile de polices | `Georgia, serif` | **se termine par un générique CSS 2.1** (`serif`, `sans-serif`, `monospace`, `cursive`, `fantasy`) — voir ci-dessous |
| énumération | `bold`, `italic`, `uppercase`, `line-through` | valeur admise. Les graisses n'admettent que **`normal` et `bold`** — voir ci-dessous |
| chaîne CSS | `"\25D0"`, `none` | une **seule chaîne entre guillemets doubles** (les marqueurs de forme des verdicts), échappements `\` autorisés, ni guillemet nu ni `<` ni `}` — ou le mot-clé `none`. Le type paraît anodin, mais la valeur atterrit dans le `<style>` inliné de la page : une accolade nue y fermerait la déclaration, un `</style>` littéral la feuille entière — c'est le seul axe dont une valeur voyage sans transformation, donc le seul à devoir se garder lui-même |

**Pourquoi les piles finissent sur un générique.** Aucune police nommée
n'est garantie : Arial et Times New Roman sont absents d'un Linux de base
et de la plupart des Android — nommer une police est un vœu. Le seul
plancher réel est celui des génériques CSS 2.1, que le moteur du
navigateur **doit** résoudre vers une police réelle. Tout ce qui précède
le générique est une chance ; le générique est la promesse. La règle est
vérifiable en une ligne et n'interdit rien. Le message d'erreur la
rappelle. (Les familles `ui-*` sont propres à Safari : utiles en tête de
pile, jamais en ancre.)

**Pourquoi deux graisses seulement.** Sur une famille à deux graisses —
le cas courant d'un générique — l'algorithme d'appariement CSS rend 400
pour 500 et 700 pour 600 comme pour 700 : trois graisses déclarées
s'effondrent en deux, et « partiellement » redevient indistinguable de
« oui ». Seules `normal` et `bold` sont fiables, parce que ce sont les
seules que CSS garantit de produire, au besoin par synthèse. Le motif
figure dans le message d'erreur. (C'est aussi ce qui justifie, après
coup, le marqueur de forme des verdicts, mieux que l'argument
d'accessibilité qui l'avait motivé — §6.1.) De même, le piège de taille
de `font-family: monospace` ne peut plus mordre : la complétude impose
une taille explicite à chaque composant portant du texte, donc le défaut
divergent des moteurs n'est jamais consulté et le contournement
historique `monospace, monospace` devient inutile.

**Les renvois.** Un renvoi est un mot, pas une fonction, et il est résolu
à la fusion — il ne survit jamais dans la sortie :

- **Un mot nu est cherché dans l'espace de son type** : l'axe fixe le
  type, le type fixe l'espace. `tag.fg: ink-quiet` se lit
  `color.ink-quiet` parce que `fg` est une couleur ;
  `page.font: mono` se lit `font.mono`. C'est toute la règle — le
  moteur ne devine jamais si une valeur « ressemble » à une clé : un
  littéral se reconnaît à sa forme (une couleur commence par `#`, une
  pile contient une virgule ou est un générique).
- **Un mot pointé référence une autre propriété**, qualifiée :
  `title1.fg: cover.fg`, `cover.bg.to: cover.bg.from`.
- **Profondeur maximale : 3 sauts.** Les chaînes étant résolues à la
  génération, la limite ne protège que le lecteur d'un fichier de
  settings. Deux sauts se sont avérés trop courts le jour où le thème
  `terminal` du catalogue a eu besoin de `page.font → font.text →
  font.mono` : un thème ordinaire saturait la limite et ne laissait à
  une série aucune indirection propre.
- **Les cycles sont détectés et nommés** : `tag.fg: reference cycle
  tag.fg -> summary.fg -> tag.fg`, jamais une boucle infinie ni un
  plantage obscur.
- **Une clé inconnue est une erreur** qui suggère la clé voisine quand
  l'axe correspond (`did you mean …?`) ; un renvoi vers une propriété
  inexistante est une erreur qui rappelle la règle de l'espace de
  recherche.

### 9.3 La cascade à cinq couches et les trois fichiers

```
   défauts intégrés  →  thème  →  templates/settings.conf  →  propriétés d'article
        └────────── fusion, résolution des renvois, typage ──────────┘
                                   ↓
                        CSS composé en mémoire, par page
                                   ↓
              inliné dans la page ({{css}})   +   templates/custom.css
                                   ↓
                      balises d'instance (§9.6)  →  cascade
```

**La chaîne n'est pas homogène, et la couture doit être vue.** Les quatre
premières couches se résolvent **avant l'émission** : le moteur fusionne
des dictionnaires — rien à arbitrer, pas d'ordre de règles, pas de
spécificité. Le CSS est composé **par page** (il est inliné dans chaque
page via `{{css}}`, §18.1), donc la personnalisation par article (§9.6)
ne coûte qu'un jeu de propriétés différent pour cette page. La cinquième
couche — les balises d'instance — ne **peut pas** fonctionner ainsi :
elle vise une instance, pas une page (deux passages balisés dans le même
article doivent pouvoir différer) ; elle passe donc par des styles en
ligne, donc par la cascade. La couture est là, entre « par page » et
« par instance ».

**La feuille composée** est faite de trois parts, dans cet ordre :

1. le bloc `:root` — une variable CSS par propriété
   (`tag.fg` → `--tag-fg`), toutes valeurs résolues ;
2. les règles pilotées, dérivées du registre — chaque règle ne lit que
   des variables de composant, jamais une valeur partagée directement
   (un seul saut jusqu'à une valeur, le CSS reste lisible tel quel) ;
3. le **squelette** statique — la mise en page seule : tout ce qu'aucune
   propriété ne pilote. C'est un **littéral** (`TEMPLATE_SKELETON`), et
   non plus une extraction faite au vol sur l'ancienne feuille : ce qu'on
   y lit est exactement ce qu'une page reçoit, éditer une ligne n'y est
   jamais un no-op silencieux. Ses `@media` passent **après** les règles
   du moteur : à spécificité égale, l'ordre les fait gagner, ce qui est
   exactement leur raison d'être. Deux invariants, tenus par des tests
   plutôt que par un garde-fou d'extraction : aucune déclaration n'est
   pilotée des deux côtés à la fois (le littéral périmé gagnerait
   silencieusement, venant après), et aucune ne référence de variable
   hors `--content-max` — un tel reste serait une décision visuelle que
   le registre n'expose pas, donc une décision confisquée (§9.1).

`templates/custom.css` (§9.3.2) est ajouté **en dernier**, après la
feuille composée. Rien de tout cela n'atteint le disque : la feuille
peut n'exister qu'en mémoire et reste intégralement consultable — elle
est inlinée dans chaque page, il suffit d'en afficher la source.

**Les trois fichiers, un propriétaire chacun :**

| Fichier | Propriétaire | Écrit par le système |
|---|---|---|
| feuille émise | le système | régénérée à chaque build, jamais sur disque |
| `templates/settings.conf` | l'auteur | **jamais**, sauf demande explicite (`series theme set` réécrit la seule ligne `theme:`, §9.4.2) |
| `templates/custom.css` | l'auteur | **jamais** (créé vide à l'init) |
| `templates/nav.js` | l'outil | remplacé par `template update`, sauvegarde `.bak` (§9.4.3) |

**C'est ce partage qui supprime l'appareillage.** Le marqueur de
personnalisation, sa variante héritée, la recherche de sa première
occurrence, la vérification d'identité octet pour octet, le `--force` de
`series theme set`, le `[SKIP]` sans marqueur : une dizaine de mécanismes dont
l'unique raison d'être était que le système écrivait dans le fichier que
l'auteur édite. La bonne façon de ne pas détruire le travail de
quelqu'un n'est pas de le détecter, c'est de ne pas écrire là où il est.

#### 9.3.1 `templates/settings.conf` : les valeurs, et le scaffold

Le format est celui du bloc meta d'un article : des lignes
`clé: valeur`, des commentaires `#`, rien d'autre. Deux clés spéciales :
`theme: <slug>` choisit le thème de la série (absente, la série est sur
les défauts intégrés), et `# scaffold-for: <slug>` — un commentaire —
enregistre le thème sous lequel le fichier a été généré, ce qui permet à
`audit` de signaler un scaffold désaccordé (§9.4.4).

**Les erreurs sont nommées.** Une ligne qui n'est pas `clé: valeur` est
une erreur qui donne le fichier et la ligne, et rappelle que les règles
CSS vont dans `custom.css` — un fichier qui ressemble à des propriétés
et avalerait du CSS en silence serait l'ancienne surface de retour. Une
clé inconnue, une valeur mal typée, un renvoi cassé sont des erreurs de
`build` qui nomment la clé (§9.2). Un `theme:` inconnu nomme la ligne et
renvoie vers `lightwebpres theme list`.

**Le scaffold.** Le fichier est généré **une fois** (à l'init, §9.4.1)
avec **toutes** les propriétés présentes, en commentaire, à la valeur du
thème choisi — les renvois montrés comme des mots
(`# tag.fg: ink-quiet`), parce que c'est le vocabulaire que l'auteur
écrit. Décommenter une ligne l'**épingle** : elle survit à tout
changement de thème et à toute montée de version. Le scaffold règle
trois problèmes d'un coup : la découvrabilité — la surface complète est
sous les yeux, sans documentation (il remplace ainsi le bloc de
« recettes prêtes à coller » de l'ancienne feuille, qui ne couvrait
qu'un seul objet et dont le compte annoncé avait dérivé) ; la mise à
jour — `template update --scaffold` (§9.4.3) régénère à la demande la
surface commentée pour le thème courant, en gardant les lignes
épinglées : les propriétés apparues et disparues se lisent comme un diff
; et la dérive de la documentation, puisque le
fichier est **généré depuis le registre**, la structure même qui émet le
CSS, jamais tenu à la main — sinon il deviendrait une seconde source de
vérité.

**Il n'est jamais réécrit d'initiative.** Ses commentaires vieillissent
quand le thème change ; le remède est de le **signaler** (`audit`
compare `scaffold-for` au `theme:` déclaré, §9.4.4), pas de l'écraser —
le fichier appartient à l'auteur. Les valeurs épinglées, elles, restent
volontairement en place à travers un changement de thème : le système
sait quelles clés sont épinglées et depuis quel thème ; il ne les touche
pas, il peut le dire.

#### 9.3.2 `templates/custom.css` : les règles

Du CSS complet, sans sous-ensemble, jamais écrit par l'outil (installé
vide, avec un commentaire d'usage). Il est ajouté **après** la feuille
composée, donc ses règles gagnent tout arbitrage à spécificité égale.
C'est la borne de la rigidité du vocabulaire (§9.1) : tout ce que les
propriétés ne savent pas dire — une règle nouvelle, un sélecteur
d'exception, une media query, un `@font-face`.

Les variables `--composant-axe` de la feuille composée y sont utilisables
(`border-color: var(--color-mark)`), et c'est la façon recommandée d'y
référencer la palette : la règle suit alors le thème. `audit` signale
tout nom de variable **retiré** encore référencé (§9.8) — une
déclaration `var()` qui ne résout rien ne peint rien et ne dit rien.

Aucune police n'est embarquée par l'exécutable — ce serait 300 Ko de
binaire dans un fichier unique. Mais l'auteur peut le faire lui-même : un
`@font-face` dans `custom.css`, la famille nommée en tête de pile dans
`settings.conf`. Le moteur n'a rien à en savoir ; c'est une raison de
plus de garder `custom.css`.

#### 9.3.3 JS (`nav.js`)

Le JavaScript de navigation gère :
- Le scroll entre slides (flèches, PageUp/PageDown)
- Les boutons prev/next/home
- Les nav-dots (points de navigation)
- La détection de la slide courante au scroll
- Le bouton de partage et sa matrice (§9.3.4)
- Le parcours clavier complet (flèches Haut/Bas) : fiche par fiche, puis
  carte par carte sur la fiche series-nav, puis défilement par
  incréments sur une fiche plus grande que l'écran (§9.3.5)

Éditable via `templates/nav.js` — un override remplace `nav.js` **en
bloc**, y compris le bouton de partage : il n'y a pas de mécanisme pour
ne remplacer qu'une partie du comportement de navigation.

#### 9.3.4 Bouton de partage

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
  nav-dots, §9.3.3). Elle n'a de sens que pour une slide standard ou
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

#### 9.3.5 Parcours clavier (flèches Haut/Bas)

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

#### 9.3.6 Extension de la page d'index (`index_extra.html`)

La structure de la page d'index reste fixe, mais un site migré ou une
fonctionnalité maison (bouton, modale, script tiers...) peut avoir besoin
d'un point d'ancrage que `settings.conf`/`custom.css`/`nav.js` ne
couvrent pas (`nav.js` ne s'applique qu'aux pages d'article, pas à
l'index). Si `templates/index_extra.html` existe, son contenu est inséré
tel quel (HTML, CSS inline, `<script>`... — aucune transformation) juste
avant `</body>` de la page d'index générée. Absent par défaut : `init`
ne crée pas ce fichier, contrairement à `settings.conf`/`custom.css`/
`nav.js`.

### 9.4 Les commandes

Le détail CLI (options, codes de sortie) est en §11 ; cette section fixe
le **comportement** de chaque commande vis-à-vis des trois fichiers.
`build` lui-même n'a pas de sous-section : il lit `settings.conf` (et
avertit si un `templates/style.css` hérité traîne encore, §9.8), compose
la feuille (§9.3), la recompose pour toute page portant des propriétés
d'article (§9.6), et échoue avec une erreur nommée sur la première
propriété invalide.

#### 9.4.1 `init --theme`

`init` écrit les trois fichiers : `settings.conf` — le scaffold
complet du thème choisi, avec sa ligne `theme: <slug>` et son
`# scaffold-for: <slug>` (sans `--theme` : pas de ligne `theme:` active,
scaffold aux défauts intégrés) —, `custom.css` (le gabarit commenté,
vide de règles) et `nav.js`. Aucune substitution dans du CSS : choisir
un thème à l'init, c'est écrire un mot dans un fichier de données. Un
slug inconnu est une erreur fatale qui liste les slugs valides.

#### 9.4.2 `series theme set`

`series theme set [répertoire] --theme <slug>` réécrit **la seule ligne du
fichier qui soit à l'outil** : la ligne `theme:` de `settings.conf` (ou
le placeholder commenté `# theme:` du scaffold, ou en tête de fichier si
ni l'un ni l'autre n'existe). Tout ce que l'ancienne implémentation
gardait — fichiers à moitié recolorés, marqueurs mentant sur le thème,
`--force` — existait parce que l'outil écrivait dans le fichier que
l'auteur édite ; il n'y a plus rien à garder, et **`--force` n'existe
plus**. Comportements, tous vérifiés :

- répertoire jamais installé (pas de `templates/`) : erreur propre
  renvoyant vers `init` — `series theme set` configure une série, il n'en
  crée pas ;
- `templates/` présent mais pas de `settings.conf` (série d'avant la
  refonte) : un scaffold neuf est écrit pour le thème demandé — écrire
  un fichier qui n'existe pas ne trahit aucune promesse de propriété ;
- thème déjà en place : `Theme unchanged`, rien n'est écrit ;
- sinon : `Theme changed: <ancien|default> -> <nouveau>`, et le message
  rappelle que les valeurs décommentées restent en place et s'appliquent
  par-dessus le nouveau thème, et que les commentaires du scaffold
  montrent encore l'ancien (ce que `audit` signale, §9.4.4).

Les valeurs épinglées survivent **volontairement** : elles sont la
sémantique voulue par l'auteur. Le risque résiduel — des valeurs
calibrées pour l'ancienne palette — est rendu **visible** (`audit`),
jamais corrigé d'office.

#### 9.4.3 `template update`

Sous le modèle de feuille composée, la feuille est toujours fraîche par
construction : elle vient de l'exécutable courant à chaque build. Le seul
fichier de l'outil restant sur disque est `nav.js` — remplacé s'il
diffère de la version intégrée, l'ancien sauvegardé en
`templates/nav.js.bak` ; rapporté « already up to date » sinon. Plus de
marqueur, plus de `[SKIP]`. En complément, la commande **crée** les
fichiers de la surface auteur s'ils manquent (série d'avant la
refonte) : un `settings.conf` neuf (scaffold aux défauts, aucun thème
déclaré) et un `custom.css` vide. Un `templates/style.css` hérité est
**signalé, jamais migré** : ses valeurs sont les décisions de l'auteur,
les déplacer lui revient — `audit` nomme chaque renommage pour rendre le
geste mécanique (§9.8).

**`--scaffold`** est la seule exception à « l'outil ne touche jamais
`settings.conf` », et elle est explicite. Elle régénère la surface
commentée du `settings.conf` existant pour le thème courant — les
propriétés apparues dans une nouvelle version apparaissent, les disparues
disparaissent — **en conservant chaque ligne décommentée** que l'auteur a
épinglée, et en réalignant `scaffold-for:` sur le thème déclaré. C'est
l'action que `audit` recommande quand les deux divergent, et le seul moyen
de voir les propriétés d'une nouvelle version sans fusion à la main. Une
propriété épinglée que le registre ne connaît plus n'est pas perdue : elle
passe, commentée, dans une section « no longer recognized » en fin de
fichier — préservée d'une régénération à la suivante, jamais
silencieusement supprimée — avec un avertissement, car un build la
rejetterait.

#### 9.4.4 `audit` (volet présentation)

`audit` (§11.5) avertit, ne bloque jamais. Trois yeux sur la surface de
présentation, chacun vérifié :

1. **`templates/style.css` hérité** : le fichier n'est plus lu ;
   l'avertissement le dit et énumère chaque variable retirée qu'il
   référence encore, avec son remplaçant (table de §9.8).
2. **Noms retirés dans `custom.css`** : une déclaration `var(--marker)`
   ne résout plus rien — elle ne peint rien et ne dit rien ;
   l'avertissement la nomme, avec le remplaçant.
3. **`settings.conf`** : une erreur de syntaxe ou de propriété (mêmes
   messages qu'au build, mais non bloquants ici) ; et un
   `scaffold-for:` différent du `theme:` déclaré — décommenter une ligne
   épinglerait une valeur du thème quitté ; l'avertissement renvoie à
   `template update --scaffold` (§9.4.3), qui réaligne la surface
   commentée sans perdre les épingles.

`audit` énumère aussi, par article, les **balises d'instance** (§9.6) —
une note informative (`[NOTE]`, pas un avertissement compté) : ce sont
des interventions d'auteur qui survivent à tout changement de thème, et
cette visibilité est ce qui rend les littéraux dans le texte acceptables.

### 9.5 Thèmes de couleurs prédéfinis

#### 9.5.1 Le catalogue, et sa conversion en couche de propriétés

Une table `THEMES`, embarquée dans l'exécutable, associe un nom court
(« slug ») à une entrée : six couleurs de rôle (`page`, `ink`,
`ink-muted`, `marker`, `accent`, `positive`), les propriétés de rendu du
gras en encadré (`fact_weight`/`fact_style`/`fact_highlight`/
`fact_decoration`/`fact_decoration_color`), un drapeau de polarité
(`dark_background`), une intensité déclarée (`intensity`, §9.5.2), et des
métadonnées purement éditoriales (étiquette affichable, source,
remarque — §9.5.4) qui ne servent qu'à `theme gallery` (§11.7).
`fact_weight`, `fact_style` et `fact_highlight` sont toujours explicites
dans chaque entrée, même à la valeur par défaut — un choix délibéré
consigné, pas un oubli ; les deux clés de soulignement font exception :
absentes, elles valent « pas de soulignement », le sens de « pas
d'avis » pour un axe ajouté après coup. `THEMES` est la **seule** source
de vérité : la couche appliquée par `init --theme`/`series theme set` et les
aperçus de `theme gallery` viennent de la même donnée et ne peuvent pas
diverger par construction.

Les neuf premières entrées reprennent des palettes d'éditeurs de code
connues (`nord`, `dracula`, `solarized`, `gruvbox`, `catppuccin`,
`tokyo-night`, `monokai`, `everforest`, `rose-pine`) ; le catalogue
s'est ensuite élargi à des thèmes propres au projet
(`source: 'lightwebpres'`). Le nombre exact d'entrées n'est pas figé par
cette spécification — c'est justement pourquoi les facettes (§9.5.2)
existent : au-delà d'une trentaine de thèmes, une liste plate n'est plus
un moyen de choisir.

**La conversion.** Une entrée `THEMES` devient une couche de propriétés
(`theme_property_layer()`), et ce que `dark_background` faisait basculer
en douce derrière le dos du thème, la couche le **dit** :

- les six rôles deviennent les six valeurs partagées (`page` →
  `color.page`, `ink-muted` → `color.ink-quiet`, `marker` →
  `color.mark`, `accent` → `color.call`, `positive` → `color.affirm`) ;
- sur un thème **sombre**, le **mobilier** s'inverse par une table
  partagée unique (`DARK_FURNITURE_PROPS`) : les voiles noirs des filets
  deviennent des voiles blancs, les surfaces claires des voiles blancs
  faibles, les creux des voiles noirs profonds — des couleurs ARGB
  ordinaires, plus un jeu caché substitué hors de la vue du thème. Les
  thèmes clairs n'ont pas de table : les défauts du registre **sont** le
  jeu clair ;
- la **couverture** cesse de s'inverser sur un thème sombre : son fond
  est un voile noir posé sur la page (`cover.bg.from: #00000073`) —
  jamais `ink`, qui y porte la couleur du **texte** — et son encre est
  `ink` ; les deux opacités mesurées du résumé et du numéro de
  couverture sont réénoncées en ARGB **contre la palette réelle** (alpha
  `C7`, le 0,78 mesuré ; `8F`, le 0,56) au lieu de présupposer la
  palette par défaut. Sur un thème clair, seule `cover.summary.fg` est
  réénoncée (`page` du thème + alpha `C7`) pour que la mesure suive ;
- les clés `fact_*` deviennent `fact.strong.*`. Deux axes y vont **par
  paire**, et la paire est la règle : `fact.strong.bg` (le fond façon
  `<mark>`) avec `fact.strong.fg` (l'encre posée dessus), et
  `fact.strong.decoration` avec `fact.strong.decoration-color`. L'encre
  est **dérivée**, jamais déclarée dans une entrée : `page` sur un thème
  sombre (où c'est le ton foncé), `ink` sur un clair — pour qu'un thème
  ne puisse pas se donner une encre illisible sur son propre marqueur
  (le contraste avait été mesuré à 1,00 avant que l'axe existe). Un
  `fact_highlight` valant explicitement `None` — cinq thèmes du
  catalogue — donne `transparent` + encre héritée : pas de fond du tout,
  ce qui n'est pas la même chose que ne rien dire (l'absence de clé
  retombe sur le défaut, le fond `mark`). Changer le fond sans revoir
  l'encre peut tomber sous le seuil de lisibilité — un vert `affirm`
  sous l'encre par défaut mesure 3,14:1 sur High Contrast et 2,14:1 sur
  Pop Lemon, deux échecs AA — c'est exactement pourquoi l'axe `fg`
  existe et pourquoi la paire est documentée ici ;
- enfin, des **surcharges par slug** (`THEME_PROPERTY_OVERRIDES`)
  portent ce que l'ancienne forme d'entrée ne savait pas dire :
  `terminal` passe tout le texte en chasse fixe
  (`font.text`/`font.display`/`font.ui: mono` — trois lignes, c'est ce
  que le nom du thème promet) et pose un halo phosphore sur ses titres
  et son chiffre-clé (`title1.shadow.*`, `highlight.shadow.*`, §9.7) ;
  `dracula` et `tokyo-night` passent leur seul **appareil** en chasse
  fixe (`font.ui`), le corps restant sur la serif de lecture ; `monokai`
  y passe tout, et sort son rose du texte (`verdict.partial.fg`,
  `footnote-call.fg`) parce qu'il franchit 3:1 sans franchir 4,5:1 ;
  `everforest` élargit ses interlignes.

**Défauts typographiques (B9).** Une serif pour lire, une sans pour
l'appareil. La pile système unique d'avant donnait la même voix au
corps, aux titres, aux tags et aux tableaux, et rendait le produit
identique à n'importe quelle page web. Le petit appareil textuel — tags,
numéros de fiche, étiquettes d'encadré, sources, pieds de page — est de
la signalétique, pas de la prose. `font.display` renvoie à `text` : le
contraste titre/corps est déjà porté par la taille et la graisse, et une
troisième famille par défaut serait un pari ne tenant sur aucune
plateforme sans les polices nommées — c'est aux **thèmes** de diverger
sur `display`. Toutes les piles finissent sur un générique CSS 2.1,
seule chose réellement garantie ; les noms sont un bonus là où ils
existent. `font.ui` n'est délibérément **pas** menée par `system-ui`,
qui rendrait la police de l'OS, c'est-à-dire l'absence de choix qu'on
quitte.

**Quatre palettes empruntées rendues à leur propre fond (B9).** Une
palette de coloration syntaxique distribue la *teinte* à clarté quasi
constante — c'est son cahier des charges, pour qu'aucun token ne hurle
plus fort qu'un autre — donc elle ne peut pas, par construction, peindre
du texte sur un papier clair. Ce n'était pas une affaire de valeurs à
retoucher : `dracula`, `tokyo-night`, `monokai` et `everforest` sont
désormais `dark_background`, sur les fonds pour lesquels elles ont été
dessinées. Mesuré, **aucun de leurs rôles de texte n'est plus sous AA**,
là où `dracula` affichait 1,29:1 et `tokyo-night` 1,41:1. C'est une
restauration de fidélité autant qu'une correction de lisibilité : le
catalogue rendait Tokyo Night avec les accents *Night* posés sur le fond
*Day*, ce qui n'est ni l'un ni l'autre.

Les deux thèmes qui emploient le soulignement du gras d'encadré sont
`monochrome` et `graphite`, et ce n'est pas arbitraire : ce sont les
deux palettes qui s'interdisent la teinte, et un soulignement est une
forme, pas une teinte. Elles couvrent les deux emplois de l'axe —
`monochrome` cumule surlignage **et** soulignement, `graphite` souligne
**à la place** — sur les deux polarités de fond. Un `mark` fait pour
servir de fond est souvent trop pâle pour servir de trait (mesuré à
1,23:1 sur `newsprint`, 1,49:1 sur `blueprint`) : d'où le trait laissé à
l'encre du texte sur `monochrome`, et en `mark` sur `graphite` seulement
parce que ce thème est sombre, où le même gris ressort à 11,3:1.

#### 9.5.2 Critères d'admission d'un thème, et facettes

**Admission.** Les thèmes propres au projet (`source: 'lightwebpres'`)
sont dessinés puis **mesurés** avant d'être retenus, jamais retenus sur
l'impression qu'ils font :

- texte courant sur le fond : niveau AAA (rapport ≥ 7) ;
- textes secondaires et accents : niveau AA (≥ 4,5) ;
- filets et bordures : ≥ 3 ;
- verdicts d'un tableau comparatif (§6.1) : séparables en vision
  deutéranope et protanope — la couleur n'étant de toute façon jamais le
  seul porteur de l'information, puisque chaque verdict porte aussi son
  marqueur de forme (WCAG 1.4.1).

**Cette section décrit le critère d'admission, pas un état vérifié du
catalogue, et la différence a été mesurée.** Cinq entrées du projet sont
aujourd'hui **en dessous** et n'ont pas été corrigées : `blueprint`,
`sage`, `sprout`, `dread` et `vaporwave`, sur neuf rôles au total
(textes secondaires ou accents entre 2,02:1 et 4,52:1). Le critère
« filets ≥ 3 » n'est pas davantage tenu par `mark` sur les thèmes clairs
du projet, où il est fait pour servir de fond avant de servir de trait —
le §9.5.1 le dit déjà dans ses propres termes. Les mesures et la
correction restante sont au BACKLOG (B9). La phrase précédente affirmait
le contraire jusqu'ici ; elle était fausse depuis l'admission de ces cinq
thèmes.

**Ces critères n'ont jamais été rétro-appliqués aux neuf palettes
empruntées**, reprises telles quelles de leur source pour la fidélité —
et la mesure faite depuis montre que plusieurs de leurs accents échouent
AA sur fond clair (aucun accent de ces palettes n'atteint 4,5:1 sur
clair ; le pire mesuré descend à 1,29:1). Le choix d'issue — corriger
ces palettes, les basculer en polarité sombre, ou les déclarer offertes
pour la fidélité et non pour la mesure — est un choix éditorial **ouvert
au BACKLOG (B5)** ; cette spécification ne le tranche pas. En attendant,
la promesse est scopée honnêtement : les critères ci-dessus décrivent
les palettes du projet, pas le catalogue entier.

**Facettes.** Passé une douzaine de palettes, une galerie cesse d'être
un moyen de choisir et devient une chose à faire défiler. Trois facettes
décrivent donc chaque entrée ; `theme gallery` (§11.7) les expose en
filtres, et la commande `theme list` (§11.9) en options :

| Facette | Valeurs | Origine |
|---|---|---|
| polarity | `light`, `dark` | dérivée de `dark_background` (§9.5.1) |
| intensity | `sober`, `vivid`, `mono` | déclarée dans l'entrée ; absente, vaudrait `sober`, mais les 33 entrées la déclarent — le repli n'est pas exercé par le catalogue |
| hue | `neutral`, `red`, `orange`, `yellow`, `green`, `cyan`, `blue`, `violet`, `magenta` | **calculée** à partir du fond |

Les noms de facettes et leurs valeurs sont en anglais, comme tout
identifiant que la ligne de commande accepte — et comme la galerie
elle-même, page anglaise depuis la v0.12.1 (ses libellés d'affichage,
« Light », « Sober », restent séparés des valeurs sur lesquelles elle
filtre : une chaîne affichée et une clé ne sont pas la même chose, et
les confondre rendrait la CLI intraduisible).

Une même fonction, `theme_facets()`, alimente les deux surfaces. Un
sélecteur dans un terminal et un sélecteur dans un navigateur ne peuvent
donc pas diverger — propriété vérifiée par un test qui compare, pour
chaque combinaison, la sortie de `theme list` aux attributs `data-*` des
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
seuil, un fond se lit comme du papier ou de l'encre, jamais comme une
teinte, et la facette vaut `neutral`. Le seuil n'est pas fixe — il
**suit la clarté** (`neutral_chroma_threshold(L) = max(4,0 ; 0,25 × L)`),
précisément pour que le papier crème de Gruvbox (C = 21,8) se lise neutre
et que le bleu nuit de Blueprint Night (C = 12,6) ne se lise pas. Les bornes
d'angle ont été calibrées en mesurant des références connues plutôt que
de mémoire : les angles CIELAB ne sont pas ceux que l'intuition RVB
suggère — un bleu franc se situe vers 297°, pas 240°, et le cyan vers
227°.

La teinte est prise sur `color.page`, c'est-à-dire **le fond de la
page** : c'est ce qu'un lecteur voit en premier, et ce qu'il désigne en
disant « un thème vert ». Sur un thème à polarité sombre, `color.page`
porte le fond sombre, donc la même règle continue de s'appliquer sans
cas particulier.

Ces facettes ne changent rien au rendu : elles ne servent qu'à
présenter et à choisir. `init --theme` continue de ne connaître que
des slugs.

#### 9.5.3 Les liens du corps de texte, et le plancher de contraste

**Un lien du corps de texte n'a pas de couleur de palette.** Il hérite de
l'encre qui l'entoure (`color: inherit`) et se signale par un
**soulignement**, dont la teinte est le seul axe exposé :
`link.decoration-color`, à défaut `ink` — le trait a la couleur du texte,
qui ne peut jamais échouer ; un thème ou une série peut le teinter là où
il a mesuré une couleur qui tient. L'héritage et le soulignement
eux-mêmes sont de l'architecture (correctif B3), pas des réglages : ils
ne sont pas exposés.

La règle est portée par `.fact-content a, .full-article a` — les deux
seuls conteneurs dans lesquels le convertisseur Markdown écrit. Elle ne
doit jamais viser `a` nu : cela soulignerait aussi les pastilles de
progression, les cartes de la navigation entre articles et celles de
l'index.

Mesuré sur les 33 thèmes avant de choisir, et c'est ce qui a écarté les
autres options :

- Le bleu par défaut du navigateur, livré jusqu'à la v0.12.1, échoue AA
  sur **19** thèmes et tombe à 1,03:1 sur `pop-violet`. Contrairement
  à ce que BACKLOG B3 supposait, ce ne sont pas seulement les thèmes
  sombres : `pop-tangerine` est un thème clair à 4,27:1.
- `call` échoue AA sur **8** thèmes **et** est la couleur du verdict
  « partiellement », par identité (ΔE = 0) sur 32 des 33 — `monokai` a
  sorti son rose du texte (§9.5.1).
- `affirm` et `ink-quiet` sont les deux autres couleurs de verdict.
  Aucune valeur partagée n'est donc libre, sauf `mark`, utilisable sur
  **18** thèmes sur 33 — tous les sombres.
- `ink` sur `page` est le seul couple sur lequel **tout** thème est
  admis (§9.5.2). Un lien est donc AA et AAA partout par construction, et
  WCAG 1.4.1 est satisfait par le soulignement, qui n'est pas une
  couleur.

**Plancher général.** Aucune règle portant du texte courant ne s'atténue
par `opacity`. Deux le faisaient et échouaient : la carte « en cours de
lecture » du bloc de navigation (1,62:1) et le verdict « non » (1,99:1).
Une exception n'est recevable que **mesurée** : le résumé de couverture
garde son atténuation de 0,78 parce que le résultat composité vaut
5,05:1 au pire (catppuccin) — mais elle est désormais portée par l'alpha
de la couleur elle-même (`cover.summary.fg`, alpha `C7`), pas par une
`opacity` du squelette, et la conversion de thème la réénonce contre la
palette réelle (§9.5.1) ; un test recalcule cette valeur sur les 33
thèmes à chaque exécution. Le texte secondaire de couverture
(`cover.num.fg`) suit la même règle : c'était un `rgba` fixe jamais
mesuré, à 2,37:1 au pire ; ses alphas sont calculés pour tenir AA sur
les deux polarités (0,70 en clair, 0,56 en sombre). Atténuer le fond ne
coûte aucun contraste ; atténuer le texte en coûte toujours.

#### 9.5.4 Le champ `note` d'un thème est du texte nu

Chaque entrée de `THEMES` porte une `note`, et elle a **deux
consommateurs aux besoins opposés** : `theme list` (§11.9) l'imprime dans un
terminal, `theme gallery` (§11.7) la place dans une page HTML.

Elle est stockée **en texte nu**, en UTF-8, et c'est la galerie qui
convertit — jamais l'inverse. Le sens de conversion n'est pas
indifférent : un terminal ne sait pas rendre du balisage, alors qu'on
peut toujours produire du HTML à partir de texte. Le stockage prend donc
la forme qui se dégrade le mieux.

Jusqu'à la v0.12.1 c'était l'inverse — la note était écrite en HTML de
galerie et nettoyée à la volée pour le terminal. Le nettoyage ne retirait
que les balises, et les entités caractères, qui sont l'autre moitié du
balisage, arrivaient telles quelles à l'écran sur huit thèmes. Un
nettoyage énumère ce qu'il connaît déjà : le balisage ajouté ensuite
serait reparti à l'écran de la même façon. Signalé depuis un projet
utilisateur.

Une note peut contenir **une seule** forme de balisage, l'apostrophe
inverse autour d'un nom de variable — la syntaxe de code en ligne du
format lui-même (§6.1) —, et `note_to_html()` l'y convertit après avoir
échappé `&`, `<` et `>`. L'ordre est normatif : échapper d'abord, puis
convertir. Une note est du contenu, jamais du balisage, et le seul élément
qu'elle peut produire est le `<code>` que ses propres apostrophes
demandent.

Verrouillé par test **à la source** — aucune note ne contient `<`, `>`
ni d'entité — et non sur l'affichage : c'est le stockage qui est la
règle, l'affichage n'en est que la conséquence.

### 9.6 La couche article, et les balises d'instance

#### 9.6.1 Propriétés d'article (`style.*` dans le bloc meta)

Toute ligne `style.<propriété>: valeur` du bloc `lwp:meta` d'un article
restyle **cette page seule**, par-dessus le thème et les settings de la
série — quatrième couche de la cascade (§9.3). Même vocabulaire, mêmes
types, mêmes renvois, mêmes erreurs que `settings.conf` :
`style.verdict.partial.fg: #8A4B00`, `style.cover.bg.angle: 90deg`. La
feuille étant composée par page, la recomposition ne coûte qu'une fusion
de plus. Une clé ou une valeur invalide est une erreur fatale du build
qui **nomme le fichier** — une faute de propriété dans un article ne
doit jamais se lire comme un mystère de build.

#### 9.6.2 Variantes de composant (`fact-variant`)

Un auteur qui veut un encadré différent **désigne une variante**, il ne
fixe pas des valeurs : `fact-variant: warning` sur une fiche standard
ajoute la classe `fact--warning` à son encadré. La source porte du sens
(« ceci est un avertissement »), pas une décision visuelle (« ceci est
rouge ») — ce que ça donne à l'écran se définit une fois par série (une
règle `.fact--warning` dans `custom.css`), donc un changement de thème
emporte la variante avec lui. Le nom devient une classe CSS et est
validé comme telle (`[a-z][a-z0-9-]*`, sinon erreur fatale nommant la
valeur). Sans `fact-label:` il n'y a pas d'encadré, donc pas de classe à
accrocher. Le format a un précédent assumé pour ce geste : les classes
de verdict sur une cellule (§6.1) sont déjà un point de personnalisation
documenté.

#### 9.6.3 Balises d'instance

La cinquième couche de la cascade — portée **instance** au lieu de
portée page — avec le même vocabulaire et les mêmes types que les quatre
autres. Des balises **définies par le format**, utilisables dans tout
texte libre (corps de fiche, article de fond) :

| Balise | Effet |
|---|---|
| `{color:#E8A33D}…{/color}` | couleur littérale (hex 3/4/6/8 chiffres, normalisée ARGB) |
| `{color:mark}…{/color}` | une valeur partagée par son nom (`page`, `ink`, `ink-quiet`, `mark`, `call`, `affirm`) |
| `{font:mono}…{/font}` | une pile partagée par son nom (`text`, `display`, `ui`, `mono`), ou une pile littérale finissant sur un générique |
| `{sc}…{/sc}` | petites capitales |
| `{u}…{/u}` | souligné |
| `{strike}…{/strike}` | barré |
| `{align:center}` … `{/align}` | **alignement d'un bloc** — ouvreur et fermeur chacun seul sur sa ligne |

Les balises de forme nues (`sc`, `u`, `strike`, et `mono` comme
raccourci de `{font:mono}`) sont autorisées librement : elles ne
composent avec rien, ne dépendent d'aucun thème et ne peuvent pas
produire un résultat illisible. Les **littéraux** dans le texte sont
admis parce que la balise passe par le compilateur, donc trois garanties
s'appliquent d'elles-mêmes :

- **les mêmes types partout** — une couleur y est un ARGB valide, une
  pile finit sur un générique, sinon erreur fatale du build nommant la
  balise et l'article. La position antérieure — variantes seulement —
  visait le bon danger au mauvais endroit : le risque n'était pas le
  littéral, c'était l'invisibilité d'une intervention écrite en CSS
  libre que rien ne lit ;
- **un nom partagé est émis en `var()`** (`{color:call}` →
  `var(--color-call)`), que le `:root` de toute page définit par
  construction — la balise suit donc les changements de thème ;
- **`audit` les énumère** par article, en `[NOTE]` informatif, jamais
  bloquant (§9.4.4) : l'auteur qui change de thème sait où regarder.

**L'alignement est la seule balise de bloc, et c'est CSS qui l'impose.**
`text-align` est une propriété de conteneur de bloc : posée sur le
`<span>` en ligne que produisent toutes les autres balises, elle ne fait
rien, à aucune taille de fenêtre. Et un paragraphe ne s'ouvre pas en
plein milieu. La règle qui se généralise n'est donc pas « toute propriété
a une balise en ligne » mais **la portée de la balise épouse la portée de
la propriété** : propriété en ligne, balise en ligne ; propriété de bloc,
balise de bloc. L'ouvreur et le fermeur sont chacun seuls sur leur ligne
et enveloppent des paragraphes entiers dans un `<div class="align-…">` ;
une valeur inconnue est une erreur de build nommant la balise ; un
fermeur sans ouvreur reste du texte littéral, comme un ouvreur en ligne
non fermé.

La classe atteint aussi les descendants (`.align-center *`). Ce n'est pas
une commodité : `text-align` s'hérite, mais un composant qui déclare le
sien bat ce qu'il hérite, donc sans le sélecteur de descendance le choix
local d'un auteur ne pourrait jamais l'emporter sur le thème — ce qui est
exactement la raison d'être d'une balise d'instance. Corollaire à
connaître : tout ce qui est dans le bloc s'aligne, y compris les cellules
d'un tableau qu'il contient.

Mécanique de rendu, vérifiée : les balises s'imbriquent (résolution de
l'intérieur vers l'extérieur), le Markdown à l'intérieur se convertit
toujours ; un ouvreur sans son fermeur sur la même ligne reste du texte
littéral — visible dans le rendu, là où l'auteur regarde déjà ; à
l'intérieur d'un span de `` `code` ``, rien n'est jamais une balise. La
**variante reste le geste recommandé** pour ce qui se répète ; la balise
est l'outil de l'intervention ponctuelle d'un auteur qui sait ce qu'il
fait.

### 9.7 Effets et dégradés

**Fond dégradable.** Un fond qui sait se dégrader se paramètre en trois
axes — `bg.from`, `bg.to`, `bg.angle` (aujourd'hui : la couverture,
`cover.bg.*`) — et **un aplat est un dégradé dont les deux bornes sont
égales** : `bg.to` renvoie par défaut à `bg.from`, pas de branche, pas
de cas particulier, et les thèmes du catalogue restent des aplats sans
rien dire. Deux réserves : un dégradé est une `background-image`, donc
`print-color-adjust: exact` est nécessaire à l'impression ; et un
dégradé **sur du texte** exigerait `background-clip: text` — hors
périmètre, les dégradés sont réservés aux fonds.

**Ombres et halos.** Ombre et halo passent par `text-shadow`, en trois
axes par composant porteur : `shadow.fg`, `shadow.blur`, `shadow.dy`.
**Un halo est une ombre sans décalage** — même mécanisme, pas de
branche, comme l'aplat est un dégradé à bornes égales. Le défaut est
`transparent` : aucun effet tant qu'un thème n'en demande pas. Trois
composants portent les axes : `page`, `title1` et `highlight`.
`text-shadow` étant une propriété **héritée**, les axes posés sur `page`
teintent tout le texte du site d'un coup — l'effet « aérien » global est
trois lignes — et les composants qui portent leurs propres axes
divergent localement : le halo vert de `terminal` sur ses titres et son
chiffre-clé (§9.5.1), sans toucher au corps.

Le barré appartient à l'énumération de décoration (`line-through`), qui
sert aussi aux balises d'instance (§9.6.3).

**Alignement.** Une énumération `left | center | right | justify` portée
par les composants qui portent du texte — `title1`, `title2`, `summary`,
`fact`, `cover`, `table.head`, `table.cell`, `caption`, `article`,
`highlight`. Les quatre premières couches se comportent comme n'importe
quel autre axe ; la cinquième a sa syntaxe de bloc (§9.6.3). Ce que cela
a retiré du squelette, ce sont des décisions de mise en page par décret :
le chiffre-clé centré sans recours (B4), les cellules de tableau à
gauche, la légende de figure centrée.

**La coupure des mots en fin de ligne ne se fait jamais d'elle-même.**
C'est un axe à part, `page.hyphens` (`manual | auto`, défaut `manual`,
qui est la valeur initiale de CSS : un mot ne se coupe que là où
l'auteur a mis un tiret conditionnel). Elle a été livrée une fois liée à
`justify` — choisir un alignement allumait donc la coupure en silence,
une décision typographique arrivant comme l'effet de bord d'une autre.
Les deux sont indépendantes : réaligner un bloc ne change jamais si ses
mots se coupent. L'axe est hérité, donc une seule déclaration gouverne
toute la page ; et la coupure automatique a besoin de la langue, que les
gabarits déclarent déjà en `<html lang="…">`.

**Largeur de colonne.** `page.content-max` est la largeur du texte
courant dans une fiche : **proportionnelle à la zone d'affichage**, et
sans plafond — `84vw` par défaut. Une page construite est un deck (chaque
fiche fait `min-height: 100vh`), et un deck montré en plein écran doit
utiliser l'écran : mesuré à 3840 px sous l'ancien plafond de 1100 px, la
colonne faisait 29 % de la largeur avec du texte à 22 px.

L'échelle typographique est proportionnelle elle aussi (`Nvmin`, sans
plafond), et **c'est le couple qui tient** : quand la colonne et le corps
grandissent du même facteur, le nombre de caractères par ligne ne bouge
pas — mesuré invariant de 1080p à 4K. Lever un plafond sans l'autre
produirait une mauvaise page : une colonne plus large seule allonge les
lignes, un corps plus gros seul les raccourcit.

Le **plancher** de chaque taille reste : c'est lui qui gouverne un
téléphone, où les fiches sont déjà serrées en hauteur (§7 de
`ETUDE-VIEWPORT.md` compte celles qui débordent). Mesuré à 375×667 :
identique à l'octet près.

**Toutes** les tailles suivent cette forme `max(<plancher>, <N>vmin)` —
les trente-cinq, pas seulement les huit du corps de texte. Une taille
figée en pixels rétrécit *relativement* à tout ce qui l'entoure à mesure
que l'écran grandit : mesuré à 3840, le rapport `tag`/`summary` valait
0,206 pour 0,556 voulu, c'est-à-dire une étiquette presque trois fois
trop petite. Le coefficient de chaque taille vaut sa valeur en pixels
divisée par 8, ce qui redonne à 1920×1080 exactement le rapport que le
dessin avait, et le conserve au-delà. Un thème qui redéclare une taille
redéclare une **échelle** : écrite en pixels nus, elle serait la seule
part de la page à ne pas grandir, ce qui inverse l'intention du thème sur
l'écran où elle compte.

**Largeur des blocs.** `page.block-max` gouverne ce qui n'est pas du
texte courant — tableau, bloc de code, figure —, dimensionné par ce qu'il
contient et non par un compte de caractères. Le `1100px` y est un
**plancher**, pas un plafond, pour la même raison : mesuré à 3840, un
tableau dont le texte atteignait 41 px tenait dans une boîte restée à
1100 px, soit environ 26 caractères par ligne. `102vmin` vaut 1100 px à
1920×1080, donc rien ne bouge à cette taille ni en dessous ; au-delà, la
boîte garde la part de colonne qu'elle y avait — 68 %, mesuré à 1920
comme à 3840.

Le bloc `highlight` fait exception aux blocs et lit `page.content-max` :
c'est le seul bloc **centré**, et une boîte centrée plus étroite que la
colonne n'a pas seulement une autre largeur, elle a un autre centre.
Mesuré sous `page.block-max`, le chiffre-clé était décentré de 256 px à
1920 et de 1063 px à 3840 par rapport à tout ce qui l'entourait. Un bloc
aligné à gauche n'a pas ce problème : plus étroit, il partage quand même
le bord gauche de la colonne. Le bloc n'est pas non plus une colonne
flex : `align-items: center` rendait `highlight.align` inerte — mesuré,
`highlight.align: left` déplaçait le chiffre de zéro pixel — alors que
des blocs ordinaires héritent de `text-align`, ce qui rend la propriété
effective.

**Les halos suivent le glyphe.** Ce qui est dessiné *contre* le texte est
dimensionné par lui : la boîte colorée d'un passage marqué et l'arrondi de
ses coins, l'épaisseur du filet et sa distance à la ligne de base, et la
lueur (`*.shadow.blur`) qu'un thème peut poser autour d'un titre. En
pixels nus, une boîte de 4 px de marge latérale se lit comme un
surligneur sur un corps de 24 px et comme une coquille sur un corps de
47 px ; une lueur de 10 px entoure un titre de 51 px à 1080p et le même
titre à 132 px à 3840. Les planchers gardent les deux collisions mesurées
(descendantes, bord bas de la marque) telles qu'elles ont été mesurées.

**Navigation de série.** `.series-list` lit `page.content-max`, comme
tout le reste d'une fiche. Une largeur fixe la mettait à 42 % de la
colonne à 1920 et 21 % à 3840, collée au bord gauche d'une fiche dont le
titre occupait toute la largeur — et ce titre est la seule autre chose
présente sur une fiche `series-nav`, donc toute largeur inférieure à la
colonne y est aussi un second centre.

Elle a brièvement été une mesure en `ch`, et la raison même pour laquelle
ce choix avait été fait est ce qui l'a fait échouer : une longueur en `ch`
placée dans une propriété personnalisée se résout contre la police de
l'élément **consommateur**. Une seule valeur déclarée devenait donc une
largeur en pixels **différente par composant** — `50ch` fait environ
800 px sur un titre à 32 px et environ 450 px sur du texte à 18 px. Une
fiche dont le titre va jusqu'à un bord et dont le texte s'arrête bien
avant n'a plus de bord intérieur du tout, et son texte cesse de paraître
lié à la fiche qui l'entoure. C'est ce que voit un lecteur ; le nombre de
caractères par ligne est ce que voit un tableur.

Un plafond en unités absolues se résout **identiquement pour tous les
éléments** : le titre et le paragraphe en dessous partagent un même bord
droit. Le terme en `vw` garde l'ensemble lié à la largeur réellement
disponible. Les autres constats de l'étude de fenêtres tiennent ; ce
qu'elle avait mal jugé, c'est d'avoir compté « la bonne mesure à chaque
corps » comme un gain, alors que c'est précisément ce qui casse
l'alignement.

Les tailles fluides sont exprimées en `vmin`, non en `vw` : en portrait
`vmin` **est** `vw`, donc rien n'y bouge, et en paysage le corps suit la
dimension contraignante au lieu de grossir pendant que l'écran raccourcit.
Un point de rupture en hauteur (`@media (max-height: 520px)`) récupère le
rembourrage vertical là où l'écran est trop court ; il est déclaré **en
dernier** dans le squelette, parce qu'à spécificité égale c'est la règle
la plus tardive qui gagne.

### 9.8 Migration depuis `templates/style.css`

**Rupture nette, sans alias.** Un `var(--yellow)` ou un `var(--marker)`
ne se replie sur rien : la déclaration est invalide et la propriété
garde sa valeur héritée, sans que le navigateur ne dise mot. La
politique maison — rupture annoncée à voix haute, casse silencieuse
rendue audible — s'applique par trois canaux, tous vérifiés :

Pourquoi cette politique est défendable **ici** et ne le serait pas
ailleurs : le facteur discriminant n'est pas la taille du projet, c'est
**qui paie la migration**. Alias de compatibilité et codemods se
justifient quand des milliers de dépôts tiers consomment les jetons ;
alors le coût de la rupture est payé par des gens qui n'ont pas décidé.
Ce n'est pas le cas de ce projet — c'est celui qui change le vocabulaire
qui migre ses propres séries.

- **`build`** avertit (`[WARN]`) si `templates/style.css` existe
  encore : le fichier n'est plus lu, la feuille est composée depuis
  `settings.conf` ; les valeurs vont dans `settings.conf`, les règles
  dans `custom.css`, puis le fichier se supprime.
- **`template update`** répète l'avertissement et **crée** la surface
  neuve manquante (scaffold + `custom.css` vides) sans jamais migrer les
  valeurs : ce sont les décisions de l'auteur, les déplacer lui revient
  (§9.4.3).
- **`audit`** rend le geste mécanique : une table plate embarquée,
  `RETIRED_VARIABLES`, associe **chaque nom de variable ayant existé et
  n'existant plus** à son remplaçant, et `audit` nomme chaque occurrence
  trouvée — dans un `style.css` hérité comme dans `custom.css`
  (§9.4.4). Elle couvre les renommages de la v0.12.0 (`--yellow` →
  `--color-mark`…) comme ceux de la refonte (`--page` → `--color-page`,
  `--fact-strong-highlight` → `--fact-strong-bg`…). L'avertissement est
  d'autant plus utile qu'un ancien nom se scinde parfois en plusieurs
  remplaçants selon l'emploi — `--accent` devient `--color-call` ou
  l'axe du composant visé (`--footnote-call-fg`, `--verdict-partial-fg`,
  `--nav-btn-ring`…), `--rule` se dissout par composant
  (`--slide-rule-fg`, `--footer-rule-fg`…) — c'est précisément le cas où
  un alias serait faux et où un message est juste.

Une série d'avant la refonte reste constructible sans rien faire (la
feuille composée part des défauts intégrés) ; elle récupère la surface
neuve au premier `template update`, ou directement le thème voulu par
`series theme set` (qui écrit un scaffold frais quand `settings.conf` manque,
§9.4.2). L'hypothèse de travail est assumée : un seul utilisateur,
capable de tout régénérer — l'architecture est conçue pour être juste,
pas compatible.

---

## 10. Pipeline GitLab CI

Optionnel — `init` ne l'écrit que si `--gitlab-ci` est passé (§11.1) :
`init` seul ne présuppose jamais un déploiement GitLab, pour ne pas
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
série lui-même (`init` l'y copie, §11.1). Le pipeline n'a besoin que de
Python 3 (image `python:3.12-slim`), pas de `pip install`.

Rien n'empêche d'ajouter une étape `python3 lightwebpres verify .` avant le
`build` : son code de sortie non nul en cas de différence (§11.4) en fait
une porte de vérification utilisable dans ce même pipeline, pour détecter
un `public/` non reconstruit avant de merge — pas fait par défaut par
`init`, à ajouter à la main si voulu.

---

## 11. Commandes de l'exécutable

### 11.1 `init`

```bash
lightwebpres init [répertoire] [--lang fr] [--theme nom] [--gitlab-ci]
```

Crée la structure de travail dans `[répertoire]` :

1. Crée le répertoire s'il n'existe pas
2. Crée les sous-répertoires : `articles/`, `templates/`, `language/`,
   `public/`
3. Écrit la surface de personnalisation (§9.3, §9.4.1) :
   - `templates/settings.conf` — le scaffold complet : toutes les
     propriétés en commentaire à la valeur du thème choisi, avec la ligne
     `theme: <nom>` si `--theme <nom>` est fourni (sinon, scaffold aux
     défauts intégrés, sans ligne `theme:` active) ; `<nom>` inconnu de
     `THEMES` est une erreur fatale, qui liste les noms valides
   - `templates/custom.css` — le gabarit commenté, vide de règles
   - `templates/nav.js`
   (pas de `templates/style.css` : la feuille est composée au build, §9.3)
4. Extrait les packs de langue par défaut depuis l'exécutable :
   - `language/fr.json`
   - `language/en.json`
5. Crée un `series.json` de départ : `series_meta` pré-rempli de
   valeurs génériques (`title`/`subtitle`/`version`/`intro`, plus
   `author`/`license` vides — présents pour faire connaître les champs,
   rien n'est rendu tant qu'ils sont vides) et un tableau `articles`
   vide
6. Crée un `.gitlab-ci.yml` de base, **mais seulement si `--gitlab-ci` est
   passé** — `init` seul ne présuppose jamais un déploiement GitLab
   (§10) ; par défaut, aucun fichier de CI n'est créé. La commande de
   build de ce fichier porte la langue choisie (`build . --lang <lang>`,
   `fr` par défaut)
7. Copie l'exécutable `lightwebpres` dans le répertoire (pour autonomie)

**`--lang` à l'init.** La langue n'est **pas** une propriété du projet
stockée quelque part : les deux packs (fr, en) sont toujours installés, et
la langue est un choix **par build** (`--lang` sur `build`/`demo`, ou
`$LWP_LANG`, `fr` par défaut — §7.1/§12.1). À l'install, `--lang` ne fait
qu'une chose : fixer la langue inscrite dans la commande de build du
`.gitlab-ci.yml` généré (donc utile surtout avec `--gitlab-ci`).

Si le répertoire existe déjà et contient déjà des fichiers, `init` refuse
et s'arrête (erreur, code de sortie non nul), sauf avec `--force` qui laisse
`init` procéder quand même. Pas d'invite interactive : l'outil est pensé
pour un usage scripté (LLM, CI, §13.5), une invite bloquerait ces usages en
attendant une entrée qui ne viendra jamais.

### 11.2 `demo`

```bash
lightwebpres demo [répertoire] [--lang fr] [--output public/]
```

Vérifie que `init` a été fait (présence de `templates/settings.conf`,
ou de `templates/nav.js` pour qu'une série installée avant la refonte §9
reste reconnue). Si non, erreur fatale invitant à lancer `init`
d'abord.

Refuse de s'exécuter si l'un des 7 fichiers de démo (6 `.md` +
`img/demo-figure.svg`) existe déjà dans `articles/`, **ou si
`series.json` liste déjà au moins un article** (erreur fatale dans les
deux cas) — jamais d'écrasement silencieux d'un travail en cours :
`demo` réécrit `series.json` entièrement, ce qui n'est inoffensif que
sur le boilerplate d'un `init` frais (liste d'articles vide).

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

1. Lit `series.json` dans `[répertoire]`. Les articles `status: ignored`
   (§20.6) sortent de la liste d'abord et sans condition. Les articles
   `status: draft` sont ensuite **entièrement exclus** — pas de page, pas
   de carte d'index, pas d'entrée dans les navigations des autres
   articles — sauf avec `--include-drafts` (build **et** check), qui les
   construit tous, chaque page brouillon portant alors un bandeau
   « Brouillon » (clé `draft_banner` du fichier de langue) affiché au
   centre de l'en-tête de page, entre l'éventuel build stamp (§11.3.2) et
   le numéro de fiche — un aperçu ne doit jamais être confondu avec une
   publication (style inline, comme le stamp, pour ne dépendre d'aucune
   règle de la feuille composée ni d'un `custom.css` de série).
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
   e. Assemble le HTML avec la structure de page fixe (§9), la feuille
      composée (§9.3 — recomposée pour cette page si le bloc meta porte
      des propriétés `style.*`, §9.6.1) et le JS
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
correspondant mais dont le fichier n'existe pas. Les deux filtres de
§20.6 s'appliquant avant celui-ci, un article `status: draft` n'est
désignable par `--only` qu'avec `--include-drafts`, et un article
`status: ignored` ne l'est jamais.

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
mécanisme pour `status` : l'empreinte est calculée sur la liste *après*
les filtres de §20.6, donc changer le statut d'un article change
l'ensemble des clés et force un build complet.

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
que `verify` (§11.4) présuppose justement pour son diff exact.

**`verify` ignore le marqueur, dans les deux sens, pour les deux
variantes** : le HTML généré en mémoire par `verify` pour comparaison
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

**Style entièrement en ligne, jamais dans la feuille de style** — bug
réel trouvé en testant à la main juste après la première version : à
l'époque du `templates/style.css` éditable, une série au fichier
personnalisé (ou simplement scaffoldé avant l'existence de cette option)
n'avait aucun moyen de récupérer une nouvelle règle intégrée sans passer
par `template update`. La première version du marqueur dépendait d'une
règle `.build-stamp` dans la feuille partagée — absente de ce genre de
série, la `<div>` se retrouvait sans style du tout : un bloc pleine
largeur, texte de couleur par défaut, poussant la première fiche vers le
bas au lieu de se superposer discrètement dans le coin (repéré
visuellement, capture d'écran à l'appui, avant d'être corrigé). Le style
(couleur, taille, `pointer-events: none`, positionnement) est
entièrement porté par l'attribut `style=""` de la `<div>` elle-même,
jamais dépendant d'une règle externe — y compris la couleur grise, en
valeur hexadécimale fixe plutôt qu'en `var()`. La règle survit à la
feuille composée (§9.3), qui est pourtant toujours fraîche : un
`custom.css` de série peut légitimement écraser ou omettre n'importe
quelle règle, et un outillage interne ne doit jamais dépendre de la
surface que l'auteur possède.

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

### 11.3.3 Un article qui réclame `index.html`

`build` écrit toujours un index de série, à `index.html`. Un article dont
le `page_dest` vaut ce même nom entre donc en collision avec lui, et
jusqu'ici la page de l'article était écrite puis **écrasée par l'index,
en silence, avec un code de sortie 0** : une série déclarant trois
articles en livrait deux, et `verify` n'y voyait rien. C'est la classe de
défaut que §22.8 interdit déjà pour un fichier d'article manquant — une
page corrompue livrée en vert — appliquée à une collision de noms.

La règle dépend du **nombre d'articles**, et ce n'est pas un cas
particulier concédé : c'est la reconnaissance de ce que l'index vaut dans
chaque cas.

- **Plus d'un article** : l'index porte une information réelle — la liste
  des articles — et l'écraser est une perte. **Erreur fatale**, nommée,
  code de sortie non nul.
- **Exactement un article** : l'index ne listerait qu'une entrée. Il
  n'apporte rien. L'article réclame la place, il l'obtient : **l'index de
  série n'est pas produit**, et `build` le dit dans sa sortie plutôt que
  de le faire en douce.

Ce que cette seconde branche reconnaît, c'est qu'une série d'un seul
article est une **brique** autant qu'un site. Elle peut atterrir dans un
répertoire dont l'index est tenu autrement — à la main, par un autre
générateur, ou parce que d'autres articles y vivent déjà ; l'auteur laisse
alors le nom par défaut et ne réclame rien. Ou elle est seule chez elle,
et `index.html` est le nom qui a du sens. **Le nom choisi est la
déclaration d'intention**, et l'outil n'a pas à la deviner autrement.

### 11.4 `verify`

```bash
lightwebpres verify [répertoire] [--lang fr] [--no-typography]
```

Vérifie sans modifier :

1. Lance le build en mémoire (sans écrire les fichiers) ; `--no-typography`
   a le même effet que sur `build` (§11.3), sur ce build en mémoire —
   utile pour vérifier un `public/` déjà généré sans typographie, pas pour
   ignorer une vraie différence de typographie sur un `public/` généré
   normalement (`verify` comparerait alors deux HTML volontairement
   différents et signalerait un `[DRIFT]` correct, pas un faux positif)
2. Compare la sortie générée avec l'existant : **chaque page d'article**
   contre `public/`, plus **`index.html`** (contre `public/`) et
   **`README.md`** (contre la racine du répertoire de série) — un
   changement de `series_meta` (titre, intro, ordre des articles) ne
   modifie que ces deux derniers, et `verify` restait vert dessus avant la
   v0.9.0 : c'était un trou dans la porte de CI. Quand un article unique
   porte le nom de l'index (§11.3.3), `build` ne produit aucun index de
   série et `verify` n'en compare pas non plus : la page d'article qui
   occupe ce nom est déjà comparée à sa propre place, et confronter en
   plus un index fraîchement rendu à cette page signalerait un `[DRIFT]`
   permanent sur une série pourtant correctement construite, qu'aucune
   reconstruction ne pourrait résoudre. Un `series.json` que `build`
   refuse (§11.3.3, plus d'un article) est refusé ici avec la même
   erreur, plutôt que rapporté comme une dérive ordinaire
3. Pour chaque fichier différent, affiche `[DRIFT] fichier` suivi d'un diff ;
   pour chaque fichier absent, affiche `[NEW] fichier` ; pour
   chaque fichier identique, affiche `[OK] fichier`
4. Affiche un résumé chiffré : « N file(s) OK, M file(s) different. »
   (N + M = nombre d'articles + 2 — + 1 quand aucun index de série n'est
   produit, §11.3.3)
5. Code de sortie non nul (1) si au moins un fichier diffère ou est absent —
   c'est ce qui permet d'utiliser `verify` comme porte de vérification dans un
   script ou une CI (§10) ; code de sortie 0 et « All files are up to
   date. » si tout est identique (M = 0)

### 11.5 `audit`

```bash
lightwebpres audit [répertoire] [--lang fr]
```

Vérifie des **conventions éditoriales non bloquantes**, sans jamais faire
échouer la commande ni modifier de fichier (contrairement à `verify`, qui
compare le HTML généré à l'existant, §11.4) :

1. Pour chaque article, lit et parse le `.md` source
2. Note (`[NOTE]`, informatif, non compté comme avertissement) les
   **balises d'instance** que l'article contient, avec leur décompte par
   type — des interventions d'auteur qui survivent aux changements de
   thème (§9.6.3), que l'auteur doit savoir localiser
3. Avertit si l'article ne contient **aucune** fiche `cover`
4. Avertit si la **première** fiche de l'article n'est pas une `cover`
5. Avertit si l'article n'a de description **nulle part** (`page_desc`
   vide à tous les niveaux de la cascade §20.3.1 — la balise
   `<meta name="description">` serait omise)
6. Volet présentation (§9.4.4) : avertit si un `templates/style.css`
   hérité existe encore (plus lu — avec, pour lui comme pour
   `custom.css`, chaque variable **retirée** encore référencée, nommée
   avec son remplaçant, table `RETIRED_VARIABLES` de §9.8 — aucun alias
   n'a été conservé, une telle déclaration cesse de s'appliquer sans que
   rien ne le signale, et c'est ici que la rupture devient audible) ; si
   `settings.conf` contient une erreur de syntaxe ou de propriété (mêmes
   messages qu'au build, non bloquants ici) ; et si son `scaffold-for:`
   ne correspond plus au `theme:` déclaré (décommenter une ligne
   épinglerait une valeur du thème quitté)
7. Affiche un résumé (en anglais, non localisé) : « No warnings: all
   editorial conventions are respected. » ou « N warning(s). Reminder:
   audit never blocks... »

Le nombre et la position des fiches `cover` restent libres (§4.4, §22.13) :
`audit` ne fait qu'informer, la décision reste à l'auteur. Rien n'est
exclu de l'audit (§20.6) — ni brouillons ni articles `ignored`, ces
derniers étant même signalés nommément, parce que c'est le seul endroit
de l'outil qui parlera jamais d'eux.

### 11.6 `template update`

```bash
lightwebpres template update [répertoire] [--scaffold]
```

Met à jour ce qui, dans `templates/`, appartient à l'outil — voir §9.4.3
pour le raisonnement. Sous le modèle de feuille composée, la feuille est
toujours fraîche par construction (elle vient de l'exécutable courant à
chaque build) ; le seul fichier de l'outil restant sur disque est
`nav.js`.

1. Erreur fatale si `templates/` n'existe pas (`init` pas encore fait)
2. `templates/nav.js` : remplacé s'il diffère de la version intégrée
   (l'ancien est sauvegardé en `templates/nav.js.bak`), rapporté
   « already up to date » sinon
3. Crée les fichiers de la surface auteur s'ils **manquent** (série
   installée avant la refonte §9) : `templates/settings.conf` (scaffold
   aux défauts, aucun thème déclaré) et `templates/custom.css` (vide) —
   écrire un fichier qui n'existe pas ne trahit aucune promesse de
   propriété ; un fichier présent n'est **jamais** touché
4. Avertit (`[WARN]`) si un `templates/style.css` hérité existe encore :
   il n'est plus lu et n'est **jamais migré** — ses valeurs sont les
   décisions de l'auteur ; `audit` nomme chaque renommage de variable
   pour rendre le déplacement mécanique (§9.8)

Plus de marqueur, plus de `[SKIP]` : l'ancien mécanisme de coupure
n'existait que parce que l'outil écrivait dans un fichier que l'auteur
éditait, ce que le partage de propriété de §9.3 a supprimé.

Ne relance pas `build` automatiquement : les fichiers HTML déjà générés
dans `public/` restent inchangés tant que `build` n'est pas relancé à la
main.

### 11.7 `theme gallery`

```bash
lightwebpres theme gallery [chemin]
```

Génère une page HTML autonome (aucune dépendance) documentant chaque
entrée de `THEMES` (§9.5). **Un thème par ligne, quatre panneaux en
colonnes** — la couverture, une fiche portant une note, la section de
notes de page, et l'article de fond — plus ses six couleurs de rôle
(chaque pastille donne le rôle, puis le nom de propriété qu'un auteur
peut réellement taper — `color.mark` — puis la valeur), et sa remarque
éditoriale. Ne modifie aucun `series.json` ni `templates/` : cette
commande documente, elle n'installe rien.

Les quatre panneaux sont les quatre surfaces qu'un lecteur rencontre, et
ce sont les seules où les propriétés du thème se voient toutes. L'article
de fond n'était montré nulle part avant ; les deux emplacements de note
(§6.5.1) ne le seraient pas non plus avec un seul panneau, or ils ne
posent pas les corps sur le même fond.

La note du panneau « fiche » n'est ni étiquetée ni mise à part : une
fiche porte une affirmation, l'affirmation porte une référence, la
référence est sous son filet au pied de la fiche. L'appel est
délibérément placé **hors** du passage en gras — à l'intérieur il
tomberait sur le fond du surligneur, et la galerie afficherait un défaut
de contraste comme s'il s'agissait du dessin (BACKLOG B17).

L'aperçu reçoit la couche complète du thème, mobilier compris (§9.5.1),
sans quoi une palette à fond sombre s'afficherait avec les voiles d'une
page claire — c'est-à-dire pas telle qu'elle rendra réellement.

Sous chaque aperçu, une ligne « Fact-box bold » **énonce** le traitement
du gras que le thème a choisi — « Bold, highlighted `color.mark` »,
« Bold, no highlight », « Italic, highlighted `color.affirm` »… (la ligne
nomme la propriété `settings.conf`, celle qu'un auteur peut taper, jamais
une variable CSS que la feuille émise ne déclare plus). La galerie
appliquait ces propriétés à sa maquette sans jamais les nommer : neuf
combinaisons distinctes existent parmi les thèmes intégrés et aucune
n'était lisible autrement qu'en scrutant deux lignes d'aperçu. Le
soulignement n'est mentionné que lorsqu'il est présent — en annoncer
l'absence sur chaque carte noierait les axes qui, eux, diffèrent.

**L'aperçu est une vraie fiche.** Pas une imitation : `theme gallery`
fait passer une maquette écrite au format d'article réel (§4) par
`parse_markdown_extended()` puis `render_slide()` — les fonctions
qu'appelle `build` — et lui applique la feuille composée pour ce thème
(`compose_stylesheet()` sur la couche de `theme_property_layer()`,
§9.3/§9.5.1), exactement ce qu'un build produit pour une série sur ce
thème. Aucun code de rendu n'est dupliqué, donc aucune divergence n'est
possible.

Chaque aperçu est un `<iframe srcdoc>`. Deux raisons, l'une nécessaire :

- La feuille réelle emploie des mesures relatives au **viewport**
  (`clamp(28px, 4.5vw, 52px)`, `84vw`). Dans la page de la galerie elles
  se calculeraient sur la fenêtre du lecteur ; dans un iframe elles se
  calculent sur l'aperçu, comme dans une vraie page.
- La feuille réelle définit `body`, `h1`, `code`… L'isolement du document
  évite d'avoir à réécrire ses ~203 règles pour les confiner.

**Chaque panneau est rendu à sa taille réelle**, 340 × 560 px, sans
réduction géométrique. La galerie rendait auparavant à 1100 px puis
réduisait de 0,34 : acceptable pour juger une palette, inutile pour juger
une note, dont les 14 px arrivaient sous 5 pixels d'écran. Ici chaque
glyphe est à sa taille : le poids du filet, le bord du plateau et la
mesure de la note sont lisibles.

Le prix, qu'il vaut mieux énoncer que découvrir : 340 px est en dessous
de tous les points de rupture des `clamp()`, donc chaque thème s'affiche
à son échelle typographique de **fenêtre étroite** — un titre de
couverture au plancher de 28 px plutôt qu'aux ~50 px qu'il atteint sur un
bureau. Ce que le panneau sert à montrer y survit intact : couleur, fond,
filet, et la proportion entre les niveaux. La page le dit dans son
chapeau.

Les colonnes sont une piste **fixe** (`repeat(4, 340px)`), jamais `1fr` :
la largeur du panneau *est* la largeur de rendu, donc une piste élastique
donnerait à chaque ligne une échelle typographique différente et la
comparaison ne voudrait plus rien dire. Le débordement défile dans la
ligne, pas dans la page.

`min-height: 100vh` est laissé tel quel dans le document d'aperçu :
`100vh` s'y résout à la hauteur du panneau, donc la section remplit sa
fenêtre et s'y centre exactement comme sur une vraie page.

`srcdoc` conserve l'autonomie de la page — aucune requête externe. La
galerie pèse de ce fait environ 5,5 Mo, la feuille composée (~37 Ko par
document d'aperçu) étant répétée pour les 132 panneaux ; les iframes
étant isolées, cela ne peut pas être dédupliqué sans JavaScript. Les
iframes portent `loading="lazy"`, donc le coût de rendu suit ce que le
lecteur regarde. **Conséquence à connaître avant qu'elle ne morde :** une
capture pleine page de la galerie donne des panneaux vides sous la ligne
de flottaison, puisque les iframes paresseuses n'entrent jamais dans le
viewport — il faut faire défiler avant de capturer.

**Ce que cette architecture a supprimé.** L'aperçu était auparavant une
maquette faite main avec ses propres règles `.preview-*`, et une copie
entretenue à la main ne l'est pas : elle a dérivé deux fois sans que rien
ne le signale. Elle a peint tous les thèmes à fond sombre avec les voiles
d'une page claire — surlignage mesuré à 1,00:1, invisible — puis elle a
composé le chiffre-clé en ligne alignée à gauche, avec une flèche entre
le chiffre et sa légende que `render_slide()` n'a jamais émise. Les deux
étaient invisibles pour une suite qui vérifiait la copie contre
elle-même. Les tests portent désormais sur l'**identité** : le document
d'aperçu contient exactement la sortie de `render_slide()` et exactement
la feuille composée pour ce thème.

En tête de page, une barre de **facettes** (§9.5.2) filtre les aperçus
par polarité, intensité et teinte. Elle est produite en HTML statique
mais masquée par défaut, et révélée par le script inline de la page :
sans JavaScript, la galerie reste une liste complète et lisible plutôt
qu'une barre de boutons inertes. Le script affiche en permanence le
nombre d'aperçus visibles et **désactive** toute facette qui ne mènerait
à aucun résultat compte tenu des autres déjà actives — on ne peut donc
pas se retrouver devant une page vide sans comprendre pourquoi.

`chemin`, s'il est omis, vaut `theme gallery.html` dans le répertoire
courant — c'est ainsi que le fichier à la racine du dépôt lightwebpres
lui-même est produit, et il n'a plus vocation à être modifié à la main
(§9.5) : toute correction sur un thème (couleur, remarque) se fait dans
`THEMES`, puis `theme gallery` régénère le fichier.

Le texte d'exemple de chaque aperçu (« Chapter 1 », « Temperature
changes everything », etc.) est fixe, non localisé par `--lang` — la
galerie est une page anglaise depuis la v0.12.1, comme ses libellés
d'interface ; c'est un choix éditorial pour cette page de référence, pas
une limite du moteur de fiches lui-même. Le point de fond demeure : une
chaîne affichée et une clé de facette sont deux choses distinctes
(§9.5.2).

### 11.8 `--help`

Affiche l'aide avec la liste des commandes et options.

La section THEMES de cette aide **n'énumère plus les slugs**. À neuf
thèmes, la liste était un rappel utile ; passé la trentaine, c'est un mur
de noms qui ne dit rien de ce que chacun donne à l'écran — exactement le
problème que les facettes existent pour résoudre, simplement déplacé de
la galerie vers le terminal. L'aide renvoie donc aux deux commandes qui
savent répondre à « lequel je veux » : `theme list` et `theme gallery`, et
sur celle qui répond à « celui-là, il vaut quoi » : `theme show`.

### 11.9 `theme list`

```bash
lightwebpres theme list [--polarity light|dark] [--intensity sober|vivid|mono] [--hue <teinte>]
```

Liste les thèmes intégrés depuis le terminal, avec pour chacun son slug,
ses trois facettes (§9.5.2), son étiquette et sa remarque éditoriale.
Sans option, les liste tous ; chaque option restreint la liste, et les
options se combinent.

Cette commande existe parce que **lightwebpres doit pouvoir être utilisé
seul**. Les facettes n'ont d'abord vécu que dans le HTML produit par
`theme gallery`, ce qui imposait un aller-retour par un navigateur pour
choisir un thème — inacceptable pour un outil en ligne de commande, et
d'autant plus que l'interface graphique est un projet séparé qui ne peut
rien garantir ici.

Le slug est mis en avant dans la sortie parce que c'est ce que
`init --theme` et `series theme set` attendent : ce qu'on lit est
directement ce qu'on retape.

Deux cas se distinguent volontairement :

- **Valeur de facette inconnue** (`--hue rouge`) : erreur fatale qui
  liste les valeurs valides. Répondre « aucun thème ne correspond »
  enverrait le lecteur chercher un thème qui existe pourtant, à une
  faute de frappe près.
- **Combinaison valide mais vide** (`--polarity dark --hue orange`) :
  succès, avec un message nommant la combinaison restée sans résultat.
  Ce n'est pas une erreur, c'est une réponse.

### 11.9.1 `theme show`

```bash
lightwebpres theme show <slug> [--format text|json]
lightwebpres theme show [répertoire] [--format text|json]
```

Décrit **un** thème sans rien installer : sa palette, ses facettes, et le
niveau de contraste qu'il atteint réellement, mesuré.

#### Pourquoi la mesure et non une étiquette

Le niveau d'accessibilité d'un thème est **calculé** à partir du registre
de propriétés, jamais déclaré à la main dans la définition du thème. Une
étiquette écrite à la main ment dès le premier ajustement de palette, et
elle mentirait en silence : rien ne la relie à la couleur qu'elle prétend
qualifier. Le calcul emprunte le même chemin que le reste du moteur — les
propriétés résolues, les fonds composités — donc il est juste par
construction ou faux pour tout le monde en même temps.

Corollaire assumé : **tous les thèmes n'ont pas à être conformes.** Un
thème est un parti pris ; `terminal` avec son halo de phosphore et
`synthwave` avec ses saturations sont des choix, et les rendre AAA les
détruirait. Ce qui est exigé n'est pas que les 33 soient conformes, c'est
qu'on **sache lequel l'est** au moment de choisir, et qu'il y en ait.

#### Ce que la commande ne fait pas

L'information s'arrête à l'auteur. **Rien de ce niveau n'entre dans la
page construite** : ni balise, ni classe, ni mention. Le lecteur d'une
présentation n'a pas à être informé du niveau de contraste du thème qu'on
a choisi pour lui ; c'est une donnée d'outillage, pas de publication. Le
format ne change pas, `build` ne change pas.

#### Deux cibles

- **Un slug** (`theme show nord`) : le thème intégré, tel qu'il est
  livré. Aucun répertoire de série n'est nécessaire — c'est le cas
  « avant d'installer », celui qui sert à choisir.
- **Un répertoire de série** (`theme show .`) : le thème **effectif**,
  c'est-à-dire après application des valeurs que la série épingle dans
  `templates/settings.conf`. Les deux réponses peuvent différer, et c'est
  précisément le renseignement utile : un auteur qui a épinglé trois
  couleurs a pu faire tomber son thème sous le seuil sans le savoir.

#### Un niveau par catégorie, pas une lettre

Une lettre unique mentirait : un thème peut être irréprochable sur le
texte et échouer sur ses bordures. La sortie donne donc un niveau par
catégorie WCAG 2.x, chacune avec son seuil :

| Catégorie | AA | AAA |
|---|---|---|
| Texte courant | 4,5:1 | 7:1 |
| Grand texte (≥ 24 px, ou ≥ 18,7 px en gras) | 3:1 | 4,5:1 |
| Non textuel porteur d'information (SC 1.4.11) | 3:1 | — |

Le non-textuel n'a pas de niveau AAA dans la norme ; la sortie dit
`pass`/`fail`, pas un niveau, plutôt que d'inventer une graduation.

Chaque catégorie qui échoue est accompagnée des **paires fautives** avec
leur ratio mesuré et le seuil manqué — un niveau sans ses contre-exemples
n'est pas actionnable.

#### Ce qui est mesuré, et ce qui ne l'est pas

Une balayage de toutes les couleurs contre toutes les autres produirait
des échecs sur des paires que la page ne superpose jamais : illisible et
inactionnable. La mesure porte donc sur des **sites**, et un site nomme
trois choses : la propriété d'avant-plan, la **pile** de propriétés de
fond sous elle, et l'endroit de la page où cela arrive.

La répartition entre ce qui est déclaré et ce qui est dérivé n'est pas
un compromis, c'est la ligne de partage du §9.1 :

- **L'imbrication est déclarée.** Qu'un `strong` d'encadré se pose sur
  `fact.strong.bg` par-dessus `fact.bg` par-dessus la page est un fait
  sur les gabarits et le squelette ; aucune lecture du registre ne le
  retrouve. Idem pour la taille héritée quand elle vient du squelette
  (`.full-article h1` à 28 px, `.share-cell-head` à 11 px).
- **Tout le reste est dérivé du registre.** Les couleurs sont les
  propriétés résolues ; la **catégorie WCAG** d'un site est calculée à
  partir de ses propres axes `size` et `weight` résolus, donc un thème
  qui agrandit son résumé voit son résumé jugé en grand texte sans que
  rien n'ait à être mis à jour ; la palette et les piles de polices de la
  sortie sont dérivées de `THEME_SHARED_PROPS`, donc une septième valeur
  partagée apparaîtrait le jour où elle existerait.
- **L'oubli est impossible.** Toute propriété de type couleur du registre
  est soit dans un site, soit dans `CONTRAST_UNMEASURED` avec sa raison
  écrite — un test parcourt le registre contre les deux. Ajouter une
  dispense est une décision ; en oublier une ne se peut pas. C'est le
  même dispositif que celui qui a rattrapé deux fois l'omission de voiles
  de mobilier (§9.5.1), et pour la même raison : une table qui *paraît*
  complète à la lecture.

**Composition à 8 bits.** Un fond est composité `source-over` puis
quantifié en canaux 8 bits, parce que l'écran n'a nulle part où garder la
fraction. Ce n'est pas un détail : porté en flottant, un anneau de focus
du catalogue mesure 3,0009:1 et passe ; à la précision que le lecteur
reçoit réellement, il mesure 2,9970:1 et ne passe pas. La base de toute
pile est la toile blanche du navigateur, sous `page.bg` — un fond de page
avec un alpha laisse voir la toile, pas le néant.

**Comparaison non arrondie.** Le seuil est franchi sur le ratio brut :
2,9970 s'arrondit à 3,00 sans jamais atteindre 3. Les ratios sont
imprimés à quatre décimales, parce que « 3,00 n'est pas 3,00 » n'est pas
un message d'échec sur lequel on puisse agir.

**Ce que le non-textuel retient.** SC 1.4.11 vise l'information
**nécessaire** pour identifier un composant ou un état, et exempte
explicitement le décoratif. Sont donc mesurés : les anneaux de focus
(seule chose qui dise où est le clavier, contre la page **et** contre le
remplissage du contrôle), la pastille de la fiche courante (contre la
page et contre les autres pastilles — les distinguer *est*
l'information), le soulignement d'un lien de corps de texte (seul
porteur, puisque la couleur est héritée, §9.5.3), celui du gras
d'encadré quand un thème l'emploie, et le filet de la colonne `col-snap`.
Sont dispensés, chacun avec sa raison écrite dans le code : les filets
séparateurs (un trait dont le retrait ne coûte rien au lecteur), le bord
d'un contrôle qui porte déjà un libellé ou un glyphe — lesquels sont
mesurés, eux, sur le remplissage du contrôle —, les états au survol (le
clavier a l'anneau, qui est mesuré), et le voile de modale, dont le
métier est justement de ne pas se voir. Exiger le bord des contrôles en
plus mettrait les 33 thèmes à `fail` pour un motif qu'aucun lecteur
n'éprouve : ces bords sont tous un voile à 16 %, par construction.

**Ce que la mesure ne voit pas.** `templates/custom.css` n'est pas
mesuré : c'est du CSS libre, hors de la surface typée, et rien n'y est
une propriété résolue. La sortie le **dit** quand le fichier porte des
règles — une mesure qui ignorerait la moitié de la feuille en silence
serait l'étiquette écrite à la main de nouveau.

#### Facettes d'une cible répertoire

Sur un slug, les facettes sont celles de `theme_facets()` telles quelles
(§9.5.2) : `theme list`, la galerie et cette commande ne peuvent pas diverger
sur la même entrée. Sur un répertoire, la question porte sur le thème
*effectif* : la polarité et la teinte sont donc recalculées sur la page
qu'un build peindrait réellement — épingler un `color.page` sombre sur un
thème clair change les deux. L'intensité, elle, est déclarée et ne se
dérive de rien (§9.5.2) : elle reste le mot du thème, et vaut `null`
quand aucun thème n'est nommé.

#### Format machine : JSON

`--format json` émet du JSON, et non du YAML. La raison est la contrainte
qui gouverne tout le projet : `lightwebpres` n'utilise que la
bibliothèque standard, où `json` est présent et `yaml` non. Adopter YAML
coûterait la dépendance zéro. Côté `lightwebpres-gui`, JSON se lit sans
rien écrire du tout.

La sortie texte reste la sortie par défaut et vise la lecture humaine,
sans chercher à être aussi un YAML valide : servir deux maîtres
produirait un texte moins lisible que l'un et moins fiable que l'autre.

**Les clés, une par une.** Racine :

| Clé | Type | Sens |
|---|---|---|
| `schema` | chaîne | `lightwebpres.theme show/1`. Ce que le GUI teste pour distinguer un exécutable ancien d'un neuf, au lieu de le deviner aux clés qu'il trouve. Le nombre change quand une clé change de sens ou disparaît, jamais parce qu'une clé s'ajoute |
| `lightwebpres_version` | chaîne | le `VERSION` de l'exécutable qui a répondu |
| `target` | objet | ce sur quoi la question portait (ci-dessous) |
| `label` | chaîne ou `null` | l'étiquette affichable du thème ; `null` si aucun thème n'est nommé |
| `note` | chaîne ou `null` | la remarque éditoriale, **en texte nu** (§9.5.4) |
| `source` | chaîne ou `null` | la provenance de la palette (`lightwebpres`, `nord`, …) |
| `facets` | objet | `polarity`, `intensity`, `hue` (§9.5.2) ; `intensity` vaut `null` sur un répertoire sans thème |
| `palette` | objet | les six valeurs partagées **résolues**, clés sans le préfixe `color.` : `page`, `ink`, `ink-quiet`, `mark`, `call`, `affirm`. Valeurs en `#RRGGBBAA` |
| `fonts` | objet | les quatre piles résolues : `text`, `display`, `ui`, `mono` |
| `accessibility` | objet | les trois catégories (ci-dessous) |

`target` :

| Clé | Type | Sens |
|---|---|---|
| `kind` | `"theme"` ou `"series"` | laquelle des deux cibles a répondu |
| `theme` | chaîne ou `null` | le slug ; `null` pour une série dont `settings.conf` ne nomme aucun thème (elle tourne alors sur les défauts du registre) |
| `directory` | chaîne ou `null` | le chemin absolu de la série ; `null` sur un slug |
| `pinned` | liste de chaînes | les clés de propriété épinglées (décommentées) dans `templates/settings.conf`, triées. Vide sur un slug. C'est la réponse à « qu'est-ce que cette série a changé » |
| `custom_css` | booléen | `templates/custom.css` porte des règles — donc quelque chose de non mesuré s'applique par-dessus |

`accessibility` a trois clés — `body_text`, `large_text`, `non_text` —
de même forme :

| Clé | Type | Sens |
|---|---|---|
| `level` | chaîne | `AAA`, `AA` ou `fail` pour les deux catégories de texte ; `pass` ou `fail` pour `non_text`, qui n'a pas de niveau AAA dans la norme |
| `threshold_aa` | nombre | le seuil AA de la catégorie |
| `threshold_aaa` | nombre ou `null` | le seuil AAA, `null` pour `non_text` |
| `pairs_measured` | entier | le nombre de paires distinctes mesurées dans cette catégorie |
| `worst` | objet paire | la paire qui **décide** le niveau — donc, à AA, celle qu'il faut déplacer pour atteindre AAA |
| `failures` | liste d'objets paire | les paires sous le seuil AA, la pire d'abord. Vide quand la catégorie franchit AA |

Une **paire** :

| Clé | Type | Sens |
|---|---|---|
| `site` | chaîne | où cela se passe dans la page, en clair (`cover tag`, `verdict "yes"`) |
| `foreground` | chaîne | la clé de propriété peinte |
| `foreground_color` | chaîne | sa valeur résolue, `#RRGGBBAA` |
| `ground` | liste de chaînes | la pile de propriétés de fond, de l'intérieur vers l'extérieur, `page.bg` implicite en base ; `[]` = à même la page |
| `ground_color` | chaîne | le fond **composité**, opaque, `#RRGGBB` |
| `ratio` | nombre | le ratio mesuré, à quatre décimales |
| `required` | nombre | le seuil AA de la catégorie, celui que `failures` a manqué |

Deux sites qui compositent vers les deux mêmes couleurs — les deux
arrêts d'un dégradé plat, les deux colonnes teintées d'un tableau au même
alpha — comptent pour **une** paire : le niveau serait le même, mais le
lecteur recevrait quatre fois le même contre-exemple, ce qui est
exactement la façon dont une liste actionnable cesse de l'être.

#### État mesuré du catalogue

Le corollaire du §9.5.2 se lit maintenant en chiffres, et il est net :
la catégorie est décidée par sa **pire** paire, or le petit appareil
textuel (`ink-quiet` et les couleurs de verdict à 12-14 px sur un voile
de carte) est le point bas de tous les thèmes. Aucune entrée du
catalogue n'atteint donc AAA en texte courant ; **douze** franchissent AA
et **vingt et une** échouent, sur les couleurs de verdict, les libellés
de navigation de série, les étiquettes d'encadré et les légendes. En non
textuel, **seize** passent et **dix-sept** échouent, presque toujours sur
la pastille de fiche courante peinte en `mark` — la faiblesse que le
§9.5.1 nomme déjà dans ses propres termes (« un `mark` fait pour servir
de fond est souvent trop pâle pour servir de trait »), et qui frappe les
thèmes clairs. **Dix** entrées tiennent les deux à la fois :
`blueprint-night`, `ember`, `evergreen`, `gold-leaf`, `graphite`,
`pop-fuchsia`, `pop-red`, `synthwave`, `terminal`, `tokyo-night` — toutes
sombres, ce qui n'est pas une coïncidence mais la même cause vue de
l'autre côté. Le grand texte est AAA partout, ce qui est attendu : c'est
`ink` sur `page`, le seul couple sur lequel tout thème est admis
(§9.5.3).

Ces nombres ne sont pas figés ici — ils changent avec le catalogue, et
c'est la commande qui les dit. Ce qui est figé, c'est qu'ils soient
**mesurés**.

#### Consommateur connu

`lightwebpres-gui` s'en sert pour afficher le niveau à côté de chaque
thème dans son sélecteur (sa spec §1.3). C'est un contrat entre les deux
dépôts au sens de §1.2 : le nom des clés JSON est une surface publique,
et le renommer casse le GUI sans que rien ne rougisse ici.

### 11.10 `series theme set`

```bash
lightwebpres series theme set [répertoire] --theme <slug>
```

Change le thème d'une série existante en réécrivant **la seule ligne de
`templates/settings.conf` qui soit à l'outil** : la ligne `theme:` (ou le
placeholder commenté `# theme: <slug>` du scaffold, ou en tête de fichier
si ni l'un ni l'autre n'existe) — voir §9.4.2 pour le raisonnement.
Aucun CSS n'est réécrit : la feuille est composée au prochain `build`
depuis la couche du nouveau thème (§9.3), et les valeurs décommentées par
l'auteur restent en place et s'appliquent par-dessus (§9.4.2).

Comportements, tous vérifiés :

- **Répertoire jamais installé** (pas de `templates/`) : erreur fatale
  (code de sortie non nul) renvoyant vers `init` — `series theme set`
  configure une série existante, il n'en crée pas.
- **`templates/` présent mais pas de `settings.conf`** (série installée
  avant la refonte §9) : un scaffold neuf est écrit pour le thème
  demandé — écrire un fichier qui n'existe pas ne trahit aucune
  promesse de propriété (§9.4.2).
- **Thème déjà en place** : `Theme unchanged: already <slug>. Nothing
  written.` — rien n'est écrit, plutôt que de mettre à jour une date de
  modification pour rien.
- **Sinon** : `Theme changed: <ancien> -> <nouveau>`, l'ancien étant
  `default` si aucune ligne `theme:` n'était active — une réponse à
  « remplacé par quoi », pas une valeur manquante. Le message rappelle
  que les valeurs décommentées restent en place et s'appliquent
  par-dessus le nouveau thème, que les commentaires du scaffold montrent
  encore l'ancien (`audit` le signale, §9.4.4), et qu'un `build` doit
  être relancé pour que le changement atteigne `public/`.
- **`<slug>` inconnu de `THEMES`** : erreur fatale qui renvoie vers
  `lightwebpres theme list` (avec le compte des slugs valides).

**`--force` n'existe plus** (le passer est une erreur fatale
`Unknown option`, §2.4) : il ne protégeait que la réécriture partielle
d'un `templates/style.css` à moitié personnalisé — un fichier que plus
rien n'écrit ni ne lit (§9.4.2, §9.8). De même, plus de notion de
« fichier standard », plus de marqueur de thème, plus de refus : la
commande n'écrit que dans un fichier de données, sur une ligne qui lui
appartient.

### 11.11 `status`

```bash
lightwebpres status [répertoire] [--format text|json]
```

Décrit **ce qu'il y a dans une série** sans rien construire : ses
articles, dans l'ordre de `series.json`, chacun avec ses champs
**résolus**.

#### Pourquoi une commande, et pas une lecture de `series.json`

Un titre d'article est le résultat d'une cascade — `series.json`, puis le
bloc meta de l'article, puis le titre de sa couverture, puis `page_dest`
(§20.3.1). Lire `series.json` ne donne donc pas un titre : ça donne, le
plus souvent, un nom de fichier et rien d'autre, parce qu'une entrée
minimale ne porte que `page_source`.

Cette commande existe parce que **la cascade appartient au moteur**. Tout
consommateur qui la réimplémente — `lightwebpres-gui` au premier chef —
en produirait une copie qui dérive, et finirait par afficher un titre que
le build ne donne pas. C'est la même raison qui a fait exister
`theme show` (§11.9.1) plutôt que de laisser un second calcul de
contraste s'installer ailleurs : quand un consommateur a besoin d'une
donnée que le moteur possède, **le moteur l'expose ; il ne se fait pas
fouiller**. L'alternative était d'élargir la surface interne que le GUI
atteint déjà (§1.2), c'est-à-dire d'ajouter un symbole de plus dont la
suite de tests d'ici ne voit pas le couplage.

Elle répond aussi à une question que rien ne traitait en ligne de
commande : « qu'y a-t-il dans cette série ? ». `verify` compare, `audit`
avertit, `build` construit ; aucun ne se contente de dire ce qu'il y a.

#### Ce qu'elle rapporte

Par article, dans l'ordre de `series.json` — l'ordre **est** une donnée,
c'est lui qui fixe la navigation inter-articles :

- `page_source`, et le `page_dest` résolu ;
- les champs résolus de la cascade : `page_title`, `page_desc`,
  `card_title`, `card_desc`, `card_label`, `nav_title`, `nav_desc` ;
- `status`, parce qu'un article écarté du build reste dans la série et
  qu'un consommateur doit pouvoir le montrer comme tel plutôt que de le
  faire disparaître — y compris un article `ignored`, qui est hors de la
  chaîne mais pas hors du fichier ;
- pour chaque champ, **d'où vient la valeur retenue** — `series.json`, le
  bloc meta, le contenu, ou le repli. C'est ce qui permet à une interface
  de dire « ce titre vient du fichier » plutôt que de présenter une
  valeur dérivée comme si l'auteur l'avait écrite.

Au niveau de la série : le `series_meta`, le thème en vigueur, et le
décompte des articles, réparti sur les trois statuts de §20.6.

**Les trois champs éditoriaux ne sont pas rapportés ici.** `author`,
`license` et `date` se résolvent comme les autres, mais leur
avant-dernier niveau est `series_meta` (§20.3.1) : un défaut *de série*,
écrit par l'auteur, qui n'est ni la ligne `series.json` de cet article ni
un repli intégré. Il porte son propre mot, `series-default` — le sixième
du vocabulaire, décidé avant les clés qui l'emploient. `resolve` (§11.12)
les atteint par leur nom, un à la fois ; cet inventaire-ci reste sur les
huit champs d'affichage, parce qu'un rapport qui liste tout n'a pas
besoin de porter aussi ce que personne n'y cherche.

#### Ce qu'elle ne fait pas

Elle **ne construit rien** et n'écrit rien. Elle ne valide pas non plus
au-delà de ce que la résolution exige : une série dont un article est
introuvable est une erreur de `build`, et le rester ; `status` n'a
pas à devenir un second `verify`.

**Un article illisible ne coûte pas le reste de la réponse.** Un
`page_source` absent, illisible ou non-UTF-8 ne peut être lu ni pour son
bloc meta ni pour son contenu : l'entrée est **quand même rapportée**,
ses champs repliés sur ce que `series.json` et les défauts donnent,
`source_read` à `false`, et un `[WARN]` sur **stderr** — pour que stdout
reste un document JSON unique. Le code de sortie reste 0 : le
renseignement sur les autres articles est intact, et la faute est déjà
fatale là où elle doit l'être (§20.3, `build` et `verify`). La rendre
fatale ici ferait de `status` le second `verify` qu'elle refuse
d'être, et priverait une interface de toute la série pour un fichier
manquant.

#### Format

`--format json` comme pour `theme show`, et pour la même raison — la
bibliothèque standard porte `json` et pas `yaml`. Les noms de clés sont
une **surface publique** consommée par `lightwebpres-gui` : les renommer
casse le GUI sans que rien ne rougisse ici, ce qui en fait un élément du
contrat de §1.2 au même titre que les symboles internes qui y sont listés.

La sortie texte est le défaut et vise la lecture humaine.

**Les clés, une par une.** Racine :

| Clé | Type | Sens |
|---|---|---|
| `schema` | chaîne | `lightwebpres.status/1`. Même promesse que celle de `theme show` : le nombre change quand une clé change de sens ou disparaît, jamais parce qu'une clé s'ajoute |
| `lightwebpres_version` | chaîne | le `VERSION` de l'exécutable qui a répondu |
| `target` | objet | ce sur quoi la question portait (ci-dessous) |
| `series_meta` | objet | les six champs textuels de §20.5 — `title`, `subtitle`, `version`, `intro`, `author`, `license` —, `null` pour un champ que l'auteur n'a pas écrit. `comment` en est absent : c'est une note de relecture que le build ignore (§4.6). Le repli « série sans titre » n'est **pas** appliqué : c'est une décision de rendu, et qui dépend de la langue (§7.3), alors que cette commande ne prend pas de `--lang` et décrit une donnée |
| `counts` | objet | un nombre par statut de §20.6 — `active`, `draft`, `ignored` — dont la somme est la liste entière. Un article `ignored` est toujours *dans* le fichier de série : le sortir discrètement de l'arithmétique ferait paraître la série plus petite qu'elle n'est |
| `articles` | liste | un objet par article, **dans l'ordre de `series.json`** (ci-dessous) |

`target` :

| Clé | Type | Sens |
|---|---|---|
| `kind` | `"series"` | la seule cible de cette commande ; présent pour que le bloc ait la forme de celui de `theme show` |
| `directory` | chaîne | le chemin absolu de la série |
| `theme` | chaîne ou `null` | le thème en vigueur, lu dans `templates/settings.conf` par le parseur du build ; `null` quand la série n'en nomme aucun (elle tourne alors sur les défauts du registre, §9.3) |

Un article :

| Clé | Type | Sens |
|---|---|---|
| `page_source` | chaîne | le fichier source, tel que `series.json` le nomme. Seul champ obligatoire (§20.3), donc seul champ sans provenance : il vient toujours de `series.json` |
| `source_read` | booléen | le fichier a pu être lu et analysé. `false` = absent, illisible ou non-UTF-8, et les champs ci-dessous sont repliés d'autant |
| `status` | objet champ | le statut de l'article (§20.6) : `active`, `draft` ou `ignored`. À part des autres parce qu'il ne se lit pas comme eux — il ne dit pas ce que la page affiche, il dit si elle existe |
| `fields` | objet | les huit champs résolus, dans l'ordre où la cascade les résout : `page_dest`, `page_title`, `page_desc`, `card_title`, `card_desc`, `card_label`, `nav_title`, `nav_desc`. Chacun est un objet champ |

Un **champ** — la forme ne change jamais, y compris quand la valeur est
vide, parce qu'un `card_label` qui se résout légitimement à rien a quand
même une provenance :

| Clé | Type | Sens |
|---|---|---|
| `value` | chaîne | la valeur retenue, exactement celle que le build emploierait |
| `source` | chaîne | le niveau de la cascade qui l'a décidée (ci-dessous) |

**Le vocabulaire de provenance est fermé**, et il est celui de toute
commande d'ici qui répond à « d'où vient cette valeur ? » : un
consommateur n'écrit qu'un seul code, pour deux écrans voisins.

| Valeur | Ce qu'elle dit |
|---|---|
| `series` | le fichier de série a décidé — ici, l'entrée de l'article dans `articles[]` |
| `article` | le bloc meta de l'article a décidé |
| `series-default` | le `series_meta` a décidé : une valeur écrite une fois pour toute la série. N'apparaît que pour les champs qui ont ce niveau — `author`, `license`, et les réglages de notes (§6.5) |
| `content` | déduit du contenu de l'article lui-même : le titre `#` de sa fiche cover, ou son `summary` |
| `derived` | calculé depuis un autre champ résolu : `page_dest` depuis `page_source` extension changée, `card_title` depuis `page_title`, `nav_desc` depuis `card_desc` |
| `default` | le repli intégré, **y compris** « se résout à vide » |

Deux conséquences à énoncer, parce qu'elles se devinent mal :

- La provenance porte sur **le champ**, pas sur l'origine ultime du
  texte. Un `card_title` qui hérite d'un `page_title` lui-même déduit de
  la fiche cover est `derived` : personne n'a écrit de `card_title`, et
  c'est précisément ce que l'interface doit pouvoir dire.
- `status` n'est pas un champ d'affichage et n'est pas rangé avec eux :
  les autres disent ce que la page montre, celui-là dit si elle existe
  (§20.6).

#### Une seule cascade, pas deux

La commande ne résout rien elle-même : elle rapporte ce que
`resolve_article_fields()` — la fonction que le build appelle — a résolu,
et les provenances que cette fonction a enregistrées **pendant** qu'elle
résolvait. C'est la raison d'être de la commande retournée contre son
implémentation : exposer la cascade en la réécrivant aurait installé
dans cet exécutable la copie divergente qu'on refuse au GUI. Un test le
tient (aucune fonction de `status` n'atteint l'analyseur d'article),
parce que deux implémentations qui dérivent continuent chacune de passer
ses propres tests.

#### Consommateur connu

`lightwebpres-gui` s'en sert pour lister les articles d'une série avec
leurs vrais titres, et pour distinguer un titre écrit d'un titre déduit.
C'est un contrat entre les deux dépôts au sens de §1.2, exactement comme
pour `theme show`.

### 11.12 `resolve`

```bash
lightwebpres resolve [répertoire] <nom> [--article <fichier>] [--format text|json]
```

Répond à une seule question, sur **un seul nom** : *quelle est sa valeur
ici, et à quel niveau a-t-elle été décidée ?* Et, parce que c'est la
moitié utile de la réponse, **elle montre aussi les niveaux perdants**.

#### Pourquoi

Ce format porte quatre cascades — les champs d'article (§20.3.1), les
propriétés de thème (§9.3), les réglages de notes (§6.5), les champs
éditoriaux — et aucune n'écrit son résultat nulle part. Aujourd'hui, pour
savoir ce que vaut `tag.fg` dans une série, il faut lire `settings.conf`,
puis la table du thème, puis les défauts du registre, et reconstituer de
tête l'ordre dans lequel les trois se recouvrent. Pour savoir ce que vaut
`page_title`, il faut lire `series.json`, puis le bloc meta, puis la
fiche cover. Le moteur, lui, connaît la réponse : il vient de la calculer.

`status` (§11.11) et `theme show` (§11.9.1) répondent déjà, mais
chacune par un **inventaire** : tous les articles, ou toutes les
propriétés. Elles servent à peupler une interface. `resolve` sert à
comprendre une surprise — « pourquoi ce titre-là ? », « pourquoi cette
couleur alors que j'ai écrit autre chose ? » — et une question ponctuelle
ne se pose pas en lisant deux cents lignes de rapport.

**Les niveaux perdants sont la fonctionnalité, pas un ornement.** Une
valeur seule ne dit pas pourquoi la ligne qu'on vient d'écrire n'a rien
changé. La chaîne, si : elle montre que `settings.conf` porte bien la
propriété mais que la ligne est encore commentée, ou que `series.json`
écrase le bloc meta qu'on était en train de corriger. C'est exactement la
classe de fautes qu'un format à cascades produit et qu'aucun message
d'erreur ne peut attraper, puisqu'il n'y a pas d'erreur : le mécanisme a
fonctionné, sur une entrée dont l'auteur avait oublié l'existence.

#### La forme du nom choisit la cascade

Aucun argument ne dit de quel genre de nom il s'agit, parce que le nom le
dit déjà (§20.0) :

| Forme du `<nom>` | Cascade interrogée |
|---|---|
| pointé — `tag.fg`, `card.title.size` | les propriétés de thème (§9.3) |
| `snake_case` — `page_title`, `notes_placement` | les champs d'article et de série (§20.3.1, §6.5) |
| `kebab-case` — `fact-label`, `highlight-caption` | les champs de diapositive (§4.3) |

C'est la contrepartie concrète de la convention de nommage : un espace
d'interrogation **plat**, sans collision, et sans table de désambiguïsation
à écrire ni à tenir à jour. Un nom dont la forme ne correspond à rien de
connu est une erreur qui **nomme la lecture faite** — « `notes-placement`
a été lu comme un champ de diapositive ; aucun champ de diapositive ne
porte ce nom » —, parce que la faute la plus probable est justement d'avoir
écrit la mauvaise forme.

#### Ce que chaque genre rapporte

**Propriété de thème.** La chaîne est celle de §9.3, du plus fort au plus
faible : `article` (une ligne `style.<propriété>` du bloc meta, présente
seulement avec `--article`), `settings` (`templates/settings.conf`),
`theme` (le thème que ce fichier nomme), `default` (le registre). Chaque
niveau montre la valeur **écrite** ; le niveau retenu montre en plus la
valeur **résolue**, avec les sauts de référence traversés (`ink-quiet →
#6b7280`), puisqu'une valeur écrite peut être un mot et pas une couleur
(§9.2).

**Les balises d'instance ne sont pas dans la chaîne.** Elles sont la
cinquième couche (§9.6.3), mais elles sont *par occurrence* : il n'y a pas
une valeur d'instance dans un article, il y en a autant que de balises.
Une cascade qui prétendrait en retenir une mentirait sur les autres.
`audit` les énumère déjà, et c'est la bonne forme pour cette donnée-là.
La chaîne le dit explicitement plutôt que de les omettre en silence.

**Champ d'article ou de série.** La chaîne est celle de §20.3.1, du plus
fort au plus faible : `series`, `article`, `series-default`, `content`,
`derived`, `default` — le vocabulaire de §11.11, sans un mot de plus. Un
champ ne porte que les niveaux qui existent pour lui : `card_label` n'en
a que trois, `author` en a quatre, `page_title` cinq. Un niveau affiché
vide et un niveau qui n'existe pas ne se ressemblent pas ici, parce que
le premier est un endroit où l'auteur *pourrait* écrire la valeur qu'il
cherche.

Les réglages de notes (§6.5) et les commutateurs de typographie (§4.5)
ont chacun leur cascade, plus courte, et elle est rapportée telle quelle
— y compris quand elle n'a qu'un niveau utile : « ce champ ne se règle
que dans le bloc meta » est la moitié utile de la réponse.

Les champs de `series_meta` (§20.5) se résolvent sans `--article` ; tous
les autres l'exigent, et l'erreur qui le dit **liste les articles de la
série**, pour que la correction soit un copier-coller et pas une
recherche.

**Champ de diapositive.** Il n'a pas de cascade : il est écrit sur une
diapositive ou il n'y est pas. La réponse honnête n'est donc pas une
valeur unique mais un **relevé de sites** — chaque diapositive qui porte
ce champ, avec son article, son rang, son titre et sa valeur. C'est la
même question (« quelle valeur, et où ? ») posée au seul niveau que ce
champ possède. Sans `--article`, le relevé couvre la série entière.

#### Ce qu'elle ne fait pas

Elle ne construit rien et n'écrit rien. Comme `status`, elle ne
valide pas au-delà de ce que la résolution exige, et un article illisible
n'est pas fatal : il est signalé sur stderr et le reste de la réponse
tient. Elle ne prend pas de `--lang` : elle décrit des données, pas un
rendu.

**Deux noms sont refusés, avec leur raison.** `comment` est une note de
relecture : tous les niveaux la lisent et aucun moteur de rendu ne
l'emploie, donc elle n'a pas de valeur résolue — c'est aussi le seul nom
que les deux niveaux se partagent, et le refuser est ce qui évite d'avoir
à trancher lequel des deux la question visait. `slide_title` n'est pas un
champ : le titre d'une diapositive s'écrit `#` ou `##` (§22.2). Répondre
quelque chose serait pire que refuser dans les deux cas.

#### Format

Texte par défaut, pour la lecture humaine. `--format json` pour un
consommateur, avec la même promesse de schéma que les deux commandes
voisines. Racine :

| Clé | Type | Sens |
|---|---|---|
| `schema` | chaîne | `lightwebpres.resolve/1` |
| `lightwebpres_version` | chaîne | le `VERSION` de l'exécutable qui a répondu |
| `query` | objet | `name`, `kind`, `directory`, `article` (ou `null`) |

`kind` a quatre valeurs. Trois viennent directement de la forme du nom —
`theme-property`, `article-field`, `slide-field` — et la quatrième,
`series-field`, du fait que `snake_case` couvre deux niveaux : `author`
et `license` existent aux deux, et interrogés **sans** `--article` la
question porte sur la valeur de la série. Le `kind` le dit, plutôt que de
laisser un lecteur appliquer le vocabulaire d'article à une réponse de
série.
| `resolution` | objet | la réponse (ci-dessous) |

`resolution`, pour une propriété de thème ou un champ d'article :

| Clé | Type | Sens |
|---|---|---|
| `value` | chaîne | la valeur retenue, celle que le build emploierait |
| `source` | chaîne | le niveau qui l'a décidée — mêmes mots que §11.11 |
| `chain` | liste | les niveaux, **du plus fort au plus faible**, y compris ceux qui n'ont rien à dire |

Un maillon de `chain` :

| Clé | Type | Sens |
|---|---|---|
| `level` | chaîne | le niveau, même vocabulaire que `source` |
| `present` | booléen | ce niveau porte-t-il une valeur ? |
| `value` | chaîne ou `null` | ce qu'il porte, tel qu'écrit |
| `winner` | booléen | ce maillon est-il celui qui a décidé ? |
| `note` | chaîne ou absent | pourquoi ce niveau n'a pas été consulté (pas de `--article`, balises d'instance hors cascade) |

L'ordre est **le plus fort d'abord** dans les deux cas, alors que les deux
cascades sont écrites en sens inverse l'une de l'autre dans ce document
(les propriétés fusionnent du plus faible au plus fort, les champs
s'essaient du plus fort au plus faible). Le rapport tranche pour l'ordre
de lecture d'un humain qui débogue : on commence par le niveau qui aurait
dû gagner.

Pour un champ de diapositive, `resolution` porte `sites`, une liste de
`{article, slide, slide_title, value}`, dans l'ordre des articles puis des
diapositives. Deux formes plutôt qu'une seule forcée : `kind` les
distingue, et prétendre qu'un relevé de sites est une cascade à un maillon
aurait été une uniformité de façade.

#### Une seule cascade, encore

Comme `status`, la commande ne résout rien elle-même : elle
interroge `resolve_article_fields()` et `resolve_theme_properties()`, les
fonctions que le build appelle. Un test l'exige, pour la raison déjà
donnée en §11.11 — deux implémentations qui dérivent continuent chacune
de passer ses propres tests.

---

## 12. Algorithme du build

### 12.1 Étape par étape

```
build(répertoire):
  1. series = read_json(répertoire/series.json)
  2. lang = --lang OU $LWP_LANG OU "fr" (défaut)
  3. language = load_language(lang, --language-file)  # rules + strings, §19.5 pour l'ordre de priorité complet
  4. settings = parse_settings(répertoire/templates/settings.conf)  # §9.3.1 ; absent = couche vide
     css = compose_stylesheet(défauts ← thème(settings.theme) ← settings)  # §9.3 — en mémoire, jamais sur disque
           + read_file(répertoire/templates/custom.css)  # ajouté en dernier (§9.3.2)
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
          "css": css,  # recomposée pour cette page si le bloc meta porte des propriétés style.* (§9.6.1)
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
  renommer/supprimer un champ gelé (§20.2), changer la sémantique de la
  cascade (§20.3.1), retirer une commande ou une option. C'est exactement
  ce qui a motivé le gel de nomenclature avant la 1.0.

**Le contrat stable, c'est l'entrée, pas la sortie.** Sont garantis
stables au sein d'une même version MAJEURE : les noms et la portée des
champs (`GLOSSARY.md` § « Naming conventions », liste gelée en §20.2),
la structure de `series.json`, le format de l'article `.md`, les commandes et options de la CLI, les variables `LWP_*`. Le
**HTML produit**, lui, peut changer entre deux CORRECTIFs (amélioration de
style, de sémantique, d'accessibilité) : c'est pourquoi `verify` (§11.4)
signale une dérive normale après une montée de version, jusqu'au prochain
`build` — ce n'est pas une régression, mais le comportement attendu. Un
build reste **reproductible à l'octet pour une version donnée** (§13.3),
ce dont `verify` dépend ; la reproductibilité ne traverse pas les versions.

Avant la 1.0, toutes les releases sont des **préversions** : le format a
pu bouger d'une mineure à l'autre (c'est la phase de stabilisation qui
s'achève avec le gel des noms de champs (§20.2). La 1.0 est le premier
engagement de stabilité
au sens ci-dessus.

---

## 14. Parcours utilisateur

### 14.1 Parcours de création

```bash
# 1. Installer le framework
cp lightwebpres /usr/local/bin/  # ou utiliser ./lightwebpres

# 2. Créer une nouvelle série
lightwebpres init ma-serie

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
lightwebpres verify ma-serie

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
# 5. L'LLM vérifie : lightwebpres verify ma-serie
# 6. Si OK, l'LLM signale que la correction est faite
```

### 14.4 Parcours de pipeline CI

```bash
# Le .gitlab-ci.yml (créé par init --gitlab-ci, opt-in — §10/§11.1) fait :
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

1. CLI avec `init`, `build`, `verify`
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
13. Commande `verify` (comparaison)
14. Génération du README

### Phase 4 : CI et polish

16. `.gitlab-ci.yml` de base
17. Templates par défaut (CSS, JS)
18. Tests unitaires
19. Documentation

### Phase 5 : commande `audit` (implémentée)

Voir §11.5. Contrairement à `verify` (qui compare le HTML généré à
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
    affiché petit, centré et gris (propriétés `caption.*`, encre
    `ink-quiet` par défaut, §9.1) sous l'image — le style par défaut suit
    donc automatiquement chaque thème. Les légendes
    de **tableaux** restent non planifiées.
22. **Agrandissement d'image (lightbox)** — pas de comportement par défaut
    (ouvrir l'image en taille réelle par-dessus la page) ; à ajouter dans
    `nav.js` le jour où le besoin se présente. À ne pas confondre avec une
    figure cliquable, qui elle est une ligne-image enveloppée d'un lien
    Markdown (§6.1) et n'a rien à voir avec du JavaScript.
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
  fichier — seuls `custom.css` et `nav.js` le sont
- **`.css`** : `templates/custom.css` ajouté après la feuille composée
  (§9.3.2), le tout inliné dans `<style>` ✓
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
- **Override** : `settings.conf`/`custom.css`/`nav.js` et le fichier de
  langue sont éditables (§9, §7) ; la structure HTML des pages ne l'est
  pas ✓ (délibérément, §9)

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
  <!-- matrice 2×3 : copier le lien / afficher le QR code × série / article / fiche, §9.3.4 -->
</div>

<div class="share-qr-modal" id="shareQrModal">
  <!-- QR code SVG généré côté client, §9.3.4 -->
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
| `{{css}}` | Feuille composée en mémoire (§9.3) + `templates/custom.css` | Le CSS inline |
| `{{slides}}` | Généré par le build | Toutes les `<section class="slide">` |
| `{{js_nav}}` | `templates/nav.js` | Le JS de navigation (scroll, boutons, bouton de partage, encodeur QR) |
| `{{str_KEY}}` | `language/{lang}.json` → `strings` | Chaîne d'interface (voir §7.3), remplacée dans `page.html` **et** dans `js_nav` une fois celui-ci chargé |
| `{{meta_head}}` | `author`/`page_desc` résolus (§20.3.1) | Balises `<meta name="author">` et `<meta name="description">` (débalisées, échappées) — vides toutes deux = rien d'émis |
| `{{page_footer}}` | `author`/`date`/`license` résolus (§20.3.1) | Pied de page éditorial (`<footer class="page-footer">`) — tout absent = rien d'émis |
| `{{build_stamp}}` | `--build-stamp`/`--build-stamp-minimal` (§11.3.2) | Marqueur de fraîcheur du build, vide par défaut |
| `{{draft_banner}}` | `status: draft` + `--include-drafts` (§20.6) | Bandeau « Brouillon » centré dans l'en-tête, vide hors brouillon |

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
par les flèches au niveau document (§9.3.5).

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
| `{{js_index}}` | Généré, intégré à l'exécutable | Le JS spécifique à l'index (scroll) — pas overridable (§9). Pas de bouton de partage sur l'index (§9.3.4) |
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

#### 19.3.1 Ce que font les règles embarquées

Le mécanisme ci-dessus dit comment une règle s'applique ; cette section
dit **ce que les règles livrées font**, parce que c'est le contrat qu'un
auteur de nouveau pack lit pour savoir ce qui est déjà couvert et ce
qu'il lui reste à écrire.

**La distinction qui gouverne tout : règle de langue ou règle de mise en
page.** Une règle de **langue** encode une convention nationale — en
français l'insécable devant `; : ! ? »`, qui n'existe ni en anglais ni en
allemand. Une règle de **mise en page** protège une espace qui est déjà
là contre une coupure de ligne malheureuse ; elle ne dépend d'aucune
langue et **doit figurer dans tout pack**. Le premier groupe est à
réécrire pour chaque langue, le second est à recopier tel quel.

| Règle | Groupe | Ce qu'elle fait | Packs |
|---|---|---|---|
| `nbsp_before_double_punctuation` | langue | Insécable avant `; : ! ? »` | fr |
| `nbsp_after_opening_quote` | langue | Insécable après `«` | fr |
| `nbsp_before_percent` | langue | Insécable avant `%` | fr |
| `nbsp_thousands_separator` | langue | Insécable entre groupes de 3 chiffres **déjà espacés** — n'ajoute jamais de groupement à `170000` | fr |
| `nbsp_before_unit` | langue | Insécable entre un nombre et `million(s)`, `milliard(s)`, `dollar(s)`, `$` | fr |
| `nbsp_after_operator` | langue | Insécable entre `×`/`≈` et le nombre qui suit | fr |
| `nbsp_inside_dash_incise` | **mise en page** | Incise encadrée de tirets : insécable **après** le tiret ouvrant et **avant** le fermant, sécable à l'extérieur | fr, **en** |
| `nbsp_before_lone_dash` | **mise en page** | Tiret non apparié : insécable **avant**, pour qu'il ne puisse jamais commencer une ligne | fr, **en** |

**Les deux règles de tiret sont dans le pack anglais, et ce n'est pas une
inadvertance.** Un cadratin collé à ses mots (`word—word`, style Chicago)
n'offre aucune espace à protéger : la règle ne matche pas et ne fait
rien. Un cadratin espacé (`word — word`, style AP et la plus grande
partie de l'écrit web) s'orpheline exactement comme en français. La règle
protège une espace existante ; elle ne change jamais ce qui est écrit.
Elle vaut donc pour toute langue qui espace ses tirets.

**Ce que le moteur ne fait pas, et ne fera pas par défaut :** transformer
un signe en un autre. Aucune règle embarquée ne promeut un trait d'union
en cadratin, ne redresse une apostrophe droite, ne convertit `"` en
guillemets. Ce sont des transformations de **contenu**, pas de mise en
page : elles réécrivent ce que l'auteur a tapé, et un article déjà publié
verrait son texte muter au build suivant. Un auteur qui les veut les
ajoute dans son propre `language/<lang>.json` — le mécanisme de surcharge
(§19.2) est fait pour ça. À titre d'exemple, la promotion d'un trait
d'union espacé, qui n'existe pas en français, en tiret d'incise :

```json
{
  "name": "dash_from_spaced_hyphen",
  "pattern": "(?<=[^\\s\\d]) - (?=[^\\s\\d])",
  "replacement": " — ",
  "flags": "g"
}
```

**Cinq contraintes qu'une règle doit respecter**, toutes vérifiables :

1. **Idempotence** (§19.3) : appliquée deux fois, elle ne doit rien
   changer. Une règle qui insère une insécable doit donc exclure le cas
   déjà traité — c'est la raison du `(?!\u00a0)` de
   `nbsp_before_lone_dash`.
2. **Écrire l'insécable en `\u00a0`, jamais en caractère littéral.** Un
   U+00A0 dans un fichier source est invisible : il se perd à la copie,
   au passage dans un éditeur, dans un diff. Les deux packs embarqués
   l'écrivent en échappement pour cette raison, découverte en le perdant.
3. **Ne jamais toucher à ce qui n'est pas espacé.** C'est ce qui
   distingue un tiret d'un trait d'union : `Marie-Claire` et `12-15`
   n'ont pas d'espace, donc aucune règle de tiret ne les voit.
4. **L'ordre compte** : les règles s'appliquent dans l'ordre du tableau,
   et une règle peut dépendre du travail de la précédente. L'incise
   appariée passe avant le tiret solitaire, sans quoi le tiret ouvrant
   serait lié des deux côtés.
5. **Pas de quantificateur imbriqué.** Un fichier de langue est du code
   de confiance (§7.2), mais ses regex tournent sur tout le texte de tous
   les articles : une classe négative bornée (`[^—–]*?`) est linéaire, un
   `.*` sous `DOTALL` ne l'est pas.

### 19.4 Fichier `en.json` (anglais)

L'anglais n'a **aucune règle de langue** — pas d'insécable avant la
ponctuation, pas de guillemets français — mais il porte les **deux règles
de mise en page** sur les tirets (§19.3.1), et un bloc `strings` aussi
complet que le français, puisque c'est lui qui sert de repli ultime
(§7.1, §7.4) :

```json
{
  "lang": "en",
  "name": "English",
  "rules": [
    { "name": "nbsp_inside_dash_incise",  "...": "..." },
    { "name": "nbsp_before_lone_dash",    "...": "..." }
  ],
  "strings": {
    "nav_prev": "Previous slide",
    "copy_link": "Copy link"
  }
}
```

Cette section a longtemps affirmé que `rules` était vide « car l'anglais
n'a pas de règles typographiques spéciales ». C'était vrai des règles de
langue et faux des règles de mise en page : un cadratin espacé, qui est
la norme de l'écrit web anglophone, s'orpheline en fin de ligne dans les
deux langues. La distinction est maintenant celle du §19.3.1, et c'est
elle qu'un auteur de pack doit suivre.

### 19.5 Packs par défaut embarqués dans l'exécutable

L'exécutable contient en interne les packs `fr` et `en` (règles + chaînes)
sous forme de strings JSON. La commande `init` les extrait dans
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

`--no-typography`, sur `build` et `verify` (§11.3/§11.4), saute entièrement
le chargement d'un moteur de règles pour ce lancement — aucune règle,
qu'elle vienne du pack intégré ou d'un override (§7.4/§19.5), ne s'exécute
sur aucun article ni sur l'index, pour toute la durée de ce build. C'est
la portée la plus large des trois mécanismes de désactivation (§4.5) :
`typo_units`/`typo_thousands` ne visent qu'une paire de règles nommées,
`typo: off` vise déjà toutes les règles mais pour un seul article, `--no-
typography` les vise toutes pour tout le build — y compris toute règle qui
serait ajoutée plus tard, puisque le mécanisme ne construit simplement pas
de moteur du tout plutôt que d'énumérer des noms de règles à exclure.

---

## 20. Schéma formel de `series.json`

### 20.0 Nomenclature : la forme d'un nom dit son niveau

Le format n'a pas trois styles de nommage par accident. **La forme d'un
nom indique à quel niveau il se règle**, et c'est une règle, pas une
habitude :

| Forme | Niveau | Exemples |
|---|---|---|
| `kebab-case` | champ de **diapositive** | `fact-label`, `highlight-caption` |
| `snake_case` | champ d'**article** ou de **série** | `page_title`, `nav_desc`, `notes_placement` |
| `pointé` | **propriété de thème** (`composant.axe`) | `card.title.size`, `verdict.yes.fg` |

Ce que cela achète, dans un format où un même fichier porte les trois :
un coup d'œil suffit à savoir si une ligne va dans un en-tête de
diapositive ou dans le bloc meta. Se tromper d'endroit **ne produit
aucune erreur** — le champ est simplement ignoré — donc un indice lisible
vaut mieux qu'un diagnostic qui n'existera jamais.

**Et c'est ce qui rend `resolve` (§11.12) implémentable sans registre de
désambiguïsation.** La forme du nom dit à quelle cascade s'adresser :
`resolve page_title` interroge la cascade d'article, `resolve fact-label`
celle de diapositive, `resolve card.title.size` celle du thème. Un espace
d'interrogation plat, sans collision et sans arbitrage à écrire. La
convention n'est donc plus seulement une aide de lecture : elle est
portante.

**Corollaire, et il est contraignant :** un nouveau champ est nommé
d'après son niveau, jamais d'après ce qui « paraît naturel ». Quatre
champs de niveau article — les réglages de notes et deux commutateurs de
typographie — ont été nommés en kebab-case par voisinage visuel avec
`highlight-caption` et avec le CSS, alors que la règle les voulait en
`snake_case`. C'est le mode de rupture à attendre : la ressemblance
l'emporte sur la règle dès que rien ne vérifie. Un test le vérifie
désormais.

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
| `status` | chaîne | non | build/verify/status | `active` (défaut) \| `draft` \| `ignored` (§20.6) |
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
  sinon **erreur fatale**, pour `build` comme pour `verify`, vérifiée en
  amont avant toute écriture (aucune sortie partielle). Un article
  volontairement absent du build a ses mécanismes dédiés : `status: draft`
  et `status: ignored` (§20.6). `audit`, non bloquant par contrat, signale le fichier
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
  octet par octet, ce sur quoi `verify` (§11.4) repose.
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

### 20.6 Statut d'un article (`status`)

`status` dit **ce qu'un article vaut à la série qui le liste**. Trois
valeurs, insensibles à la casse, et rien d'autre — une valeur inconnue
est une erreur fatale nommant l'article, au même titre que toute autre
valeur typée de ce format :

| Valeur | Construit | Compté | Ce que c'est |
|---|---|---|---|
| `active` | oui | oui | le défaut, et ce que veut dire une entrée qui ne dit rien |
| `draft` | seulement sous `--include-drafts`, avec bandeau | oui | un article de la série, tenu hors de la **sortie** |
| `ignored` | jamais, quels que soient les drapeaux | non | un article **hors de la chaîne**, dont la configuration survit |

Posable dans l'entrée `series.json` ou le bloc meta de l'article,
`series.json` prioritaire (§20.3.1). Absent partout : `active`.

**Le champ existe pour `ignored`.** Retirer un article d'une série se
faisait en supprimant son entrée, ce qui jetait avec elle tous les champs
qu'elle portait — `card_label`, `nav_title`, `page_dest`, le travail de
réglage entier. Un mot suffit désormais, et un mot le ramène.

`draft` est le comportement du booléen qu'il remplace, à une chose près
qui n'en est plus une : le prédécesseur avait besoin d'une règle propre
disant que **la présence** choisissait le niveau, et non la valeur, parce
que `"draft": false` était indistinguable d'un champ absent — sans quoi
`series.json` n'aurait jamais pu remettre en circulation un brouillon
déclaré dans le fichier. Avec trois mots nommés, aucune valeur n'est
« fausse » : `"status": "active"` dans `series.json` écrase un
`status: draft` du bloc meta par la cascade ordinaire, sans exception à
écrire ni à tester.

**Ce que chacun coûte au reste de l'outil :**

- **Le build.** `ignored` sort de la liste d'abord et sans condition ;
  `draft` sort ensuite, sauf `--include-drafts`. Il n'y a **pas** de
  drapeau pour construire un article `ignored` : ce serait en faire un
  second `draft`, alors que c'est précisément la valeur qui n'a aucun
  effet. Chaque exclusion est annoncée (`[ignored] x.html`,
  `[draft] x.html skipped`), jamais silencieuse.
- **Le nom d'index (§11.3.3).** Le décompte se prend **entre les deux
  filtres** : un brouillon est un article de la série, donc une série de
  deux dont l'un est brouillon a bien un index à protéger, et la
  collision est fatale avec ou sans `--include-drafts`. Compter la liste
  effectivement construite rendrait un même `series.json` légal ou
  illégal selon un drapeau de build. Un article `ignored` n'est pas un
  article de la série : il ne compte pas.
- **`status` (§11.11).** Trois nombres, dont la somme est la liste
  entière — un article `ignored` est toujours *dans* le fichier de série,
  et un rapport qui le sortirait discrètement de l'arithmétique ferait
  paraître la série plus petite qu'elle n'est. Il reste **listé**, avec
  son statut : il est hors de la chaîne, pas hors du fichier, et un
  consommateur doit pouvoir le montrer et le ramener.
- **`audit`.** Il n'exclut rien, ni brouillons ni ignorés — c'est un
  outil d'écriture, le travail en cours est ce qu'il doit regarder. Et
  c'est **le seul endroit qui nomme un article `ignored`** : tout le
  reste de l'outil est muet à son sujet par construction, ce qui est son
  intérêt et aussi son unique danger, puisqu'un article peut rester hors
  circuit des mois pendant que son auteur se souvient l'avoir écrit.

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

### 22.9.2 Type inconnu dans un marqueur `<!-- lwp:slide:TYPE -->`

Erreur fatale, citant le rang de la fiche, le jeton fautif et la liste des
types connus — quelqu'un qui a mal tapé `cover` ne peut pas aller lire une
liste qui n'existe que dans le code.

C'est le défaut le plus probable de ce format, et c'était le seul que le
moteur ne signalait pas : `render_slide()` traite comme `standard` tout ce
qui n'est ni `cover`, ni `series-nav`, ni `full-article`, donc
`<!-- lwp:slide:covre -->` se publiait — sans erreur, sans avertissement,
et avec une fiche d'ouverture du mauvais type. Les quatre types sont un
registre (`SLIDE_TYPES`), lu par cette validation **et** par `--help` : un
type ne peut pas être reconnu par l'un et absent de l'autre. L'analyse
syntaxique, elle, reste permissive sur le jeton ; c'est la validation qui
refuse, pour que le message puisse nommer le rang de la fiche.

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
