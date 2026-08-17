# Antériorité — systèmes de jetons et catalogues de thèmes

**Relevé d'enquête.** Ce document rassemble ce qui a été trouvé ailleurs
avant la refonte du système de thèmes de 2026-08-04 : comment les
systèmes de jetons, les générateurs comparables et les catalogues de
palettes existants ont résolu — ou raté — les mêmes problèmes.

Il n'oblige rien. `specifications.md` fait foi, et §9.1 et §9.8 portent
celles de ces conclusions qui **contraignent la conception** : la norme à
deux niveaux et son seuil de rentabilité, la leçon base16/Tinted, le
critère « qui paie la migration », et le fait que `contrast-color()` ne
répond pas au besoin. Ce qui reste ici est l'enquête elle-même — qui fait
quoi, avec quelles versions, à quelle date — c'est-à-dire ce qu'une spec
normative n'a pas à porter et ce qui vieillira.

Les mesures de contraste qui accompagnaient §6.3 ont rejoint
`REVISION-THEMES.md`, qui est le relevé de mesure sur ce sujet.

Informatif. Ne préjuge pas de l'architecture, mais borne l'espace des solutions
et écarte deux fausses pistes.

## 1. Nous sommes à deux niveaux, pas trois — et c'est la norme

Dans le vocabulaire de l'industrie, l'architecture à trois tiers est
*primitive → sémantique → composant*. Nos « réglages de forme » ne sont pas un
tiers de jetons : c'est une décomposition par propriété, plus proche d'un jeton
composite. Nous visons donc **deux tiers**, ce que 90 % des équipes ont adopté
et que les critiques de la sur-conception recommandent explicitement pour les
petits projets. Le tiers *composant* — celui dont on dit qu'il est rarement
justifié — n'est pas en jeu.

Le seuil de rentabilité de la couche sémantique, tel qu'il ressort des sources,
est **le troisième ou quatrième thème**. Nous en avons trente-trois.

Aucun générateur comparable n'expose trois niveaux : reveal.js en a deux
(27 variables, 3 dérivées), Quarto en a deux explicites dans `_brand.yml`
(palette nommée → rôles sémantiques), mkdocs-material deux avec variantes
dérivées, Hugo/Zola/Eleventy zéro au niveau du moteur.

## 2. Le mécanisme existe et il est éprouvé : le défaut dérivé

VS Code déclare chaque couleur d'atelier avec un défaut qui n'est pas forcément
une valeur : ce peut être un autre jeton, ou une **transformation** d'un autre
jeton — `transparent(x, 0.5)`, `darken(x, 0.2)`, `lighten`, `lessProminent`,
`oneOf(a, b, c)` pour une chaîne de repli, `ifDefinedThenElse` pour un
comportement conditionnel à ce que le thème a fourni. Les défauts sont **par
polarité** : `lighten` en sombre, `darken` en clair.

Conséquence : un thème VS Code ne définit pas ses six cents clés, il en définit
quelques dizaines. C'est exactement E2 + E3, et c'est calculable en Python en
une vingtaine de lignes, résolu à la génération, avec un CSS émis qui reste
plat.

shadcn/ui livre la variante minimale du même geste, en CSS pur : un bloc qui
donne les valeurs, un bloc qui aliase vers les rôles.

## 3. Le conflit fidélité/accessibilité ne se résout pas — il se refuse

Mesures indépendantes, formule WCAG 2, sur deux fonds clairs nommés :
la table est en annexe A de `REVISION-THEMES.md`, qui est le relevé de
mesure sur ce sujet et que `BACKLOG.md` B5 cite.

**Aucun accent d'aucune de ces palettes n'atteint 4,5:1 sur fond clair.** Pas
un seul. Le problème n'est pas Dracula, c'est la classe entière des palettes
d'accents conçues pour fond sombre. Et Solarized — le seul système conçu
explicitement pour les deux fonds, avec des écarts de clarté symétriques en
CIELAB — plafonne à 3,2–3,7:1, c'est-à-dire AA pour grand texte, jamais pour
texte courant. Les seuls jetons Solarized qui passent 4,5:1 sur clair sont les
monotones, ceux dont la fonction *est* d'être du texte.

**Corollaire directement actionnable :** sur fond clair, les accents empruntés
sont utilisables comme surface, comme bordure, comme marqueur graphique — jamais
comme texte de corps. C'est E4, et c'est ce qui rend E4 décisif plutôt que
cosmétique : la correction n'est pas un réglage par thème, c'est une séparation
par classe d'emploi.

