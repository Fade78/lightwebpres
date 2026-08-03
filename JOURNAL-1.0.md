# Journal de préparation de la 1.0

Fichier de travail versionné — la seule mémoire fiable entre sessions
(les conteneurs de travail sont éphémères). Règles d'usage : toute
décision actée en discussion est reportée ici **avant** d'être
implémentée ; l'état est resynchronisé ici après chaque étape poussée ;
le contenu est présenté régulièrement dans les comptes rendus.

Dernière mise à jour : 2026-08-03 — état du dépôt : v0.6.0 (champ
`comment` + gel de la nomenclature §2, implémenté en une passe : code,
tests, spec, glossaire, README, GUIDE, SKILL). La release GitHub v0.6.0
couvre tout depuis v0.5.1.

## 1. Cadrage produit (décidé)

- **Le produit est généraliste.** Il est né d'un besoin précis (séries de
  fiches sourcées pour adolescents) mais ne s'y cantonne pas : il n'y a
  **pas de public lecteur cible**. Il y a des utilisateurs qui consultent
  le contenu sur mobile ou ordinateur. Le logiciel permet de faire des
  slides de différents types et, éventuellement, d'y adjoindre un long
  texte — qui n'est pas forcément un article sourcé.
- Conséquence : **réécrire §1 de specifications.md** dans ce sens (FAIT, v0.6.0)
  (supprimer « public adolescent », reformuler « article de fond » comme
  cas particulier de « texte long optionnel »).

## 2. Gel de la nomenclature (décisions actées — IMPLÉMENTÉ en v0.6.0)

### 2.1 Renommage `source`/`file` → `page_source`/`page_dest`

- Le champ de fiche `source` (citation académique) **ne change pas** :
  « source » est le mot standard, et la fiche ne « cite » pas forcément —
  `citation` a été examiné et rejeté.
- Au niveau article : `source` → **`page_source`**, `file` →
  **`page_dest`** (« target » rejeté : la cible est ce qu'on vise, pas ce
  qu'on produit ; « file » n'a jamais plu). La famille `page_*` devient
  complète : `page_source`, `page_dest`, `page_title`, `page_desc`.
- `page_source` reste structurel : `series.json` uniquement, obligatoire
  (un fichier ne déclare pas son propre nom — œuf et poule).
- `page_dest` garde la cascade de `file` : `series.json` > meta
  `page_dest:` > déduit de `page_source` (`.md` → `.html`).
- Le homonyme `source` disparaît ainsi complètement du format.
- **Migration** : une seule série existante ; son propriétaire la rendra
  compatible lui-même (via agent). Implémenté : les anciens noms
  `source`/`file` dans series.json produisent une erreur fatale explicite
  (« renommé en X à la v1.0 »), détectée avant toute autre validation.

### 2.2 Nouveaux champs éditoriaux : `author`, `license`, `date`

- **Nouveau motif de cascade** (à documenter comme tel) : article →
  série. `series.json` (entrée d'article) > bloc meta de l'article >
  **défaut de `series_meta`** (pour `author` et `license` ; `date` est
  par article seulement, sans défaut de série).
- **Affichés dans l'export** (pas seulement gardés en source) :
  - `author` : signature discrète sur la page de l'article (pied de
    page) + `<meta name="author">` ; absent = rien.
  - `license` : mention en pied de **chaque** page générée (articles +
    index), texte libre, HTML brut autorisé pour un lien (§6.2) ;
    absent = rien.
  - `date` : affichée près de la signature ; **texte libre affiché tel
    quel** — jamais de date automatique depuis le mtime (casserait la
    reproductibilité sur laquelle `check` repose).

### 2.3 `page_desc` — branche parallèle, PAS chaînée

- `page_desc` : `series.json` > meta > summary de la cover > **balise
  omise**. Alimente `<meta name="description">`.
- `card_desc` **inchangé** : `series.json` > meta > summary de la cover.
- **Interdit de chaîner `card_desc` ← `page_desc`** : `page_desc` est une
  métadonnée invisible (SEO/partage), `card_desc` de l'UI visible — un
  `page_desc` optimisé référencement fuiterait dans les cartes d'index.
  L'asymétrie avec la chaîne des titres (`page_title` → `card_title` →
  `nav_title`, qui elle se chaîne) est **intentionnelle** et doit être
  documentée comme telle dans §20.3.1, sinon quelqu'un la « corrigera ».
- `audit` : avertissement quand un article n'a aucune description nulle
  part (balise omise) — avertir plutôt que substituer.

### 2.4 `draft` et `--include-drafts`

- `draft: true` (insensible à la casse ; toute autre valeur = pas
  brouillon), posable dans l'entrée `series.json` ou le bloc meta —
  `series.json` prioritaire.
- Par défaut : article draft **entièrement exclu** du build (pas de
  page, pas de carte d'index, pas d'entrée dans les navs des autres).
- `--include-drafts` (build **et** check) : construit tout — pour les
  auteurs et l'aperçu du GUI.
- Avec `--include-drafts`, **bandeau « brouillon » affiché au centre de
  l'en-tête de page, entre l'éventuel build stamp et le numéro de
  fiche** — un aperçu ne doit jamais être confondu avec une publication.

### 2.5 Convention de casse (à énoncer dans GLOSSARY.md)

