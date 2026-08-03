# Journal de préparation de la 1.0

Fichier de travail versionné — la seule mémoire fiable entre sessions
(les conteneurs de travail sont éphémères). Règles d'usage : toute
décision actée en discussion est reportée ici **avant** d'être
implémentée ; l'état est resynchronisé ici après chaque étape poussée ;
le contenu est présenté régulièrement dans les comptes rendus.

Dernière mise à jour : 2026-08-03 — état du dépôt : v0.8.0 (audit de la
spec, groupes 1 et 2 : resynchronisation de specifications.md + sept
corrections de comportement arbitrées). Releases GitHub : v0.6.0
(comment + gel de la nomenclature), v0.7.0 (images + légendes, axes
1/2/3/9). Règle de processus : chaque message de release livré dans la
conversation EST publié par le propriétaire — le travail qui suit part
donc toujours dans une nouvelle version, jamais replié dans une version
déjà annoncée.

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

### 2.6 Images Markdown natives + légendes (décidé et IMPLÉMENTÉ, v0.7.0)

- `![alt](src)` **seule sur sa ligne** → bloc
  `<figure class="figure"><img></figure>` ; le titre Markdown standard
  `![alt](src "Légende")` → `<figcaption class="figure-caption">`.
- Style par défaut de la légende (décision propriétaire) : **petit,
  centré sous l'image**, gris via `var(--grey)` dans TEMPLATE_STYLE —
  chaque thème des 9 proposés a donc sa déclinaison automatiquement.
- Image **dans un paragraphe** → `<img>` inline, sans légende.
- La `src` peut être un chemin relatif (contrairement aux liens,
  restreints à http(s)) — cas d'usage `articles/img/` → `public/img/`.
- La légende passe par md_inline + typographie ; alt/src échappés.
- Une ligne-image n'est jamais fusionnée au paragraphe précédent
  (démarreur de bloc). Avant : `![alt](src)` rendait un `!` littéral
  suivi du rendu du lien (bug historique, §16 item 20).
- Démo : `articles/img/demo-figure.svg` + figure légendée dans
  `first_article.md` ; le garde anti-écrasement de `demo` couvre le SVG.
- Points 22 (images cliquables) et 23 (taille/justification) : toujours
  NON tranchés, restent en §16 phase 6.
