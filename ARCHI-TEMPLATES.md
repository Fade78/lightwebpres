# Architecture du système de rendu d'un thème

**Statut :** architecture retenue, répondant au cahier des charges
`CDC-TEMPLATES.md`. Destinée à être fondue dans `specifications.md` §9.
L'inventaire complet des propriétés suit ce document.

**Date :** 2026-08-04. **Base :** v0.12.2.

---

## 0. Périmètre

Deux sujets se ressemblent et ne sont pas le même.

**Ce document traite du système de rendu :** comment une feuille cohérente se
construit **à partir d'un thème donné**. C'est ce qui se grave dans le code.

**Il ne traite pas de la construction d'un thème cohérent :** comment choisir des
couleurs qui vont ensemble, ce qui fait qu'une palette est réussie, si telle
entrée mérite le catalogue. Savoir éditorial, place distincte. Le mélanger ici
produirait un moteur qui juge ses entrées au lieu de les traiter.

**Hypothèse de travail :** un seul utilisateur, capable de tout régénérer.
L'architecture est conçue pour être juste, pas compatible.

---

## 1. Le principe

**Le vocabulaire d'écriture est une liste de propriétés typées. Le CSS n'est
qu'un format d'émission.**

Personne n'écrit de CSS pour paramétrer, personne ne lit le CSS produit pour
savoir ce qui existe. Trois conséquences, et ce sont elles qui justifient tout le
reste :

**La sortie cesse d'être une interface.** Aujourd'hui `style.css` est à moitié
source, à moitié sortie — d'où l'appareillage de marqueurs, et d'où le gel de sa
forme, puisque des gens l'éditent. Une fois qu'il n'est plus qu'un artefact, sa
structure redevient libre de changer à chaque version : renommer une classe ou
réorganiser les règles n'est plus un changement de contrat.

**Une erreur devient nommée au lieu d'être silencieuse.** Une clé inconnue, une
valeur hors énumération, une unité inconnue : autant d'erreurs localisées à la
génération. Le scénario qui a coûté le plus cher dans le système actuel — une
variable mal choisie qui ne fait rien, sans un mot — devient impossible.

**Il n'y a plus qu'un seul niveau dans ce qui circule.** La superposition existe à
l'écriture, la fusion la résout, et le CSS émis est plat. C'est le modèle
TCP/IP : ce qui peut être résolu à la construction l'est, et seul ce qui dépend
de l'instance reste à résoudre à l'exécution.

### Pas de couche sémantique

Une propriété porte le nom du **composant** qu'elle peint, repris du vocabulaire
que `GLOSSARY.md` fixe déjà pour le format — `tag`, `summary`, `highlight`,
`fact-label`, `source`, les verdicts, la couverture. Ce sont des faits, pas des
jugements : on peut pointer la chose du doigt.

Aucune catégorie intermédiaire n'est inventée. Le seul groupement qui existait
— `--accent` pour l'appel de note, le verdict « partiellement » et l'anneau de
focus — était un accident, pas un besoin : personne n'a jamais voulu que ces
trois-là bougent ensemble. La coordination ne disparaît pas pour autant, elle se
loge dans le **défaut**, qui pointe vers une valeur partagée du thème.

Le piège du jeton par occurrence (`footnote-marker-hover-color`) est écarté par
une raison solide : la liste des composants est close et déjà spécifiée ailleurs.
« Survol du verdict partiel » n'est pas un objet du format.

---

## 2. La chaîne de résolution

```
   défauts intégrés  →  thème  →  settings de la série  →  propriétés d'article
        └─────────── fusion, résolution des renvois, typage ───────────┘
                                   ↓
                        CSS composé en mémoire, par page
                                   ↓
                      inliné dans la page ({{css}})   +   custom.css
                                   ↓
                    variantes de composant, balises locales  →  cascade
```

**La chaîne n'est pas homogène, et la couture doit être vue.**

Les quatre premiers niveaux se résolvent **avant l'émission**. Le moteur fusionne
des dictionnaires : rien à arbitrer, pas d'ordre de règles, pas de spécificité.
Le CSS est composé par page — le moteur le fait déjà, puisque la feuille est
inlinée dans chaque page via `{{css}}` — donc la personnalisation par article ne
coûte rien de plus qu'un jeu de propriétés différent pour cette page.

