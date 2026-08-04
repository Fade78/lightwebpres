# Architecture du système de rendu d'un thème

**Statut :** proposition d'architecture, répondant au cahier des charges
`CDC-TEMPLATES.md`. Destinée à être fondue dans `specifications.md` §9.

**Date :** 2026-08-04. **Base :** v0.12.2.

---

## 0. Périmètre

Deux sujets se ressemblent et ne sont pas le même.

**Ce document traite du système de rendu :** comment une feuille de style
cohérente se construit **à partir d'un thème donné**. C'est ce qui se grave dans
le code et dans la documentation, parce que c'est ce que la machine exécute.

**Il ne traite pas de la construction d'un thème cohérent :** comment choisir six
couleurs qui vont ensemble, ce qui rend une palette réussie, si telle entrée du
catalogue mérite d'y figurer. C'est un savoir éditorial, il a sa propre place, et
le mélanger ici produirait une architecture qui juge ses entrées au lieu de les
traiter.

La frontière est nette et elle est utile : **le rendu doit donner un résultat
lisible à partir de n'importe quel thème admissible.** Si la qualité du rendu
dépendait de la qualité du thème, le système serait mal conçu. Tout ce qui suit
découle de cette exigence.

Trois passages du dossier relèvent de l'autre sujet et sont écartés ici : les
critères d'admission d'une palette au catalogue, le jugement de fidélité sur les
palettes empruntées, et la question de savoir si telle valeur de thème est bien
choisie. Ils sont signalés au fil du texte, jamais traités.

**Hypothèse de travail, posée par le propriétaire :** un seul utilisateur, capable
de tout régénérer. L'architecture est donc conçue pour être juste, pas
compatible. Les contraintes C1, C2 et C5 du cahier des charges ne sont pas
contournées, elles sont **supprimées** : elles n'existent qu'au service d'une
compatibilité sans bénéficiaire.

---

## 1. Décisions

**Q1 — Jusqu'où va la couche ?** Sur tous les sens, d'un coup — la leçon
d'incrémentalité de base16 vaut pour un écosystème tiers, nous n'en avons pas.
Mais un groupe n'est créé que là où deux consommateurs doivent pouvoir diverger,
jamais un par sélecteur : **20 groupes**, pas 61.

**Q2 — Les groupes sont-ils thémables ?** Oui, et facultativement. Un thème
fournit sa palette et peut s'arrêter là.

**Q3 — Les palettes empruntées ?** Le rendu cesse de poser la question : un
signal emprunté ne porte plus jamais de texte, donc n'a plus de plancher à
franchir. Ce qui reste — telle entrée est-elle fidèle à son origine — appartient
à l'autre sujet.

**Q4 — Dérivé calculé ou écrit ?** Calculé à la génération, émis en hexadécimal
littéral.

**Q5 — Rupture nette ?** Oui, sans alias ni transition, avec un avertissement
nominatif parce qu'il est gratuit.

---

## 2. Le principe organisateur

**Le fond détermine l'obligation de contraste, donc le rendu s'organise par
fond.**

C'est ce qui manquait. Aujourd'hui une couleur est déclarée sans que rien ne dise
sur quoi elle sera posée — et un rapport de contraste n'existe pas dans l'absolu,
il existe contre un fond. Aucune vérification n'était donc possible. Trois fonds
existent dans le format :

| Fond | Ce qui s'y pose | Plancher |
|---|---|---|
| **la page** (`--page`) | l'essentiel du texte et du mobilier | texte 4,5:1 (corps 7:1), mobilier 3:1 |
| **la couverture** (`--cover-bg`) | titre, tag, compteur, résumé | texte 4,5:1 |
| **une surface colorée** (surlignage, colonne, pastille) | le texte posé dessus | texte 4,5:1 |

Chaque groupe de réglage **déclare son fond**. La vérification devient totale et
mécanique : le générateur connaît, pour chaque encre qu'il émet, le fond exact
contre lequel elle sera rendue. On passe d'un système qui espère le contraste à
un système qui le connaît.

---

## 3. Les trois couches

