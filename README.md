🇬🇧 [English version](README.en.md)

<p align="center">
  <img src="assets/logo/psyset-lockup.svg" alt="PsySet" width="360">
</p>

# PsySet — composer un examen neuropsychologique en une minute

Petite application (Mac et PC, interface FR/EN) pour les neuropsychologues :
vous cochez les tests choisis pour le patient, vous les mettez dans l'ordre,
et PsySet fabrique les PDF prêts à imprimer — feuilles patient, CRF, ou tout
fusionné. Elle lit **votre** dossier de tests, tel qu'il est sur votre
ordinateur. **100 % local : aucune donnée ne quitte votre ordinateur.**

<!-- TODO: add assets/screenshots/psyset-fr.png -->

## Pourquoi l'utiliser ?

Pour chaque patient, le même rituel : ouvrir le dossier des tests, parcourir
domaine après domaine, ouvrir les bons fichiers, imprimer la feuille du
patient et le CRF de chaque test… et oublier une feuille en route. PsySet
remplace tout cela par une liste à cocher. À côté de chaque test, des
pastilles montrent d'un coup d'œil ce qu'il contient :
`FEUILLE · CRF · CONSIG. · NORMES` (une pastille barrée = fichier absent).

## Organiser votre bibliothèque de tests

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
| `norms…`, `norm…` | normes (un ou plusieurs fichiers) | `NORMES` |

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

## Installation

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
(PsySet vous prévient juste avant). Si un fichier ne peut pas être converti,
la génération s'arrête en le nommant : jamais de PDF avec un trou silencieux.

## Utilisation

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

## 100 % local

Aucune connexion réseau, aucune donnée patient : PsySet ne manipule que vos
fichiers de tests, sur votre ordinateur.

---

## Pour les développeurs

Application Python/tkinter : point d'entrée [`PsySet.py`](PsySet.py), code dans
[`psyset/`](psyset), logos et icônes dans [`assets/`](assets). Dépendances :
`pypdf` et `send2trash`.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

**Construction locale (macOS)** : `./build.sh` (PyInstaller) → `dist/PsySet.app`.

**Releases automatiques** : pousser un tag `v*` déclenche GitHub Actions
([`.github/workflows/build.yml`](.github/workflows/build.yml)), qui lance les
tests, construit le `.app` macOS universel et le `.exe` Windows, puis les
attache à la Release :

```bash
git tag v1.0.0 && git push origin v1.0.0
```

## Licence

[MIT](LICENSE) — libre d'utilisation, de modification et de partage.