Les deux derniers ne **peuvent pas** fonctionner ainsi : ils visent une instance,
pas une page. Deux encadrés dans le même article doivent pouvoir différer. Ils
passent donc par des sélecteurs, donc par la cascade.

La couture est là, entre « par page » et « par instance ».

**Rien n'a besoin d'atteindre le disque.** Le CSS peut n'exister qu'en mémoire, et
il reste intégralement consultable : il est inliné dans chaque page, il suffit
d'en afficher la source.

---

## 3. Les trois fichiers, un propriétaire chacun

| Fichier | Propriétaire | Écrit par le système |
|---|---|---|
| feuille émise | le système | régénérée à volonté, éventuellement jamais sur disque |
| `templates/settings.conf` | l'auteur | **jamais**, sauf demande explicite |
| `templates/custom.css` | l'auteur | **jamais** |

**C'est ce partage qui supprime l'appareillage.** Le marqueur de personnalisation,
son variant hérité, la recherche de sa première occurrence, la vérification
d'identité octet pour octet, le `--force` de `set-theme`, le `[SKIP]` sans
marqueur, la ligne vide qui s'accumulait : une dizaine de mécanismes dont l'unique
raison d'être est que le système écrit dans le fichier que l'auteur édite. La
bonne façon de ne pas détruire le travail de quelqu'un n'est pas de le détecter,
c'est de ne pas écrire là où il est.

### Le scaffold

`settings` est généré **une fois**, avec toutes les propriétés en commentaire à
la valeur du thème choisi. L'auteur décommente ce qu'il veut épingler.

Il règle trois problèmes d'un coup : la découvrabilité — la surface complète est
sous les yeux, sans documentation ; la mise à jour — une régénération demandée
montre les propriétés apparues et disparues comme un diff ; et la dérive de la
documentation, celle qui fait qu'on annonce vingt et une variables quand il y en a
vingt-deux.

Deux conditions, sans quoi il s'inverse. **Il est généré depuis la structure qui
émet le CSS**, jamais tenu à la main — sinon il devient une seconde source de
vérité. Et **il n'est jamais réécrit d'initiative** : ses commentaires vieillissent
quand le thème change, et le remède est de le **signaler**, pas de l'écraser.
`audit` compare et dit : ces propriétés sont apparues, celle-ci n'existe plus, ces
commentaires portent les valeurs de `dracula` alors que la série est sur `nord`.

### Ce que ça débloque

Les surcharges cessent d'être du CSS opaque pour devenir des données. Le pire
scénario du système actuel — un auteur corrige deux couleurs pour un thème, en
change plus tard, et ses valeurs calibrées pour l'autre palette restent en place
sans un mot — conserve sa sémantique voulue, mais devient **visible**. Le système
sait quelles clés sont épinglées et depuis quel thème. Il ne les touche pas ; il
peut le dire.

---

## 4. Le vocabulaire

Une propriété s'écrit `composant.axe: valeur`, dans l'idiome `clé: valeur` que le
format d'article emploie déjà. Un renvoi vers une valeur partagée est un mot, pas
une fonction : `cover.fg: ink`. Il est résolu à la fusion et ne survit pas dans la
sortie.

### Les six types

| Type | Exemple | Vérifié |
|---|---|---|
| couleur | `#E8A33DFF` | forme, alpha |
| longueur | `4px`, `1.5rem`, `clamp(1rem, 2vw, 1.375rem)` | unité connue |
| angle | `200deg` | unité connue |
| pile de polices | `…, serif` | **se termine par un générique** (§6) |
| énumération | `bold`, `italic`, `uppercase` | valeur admise |
| texte | `"\25D0"` | libre |

### La règle de complétude

> **Une propriété non exposée est une décision confisquée au thème.**

C'est le critère de qualité du système, et il se vérifie par énumération plutôt
que par argument. Il a un coût assumé : des tailles aujourd'hui figées dans les
règles deviennent des propriétés, et la surface s'élargit à une vingtaine de
composants sur une dizaine d'axes. Une liste longue reste lisible là où une
hiérarchie profonde ne l'est plus.

Sa contrepartie est la **rigidité** : l'auteur ne peut exprimer que ce que le
vocabulaire admet. Elle est bornée par `custom.css`, qui est du CSS complet et
sans sous-ensemble. La rigidité n'est jamais un mur, seulement un aiguillage —
soit c'est un réglage et il est typé, soit c'est une règle et elle est libre.

