#!/bin/bash
set -e

VENV_DIR=".venv"
SCRIPTS=(
  "./script/normalize.py"
  "./script/preprocess.py"
)

# 1. Créer l'environnement virtuel s'il n'existe pas
if [ ! -d "$VENV_DIR" ]; then
    echo "Création de l'environnement virtuel..."
    python -m venv "$VENV_DIR"
fi

# 2. Activer l'environnement virtuel
source "$VENV_DIR/Scripts/activate"

# 3. Installer les dépendances si requirements.txt existe
if [ -f "requirements.txt" ]; then
    echo "Installation des dépendances..."
    pip install -r requirements.txt
fi

# 4. Exécuter le script Python
for script in "${SCRIPTS[@]}"; do
    echo "=============================="
    echo "Exécution de $script"
    echo "=============================="

    python "$script"
done