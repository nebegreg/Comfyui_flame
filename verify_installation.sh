#!/bin/bash

###############################################################################
# ComfyUI-Flame Integration - Script de Vérification
# Version: 3.0 Production
# Teste tous les aspects de l'installation
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Variables
FLAME_PYTHON_DIR="/opt/Autodesk/shared/python"
WORKFLOWS_DIR="${FLAME_PYTHON_DIR}/comfyui_workflows"
CONFIG_FILE="${FLAME_PYTHON_DIR}/flame_comfyui_config.json"
LOG_FILE="/tmp/flame_comfyui_final.log"

# Compteurs
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Fonction de test
test_item() {
    local description="$1"
    local test_command="$2"

    ((TOTAL_CHECKS++))

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}[✓]${NC} $description"
        ((PASSED_CHECKS++))
        return 0
    else
        echo -e "${RED}[✗]${NC} $description"
        ((FAILED_CHECKS++))
        return 1
    fi
}

test_warning() {
    local description="$1"
    local test_command="$2"

    ((TOTAL_CHECKS++))

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}[✓]${NC} $description"
        ((PASSED_CHECKS++))
        return 0
    else
        echo -e "${YELLOW}[!]${NC} $description"
        ((WARNING_CHECKS++))
        return 1
    fi
}

# Banner
echo "═══════════════════════════════════════════════════════════════"
echo "  ComfyUI-Flame Integration - Vérification Complète"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Section 1: Fichiers d'installation
echo -e "${CYAN}━━━ 1. FICHIERS D'INSTALLATION ━━━${NC}"
test_item "Hook principal installé" "[ -f ${FLAME_PYTHON_DIR}/network_comfyui.py ]"
test_item "Module d'extensions installé" "[ -f ${FLAME_PYTHON_DIR}/comfyui_extensions.py ]"
test_item "Configuration installée" "[ -f ${CONFIG_FILE} ]"
test_item "Répertoire workflows existe" "[ -d ${WORKFLOWS_DIR} ]"

