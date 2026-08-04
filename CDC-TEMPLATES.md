# Cahier des charges — refonte du système de templates

**Statut : document historique, gelé.** Ce cahier des charges décrivait le
système *antérieur* à la refonte de 2026-08-04 et ce qu'elle devait en faire ;
la refonte a eu lieu, et `specifications.md` §9 fait foi. Les contraintes
C1-C12 décrivent un monde démoli (marqueurs, `style.css` substitué,
`theme_state`) — elles expliquent le pourquoi, elles n'obligent plus rien.
L'adjudication des critères A1-A11 est consignée dans l'historique du dépôt
(commit de réadjudication du backlog, 2026-08-04). Restent d'actualité comme
références : la table de mesures du §6.3 (aucun accent emprunté n'atteint 4,5:1
sur fond clair — citée par B5) et les décisions Q1-Q5, dont les réponses sont
dans `ARCHI-TEMPLATES.md` et les messages de commit de la refonte.

---

**Date :** 2026-08-04. **Version de référence :** v0.12.2.

---

## 1. Vocabulaire

Trois mots, fixés ici, à reprendre partout ensuite. Aucun n'est aujourd'hui
défini dans `GLOSSARY.md`, qui ne couvre que les champs du format d'entrée — le
« contrat de vocabulaire partagé » avec le projet GUI est donc vide sur toute la
couche de présentation. C'est un manque à combler, pas une commodité de
rédaction.

**Template** — la couche du haut. Ce qui coordonne : un thème, une feuille
livrée, un choix d'ensemble. C'est le niveau où l'on dit *« ce site ressemble à
ça »*.

**Groupe de réglage** — la couche intermédiaire. Un sens nommé, et les axes qui
le rendent. Le niveau où l'on dit *« le verdict "partiellement" se rend comme
ceci »*, indépendamment de ce que rend le verdict « oui ».

**Réglage de forme** — la feuille. Un attribut : une couleur, une graisse, un
style, une décoration, une épaisseur. Le niveau où l'on dit *« et cette
couleur-là vaut telle valeur »*.

Le mot **rôle** reste réservé à son sens actuel — l'un des six emplois nommés de
la palette. Le mot **marqueur** est aujourd'hui homonyme sur trois objets sans
lien (marqueur de personnalisation, marqueur de thème, marqueur de forme d'un
verdict) et l'un d'eux porte en plus le nom d'une couleur (`--marker`) : la
refonte doit les désambiguïser ou acter l'homonymie explicitement.

---

## 2. Le problème

### 2.1 Le constat

