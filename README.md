<p align="center">
  <img src="assets/logo/psyset-lockup.svg" alt="PsySet" width="360">
</p>

<p align="center"><b><a href="#english">English</a> · <a href="#français">Français</a></b></p>

<!-- TODO: add a screenshot (assets/screenshots/psyset-fr.png) -->

## English

**PsySet — put together a neuropsychological exam in a minute**

A small app (Mac and PC, FR/EN interface) for neuropsychologists: tick the
tests you chose for the patient, put them in order, and PsySet builds the
print-ready PDFs — patient sheets, CRFs, or everything merged. It reads
**your own** tests folder, as it is on your computer. **100% local: no data
ever leaves your computer.**

### Why use it?

For every patient, the same ritual: open the tests folder, go domain by
domain, open the right files, print the patient's sheet and the CRF of each
test… and forget a sheet along the way. PsySet replaces all that with a
checklist. Next to each test, small tags show at a glance what it contains:
`SHEET · CRF · INSTR · NORMS` (a crossed-out tag = missing file).

### Organise your tests library

PsySet reads your folder tree: the tree is the master copy, and you can keep
browsing it in Finder or Explorer. One folder per domain, one subfolder per
test:

```
Tests library/
├── Executive functioning/         ← domain
│   ├── TMT/                       ← test
│   │   ├── psyset.json            ← test info (written by the app)
│   │   ├── test.pdf               ← patient sheet
│   │   ├── rating.pdf             ← CRF (the clinician's scoring form)
│   │   └── instructions.pdf       ← administration instructions
│   └── Hayling/
│       ├── rating.pdf
│       ├── instructions.docx
│       ├── norms.pdf              ← norms
│       └── norm-calculation.xlsx  ← also counted as norms
└── Memory/
    └── CVLT/
        ├── test-A.pdf             ← version A: patient sheet…
        ├── rating-A.pdf           ←   …and its CRF
        ├── test-B.pdf             ← version B
        └── rating-B.docx
```

The four roles are recognised from the file name:

| File | Role | Tag |
|---|---|---|
| `test` | patient sheet | `SHEET` |
| `rating` | CRF | `CRF` |
| `instructions` | instructions | `INSTR` |
| anything starting with `norm` (`norms.pdf`, `norm-calculation.xlsx`…) | norms (one or several files) | `NORMS` |

- **Versions**: `test-A.pdf` and `rating-A.pdf` belong together (parallel
  forms A/B, or one sheet per subtest). An unlabelled file (`test.pdf`) is
  shared by all versions.
- Patient sheets and CRFs can be **PDF, Word (`.doc`, `.docx`) or `.odt`**.
- A test folder laid out differently, or files with unusual names, still show
  up: unclassified files are greyed out, and one click lets you assign them a
  role (the file is then renamed).

No library yet? At first launch, PsySet can **create an empty one** with the
recommended domains: Executive functioning, Memory, Instrumental functioning,
Attention, Social cognition, Autonomy, Mood.

### Installation

Download the zip of the latest version from the
**[Releases](../../releases/latest)** tab.

**On Mac** (`PsySet-macOS.zip`)
1. Unzip, then drag `PsySet.app` wherever you like (Applications, Desktop…).
2. First launch only: **right-click the app → "Open" → "Open"**.
   (The app is not Apple-signed; a normal double-click would be blocked.)

**On Windows** (`PsySet-Windows.zip`)
1. Unzip, then double-click `PsySet.exe`.
2. If the blue "Windows protected your PC" screen appears:
   *More info* → *Run anyway* (first launch only).

At first launch, pick the language, then **your existing tests folder** or
**create an empty library**. You can change the folder later from the
settings (top right).

### Word or LibreOffice

To merge sheets or CRFs that are Word/ODT files, PsySet has to convert them to
PDF, so you need **Microsoft Word or LibreOffice** installed (nothing to
install if all your documents are already PDFs). Your original files are never
modified: conversion works on temporary copies.

On a Mac with Word, the first conversion triggers a one-time macOS prompt:
**"PsySet wants to control Microsoft Word"**. Click OK (the first time, PsySet warns you just
before). If a file can't be converted, generation stops and names it: never a
PDF with a silent gap.

### Usage

1. **Tick** the tests in the middle list (pick a domain on the left, or search
   by name, subdomain or author across the whole library). Clicking a tag opens
   the matching file.
2. **Order** the exam in the right-hand panel: drag and drop, or the ▲ ▼
   arrows; ✕ removes a test.