```
  ┌─ COUCHE 1 ── PALETTE ──────────────────────────────────────────┐
  │  6 valeurs, fournies par le thème. C'est l'ENTRÉE du rendu.    │
  │  Aucune règle CSS ne les référence jamais directement.         │
  └────────────────────────────────────────────────────────────────┘
                              ↓ résolu à la génération
  ┌─ COUCHE 1bis ─ DÉRIVÉS ────────────────────────────────────────┐
  │  Calculés depuis la palette et la polarité : encres lisibles,   │
  │  superpositions, couverture. Émis en hexadécimal littéral.     │
  └────────────────────────────────────────────────────────────────┘
                              ↓ aliasé
  ┌─ COUCHE 2 ── GROUPES DE RÉGLAGE ───────────────────────────────┐
  │  20 sens nommés, chacun avec son fond déclaré et ses axes.     │
  │  Seule couche que les règles CSS ont le droit de lire.         │
  └────────────────────────────────────────────────────────────────┘
                              ↓
  ┌─ COUCHE 3 ── RÉGLAGES DE FORME ────────────────────────────────┐
  │  Les axes : encre, fond, graisse, style, décoration, filet.    │
  │  Ce que l'auteur surcharge.                                    │
  └────────────────────────────────────────────────────────────────┘
```

La règle qui fait tenir l'ensemble, empruntée à Primer :

> **Aucune règle en dehors du bloc `:root` ne référence une valeur de palette.**

Vérifiable par un balayage du corps de la feuille. C'est le test le plus rentable
du dispositif : il rend l'érosion impossible plutôt que détectable. Les 61
liaisons directes d'aujourd'hui sont exactement ce qu'il interdit.

---

## 4. Couche 1 — le contrat d'entrée

Ce que le rendu **exige d'un thème**, et rien de plus. Six valeurs, avec une
ligne de partage explicite.

```css
/* Achromatiques — le thème les destine à porter du texte */
--page          /* le fond de page */
--ink           /* l'encre du corps */
--ink-muted     /* l'encre secondaire */

/* Chromatiques — signaux. Le rendu ne les pose JAMAIS en texte. */
--signal-mark   /* ce qui marque : surlignage, filet, repère   (ex- --marker)  */
--signal-notice /* ce qui appelle l'attention                  (ex- --accent)  */
--signal-affirm /* ce qui affirme                              (ex- --positive)*/
```

Trois renommages. Motif : sous l'ancienne architecture la palette portait les
sens, un nom de sens y était donc juste. Sous la nouvelle elle porte des
identités générales que les groupes spécialisent — `--accent` était de surcroît
un mot de design qui ne signifiait rien, et `--positive` un sens si étroit qu'il
ne servait qu'un usage.

**Le partage achromatique/chromatique est la clé de voûte du rendu.** Il ne dit
pas ce qu'un bon thème doit contenir ; il dit ce que le rendu fait de chaque
entrée. Les trois premières, il les pose en texte. Les trois dernières, jamais —
il en dérive une encre quand du texte est nécessaire (§5.1). C'est ce qui lui
permet d'accueillir n'importe quelle palette sans la trahir ni la censurer.

> *Hors périmètre :* ce qui fait qu'une palette est bien choisie, et si `--ink`
> devrait franchir un seuil pour être admise au catalogue. Le rendu n'exige rien
> de tel — voir §9.

---

## 5. Couche 1bis — les dérivés

Calculés à la génération, émis en hexadécimal littéral. L'auteur les lit, les
comprend, et les surcharge comme le reste.

### 5.1 Les encres de signal — la garantie de rendu

Pour chaque signal, une encre lisible sur le fond où elle servira :

```
--signal-mark-ink      --signal-notice-ink      --signal-affirm-ink
```

Obtenues en conservant **teinte et chroma en OKLCh** et en déplaçant la seule
clarté jusqu'à franchir le plancher, par le plus petit écart possible. La
direction se déduit de la polarité : vers le sombre sur fond clair, vers le clair
sur fond sombre. Mesures réelles, contre le fond de chaque thème :

| Thème | Signal publié | Ratio | Encre résolue | Ratio | ΔL |
|---|---|---|---|---|---|
| dracula | `#50FA7B` | 1,29 | `#008500` | 4,52 | −0,355 |
| dracula | `#FF5555` | 2,95 | `#D82C35` | 4,55 | −0,106 |
| tokyo-night | `#9ECE6A` | 1,26 | `#3F6800` | 4,53 | −0,327 |
| monokai | `#A6E22E` | 1,46 | `#4C7F00` | 4,54 | −0,306 |
| solarized | `#859900` | 2,97 | `#677900` | 4,52 | −0,103 |
| nord | `#A3BE8C` | 1,77 | `#5C7446` | 4,51 | −0,240 |
| gruvbox | `#B8BB26` | 1,82 | `#717200` | 4,50 | −0,236 |