Le modèle a trois niveaux ; le code en a deux. La palette occupe simultanément
le niveau **template** (des valeurs qu'un thème substitue) et le niveau **groupe
de réglage** (des sens assignés). La preuve tient dans la documentation que le
code produit lui-même : la palette y est décrite par ce qu'elle **signifie**.

Six rôles — `--page`, `--ink`, `--ink-muted`, `--marker`, `--accent`,
`--positive` — portent environ **seize sens distincts** et sont consommés
**61 fois** dans `TEMPLATE_STYLE` :

| Rôle | Usages | Sens portés |
|---|---|---|
| `--ink-muted` | 20 | légende, source, tag, signature, citation, verdict « non », et 14 autres |
| `--ink` | 18 | texte courant, résumé de fiche, sol de couverture en thème clair |
| `--marker` | 9 | filet d'encadré, tag de couverture, soulignement de titre, point de nav actif, colonne mise en avant |
| `--page` | 7 | fond, encre de couverture |
| `--accent` | 5 | appel de note, verdict « partiellement », anneau de focus (×2) |
| `--positive` | 2 | verdict « oui » |

Un seul rôle porte un seul sens — et il s'appelle `--positive`, un nom de
signification et non de couleur. Le glissement est déjà inscrit dans le
nommage.

**Conséquence unique, dont tout le reste découle :** on ne peut pas modifier un
sens sans modifier tous ceux qui partagent son rôle. Ce ne sont pas des
variables coordonnées, c'est la même variable.

### 2.2 La signature du glissement

Un groupe de réglage n'a été créé **que là où le besoin dépassait la couleur**.
Le gras d'un encadré de fait demandait graisse, style et soulignement — trois
choses qu'aucune couleur ne peut loger. Un groupe est né : `--fact-strong-*`,
six variables sur quatre axes, avec des défauts qui *pointent* vers la palette
sans s'y confondre, résolus par thème. Partout où le besoin était purement
chromatique, la palette l'a absorbé, parce qu'elle le pouvait.

Ce n'est donc pas une mauvaise direction : c'est une couche appliquée une fois,
là où elle était inévitable, et sautée partout ailleurs. La refonte est
**additive**, pas corrective.

### 2.3 Ce que le problème produit déjà

**B5 et B6 sont un seul fait d'architecture affleurant à deux endroits.** B5 :
trois rôles sous WCAG AA contre leur propre page — `--ink-muted` 9/33 (pire
2,48, solarized), `--positive` 11/33 (pire 1,29, dracula), `--accent` 11/33
(pire 2,05, tokyo-night). B6 : les points de progression sous 3:1 sur les 33
thèmes, parce que `--marker` a été choisi pour surligner et qu'on lui demande
ensuite d'être un point de navigation. B5 note « aucun rôle de palette n'est
libre » : six rôles pour seize sens, il ne peut pas y en avoir de libre.

**Une tentative d'ajout d'axe est déjà morte au verrou.**
`--link-decoration-color` est lu par le code, documenté dans l'aide, une recette
prête à coller existe — et **aucun des 33 thèmes ne le pose**, parce qu'un test
verrouille le contrat de clés d'une entrée de thème et rejetterait la clé. Le
coût de l'opération est donc déjà connu, mesuré sur un seul axe.

**La documentation envoie l'utilisateur sur le mauvais levier.** Quatre surfaces
— la spec, le README, `--help`, et le commentaire du fichier qu'il a sous les
yeux — lui disent que le résumé d'une fiche est peint par `--ink-muted`. La
règle emploie `--ink`. Qui veut foncer ses résumés sans toucher au verdict
« non » suit la doc, redéclare `--ink-muted`, et obtient **zéro effet sur sa
cible, vingt effets hors cible, dont le verdict « non » précisément**.

**Aucun instrument ne regarde la couche en cause.** Il n'y a pas une ligne de
calcul de contraste WCAG dans l'exécutable. Les tests en ont, mais ne mesurent
que des compositions alpha du mobilier — voiles, opacités — jamais les valeurs
de palette. Le code sait mesurer ce que produit le niveau feuille, et ne sait
pas mesurer ce qu'impose le niveau intermédiaire. B5 et B6 ont été trouvés par
une campagne de mesure externe, pas par un test.

### 2.4 Ce que la préservation coûte

La promesse la mieux tenue du système est ce qui rend le contournement toxique.
Ce que l'auteur écrit après le marqueur survit à `refresh-templates`, à
`set-theme`, à tout. Donc une surcharge écrite pour corriger Dracula reste en
place quand l'utilisateur passe à Nord, impose des valeurs calibrées pour une
autre palette, et `set-theme` affiche `Theme changed: dracula -> nord` sans un
mot — alors que cette même commande refuse par ailleurs de toucher un fichier
non standard précisément pour ne pas livrer « une page à moitié recolorée ». Le
garde-fou couvre la portion intégrée et rate exactement le cas qui produit le
symptôme redouté.

Le système protège parfaitement une couche qu'il n'a aucun moyen de comprendre.

---

## 3. Ce que la refonte doit permettre

Exigences fonctionnelles. Chacune est formulée comme un besoin utilisateur
vérifiable, pas comme une solution.

**E1 — Modifier un sens sans déplacer les autres.** Il doit être possible de
changer le rendu du verdict « partiellement » sans toucher à l'appel de note ni
aux anneaux de focus ; de foncer les résumés sans toucher au verdict « non » ; de
recolorer le point de nav actif sans toucher au filet d'encadré. C'est
l'exigence dont tout le reste dérive.

**E2 — Ne rien changer par défaut.** L'introduction de la couche doit être
invisible au rendu : une série installée avant et après doit produire le même
HTML et la même apparence, sur les 33 thèmes. Un défaut qui aliase le rôle
actuel satisfait cette exigence ; une valeur recopiée à la main ne la satisfait
pas durablement.

**E3 — Permettre à un thème de ne surcharger qu'un niveau.** Un thème doit
pouvoir se contenter de fournir sa palette, comme aujourd'hui, sans énumérer les
groupes de réglage. Un thème qui veut corriger un seul groupe doit pouvoir le
faire sans reprendre les autres.

**E4 — Distinguer les emplois textuels des emplois non textuels.** Un rôle sert
aujourd'hui indifféremment à peindre du texte (appel de note, verdict) et du
mobilier (anneau de focus, filet). Ces deux emplois n'ont pas le même seuil de
contraste — 4,5:1 contre 3:1 — et ne peuvent donc pas partager une contrainte.
La couche doit rendre cette distinction exprimable.

**E5 — Mesurer plutôt qu'espérer.** L'exécutable doit pouvoir vérifier, à la
génération, que chaque couple couleur/fond qu'il produit tient son seuil, et le
dire. Aujourd'hui les critères d'admission de §9.5.3 sont de la prose que rien
ne contrôle.

**E6 — Répondre à « qui peint quoi ».** Rien dans le produit ne permet
aujourd'hui de savoir quelle variable peint quel élément ; c'est ce qui rend
l'erreur de documentation du §2.3 indétectable par l'utilisateur. La refonte
doit rendre cette correspondance consultable, et de préférence dérivée du code
plutôt que rédigée à côté.

**E7 — Avertir quand une personnalisation devient caduque.** Une surcharge
d'auteur qui référence un nom retiré, ou qui fixe une valeur qu'un changement de
thème vient de désaccorder, doit produire un avertissement. La politique maison
— rupture nette, annoncée à voix haute, casse silencieuse rendue audible —
s'applique, et `audit` en est le lieu naturel.

**E8 — Offrir des recettes pour plus d'un objet.** Les six recettes prêtes à
coller livrées dans chaque `style.css` ne couvrent qu'un seul objet, le gras en
encadré de fait — la seule couche intermédiaire du système est aussi la seule à
avoir des recettes. Toute couche introduite doit venir avec les siennes.

---

## 4. Ce que la refonte ne doit pas casser

Contraintes. Elles sortent du relevé de code et priment sur les exigences en cas
de conflit.

**C1 — L'identité octet pour octet de la portion intégrée.** `theme_state()`
exige que la portion intégrée d'un `style.css` soit exactement ce que
l'exécutable régénérerait ; `set-theme` refuse un fichier qui s'en écarte.
Ajouter la moindre variable rend donc **non standard tous les `style.css`
installés par une version antérieure**. Ce coût se paie intégralement chez
l'utilisateur : la suite de tests réinstalle toujours depuis zéro et ne peut pas
le voir. Le message d'erreur actuel — « edited by hand, or written by another
version » — est exact mais ne suggère pas le remède.

*Conséquence :* la refonte doit livrer un chemin de migration et le message qui
l'indique, **avant** d'ajouter la première variable.

**C2 — La substitution réécrit, elle n'ajoute jamais.** `apply_theme()` opère
par réécriture de déclarations existantes. Une variable absente du `:root` garde
silencieusement sa valeur, et le fichier reçoit quand même le marqueur du thème.
Toute variable nouvelle doit donc exister dans le `:root` livré, sans quoi elle
est muette.

**C3 — La substitution est confinée au premier bloc `:root`.** Parce que la
feuille livrée contient plus bas des recettes qui sont littéralement des blocs
`:root` en commentaire, et un second `:root` réel sous media query. Toute
structure nouvelle doit rester compatible avec ce confinement.

**C4 — La palette n'est reconnue qu'en notation hexadécimale.** Le motif de
substitution des six rôles exige `#rrggbb` ; une valeur en `rgb()`, `hsl()`,
`oklch()` ou `var()` n'est ni substituée ni signalée. Le calcul de teinte fait
la même hypothèse et lève sur trois chiffres. Toute valeur dérivée doit ou bien
être résolue en hexadécimal à la génération, ou bien sortir du périmètre
substitué en connaissance de cause.

**C5 — Le contrat de clés d'une entrée de thème est verrouillé par test.** Hors
métadonnées et hors préfixe `fact_`, les clés restantes doivent être exactement
les six rôles. C'est ce verrou qui a tué `--link-decoration-color`. Il devra
être révisé explicitement, pas contourné.

**C6 — Les deux jeux de superpositions doivent garder des clés identiques.**
C'est ce qui permet de substituer l'un pour l'autre sans savoir quelle polarité
on traite.

**C7 — La personnalisation après marqueur reste préservée sans condition.**
C'est la promesse la plus testée et la plus répétée du système. Elle n'est pas
négociable, même quand elle est ce qui rend une surcharge obsolète invisible :
le remède est l'avertissement E7, pas la suppression.

**C8 — L'idempotence des deux chemins d'écriture.** `install --theme X` et
`set-theme X` doivent produire des fichiers identiques octet pour octet, et des
changements de thème répétés ne doivent rien accumuler.

**C9 — Aucune dépendance nouvelle.** L'exécutable reste un fichier Python
autonome. Tout calcul de couleur ou de contraste doit tenir en bibliothèque
standard.

**C10 — Le CSS émis reste lisible tel quel.** C'est un livrable que l'auteur
ouvre et modifie. Une chaîne d'alias qu'il faut remonter sur plusieurs sauts
pour connaître une valeur détruit ce que la refonte cherche à gagner.

**C11 — La structure HTML reste fixe.** Elle n'est pas un template éditable, et
le refactor ne l'ouvre pas.

**C12 — La GUI web n'impose rien.** Elle n'expose que `build` et n'a aucun
couplage aux templates. Aucune synchronisation n'est requise de ce côté. C'est
la seule contrainte du dossier qui soit gratuite.

---

## 5. Ce qu'il faut corriger au passage

Dette avérée, indépendante de l'architecture retenue. Chacune est un fait
constaté, pas une opinion.

**D1 — `.summary` est peint par `--ink`, quatre surfaces disent `--ink-muted`.**
À corriger dans la spec, le README, `--help`, et le commentaire du `style.css`
livré.

**D2 — §9.1 et §9.5.5 se contredisent sur les liens.** §9.1 affirme encore que
le corps de texte n'a aucune règle de lien ; la règle existe depuis le correctif
B3, et §9.5.5 dit l'inverse. C'est la section qui définit le vocabulaire des
rôles qui est périmée.

**D3 — « vingt et une variables » est faux : il y en a vingt-deux substituées,
sur vingt-trois déclarées.** Annoncé dans au moins cinq surfaces. Le chiffre
n'a pas suivi l'ajout de `--link-decoration-color`. **Une refonte qui multiplie
les variables doit dériver ce nombre du code ou renoncer à l'annoncer.**

**D4 — Le bloc de recettes annonce cinq recettes et en contient six.**

**D5 — La galerie est décrite comme française ; elle est en anglais depuis
v0.12.1.** Le point de fond — clé et libellé sont séparés — reste vrai, l'exemple
est mort.

**D6 — Rien ne distingue les neuf palettes empruntées des vingt-quatre
mesurées.** Ni `themes`, ni la galerie. La pastille existante qualifie une
remarque éditoriale, pas une mesure : la note de Dracula signale honnêtement un
emprunt, elle n'informe personne d'un 1,29:1.

**D7 — `--fact-strong-*` compte six variables sur quatre axes**, jamais mis en
table ; l'aide énumère les six d'affilée sans indiquer que `highlight`/`ink` et
`decoration`/`decoration-color` vont par paires.

**D8 — `GLOSSARY.md` ne définit aucun terme de la couche de présentation**, alors
qu'il est érigé en contrat de vocabulaire partagé avec le projet GUI.

---

## 6. Ce que dit l'antériorité

Informatif. Ne préjuge pas de l'architecture, mais borne l'espace des solutions
et écarte deux fausses pistes.

### 6.1 Nous sommes à deux niveaux, pas trois — et c'est la norme

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

### 6.2 Le mécanisme existe et il est éprouvé : le défaut dérivé

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

### 6.3 Le conflit fidélité/accessibilité ne se résout pas — il se refuse

Mesures indépendantes, formule WCAG 2, sur fond clair :

| Couleur | sur blanc | sur `#FDF6E3` |
|---|---|---|
| Dracula vert `#50FA7B` | 1,37 | 1,27 |
| Monokai vert `#A6E22E` | 1,55 | 1,44 |
| Tokyo Night vert `#9ECE6A` | 1,83 | 1,69 |
| Nord 8 `#88C0D0` | 2,00 | 1,85 |
| Gruvbox vert `#B8BB26` | 2,06 | 1,91 |
| **Solarized vert `#859900`** | **3,20** | 2,97 |
| **Solarized bleu `#268BD2`** | **3,68** | 3,41 |

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

### 6.4 Notre trajectoire a déjà été jouée par base16

Seize emplacements à sémantique fixe, remplis par des palettes tierces →
critiques documentées de lisibilité et de rigidité, dont « deux sens distincts
partagent un emplacement, on ne peut pas les séparer » → tentative de refonte
d'un coup (base17) **abandonnée**, les mainteneurs préférant enrichir le format
« itérativement plutôt que d'un coup » → direction retenue (Tinted8) : séparer
la palette de ses usages, et séparer les usages entre eux.

La leçon d'ingénierie n'est pas « faites une couche sémantique ». C'est
**séparez palette et usage, et faites-le par étapes**.

### 6.5 Deux emprunts techniques à retenir

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

### 6.6 Les pièges, nommés pour être écartés

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

### 6.7 Sur la migration

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

## 7. Critères d'acceptation

Vérifiables. Une refonte qui ne les passe pas n'est pas finie.

**A1** — Une série installée avec la version antérieure et rebâtie avec la
nouvelle produit un HTML identique, et un rendu identique sur les 33 thèmes.

**A2** — Il existe une fixture de test portant un `style.css` produit par une
version antérieure, et un test qui vérifie ce que la nouvelle version en fait.
*Cette fixture n'existe pas aujourd'hui et son absence est ce qui rend C1
invisible.*

**A3** — Les trois parcours de friction du §2.3 sont réalisables sans écrire une
seule règle CSS qui court-circuite une règle intégrée : par surcharge d'un
groupe de réglage, après le marqueur, et rien d'autre.

**A4** — Chacun de ces trois parcours survit à `refresh-templates`, à
`set-theme`, et est signalé par `audit` s'il devient caduc.

**A5** — Un test mesure, sur les 33 thèmes, le contraste de chaque couple
texte/fond que la feuille produit, contre les seuils annoncés en §9.5.3.
*Aujourd'hui aucun test ne mesure une valeur de palette.*

**A6** — Le nombre de variables annoncé à l'utilisateur est dérivé du code, et un
test le vérifie.

**A7** — Un thème peut ne fournir que sa palette et rester valide.

**A8** — Aucune chaîne d'alias ne dépasse deux sauts, et un test le vérifie.

**A9** — Les recettes prêtes à coller couvrent au moins les groupes de réglage
nouvellement introduits, et leur nombre annoncé est exact.

**A10** — `GLOSSARY.md` définit template, groupe de réglage, réglage de forme,
rôle, thème, palette et personnalisation.

**A11** — Les huit points de dette du §5 sont corrigés.

---

## 8. Hors périmètre

- La structure HTML des pages (C11).
- Un format de thème utilisateur externe. Aucun n'existe aujourd'hui ; en créer
  un est un sujet distinct, à ne pas fondre dans celui-ci.
- La GUI web (C12).
- Le choix éditorial de B5 entre corriger les palettes empruntées, les basculer
  en fond sombre, ou les déclarer telles quelles. La refonte doit rendre ce
  choix **possible et bon marché** ; elle ne le prend pas.
- Le format d'entrée des articles, à une exception près : les classes de verdict
  et de colonne sont un point de personnalisation documenté, et ce contrat-là
  est engagé.

---

## 9. Décisions à prendre avant l'architecture

**Q1 — Jusqu'où va la couche ?** Les seize sens, ou seulement ceux qui posent
un problème constaté — verdicts, appel de note, anneau de focus, point de nav ?
La leçon de base16 penche pour l'incrémental ; le risque de l'incrémental est de
figer un demi-vocabulaire.

**Q2 — Les groupes de réglage sont-ils thémables ?** Un thème peut-il fournir ses
propres groupes, ou seulement sa palette ? Cela décide si C5 doit être révisé,
et de combien.

**Q3 — Que devient la promesse d'accessibilité des palettes empruntées ?** Trois
issues cohérentes : les corriger, les basculer en fond sombre — ce que §6.3
requalifie en rétablissement de fidélité —, ou les déclarer offertes pour la
fidélité et non pour la mesure. La refonte ne tranche pas, mais la réponse
détermine si A5 doit passer sur 33 thèmes ou sur 24.

**Q4 — Une valeur dérivée est-elle calculée ou écrite ?** Un défaut peut aliaser
un rôle tel quel, ou en dériver par transformation (§6.2, §6.5). La seconde
option résout des cas que la première ne peut pas, au prix d'un calcul de
couleur dans l'exécutable — contraint par C4 et C9, mais tenable.

**Q5 — La rupture est-elle nette ?** La politique maison dit oui. C1 en fixe le
prix : tous les `style.css` installés deviennent non standard. La question n'est
pas *si* on prévient, mais *quand* — avant la première variable ajoutée, ou en
même temps.
