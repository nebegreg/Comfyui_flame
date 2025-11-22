# 🚀 ComfyUI-Flame v3.0 - Quick Start Guide

Get up and running in **15 minutes**!

## ⚡ Prerequisites Check

Before starting, verify you have:

- [ ] **Autodesk Flame** 2023.x, 2024.x, or 2025.2 installed
- [ ] **NVIDIA GPU** with 12GB+ VRAM (RTX 3060 Ti or better)
- [ ] **CUDA** 11.8+ or 12.1+ installed
- [ ] **Python 3.10+** (bundled with Flame)
- [ ] **100GB+ free disk space**

## 📦 Step 1: Install ComfyUI (10 minutes)

```bash
# Navigate to home directory
cd ~

# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install PyTorch with CUDA support
pip3 install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121

# Install ComfyUI dependencies
pip3 install -r requirements.txt

# Install additional dependencies for v3.0
pip3 install websocket-client requests Pillow

# Test ComfyUI
python3 main.py
```

**Expected output:**
```
Starting server
To see the GUI go to: http://127.0.0.1:8188
```

✅ If you see this, ComfyUI is running! Leave it running and **open a new terminal**.

## 🔌 Step 2: Install Essential Custom Nodes (5 minutes)

```bash
cd ~/ComfyUI/custom_nodes/

# Critical for Flame workflows
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git
git clone https://github.com/GeekyGhost/ComfyUI-GeekyRemB.git
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
git clone https://github.com/WASasquatch/was-node-suite-comfyui.git
git clone https://github.com/chflame163/ComfyUI_LayerStyle.git
git clone https://github.com/cubiq/ComfyUI_essentials.git

# Restart ComfyUI to load nodes
# Press Ctrl+C in the ComfyUI terminal, then:
python3 main.py
```

## 📥 Step 3: Download Required Models (varies - can run in background)

Create model directories:

```bash
cd ~/ComfyUI/models/

# Download checkpoints (required)
cd checkpoints/
wget https://huggingface.co/Lykon/DreamShaper/resolve/main/DreamShaper_8_pruned.safetensors -O dreamshaper_8.safetensors
wget https://civitai.com/api/download/models/245598 -O realisticVisionV60B1_v51VAE.safetensors

cd ../

# Download AnimateDiff (for temporal coherence)
mkdir -p animatediff_models
cd animatediff_models/
wget https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt

cd ../

# Download upscale models
mkdir -p upscale_models
cd upscale_models/
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth -O 4x-ClearRealityV2.pth

cd ~/ComfyUI
```

**Note**: Model downloads can take 30-60 minutes depending on your connection. You can continue to Step 4 while models download.

## 🔥 Step 4: Install Flame Integration (2 minutes)

```bash
# Clone the Flame-ComfyUI repository (or use your existing clone)
cd /tmp
git clone https://github.com/nebegreg/Comfyui_flame.git
cd Comfyui_flame/ComfyUI_Flame_2023-2025.2.x/

# Copy to Flame Python directory
sudo cp network_comfyui.py /opt/Autodesk/shared/python/
sudo cp comfyui_extensions.py /opt/Autodesk/shared/python/
sudo cp flame_comfyui_config_v3.json /opt/Autodesk/shared/python/

# Create workflows directory
sudo mkdir -p /opt/Autodesk/shared/python/comfyui_workflows
sudo cp workflows/*.json /opt/Autodesk/shared/python/comfyui_workflows/

# Create presets directory
sudo mkdir -p /opt/Autodesk/shared/python/comfyui_presets

# Set permissions
sudo chmod 755 /opt/Autodesk/shared/python/network_comfyui.py
sudo chmod 755 /opt/Autodesk/shared/python/comfyui_extensions.py
sudo chmod 644 /opt/Autodesk/shared/python/flame_comfyui_config_v3.json
sudo chmod 755 /opt/Autodesk/shared/python/comfyui_workflows
```

## ⚙️ Step 5: Configure Paths (1 minute)

Edit the configuration file:

```bash
sudo nano /opt/Autodesk/shared/python/flame_comfyui_config_v3.json
```

Update these paths (replace `YOUR_USERNAME`):

```json
{
  "paths": {
    "input_dir": "/home/YOUR_USERNAME/ComfyUI/output/flacom",
    "output_dir": "/home/YOUR_USERNAME/ComfyUI/output",
    "lut_dir": "/home/YOUR_USERNAME/ComfyUI/luts"
  }
}
```

**Save**: Ctrl+O, Enter, Ctrl+X

## 🎬 Step 6: Load in Flame (1 minute)

1. **Start Autodesk Flame**

2. **Reload Python Hooks**:
   - Press: **Shift + Ctrl + H + P**
   - Wait 3-5 seconds

3. **Verify Installation**:
   - Right-click any clip in **Media Panel**
   - Look for **"ComfyUI"** submenu
   - You should see: **"Process with ComfyUI"**

