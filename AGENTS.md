# AGENTS.md — Guide pour agents (humains, IA, LLM) travaillant sur ce dépôt

Document normatif du dépôt (`specifications.md` §1.1) : il oblige qui
modifie ce dépôt. Il ne dit rien du format lui-même.

À ne pas confondre avec `agent/skills/lightwebpres/SKILL.md`, qui décrit
le **format** à qui écrit un article. Les deux s'adressent à un agent et
ne parlent pas du même métier : ici, comment travailler **sur** l'outil ;
là-bas, ce que l'outil **accepte**.

## Commandes essentielles

### Tests (obligatoire avant et après chaque changement)
```bash
python3 tests/run_tests.py                              # obligatoire : parallèle, CPUs disponibles - 2
python3 tests/run_tests.py --workers 4                  # override explicite
python3 -m unittest tests.test_lightwebpres              # diagnostic séquentiel : fichier principal seul
python3 -m unittest tests.test_lightwebpres -v          # diagnostic verbeux séquentiel
```

### Vérification compilation
```bash
python3 -m py_compile lightwebpres                    # silencieux = OK
```

### Lancer l'outil
```bash
python3 lightwebpres --help                           # aide : registre live + texte de référence maintenu à la main
python3 lightwebpres <command> [dir] [options]        # usage général
eval "$(python3 lightwebpres completion --shell bash)" # completion tab (optionnel)
```

## Structure du dépôt

### Code et tests
- `lightwebpres` — le code, un seul fichier Python. Pas de dépendances
  externes (stdlib uniquement, Python 3.8+).
- `tests/test_lightwebpres.py` — la suite principale ;
  `tests/run_tests.py` en découvre davantage, dont les volets navigateur.
  Deux registres y cohabitent, voir Conventions : `run(*args)` lance
  l'exécutable en sous-processus, `load_lightwebpres_module()` importe le
  module pour mesurer ce qu'une sortie ne montre pas.
  Les comptes ne sont pas écrits ici : ils changent à chaque lot et un
  nombre faux dans un guide de travail est pire que pas de nombre. Pour
  l'avoir, lancer la suite.

### Documentation permanente (fait foi)
- `specifications.md` — spécification normative du format (référence).
- `GLOSSARY.md` — contrat de vocabulaire partagé (avec `lightwebpres-gui`).
- `README.md`, `GUIDE.md` — documentation utilisateur.
- `BACKLOG.md` — registre pérenne des dettes et décisions différées.
- `CHANGELOG.md` — ce qui a changé d'une version à l'autre, dans les
  mots de l'annonce. L'entrée **est** le corps de la release GitHub.
- `agent/skills/` — les skills (format LWP, méthode éditoriale) + index.
- `AGENTS.md` — ce document.
- `THIRD-PARTY-NOTICES.md` — licences de ce qui est embarqué.

### Relevés datés (consultables, non normatifs)
- `docs/AUDIT-*.md` — les audits, avec leurs mesures et leurs conditions.
  Les nombres qu'ils portent disent l'état du jour de la mesure : ils ne
  se périment pas, et ne se lisent pas comme des affirmations présentes.

### Outillage
- `docs/guide-deck.md` — deck source du guide (se compile via
  `tools/build_guide.py`, qui assemble `GUIDE.md` comme article). Entrée
  de build, pas documentation : se corrige comme du code.

### Artefacts régénérables
- `themes-gallery.html` — généré par `lightwebpres theme gallery` (le test
  `test_the_committed_gallery_is_byte_identical_to_a_fresh_one` vérifie qu'il
  est à jour).
- `docs/guide/` — build output du guide (`tools/build_guide.py`).

### Documents d'étape (consultables, hors arborescence active)
- `delete-before-1.0/` — miroir de la racine. Ce qui y entre reste
  consultable mais quitte l'arborescence active : mémoire de travail,
  relevés dont le raisonnement est versé ailleurs, et documents de
  conception absorbés (sous `docs/`). git en conserve l'historique ; la
  suppression effective se fera avant la 1.0, ce que son nom dit.

  **Avant d'y envoyer un document, vérifier ce qu'il porte encore.** Un
  plan livré contient souvent une décision que personne n'a prise et qui
  ne vit nulle part ailleurs ; elle va au `BACKLOG.md` avec sa mesure
  avant que le document ne sorte. Sans ce geste, ranger revient à perdre
  (`specifications.md` §1.1).

## Conventions

