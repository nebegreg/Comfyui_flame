#!/bin/bash

###############################################################################
# ComfyUI-Flame Integration - Installation Script Ultra-Professionnel
# Version: 3.0 Production
# Compatible: Autodesk Flame 2023.x - 2026.x
# Système: Linux (Rocky/CentOS/Ubuntu)
###############################################################################

set -e  # Exit on error

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour logger
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo "═══════════════════════════════════════════════════════════════"
echo "  ComfyUI-Flame Integration - Installation Ultra-Pro v3.0"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Vérifier si on est root pour certaines opérations
SUDO=""
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
    log_info "Script lancé en tant qu'utilisateur normal (utilisera sudo)"
else
    log_warning "Script lancé en tant que root"
fi

# Variables d'installation
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLAME_PYTHON_DIR="/opt/Autodesk/shared/python"
WORKFLOWS_DIR="${FLAME_PYTHON_DIR}/comfyui_workflows"
SOURCE_DIR="${SCRIPT_DIR}/ComfyUI_Flame_2023-2025.2.x"

# Chemins des fichiers sources
HOOK_FILE="${SOURCE_DIR}/network_comfyui.py"
EXTENSIONS_FILE="${SOURCE_DIR}/comfyui_extensions.py"
CONFIG_FILE="${SOURCE_DIR}/flame_comfyui_config.json"
WORKFLOWS_SOURCE="${SOURCE_DIR}/workflows"

# Détection de la version de Flame installée
detect_flame_version() {
    log_info "Détection de la version de Flame installée..."

    if [ -d "/opt/Autodesk/flame_2026" ]; then
        FLAME_VERSION="2026"
    elif [ -d "/opt/Autodesk/flame_2025" ]; then
        FLAME_VERSION="2025"
    elif [ -d "/opt/Autodesk/flame_2024" ]; then
        FLAME_VERSION="2024"
    elif [ -d "/opt/Autodesk/flame_2023" ]; then
        FLAME_VERSION="2023"
    else
        FLAME_VERSION="unknown"
    fi

    if [ "$FLAME_VERSION" != "unknown" ]; then
        log_success "Flame ${FLAME_VERSION} détecté"
    else
        log_warning "Version de Flame non détectée, installation générique"
    fi
}

# Vérification des prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."

    # Vérifier Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 n'est pas installé"
        exit 1
    fi
    log_success "Python 3: $(python3 --version)"

    # Vérifier PIL/Pillow
    if ! python3 -c "import PIL" 2>/dev/null; then
        log_warning "Pillow (PIL) n'est pas installé"
        log_info "Installation de Pillow..."
        pip3 install --user Pillow
    fi
    log_success "Pillow installé"

    # Vérifier PySide6 ou PySide2
    if ! python3 -c "from PySide6 import QtCore" 2>/dev/null; then
        if ! python3 -c "from PySide2 import QtCore" 2>/dev/null; then
            log_warning "Ni PySide6 ni PySide2 ne sont installés"
            log_info "Installation de PySide6..."
            pip3 install --user PySide6
        else
            log_success "PySide2 installé"
        fi
    else
        log_success "PySide6 installé"
    fi

    # Vérifier que le répertoire Flame Python existe
    if [ ! -d "$FLAME_PYTHON_DIR" ]; then
        log_error "Répertoire Flame Python n'existe pas: $FLAME_PYTHON_DIR"
        log_info "Création du répertoire..."
        $SUDO mkdir -p "$FLAME_PYTHON_DIR"
    fi
    log_success "Répertoire Flame Python existe: $FLAME_PYTHON_DIR"

    # Vérifier que les fichiers sources existent
    if [ ! -f "$HOOK_FILE" ]; then
        log_error "Fichier hook non trouvé: $HOOK_FILE"
        exit 1
    fi
    log_success "Fichiers sources trouvés"
}