3. **Versions**: if a test has several, `[A] [B]` chips on its row let you
   choose A, B, or A+B.
4. **Generate**: tick what you need — *Patient sheets*, *CRFs*, *Everything
   merged* ("test by test" or "sheets, then CRFs") — then **Generate PDFs…**.
   Suggested names look like `2026-10-23_patient-sheets.pdf` (never a patient
   name).
5. **Double-sided**: the option adds a blank page after any document with an
   odd page count, so each document starts on a fresh sheet.
6. A warning lists the tests that have no patient sheet or no CRF.

PsySet doesn't print: open the PDF and print it.

**Add or edit a test**: "＋ Add a test" (name, bibliographic reference,
domain, subdomain, and one file per role; several labelled files A, B… for
sheets and CRFs). Files are **copied** into the library under their standard
names; your originals stay where they are. "Edit info" reopens the form; "Remove
test" sends the folder to the **Trash / Recycle Bin**: nothing is ever
permanently deleted. Exception on Windows: a network or removable drive (USB
stick) often has no Recycle Bin, so "moving to the Recycle Bin" can be
permanent there.

### 100% local

No network access, no patient data: PsySet only handles your test files, on
your computer.

---

## Français

**PsySet — composer un examen neuropsychologique en une minute**

Petite application (Mac et PC, interface FR/EN) pour les neuropsychologues :
vous cochez les tests choisis pour le patient, vous les mettez dans l'ordre,
et PsySet fabrique les PDF prêts à imprimer — feuilles patient, CRF, ou tout
fusionné. Elle lit **votre** dossier de tests, tel qu'il est sur votre
ordinateur. **100 % local : aucune donnée ne quitte votre ordinateur.**

### Pourquoi l'utiliser ?

Pour chaque patient, le même rituel : ouvrir le dossier des tests, parcourir
domaine après domaine, ouvrir les bons fichiers, imprimer la feuille du
patient et le CRF de chaque test… et oublier une feuille en route. PsySet
remplace tout cela par une liste à cocher. À côté de chaque test, des
pastilles montrent d'un coup d'œil ce qu'il contient :
`FEUILLE · CRF · CONSIG. · NORMES` (une pastille barrée = fichier absent).

### Organiser votre bibliothèque de tests

PsySet lit l'arborescence de votre dossier : c'est elle qui fait foi, et vous
pouvez continuer à la parcourir dans le Finder ou l'Explorateur. Un dossier
par domaine, un sous-dossier par test :

```
Bibliothèque de tests/
├── Fonctions exécutives/          ← domaine
│   ├── TMT/                       ← test
│   │   ├── psyset.json            ← fiche du test (écrite par l'application)
│   │   ├── test.pdf               ← feuille patient
│   │   ├── rating.pdf             ← CRF (feuille de cotation du clinicien)
│   │   └── instructions.pdf       ← consignes de passation
│   └── Hayling/
│       ├── rating.pdf
│       ├── instructions.docx
│       ├── norms.pdf              ← normes
│       └── norm-calculation.xlsx  ← compte aussi comme normes
└── Mémoire/
    └── CVLT/
        ├── test-A.pdf             ← version A : feuille patient…
        ├── rating-A.pdf           ←   …et son CRF
        ├── test-B.pdf             ← version B
        └── rating-B.docx
```

Les quatre rôles sont reconnus d'après le nom du fichier :

| Fichier | Rôle | Pastille |
|---|---|---|
| `test` | feuille patient | `FEUILLE` |
| `rating` | CRF | `CRF` |
| `instructions` | consignes | `CONSIG.` |
| tout nom commençant par `norm` (`norms.pdf`, `norm-calcul.xlsx`…) | normes (un ou plusieurs fichiers) | `NORMES` |

- **Versions** : `test-A.pdf` et `rating-A.pdf` vont ensemble (formes
  parallèles A/B, ou une feuille par sous-test). Un fichier sans étiquette
  (`test.pdf`) est partagé par toutes les versions.
- Les feuilles patient et les CRF peuvent être en **PDF, Word (`.doc`,
  `.docx`) ou `.odt`**.
- Un dossier de test rangé autrement, ou des fichiers au nom inhabituel,
  s'affichent quand même : les fichiers non classés sont grisés, et un clic
  permet de leur attribuer un rôle (le fichier est alors renommé).

Pas de bibliothèque ? Au premier lancement, PsySet peut en **créer une vide**
avec les domaines recommandés : Fonctions exécutives, Mémoire, Fonctions
instrumentales, Attention, Cognition sociale, Autonomie, Thymie.

