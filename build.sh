#!/bin/zsh
# Construit PsySet.app dans dist/ (icônes et logos embarqués).
set -e
cd "$(dirname "$0")"

PYINSTALLER="$HOME/venvs/pyinstaller_env/bin/pyinstaller"
if [[ ! -x "$PYINSTALLER" ]]; then
  echo "PyInstaller introuvable ($PYINSTALLER). Installez-le :"
  echo "  python3 -m venv ~/venvs/pyinstaller_env && ~/venvs/pyinstaller_env/bin/pip install pyinstaller"
  exit 1
fi

# Dépendances d'exécution (pypdf, send2trash) dans le venv de PyInstaller uniquement.
"$HOME/venvs/pyinstaller_env/bin/pip" install -q -r requirements.txt

"$PYINSTALLER" --windowed --noconfirm --name "PsySet" \
  --icon assets/psyset.icns \
  --add-data "assets:assets" \
  PsySet.py

# macOS affiche « PsySet souhaite contrôler Word » : on y joint une explication.
PLIST="dist/PsySet.app/Contents/Info.plist"
plutil -replace NSAppleEventsUsageDescription -string \
  "PsySet utilise Word pour convertir vos documents en PDF. / PsySet uses Word to convert your documents to PDF." \
  "$PLIST"
# Modifier Info.plist invalide la signature : re-signature ad hoc.
codesign --force --deep -s - dist/PsySet.app

echo "OK → dist/PsySet.app"