# Backup des fichiers existants
backup_existing_files() {
    log_info "Sauvegarde des fichiers existants (si présents)..."

    BACKUP_DIR="${FLAME_PYTHON_DIR}/backup_$(date +%Y%m%d_%H%M%S)"

    if [ -f "${FLAME_PYTHON_DIR}/network_comfyui.py" ]; then
        $SUDO mkdir -p "$BACKUP_DIR"
        $SUDO cp "${FLAME_PYTHON_DIR}/network_comfyui.py" "$BACKUP_DIR/"
        log_success "Backup créé: $BACKUP_DIR"
    else
        log_info "Aucun fichier existant à sauvegarder"
    fi
}

# Installation des fichiers principaux
install_main_files() {
    log_info "Installation des fichiers principaux..."

    # Copier le hook principal
    log_info "  • Copie de network_comfyui.py..."
    $SUDO cp "$HOOK_FILE" "${FLAME_PYTHON_DIR}/"
    $SUDO chmod 755 "${FLAME_PYTHON_DIR}/network_comfyui.py"
    log_success "  Hook installé"

    # Copier le module d'extensions
    if [ -f "$EXTENSIONS_FILE" ]; then
        log_info "  • Copie de comfyui_extensions.py..."
        $SUDO cp "$EXTENSIONS_FILE" "${FLAME_PYTHON_DIR}/"
        $SUDO chmod 755 "${FLAME_PYTHON_DIR}/comfyui_extensions.py"
        log_success "  Extensions installées"
    fi

    # Copier la configuration
    log_info "  • Copie de flame_comfyui_config.json..."
    $SUDO cp "$CONFIG_FILE" "${FLAME_PYTHON_DIR}/"
    $SUDO chmod 644 "${FLAME_PYTHON_DIR}/flame_comfyui_config.json"
    log_success "  Configuration installée"
}