Et personne, dans les projets qui prennent le sujet au sérieux, ne rend une
palette sombre telle quelle sur fond clair : **Dracula publie Alucard**,
**Catppuccin publie Latte**, les auteurs de base16 font deux schémas distincts
« plutôt qu'une palette réversible unique ». Rendre sept palettes conçues pour
fond sombre sur un fond clair et appeler cela « fidélité » est une fidélité au
tableau de valeurs hexadécimales, pas au thème — les auteurs eux-mêmes ne s'y
reconnaîtraient pas. Cela déplace l'option 1 de B5 : basculer Dracula, Monokai
et Tokyo Night en `dark_background` n'est pas une perte de fidélité, c'en est le
rétablissement.

## 4. Notre trajectoire a déjà été jouée par base16

Seize emplacements à sémantique fixe, remplis par des palettes tierces →
critiques documentées de lisibilité et de rigidité, dont « deux sens distincts
partagent un emplacement, on ne peut pas les séparer » → tentative de refonte
d'un coup (base17) **abandonnée**, les mainteneurs préférant enrichir le format
« itérativement plutôt que d'un coup » → direction retenue (Tinted8) : séparer
la palette de ses usages, et séparer les usages entre eux.

La leçon d'ingénierie n'est pas « faites une couche sémantique ». C'est
**séparez palette et usage, et faites-le par étapes**.

## 5. Deux emprunts techniques à retenir

**Prévoir dès la conception le jeton « texte posé sur le jeton coloré ».** Radix
garantit ses pas de texte par construction, mais a dû ajouter `--accent-contrast`
parce qu'un pas coloré ne pouvait pas satisfaire deux contraintes à la fois. Le
même mur nous attend sur `--fact-strong-highlight` / `--fact-strong-ink`, qui
sont déjà couplées par contrat et par rien d'autre.

**Exprimer la contrainte comme un écart de clarté, pas comme un ratio à
vérifier après coup.** C'est ce que fait MD3 en imposant des écarts de ton
plutôt que des ratios. Transposable sans HCT : un ajustement de clarté en OKLCH
préserve teinte et chroma — le vert de Dracula reste perceptuellement le vert de
Dracula tout en devenant lisible. À noter que `contrast-color()` en CSS natif,
disponible partout depuis avril 2026, ne répond pas au besoin : elle ne renvoie
que du noir ou du blanc.

## 6. Les pièges, nommés pour être écartés

1. **Un jeton par occurrence ou par état** (`footnote-marker-hover-color`) est le
   patron que tout le monde regrette. Nommer les rôles, pas les occurrences.
2. **Les chaînes d'alias au-delà de deux sauts** annulent le bénéfice : le
   lecteur ne peut plus connaître une valeur sans remonter la chaîne. Voir C10.
3. **Sémantiser par symétrie.** La couleur et la typographie s'y prêtent,
   l'espacement beaucoup moins. Ne pas inventer de rôles là où une valeur suffit.
4. **Annoncer un nombre de jetons écrit à la main.** Voir D3 : il a déjà dérivé.
5. **La spécificité des sélecteurs de thème est une dette d'API.**
   mkdocs-material qualifie ses règles de thème par deux attributs et condamne
   ses utilisateurs à `!important`.

## 7. Sur la migration

Notre politique — rupture nette, sans alias, annoncée à voix haute — est celle
de Radix Themes, qui procède ainsi à chaque majeure avec un inventaire nominatif
exhaustif dans le changelog. Le facteur discriminant n'est pas la taille du
projet mais **qui paie la migration** : alias et codemods se justifient quand des
milliers de dépôts tiers consomment les jetons. Ce n'est pas notre cas.

Il existe un moyen terme gratuit et absent chez Radix, que nous pratiquons déjà
sur un seul renommage : **l'avertissement à la génération**. C'est E7, et
l'infrastructure existe (`audit_legacy_palette_names`).

Le format W3C DTCG a atteint sa première version stable en octobre 2025, mais
reste un *Community Group*, pas une Recommandation. S'y conformer imposerait du
JSON, un résolveur d'alias, une détection de cycles et une gestion de types,
pour un exécutable qui n'échange de jetons avec aucun outil tiers. **Ne pas s'y
conformer**, mais en retenir trois idées : qu'un alias est une valeur légitime,
que la dépréciation porte un message explicatif, et que **les cycles doivent être
détectés** — si les groupes de réglage peuvent s'aliaser entre eux, il y aura des
cycles, et un plantage obscur est pire qu'une erreur nommée.

---