✅ **Success!** If you see this menu, you're ready to go!

## 🎯 First Test: Remove Background (1 minute)

Let's test with the simplest workflow:

1. **Select a clip** in Media Panel (any clip with a clear subject)

2. **Right-click** → **ComfyUI** → **Process with ComfyUI**

3. **Choose workflow**: `klaus.json` (simple background removal)

4. **Click "Confirm"**

5. **Wait**: Processing time ~2-5 seconds per frame
   - Watch Flame console/shell for progress
   - Check `/tmp/flame_comfyui_v3.log` for detailed logs

6. **Results**:
   - New sequence appears in the same reel
   - Named: `klaus_v1.00001.png`, `klaus_v1.00002.png`, etc.
   - Subject isolated with alpha channel

**Expected time**: 30 seconds for a 24-frame clip

## 🎨 Second Test: Film Look Grading (2 minutes)

1. Select a clip with colors (not already graded)

2. Right-click → ComfyUI → Process with ComfyUI

3. Choose: `film_look_lut_grading.json`

4. **Wait**: ~1-2 seconds per frame

5. **Results**: Cinematic teal/orange look applied

## 🐛 Troubleshooting

### "ComfyUI not running" error

```bash
# Check if ComfyUI is running
ps aux | grep comfyui

# If not, start it:
cd ~/ComfyUI
python3 main.py
```

### "No workflows found"

```bash
# Check workflows directory
ls -la /opt/Autodesk/shared/python/comfyui_workflows/

# Should show 13+ .json files
# If empty, re-copy workflows:
sudo cp /tmp/Comfyui_flame/ComfyUI_Flame_2023-2025.2.x/workflows/*.json \
        /opt/Autodesk/shared/python/comfyui_workflows/
```

### "ComfyUI menu not appearing"

```bash
# Check if hook is loaded
ls -la /opt/Autodesk/shared/python/network_comfyui.py

# Should show the file
# In Flame, reload hooks: Shift + Ctrl + H + P
```

### Check logs

```bash
# View real-time log
tail -f /tmp/flame_comfyui_v3.log

# Search for errors
grep -i error /tmp/flame_comfyui_v3.log
```

## 📚 Next Steps

Now that everything works, explore:

1. **Temporal Coherence**: `temporal_coherence_animatediff.json`
   - Stabilize AI-generated VFX elements
   - Eliminate frame flicker

2. **RIFE Slow-Motion**: `rife_frame_interpolation.json`
   - Create 2x, 4x, 8x slow-motion
   - Smooth jerky footage

3. **Advanced Keying**: `advanced_chroma_key.json`
   - AI-powered green/blue screen removal
   - Better than traditional keyers

4. **3D Maps**: `3d_maps_depth_normal_ao.json`
   - Generate depth, normal, AO maps
   - Use in Flame Action for 3D compositing

5. **4x Upscale**: `flux_4x_8x_upscale.json`
   - 1080p → 4K AI upscaling
   - Tiled processing for large images

## 🎓 Learn More

- **Full Documentation**: See `README_V3_ULTIMATE.md`
- **Workflow Reference**: Detailed guide for each workflow
- **Improvements Analysis**: See `IMPROVEMENTS_ANALYSIS.md` for technical details

## 💡 Pro Tips

1. **Keep ComfyUI Running**: Start it when you boot, run in background
   ```bash
   # Run in screen/tmux for persistence
   screen -S comfyui
   cd ~/ComfyUI
   python3 main.py
   # Ctrl+A, D to detach
   ```

2. **Monitor Resources**:
   ```bash
   # Check GPU usage
   nvidia-smi -l 1

   # Check ComfyUI memory
   curl http://127.0.0.1:8188/system_stats
   ```

3. **Create Favorites**: Edit config to add your most-used workflows to favorites

4. **Batch Processing**: Select multiple clips, process them all overnight

## ✅ Checklist

- [ ] ComfyUI installed and running on port 8188
- [ ] Essential custom nodes installed (9 repos)
- [ ] Base models downloaded (DreamShaper, Realistic Vision)
- [ ] Flame hook installed (`network_comfyui.py`)
- [ ] Extensions installed (`comfyui_extensions.py`)
- [ ] Configuration file updated with correct paths
- [ ] Workflows directory populated (13+ JSON files)
- [ ] Flame hooks reloaded (Shift+Ctrl+H+P)
- [ ] "ComfyUI" menu visible in Media Panel
- [ ] First test successful (background removal)

**Total time**: ~15-20 minutes (excluding model downloads)

---

**Need Help?**

- Check logs: `/tmp/flame_comfyui_v3.log`
- ComfyUI logs: `~/ComfyUI/comfyui.log`
- GitHub Issues: https://github.com/nebegreg/Comfyui_flame/issues

**Enjoy your new AI-powered VFX pipeline! 🎬🔥**
