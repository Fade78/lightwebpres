# Six thèmes à écrire — décisions arrêtées le 2026-08-17

Issus d'un aller-retour sur maquettes. Toutes les valeurs ci-dessous ont
été rendues et mesurées à l'instrument 2
(`tests/test_rendered_contrast.py`), sur la page `middle.html` de la démo
à 1440×900.

> **État : implémenté**, sauf `pop-rose`. Les slugs ont changé au
> moment d'écrire la famille `light`, qui les a absorbés dans un ensemble
> plus large : `sky-dream` → **`dusk`**, `night` → **`midnight`**,
> `daydream` → **`daybreak`**. `pink-dream` et `cloudy` gardent leur nom.
> Le fond de `daybreak` a bougé de `#A8CBEC` à `#A8C7EC` (il tombait dans
> la bande `cyan`, ce qui aurait coupé le triptyque du ciel en deux
> facettes) et celui de `pink-dream` de `#1A0B1F` à `#1A0B17` (il tombait
> dans `violet`, où il percutait `nebula`). Voir la section finale pour
> ce qui a été livré autour.

## Pourquoi ces thèmes-là

Croisement teinte × polarité des 34 thèmes existants :

| teinte | clair | sombre |
|---|---|---|
| neutral | 13 | 7 |
| red | **—** | pop-red |
| orange | pop-tangerine | **—** |
| yellow | pop-lemon | monokai |
| green | **—** | evergreen, pop-lime |
| cyan | **—** | pop-lagoon |
| blue | **—** | dracula, tokyo-night, blueprint-night, pop-cobalt |
| violet | **—** | synthwave, pop-violet |
| magenta | **—** | pop-fuchsia |

**La colonne claire est vide de couleur** : treize thèmes clairs, douze
neutres. La famille pop couvre déjà les huit teintes — son manque n'est
pas une teinte de plus, c'est qu'elle est une famille sombre avec deux
exceptions claires.

Côté halos : deux thèmes en avaient, `code` et `terminal`, avec le
**même** `#33FF88`. Et `shadow.dy` n'était utilisé par **aucun** thème —
tout l'axe de l'ombre portée, par opposition à la lueur, dormait.

## Les six

Le fond de couverture vaut `color.ink` et ne suit pas `color.page` : on
peut donc changer le fond des fiches sans toucher à la couverture.

### 1. `pop-rose` — light / vivid / magenta

```
color.page: #FFC2D8   color.ink: #40071F   color.ink-quiet: #7A1440
color.mark: #FFE761   color.call: #1F3A8A  color.affirm: #0F5132
```
Mesuré : 35 éléments, **0 sous AA**, pire 6,37:1.

### 2. `pink-dream` — dark / vivid / magenta, lueur

Base sombre obligatoire (voir « piège » plus bas).
```
color.page: #1A0B1F   color.ink: #FFD9EC   color.ink-quiet: #D79FC0
color.mark: #FF5FA2   color.call: #FFB86C  color.affirm: #7CE0B0
title1.shadow.fg: #FF5FA277      title1.shadow.blur: 0.30em
highlight.shadow.fg: #FF5FA266   highlight.shadow.blur: 0.20em
```
Mesuré : **0 sous AA**, pire 5,83:1.

### 3. `sky-dream` — dark / vivid / blue, lueur

```
color.page: #081524   color.ink: #D8ECFF   color.ink-quiet: #94BEE0
color.mark: #4CC9F0   color.call: #FFC46B  color.affirm: #7CE0B0
title1.shadow.fg: #4CC9F080      title1.shadow.blur: 0.30em
highlight.shadow.fg: #4CC9F06B   highlight.shadow.blur: 0.20em
```
L'accent est un **or chaud**, pas un troisième bleu : sans lui la fiche
vire au camaïeu et la hiérarchie disparaît. Mesuré : **0 sous AA**,
pire 5,61:1.

### 4. `night` — dark / vivid / blue, lueur, plus sombre

```
color.page: #030711   color.ink: #DCEEFF   color.ink-quiet: #8FB6D8
color.mark: #58D5FF   color.call: #FFC46B  color.affirm: #7CE0B0
page.shadow.fg: #58D5FF1F        page.shadow.blur: 0.14em
title1.shadow.fg: #58D5FF8C      title1.shadow.blur: 0.30em
highlight.shadow.fg: #58D5FF73   highlight.shadow.blur: 0.20em
```
Mesuré : **0 sous AA**, pire 6,37:1.

