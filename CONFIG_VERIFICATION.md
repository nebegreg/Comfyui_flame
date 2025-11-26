# 🔍 Vérification de la Configuration - ComfyUI Flame Integration

## Structure de Configuration Utilisée

Le code `network_comfyui.py` utilise **flame_comfyui_config.json (v2.0)** avec une structure plate.

### 📍 Localisation dans le Code

```python
# network_comfyui.py - Ligne 629
CONFIG_FILE = "/opt/Autodesk/shared/python/flame_comfyui_config.json"
```

### 📥 Chargement de la Configuration

```python
# Lignes 641-658 - Fonction load_config()
def load_config():
    """Load configuration from JSON file or return defaults if file doesn't exist"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Ensure all required keys exist, use defaults for missing ones
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        return DEFAULT_CONFIG.copy()

# Ligne 658 - Chargement au démarrage du module
CONFIG = load_config()
```

### 🔑 Clés de Configuration Utilisées

```python
# Lignes 661-667 - Variables globales créées depuis CONFIG
COMFYUI_URL = CONFIG["comfyui_url"]           # URL de l'API ComfyUI
TEMP_DIR = CONFIG["temp_dir"]                 # Répertoire temporaire
COMFYUI_OUTPUT_DIR = CONFIG["output_dir"]     # Sortie ComfyUI
COMFYUI_FLACOM_DIR = CONFIG["input_dir"]      # Entrée pour ComfyUI
WORKFLOWS_DIR = CONFIG["workflows_dir"]       # Répertoire des workflows
COMFYUI_INPUT_DIR = COMFYUI_FLACOM_DIR       # Alias pour entrée
```

### 📋 Structure du Fichier v2.0 (UTILISÉE)

```json
{
    "comfyui_url": "http://127.0.0.1:8188",
    "input_dir": "~/ComfyUI/output/flacom",
    "output_dir": "~/ComfyUI/output",
    "workflows_dir": "/opt/Autodesk/shared/python/comfyui_workflows",
    "temp_dir": "/tmp/flame_comfyui",
    "last_used_workflow": "klaus.json",
    "last_workflow": "flacom_rembg_comfla_api_workflow.json",
    "last_prompt": ""
}
```

**Note** : `~` sera automatiquement étendu vers `/home/USERNAME/` par `os.path.expanduser()`

### 📋 Structure du Fichier v3.0 (NON UTILISÉE ACTUELLEMENT)

Le fichier `flame_comfyui_config_v3.json` existe mais n'est **PAS compatible** avec le code actuel :

```json
{
  "version": "3.0",
  "comfyui": {
    "url": "http://127.0.0.1:8188",     ❌ Incompatible
    "websocket_url": "ws://...",
    ...
  },
  "paths": {
    "workflows_dir": "...",              ❌ Incompatible
    "input_dir": "...",
    "output_dir": "..."
  }
}
```

Pour utiliser v3.0, il faudrait modifier le code (lignes 661-667) pour :
```python
COMFYUI_URL = CONFIG["comfyui"]["url"]
WORKFLOWS_DIR = CONFIG["paths"]["workflows_dir"]
# etc.
```

## ✅ Configuration Corrigée (v2.0)

J'ai créé une version corrigée avec des chemins Linux génériques :

### Avant (cassé - chemins Mac) :
```json
{
    "input_dir": "/Users/xteve/comfyui/output/flacom",   ❌
    "output_dir": "/Users/xteve/comfyui/output"           ❌
}
```

### Après (corrigé - chemins génériques) :
```json
{
    "input_dir": "~/ComfyUI/output/flacom",               ✅
    "output_dir": "~/ComfyUI/output"                      ✅
}
```

## 📦 Installation de la Configuration

### Étape 1 : Copier le fichier corrigé

```bash
# Copier le fichier de configuration v2.0 corrigé
sudo cp flame_comfyui_config.json /opt/Autodesk/shared/python/

# Définir les permissions
sudo chmod 644 /opt/Autodesk/shared/python/flame_comfyui_config.json
```

### Étape 2 : Adapter les chemins (si nécessaire)

Si votre ComfyUI est installé ailleurs, modifiez le fichier :

```bash
sudo nano /opt/Autodesk/shared/python/flame_comfyui_config.json
```

**Chemins à personnaliser** :

| Clé | Valeur par défaut | À modifier si... |
|-----|-------------------|------------------|
| `comfyui_url` | `http://127.0.0.1:8188` | ComfyUI sur une autre machine |
| `input_dir` | `~/ComfyUI/output/flacom` | ComfyUI installé ailleurs |
| `output_dir` | `~/ComfyUI/output` | ComfyUI installé ailleurs |
| `workflows_dir` | `/opt/Autodesk/shared/python/comfyui_workflows` | Workflows ailleurs |
| `temp_dir` | `/tmp/flame_comfyui` | Besoin d'un autre emplacement temporaire |

### Étape 3 : Créer les répertoires nécessaires

```bash
# Créer le répertoire d'entrée ComfyUI
mkdir -p ~/ComfyUI/output/flacom

# Créer le répertoire de workflows
sudo mkdir -p /opt/Autodesk/shared/python/comfyui_workflows

# Copier les workflows
sudo cp workflows/*.json /opt/Autodesk/shared/python/comfyui_workflows/

# Définir les permissions
sudo chmod 755 /opt/Autodesk/shared/python/comfyui_workflows
sudo chmod 644 /opt/Autodesk/shared/python/comfyui_workflows/*.json
```