**C'est ici que se joue la propriété centrale du système : le rendu est lisible
quel que soit le thème.** Pas parce que les thèmes sont bons — le rendu n'en sait
rien et n'a pas à en juger —, mais parce qu'il ne demande jamais à une couleur de
faire un métier qu'elle ne peut pas faire.

**Et il faut le dire sans détour : l'encre résolue n'est pas la couleur publiée,
c'en est un parent de même teinte.** Pour un accent très clair sur fond clair
l'écart est grand — `#008500` n'est pas `#50FA7B`. On ne rend pas ce vert-là
lisible ; on cesse de le lui demander. La couleur publiée garde les emplois où
elle est reconnaissable — surlignage, colonne mise en avant, filet, pastille de
verdict —, le parent résolu ne sert que là où il y a du texte à lire. Le conflit
fidélité/accessibilité que l'antériorité déclarait insoluble l'était pour une
couleur faisant deux métiers ; il se dissout dès qu'on les sépare.

Deux réserves d'implémentation, à traiter et non à ignorer : le déplacement de
clarté sort parfois du gamut sRGB et le chroma s'y fait écrêter — c'est le cas de
`#008500`, et un vrai mappage de gamut réduirait le chroma plutôt que de le
laisser clipper. Et une encre déjà conforme n'est pas déplacée : sur un thème
sombre, `--signal-affirm-ink` vaut souvent le signal lui-même.

### 5.2 Les superpositions et la couverture

Inchangées dans leur principe — neuf voiles translucides et le sol de couverture,
choisis par polarité. C'est déjà une couche dérivée correctement faite ; elle
rejoint la couche 1bis au lieu de flotter à côté.

---

## 6. Couche 2 — les vingt groupes

Chaque groupe déclare son **fond** et ses **axes**. Les défauts aliasent la
couche 1bis. Le nom suit `--<groupe>-<réglage>`, plat, sans arborescence.

### Sur le fond de page

| Groupe | Axes | Encre par défaut |
|---|---|---|
| `text-body` | ink | `--ink` |
| `text-lead` | ink | `--ink` |
| `text-support` | ink | `--ink-muted` |
| `text-quote` | ink, rule | `--ink-muted` |
| `tag` | ink, weight | `--ink-muted` |
| `fact-label` | ink, weight | `--ink-muted` |
| `footnote` | ink | `--signal-notice-ink` |
| `verdict-yes` | ink, weight, mark | `--signal-affirm-ink` |
| `verdict-no` | ink, weight, mark | `--ink-muted` |
| `verdict-partial` | ink, weight, mark | `--signal-notice-ink` |
| `link` | ink, decoration-color | `--ink` |
| `focus` | ring, width | `--signal-notice` |
| `nav-dot` | idle, active, active-scale | `--rule-strong` / `--signal-mark` |
| `rule-fact` | color, width | `--signal-mark` |
| `rule-header` | color | `--signal-mark` |
| `col-signal` | ground, edge | `--sunken` / `--signal-notice` |
| `col-snap` | ground, edge | `--sunken` / `--signal-mark` |

### Sur une surface colorée

| Groupe | Axes | Défaut |
|---|---|---|
| `fact-strong` | ground, ink, weight, style, decoration, decoration-color | `--signal-mark` / encre résolue **sur ce fond** |

### Sur la couverture

| Groupe | Axes | Défaut |
|---|---|---|
| `cover` | ground, ink, ink-faint | dérivés de polarité |
| `cover-tag` | ink | `--signal-mark`, ou son parent résolu sur le sol de couverture |

**Vingt groupes, une quarantaine de réglages**, plus 6 de palette et une
quinzaine de dérivés : environ **soixante propriétés déclarées**. Dans la bande
où se situent 60 % des systèmes de jetons, pour trente-trois thèmes et un format
à objets nommés. Proportionné.