### 5. `daydream` — light / vivid / blue, ombre portée — **version C retenue**

```
color.page: #A8CBEC   color.ink: #14304A   color.ink-quiet: #36597A
color.mark: #FFD166   color.call: #A63D0F  color.affirm: #0F5132
page.shadow.fg: #14304A26        page.shadow.blur: 0.13em   page.shadow.dy: 0.05em
title1.shadow.fg: #2E6B9E66      title1.shadow.blur: 0.28em title1.shadow.dy: 0.10em
highlight.shadow.fg: #2E6B9E59   highlight.shadow.blur: 0.16em highlight.shadow.dy: 0.06em
```

**Une ombre portée et non une lueur, délibérément** : une lueur sur fond
clair est invisible — du clair sur du clair ne fait rien. Même bleu,
même famille, l'autre mécanisme.

Mesuré : **8 éléments sous AA sur 35**, pire 3,96:1 (les trois lignes de
la fiche de navigation, puis kicker, légende, source). L'encre
principale reste à 8,0:1. **C'est un choix assumé** : §11.9.1 dit que
tous les thèmes n'ont pas à atteindre AA, et le rapport du registre
annoncera `fail` de lui-même, ce qui est le comportement voulu — l'auteur
voit le niveau avant de choisir. Deux profondeurs avaient été mesurées,
`#B5D3EF` (3 sous AA) et `#A8CBEC` (8) ; la seconde est retenue.

### 6. `cloudy` — light / sober / neutral, ombre portée

```
color.page: #EDF1F5   color.ink: #1F2933   color.ink-quiet: #52606D
color.mark: #FFD966   color.call: #B54708  color.affirm: #0F5132
page.shadow.fg: #1F293329        page.shadow.blur: 0.13em   page.shadow.dy: 0.05em
title1.shadow.fg: #1F293366      title1.shadow.blur: 0.26em title1.shadow.dy: 0.10em
highlight.shadow.fg: #1F29334D   highlight.shadow.blur: 0.13em highlight.shadow.dy: 0.05em
```
Mesuré : **0 sous AA**, pire 5,18:1.

## Le halo se dessine contre le glyphe, en `em`

Première version écrite en unités de viewport : les deux `h1` d'une même
page recevaient **0,70 et 1,21** de flou rapporté à leur taille, pour la
même déclaration, et tout le reste de la page n'avait rien. Réécrit en
`em`, les deux partagent **0,26**. Le chiffre clé passe de 29,3 px de
flou à 12,6 px.

C'est le défaut §5.7 — « longueur figée contre le glyphe » — mais dans la
couche thème plutôt que dans le squelette.

## Deux limites, et une décision qui reste à prendre

**`page.shadow` ne peut pas être proportionnelle au glyphe.** C'est une
propriété héritée : son `em` se résout une seule fois à la racine (16 px
→ 2,1 px) puis se propage comme une longueur absolue. Mesuré après
correction :

| élément | taille | flou ÷ taille |
|---|---|---|
| kicker, `fact-label`, source | 13,5 px | 0,15 |
| summary | 24,3 px | 0,09 |
| **`h2` de fiche** | **42,3 px** | **0,05** |
| `h1` | 54,9 / 31,5 px | 0,26 |
| chiffre clé | 97,2 px | 0,13 |

Le `h2` est le plus mal servi, et il n'existe que **trois** points
d'accroche pour les halos : `page`, `title1`, `highlight`. Ni `title2`,
ni `summary`, ni `fact`.

**Décision en attente** : accepter que l'atmosphère soit uniforme et que
seuls le titre et le chiffre aient un halo proportionnel — ce qui se
défend —, ou ajouter des points d'accroche au registre. La seconde
option est une modification du **moteur**, pas un réglage de thème.

**Effet de bord constaté** : `page.shadow` étant héritée, elle atteint
aussi l'interface — pastilles de navigation, compteur, panneau
présentateur portent l'ombre du thème (2,1 px à 16 %). Discret, et
défendable pour un thème atmosphérique, mais c'est un choix et non un
accident à découvrir plus tard.