---

## 5. Couleurs et dégradés

Toute couleur est un **ARGB**. Les neuf voiles translucides cessent d'être d'une
autre nature que les couleurs : un seul type de valeur, une seule notation.

Un fond se paramètre en trois axes — `bg.from`, `bg.to`, `bg.angle` — et **un
aplat est un dégradé dont les deux bornes sont égales**. Pas de branche, pas de
cas particulier, et les thèmes actuels restent des aplats sans rien changer.

Deux réserves. Un dégradé est une `background-image`, donc `print-color-adjust:
exact` est nécessaire à l'impression — le code le fait déjà pour la colonne mise
en avant. Et un dégradé **sur du texte** exigerait `background-clip: text` : hors
périmètre, les dégradés sont réservés aux fonds.

---

## 6. Typographie

*(Section à compléter par la décision en cours — voir §6.4.)*

### 6.1 Ce qui est garanti

**Aucune police nommée n'est garantie.** Les « web-safe fonts » sont un héritage
Windows/macOS : Arial et Times New Roman sont absents d'un Linux de base et de la
plupart des Android. Nommer une police, c'est formuler un vœu.

Le seul plancher réel est celui des génériques, que le moteur **doit** résoudre
vers une police réelle : `serif`, `sans-serif`, `monospace`, `cursive`, `fantasy`
(CSS 2.1). `system-ui` est largement supporté ; `ui-serif`, `ui-sans-serif`,
`ui-monospace`, `ui-rounded` sont **propres à Safari** — utiles en tête de pile,
jamais en ancre.

La garantie porte sur l'**existence**, pas sur l'**identité** : métriques,
chasses et graisses disponibles varient, et l'utilisateur peut changer la
résolution dans son navigateur.

### 6.2 Deux conséquences structurelles

**Les graisses intermédiaires ne survivent pas.** Sur une famille à deux graisses
— cas courant d'un générique —, l'algorithme d'appariement CSS rend 400 pour 500,
et 700 pour 600 comme pour 700. Les trois graisses qui distinguent aujourd'hui les
verdicts s'effondrent en deux, et « partiellement » redevient indistinguable de
« oui ». **Seules `normal` et `bold` sont fiables**, parce que ce sont les seules
que CSS garantit de produire, au besoin par synthèse. Même chose pour `italic`.

Ce qui justifie après coup la marque de forme des verdicts bien mieux que
l'argument d'accessibilité qui l'avait motivée.

**Le piège de taille du monospace ne peut plus mordre.** `font-family: monospace`
déclenche une taille par défaut différente dans les moteurs. Comme la règle de
complétude impose une taille explicite à chaque composant portant du texte, le
défaut n'est jamais consulté. Le contournement historique (`monospace, monospace`)
devient inutile.

### 6.3 Ce qui en découle

Une pile doit **se terminer par un générique CSS 2.1**. Règle vérifiable en une
ligne, qui n'interdit rien : tout ce qui précède le générique est une chance, le
générique est la promesse.

Aucune police n'est embarquée par l'exécutable — ce serait 300 Ko de binaire dans
un fichier unique. Mais l'auteur peut le faire lui-même : un `@font-face` dans
`custom.css`, la famille nommée en tête de pile dans `settings`. Le moteur n'a
rien à en savoir. C'est une raison de plus de garder `custom.css`.

### 6.4 Décisions prises

**Quatre piles partagées** — `font.text`, `font.display`, `font.ui`,
`font.mono`. Les trois premières passent le test « plusieurs composants en
dépendent » ; la quatrième a une justification différente et nommée comme
telle : c'est une valeur de bibliothèque, la seule pile monospace correcte,
écrite une fois. `display` reprend une distinction que le HTML émis fait déjà
(`slide_title` rend `<h1>`/`<h2>`) : on ne fabrique pas de catégorie, on laisse
une balise existante porter sa typographie.

**Les thèmes touchent aux polices.** Un thème « Terminal » en chasse fixe est
trois lignes (`font.text/display/ui: mono`). Les 33 entrées du catalogue sont à
revoir sous cet angle — travail de construction de thèmes, hors de ce document.

**Deux graisses, `normal` et `bold`**, vérifiées par type, avec le motif dans le
message d'erreur.