- **Parseur CLI fait main** (pas d'argparse) — `parse_cli_options()` + tables
  `_COMMAND_OPTIONS`, `_VALUE_OPTIONS`, `_GLOBAL_OPTIONS`. L'aide (`--help`)
  est un template maintenu à la main ; un test la verrouille contre les
  tables d'options pour qu'elle ne puisse pas dériver en silence.
- **Deux registres de test, et il faut les deux.** Le registre *boîte
  noire* lance l'exécutable en sous-processus (`run(*args)`) et vérifie ce
  qu'un utilisateur obtient : sortie, code de retour, fichiers écrits.
  C'est le registre par défaut pour tout ce qui a une surface CLI.

  Le registre *par introspection* importe le module
  (`load_lightwebpres_module()`, puis `self.lwp.…`) pour mesurer ce qu'une
  sortie ne montre pas : le registre de propriétés, les palettes résolues,
  les ratios de contraste, l'AST de l'exécutable. Une garde qui mesure
  57 thèmes ne peut pas le faire en construisant 57 sites.

  Cette convention disait « pas d'import direct des fonctions internes » ;
  c'était faux et cela aurait empêché d'écrire la moitié des gardes de ce
  dépôt. Le vrai critère n'est pas l'import, c'est **ce qu'on affirme** :
  un comportement visible se vérifie par la sortie, une propriété interne
  se mesure par le module.
- **Versionnage sémantique** (spec §13.9) : MAJOR = incompatible, MINOR =
  rétrocompatible. La constante `VERSION` est dans `lightwebpres`.
- **Bumper `VERSION`, c'est ouvrir une section du `CHANGELOG.md`** dans le
  même commit, sous le titre `## Unreleased — X.Y.Z`. Une garde
  (`test_the_version_it_announces_has_a_changelog_entry`) refuse la suite
  si le numéro annoncé n'a pas de section, donc les deux ne peuvent pas
  diverger en silence. La section se remplit au fil du travail, pas le
  jour de la release : c'est ce texte-là, tel quel, qui est collé dans le
  formulaire GitHub, et le titre devient `## vX.Y.Z — AAAA-MM-JJ` quand le
  propriétaire a tagué. Un texte, un endroit — un second récit du même
  changement s'écarte du premier en quelques mois.
- **Le propriétaire seul tague et publie.** L'agent ne crée ni tag ni
  release ; le proxy git refuse d'ailleurs les nouveaux `refs/tags/`. Ce
  que l'agent fournit, c'est le texte, dans un bloc copiable.
- **Style de commit** : un sujet en phrase, qui dit ce que le changement
  fait — **aucun préfixe**, pas même pour une release. Le corps n'est pas
  replié à 72 colonnes et explique le *pourquoi*, avec les mesures quand
  il y en a.

  Cette ligne annonçait `feat:` / `Docs:` / `Chore:` / `vX.Y.Z:`, et ce
  n'était pas faux à l'écriture : la convention a bel et bien été
  `vX.Y.Z:` jusqu'au 15 août 2026, puis elle a changé sans que ce document
  suive. Depuis, aucun sujet ne porte de préfixe. C'est le mode de
  décomposition à connaître ici — une convention citée de mémoire survit
  à la pratique qu'elle décrit — d'où la règle : **lire le style plutôt
  que ce paragraphe**, avec `git log --format=%s -20`.
- **Push** : `git push -u origin main`. Il n'y a qu'un remote, `origin`, et
  qu'une branche de travail, `main` — pas de branche de fonctionnalité.
  Jamais de push forcé.

## Licence et extension

- `lightwebpres` est sous **GPL v3** (`COPYING`). L'**Output Exception**
  (`COPYING.EXCEPTION`) permet aux présentations générées d'être diffusées
  sous la licence que choisit l'auteur du texte, pas celle du logiciel —
  sauf si l'œuvre diffusée est elle-même un générateur utilisant la sortie
  comme modèles.
- L'**intégration verticale** : un seul outil couvre toute la chaîne (écriture
  → build → thèmes → CI → présentation).
- L'**intégration horizontale** se décline en deux niveaux :
  - **`web/` dans l'arborescence** — un outil navigateur léger (deux onglets :
    déposer un zip à construire, ou tirer/build/pousser vers un dépôt GitLab).
    Tourne sous Pyodide en réutilisant l'exécutable `lightwebpres` tel quel,
    sans le réimplémenter (`web/app.py`, `web/git_sync.py`, `web/index.html`).
  - **`lightwebpres-gui`** (projet séparé, dépôt distinct hors de celui-ci) —
    un éditeur complet : navigateur de fichiers, éditeur Markdown (CodeMirror),
    bouton build, stockage persistant OPFS, PWA hors-ligne, chiffrement au repos
    (AES-GCM-256 + Argon2id), import/export GitLab. Tourne aussi sous Pyodide
    avec l'exécutable vendorisé.
  Le contrat est unidirectionnel : `lightwebpres` est la source de vérité, le
  GUI suit (spec §1.2).
- L'**extension** (GPL) : quiconque peut modifier et redistribuer, sous les
  conditions de la GPL. L'Output Exception est la soupape qui distingue
  « utiliser l'outil » de « redistribuer l'outil ».

## Ce qui n'est pas dans ce dépôt

- La création de thème est un **objectif séparé** : les thèmes livrés
  rendent des couleurs et des propriétés typées, mais l'outil ne *conçoit*
  pas un thème accessible. Il **mesure** (`theme show`, `series theme` :
  un niveau WCAG par catégorie, jamais un verdict) et il **avertit**
  (`audit` : la feuille résolue d'une série, sur trois défauts qui ne sont
  pas affaire de goût — un contrôle invisible, du texte de la couleur de
  son fond, une taille sous le plancher). Il ne refuse jamais un thème sur
  son apparence, et les seuils de l'avertissement sont dérivés du
  catalogue livré, jamais choisis : la règle est en `specifications.md`
  §9.5.6, à lire avant d'en déplacer un. L'expertise accessibilité
  (atteindre AA sur une palette donnée) est externe. Les dettes ouvertes sont au `BACKLOG.md` ; elles ne sont pas
  énumérées ici, parce qu'une liste de numéros dans un second fichier se
  périme sans que rien ne le signale — celle qui était là citait quatre
  entrées, toutes closes depuis.
- `series article add/remove/set` est **exclu** du périmètre CLI actuel
  (BACKLOG C2).