## Piège pour l'auteur, à documenter

Épingler des couleurs sombres dans `settings.conf` **ne déclenche pas**
le mobilier sombre : `DARK_FURNITURE_PROPS` dépend du drapeau
`dark_background` de la définition du thème, qu'un épinglage ne peut pas
atteindre. Constaté en maquettant `pink-dream` sur une base claire : 21
éléments sous AA, pire 1,08:1. Refaite sur base sombre, elle passe à 0.

Rien n'avertit l'auteur. À traiter, au minimum dans le GUIDE.

## À faire à l'implémentation

- Définitions dans `THEMES`, halos dans `THEME_PROPERTY_OVERRIDES`,
  valeurs de notes par thème dans `THEME_NOTE_PROPS`.
- Régénérer `themes-gallery.html` (le test d'identité octet le vérifie).
- **Étendre `test_a_halo_is_drawn_against_the_glyph_it_surrounds`** : il
  ne lit aujourd'hui que `.shadow.blur` et saute les valeurs à `0`.
  `cloudy` et `daydream` seront les premiers thèmes à utiliser
  `shadow.dy` ; sans extension, un décalage écrit en px plat passera
  sans bruit — exactement le défaut 5.8 qu'on vient de corriger.
- Le compte de thèmes est dérivé du registre à plusieurs endroits
  (`--help`, `theme list`, README) : vérifier qu'aucun ne le code en dur.

## Ce qui a effectivement été livré

Les six thèmes ci-dessus sont devenus **dix-neuf**, répartis dans trois
familles. Le catalogue passe de 34 à 53.

**`light` — d'où vient la lumière, et à quelle heure** (11 nouveaux,
15 en tout). Le ciel à trois heures : `daybreak`, `dusk`, `midnight`. Le
feu, dans l'ordre de ce qu'il éclaire : `candlelight`, `lantern`, `lava`.
Ce qui est au-dessus et au-dessous : `aurora`, `nebula`, `abyss`,
`pink-dream`. Et `cloudy`, seul membre sobre de la famille. C'est la
seule famille du catalogue qui remplit **les neuf cases de teinte**.

**`terrain` — le monde matériel** (5 nouveaux, 8 en tout). `loam` (la
terre retournée, le seul fond brun du catalogue), `clay` (la terre
cuite), `concrete` (le béton, accent orange de chantier), `slate` (la
pierre, contrepartie sombre de `concrete`), `canopy` (sous les arbres,
là où `evergreen` est la nuit dans le sous-bois). Aucun halo : la terre
et la pierre n'émettent pas, et c'est ce qui sépare cette famille de
`light`.

**`desk` — le registre du travail** (3 nouveaux, 10 en tout).
`high-contrast-night` complète la paire de `high-contrast` : la
photophobie est un besoin d'accessibilité au même titre que la
malvoyance, et le seul thème qui visait AAA était aussi la page la plus
claire du catalogue. `ledger` et `chalkboard` sont la paire ordinaire —
tous les autres membres de `desk` ont un registre (technique, éditorial,
doré, ou sans couleur du tout) et aucun n'était simplement « un document
de travail ».

**Le défaut trouvé en chemin.** `nav-dot.bg-active` et
`table.col-snap.rule-fg` prennent tous deux `mark` par défaut, et `mark`
est presque partout un surligneur — un lavis assez pâle pour que du texte
survive dessus. En pastille pleine il disparaît : **dix-huit thèmes**
mesuraient sous 3:1, quatre sous 1,10:1, `vaporwave` à **1,007:1** (sa
pastille est son propre fond) et `high-contrast`, dont c'est toute la
promesse, à **1,022:1**. Le lecteur ne voyait pas où il en était dans le
deck. Corrigé thème par thème — `call` là où l'accent a la profondeur,
`ink` sinon — parce que le ton qui marche est une question de palette. Un
garde balaie désormais le catalogue et mesure les deux fonds : la page,
et le rail voilé où la rangée de pastilles est posée.

Conséquence sur les tests : `nord` passe `fail` → `pass` en non-texte, et
le contrôle d'identité de rendu contre `v0.34.0` déclare sa seule dérive
ligne à ligne (`--nav-dot-bg-active` sous `pop-lemon`), le reste restant
comparé octet par octet.