if [ -d "$WORKFLOWS_DIR" ]; then
    WORKFLOW_COUNT=$(ls -1 "$WORKFLOWS_DIR"/*.json 2>/dev/null | wc -l)
    if [ "$WORKFLOW_COUNT" -gt 0 ]; then
        echo -e "${GREEN}[✓]${NC} ${WORKFLOW_COUNT} workflows trouvés"
        ((PASSED_CHECKS++))
    else
        echo -e "${RED}[✗]${NC} Aucun workflow trouvé"
        ((FAILED_CHECKS++))
    fi
    ((TOTAL_CHECKS++))
fi
echo ""

# Section 2: Permissions
echo -e "${CYAN}━━━ 2. PERMISSIONS ━━━${NC}"
test_item "Hook exécutable" "[ -x ${FLAME_PYTHON_DIR}/network_comfyui.py ]"
test_item "Hook lisible" "[ -r ${FLAME_PYTHON_DIR}/network_comfyui.py ]"
test_item "Config lisible" "[ -r ${CONFIG_FILE} ]"
test_item "Workflows lisibles" "[ -r ${WORKFLOWS_DIR} ]"
echo ""

# Section 3: Dépendances Python
echo -e "${CYAN}━━━ 3. DÉPENDANCES PYTHON ━━━${NC}"
test_item "Python 3 installé" "command -v python3"
test_item "Pillow (PIL) installé" "python3 -c 'import PIL'"
test_item "PySide6 ou PySide2 installé" "python3 -c 'from PySide6 import QtCore' || python3 -c 'from PySide2 import QtCore'"
test_item "Module json disponible" "python3 -c 'import json'"
test_item "Module subprocess disponible" "python3 -c 'import subprocess'"
echo ""

# Section 4: Configuration
echo -e "${CYAN}━━━ 4. CONFIGURATION ━━━${NC}"
if [ -f "$CONFIG_FILE" ]; then
    # Vérifier que c'est un JSON valide
    test_item "Config JSON valide" "python3 -c 'import json; json.load(open(\"${CONFIG_FILE}\"))'"

    # Extraire les valeurs
    COMFYUI_URL=$(python3 -c "import json; print(json.load(open('${CONFIG_FILE}')).get('comfyui_url', 'N/A'))" 2>/dev/null || echo "N/A")
    INPUT_DIR=$(python3 -c "import json; print(json.load(open('${CONFIG_FILE}')).get('input_dir', 'N/A'))" 2>/dev/null || echo "N/A")
    OUTPUT_DIR=$(python3 -c "import json; print(json.load(open('${CONFIG_FILE}')).get('output_dir', 'N/A'))" 2>/dev/null || echo "N/A")

    echo -e "${BLUE}[i]${NC} ComfyUI URL: ${COMFYUI_URL}"
    echo -e "${BLUE}[i]${NC} Input Dir:   ${INPUT_DIR}"
    echo -e "${BLUE}[i]${NC} Output Dir:  ${OUTPUT_DIR}"
else
    echo -e "${RED}[✗]${NC} Fichier de configuration non trouvé"
fi
echo ""

# Section 5: Répertoires utilisateur
echo -e "${CYAN}━━━ 5. RÉPERTOIRES UTILISATEUR ━━━${NC}"
COMFYUI_HOME="${HOME}/ComfyUI"
test_warning "Répertoire ComfyUI existe" "[ -d ${COMFYUI_HOME} ]"
test_warning "Répertoire output existe" "[ -d ${COMFYUI_HOME}/output ]"
test_warning "Répertoire flacom existe" "[ -d ${COMFYUI_HOME}/output/flacom ]"
test_warning "Répertoire comfla existe" "[ -d ${COMFYUI_HOME}/output/comfla ]"
echo ""

# Section 6: ComfyUI Server
echo -e "${CYAN}━━━ 6. COMFYUI SERVER ━━━${NC}"
if [ "$COMFYUI_URL" != "N/A" ]; then
    test_warning "ComfyUI répond sur ${COMFYUI_URL}" "curl -s ${COMFYUI_URL} > /dev/null"

    if curl -s "${COMFYUI_URL}/system_stats" > /dev/null 2>&1; then
        echo -e "${GREEN}[✓]${NC} API ComfyUI accessible"
        ((PASSED_CHECKS++))
    else
        echo -e "${YELLOW}[!]${NC} API ComfyUI non accessible (démarrez ComfyUI)"
        ((WARNING_CHECKS++))
    fi
    ((TOTAL_CHECKS++))
else
    echo -e "${YELLOW}[!]${NC} URL ComfyUI non configurée"
    ((WARNING_CHECKS++))
    ((TOTAL_CHECKS++))
fi
echo ""

# Section 7: Logs
echo -e "${CYAN}━━━ 7. LOGS ET DEBUG ━━━${NC}"
if [ -f "$LOG_FILE" ]; then
    echo -e "${GREEN}[✓]${NC} Fichier de log existe: ${LOG_FILE}"
    ((PASSED_CHECKS++))

    LOG_SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    echo -e "${BLUE}[i]${NC} Taille du log: ${LOG_SIZE} bytes"

    # Chercher des erreurs récentes
    if grep -i "error" "$LOG_FILE" | tail -5 > /dev/null 2>&1; then
        echo -e "${YELLOW}[!]${NC} Des erreurs ont été loggées (voir ci-dessous)"
        echo ""
        echo -e "${YELLOW}Dernières erreurs:${NC}"
        grep -i "error" "$LOG_FILE" | tail -5 | sed 's/^/  /'
    else
        echo -e "${GREEN}[✓]${NC} Aucune erreur récente dans les logs"
        ((PASSED_CHECKS++))
    fi
    ((TOTAL_CHECKS++))
else
    echo -e "${YELLOW}[!]${NC} Aucun log trouvé (normal si Flame n'a pas encore été lancé)"
    ((WARNING_CHECKS++))
    ((TOTAL_CHECKS++))
fi
echo ""

# Section 8: Workflows détaillés
echo -e "${CYAN}━━━ 8. WORKFLOWS DISPONIBLES ━━━${NC}"
if [ -d "$WORKFLOWS_DIR" ]; then
    for workflow in "$WORKFLOWS_DIR"/*.json; do
        if [ -f "$workflow" ]; then
            WORKFLOW_NAME=$(basename "$workflow")
            if python3 -c "import json; json.load(open('${workflow}'))" > /dev/null 2>&1; then
                echo -e "${GREEN}[✓]${NC} ${WORKFLOW_NAME}"
            else
                echo -e "${RED}[✗]${NC} ${WORKFLOW_NAME} (JSON invalide)"
            fi
        fi
    done
fi
echo ""

# Section 9: Vérification de la structure du code
echo -e "${CYAN}━━━ 9. INTÉGRITÉ DU CODE ━━━${NC}"
HOOK_FILE="${FLAME_PYTHON_DIR}/network_comfyui.py"
if [ -f "$HOOK_FILE" ]; then
    # Vérifier la présence de fonctions clés
    test_item "Fonction get_media_panel_custom_ui_actions définie" "grep -q 'def get_media_panel_custom_ui_actions' ${HOOK_FILE}"
    test_item "Fonction process_with_comfyui définie" "grep -q 'def process_with_comfyui' ${HOOK_FILE}"
    test_item "Fonction load_config définie" "grep -q 'def load_config' ${HOOK_FILE}"
    test_item "Configuration chargée au démarrage" "grep -q 'CONFIG = load_config()' ${HOOK_FILE}"

    # Vérifier que les corrections ont été appliquées
    if grep -q "# COMMENTED OUT - This was causing hook to fail loading in Flame 2026" "$HOOK_FILE"; then
        echo -e "${GREEN}[✓]${NC} Corrections Flame 2026 appliquées"
        ((PASSED_CHECKS++))
    else
        echo -e "${YELLOW}[!]${NC} Corrections Flame 2026 non détectées"
        ((WARNING_CHECKS++))
    fi
    ((TOTAL_CHECKS++))
fi
echo ""

# Section 10: Test de syntaxe Python
echo -e "${CYAN}━━━ 10. VALIDATION PYTHON ━━━${NC}"
if [ -f "$HOOK_FILE" ]; then
    if python3 -m py_compile "$HOOK_FILE" 2>/dev/null; then
        echo -e "${GREEN}[✓]${NC} Syntaxe Python valide pour network_comfyui.py"
        ((PASSED_CHECKS++))
    else
        echo -e "${RED}[✗]${NC} Erreurs de syntaxe dans network_comfyui.py"
        ((FAILED_CHECKS++))
    fi
    ((TOTAL_CHECKS++))
fi

EXT_FILE="${FLAME_PYTHON_DIR}/comfyui_extensions.py"
if [ -f "$EXT_FILE" ]; then
    if python3 -m py_compile "$EXT_FILE" 2>/dev/null; then
        echo -e "${GREEN}[✓]${NC} Syntaxe Python valide pour comfyui_extensions.py"
        ((PASSED_CHECKS++))
    else
        echo -e "${RED}[✗]${NC} Erreurs de syntaxe dans comfyui_extensions.py"
        ((FAILED_CHECKS++))
    fi
    ((TOTAL_CHECKS++))
fi
echo ""

# Résumé final
echo "═══════════════════════════════════════════════════════════════"
echo "  RÉSUMÉ DE LA VÉRIFICATION"
echo "═══════════════════════════════════════════════════════════════"
echo ""

SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo -e "Total de tests: ${TOTAL_CHECKS}"
echo -e "${GREEN}Réussis:        ${PASSED_CHECKS}${NC}"
echo -e "${RED}Échoués:        ${FAILED_CHECKS}${NC}"
echo -e "${YELLOW}Avertissements: ${WARNING_CHECKS}${NC}"
echo ""
echo -e "Taux de réussite: ${SUCCESS_RATE}%"
echo ""

# Status final
if [ "$FAILED_CHECKS" -eq 0 ]; then
    if [ "$WARNING_CHECKS" -eq 0 ]; then
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  ✓ INSTALLATION PARFAITE - PRÊT POUR LA PRODUCTION${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        EXIT_CODE=0
    else
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}  ! INSTALLATION CORRECTE AVEC AVERTISSEMENTS${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        EXIT_CODE=0
    fi
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ✗ DES PROBLÈMES ONT ÉTÉ DÉTECTÉS${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    EXIT_CODE=1
fi

echo ""
echo "Actions recommandées:"
echo ""

if [ "$FAILED_CHECKS" -gt 0 ]; then
    echo "• Relancer l'installation: ./install_flame_comfyui.sh"
fi

if [ "$WARNING_CHECKS" -gt 0 ]; then
    if ! curl -s "http://127.0.0.1:8188" > /dev/null 2>&1; then
        echo "• Démarrer ComfyUI: cd ~/ComfyUI && python3 main.py"
    fi
    if [ ! -d "$COMFYUI_HOME/output/flacom" ]; then
        echo "• Créer les répertoires: mkdir -p ~/ComfyUI/output/flacom"
    fi
fi

echo "• Recharger les hooks dans Flame: Shift + Ctrl + P + H"
echo "• Vérifier les logs: tail -f /tmp/flame_comfyui_final.log"
echo ""
echo "Documentation: FLAME_2026_INSTALLATION.md"
echo ""

exit $EXIT_CODE
