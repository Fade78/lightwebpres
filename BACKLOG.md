# Backlog

Registre **pérenne** des points signalés mais non traités : bugs sans
urgence, demandes d'évolution, décisions de format à trancher. Contrairement
à `JOURNAL-1.0.md` (mémoire de travail de la 1.0, supprimée à la sortie),
ce fichier survit aux releases — c'est ici que va tout ce qui doit être
retrouvé « plus tard », pas dans le journal.

Chaque entrée dit ce qui a été **vérifié** et ce qui reste à **décider**.

---

## B1 — Image en milieu de paragraphe avec titre : reste en Markdown littéral

**Type :** bug d'implémentation (le comportement attendu est déjà spécifié).
**Signalé sur :** v0.11.0, dans un article de fond (`_article.md`).
**Impact constaté :** nul chez le rapporteur, aucun article n'utilise ce cas.
**Statut :** reproduit et cause confirmée ; correction non faite.

### Les quatre cas

| Cas | Forme | Attendu | Réel |
|---|---|---|---|
| A | seule sur sa ligne, sans titre | `<figure>` | OK |
| B | seule sur sa ligne, avec titre | `<figure>` + `<figcaption>` | OK |
| C | milieu de paragraphe, sans titre | `<img>` inline | OK |
| D | milieu de paragraphe, **avec titre** | `<img>` inline, titre ignoré | **texte littéral** |

### Cause, vérifiée

Deux motifs distincts lisent la même syntaxe, et un seul accepte le titre
optionnel :

- `_FIGURE_LINE_RE` (image seule sur sa ligne) —
  `^!\[([^\]]*)\]\(\s*([^)\s"]+)(?:\s+"([^"]*)")?\s*\)$` : le groupe
  `(?:\s+"([^"]*)")?` lit le titre.
- le motif inline dans `md_inline()` —
  `!\[([^\]]*)\]\(([^)\s"]+)\)` : **pas** de groupe de titre, et
  `[^)\s"]+` s'arrête au premier espace. Une image à titre ne matche donc
  rien du tout et traverse la conversion intacte.

Reproduction directe (v0.11.0, `md_inline()` seule) :

```
'texte ![alt](img/x.jpg) texte'
  -> 'texte <img src="img/x.jpg" alt="alt"> texte'
'texte ![alt](img/x.jpg "Legende") texte'
  -> 'texte ![alt](img/x.jpg "Legende") texte'      <- inchangé
```

**Symptôme secondaire, confirmé lui aussi** : le texte resté littéral
traverse ensuite le moteur typographique, qui voit le `!` de `![alt]`
comme une ponctuation haute et insère une insécable devant. La sortie
contient donc `texte\xa0![alt](...)` — une insécable au milieu d'un motif
Markdown non converti. C'est un bon marqueur pour repérer le cas dans une
page déjà publiée.

### Ce qui est déjà tranché

`specifications.md` §6.1 dit : « Une image **au milieu d'un paragraphe**
devient un simple `<img>` inline, sans légende. » Le comportement attendu
n'est donc pas à décider — le titre doit être **lu puis ignoré**, pas
laisser le Markdown brut. Le skill dit la même chose. Il ne reste qu'à
aligner l'implémentation.

### Piste de correction

Donner au motif inline le même groupe de titre optionnel qu'à
`_FIGURE_LINE_RE`, et le jeter côté rendu. Attention à ne pas casser
l'échappement d'attribut déjà en place sur `src`/`alt` (la `src` est un
contexte d'attribut, cf. le commentaire voisin dans `md_inline`), ni la
borne anti-ReDoS (`[^<>]`, jamais `.*`). À couvrir par un test des quatre
cas A/B/C/D d'un coup — le trou vient précisément de ce que A/B et C
étaient testés séparément.

---

## B2 — Exprimer un verdict visuel dans une cellule de tableau

**Type :** demande d'évolution du format + décision à prendre.
**Statut :** rien de décidé. La question posée est explicitement « est-ce
un manque ou un choix ? » — donc à trancher, pas à implémenter d'office.

### Le besoin

Un comparatif de trois plateformes sur sept critères, où chaque cellule
porte une classe qui la colore selon le verdict : `yes` / `no` /
`partial`. Trente attributs de classe. Le Markdown ne sait pas
l'exprimer, donc ce tableau-là reste écrit en HTML brut à la main, alors
que les autres tableaux de la même fiche sont passés au Markdown natif
(`class="comparison-table"`, §6.1) dès qu'il a été disponible.

L'argument, qui porte : dans un format conçu pour des articles à fiches
lus en diagonale, « fait / ne fait pas / partiellement » se saisit d'un
coup d'œil quand c'est coloré et devient un mur de texte sinon. Le cas
paraît récurrent, pas propre à un projet.

Cas voisin signalé pour information (même famille, pas la même demande) :
deux autres tableaux restent en HTML brut pour une classe `col-signal`
qui met en valeur une **colonne** entière.

### Options, avec leurs conséquences

1. **Convention sur le contenu** — une cellule ne contenant que « oui » /
   « non » / un symbole reçoit automatiquement sa classe.
   *Contre, sérieux :* dépend de la langue, alors que le format est
   i18n (packs `fr`/`en`, §17) ; et surtout **change rétroactivement le
   sens du contenu existant** — un tableau déjà publié dont une cellule
   dit « non » se met soudain à rougir. Difficilement compatible avec la
   stabilité du contrat d'entrée promise à partir de la 1.0 (§13.9).
2. **Marqueur explicite en tête de cellule** (forme à définir, p. ex.
   `| +oui |`, `| -non |`, `| ~partiel |`).
   *Pour :* explicite, indépendant de la langue, local à la cellule,
   n'altère aucun contenu existant. *Contre :* une syntaxe de plus à
   geler — donc un ajout au contrat d'entrée, c'est-à-dire une **version
   mineure post-1.0** (§13.9), jamais un correctif.
3. **Documenter que le HTML brut est la voie prévue** pour ce cas.
   *Pour :* zéro changement de format, ça marche déjà — §6.2 autorise
   explicitement le HTML inline. *Contre :* verbeux (trente attributs à
   la main), et laisse le besoin non couvert par le format lui-même.

Le rapporteur précise que l'option 3 lui conviendrait aussi : ce qui
compte est de **savoir**, pas d'obtenir la fonctionnalité.

### Recommandation (à valider)

Écarter l'option 1 : la rétro-action sur du contenu déjà écrit est
rédhibitoire pour un format qui promet la stabilité de ses entrées.
Entre 2 et 3, trancher explicitement puis l'écrire dans
`specifications.md` §6.1 — y compris si c'est 3, parce que « le HTML brut
est la voie prévue » n'est un choix que si c'est écrit quelque part. Si
c'est 2, prévoir en même temps le cas colonne (`col-signal`) plutôt que
d'y revenir séparément.

Dans tous les cas : **post-1.0**. Ce n'est pas un blocage de sortie.