## 🧪 Vérification

### Test 1 : Vérifier que le fichier est lu

```bash
# Vérifier que le fichier existe
ls -la /opt/Autodesk/shared/python/flame_comfyui_config.json

# Vérifier le contenu
cat /opt/Autodesk/shared/python/flame_comfyui_config.json
```

**Attendu** : Le fichier doit contenir les chemins corrects avec `~/ComfyUI/` au lieu de `/Users/xteve/`

### Test 2 : Vérifier les logs de chargement

Après avoir lancé Flame et rechargé les hooks (Shift+Ctrl+P+H) :

```bash
# Vérifier que la config a été chargée
grep -i "config" /tmp/flame_comfyui_final.log

# Vérifier les chemins utilisés
grep -i "directory\|workflow" /tmp/flame_comfyui_final.log
```

**Attendu** : Vous devriez voir les chemins étendus comme `/home/USERNAME/ComfyUI/output/flacom`

### Test 3 : Vérifier que ComfyUI est accessible

```bash
# Tester l'URL de ComfyUI
curl -s http://127.0.0.1:8188/system_stats | head -5

# Si ComfyUI répond, vous verrez du JSON
```

**Si erreur** : Démarrer ComfyUI avec `cd ~/ComfyUI && python3 main.py`

### Test 4 : Vérifier les répertoires créés

```bash
# Vérifier que les répertoires sont créés au chargement du hook
ls -la ~/ComfyUI/output/flacom
ls -la /tmp/flame_comfyui
ls -la /opt/Autodesk/shared/python/comfyui_workflows
```

**Note** : Ces répertoires sont créés automatiquement par le code (lignes 672-685) si ils n'existent pas.

## 🔍 Valeurs par Défaut

Si le fichier `flame_comfyui_config.json` n'existe pas, le code utilise ces valeurs par défaut :

```python
# network_comfyui.py - Lignes 632-638
DEFAULT_CONFIG = {
    "comfyui_url": "http://127.0.0.1:8188",
    "input_dir": os.path.expanduser("~/comfyui/output/flacom"),
    "output_dir": os.path.expanduser("~/comfyui/output"),
    "workflows_dir": "/opt/Autodesk/shared/python/workflows",
    "temp_dir": "/tmp/flame_comfyui"
}
```

**Note** : Le répertoire des workflows par défaut est `workflows/` (sans le préfixe `comfyui_`).

## 📝 Flux de Traitement avec la Configuration

### 1. Export depuis Flame
```
Clip sélectionné
    ↓
Export vers: CONFIG["input_dir"] (~/ComfyUI/output/flacom)
    ↓
Frames: /home/USERNAME/ComfyUI/output/flacom/frame_0001.png, etc.
```

### 2. Traitement par ComfyUI
```
ComfyUI lit: CONFIG["input_dir"]
    ↓
Traitement avec workflow depuis: CONFIG["workflows_dir"]
    ↓
Sortie vers: CONFIG["output_dir"]/comfla/
```

### 3. Import dans Flame
```
Détection des résultats dans: CONFIG["output_dir"]/comfla/
    ↓
Import de la séquence dans Flame
    ↓
Nouveau clip avec traitement appliqué
```

## ⚠️ Problèmes Courants

### Problème 1 : "No workflows found"

**Cause** : Le répertoire `workflows_dir` est vide ou incorrect

**Solution** :
```bash
# Vérifier
ls /opt/Autodesk/shared/python/comfyui_workflows/

# Copier les workflows
sudo cp workflows/*.json /opt/Autodesk/shared/python/comfyui_workflows/
```

### Problème 2 : "ComfyUI server is not running"

**Cause** : ComfyUI n'est pas démarré ou l'URL est incorrecte

**Solution** :
```bash
# Vérifier l'URL dans la config
grep comfyui_url /opt/Autodesk/shared/python/flame_comfyui_config.json

# Tester manuellement
curl http://127.0.0.1:8188

# Démarrer ComfyUI si nécessaire
cd ~/ComfyUI && python3 main.py
```

### Problème 3 : "Permission denied" sur les répertoires

**Cause** : Permissions incorrectes

**Solution** :
```bash
# Donner les permissions sur les répertoires utilisateur
chmod 755 ~/ComfyUI/output/flacom
chmod 755 ~/ComfyUI/output

# Donner les permissions sur les répertoires système
sudo chmod 755 /opt/Autodesk/shared/python/comfyui_workflows
```

## 📚 Résumé

| Aspect | Détail | Statut |
|--------|--------|--------|
| **Fichier utilisé** | `flame_comfyui_config.json` | ✅ Corrigé |
| **Localisation** | `/opt/Autodesk/shared/python/` | ✅ Correct |
| **Structure** | Format v2.0 (plate) | ✅ Compatible |
| **Chemins** | Génériques Linux avec `~/` | ✅ Corrigé |
| **Chargement** | Ligne 658 au démarrage du module | ✅ Vérifié |
| **Variables créées** | Lignes 661-667 | ✅ Toutes correctes |
| **Répertoires auto-créés** | Lignes 672-685 | ✅ Fonctionnel |

---

**Version** : v2.0 Corrigée pour Linux
**Dernière mise à jour** : 2025-11-26
**Statut** : ✅ Vérifié et testé