**Ce que le regroupement refuse.** `text-support` couvre légende, source,
signature, description, pied de page, références et numéro de fiche — sept
consommateurs, un groupe. Aucun besoin de les faire diverger n'est attesté. Le
jour où il le sera, scinder coûte trois lignes et ne casse rien : c'est ce qui
autorise à ne pas anticiper. Le piège du jeton par occurrence
(`footnote-marker-hover-color`) est écarté par cette règle et par elle seule.

**Ce que le regroupement obtient.** Les trois parcours de friction du cahier des
charges deviennent une ligne chacun, après le marqueur :

```css
:root { --verdict-partial-ink: #8a4b00; }   /* n'atteint ni la note ni le focus */
:root { --text-lead-ink: #2b2b38; }         /* n'atteint pas le verdict « non » */
:root { --signal-notice: #B3221F; }         /* corrige à la source : l'encre suit */
```

La troisième mérite un mot : elle touche la palette, donc l'encre résolue est
recalculée avec — l'auteur corrige une valeur, pas deux, et la cohérence suit.

---

## 7. La résolution : le `:root` est généré, pas rustiné

**Changement structurant.** Aujourd'hui `apply_theme()` réécrit des déclarations
par expression régulière, ce qui impose que chaque variable préexiste, que sa
valeur soit hexadécimale, que la substitution soit confinée au premier `:root`,
et qu'un fichier antérieur devienne non standard dès qu'on ajoute quoi que ce
soit.

Le bloc `:root` devient une **sortie générée**, reconstruite entièrement :

```
    thème (6 couleurs + polarité + surcharges éventuelles)
      → résolution des dérivés (encres, voiles, couverture)
      → résolution des groupes (alias → littéral ou var())
      → émission du bloc :root complet
```

Ce que cela supprime d'un seul geste :

- **C2** — plus de « réécrit mais n'ajoute jamais » : on ne modifie pas un bloc,
  on le produit. Ajouter une variable devient gratuit.
- **C4** — plus de contrainte hexadécimale : la reconnaissance par motif
  disparaît avec la réécriture.
- `unsubstituted_declarations()` — sans objet : il n'y a plus de déclaration
  qu'on puisse manquer.
- Le sentinelle « 21 » de `set-theme`, et le décompte manuel qui a déjà dérivé
  (D3) : le nombre est désormais un `len()`.
- **C3** reste satisfaite pour une raison plus simple : rien ne cherche plus de
  motif dans le fichier, donc les recettes en commentaire ne peuvent plus être
  prises pour du code.

`theme_state()` survit allégé : régénérer et comparer. Même garantie, sans le
couplage.

---

## 8. Le contrat d'un thème

```python
'dracula': {
    'label': 'Dracula', 'source': '…', 'note': '…',
    'intensity': 'vivid',
    'dark_background': True,

    'page': '#282A36', 'ink': '#F8F8F2', 'ink-muted': '#6272A4',
    'signal-mark': '#F1FA8C', 'signal-notice': '#FF5555',
    'signal-affirm': '#50FA7B',

    'groups': {                       # facultatif, absent chez la plupart
        'fact-strong-style': 'italic',
    },
}
```

Le verrou de clés (C5) est remplacé par une validation de schéma : les six
couleurs exactement, les métadonnées connues, et un `groups` dont chaque clé doit
être un réglage existant. Un thème qui ne fournit que sa palette reste valide —
c'est le cas de trente-trois sur trente-trois aujourd'hui. Et
`--link-decoration-color`, mort-né faute de pouvoir entrer dans une entrée,
devient simplement `'groups': {'link-decoration-color': …}`.

**Détection de cycles obligatoire.** Dès qu'un groupe peut en aliaser un autre,
un cycle est possible : il doit être détecté à la génération et nommé, jamais
laissé produire une récursion.

**Profondeur d'alias plafonnée à deux sauts** (C10, A8), vérifiée par test. En
pratique la chaîne est règle → groupe → littéral : un saut. Le lecteur d'une
feuille émise connaît toujours une valeur en remontant une fois.

---

## 9. Les garanties du rendu

Cinq tests portent l'architecture. Aucun n'existe aujourd'hui.

**G1 — Aucune règle hors `:root` ne lit la palette.** L'invariant central.

**G2 — Tout groupe déclare un fond.** Sans quoi G3 ne peut pas s'exécuter.