### Installation

Télécharger le zip de la dernière version dans l'onglet
**[Releases](../../releases/latest)**.

**Sur Mac** (`PsySet-macOS.zip`)
1. Dézipper, puis glisser `PsySet.app` où vous voulez (Applications, Bureau…).
2. Premier lancement uniquement : **clic droit sur l'app → « Ouvrir » → « Ouvrir »**.
   (L'application n'est pas signée Apple ; un double-clic normal serait bloqué.)

**Sur PC Windows** (`PsySet-Windows.zip`)
1. Dézipper, puis double-cliquer `PsySet.exe`.
2. Si l'écran bleu « Windows a protégé votre ordinateur » apparaît :
   *Informations complémentaires* → *Exécuter quand même* (première fois uniquement).

Au premier lancement, choisissez la langue puis **votre dossier de tests**
existant, ou **créez une bibliothèque** vide. Le dossier peut être changé plus
tard depuis les réglages (en haut à droite).

### Word ou LibreOffice

Pour fusionner des feuilles ou des CRF au format Word/ODT, PsySet doit les
convertir en PDF : il faut donc **Microsoft Word ou LibreOffice** installé
(rien à installer si tous vos documents sont déjà des PDF). Vos fichiers
d'origine ne sont jamais modifiés : la conversion se fait sur des copies
temporaires.

Sur Mac avec Word, la première conversion déclenche une demande unique de
macOS : **« PsySet souhaite contrôler Microsoft Word »**. Cliquez sur OK
(la première fois, PsySet vous prévient juste avant). Si un fichier ne peut pas être converti,
la génération s'arrête en le nommant : jamais de PDF avec un trou silencieux.

### Utilisation

1. **Cocher** les tests dans la liste du milieu (choisir un domaine à gauche,
   ou chercher par nom, sous-domaine ou auteur dans toute la bibliothèque).
   Un clic sur une pastille ouvre le fichier correspondant.
2. **Ordonner** l'examen dans le panneau de droite : glisser-déposer, ou
   flèches ▲ ▼ ; ✕ retire un test.
3. **Versions** : si un test en a plusieurs, des pastilles `[A] [B]` sur sa
   ligne permettent de choisir A, B, ou A+B.
4. **Générer** : cocher ce qu'il vous faut — *Feuilles patient*, *CRF*,
   *Tout fusionné* (« test par test » ou « feuilles, puis CRF ») — puis
   **Générer les PDF…**. Les noms proposés sont du type
   `2026-10-23_feuilles-patient.pdf` (jamais de nom de patient).
5. **Recto-verso** : l'option ajoute une page blanche après tout document
   de nombre de pages impair, pour que chaque document commence sur une
   feuille neuve.
6. Un message signale les tests sans feuille patient ou sans CRF.

PsySet n'imprime pas : ouvrez le PDF et imprimez-le.

**Ajouter ou modifier un test** : « ＋ Ajouter un test » (nom, référence
bibliographique, domaine, sous-domaine, et un fichier par rôle ; plusieurs
fichiers avec étiquette A, B… pour les feuilles et CRF). Les fichiers sont
**copiés** dans la bibliothèque sous leur nom standard ; vos originaux restent
où ils sont. « Modifier » rouvre le formulaire ; « Supprimer le test » envoie
le dossier à la **Corbeille** — rien n'est jamais supprimé définitivement.
Exception sous Windows : un lecteur réseau ou amovible (clé USB) n'a souvent
pas de Corbeille, et y « mettre à la Corbeille » peut alors être définitif.

### 100 % local

Aucune connexion réseau, aucune donnée patient : PsySet ne manipule que vos
fichiers de tests, sur votre ordinateur.

---

## For developers · Pour les développeurs

Python/tkinter app: entry point [`PsySet.py`](PsySet.py), code in
[`psyset/`](psyset), logos and icons in [`assets/`](assets). Dependencies:
`pypdf`, `send2trash` and `cryptography` (publishers' protected PDFs).

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

**Local build (macOS)**: `./build.sh` (PyInstaller) → `dist/PsySet.app`.

**Automated releases**: pushing a `v*` tag triggers GitHub Actions
([`.github/workflows/build.yml`](.github/workflows/build.yml)), which runs the
tests, builds the universal macOS `.app` and the Windows `.exe`, then
attaches them to the Release:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

## License · Licence

[MIT](LICENSE) — free to use, modify and share · libre d'utilisation, de modification et de partage.