# Installation des workflows
install_workflows() {
    log_info "Installation des workflows..."

    # Créer le répertoire des workflows
    $SUDO mkdir -p "$WORKFLOWS_DIR"

    # Copier tous les workflows
    WORKFLOW_COUNT=0
    if [ -d "$WORKFLOWS_SOURCE" ]; then
        for workflow in "$WORKFLOWS_SOURCE"/*.json; do
            if [ -f "$workflow" ]; then
                $SUDO cp "$workflow" "$WORKFLOWS_DIR/"
                ((WORKFLOW_COUNT++))
            fi
        done
    fi

    $SUDO chmod 755 "$WORKFLOWS_DIR"
    $SUDO chmod 644 "$WORKFLOWS_DIR"/*.json 2>/dev/null || true

    log_success "  ${WORKFLOW_COUNT} workflows installés dans $WORKFLOWS_DIR"
}

# Création des répertoires utilisateur
create_user_directories() {
    log_info "Création des répertoires utilisateur..."

    # Déterminer le répertoire home de l'utilisateur réel
    if [ -n "$SUDO_USER" ]; then
        USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        USER_HOME="$HOME"
    fi

    COMFYUI_DIR="${USER_HOME}/ComfyUI"

    # Créer les répertoires avec le bon propriétaire
    if [ -n "$SUDO_USER" ]; then
        $SUDO -u "$SUDO_USER" mkdir -p "${COMFYUI_DIR}/output/flacom"
        $SUDO -u "$SUDO_USER" mkdir -p "${COMFYUI_DIR}/output/comfla"
    else
        mkdir -p "${COMFYUI_DIR}/output/flacom"
        mkdir -p "${COMFYUI_DIR}/output/comfla"
    fi

    log_success "  Répertoires créés: ${COMFYUI_DIR}/output/"
}

# Vérification de ComfyUI
check_comfyui() {
    log_info "Vérification de ComfyUI..."

    if curl -s http://127.0.0.1:8188 > /dev/null 2>&1; then
        log_success "  ComfyUI est en cours d'exécution sur http://127.0.0.1:8188"
    else
        log_warning "  ComfyUI ne semble pas être en cours d'exécution"
        log_info "  Démarrez ComfyUI avec: cd ~/ComfyUI && python3 main.py"
    fi
}

# Test de l'installation
test_installation() {
    log_info "Test de l'installation..."

    # Vérifier que les fichiers sont bien installés
    ERRORS=0

    if [ ! -f "${FLAME_PYTHON_DIR}/network_comfyui.py" ]; then
        log_error "  Hook non installé"
        ((ERRORS++))
    else
        log_success "  Hook: OK"
    fi

    if [ ! -f "${FLAME_PYTHON_DIR}/flame_comfyui_config.json" ]; then
        log_error "  Configuration non installée"
        ((ERRORS++))
    else
        log_success "  Configuration: OK"
    fi

    if [ ! -d "$WORKFLOWS_DIR" ] || [ -z "$(ls -A $WORKFLOWS_DIR 2>/dev/null)" ]; then
        log_error "  Workflows non installés"
        ((ERRORS++))
    else
        WORKFLOW_COUNT=$(ls -1 "$WORKFLOWS_DIR"/*.json 2>/dev/null | wc -l)
        log_success "  Workflows: ${WORKFLOW_COUNT} fichiers OK"
    fi

    # Vérifier les permissions
    if [ -r "${FLAME_PYTHON_DIR}/network_comfyui.py" ] && [ -x "${FLAME_PYTHON_DIR}/network_comfyui.py" ]; then
        log_success "  Permissions: OK"
    else
        log_warning "  Permissions incorrectes sur le hook"
    fi

    return $ERRORS
}

# Afficher les instructions post-installation
show_post_install_instructions() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Installation terminée avec succès!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo -e "${GREEN}Prochaines étapes:${NC}"
    echo ""
    echo "1. Démarrer ComfyUI (si pas déjà fait):"
    echo "   cd ~/ComfyUI && python3 main.py"
    echo ""
    echo "2. Lancer Autodesk Flame"
    echo ""
    echo "3. Recharger les hooks Python dans Flame:"
    echo "   ${BLUE}Shift + Ctrl + P + H${NC}"
    echo ""
    echo "4. Vérifier que le menu apparaît:"
    echo "   • Ouvrir Media Panel"
    echo "   • Clic droit sur un clip"
    echo "   • Chercher ${GREEN}\"ComfyUI\"${NC} dans le menu"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Fichiers installés:"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Hook:        ${FLAME_PYTHON_DIR}/network_comfyui.py"
    echo "Extensions:  ${FLAME_PYTHON_DIR}/comfyui_extensions.py"
    echo "Config:      ${FLAME_PYTHON_DIR}/flame_comfyui_config.json"
    echo "Workflows:   ${WORKFLOWS_DIR}/"
    echo ""
    echo "Logs:        /tmp/flame_comfyui_final.log"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Dépannage"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Si le menu n'apparaît pas:"
    echo ""
    echo "1. Vérifier les logs:"
    echo "   tail -f /tmp/flame_comfyui_final.log"
    echo ""
    echo "2. Vérifier que ComfyUI répond:"
    echo "   curl http://127.0.0.1:8188"
    echo ""
    echo "3. Relancer l'installation si nécessaire:"
    echo "   ./install_flame_comfyui.sh"
    echo ""
    echo "Documentation complète: FLAME_2026_INSTALLATION.md"
    echo ""
}

# Fonction principale
main() {
    # Étapes d'installation
    detect_flame_version
    echo ""

    check_prerequisites
    echo ""

    backup_existing_files
    echo ""

    install_main_files
    echo ""

    install_workflows
    echo ""

    create_user_directories
    echo ""

    check_comfyui
    echo ""

    # Test final
    if test_installation; then
        show_post_install_instructions
        exit 0
    else
        log_error "Des erreurs ont été détectées pendant l'installation"
        exit 1
    fi
}

# Exécuter le script
main