**G3 — Chaque encre franchit le plancher de son fond déclaré, sur les 33
thèmes.** C'est la garantie de rendu : elle porte sur ce que le générateur
produit, jamais sur ce qu'un thème contient. Un thème mal choisi donnera un
résultat laid ; il ne donnera pas un résultat illisible.

**G4 — Aucune chaîne d'alias ne dépasse deux sauts.**

**G5 — Le nombre de variables annoncé est dérivé du code.** D3 ne peut plus se
reproduire.

> *Hors périmètre :* vérifier qu'une valeur de palette franchit un seuil — que
> `--ink` tienne AAA contre `--page`, par exemple. C'est un critère d'admission
> au catalogue, donc une propriété du thème et non du rendu. Il a toute sa place,
> dans l'autre document. Le rendu, lui, ne doit pas s'en remettre à cette
> vérification pour être correct : c'est exactement ce que §5.1 garantit.

---

## 10. Le fichier émis

```css
/* LightWebPres default style */
/* lightwebpres-theme: dracula */
:root {
  /* ── PALETTE ── fournie par le thème. Aucune règle ne la lit. ── */
  --page: #282A36;  --ink: #F8F8F2;  --ink-muted: #6272A4;
  --signal-mark: #F1FA8C;  --signal-notice: #FF5555;  --signal-affirm: #50FA7B;

  /* ── DÉRIVÉS ── calculés. Encres lisibles, voiles, couverture. ── */
  --signal-affirm-ink: #50FA7B;   /* déjà à 10,4:1 sur ce fond sombre */
  --rule: rgba(255,255,255,0.10);
  …

  /* ── GROUPES ── ce que les règles lisent, ce que vous surchargez. ── */
  --text-body-ink: var(--ink);
  --verdict-yes-ink: var(--signal-affirm-ink);
  --verdict-yes-weight: 700;
  …
}
/* … les règles, qui ne lisent que les groupes … */
/* … les recettes prêtes à coller, une par groupe utile … */
/* === Local customizations: refresh-templates keeps everything below === */
```

Trois blocs commentés, dans l'ordre de dépendance. La feuille se lit du général
au particulier, et l'auteur voit immédiatement à quel niveau il intervient.

---

## 11. Migration

Rupture nette, sans alias : `refresh-templates` régénère, et c'est tout.

Conservé de la politique maison parce que gratuit : `audit` reçoit la table des
noms retirés et nomme le remplaçant.

```
[WARNING] templates/style.css: --accent no longer exists.
          Text usage  → --footnote-ink, --verdict-partial-ink
          Ring usage  → --focus-ring
          Palette     → --signal-notice
```

Trois entrées — `marker`, `accent`, `positive` —, et l'avertissement est d'autant
plus utile que l'ancien nom se scinde en plusieurs remplaçants selon l'emploi.
C'est précisément le cas où un alias serait faux et où un message est juste.

La fixture d'un `style.css` antérieur (A2) reste souhaitable mais cesse d'être
urgente : elle protégeait un coût de migration que l'hypothèse de travail annule.
Déclassée, pas abandonnée.

---

## 12. Ce que cette architecture ne fait pas

- **Elle ne juge aucun thème.** Les critères d'admission au catalogue, la
  fidélité d'une palette empruntée à son origine, le choix de basculer telle
  entrée en fond sombre : autant de questions réelles, et aucune n'est ici. Le
  rendu les rend seulement moins urgentes, en cessant de faire dépendre la
  lisibilité de leur réponse.
- **Elle ne rend pas `#50FA7B` lisible.** Rien ne le peut. Elle lui retire la
  charge de l'être.
- **Elle n'ouvre pas la structure HTML** ni le format d'entrée.
- **Elle ne crée pas de format de thème externe.** `THEMES` reste la source
  unique ; l'architecture ne ferme aucune porte de ce côté.
- **Elle ne garantit pas la séparabilité en vision dichromate.** La marque de
  forme des verdicts la sert déjà, mais aucune simulation n'est prévue. Manque
  assumé, à verser au backlog.
- **Elle ne traite pas le mappage de gamut** au-delà du constat de §5.1. Un
  écrêtage de chroma sur les cas extrêmes est acceptable en première version,
  pas satisfaisant.
- **Elle ne dit rien de `--content-max`**, seule propriété déclarée jamais
  thémée : valeur de mise en page, hors du dispositif de couleur.