**Ancrage souple** : toute pile finit sur un générique CSS 2.1, sans exiger que
`font.mono` finisse sur `monospace`. Le catalogue publié, lui, est tenu plus
strictement — c'est la répartition habituelle entre le moteur et ses entrées.

**Défauts livrés : l'aspect actuel.** Le vrai parti typographique appartient à
la révision du catalogue.

---

## 7. Variantes et balises locales

**Variantes de composant.** Un auteur qui veut un encadré différent **désigne une
variante**, il ne fixe pas des valeurs : `fact-variant: warning` dans la source,
`fact.warning.*` dans les propriétés. La source porte du sens (« ceci est un
avertissement »), pas une décision visuelle (« ceci est rouge »), donc un
changement de thème l'emporte avec lui. Le projet a déjà ce précédent assumé :
`class="yes"` sur une cellule est décrit comme un point de personnalisation
documenté.

**Balises locales.** Gras, italique, non proportionnel, petites capitales,
souligné : autorisés librement — ils ne composent avec rien, ne dépendent d'aucun
thème, et ne peuvent pas produire un résultat illisible.

**Les littéraux dans le texte sont admis, par balise du format.** La position
antérieure — variantes seulement — visait le bon danger au mauvais endroit : le
risque n'était pas le littéral, c'était l'invisibilité d'une intervention
écrite en CSS libre que rien ne lit. Une balise **définie par le format** passe
par le compilateur, donc trois garanties s'appliquent d'elles-mêmes :

- **les mêmes types partout** — une couleur y est un ARGB valide, une pile de
  polices y finit sur un générique, sinon erreur nommée à la génération ;
- **`audit` les énumère** — « fiche 4 : couleur littérale, fiche 7 : police » —
  informatif, jamais bloquant : l'auteur qui change de thème sait où regarder ;
- **la variante reste le geste recommandé** pour ce qui se répète ; le littéral
  est l'outil de l'intervention ponctuelle d'un auteur qui sait ce qu'il fait.

La balise locale est ainsi la **cinquième couche de la cascade** — portée
instance au lieu de portée page — avec le même vocabulaire et les mêmes types
que les quatre autres.

---

## 8. Les garanties

**G1 — Aucune règle émise ne lit une valeur partagée du thème directement.** Les
règles ne lisent que des propriétés de composant. Un seul saut jusqu'à une valeur.

**G2 — Toute propriété est typée, et son type est vérifié à la génération.**

**G3 — Toute pile de polices se termine par un générique CSS 2.1.**

**G4 — Toute énumération de graisse est `normal` ou `bold`.**

**G5 — Tout composant portant du texte déclare une taille explicite.**

**G6 — Le nombre de propriétés annoncé est dérivé du code**, jamais écrit à la
main. La dérive du décompte actuel ne peut plus se reproduire.

**G7 — La liste des propriétés couvre tout ce que les règles émises consomment.**
La règle de complétude, vérifiée par balayage plutôt que par revue.

---

## 9. Migration

Rupture nette, sans alias. `refresh-templates` régénère.

Conservé de la politique maison parce que gratuit : `audit` reçoit la table des
noms retirés et nomme le remplaçant. L'avertissement est d'autant plus utile
qu'un ancien nom se scinde en plusieurs remplaçants selon l'emploi — c'est
précisément le cas où un alias serait faux et où un message est juste.

---

## 10. Ce que cette architecture ne fait pas

- **Elle ne juge aucun thème.** Critères d'admission, fidélité d'une palette
  empruntée, choix de basculer telle entrée en fond sombre : questions réelles,
  aucune n'est ici.
- **Elle n'arbitre rien de ce que l'auteur écrit.** Aucun seuil ne s'applique à
  ses valeurs, et `audit` informe sans jamais refuser.
- **Elle ne calcule aucune couleur.** Résoudre une clarté pour rendre une teinte
  lisible est de l'ingénierie de thème, pas du rendu.
- **Elle n'ouvre pas la structure HTML** ni le format d'entrée, hors les variantes
  de §7.
- **Elle ne crée pas de format de thème externe** — mais un thème *étant* un
  fichier de propriétés, plus rien n'est à construire pour l'ouvrir un jour.
- **Elle ne garantit pas la séparabilité en vision dichromate.** La marque de
  forme la sert déjà ; aucune simulation n'est prévue. Manque assumé.