- Champs de fiche : kebab-case (`fact-label`, `highlight-caption`).
- Champs article/série : snake_case (`page_title`, `nav_desc`).
- Règle à figer pour tout futur champ.

## 3. Revue 1.0 — axes restants (après le gel)

Ordre : le gel (§2 ci-dessus) d'abord, tout le reste en dépend.

1. FAIT (v0.6.0) — Robustesse des entrées dégénérées : BOM UTF-8 accepté
   partout (utf-8-sig via un helper read_text_file unique ; un BOM dans un
   full-article fuyait un U+FEFF dans le HTML publié et cassait son
   premier titre), CRLF déjà sain (universal newlines de Python, testé),
   fichier vide → erreur propre §22.7, UTF-8 invalide → erreur propre au
   lieu d'une traceback, série vide → index vide. Reste ouvert : très
   gros fichiers/séries (perf), reporté avec l'axe 3.
2. FAIT (v0.6.0) — Portabilité : minimum Python 3.8 déclaré (§2.1,
   README, --help) et vérifié à l'import avec message clair (le source
   parse jusqu'à 3.6, pin par test ast feature_version) ; suite verte
   sous 3.10/3.11/3.13 ; liens du README générés en as_posix (relpath
   donnait des antislashs sous Windows = liens Markdown cassés) ;
   collision de page_dest insensible à la casse désormais fatale
   (écrasement silencieux sinon sur FS Windows/macOS) ; Pyodide
   (emscripten, POSIX) sans point notable.
3. FAIT (v0.6.0) — Reproductibilité : audit du code (datetime.now()
   uniquement dans build_stamp_html ; pas de random/locale/énumération de
   répertoire dans le chemin de build) + preuve empirique (300 articles,
   deux builds byte-identiques sur tous les fichiers) + test de
   régression BuildDeterminism. Perf au passage : 300 articles avec
   series-nav de 300 entrées chacun → 6,4 s, ~39 Mo (dominé par le
   CSS/JS inline par page, par conception).
4. Couverture de test par § de spec : croiser chaque § avec la suite,
   lister les trous.
   (Note de cohérence, faite avec l'axe 3 : démo enrichie de `date:` +
   `comment:` sur l'article 1, scaffold install avec clés
   `author`/`license` vides, §11.1/§11.2/§12.1 resynchronisés.)
5. Sécurité (2e passe post-gel) : injection via sources, XSS, path
   traversal, ReDoS fichiers de langue.
6. Dogfooding de la doc : exécuter GUIDE.md et README.md verbatim dans
   un répertoire vierge.
7. Qualité des messages d'erreur : provoquer chaque erreur fatale, juger
   le message sans connaître le code.
8. Accessibilité + validité du HTML généré : sémantique, ARIA, contraste
   des 9 thèmes, validation W3C.
9. FAIT (v0.6.0) — Parité i18n + UTF-8 natif : clés fr/en identiques
   (26/26), toute clé référencée présente dans les deux packs, zéro clé
   morte (copy_link_done, définie mais jamais utilisée, désormais câblée
   comme tooltip du retour de copie ✓) — le tout figé par des tests qui
   échoueraient sur toute future divergence. UTF-8 vérifié de bout en
   bout : accents, CJK, emoji, cyrillique, arabe RTL dans tous les
   champs ET dans les noms de fichiers page_source/page_dest (contenu,
   hrefs, liens README, balises meta) — test NativeUtf8EndToEnd.
10. Contrat avec lightwebpres-gui : convention partagée (glossaire,
    version vendorisée) à énoncer formellement.
11. Administratif : LICENSE du dépôt, politique de versionnage post-1.0
    (que promet-on exactement à partir de 1.0 ?).

## 4. Notes de processus (demandes explicites du propriétaire)

- **Messages de release : toujours dans la conversation, dans un bloc
  texte copiable.** (Les releases GitHub sont créées par le propriétaire.)
- Pousser régulièrement — ne jamais laisser de travail non commité (les
  conteneurs sont détruits sans prévenir).
- Ce journal est mis à jour à chaque décision et présenté régulièrement
  dans les comptes rendus.
- **À chaque action terminée : toujours dire la suite qu'on devrait
  faire et ce qui reste à faire.**
- Le glossaire (GLOSSARY.md) est en anglais ; specifications.md en
  français.
- Versionnage observé : fonctionnalité = bump mineur, correctif = patch,
  toutes les releases GitHub en prerelease jusqu'à la 1.0.

## 5. Historique récent (contexte)

- v0.5.0 : articles auto-décrits (`series.json` ne requiert que la
  source), cascade `file`/`page_title`, split `card_*`/`nav_*`,
  suppression de la syntaxe champ `h1:`/`h2:` (concept unifié
  `slide_title`), fact-box acceptant titres/listes, GLOSSARY.md créé.
- v0.5.1 : fix — `build_series_nav()` n'appliquait aucune typographie
  (nav_title/nav_desc/card_label).
- v0.6.0 (couvre tout depuis la release GitHub v0.5.1) : champ `comment`
  (note de relecture, reconnu partout, jamais rendu ni publié) + gel de
  la nomenclature (§2) — `page_source`/`page_dest`,
  `author`/`license`/`date` affichés, `page_desc` + `<meta>` tags,
  `draft`/`--include-drafts` + bandeau, erreurs de migration, §1
  généraliste, convention de casse au glossaire.
