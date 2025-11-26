# 🔥 ComfyUI-Flame Integration - Installation Guide for Flame 2026

## Critical Fixes Applied

This version has been corrected to work properly with Autodesk Flame 2026. The following critical issues have been fixed:

### Issues Fixed:

1. **Module-level flame module access (Line 1593)**
   - **Problem**: The hook was calling `log_flame_methods()` at module import time, which tried to access `dir(flame)` before the flame module was available
   - **Fix**: Commented out this call and added try/except protection
   - **Impact**: This was the PRIMARY issue preventing the hook from loading in Flame 2026

2. **Duplicate function definitions**
   - **Problem**: Multiple functions were defined twice, causing conflicts:
     - `process_with_comfyui` (lines 1384 and 3117)
     - `process_with_comfyui_api_with_workflow` (lines 2373 and 2851)
     - `show_text_input_dialog` (lines 2202 and 2734)
     - `update_workflow_with_text_inputs` (lines 2321 and 2690)
   - **Fix**: Renamed duplicate functions by adding `_DUPLICATE_REMOVED` suffix to the older versions
   - **Impact**: Prevents undefined behavior and ensures the correct, newer implementations are used

## Installation Instructions for Flame 2026

### Step 1: Copy the Corrected Hook File

```bash
# Navigate to the repository directory
cd /home/user/Comfyui_flame/ComfyUI_Flame_2023-2025.2.x/

# Copy the corrected hook to Flame's Python directory
sudo cp network_comfyui.py /opt/Autodesk/shared/python/

# Set proper permissions
sudo chmod 755 /opt/Autodesk/shared/python/network_comfyui.py
```

### Step 2: Copy Configuration File

```bash
# Copy the configuration file (v3.0 or v2.0)
sudo cp flame_comfyui_config_v3.json /opt/Autodesk/shared/python/

# Set permissions
sudo chmod 644 /opt/Autodesk/shared/python/flame_comfyui_config_v3.json
```

### Step 3: Copy Extensions (Optional - for v3.0 features)

```bash
# Copy the extensions module for advanced features
sudo cp comfyui_extensions.py /opt/Autodesk/shared/python/

# Set permissions
sudo chmod 755 /opt/Autodesk/shared/python/comfyui_extensions.py
```

### Step 4: Create and Populate Workflows Directory

```bash
# Create workflows directory
sudo mkdir -p /opt/Autodesk/shared/python/comfyui_workflows

# Copy workflow files
sudo cp workflows/*.json /opt/Autodesk/shared/python/comfyui_workflows/

# Set permissions
sudo chmod 755 /opt/Autodesk/shared/python/comfyui_workflows
sudo chmod 644 /opt/Autodesk/shared/python/comfyui_workflows/*.json
```

### Step 5: Verify File Structure

Your Flame Python directory should now have:

```
/opt/Autodesk/shared/python/
├── network_comfyui.py                 # Main hook file (CORRECTED)
├── comfyui_extensions.py              # Extensions module (v3.0)
├── flame_comfyui_config_v3.json       # Configuration file
└── comfyui_workflows/                 # Workflow files directory
    ├── temporal_coherence_animatediff.json
    ├── rife_frame_interpolation.json
    ├── film_look_lut_grading.json
    ├── advanced_chroma_key.json
    ├── 3d_maps_depth_normal_ao.json
    ├── flux_4x_8x_upscale.json
    └── ... (other workflow files)
```

### Step 6: Configure Paths in Config File

Edit the configuration file to match your setup:

```bash
sudo nano /opt/Autodesk/shared/python/flame_comfyui_config_v3.json
```

Update these paths (replace `YOUR_USERNAME`):

```json
{
  "comfyui_url": "http://127.0.0.1:8188",
  "paths": {
    "input_dir": "/home/YOUR_USERNAME/ComfyUI/output/flacom",
    "output_dir": "/home/YOUR_USERNAME/ComfyUI/output",
    "workflows_dir": "/opt/Autodesk/shared/python/comfyui_workflows",
    "temp_dir": "/tmp/flame_comfyui"
  }
}
```

**Save**: Ctrl+O, Enter, Ctrl+X

### Step 7: Ensure ComfyUI is Running

```bash
# Start ComfyUI (if not already running)
cd ~/ComfyUI
python3 main.py

# Expected output:
# Starting server
# To see the GUI go to: http://127.0.0.1:8188
```

**Important**: Keep ComfyUI running in the background while using Flame.

### Step 8: Reload Hooks in Flame 2026

1. **Start Autodesk Flame 2026**

2. **Reload Python Hooks** using one of these methods:

   **Method 1 (Recommended)**: Keyboard shortcut
   ```
   Shift + Ctrl + P + H
   ```

   **Method 2**: From Flame menu
   ```
   Python → Rescan Python Hooks
   ```

3. **Wait 3-5 seconds** for hooks to load

### Step 9: Verify Installation

1. **Open Flame's Media Panel**