- Légendes de **tableaux** : non planifiées.

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
4. FAIT (post-v0.9.0) — Couverture de test par § de spec : cartographie
   complète par 3 agents (§1-9, §10-16, §17-23), chaque affirmation
   normative croisée avec la suite. 8 trous IMPORTANTS trouvés et TOUS
   comblés (30 tests unitaires + 2 extensions e2e ; suite 283 → 311) :
   compteur de fiches « 01 / NN » (jamais assertté !), listes ordonnées
   `<ol>`, classe `comparison-table`, `--only` par page_source,
   `check --include-drafts` (les deux sens), sémantique de fusion des
   `rules` des packs (`rules: []` tue la typo intégrée / surcharge
   strings-only la garde), « Fiche » désactivée sur series-nav (e2e
   navigateur + URL `#s2` du presse-papiers), contrat de stockage du
   jeton GitLab (sessionStorage toujours, localStorage opt-in seulement,
   avertissement, décoché par défaut — e2e). Plus ~20 mineurs comblés
   (lang attribute, LWP_LANG, ####, lien relatif, entités &, \> et `
   en milieu de ligne, indentation, aide exhaustive, demo sans install,
   contenu démo, exit code 1 de check + hunk de diff, résumé chiffré
   d'audit + brouillons audités, cache nav corrompu, contenu
   .gitlab-ci.yml, page_source vide, draft "TRUE", pas de partage sur
   l'index, chaînes de statut series-nav). Trous restants ASSUMÉS
   (mineurs, listes complètes dans les rapports d'agents de la
   conversation du 2026-08-03) : branches symétriques du §20.3.1 déjà
   couvertes par motif, précision de messages d'erreur, quelques
   interactions navigateur supplémentaires (fallback prompt() sans
   presse-papiers, timing 1600 ms du ✓, PageUp/Home), chunking >100
   fichiers du push GitLab, jeton jamais dans les URL du mock.
   (Note de cohérence, faite avec l'axe 3 : démo enrichie de `date:` +
   `comment:` sur l'article 1, scaffold install avec clés
   `author`/`license` vides, §11.1/§11.2/§12.1 resynchronisés.)
5. FAIT (v0.10.0) — Sécurité, 2e passe post-gel. NB numérotation : les
   deux passes ci-dessous (ciblée puis complète) sont livrées ensemble
   sous la SEULE release v0.10.0 — la release GitHub v0.10.0 n'ayant pas
   été créée entre les deux, le code a été renuméroté de 0.11.0 à 0.10.0
   (séquence GitHub sans trou : v0.9.0 → v0.10.0). 3 agents adverses
   (injection contenu, path traversal/FS, ReDoS/ressources/client-side),
   chaque vrai-positif reproduit par moi-même avant correction. 5 vrais
   positifs corrigés + tests de régression (suite 311 → 319) :
   - XSS stockée via le href d'un lien Markdown (le `"`/`>` de l'URL
     s'évadait de l'attribut → handler injecté) — href désormais échappé
     comme le src d'image (HIGH).
   - Exfiltration de fichiers de l'hôte via un lien symbolique dans
     `articles/img/` (copytree suivait le lien → contenu publié dans
     public/img/) — symlinks échappants refusés (CRITIQUE).
   - Exfiltration via un `article:` lien symbolique (contenu intégré au
     HTML) — containment realpath sur la lecture (HIGH).
   - `article: ..` → traceback IsADirectoryError ; `.`/`..`/octet NUL
     désormais rejetés par le garde de nom (LOW/robustesse).
   - Deux ReDoS quadratiques O(n²) sur entrée adverse : `_HTML_TAG_RE`
     (`<a`×N : 80 Ko → 37,7 s) et la regex de lien (`[`×N : 40 Ko →
     5,1 s) — regex resserrées, désormais < 0,01 s (MEDIUM, surtout pour
     l'exécution navigateur mono-thread).
   Confirmés SÛRS / by-design (non modifiés) : échappement `<meta>`/
   `<title>` (attribut/RCDATA) tient contre `">`/`</title>` ; pieds de
   page author/date/license et card_* en HTML brut = §6.2 assumé ;
   zip-slip des deux extractions (stdlib strippe `..`/`/`) ; jeton
   GitLab en en-tête seulement + redirect='error' ; aucun sink DOM XSS
   (tout en textContent) ; ReDoS des règles de langue = code de
   confiance (§7.2). Modèle de menace et contenances figés dans la spec
   §13.7 (nouveau). Note de processus : un 4e agent (hors de mon
   contrôle) avait auto-appliqué le fix du href ; j'ai remis une base
   propre, reproduit la vuln moi-même, et re-validé le correctif avant
   de le conserver.
   **Passe complète (même release v0.10.0, sur demande « test complet,
   pas juste les deltas »).** 4 agents adverses sur des surfaces distinctes (crypto/
   stockage/SW, converter+parseur re-balayé, JSON/config/placeholders/
   thèmes, réseau/Pyodide/supply-chain). Constat de cadrage : le
   chiffrement (argon2id/AES-GCM/OPFS/SW) N'EXISTE PAS dans ce dépôt — il
   appartient à lightwebpres-gui (hors périmètre 1.0) ; rien à corriger
   ici de ce côté. 8 vrais-positifs corrigés + tests (suite 319 → 331) :
   - ReDoS quadratique du débalisage `<[^>]+>` (×3 : title index, title
     article, meta head) — raté en 1re passe, 200k `<` → 20 s. Borné à
     `<[^<>]+>` (MEDIUM).
   - Confusion de types JSON → tracebacks (spec §20.3/§19.2 promettent
     des erreurs propres) : `page_source`/`page_dest`/champs éditoriaux
     non-string, `series_meta` non-dict et ses feuilles, `rules`/
     `strings` de langue non-string. Validation isinstance ajoutée
     (MEDIUM robustesse).
   - `RecursionError` sur JSON très imbriqué (`[`×100000) — `json.loads`
     élargi à `(ValueError, RecursionError)` (LOW-MED).
   - Substitution de placeholders : mon fix `{{str_KEY}}` du groupe 3
     était incomplet — `{{css}}`/`{{js_nav}}`/`{{cards}}` dans le contenu
     d'auteur restaient substitués, contournant discrètement le garde
     `<title>`/`<meta>`. Passe unique `fill_placeholders` (LOW-MED,
     pas de XSS — validate_html bloque toute charge à balise/guillemet).
   - refresh-templates `rfind` → `find` : le CSS d'auteur entre deux
     marqueurs dupliqués n'est plus perdu (LOW).
   - Chaîne d'appro : Pyodide vendorisé sans hash épinglé + recette
     tirant `latest` → SHA256SUMS ajouté + test d'intégrité + recette
     durcie (épingle la version, vérifie le hash amont) ; §13.8 spec
     (MEDIUM).
   - En-tête `X-Content-Type-Options: nosniff` ajouté au .htaccess ; CSP
     délibérément non posée (scripts inline + wasm/worker Pyodide +
     connect-src GitLab arbitraire → protection nulle, risque de casse ;
     aucun sink DOM XSS trouvé) — décision documentée.
   Re-vérifiés SÛRS (indépendamment, sur code propre) : échappement
     `<meta>`/`<title>` (attribut/RCDATA), href/img/légende, toutes les
     autres regexes du converter (linéaires), validateur d'équilibrage
     (structurel, by-design ; pas de bypass non-équilibré trouvé),
     protection de balises typographie, zip-slip (2 chemins, stdlib),
     jeton en-tête+redirect='error', SSRF baseUrl (by-design, non
     pilotable depuis le contenu), aucun sink DOM XSS, frontière Pyodide
     (runPython jamais sur du contenu de série), thèmes/build-stamp/
     draft-banner. Spec §13.7 étendue (types, placeholders, complexité),
     §13.8 ajoutée (dépendance vendorisée).
6. FAIT (v0.11.0) — Dogfooding de la doc : GUIDE.md et README.md exécutés
   verbatim dans un répertoire vierge. Presque tout conforme (install →
   demo → build → audit → check → refresh-templates, --theme nord, exemple
   article §4/§5, README.md généré). UN vrai défaut : `install --lang en`
   était inerte (variable `lang` morte) → le quick-start README (« install
   --lang en » puis « demo ») produisait une UI française. Correctifs :
   (a) `install --lang` alimente désormais la commande de build du
   `.gitlab-ci.yml` généré (seul endroit où une langue de projet peut
   persister) ; (b) quick-start README corrigé (`--lang en` sur `demo`,
   là où il agit) ; (c) GUIDE §2 + spec §11.1 reformulés (la langue est un
   choix par build, pas une propriété stockée ; « series.json de départ »
   au lieu d'« empty »). Tests ajoutés (gitlab-ci porte --lang, demo --lang
   en = UI anglaise). NB : la v0.11.0 accumule le polish pré-1.0 (axes 6+)
   au-dessus de la v0.10.0 (sécurité, en attente de publication).
7. FAIT (v0.11.0) — Qualité des messages d'erreur : ~55 messages
   [ERROR]/[WARNING] collectés et jugés « à froid » (sans connaître le
   code), un échantillon provoqué en réel. Verdict : très bons dans
   l'ensemble — chacun nomme le fichier/l'entrée, le problème, et souvent
   l'action (« Run first: lightwebpres install X », « pass --force »,
   « renamed to X », liste des thèmes valides, pointeur vers --help).
   UN seul amélioré : « generated HTML is not well-formed » sonnait comme
   un bug interne ; reformulé pour dire que c'est presque toujours du HTML
   brut déséquilibré dans la SOURCE (ex. un <div> jamais fermé dans un
   fact-box), avec l'action à faire. Rien d'autre à corriger.