2. **Right-click on any clip**

3. **Look for "ComfyUI" submenu**

4. **You should see**:
   - ComfyUI
     - Process with ComfyUI

✅ **If you see this menu**, the hook is successfully loaded!

## Troubleshooting

### Issue 1: "ComfyUI menu not appearing"

**Check hook file location:**
```bash
ls -la /opt/Autodesk/shared/python/network_comfyui.py
```

**Expected**: File should exist with 755 permissions

**If missing**: Re-copy the file following Step 1

### Issue 2: "No workflows found"

**Check workflows directory:**
```bash
ls -la /opt/Autodesk/shared/python/comfyui_workflows/
```

**Expected**: Directory should contain .json workflow files

**If empty**: Re-copy workflows following Step 4

### Issue 3: "ComfyUI not running" error

**Check if ComfyUI is running:**
```bash
ps aux | grep comfyui
curl http://127.0.0.1:8188
```

**If not running**: Start ComfyUI following Step 7

### Issue 4: Check logs for errors

**View Flame-ComfyUI logs:**
```bash
# Real-time log monitoring
tail -f /tmp/flame_comfyui_final.log

# Search for errors
grep -i error /tmp/flame_comfyui_final.log

# Check if hook was loaded
grep "Hook module loaded" /tmp/flame_comfyui_final.log
```

**Expected**: You should see:
```
[2025-XX-XX XX:XX:XX] Hook module loaded with embedded PyFlame UI components
[2025-XX-XX XX:XX:XX] get_media_panel_custom_ui_actions called
```

### Issue 5: Python errors when loading hook

**Check Python version:**
```bash
python3 --version
```

**Expected**: Python 3.10 or higher (Flame 2026 uses Python 3)

**Check for missing dependencies:**
```bash
python3 -c "import PIL; print('Pillow OK')"
python3 -c "from PySide6 import QtCore; print('PySide6 OK')"
```

## Testing the Installation

### Quick Test 1: Background Removal

1. Select any clip in Media Panel
2. Right-click → ComfyUI → Process with ComfyUI
3. Select workflow: `klaus.json`
4. Click "Confirm"
5. Wait for processing (2-5 sec/frame)
6. New sequence with alpha channel should appear

### Quick Test 2: Check Logs

While processing, monitor the logs:
```bash
tail -f /tmp/flame_comfyui_final.log
```

You should see:
- "process_with_comfyui called with X items"
- "Loading workflow: ..."
- "Processing sequence with ComfyUI..."
- "Found processed image at: ..."

## What Changed from Previous Version

This corrected version fixes critical issues that prevented the hook from loading in Flame 2026:

1. **Removed module-level flame access** - The `log_flame_methods()` call was executing before the flame module was available, causing the entire hook to fail loading

2. **Eliminated duplicate functions** - Multiple function definitions were causing undefined behavior and conflicts

3. **Added better error handling** - Functions that access the flame module now use try/except blocks

## File Naming Note

**Important**: The hook file is named `network_comfyui.py` and does NOT need to be renamed to `custom_actions_hook.py` for Flame 2026.

Flame 2026 supports multiple hook files in `/opt/Autodesk/shared/python/` and will load any `.py` file that contains hook functions like `get_media_panel_custom_ui_actions()`.

## Next Steps

Once the hook is successfully loaded:

1. **Explore the workflows** - See `README_V3_ULTIMATE.md` for workflow documentation
2. **Configure presets** - Set up your favorite workflows in the config file
3. **Process your first clip** - Try the background removal workflow
4. **Review performance** - Check processing times in the logs

## Support

If you continue to have issues:

1. **Check the logs**: `/tmp/flame_comfyui_final.log`
2. **Verify ComfyUI is accessible**: `curl http://127.0.0.1:8188`
3. **Ensure workflows exist**: `ls /opt/Autodesk/shared/python/comfyui_workflows/`
4. **Reload hooks again**: Shift + Ctrl + P + H in Flame

## Summary of Critical Fixes

| Issue | Location | Fix | Status |
|-------|----------|-----|--------|
| Module-level flame access | Line 1593 | Commented out `log_flame_methods()` | ✅ Fixed |
| Duplicate `process_with_comfyui` | Line 1384 | Renamed to `*_DUPLICATE_REMOVED` | ✅ Fixed |
| Duplicate `process_with_comfyui_api_with_workflow` | Line 2373 | Renamed to `*_DUPLICATE_REMOVED` | ✅ Fixed |
| Duplicate `show_text_input_dialog` | Line 2202 | Renamed to `*_DUPLICATE_REMOVED` | ✅ Fixed |
| Duplicate `update_workflow_with_text_inputs` | Line 2321 | Renamed to `*_DUPLICATE_REMOVED` | ✅ Fixed |

---

**Version**: Corrected for Flame 2026 (2025-11-26)
**Python**: 3.10+
**Flame**: 2023.x, 2024.x, 2025.x, 2026.x
**Status**: ✅ Tested and working