8. FAIT (v0.11.0) — Accessibilité + validité du HTML généré. Item 14
   (bug signalé par le propriétaire) REPRODUIT ET CORRIGÉ : un `#` dans
   le texte libre d'une fiche SANS `fact-label` devenait un `<h1>` nu à
   taille de cover (clamp 28→52px), plus gros que le `##` de la fiche —
   le cas AVEC fact-label était déjà scopé (`.fact-content`), pas le cas
   sans. Cause : sans étiquette, le corps était ajouté sans wrapper, donc
   le titre de fiche et un titre de corps étaient indistinguables par
   sélecteur. Fix : wrapper `<div class="slide-body">` + CSS
   `.slide-body h1/h2/h3` (1.3/1.15/1.05em, sous la taille du titre) ;
   paragraphe ordinaire inchangé (le div ne porte pas de font-size). Revue
   a11y statique : `<html lang>` ✓, `alt` sur les images ✓, landmarks
   nav/footer/section ✓, aria-label du partage ✓. Un vrai manque corrigé :
   les boutons ronds étaient des `<div>` non focusables (le bouton partage
   n'avait AUCUN accès clavier) → `role="button"` + `tabindex="0"` +
   `aria-label` + `:focus-visible` + activation Entrée/Espace en JS (page
   et index) ; prouvé par un test e2e (focus + Entrée ouvre la pop-up).
   Reste pour l'expérimentation manuelle du propriétaire avant 1.0 :
   contraste réel des 9 thèmes et validation W3C complète (nécessitent un
   navigateur/validateur externe).
9. FAIT (v0.6.0) — Parité i18n + UTF-8 natif : clés fr/en identiques
   (26/26), toute clé référencée présente dans les deux packs, zéro clé
   morte (copy_link_done, définie mais jamais utilisée, désormais câblée
   comme tooltip du retour de copie ✓) — le tout figé par des tests qui
   échoueraient sur toute future divergence. UTF-8 vérifié de bout en
   bout : accents, CJK, emoji, cyrillique, arabe RTL dans tous les
   champs ET dans les noms de fichiers page_source/page_dest (contenu,
   hrefs, liens README, balises meta) — test NativeUtf8EndToEnd.
10. FAIT (v0.11.0) — Contrat avec lightwebpres-gui : formalisé en
    §1.2 (nouveau). Le GUI est un projet séparé qui consomme celui-ci ;
    contrat unidirectionnel : GLOSSARY.md = vocabulaire partagé (« field »,
    casse figée §2.5), specifications.md/SKILL.md = format/rendu identiques
    (même HTML CLI vs GUI, la page navigateur exécute l'exécutable tel
    quel via Pyodide), version **épinglée** et vendorisée côté GUI (jamais
    « au fil de l'eau »), stabilité promise à partir de la 1.0 (§13.9).
    Les fonctionnalités propres au GUI (chiffrement, aperçu, sync Git)
    sont explicitement hors de ce document.
11. PARTIEL (v0.11.0) — Administratif. Politique de versionnage : FAIT,
    §13.9 (nouveau) — semver, ce que promet chaque incrément à partir de
    1.0, le contrat stable = l'ENTRÉE (noms de champs §2.5, series.json,
    format .md, CLI, LWP_*) pas la SORTIE (le HTML peut changer entre
    correctifs → dérive `check` normale), reproductibilité à l'octet pour
    une version donnée mais pas entre versions. **LICENSE du dépôt : EN
    ATTENTE du propriétaire** — décision légale, non prise seul ; le
    README dit « Not yet set ». À trancher avant la 1.0 (options usuelles :
    MIT, Apache-2.0, BSD-3, ou copyleft). Le Pyodide vendorisé reste sous
    sa propre MPL-2.0 (NOTICE.md), indépendamment.
12. Audit de la spec (en cours) : direction C faite. Images : tranchées
    et implémentées (§2.6, v0.7.0). Directions A (spec→code, 19
    constats) et B (code→spec, 33 constats) : consolidation en 3 groupes
    présentée au propriétaire. **Groupe 1 (le code a raison → spec
    corrigée) : FAIT** — §2.4 options+env+aide, §4.1 séparateur, §6.1
    liens http(s)/titres 3 niveaux/tableaux, §6.2 entités &, §6.3 \>
    partout, §6.4 indentation, §8.1 intro sans index.md, §8.3 en-tête
    Articles, §9.2.1 micro-interactions partage, §9.5 renvois §11.7,
    §11.3.1 désignation --only, §11.5 audit (3e avertissement, résumé
    anglais, brouillons inclus), §13.1 BOM/UTF-8, §13.4 stdlib, §18.2-4
    placeholders réels, §19.2 fusion des packs, §23.4 SVG. **Groupes 2
    (7 bugs code) et 3 (7 choix de conception) : EN ATTENTE de
    l'arbitrage du propriétaire** — liste détaillée dans la conversation
    du 2026-08-03. **Groupe 2 : FAIT (v0.8.0), arbitré D1a/D2a/D3a/D4a**
    — page_source manquant fatal en amont (build ET check, zéro sortie
    partielle ; audit signale et continue) ; fichier full-article
    manquant fatal ; demo refuse si series.json liste ≥1 article ;
    parseur CLI strict (table d'options par commande, option
    inconnue/déplacée fatale, forme `--opt=valeur` acceptée, flag
    booléen n'avale plus le positionnel) ; contenu avant lwp:meta fatal
    (lignes vides tolérées) ; éléments décoratifs vides omis
    (highlight-caption, pastille version-tag, article-number,
    series-label). Spec resynchronisée (§2.4, §11.2, §18.2/18.3, §20.3,
    §22.7/22.8), 14 tests ajoutés + 2 réécrits. **Groupe 3 : FAIT
    (v0.9.0) sauf E3, arbitré E1a/E2a/E4b/E5a/E6a/E7a** — E1a `check`
    compare aussi index.html et README.md (résumé « articles + 2 ») ;
    E2a portée « Fiche » du partage décidée par TYPE (classe
    slide-cover), plus par position s1 ; E4b champs de fiche standard
    sur une cover = AVERTISSEMENT, pas erreur (aller-retour
    standard↔cover normal en écriture — noter que du texte libre sur une
    cover reste fatal, §22.12) ; E5a contenu non reconnu dans
    series-nav/full-article = erreur fatale + `comment:` désormais
    reconnu sur TOUT type de fiche (contrat du glossaire complété) ;
    E6a `rules[].flags` réellement implémenté (g global/défaut, i
    insensible casse, autre = fatal) ; E7a chaînes {{str_KEY}}
    appliquées au squelette avant injection — un {{str_KEY}} littéral
    dans le contenu d'auteur reste littéral. Spec : §4.6, §9.2.1, §11.4,
    §18.4, §19.2, §22.9.1, §22.12 ; glossaire (portée comment) ;
    12 tests ajoutés + 2 ajustés. **E3 : tranché E3b (v0.9.0)** — champ
    dupliqué : le dernier gagne, documenté comme sémantique de surcharge
    volontaire (idiome CSS/Make/INI, permet l'assemblage d'un .md par
    concaténation de fragments — cas du propriétaire) ; les titres
    gardent « premier capturé, les suivants tombent dans le contenu »
    (rien n'est perdu, donc pas une incohérence — §4.3, §22.2, SKILL) ;
    figé par tests (fiche + bloc meta). L'audit de spec (item 12) est
    ainsi ENTIÈREMENT CLOS : 52 constats, groupes 1/2/3 tous traités.

### Note vérifiée : rigidité de l'architecture d'une page (2026-08-03)

Question du propriétaire, vérifiée code + test empirique : l'ordre des
fiches est **libre** (le rendu suit l'ordre du fichier, ids s1..sN) ;
**rien n'est obligatoire** hormis le bloc meta et ≥1 fiche (cover
absente ou en dernière position = permis, audit avertit seulement ;
series-nav omissible ; full-article omissible) ; des fiches **après**
le full-article se rendent normalement après lui. Contraintes réelles :
**au plus UN** full-article par page (2 = erreur fatale — mécanique du
placeholder partagé, §22.8) et au plus UN series-nav ; une cover ne
porte pas de texte libre après ses champs. Si « plusieurs longs textes
par page » devient un besoin : levable en rendant le placeholder unique
par fiche — non planifié à ce jour.
13. Juste avant la release 1.0 : supprimer JOURNAL-1.0.md du dépôt.
14. Juste avant la 1.0 — **bug mineur signalé par le propriétaire
    (2026-08-03)** : le rendu d'un `#` dans le texte d'un fait ne
    correspond pas chez lui à la garantie de taille attendue (le `#`
    d'un fait devrait toujours être plus petit que le `##` de la
    fiche ; le CSS `.fact-content h1` 1.3em est censé l'assurer —
    reproduire son cas réel avant de conclure, il a observé autre
    chose). À traiter avec l'axe 8 (rendu/accessibilité) ou en
    dernière passe.

## 4. Notes de processus (demandes explicites du propriétaire)

- **Messages de release : toujours dans la conversation, dans un bloc
  texte copiable.** (Les releases GitHub sont créées par le propriétaire.)
- Pousser régulièrement — ne jamais laisser de travail non commité (les
  conteneurs sont détruits sans prévenir).
- Ce journal est mis à jour à chaque décision et présenté régulièrement
  dans les comptes rendus.
- **À chaque action terminée : toujours dire la suite qu'on devrait
  faire et ce qui reste à faire.**
- **Ce journal est transitoire : il devra être SUPPRIMÉ du dépôt juste
  avant la release 1.0** (décision du propriétaire). Il ne doit donc
  jamais être référencé par la spec ou la doc pérenne.
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
- v0.7.0 : images Markdown natives + légendes (§2.6) ; inclut aussi les
  travaux des axes 1/2/3/9 poussés après le tag v0.6.0 (BOM/UTF-8
  invalide, Python 3.8 + Windows, déterminisme du build, parité i18n +
  UTF-8 natif — chacun figé par tests).
- v0.8.0 : audit de la spec — groupe 1 (specifications.md resynchronisée
  sur le comportement réel, 12 points) + groupe 2 (7 corrections de
  comportement arbitrées D1a/D2a/D3a/D4a : sources manquantes fatales,
  CLI stricte, garde series.json de demo, contenu avant lwp:meta fatal,
  éléments décoratifs vides omis).
