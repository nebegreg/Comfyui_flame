#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Final Flame-ComfyUI Integration Hook

This version includes basic image processing functionality
to export frames from Flame, send them to ComfyUI, and process the results.
"""

# Import built-in modules only
import os
import tempfile
import time
import uuid
import json
import base64
import subprocess
import shutil
from urllib.request import Request, urlopen
from urllib.error import URLError
import socket
from PIL import Image
import traceback
import re
from datetime import datetime
import threading
import platform
import sys
from enum import Enum
import copy  # Add this import at the top of the file

# Try to import flame module when run in Flame
try:
    import flame
except ImportError:
    pass

# Try to import PySide6, otherwise import PySide2
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtGui import QAction
    using_pyside6 = True
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    QAction = QtWidgets.QAction
    using_pyside6 = False

#---------------------------------------------
# [Constants]
#---------------------------------------------
PYFLAME_FONT = 'Discreet'  # Font used in all PyFlame UI elements
PYFLAME_FONT_SIZE = 13  # Default font size used in all PyFlame UI elements

#---------------------------------------------
# [PyFlame Enums]
#---------------------------------------------
class Color(Enum):
    """Color enum for UI elements."""
    BLUE = 'rgb(0, 110, 175)'
    BLUE_DARK = 'rgb(0, 70, 120)'
    BLUE_HIGHLIGHT = 'rgb(41, 140, 200)'
    RED = 'rgb(200, 29, 29)'
    GRAY = 'rgb(58, 58, 58)'
    GRAY_DARK = 'rgb(40, 40, 40)'
    GRAY_LIGHT = 'rgb(70, 70, 70)' 
    BLACK = 'rgb(0, 0, 0)'
    WHITE = 'rgb(255, 255, 255)'
    TEXT = 'rgb(180, 180, 180)'  # Brightened from 154
    BUTTON_TEXT = 'rgb(200, 200, 200)'  # Brightened from 165
    BORDER = 'rgb(100, 100, 100)'  # Brightened from 90
    
    # New gradient colors
    GRADIENT_START = 'rgb(45, 45, 45)'
    GRADIENT_END = 'rgb(60, 60, 60)'
    
    # Accent colors
    ACCENT_BLUE = 'rgb(0, 130, 200)'
    ACCENT_RED = 'rgb(220, 50, 50)'
    ACCENT_GREEN = 'rgb(50, 180, 50)'

class LineColor(Enum):
    """Color options for window border lines."""
    GRAY = QtGui.QColor(71, 71, 71)
    BLUE = QtGui.QColor(0, 110, 175)
    RED = QtGui.QColor(200, 29, 29)
    GREEN = QtGui.QColor(0, 180, 13)

#---------------------------------------------
# [Window Resolution Helper]
#---------------------------------------------
class WindowResolution:
    """Utility class to determine the main window resolution."""
    @staticmethod
    def main_window():
        if QtCore.__version_info__[0] < 6:
            main_window_res = QtWidgets.QDesktopWidget()
        else:
            main_window_res = QtGui.QGuiApplication.primaryScreen()
        return main_window_res

#---------------------------------------------
# [GUI Resize Functions]
#---------------------------------------------
def gui_resize(value):
    """Scale UI elements based on screen resolution."""
    if not isinstance(value, int):
        return value
        
    # Adjust this multiplier to make UI elements larger overall
    # Increase this value to make everything bigger
    UI_SCALE_FACTOR = 1.5
    
    # Baseline resolution from mac studio display
    base_screen_height = 1500  # Lowered from 3190 to better handle common resolutions
    
    # Get current screen resolution
    main_window_res = WindowResolution.main_window()
    screen_resolution = main_window_res.screenGeometry()
    
    # Get screen height
    screen_height = screen_resolution.height()
    
    # Calculate screen ratio
    screen_ratio = max(0.6, min(1.2, screen_height / base_screen_height))
    
    # Scale value based on screen ratio with additional scaling factor
    scaled_value = int(float(value) * screen_ratio * UI_SCALE_FACTOR)
    
    # Ensure minimum size for UI elements
    if value > 20:  # For larger elements like widget heights/widths
        scaled_value = max(scaled_value, value)
    
    return scaled_value

def font_resize(value):
    """Scale font sizes based on screen resolution."""
    if not isinstance(value, int):
        return value
        
    # Adjust this multiplier to make fonts larger overall
    FONT_SCALE_FACTOR = 1.3
    
    # Scale font size
    scaled_size = gui_resize(value)
    
    # Apply font scale factor
    scaled_size = int(scaled_size * FONT_SCALE_FACTOR)
    
    # Ensure minimum font size
    return max(scaled_size, value)

#---------------------------------------------
# [PyFlame UI Widget Classes]
#---------------------------------------------
class PyFlameButton(QtWidgets.QPushButton):
    """Custom QT Flame Button Widget"""
    def __init__(self, 
                 text, 
                 connect, 
                 width=50, 
                 height=28, 
                 max_width=True, 
                 color=Color.GRAY, 
                 font=PYFLAME_FONT, 
                 font_size=PYFLAME_FONT_SIZE, 
                 tooltip=None):
        super(PyFlameButton, self).__init__()
        
        # Set text
        self.setText(text)
        
        # Set size
        if max_width:
            self.setMaximumWidth(16777215)
        else:
            self.setFixedSize(gui_resize(width), gui_resize(height))
        
        # Set button color
        self.set_button_color(color)
        
        # Set font
        self.setFont(QtGui.QFont(font, font_resize(font_size)))
        
        # Set tooltip
        if tooltip:
            self.setToolTip(tooltip)
        
        # Connect button
        self.clicked.connect(connect)
    
    def set_button_color(self, color):
        """Set the color of the button."""
        if color == Color.BLUE:
            gradient_start = Color.BLUE.value
            gradient_end = Color.BLUE_DARK.value
            hover_color = Color.BLUE_HIGHLIGHT.value
        else:
            gradient_start = Color.GRADIENT_START.value
            gradient_end = Color.GRADIENT_END.value
            hover_color = Color.GRAY_LIGHT.value
            
        self.setStyleSheet(f'''
            QPushButton {{
                color: {Color.BUTTON_TEXT.value};
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {gradient_start}, stop:1 {gradient_end});
                border: 1px solid {Color.BORDER.value};
                border-radius: 4px;
                padding: 4px 12px;
                min-height: 30px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {hover_color}, stop:1 {gradient_end});
                border: 1px solid {Color.ACCENT_BLUE};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Color.BLUE_DARK.value}, stop:1 {Color.BLUE.value});
                border: 1px solid {Color.WHITE.value};
            }}
            QPushButton:disabled {{
                color: rgb(120, 120, 120);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Color.GRAY_DARK.value}, stop:1 {Color.GRAY.value});
                border: 1px solid {Color.GRAY.value};
            }}
            QToolTip {{
                color: rgb(230, 230, 230);
                background-color: rgb(60, 60, 60);
                border: 1px solid {Color.ACCENT_BLUE};
                border-radius: 3px;
                padding: 5px;
            }}
        ''')

class PyFlameLabel(QtWidgets.QLabel):
    """Custom QT Flame Label Widget"""
    def __init__(self, 
                 text="", 
                 width=150, 
                 height=28, 
                 max_width=True,
                 font=PYFLAME_FONT,
                 font_size=PYFLAME_FONT_SIZE, 
                 tooltip=None):
        super(PyFlameLabel, self).__init__()
        
        # Set text
        self.setText(text)
        
        # Set size
        if max_width:
            self.setMaximumWidth(16777215)
        else:
            self.setFixedSize(gui_resize(width), gui_resize(height))
        
        # Set font
        self.setFont(QtGui.QFont(font, font_resize(font_size)))
        
        # Set tooltip
        if tooltip:
            self.setToolTip(tooltip)
        
        # Set style
        self.setStyleSheet(f'''
            QLabel {{
                color: {Color.TEXT.value};
                padding: 2px;
            }}
            QToolTip {{
                color: rgb(230, 230, 230);
                background-color: rgb(60, 60, 60);
                border: 1px solid {Color.ACCENT_BLUE};
                border-radius: 3px;
                padding: 5px;
            }}
        ''')

class PyFlameEntry(QtWidgets.QLineEdit):
    """Custom QT Flame Line Edit Widget"""
    def __init__(self, 
                 text="", 
                 width=150, 
                 height=28, 
                 max_width=True, 
                 read_only=False, 
                 align="left",
                 font=PYFLAME_FONT, 
                 font_size=PYFLAME_FONT_SIZE,
                 tooltip=None):
        super(PyFlameEntry, self).__init__()
        
        # Set text
        self.setText(text)
        
        # Set size
        if max_width:
            self.setMaximumWidth(16777215)
        else:
            self.setFixedSize(gui_resize(width), gui_resize(height))
        
        # Set font
        self.setFont(QtGui.QFont(font, font_resize(font_size)))
        
        # Set tooltip
        if tooltip:
            self.setToolTip(tooltip)
        
        # Set alignment
        if align == "center":
            self.setAlignment(QtCore.Qt.AlignCenter)
        elif align == "right":
            self.setAlignment(QtCore.Qt.AlignRight)
        else:
            self.setAlignment(QtCore.Qt.AlignLeft)
        
        # Set read-only state
        self.setReadOnly(read_only)
        
        # Set style based on read-only state
        if read_only:
            self.setStyleSheet(f'''
                QLineEdit {{
                    color: {Color.TEXT.value};
                    background-color: rgb(30, 30, 30);
                    selection-color: rgb(38, 38, 38);
                    selection-background-color: rgb(184, 177, 167);
                    border: 1px solid rgb(55, 55, 55);
                    border-radius: 3px;
                    padding: 3px 8px;
                    min-height: 28px;
                }}
                QToolTip {{
                    color: rgb(230, 230, 230);
                    background-color: rgb(60, 60, 60);
                    border: 1px solid {Color.ACCENT_BLUE};
                    border-radius: 3px;
                    padding: 5px;
                }}
            ''')
        else:
            self.setStyleSheet(f'''
                QLineEdit {{
                    color: {Color.TEXT.value};
                    background-color: rgb(45, 45, 45);
                    selection-color: rgb(38, 38, 38);
                    selection-background-color: rgb(184, 177, 167);
                    border: 1px solid rgb(65, 65, 65);
                    border-radius: 3px;
                    padding: 3px 8px;
                    min-height: 28px;
                }}
                QLineEdit:hover {{
                    border: 1px solid {Color.ACCENT_BLUE};
                    background-color: rgb(50, 50, 50);
                }}
                QLineEdit:focus {{
                    border: 1px solid {Color.BLUE.value};
                    background-color: rgb(55, 55, 55);
                }}
                QLineEdit:disabled {{
                    color: rgb(120, 120, 120);
                    background-color: rgb(35, 35, 35);
                }}
                QToolTip {{
                    color: rgb(230, 230, 230);
                    background-color: rgb(60, 60, 60);
                    border: 1px solid {Color.ACCENT_BLUE};
                    border-radius: 3px;
                    padding: 5px;
                }}
            ''')

class PyFlamePushButtonMenu(QtWidgets.QToolButton):
    """Custom QT Flame Push Button with Menu"""
    def __init__(self, 
                 text="", 
                 menu_options=None, 
                 connect=None, 
                 width=150, 
                 height=28, 
                 max_width=True,
                 icon=None, 
                 button_width=None, 
                 show_menu_indicator=True, 
                 tooltip=None,
                 enabled=True):
        super(PyFlamePushButtonMenu, self).__init__()
        
        # Set text
        self.setText(text)
        
        # Set size
        if max_width:
            self.setMaximumWidth(16777215)
        else:
            self.setFixedSize(gui_resize(width), gui_resize(height))
        
        # Set icon
        if icon:
            self.setIcon(icon)
        
        # Store the connect callback
        self.connect_callback = connect
        
        # Set enabled state
        self.setEnabled(enabled)
        
        # Set tooltip
        if tooltip:
            self.setToolTip(tooltip)
        
        # Set up menu - modified for better clickability in Flame 2023
        self.menu = QtWidgets.QMenu()
        self.menu.setFocusPolicy(QtCore.Qt.StrongFocus)  # Changed to StrongFocus
        self.setMenu(self.menu)
        
        # Use MenuButtonPopup instead of InstantPopup for better compatibility
        self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        
        # Add menu options
        if menu_options:
            self.add_menu_options(menu_options, connect)
        
        # Set font
        self.setFont(QtGui.QFont(PYFLAME_FONT, font_resize(PYFLAME_FONT_SIZE)))
        
        # Set style - modified for better clickability
        self.setStyleSheet(f'''
            QToolButton {{
                color: {Color.TEXT.value};
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Color.GRADIENT_START.value}, stop:1 {Color.GRADIENT_END.value});
                border: 1px solid {Color.BORDER.value};
                border-radius: 4px;
                padding-left: 10px;
                padding-right: {30 if show_menu_indicator else 10}px;
                text-align: left;
                min-height: 30px;
            }}
            QToolButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Color.GRAY_LIGHT.value}, stop:1 {Color.GRADIENT_END.value});
                border: 1px solid {Color.ACCENT_BLUE};
            }}
            QToolButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Color.BLUE_DARK.value}, stop:1 {Color.BLUE.value});
                border: 1px solid {Color.WHITE.value};
            }}
            QToolButton:disabled {{
                color: rgb(120, 120, 120);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {Color.GRAY_DARK.value}, stop:1 {Color.GRAY.value});
                border: 1px solid {Color.GRAY.value};
            }}
            QToolButton::menu-indicator {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                right: 8px;
                width: {16 if show_menu_indicator else 0}px;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iNiIgdmlld0JveD0iMCAwIDEwIDYiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNSA1TDkgMSIgc3Ryb2tlPSIjQUFBQUFBIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K);
            }}
            QToolTip {{
                color: rgb(230, 230, 230);
                background-color: rgb(60, 60, 60);
                border: 1px solid {Color.ACCENT_BLUE};
                border-radius: 3px;
                padding: 5px;
            }}
            QMenu {{
                color: {Color.TEXT.value};
                background-color: rgb(50, 50, 50);
                border: 1px solid {Color.BORDER.value};
                border-radius: 3px;
                margin: 2px;
            }}
            QMenu::item {{
                height: 28px;  /* Increased from 24px */
                padding: 4px 25px 4px 20px;  /* Increased padding */
                border: 1px solid transparent;
                margin: 2px; /* Increased from 1px */
            }}
            QMenu::item:selected {{
                color: {Color.WHITE.value};
                background-color: {Color.BLUE.value};
                border-radius: 2px;
            }}
            /* Make item area more visible when hovering */
            QMenu::item:hover {{
                border: 1px solid {Color.ACCENT_BLUE};
                background-color: {Color.BLUE.value};
                color: {Color.WHITE.value};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {Color.BORDER.value};
                margin: 4px 10px;
            }}
        ''')
        
        # Connect clicked signal to handle click events
        self.clicked.connect(self.button_clicked)
    
    def button_clicked(self):
        """Handle main button click to show menu"""
        # Show menu when button is clicked
        self.showMenu()
    
    def add_menu_options(self, menu_options, connect=None):
        """Add options to the menu - improved for clickability."""
        self.menu.clear()
        self.connect_callback = connect
        
        for option in menu_options:
            if option == '':
                self.menu.addSeparator()
            else:
                # Create an Action with an explicit object name
                action = QAction(option, self)
                action.setObjectName(f"action_{option}")
                
                # Connect with a more direct approach for older Qt versions
                action.triggered.connect(lambda checked=False, text=option: self.select_menu_item(text))
                
                # Make action more visible in styling
                self.menu.addAction(action)
    
    def select_menu_item(self, text):
        """Improved method to handle menu item selection."""
        self.setText(text)
        log_to_file(f"Menu item selected: {text}")
        
        # Call the callback if it exists
        if self.connect_callback:
            self.connect_callback()
    
    def menu_triggered(self, text, connect_function):
        """Legacy handler for menu triggering - kept for compatibility."""
        self.setText(text)
        if connect_function:
            connect_function()

class PyFlameDialogWindow(QtWidgets.QDialog):
    """Custom QT Flame Dialog Window"""
    def __init__(self, 
                 title="Dialog", 
                 width=400, 
                 height=200, 
                 grid_layout=True, 
                 grid_layout_columns=4, 
                 grid_layout_rows=3, 
                 line_color=LineColor.BLUE):
        super(PyFlameDialogWindow, self).__init__()
        
        # Set window properties
        self.setWindowTitle(title)
        
        # Increase base size by 50% before scaling
        self.setFixedSize(gui_resize(width * 1.5), gui_resize(height * 1.5))
        
        # Create main layout
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(20, 25, 20, 20)  # Increased top margin for colored line
        self.setLayout(self.main_layout)
        
        # Create grid layout if requested
        if grid_layout:
            self.grid_layout = QtWidgets.QGridLayout()
            self.grid_layout.setRowStretch(grid_layout_rows - 1, 1)
            self.grid_layout.setColumnStretch(grid_layout_columns - 1, 1)
            self.grid_layout.setSpacing(gui_resize(15))  # Increased spacing
            self.main_layout.addLayout(self.grid_layout)
        
        # Set window style with a nice gradient background
        self.setStyleSheet(f'''
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 rgb(42, 42, 42), 
                                           stop:1 rgb(32, 32, 32));
                border-radius: 5px;
            }}
            
            QLabel {{
                color: {Color.TEXT.value};
            }}
            
            /* Make sure the scrollbar looks nice too */
            QScrollBar:vertical {{
                background: rgb(45, 45, 45);
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:vertical {{
                background: rgb(80, 80, 80);
                min-height: 20px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: rgb(100, 100, 100);
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        ''')
        
        # Create colored line
        self.line_color = line_color
        
    def paintEvent(self, event):
        """Paint the colored line on the dialog window."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Draw the top colored line
        line_pen = QtGui.QPen(self.line_color.value, 3)
        painter.setPen(line_pen)
        painter.drawLine(0, 0, self.width(), 0)
        
        # Draw a subtle gradient header area
        header_gradient = QtGui.QLinearGradient(0, 0, 0, 15)
        header_gradient.setColorAt(0, QtGui.QColor(60, 60, 60, 150))
        header_gradient.setColorAt(1, QtGui.QColor(50, 50, 50, 0))
        painter.fillRect(QtCore.QRect(0, 0, self.width(), 15), header_gradient)

# Configuration file location
CONFIG_FILE = "/opt/Autodesk/shared/python/flame_comfyui_config.json"

# Default configuration values
DEFAULT_CONFIG = {
    "comfyui_url": "http://127.0.0.1:8188",
    "input_dir": os.path.expanduser("~/comfyui/output/flacom"),
    "output_dir": os.path.expanduser("~/comfyui/output"),
    "workflows_dir": "/opt/Autodesk/shared/python/workflows",
    "temp_dir": "/tmp/flame_comfyui"
}

# Load configuration from file or use defaults
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

# Load configuration at startup
CONFIG = load_config()

# Constants - now using values from config
COMFYUI_URL = CONFIG["comfyui_url"]
TEMP_DIR = CONFIG["temp_dir"]
COMFYUI_OUTPUT_DIR = CONFIG["output_dir"]
COMFYUI_FLACOM_DIR = CONFIG["input_dir"]
WORKFLOWS_DIR = CONFIG["workflows_dir"]
WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "flacom_rembg_comfla_api_workflow.json")
COMFYUI_INPUT_DIR = COMFYUI_FLACOM_DIR

# Define PYFLAME_AVAILABLE as True since we're including the components directly
PYFLAME_AVAILABLE = True

# Create required directories if they don't exist
for directory in [TEMP_DIR, COMFYUI_FLACOM_DIR]:
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except Exception as e:
            pass

# Ensure workflow directory exists
if not os.path.exists(WORKFLOWS_DIR):
    try:
        os.makedirs(WORKFLOWS_DIR)
    except Exception as e:
        pass

# Main log function to record all operations
def log_to_file(message):
    """Write a message to log file"""
    log_path = "/tmp/flame_comfyui_final.log"
    try:
        with open(log_path, "a") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

# Initialize log
try:
    with open("/tmp/flame_comfyui_final.log", "w") as f:
        f.write("""
__  ___             ___     _              
\ \/ / |_ _____   _|_ _|___(_) ___  _ __   
 \  /| __/ _ \ \ / /| |/ __| |/ _ \| '_ \  
 /  \| ||  __/\ V / | |\__ \ | (_) | | | | 
/_/\_\\__ \___| \_/ |___|___/_|\___/|_| |_|  

  ____                 __       _   _ ___           _____ _                       
 / ___|___  _ __ ___  / _|_   _| | | |_ _|         |  ___| | __ _ _ __ ___   ___  
| |   / _ \| '_ ` _ \| |_| | | | | | || |   _____  | |_  | |/ _` | '_ ` _ \ / _ \ 
| |__| (_) | | | | | |  _| |_| | |_| || |  |_____| |  _| | | (_| | | | | | |  __/ 
 \____\___/|_| |_| |_|_|  \__, |\___/|___|         |_|   |_|\__,_|_| |_| |_|\___| 
                          |___/                                                            

__     _________  __  ____  _            _ _            
\ \   / /  ___\ \/ / |  _ \(_)_ __   ___| (_)_ __   ___ 
 \ \ / /| |_   \  /  | |_) | | '_ \ / _ \ | | '_ \ / _ \\
  \ V / |  _|  /  \  |  __/| | |_) |  __/ | | | | |  __/
   \_/  |_|   /_/\_\ |_|   |_| .__/ \___|_|_|_| |_|\___|
                             |_|                        
""")
        f.write("\n=== ComfyUI Hook Log ===\n")
        f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
except:
    pass

# Log that the module was loaded
log_to_file("Hook module loaded with embedded PyFlame UI components")

# Show message in Flame using different available methods
def show_flame_message(message):
    """Try different methods to display a message in Flame"""
    log_to_file(f"Attempting to show message: {message}")
    
    """Robust message display with API version detection"""
    try:
        # Modern API (2025+)
        if hasattr(flame, 'show_message'):
            flame.show_message("ComfyUI Export", message)
        # Legacy API
        elif hasattr(flame, 'execute_command'):
            flame.execute_command(f'echo "{message}"')
        else:
            log_to_file(f"MESSAGE: {message}")
    except Exception as e:
        log_to_file(f"Message error: {str(e)}")

    try:
        # Method 1: flame.message() (newer versions)
        if hasattr(flame, 'message'):
            log_to_file("Using flame.message()")
            flame.message(message)
            return True
    except Exception as e:
        log_to_file(f"Error with flame.message(): {str(e)}")
    
    try:        
        # Method 2: flame.execute_command() with proper syntax
        if hasattr(flame, 'execute_command'):
            log_to_file("Using flame.execute_command()")
            # Format the command as a shell command that displays text
            command = f"echo '{message}'"
            flame.execute_command(command, shell=True)
            return True
    except Exception as e:
        log_to_file(f"Error with flame.execute_command(): {str(e)}")
    
    try:
        # Method 3: PyDialog if available
        if hasattr(flame, 'PyDialog'):
            log_to_file("Using flame.PyDialog")
            dialog = flame.PyDialog()
            dialog.warning(message)
            return True
    except Exception as e:
        log_to_file(f"Error with flame.PyDialog: {str(e)}")
        
    try:
        # Method 4: Use PyNote if available
        if hasattr(flame, 'PyNote'):
            log_to_file("Using flame.PyNote")
            note = flame.PyNote("ComfyUI Message", message)
            return True
    except Exception as e:
        log_to_file(f"Error with flame.PyNote: {str(e)}")
        
    try:
        # Method 5: Use PyCallback if available
        if hasattr(flame, 'PyCallback'):
            log_to_file("Using flame.PyCallback with popup")
            def show_popup():
                print(f"POPUP: {message}")
            flame.PyCallback(show_popup)
            return True
    except Exception as e:
        log_to_file(f"Error with flame.PyCallback: {str(e)}")
    
    # Method 6: print to console and log (fallback)
    log_to_file("No suitable message display method found. Using print.")
    print(f"FLAME COMFYUI MESSAGE: {message}")
    return False

# Export frames from Flame clip to ComfyUI's expected directory
def export_frame(source, output_path):
    """Export frames from the selected clip directly to ComfyUI's input directory."""
    try:
        log_to_file(f"Exporting frames from: {source.name}")

        # Use ComfyUI's expected input directory
        clip_dir = COMFYUI_FLACOM_DIR
        log_to_file(f"Exporting directly to ComfyUI input directory: {clip_dir}")
        
        # Clear previous files to avoid confusion
        try:
            for old_file in os.listdir(clip_dir):
                old_path = os.path.join(clip_dir, old_file)
                if os.path.isfile(old_path):
                    os.remove(old_path)
                    log_to_file(f"Removed old file: {old_path}")
            log_to_file("Cleared directory for new export")
        except Exception as e:
            log_to_file(f"Error clearing directory: {str(e)}")
        
        if not os.path.exists(clip_dir):
            os.makedirs(clip_dir)
            log_to_file(f"Created ComfyUI input directory: {clip_dir}")
        
        # Create a duplicate clip to work with
        duplicate_clip = flame.duplicate(source)
        output_file = None
        
        try:
            # Get preset path for JPEG export
            try:
                preset_dir = flame.PyExporter.get_presets_dir(
                    flame.PyExporter.PresetVisibility.Autodesk,
                    flame.PyExporter.PresetType.Image_Sequence)
                jpeg_preset = os.path.join(preset_dir, "Jpeg", "Jpeg (8-bit).xml")
                
                if not os.path.exists(jpeg_preset):
                    preset_dir = "/opt/Autodesk/presets/2025.2.1/export/presets/flame/file_sequence"
                    jpeg_preset = os.path.join(preset_dir, "Jpeg", "Jpeg (8-bit).xml")
                    
                if not os.path.exists(jpeg_preset):
                    # Try to find any image preset
                    log_to_file("JPEG preset not found, searching for alternatives...")
                    for format_dir in ["Tiff", "OpenEXR", "DPX", "Targa"]:
                        test_path = os.path.join(preset_dir, format_dir)
                        if os.path.exists(test_path):
                            presets = [f for f in os.listdir(test_path) if f.endswith('.xml')]
                            if presets:
                                jpeg_preset = os.path.join(test_path, presets[0])
                                log_to_file(f"Using alternative preset: {jpeg_preset}")
                                break
                
                log_to_file(f"Using preset: {jpeg_preset}")
            except Exception as e:
                log_to_file(f"Error finding preset: {str(e)}")
                # Try hardcoded path as last resort
                jpeg_preset = "/opt/Autodesk/presets/2025.2.1/export/presets/flame/file_sequence/Jpeg/Jpeg (8-bit).xml"
                log_to_file(f"Falling back to hardcoded preset path: {jpeg_preset}")
            
            # Export the frame
            exporter = flame.PyExporter()
            exporter.foreground = True
            
            # Export all frames - don't restrict to marks
            exporter.export_between_marks = False 
            
            # Use a simplified basename for consistent sequence naming
            # VHS_LoadImagesPath expects a consistent pattern
            result = exporter.export(duplicate_clip, jpeg_preset, clip_dir)
            log_to_file(f"Export result: {result}")
            
            # Check if any images were exported
            files = [f for f in os.listdir(clip_dir) if f.endswith(('.jpg', '.jpeg', '.dpx', '.exr', '.png', '.tif', '.tiff'))]
            
            if files:
                log_to_file(f"Successfully exported {len(files)} files to {clip_dir}")
                log_to_file(f"Files: {files[:5]}... (showing first 5)")
                
                # Get the first file for starting ComfyUI processing
                files.sort()
                first_image = os.path.join(clip_dir, files[0])
                log_to_file(f"First image: {first_image}")
                
                return True, first_image
            else:
                log_to_file("No files were exported, trying alternative method")
            
            # If standard export fails, try creating a sequence of frames
            # using alternative methods
            log_to_file("Trying alternative frame export...")
            
            # Try alternative extraction - use appropriate range
            if hasattr(source.duration, 'frame'):
                end_frame = source.duration.frame
            elif isinstance(source.duration, str):
                log_to_file(f"Duration is a string: {source.duration}, using 10 frames")
                end_frame = 10
            else:
                try:
                    end_frame = int(source.duration)
                except:
                    end_frame = 10
            
            # Try alternative export method specifically for sequences
            extract_sequence_for_vhs(clip_dir, duplicate_clip, 1, end_frame)
            
            # Check again for exported files
            files = [f for f in os.listdir(clip_dir) if f.endswith(('.jpg', '.jpeg', '.dpx', '.exr', '.png', '.tif', '.tiff'))]
            
            if files:
                log_to_file(f"Alternative method exported {len(files)} files")
                files.sort()
                first_image = os.path.join(clip_dir, files[0])
                return True, first_image
                
            # Last resort - create at least one image
            log_to_file("Creating a blank image as last resort")
            blank_path = os.path.join(clip_dir, "frame_0001.jpg")
            
            try:
                # Create a simple blank image with PIL
                image = Image.new('RGB', (1920, 1080), color=(0, 0, 0))
                image.save(blank_path)
                log_to_file(f"Created blank image: {blank_path}")
                return True, blank_path
            except Exception as e:
                log_to_file(f"Error creating blank image: {str(e)}")
            
            return False, None
            
        except Exception as e:
            log_to_file(f"Error during export: {str(e)}")
            log_to_file(traceback.format_exc())
            show_flame_message("Export failed\nCheck log")
            return False, None
            
        finally:
            # Clean up the duplicate clip
            try:
                flame.delete(duplicate_clip)
            except Exception as e:
                log_to_file(f"Error deleting duplicate clip: {str(e)}")
                
    except Exception as e:
        log_to_file(f"Error in export_frame: {str(e)}")
        log_to_file(traceback.format_exc())
        show_flame_message("Export failed\nCheck log")
        return False, None

# New function optimized for VHS_LoadImagesPath
def extract_sequence_for_vhs(output_dir, clip, start_frame, end_frame):
    """Extract a sequence of frames optimized for VHS_LoadImagesPath"""
    log_to_file(f"Extracting sequence for VHS: frames {start_frame} to {end_frame}")
    
    # Make sure we use a consistent naming pattern that VHS can read
    # VHS likes simple, sequential numbering
    frame_pattern = "frame_%04d.jpg"
    
    try:
        # Set up the exporter 
        exporter = flame.PyExporter()
        exporter.foreground = True
        
        # Get JPEG preset
        preset_dir = flame.PyExporter.get_presets_dir(
            flame.PyExporter.PresetVisibility.Autodesk,
            flame.PyExporter.PresetType.Image_Sequence)
        jpeg_preset = os.path.join(preset_dir, "Jpeg", "Jpeg (8-bit).xml")
        
        # Export the whole clip - don't constrain to marks
        log_to_file(f"Exporting frames to: {output_dir}")
        
        # Simple direct export
        result = exporter.export(clip, jpeg_preset, output_dir)
        log_to_file(f"Export result: {result}")
        
        # Check the results
        files = [f for f in os.listdir(output_dir) if f.endswith(('.jpg', '.jpeg', '.dpx', '.exr', '.png', '.tif', '.tiff'))]
        log_to_file(f"Exported {len(files)} frames")
        
        if not files:
            # Try an alternative method - export frame by frame
            log_to_file("No files exported. Trying frame-by-frame export...")
            
            # Export each frame separately
            max_frames = min(end_frame, 10)  # Limit to 10 frames max
            
            for frame in range(start_frame, max_frames + 1):
                try:
                    # Try to export a single frame
                    frame_exporter = flame.PyExporter()
                    frame_exporter.foreground = True
                    
                    # Set marks to export only this frame
                    clip.in_mark = frame
                    clip.out_mark = frame
                    frame_exporter.export_between_marks = True
                    
                    # Export with specific filename
                    frame_path = os.path.join(output_dir, frame_pattern % frame)
                    result = frame_exporter.export(clip, jpeg_preset, output_dir)
                    log_to_file(f"Frame {frame} export result: {result}")
                except Exception as e:
                    log_to_file(f"Error exporting frame {frame}: {str(e)}")
        
        # Check if we have files now
        new_files = [f for f in os.listdir(output_dir) if f.endswith(('.jpg', '.jpeg', '.dpx', '.exr', '.png', '.tif', '.tiff'))]
        
        if new_files:
            # Rename files to ensure consistent sequence format
            for i, file in enumerate(sorted(new_files)):
                try:
                    old_path = os.path.join(output_dir, file)
                    new_name = frame_pattern % (i + 1)
                    new_path = os.path.join(output_dir, new_name)
                    
                    if file != new_name:  # Only rename if needed
                        os.rename(old_path, new_path)
                        log_to_file(f"Renamed {file} to {new_name}")
                except Exception as e:
                    log_to_file(f"Error renaming {file}: {str(e)}")
    
    except Exception as e:
        log_to_file(f"Error in extract_sequence_for_vhs: {str(e)}")
        log_to_file(traceback.format_exc())

# Function to process with ComfyUI API - updated for workflow loading
def process_with_comfyui_api(image_path, output_dir, workflow_path=None):
    """Process an image sequence with ComfyUI API"""
    try:
        log_to_file(f"Processing sequence with ComfyUI. First image: {image_path}")
        
        if not is_comfyui_running():
            log_to_file("ComfyUI server is not running")
            return None
        
        # Use the provided workflow path or default path
        workflow = load_workflow(workflow_path)
        
        if not workflow:
            # Try looking for any workflow in the directory
            if os.path.exists(WORKFLOWS_DIR):
                workflows = [f for f in os.listdir(WORKFLOWS_DIR) if f.endswith('.json')]
                if workflows:
                    workflow_path = os.path.join(WORKFLOWS_DIR, workflows[0])
                    log_to_file(f"Trying alternative workflow: {workflow_path}")
                    workflow = load_workflow(workflow_path)
            
            if not workflow:
                log_to_file(f"Error: No valid workflow found in {WORKFLOWS_DIR}")
                show_flame_message(f"Error: No valid workflow found in {WORKFLOWS_DIR}")
                
                # Let's create a basic workflow as a last resort
                workflow = {
                    "4": {
                        "inputs": {
                            "torchscript_jit": "default",
                            "image": ["5", 0]
                        },
                        "class_type": "InspyrenetRembg",
                        "_meta": {"title": "Inspyrenet Rembg"}
                    },
                    "5": {
                        "inputs": {
                            "directory": "output/flacom/",
                            "image_load_cap": 0,
                            "skip_first_images": 0,
                            "select_every_nth": 1
                        },
                        "class_type": "VHS_LoadImagesPath",
                        "_meta": {"title": "Load Images (Path) 🎥🅥🅗🅢"}
                    },
                    "13": {
                        "inputs": {
                            "filename_prefix": "comfla/img",
                            "images": ["4", 0]
                        },
                        "class_type": "SaveImage",
                        "_meta": {"title": "Save Image"}
                    }
                }
                
                log_to_file("Created inline workflow as last resort")
                
        job_id = str(uuid.uuid4())
        log_to_file(f"Job ID: {job_id}")
        
        # Ensure directory exists in ComfyUI path
        if not os.path.exists(COMFYUI_FLACOM_DIR):
            os.makedirs(COMFYUI_FLACOM_DIR)
            log_to_file(f"Created directory: {COMFYUI_FLACOM_DIR}")
        
        # Check how many frames we have 
        files = [f for f in os.listdir(COMFYUI_FLACOM_DIR) if f.endswith(('.jpg', '.jpeg', '.dpx', '.exr', '.png', '.tif', '.tiff'))]
        log_to_file(f"Processing {len(files)} frames in {COMFYUI_FLACOM_DIR}")

        # Find and update the VHS_LoadImagesPath node in the workflow
        vhs_node_found = False
        for node_id, node in workflow.items():
            if node.get("class_type") == "VHS_LoadImagesPath":
                # Make sure the directory matches where we exported the frames
                node["inputs"]["directory"] = "output/flacom"
                log_to_file(f"Updated VHS_LoadImagesPath node with directory: output/flacom")
                vhs_node_found = True
                break

        # Look for SaveImage node to determine output location
        save_node_found = False
        save_prefix = "comfla/img"  # Default prefix
        
        for node_id, node in workflow.items():
            if node.get("class_type") == "SaveImage":
                save_node_found = True
                if "inputs" in node and "filename_prefix" in node["inputs"]:
                    save_prefix = node["inputs"]["filename_prefix"]
                    log_to_file(f"Found SaveImage node with prefix: {save_prefix}")
                break

        log_to_file(f"Will look for output images with prefix: {save_prefix}")
        
        if not vhs_node_found:
            log_to_file("ERROR: No VHS_LoadImagesPath node found in workflow!")
            show_flame_message("Workflow does not have the required VHS_LoadImagesPath node")
            return None
            
        # Create API request
        api_request = {
            "prompt": workflow,
            "client_id": f"flame_comfyui_{job_id}"
        }

        # Send request
        request_data = json.dumps(api_request)
        
        curl_cmd = [
            'curl', '-s', 
            '-X', 'POST', 
            f'{COMFYUI_URL}/prompt', 
            '-H', 'Content-Type: application/json', 
            '-d', request_data
        ]
        
        # Execute the curl command
        try:
            log_to_file(f"Running command: curl -X POST {COMFYUI_URL}/prompt ...")
            result = subprocess.run(curl_cmd, capture_output=True, text=True)
            
            log_to_file(f"Command stdout: {result.stdout}")
            if result.stderr:
                log_to_file(f"Command stderr: {result.stderr}")
                
            if result.returncode != 0:
                log_to_file(f"Error submitting workflow: Return code {result.returncode}")
                if result.stderr:
                    log_to_file(f"Error details: {result.stderr}")
                return None
                
            if not result.stdout.strip():
                log_to_file("Empty response from ComfyUI server")
                return None
                
            try:
                response = json.loads(result.stdout)
                prompt_id = response.get('prompt_id')
                
                if not prompt_id:
                    log_to_file("No prompt_id in response")
                    log_to_file(f"Full response: {response}")
                    return None
                    
                log_to_file(f"Prompt ID: {prompt_id}")
                
                # Wait for job completion - INCREASED TIMEOUT
                max_retries = 9000  # 10 minutes (up from 180 seconds)
                retry_count = 0
                
                while retry_count < max_retries:
                    time.sleep(1)
                    
                    # Only log every 10th check to reduce log verbosity
                    if retry_count % 10 == 0:
                        log_to_file(f"Checking status: retry {retry_count+1}/{max_retries}")
                    
                    check_cmd = ['curl', '-s', f'{COMFYUI_URL}/history/{prompt_id}']
                    result = subprocess.run(check_cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        log_to_file(f"Error checking status: {result.stderr}")
                        retry_count += 1
                        continue

                    try:
                        history = json.loads(result.stdout)
                        
                        if prompt_id in history:
                            # Check if outputs contain images
                            outputs = history[prompt_id].get('outputs', {})
                            
                            for node_id, output in outputs.items():
                                if 'images' in output:
                                    images = output['images']
                                    
                                    if images:
                                        # Return the first image as our result
                                        image_data = images[0]
                                        image_filename = image_data.get('filename')
                                        
                                        if image_filename:
                                            output_path = os.path.join(COMFYUI_OUTPUT_DIR, image_filename)
                                            
                                            if os.path.exists(output_path):
                                                log_to_file(f"Found processed image at: {output_path}")
                                                return output_path
                                            
                                            # Try to download if not found directly
                                            local_output_path = os.path.join(output_dir, image_filename)
                                            image_url = f"{COMFYUI_URL}/view?filename={image_filename}&type=output"
                                            download_cmd = ['curl', '-s', '-o', local_output_path, image_url]
                                            
                                            dl_result = subprocess.run(download_cmd, capture_output=True)
                                            
                                            if dl_result.returncode == 0 and os.path.exists(local_output_path):
                                                log_to_file(f"Image saved to: {local_output_path}")
                                                return local_output_path
                    
                    except json.JSONDecodeError:
                        log_to_file("Invalid JSON in history response")
                    
                    retry_count += 1
                
                # We've timed out, but let's check for output files directly
                log_to_file("Timed out waiting for ComfyUI, checking for output files directly")
                
                # Look specifically for PNG files with the pattern from the SaveImage node
                comfla_dir = os.path.join(COMFYUI_OUTPUT_DIR, "comfla")
                if os.path.exists(comfla_dir):
                    png_files = [f for f in os.listdir(comfla_dir) if f.endswith('.png') and f.startswith('img_')]
                    if png_files:
                        log_to_file(f"Found {len(png_files)} PNG files with alpha in {comfla_dir}")
                        # Return the directory path
                        return comfla_dir
                
                # No files found
                log_to_file(f"No output files found in {comfla_dir}")
                return None
                
            except json.JSONDecodeError as e:
                log_to_file(f"Error parsing JSON response: {str(e)}")
                log_to_file(f"Raw response: {result.stdout}")
                return None
            
        except Exception as e:
            log_to_file(f"Error processing with ComfyUI: {str(e)}")
            return None
            
    except Exception as e:
        log_to_file(f"Error in process_with_comfyui_api: {str(e)}")
        return None

# Functions for importing images back into Flame
def check_or_create_reel():
    """Check for existing reel or create new one"""
    try:
        # Access the current workspace
        workspace = flame.project.current_project.current_workspace
        reel_names = [reel.name for reel_group in workspace.desktop.reel_groups for reel in reel_group.reels]

        if reel_names:
            reel_name = reel_names[0]
            log_to_file(f"Using existing reel: {reel_name}")
            return workspace.desktop.reel_groups[0].reels[0]  # Return actual reel object
        else:
            user_input = flame.ask("No Reels Found", "No reels exist. Please enter a name for the new reel:", ["Create"])
            if user_input:
                new_reel_name = user_input
                # Create reel in first reel group
                new_reel = workspace.desktop.reel_groups[0].create_reel(new_reel_name)
                log_to_file(f"Created new reel: {new_reel_name}")
                return new_reel
            else:
                log_to_file("User did not provide a reel name.")
                return None
    except Exception as e:
        log_to_file(f"Error in check_or_create_reel: {str(e)}")
        return None

def import_sequence_to_flame(directory_path):
    """Import a sequence of images into Flame"""
    log_to_file(f"Importing image sequence from: {directory_path}")
    
    try:
        # Check if directory exists
        if not os.path.exists(directory_path):
            log_to_file(f"Directory does not exist: {directory_path}")
            return False
        
        # Get all image files in directory
        files = [f for f in os.listdir(directory_path) if f.endswith(('.jpg', '.jpeg', '.dpx', '.exr', '.png', '.tif', '.tiff'))]
        
        if not files:
            log_to_file(f"No image files found in {directory_path}")
            return False
            
        # Sort files to ensure proper sequence
        files.sort()
        log_to_file(f"Found {len(files)} files to import")
        
        # Get access to a reel
        reel = check_or_create_reel()
        if not reel:
            log_to_file("Failed to get or create a reel")
            return False
            
        # Create full paths for each file
        file_paths = [os.path.join(directory_path, f) for f in files]
        
        # Progress dialog
        if hasattr(flame, 'create_progress_dialog'):
            progress = flame.create_progress_dialog("Importing Sequence", len(file_paths))
        else:
            progress = None
            
        # Import files - try different methods based on what's available
        try:
            if hasattr(flame, 'import_clips'):
                # Method 1: Using import_clips function if available
                log_to_file("Using flame.import_clips method")
                
                # Import the first file to see if it works
                result = flame.import_clips(file_paths[0], reel)
                log_to_file(f"Import result: {result}")
                
                if result:
                    # Import the rest of the files
                    for i, path in enumerate(file_paths[1:], 1):
                        if progress:
                            progress.set_progress(i)
                            progress.set_message(f"Importing {os.path.basename(path)}")
                            
                        flame.import_clips(path, reel)
                        
                    if progress:
                        progress.close()
                    return True
                    
            # Method 2: Using media import
            if hasattr(flame, 'media_panel_import'):
                log_to_file("Using flame.media_panel_import method")
                flame.media_panel_import(file_paths, reel)
                return True
                
            # Method 3: Using simpler import method
            if hasattr(flame, 'import_media'):
                log_to_file("Using flame.import_media method")
                flame.import_media(file_paths, reel)
                return True
                
            # Method 4: Last resort using batch script
            log_to_file("Using batch script import method")
            with open(os.path.join(directory_path, "import_script.batch"), "w") as f:
                for path in file_paths:
                    f.write(f"import {path}\n")
                    
            show_flame_message(f"Created import script at {os.path.join(directory_path, 'import_script.batch')}\nPlease load this in Flame to import the sequence.")
            return True
            
        except Exception as e:
            log_to_file(f"Error during import: {str(e)}")
            log_to_file(traceback.format_exc())
            return False
        finally:
            if progress:
                progress.close()
            
    except Exception as e:
        log_to_file(f"Error in import_sequence_to_flame: {str(e)}")
        log_to_file(traceback.format_exc())
        return False

# Updated process_with_comfyui function to import results
def process_with_comfyui(selection):
    """Process selected clips with ComfyUI and import results"""
    log_to_file(f"process_with_comfyui called with {len(selection)} items")
    
    # First check for existing files
    if not check_existing_outputs():
        log_to_file("User cancelled due to existing files")
        return
    
    # Show workflow selection dialog
    selected_workflow_path = show_workflow_selection_dialog()
    if selected_workflow_path is None:
        log_to_file("Workflow selection cancelled or no workflow selected")
        show_flame_message("Processing cancelled - no workflow selected")
        return
    
    # Load the selected workflow
    workflow = load_workflow(selected_workflow_path)
    if not workflow:
        log_to_file(f"Failed to load workflow: {selected_workflow_path}")
        show_flame_message(f"Failed to load workflow: {os.path.basename(selected_workflow_path)}")
        return
    
    # Check for text input nodes and show dialog if needed
    text_nodes = detect_text_input_nodes(workflow)
    if text_nodes:
        workflow_name = get_workflow_name(selected_workflow_path)
        text_values = show_text_input_dialog(text_nodes, workflow_name)
        
        if text_values is None:
            log_to_file("Text input dialog cancelled")
            show_flame_message("Processing cancelled - text input dialog closed")
            return
        
        # Update workflow with text inputs
        workflow = update_workflow_with_text_inputs(workflow, text_values)
    
    try:
        if not selection:
            show_flame_message("No items selected")
            return
            
        # Get the first selected clip or segment
        item = selection[0]
        log_to_file(f"Selected item: {item.name}")
        
        # Create unique job directory
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(TEMP_DIR, job_id)
        
        try:
            os.makedirs(job_dir)
            log_to_file(f"Created job directory: {job_dir}")
        except Exception as e:
            log_to_file(f"Error creating job directory: {str(e)}")
            show_flame_message(f"Error creating temp directory: {str(e)}")
            return
        
        # Check if ComfyUI is running
        if not is_comfyui_running():
            log_to_file("ComfyUI server is not running")
            show_flame_message("Error: ComfyUI server is not running at " + COMFYUI_URL)
            return
            
        # Export frames from clip - now returns the path to the first image
        export_successful, image_path = export_frame(item, job_dir)
        
        if not export_successful or not image_path:
            log_to_file("Failed to export frames from clip")
            show_flame_message("Failed to export frames from clip")
            return
        
        log_to_file(f"Image exported to: {image_path}")
        show_flame_message("Starting ComfyUI processing in background...")
        
        # Create a callback function for the background process
        def background_process():
            try:
                # Process with ComfyUI using the workflow
                # Pass the loaded workflow directly instead of the path
                output_path = process_with_comfyui_api_with_workflow(image_path, job_dir, workflow)

                # After processing with ComfyUI:
                comfla_dir = os.path.join(COMFYUI_OUTPUT_DIR, "comfla")
                
                # Check if directory exists and has any files - improved error handling
                if os.path.exists(comfla_dir):
                    png_files = [f for f in os.listdir(comfla_dir) if f.endswith('.png')]
                    if png_files:
                        log_to_file(f"Found {len(png_files)} PNG files in {comfla_dir}")
                        try:
                            # Create a callback for importing the results
                            def import_results():
                                try:
                                    import_result = import_png_sequence(selection)
                                    if import_result:
                                        show_flame_message("Successfully imported PNG sequence!")
                                    else:
                                        show_flame_message("Failed to import PNG sequence.")
                                except Exception as e:
                                    log_to_file(f"Error in import callback: {str(e)}")
                                    show_flame_message(f"Error during import: {str(e)}")
                            
                            # Use PyCallback to run import on main thread
                            if hasattr(flame, 'PyCallback'):
                                flame.PyCallback(import_results)
                            else:
                                # Fallback to direct call if PyCallback not available
                                import_results()
                            
                        except Exception as e:
                            log_to_file(f"Error scheduling import: {str(e)}")
                            show_flame_message(f"Error scheduling import: {str(e)}")
                    else:
                        show_flame_message("No PNG files found in output directory")
                        log_to_file(f"Directory exists but no PNG files found in {comfla_dir}")
                else:
                    show_flame_message("Output directory not found. Processing may have failed.")
                    log_to_file(f"Output directory not found: {comfla_dir}")
                    
            except Exception as e:
                log_to_file(f"Error in background process: {str(e)}")
                log_to_file(traceback.format_exc())
                show_flame_message(f"Error during processing: {str(e)}")
        
        # Create and start background thread
        background_thread = threading.Thread(target=background_process)
        background_thread.daemon = True  # Make thread daemon so it doesn't block program exit
        background_thread.start()
        
        show_flame_message("Processing started in background.\nYou can continue working while ComfyUI processes your frames.")
        
    except Exception as e:
        log_to_file(f"Error in process_with_comfyui: {str(e)}")
        log_to_file(traceback.format_exc())
        show_flame_message(f"Error: {str(e)}")

# Function to determine when the action should be visible
def scope_clip(selection):
    """Check if the selected items can be processed."""
    log_to_file(f"scope_clip called with selection={selection}")
    try:
        import flame
        log_to_file("Successfully imported flame in scope_clip")
        
        for item in selection:
            log_to_file(f"Checking item: {item}")
            log_to_file(f"Item type: {type(item)}")
            
            # Check if this is a clip or something that can be treated as an image
            if hasattr(item, 'name'):  # Basic test for a valid item
                log_to_file(f"Item has name attribute, returning True")
                return True
        
        log_to_file("No valid clips or segments found, returning False")
        return False
    except Exception as e:
        log_to_file(f"Error in scope_clip: {str(e)}")
        return False

# Helper function for debug logging
def debug_log(message):
    """Alias for log_to_file for debugging purposes"""
    log_to_file(message)

# The main hook function
def get_media_panel_custom_ui_actions():
    """Hook to add custom actions to Flame's Media Panel context menu."""
    debug_log("get_media_panel_custom_ui_actions called")
    
    # Return the custom actions definition
    return [
        {
            "name": "ComfyUI",
            "actions": [
                {
                    "name": "Process with ComfyUI",
                    "isVisible": scope_clip,
                    "execute": process_with_comfyui,
                    "isEnabled": True,
                    "minimize": False
                }
            ]
        }
    ]

# Add this function somewhere before it's called
def is_comfyui_running():
    """Always return True since ComfyUI is confirmed to be running"""
    return True
# For testing outside of Flame
if __name__ == "__main__":
    print("Flame ComfyUI Hook - Test Mode")
    print(f"ComfyUI URL: {COMFYUI_URL}")
    print(f"ComfyUI is running: {is_comfyui_running()}")
    print(f"ComfyUI Input Dir: {COMFYUI_INPUT_DIR}")
    print(f"ComfyUI Output Dir: {COMFYUI_OUTPUT_DIR}")
    print("Copy this file to /opt/Autodesk/shared/python/")
    print("Then reload hooks in Flame using Shift-Control-H-P")



def log_flame_methods():
    """Log available methods in the flame module for debugging."""
    log_to_file("Available methods in flame module:")
    for method in dir(flame):
        log_to_file(method)

# Call this function at the start of your script to log available methods
log_flame_methods()

# Load the workflow from the JSON file - fixed to use absolute paths properly
def load_workflow(workflow_path=None):
    """
    Load workflow from JSON file.
    If workflow_path is provided, loads that specific workflow.
    Otherwise, uses the most recent workflow file in the workflows directory.
    """
    try:
        # Check if workflows directory exists
        if not os.path.exists(WORKFLOWS_DIR):
            log_to_file(f"Creating workflows directory: {WORKFLOWS_DIR}")
            os.makedirs(WORKFLOWS_DIR)
        
        # If specific workflow path is provided, use it
        if workflow_path and os.path.exists(workflow_path):
            log_to_file(f"Loading specific workflow: {workflow_path}")
            with open(workflow_path, 'r') as f:
                workflow_data = json.load(f)
                log_to_file(f"Successfully loaded workflow with {len(workflow_data)} nodes")
                return workflow_data
        
        # Otherwise get all .json files in the directory
        workflow_files = [f for f in os.listdir(WORKFLOWS_DIR) if f.endswith('.json')]
        
        if not workflow_files:
            log_to_file("No workflow files found!")
            return None
            
        # Use the most recently modified workflow file
        workflow_files.sort(key=lambda x: os.path.getmtime(os.path.join(WORKFLOWS_DIR, x)), reverse=True)
        latest_workflow = os.path.join(WORKFLOWS_DIR, workflow_files[0])
        
        log_to_file(f"Loading most recent workflow: {latest_workflow}")
        
        with open(latest_workflow, 'r') as f:
            workflow_data = json.load(f)
            log_to_file(f"Successfully loaded workflow with {len(workflow_data)} nodes")
            return workflow_data
            
    except Exception as e:
        log_to_file(f"Error loading workflow: {str(e)}")
        log_to_file(traceback.format_exc())
        return None

# Updated function to import PNG files as a sequence
def get_project_framerate():
    """Detect the current project's framerate"""
    try:
        import flame
        # Try to get the current project's framerate
        project = flame.project
        if project:
            framerate = project.framerate
            log_to_file(f"Detected project framerate: {framerate}")
            return framerate
    except Exception as e:
        log_to_file(f"Error detecting project framerate: {str(e)}")
    
    # Default fallback
    log_to_file("Using default framerate: 50")
    return 50.0  # Default to 50fps as mentioned by user

def import_comfyui_results(framerate=None):
    """Prepare processed PNG files for sequence import"""
    log_to_file("Preparing sequence files for import...")
    
    # Get the framerate
    if framerate is None:
        framerate = get_project_framerate()
    
    log_to_file(f"Using framerate for import: {framerate}")
    
    # The exact path where ComfyUI stores the results
    comfla_dir = os.path.join(COMFYUI_OUTPUT_DIR, "comfla")
    log_to_file(f"Looking for files in: {comfla_dir}")
    
    if not os.path.exists(comfla_dir):
        log_to_file(f"Directory does not exist: {comfla_dir}")
        return False
    
    # Look specifically for PNG files with the naming pattern
    png_files = [f for f in os.listdir(comfla_dir) if f.endswith('.png') and f.startswith('img_')]
    
    if not png_files:
        log_to_file("No processed PNG files found")
        return False
    
    # Sort files to ensure proper sequence
    png_files.sort()
    log_to_file(f"Found {len(png_files)} processed PNG files")
    
    try:
        # Create standardized files with sequential numbering
        temp_dir = os.path.join(comfla_dir, "seq_import")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # Copy files with a standard sequential naming pattern
        for i, filename in enumerate(png_files):
            source = os.path.join(comfla_dir, filename)
            # Use a naming convention that Flame definitely recognizes
            target = os.path.join(temp_dir, f"sequence.{i+1:04d}.png")
            shutil.copy2(source, target)
            log_to_file(f"Created standardized file: {target}")
        
        # Prepare the import path
        import_path = os.path.join(temp_dir, "sequence.*.png")
        log_to_file(f"Using import path pattern: {import_path}")
        
        # Get a reel to import into
        reels = flame.find_reels('fuji')
        if not reels:
            log_to_file("Reel 'fuji' not found, trying to create it")
            desktop = flame.project.current_workspace.desktop
            reel = desktop.create_reel('fuji')
        else:
            reel = reels[0]
        
        log_to_file(f"Using reel: {reel.name}")
        
        # Import the sequence using the simplified approach
        imported_clips = flame.import_clips(import_path, reel)
        
        # Check import result
        if imported_clips:
            log_to_file(f"Import successful. Result: {imported_clips}")
            if isinstance(imported_clips, list) and len(imported_clips) == 1:
                log_to_file("Successfully imported as a single clip")
            else:
                log_to_file(f"Imported {len(imported_clips)} items, not as a single sequence")
            return True
        else:
            log_to_file("Import returned empty result")
            return False
            
    except Exception as e:
        log_to_file(f"Error during sequence import: {str(e)}")
        log_to_file(traceback.format_exc())
        return False

# Function to rename files to a proper sequence format that Flame will recognize
def prepare_sequence_for_flame(directory=None):
    """
    Rename files to consistent sequence patterns that Flame will recognize.
    Dynamically detects and handles ANY sequence types based on filename prefixes.
    """
    # Use the directory from parameters or get from config
    if directory is None:
        # Use the output directory from config + comfla subfolder
        directory = os.path.join(CONFIG["output_dir"], "comfla")
    
    log_to_file(f"Preparing sequences in: {directory}")
    
    if not os.path.exists(directory):
        log_to_file(f"Directory does not exist: {directory}")
        return False

    try:
        # Get all PNG files in the directory
        png_files = [f for f in os.listdir(directory) if f.endswith('.png')]
        if not png_files:
            log_to_file("No PNG files found in directory")
            return False

        # Log all found files for debugging
        log_to_file(f"Found {len(png_files)} PNG files")

        # Dynamically detect sequence prefixes by identifying common prefix patterns
        prefixes = set()
        for filename in png_files:
            # Extract prefix part (anything before numbers)
            match = re.match(r'^(.+?)(?:\d+|_\d+)', filename)
            if match:
                prefix = match.group(1)
                prefixes.add(prefix)
        
        log_to_file(f"Detected sequence prefixes: {prefixes}")
        
        # If no prefixes detected through regex, try alternative detection
        if not prefixes:
            log_to_file("Trying alternative prefix detection")
            # Group by first part of filename (before first "_" or ".")
            for filename in png_files:
                parts = re.split(r'[_.]', filename, 1)
                if parts and len(parts) > 1:
                    prefixes.add(parts[0] + "_")
        
        # If still no prefixes, create a default group for all files
        if not prefixes:
            log_to_file("No sequence prefixes detected, treating all files as one sequence")
            prefixes = {"sequence_"}
        
        # Create mapping for standardized sequence names
        sequence_types = {}
        for prefix in prefixes:
            # Create a standardized version of the prefix for Flame compatibility
            # Keep the original name but ensure it ends with _v1.
            std_prefix = prefix.rstrip('_.-') + '_v1.'
            sequence_types[prefix] = std_prefix
            log_to_file(f"Mapping sequence: {prefix} -> {std_prefix}")

        # Group files by sequence type
        sequences = {prefix: [] for prefix in sequence_types.keys()}
        
        for filename in png_files:
            assigned = False
            for prefix in sequence_types.keys():
                if filename.startswith(prefix):
                    sequences[prefix].append(filename)
                    assigned = True
                    break
            
            # If file doesn't match any prefix, add to default group or first group
            if not assigned and sequences:
                default_prefix = next(iter(sequences.keys()))
                sequences[default_prefix].append(filename)
                log_to_file(f"Unmatched file {filename} added to {default_prefix} sequence")

        # Process each sequence type
        for prefix, files in sequences.items():
            if not files:
                log_to_file(f"No files found for prefix: {prefix}")
                continue  # Skip if no files for this sequence type
                
            log_to_file(f"Processing {prefix} sequence with {len(files)} files")
            
            # Get standardized prefix for this sequence
            new_prefix = sequence_types[prefix]
            
            # Check if files already match the pattern "type_v1.#####.png"
            if all(re.match(f"{new_prefix}\d{{5}}\.png", f) for f in files):
                log_to_file(f"{prefix} sequence already has correct naming pattern")
                continue

            # Rename files in this sequence
            for i, filename in enumerate(sorted(files)):
                old_path = os.path.join(directory, filename)
                new_name = f"{new_prefix}{i+1:05d}.png"  # e.g., img_v1.00001.png
                new_path = os.path.join(directory, new_name)
                try:
                    os.rename(old_path, new_path)
                    log_to_file(f"Renamed: {filename} -> {new_name}")
                except Exception as e:
                    log_to_file(f"Error renaming {filename}: {str(e)}")
                    continue  # Continue with other files even if one fails

        log_to_file("All sequences prepared successfully")
        return True

    except Exception as e:
        log_to_file(f"Error in prepare_sequence_for_flame: {str(e)}")
        log_to_file(traceback.format_exc())
        return False

def import_png_sequence(selection):
    """
    Import ComfyUI output PNG files as proper sequences into Flame.
    Dynamically detects and imports ALL sequences found in the output directory.
    """
    try:
        # Use the output directory from config + comfla subfolder
        comfy_output_dir = os.path.join(CONFIG["output_dir"], "comfla")
        log_to_file(f"Using output directory from config: {comfy_output_dir}")
        
        # First, prepare (rename) the files to ensure the proper sequence formatting
        if not prepare_sequence_for_flame(comfy_output_dir):
            log_to_file("Failed to prepare sequence for import.")
            return False

        # Get or create the reel
        try:
            desktop = flame.project.current_project.current_workspace.desktop
            reel_groups = desktop.reel_groups
            
            if not reel_groups:
                log_to_file("No reel groups found, creating new one")
                reel_group = desktop.create_reel_group("Sequences")
            else:
                reel_group = reel_groups[0]
            
            # Try to get the currently selected reel
            reel = None
            try:
                # First try to get the reel from the selection
                if selection and hasattr(selection[0], 'reel'):
                    reel = selection[0].reel
                    log_to_file(f"Using reel from selection: {reel.name}")
            except Exception as e:
                log_to_file(f"Could not get reel from selection: {str(e)}")

            # If no reel from selection, use the first available reel or ask user
            if not reel:
                if reel_group.reels:
                    reel = reel_group.reels[0]
                    log_to_file(f"Using first available reel: {reel.name}")
                else:
                    # Ask user for reel name
                    reel_name = flame.ask("Create Reel", "Enter name for new reel:", ["Create", "Cancel"])
                    if reel_name and reel_name != "Cancel":
                        reel = reel_group.create_reel(reel_name)
                        log_to_file(f"Created new reel: {reel_name}")
                    else:
                        log_to_file("User cancelled reel creation")
                        return False
            
            if not reel:
                log_to_file("Failed to get or create a reel")
                return False
                
            log_to_file(f"Using reel: {reel.name}")

            # Dynamically detect sequence types by finding all unique prefixes in the directory
            sequence_prefixes = set()
            all_files = [f for f in os.listdir(comfy_output_dir) if f.endswith('.png')]
            
            for filename in all_files:
                # Look for pattern like "prefix_v1.00001.png"
                match = re.match(r'^(.+?_v1)\.', filename)
                if match:
                    prefix = match.group(1)
                    sequence_prefixes.add(prefix)
            
            log_to_file(f"Detected sequences to import: {sequence_prefixes}")
            
            if not sequence_prefixes:
                log_to_file("No properly formatted sequences found to import")
                return False
            
            import_success = False
            
            # Try to import each detected sequence
            for prefix in sequence_prefixes:
                sequence_name = prefix.replace('_v1', '')  # Clean up name for display
                log_to_file(f"Attempting to import sequence: {sequence_name}")
                
                # Get all PNG files for this sequence type
                png_files = sorted([f for f in os.listdir(comfy_output_dir) 
                                 if f.startswith(f'{prefix}.') and f.endswith('.png')])
                
                if not png_files:
                    log_to_file(f"No files found for {sequence_name} sequence")
                    continue

                # Create a list of full paths for all files
                file_paths = [os.path.join(comfy_output_dir, f) for f in png_files]
                log_to_file(f"Found {len(file_paths)} files for {sequence_name}")

                try:
                    # Try to import all files at once
                    result = flame.import_clips(file_paths, reel)
                    if result:
                        log_to_file(f"Successfully imported {sequence_name} sequence")
                        import_success = True
                        continue
                except Exception as e:
                    log_to_file(f"Bulk import failed for {sequence_name}: {str(e)}")

                # If bulk import fails, try sequence patterns
                patterns = [
                    f"{prefix}.*.png",
                    f"{prefix}.[#####].png",
                    f"{prefix}.[0-9][0-9][0-9][0-9][0-9].png"
                ]

                for pattern in patterns:
                    sequence_path = os.path.join(comfy_output_dir, pattern)
                    log_to_file(f"Trying sequence pattern for {sequence_name}: {sequence_path}")
                    try:
                        result = flame.import_clips(sequence_path, reel)
                        if result:
                            log_to_file(f"Successfully imported {sequence_name} sequence with pattern")
                            import_success = True
                            break
                    except Exception as e:
                        log_to_file(f"Pattern import failed for {sequence_name}: {str(e)}")

            if import_success:
                log_to_file(f"Successfully imported sequences: {', '.join(sequence_prefixes)}")
                return True
            else:
                log_to_file("No sequences were imported successfully")
                return False

        except Exception as e:
            log_to_file(f"Error setting up reel: {str(e)}")
            return False

    except Exception as e:
        log_to_file(f"Error in import_png_sequence: {str(e)}")
        log_to_file(traceback.format_exc())
        return False

def check_existing_outputs():
    """
    Check for existing PNG files in the output directory and warn user
    Returns True if it's safe to proceed, False if user wants to cancel
    """
    # Use the output directory from config + comfla subfolder
    comfy_output_dir = os.path.join(CONFIG["output_dir"], "comfla")
    
    if not os.path.exists(comfy_output_dir):
        return True
        
    existing_files = [f for f in os.listdir(comfy_output_dir) if f.endswith('.png')]
    
    if existing_files:
        message = f"Found {len(existing_files)} existing PNG files in output folder.\nDo you want to:"
        options = ["Archive & Continue", "Delete & Continue", "Cancel"]
        
        choice = flame.ask("Existing Files Warning", message, options)
        
        if choice == "Cancel":
            return False
        elif choice == "Archive & Continue":
            # Create archive folder with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            archive_dir = os.path.join(comfy_output_dir, f"archive_{timestamp}")
            try:
                os.makedirs(archive_dir)
                for file in existing_files:
                    src = os.path.join(comfy_output_dir, file)
                    dst = os.path.join(archive_dir, file)
                    shutil.move(src, dst)
                log_to_file(f"Archived {len(existing_files)} files to {archive_dir}")
            except Exception as e:
                log_to_file(f"Error archiving files: {str(e)}")
                return False
        elif choice == "Delete & Continue":
            try:
                for file in existing_files:
                    os.remove(os.path.join(comfy_output_dir, file))
                log_to_file(f"Deleted {len(existing_files)} existing files")
            except Exception as e:
                log_to_file(f"Error deleting files: {str(e)}")
                return False
                
    return True

# Function to get a list of available workflows
def get_available_workflows():
    """
    Get a list of available workflows in the workflows directory.
    Returns a list of workflow names (without .json extension).
    """
    workflows = []
    try:
        if os.path.exists(WORKFLOWS_DIR):
            workflow_files = [f for f in os.listdir(WORKFLOWS_DIR) if f.endswith('.json')]
            for workflow_file in workflow_files:
                workflow_name = os.path.splitext(workflow_file)[0]
                workflows.append(workflow_name)
            
            log_to_file(f"Found {len(workflows)} workflows: {workflows}")
        else:
            log_to_file(f"Workflows directory not found: {WORKFLOWS_DIR}")
    except Exception as e:
        log_to_file(f"Error getting available workflows: {str(e)}")
    
    return workflows

# Function to show workflow selection dialog - updated to use library solution
def show_workflow_selection_dialog():
    """
    Display a dialog to select a workflow.
    Returns the selected workflow path or None if cancelled.
    """
    try:
        workflows = get_available_workflows()
        
        if not workflows:
            show_flame_message("No workflows found in workflows directory")
            return None
        
        # Create a window using our embedded PyFlame components
        window = PyFlameDialogWindow(
            title="Select ComfyUI Workflow",
            width=400,
            height=200,
            line_color=LineColor.BLUE
        )
        
        # Add a title/info label
        info_label = PyFlameLabel(
            text="Select a workflow to process your images with ComfyUI:"
        )
        window.grid_layout.addWidget(info_label, 0, 0, 1, 2)
        
        # Add a dropdown menu for workflow selection using library's QPushButton-based menu
        # which has better compatibility with older Qt versions
        selected_workflow = [workflows[0]]  # Default to first workflow
        
        # Using QPushButton implementation instead of QToolButton for better menu behavior
        workflow_menu = QtWidgets.QPushButton(selected_workflow[0])
        workflow_menu.setFont(QtGui.QFont(PYFLAME_FONT, font_resize(PYFLAME_FONT_SIZE)))
        if using_pyside6:
            workflow_menu.setFixedHeight(gui_resize(40))
        else:
            workflow_menu.setMinimumHeight(gui_resize(40))
        workflow_menu.setStyleSheet(f'''
            QPushButton {{
                color: {Color.TEXT.value};
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 {Color.GRADIENT_START.value}, 
                                           stop:1 {Color.GRADIENT_END.value});
                border: 1px solid {Color.BORDER.value};
                border-radius: 4px;
                padding: 6px 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 {Color.GRAY_LIGHT.value}, 
                                           stop:1 {Color.GRADIENT_END.value});
                border: 1px solid {Color.ACCENT_BLUE};
            }}
        ''')
        
        # Create the menu
        menu = QtWidgets.QMenu()
        menu.setStyleSheet(f'''
            QMenu {{
                color: {Color.TEXT.value};
                background-color: rgb(50, 50, 50);
                border: 1px solid {Color.BORDER.value};
                border-radius: 3px;
            }}
            QMenu::item {{
                height: 30px;
                padding: 8px 25px;
                border: 1px solid transparent;
            }}
            QMenu::item:selected {{
                color: {Color.WHITE.value};
                background-color: {Color.BLUE.value};
                border-radius: 3px;
            }}
        ''')
        
        # Add menu actions - FIXED: Use QAction directly (imported at the top level)
        # instead of QtWidgets.QAction which doesn't exist in PySide6
        for workflow_name in workflows:
            # Use the imported QAction instead of QtWidgets.QAction
            action = QAction(workflow_name, menu)
            # Connect using a simpler approach for better compatibility
            action.triggered.connect(lambda checked=False, name=workflow_name: 
                                     workflow_menu.setText(name) or selected_workflow.__setitem__(0, name))
            menu.addAction(action)
        
        workflow_menu.setMenu(menu)
        
        # Add tip label
        tip_label = PyFlameLabel(
            text="TIP: Click to open dropdown menu or use keyboard arrows and Enter"
        )
        tip_label.setStyleSheet(f"color: {Color.ACCENT_BLUE.value}; font-style: italic;")
        
        # Add buttons with larger sizes
        cancel_button = PyFlameButton(
            text="Cancel",
            connect=window.reject,
            width=150,
            height=40
        )
        
        confirm_button = PyFlameButton(
            text="Confirm",
            connect=window.accept,
            width=150,
            height=40,
            color=Color.BLUE
        )
        
        # Place widgets in the window
        window.grid_layout.addWidget(workflow_menu, 1, 0, 1, 2)
        window.grid_layout.addWidget(tip_label, 2, 0, 1, 2)
        
        # Create a horizontal layout for the buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(confirm_button)
        
        # Add the button layout to the main grid
        window.grid_layout.addLayout(button_layout, 3, 0, 1, 2)
        
        # Show dialog
        result = window.exec_()
        
        if result:
            selected_workflow_path = os.path.join(WORKFLOWS_DIR, f"{selected_workflow[0]}.json")
            log_to_file(f"Selected workflow: {selected_workflow[0]}")
            return selected_workflow_path
        else:
            log_to_file("Workflow selection cancelled")
            return None
            
    except Exception as e:
        log_to_file(f"Error showing workflow selection dialog: {str(e)}")
        log_to_file(traceback.format_exc())
        return None

# Function to show text input dialog
def show_text_input_dialog(text_nodes, workflow_name):
    """
    Display a dialog for the user to input text for each text node.
    
    Args:
        text_nodes (list): List of text input nodes
        workflow_name (str): Name of the workflow
    
    Returns:
        dict: Dictionary of node_id -> new text value, or None if cancelled
    """
    if not text_nodes:
        return {}
    
    try:
        # Create a dialog window using our embedded components with larger sizes
        window = PyFlameDialogWindow(
            title=f"Text Inputs for {workflow_name}",
            width=600,  # Increased width
            height=100 + (len(text_nodes) * 70),  # Increased height per row
            line_color=LineColor.BLUE
        )
        
        # Add a title/info label
        info_label = PyFlameLabel(
            text="Enter text for the prompts in this workflow:"
        )
        window.grid_layout.addWidget(info_label, 0, 0, 1, 2)
        
        # Set column stretch to give the entry field more space (20% for label, 80% for text field)
        window.grid_layout.setColumnStretch(0, 2)  # Label column gets 20% weight
        window.grid_layout.setColumnStretch(1, 8)  # Text field column gets 80% weight
        
        # Create text entry fields for each text node
        text_entries = {}
        row = 1  # Start at row 1 after the info label
        
        for i, node in enumerate(text_nodes):
            # Create label for the text node
            label_text = node["title"]
            
            # Handle different node types with more friendly labels
            if "prompt" in label_text.lower():
                label_text = f"Prompt {i+1}"
            elif "negative" in label_text.lower():
                label_text = f"Negative Prompt {i+1}"
            elif "input_name" in node:
                # For custom inputs, show the input field name
                label_text = f"{node['class_type']} - {node['input_name']}"
            
            label = PyFlameLabel(
                text=label_text,
                width=140,  # Slightly reduced width for label
                height=40
            )
            
            # Create text entry that expands with the window
            # For custom inputs, create a proper node_id+input_field key
            node_key = f"{node['node_id']}.{node['input_name']}" if "input_name" in node else node["node_id"]
            
            text_entry = PyFlameEntry(
                text=node["text"],
                height=40,   # Only specify height, not width
                max_width=True  # Allow it to expand to full width
            )
            
            # Store the entry widget with the proper key
            text_entries[node_key] = text_entry
            
            # Add widgets to layout
            window.grid_layout.addWidget(label, row, 0)
            window.grid_layout.addWidget(text_entry, row, 1)
            row += 1
        
        # Add buttons with larger sizes - SWAPPED POSITIONS
        cancel_button = PyFlameButton(
            text="Cancel",
            connect=window.reject,
            width=150,
            height=40
        )
        
        confirm_button = PyFlameButton(
            text="Confirm",
            connect=window.accept,
            width=150,
            height=40,
            color=Color.BLUE  # Make confirm button blue
        )
        
        # Create a horizontal layout for the buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()  # Add space between buttons
        button_layout.addWidget(confirm_button)
        
        # Add the button layout to the main grid
        window.grid_layout.addLayout(button_layout, row, 0, 1, 2)
        
        # Show the dialog
        result = window.exec_()
        
        if result:
            # Collect text inputs
            text_values = {}
            for node_id, entry in text_entries.items():
                text_value = entry.text()
                text_values[node_id] = text_value
                log_to_file(f"Got text input for {node_id}: {text_value[:30]}...")  # Log only first 30 chars
            return text_values
        else:
            return None
            
    except Exception as e:
        log_to_file(f"Error showing text input dialog: {str(e)}")
        log_to_file(traceback.format_exc())
        return None

# Function to update workflow with new text inputs
def update_workflow_with_text_inputs(workflow, text_values):
    """
    Update the workflow with new text input values.
    Now uses deep copy and handles custom input fields.
    
    Args:
        workflow (dict): Workflow JSON data
        text_values (dict): Dictionary of node_id -> new text value
    
    Returns:
        dict: Updated workflow
    """
    if not text_values:
        return workflow
    
    try:
        # Create a DEEP copy of the workflow to modify (important for nested dictionaries)
        updated_workflow = copy.deepcopy(workflow)
        
        # Update each text node with the new value
        for node_id, new_text in text_values.items():
            if node_id in updated_workflow and "inputs" in updated_workflow[node_id]:
                # If this is a specific input field (for custom nodes)
                if "." in node_id:
                    main_id, input_field = node_id.split(".", 1)
                    if main_id in updated_workflow and "inputs" in updated_workflow[main_id]:
                        if input_field in updated_workflow[main_id]["inputs"]:
                            updated_workflow[main_id]["inputs"][input_field] = new_text
                            log_to_file(f"Updated custom input: {main_id}.{input_field} with text: {new_text[:30]}...")
                # Standard text node
                else:
                    updated_workflow[node_id]["inputs"]["text"] = new_text
                    log_to_file(f"Updated node {node_id} with text: {new_text[:30]}...")
        
        # Dump the entire workflow to log for debugging
        log_to_file(f"Final workflow has {len(updated_workflow)} nodes")
        
        return updated_workflow
    except Exception as e:
        log_to_file(f"Error updating workflow with text inputs: {str(e)}")
        log_to_file(traceback.format_exc())
        return workflow

# Function to get workflow name from path
def get_workflow_name(workflow_path):
    """Extract the workflow name from its path"""
    try:
        return os.path.splitext(os.path.basename(workflow_path))[0]
    except:
        return "Workflow"

# Create a new version of process_with_comfyui_api that accepts a workflow object
def process_with_comfyui_api_with_workflow(image_path, output_dir, workflow):
    """Process an image sequence with ComfyUI API using a provided workflow"""
    try:
        log_to_file(f"Processing sequence with ComfyUI. First image: {image_path}")
        
        if not is_comfyui_running():
            log_to_file("ComfyUI server is not running")
            return None
        
        # Generate a unique job ID - THIS WAS MISSING
        job_id = str(uuid.uuid4())
        log_to_file(f"Job ID: {job_id}")
        
        # Use the provided workflow
        if not workflow:
            log_to_file(f"Error: No valid workflow provided")
            show_flame_message(f"Error: No valid workflow provided")
            
            # Let's create a basic workflow as a last resort
            workflow = {
                "4": {
                    "inputs": {
                        "torchscript_jit": "default",
                        "image": ["5", 0]
                    },
                    "class_type": "InspyrenetRembg",
                    "_meta": {"title": "Inspyrenet Rembg"}
                },
                "5": {
                    "inputs": {
                        "directory": "output/flacom/",
                        "image_load_cap": 0,
                        "skip_first_images": 0,
                        "select_every_nth": 1
                    },
                    "class_type": "VHS_LoadImagesPath",
                    "_meta": {"title": "Load Images (Path) 🎥🅥🅗🅢"}
                },
                "13": {
                    "inputs": {
                        "filename_prefix": "comfla/img",
                        "images": ["4", 0]
                    },
                    "class_type": "SaveImage",
                    "_meta": {"title": "Save Image"}
                }
            }
            
            log_to_file("Created inline workflow as last resort")
                
        # Ensure directory exists in ComfyUI path
        if not os.path.exists(COMFYUI_FLACOM_DIR):
            os.makedirs(COMFYUI_FLACOM_DIR)
            log_to_file(f"Created directory: {COMFYUI_FLACOM_DIR}")
        
        # Check how many frames we have 
        files = [f for f in os.listdir(COMFYUI_FLACOM_DIR) if f.endswith(('.jpg', '.jpeg', '.dpx', '.exr', '.png', '.tif', '.tiff'))]
        log_to_file(f"Processing {len(files)} frames in {COMFYUI_FLACOM_DIR}")

        # Find and update the VHS_LoadImagesPath node in the workflow
        vhs_node_found = False
        for node_id, node in workflow.items():
            if node.get("class_type") == "VHS_LoadImagesPath":
                # Make sure the directory matches where we exported the frames
                node["inputs"]["directory"] = "output/flacom"
                log_to_file(f"Updated VHS_LoadImagesPath node with directory: output/flacom")
                vhs_node_found = True
                break

        # Look for SaveImage node to determine output location
        save_node_found = False
        save_prefix = "comfla/img"  # Default prefix
        
        for node_id, node in workflow.items():
            if node.get("class_type") == "SaveImage":
                save_node_found = True
                if "inputs" in node and "filename_prefix" in node["inputs"]:
                    save_prefix = node["inputs"]["filename_prefix"]
                    log_to_file(f"Found SaveImage node with prefix: {save_prefix}")
                break

        log_to_file(f"Will look for output images with prefix: {save_prefix}")
        
        if not vhs_node_found:
            log_to_file("ERROR: No VHS_LoadImagesPath node found in workflow!")
            show_flame_message("Workflow does not have the required VHS_LoadImagesPath node")
            return None
            
        # Create API request
        api_request = {
            "prompt": workflow,
            "client_id": f"flame_comfyui_{job_id}"
        }

        # Continue with the existing code to send the request to ComfyUI
        # ...existing code from process_with_comfyui_api...
        
        # Send request
        request_data = json.dumps(api_request)
        
        # Log a sample of the request for debugging
        log_to_file(f"API Request sample (first 500 chars): {request_data[:500]}...")
        
        # Log if we have any text nodes/inputs in the workflow
        text_nodes_in_workflow = detect_text_input_nodes(workflow)
        if text_nodes_in_workflow:
            log_to_file(f"Workflow contains {len(text_nodes_in_workflow)} text inputs:")
            for node in text_nodes_in_workflow:
                node_id = node["node_id"]
                text = node["text"]
                log_to_file(f"  Node {node_id}: '{text[:50]}...'")
        else:
            log_to_file("WARNING: No text inputs detected in workflow being sent to ComfyUI")
        
        curl_cmd = [
            'curl', '-s', 
            '-X', 'POST', 
            f'{COMFYUI_URL}/prompt', 
            '-H', 'Content-Type: application/json', 
            '-d', request_data
        ]
        
        # ...existing code...
        
        # Execute the curl command
        try:
            log_to_file(f"Running command: curl -X POST {COMFYUI_URL}/prompt ...")
            result = subprocess.run(curl_cmd, capture_output=True, text=True)
            
            log_to_file(f"Command stdout: {result.stdout}")
            if result.stderr:
                log_to_file(f"Command stderr: {result.stderr}")
                
            # ...rest of the existing function...
            if result.returncode != 0:
                log_to_file(f"Error submitting workflow: Return code {result.returncode}")
                if result.stderr:
                    log_to_file(f"Error details: {result.stderr}")
                return None
                
            if not result.stdout.strip():
                log_to_file("Empty response from ComfyUI server")
                return None
                
            try:
                response = json.loads(result.stdout)
                prompt_id = response.get('prompt_id')
                
                if not prompt_id:
                    log_to_file("No prompt_id in response")
                    log_to_file(f"Full response: {response}")
                    return None
                    
                log_to_file(f"Prompt ID: {prompt_id}")
                
                # Wait for job completion - INCREASED TIMEOUT
                max_retries = 9000  # 10 minutes (up from 180 seconds)
                retry_count = 0
                
                while retry_count < max_retries:
                    time.sleep(1)
                    
                    # Only log every 10th check to reduce log verbosity
                    if retry_count % 10 == 0:
                        log_to_file(f"Checking status: retry {retry_count+1}/{max_retries}")
                    
                    check_cmd = ['curl', '-s', f'{COMFYUI_URL}/history/{prompt_id}']
                    result = subprocess.run(check_cmd, capture_output=True, text=True)
                    
                    # ...remaining code from original function...
                    if result.returncode != 0:
                        log_to_file(f"Error checking status: {result.stderr}")
                        retry_count += 1
                        continue

                    try:
                        history = json.loads(result.stdout)
                        
                        if prompt_id in history:
                            # Check if outputs contain images
                            outputs = history[prompt_id].get('outputs', {})
                            
                            for node_id, output in outputs.items():
                                if 'images' in output:
                                    images = output['images']
                                    
                                    if images:
                                        # Return the first image as our result
                                        image_data = images[0]
                                        image_filename = image_data.get('filename')
                                        
                                        if image_filename:
                                            output_path = os.path.join(COMFYUI_OUTPUT_DIR, image_filename)
                                            
                                            if os.path.exists(output_path):
                                                log_to_file(f"Found processed image at: {output_path}")
                                                return output_path
                                            
                                            # Try to download if not found directly
                                            local_output_path = os.path.join(output_dir, image_filename)
                                            image_url = f"{COMFYUI_URL}/view?filename={image_filename}&type=output"
                                            download_cmd = ['curl', '-s', '-o', local_output_path, image_url]
                                            
                                            dl_result = subprocess.run(download_cmd, capture_output=True)
                                            
                                            if dl_result.returncode == 0 and os.path.exists(local_output_path):
                                                log_to_file(f"Image saved to: {local_output_path}")
                                                return local_output_path
                    
                    except json.JSONDecodeError:
                        log_to_file("Invalid JSON in history response")
                    
                    retry_count += 1
                
                # We've timed out, but let's check for output files directly
                log_to_file("Timed out waiting for ComfyUI, checking for output files directly")
                
                # Look specifically for PNG files with the pattern from the SaveImage node
                comfla_dir = os.path.join(COMFYUI_OUTPUT_DIR, "comfla")
                if os.path.exists(comfla_dir):
                    png_files = [f for f in os.listdir(comfla_dir) if f.endswith('.png') and f.startswith('img_')]
                    if png_files:
                        log_to_file(f"Found {len(png_files)} PNG files with alpha in {comfla_dir}")
                        # Return the directory path
                        return comfla_dir
                
                # No files found
                log_to_file(f"No output files found in {comfla_dir}")
                return None
                
            except json.JSONDecodeError as e:
                log_to_file(f"Error parsing JSON response: {str(e)}")
                log_to_file(f"Raw response: {result.stdout}")
                return None
            
        except Exception as e:
            log_to_file(f"Error processing with ComfyUI: {str(e)}")
            return None
            
    except Exception as e:
        log_to_file(f"Error in process_with_comfyui_api_with_workflow: {str(e)}")
        return None

# Function to detect text input nodes in the workflow - IMPROVED VERSION
def detect_text_input_nodes(workflow):
    """
    Scan a workflow for text input nodes and return node information.
    Now supports multiple node types used for text inputs.
    
    Args:
        workflow (dict): Workflow JSON data
    
    Returns:
        list: List of dictionaries containing node ID and current text value
    """
    text_nodes = []
    
    try:
        # List of known node types that accept text inputs
        text_node_types = [
            "CLIPTextEncode",           # Standard text encoder
            "KSampler",                 # Sometimes has prompt input directly
            "KSamplerAdvanced",         # Advanced sampler with prompt
            "PromptText",               # Custom text node
            "Text",                     # Generic text input
            "Note",                     # Note node (may contain prompts)
            "ConditioningTextPrompt",   # Another form of text conditioning 
            "PromptStylizerNode"        # Style adapters
        ]
        
        for node_id, node in workflow.items():
            class_type = node.get("class_type", "")
            
            # Check if this is a known text input node type
            if class_type in text_node_types:
                # For standard CLIP text encoder
                if "inputs" in node and "text" in node.get("inputs", {}):
                    text = node["inputs"]["text"]
                    title = node.get("_meta", {}).get("title", class_type)
                    
                    text_nodes.append({
                        "node_id": node_id,
                        "text": text,
                        "title": title,
                        "class_type": class_type
                    })
                    log_to_file(f"Found text input node: {node_id} ({class_type}) with title '{title}' and text '{text[:30]}...'")
            
            # Also check for custom nodes that might have text inputs
            elif "inputs" in node:
                inputs = node["inputs"]
                # Look for any input field that might contain prompt text
                for input_name, input_value in inputs.items():
                    if isinstance(input_value, str) and len(input_value) > 5 and input_name in ["prompt", "text", "positive", "negative"]:
                        title = node.get("_meta", {}).get("title", class_type)
                        if not title:
                            title = f"{class_type} - {input_name}"
                            
                        text_nodes.append({
                            "node_id": node_id,
                            "input_name": input_name,  # Store the specific input field name
                            "text": input_value,
                            "title": title,
                            "class_type": class_type
                        })
                        log_to_file(f"Found custom text input: {node_id}.{input_name} with value '{input_value[:30]}...'")
        
        log_to_file(f"Total text input nodes found: {len(text_nodes)}")
        return text_nodes
    except Exception as e:
        log_to_file(f"Error detecting text input nodes: {str(e)}")
        log_to_file(traceback.format_exc())
        return []

# Function to update workflow with new text inputs - IMPROVED VERSION
def update_workflow_with_text_inputs(workflow, text_values):
    """
    Update the workflow with new text input values.
    Now uses deep copy and handles custom input fields.
    
    Args:
        workflow (dict): Workflow JSON data
        text_values (dict): Dictionary of node_id -> new text value
    
    Returns:
        dict: Updated workflow
    """
    if not text_values:
        return workflow
    
    try:
        # Create a DEEP copy of the workflow to modify (important for nested dictionaries)
        updated_workflow = copy.deepcopy(workflow)
        
        # Update each text node with the new value
        for node_id, new_text in text_values.items():
            if node_id in updated_workflow and "inputs" in updated_workflow[node_id]:
                # If this is a specific input field (for custom nodes)
                if "." in node_id:
                    main_id, input_field = node_id.split(".", 1)
                    if main_id in updated_workflow and "inputs" in updated_workflow[main_id]:
                        if input_field in updated_workflow[main_id]["inputs"]:
                            updated_workflow[main_id]["inputs"][input_field] = new_text
                            log_to_file(f"Updated custom input: {main_id}.{input_field} with text: {new_text[:30]}...")
                # Standard text node
                else:
                    updated_workflow[node_id]["inputs"]["text"] = new_text
                    log_to_file(f"Updated node {node_id} with text: {new_text[:30]}...")
        
        # Dump the entire workflow to log for debugging
        log_to_file(f"Final workflow has {len(updated_workflow)} nodes")
        
        return updated_workflow
    except Exception as e:
        log_to_file(f"Error updating workflow with text inputs: {str(e)}")
        log_to_file(traceback.format_exc())
        return workflow

# Function to show text input dialog - FIX FOR CUSTOM INPUT FIELDS
def show_text_input_dialog(text_nodes, workflow_name):
    """
    Display a dialog for the user to input text for each text node.
    
    Args:
        text_nodes (list): List of text input nodes
        workflow_name (str): Name of the workflow
    
    Returns:
        dict: Dictionary of node_id -> new text value, or None if cancelled
    """
    if not text_nodes:
        return {}
    
    try:
        # Create a dialog window using our embedded components with larger sizes
        window = PyFlameDialogWindow(
            title=f"Text Inputs for {workflow_name}",
            width=600,  # Increased width
            height=100 + (len(text_nodes) * 70),  # Increased height per row
            line_color=LineColor.BLUE
        )
        
        # Add a title/info label
        info_label = PyFlameLabel(
            text="Enter text for the prompts in this workflow:"
        )
        window.grid_layout.addWidget(info_label, 0, 0, 1, 2)
        
        # Set column stretch to give the entry field more space (20% for label, 80% for text field)
        window.grid_layout.setColumnStretch(0, 2)  # Label column gets 20% weight
        window.grid_layout.setColumnStretch(1, 8)  # Text field column gets 80% weight
        
        # Create text entry fields for each text node
        text_entries = {}
        row = 1  # Start at row 1 after the info label
        
        for i, node in enumerate(text_nodes):
            # Create label for the text node
            label_text = node["title"]
            
            # Handle different node types with more friendly labels
            if "prompt" in label_text.lower():
                label_text = f"Prompt {i+1}"
            elif "negative" in label_text.lower():
                label_text = f"Negative Prompt {i+1}"
            elif "input_name" in node:
                # For custom inputs, show the input field name
                label_text = f"{node['class_type']} - {node['input_name']}"
            
            label = PyFlameLabel(
                text=label_text,
                width=140,  # Slightly reduced width for label
                height=40
            )
            
            # Create text entry that expands with the window
            # For custom inputs, create a proper node_id+input_field key
            node_key = f"{node['node_id']}.{node['input_name']}" if "input_name" in node else node["node_id"]
            
            text_entry = PyFlameEntry(
                text=node["text"],
                height=40,   # Only specify height, not width
                max_width=True  # Allow it to expand to full width
            )
            
            # Store the entry widget with the proper key
            text_entries[node_key] = text_entry
            
            # Add widgets to layout
            window.grid_layout.addWidget(label, row, 0)
            window.grid_layout.addWidget(text_entry, row, 1)
            row += 1
        
        # Add buttons with larger sizes - SWAPPED POSITIONS
        cancel_button = PyFlameButton(
            text="Cancel",
            connect=window.reject,
            width=150,
            height=40
        )
        
        confirm_button = PyFlameButton(
            text="Confirm",
            connect=window.accept,
            width=150,
            height=40,
            color=Color.BLUE  # Make confirm button blue
        )
        
        # Create a horizontal layout for the buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()  # Add space between buttons
        button_layout.addWidget(confirm_button)
        
        # Add the button layout to the main grid
        window.grid_layout.addLayout(button_layout, row, 0, 1, 2)
        
        # Show the dialog
        result = window.exec_()
        
        if result:
            # Collect text inputs
            text_values = {}
            for node_id, entry in text_entries.items():
                text_value = entry.text()
                text_values[node_id] = text_value
                log_to_file(f"Got text input for {node_id}: {text_value[:30]}...")  # Log only first 30 chars
            return text_values
        else:
            return None
            
    except Exception as e:
        log_to_file(f"Error showing text input dialog: {str(e)}")
        log_to_file(traceback.format_exc())
        return None

# Modified function to process with ComfyUI API - FIX JOB ID ERROR
def process_with_comfyui_api_with_workflow(image_path, output_dir, workflow):
    """Process an image sequence with ComfyUI API using a provided workflow"""
    try:
        log_to_file(f"Processing sequence with ComfyUI. First image: {image_path}")
        
        if not is_comfyui_running():
            log_to_file("ComfyUI server is not running")
            return None
        
        # Generate a unique job ID - THIS WAS MISSING
        job_id = str(uuid.uuid4())
        log_to_file(f"Job ID: {job_id}")
        
        # Use the provided workflow
        if not workflow:
            log_to_file(f"Error: No valid workflow provided")
            show_flame_message(f"Error: No valid workflow provided")
            
            # Let's create a basic workflow as a last resort
            workflow = {
                "4": {
                    "inputs": {
                        "torchscript_jit": "default",
                        "image": ["5", 0]
                    },
                    "class_type": "InspyrenetRembg",
                    "_meta": {"title": "Inspyrenet Rembg"}
                },
                "5": {
                    "inputs": {
                        "directory": "output/flacom/",
                        "image_load_cap": 0,
                        "skip_first_images": 0,
                        "select_every_nth": 1
                    },
                    "class_type": "VHS_LoadImagesPath",
                    "_meta": {"title": "Load Images (Path) 🎥🅥🅗🅢"}
                },
                "13": {
                    "inputs": {
                        "filename_prefix": "comfla/img",
                        "images": ["4", 0]
                    },
                    "class_type": "SaveImage",
                    "_meta": {"title": "Save Image"}
                }
            }
            
            log_to_file("Created inline workflow as last resort")
                
        # Ensure directory exists in ComfyUI path
        if not os.path.exists(COMFYUI_FLACOM_DIR):
            os.makedirs(COMFYUI_FLACOM_DIR)
            log_to_file(f"Created directory: {COMFYUI_FLACOM_DIR}")
        
        # Check how many frames we have 
        files = [f for f in os.listdir(COMFYUI_FLACOM_DIR) if f.endswith(('.jpg', '.jpeg', '.dpx', '.exr', '.png', '.tif', '.tiff'))]
        log_to_file(f"Processing {len(files)} frames in {COMFYUI_FLACOM_DIR}")

        # Find and update the VHS_LoadImagesPath node in the workflow
        vhs_node_found = False
        for node_id, node in workflow.items():
            if node.get("class_type") == "VHS_LoadImagesPath":
                # Make sure the directory matches where we exported the frames
                node["inputs"]["directory"] = "output/flacom"
                log_to_file(f"Updated VHS_LoadImagesPath node with directory: output/flacom")
                vhs_node_found = True
                break

        # Look for SaveImage node to determine output location
        save_node_found = False
        save_prefix = "comfla/img"  # Default prefix
        
        for node_id, node in workflow.items():
            if node.get("class_type") == "SaveImage":
                save_node_found = True
                if "inputs" in node and "filename_prefix" in node["inputs"]:
                    save_prefix = node["inputs"]["filename_prefix"]
                    log_to_file(f"Found SaveImage node with prefix: {save_prefix}")
                break

        log_to_file(f"Will look for output images with prefix: {save_prefix}")
        
        if not vhs_node_found:
            log_to_file("ERROR: No VHS_LoadImagesPath node found in workflow!")
            show_flame_message("Workflow does not have the required VHS_LoadImagesPath node")
            return None
            
        # Create API request
        api_request = {
            "prompt": workflow,
            "client_id": f"flame_comfyui_{job_id}"
        }

        # Continue with the existing code to send the request to ComfyUI
        # ...existing code from process_with_comfyui_api...
        
        # Send request
        request_data = json.dumps(api_request)
        
        # Log a sample of the request for debugging
        log_to_file(f"API Request sample (first 500 chars): {request_data[:500]}...")
        
        # Log if we have any text nodes/inputs in the workflow
        text_nodes_in_workflow = detect_text_input_nodes(workflow)
        if text_nodes_in_workflow:
            log_to_file(f"Workflow contains {len(text_nodes_in_workflow)} text inputs:")
            for node in text_nodes_in_workflow:
                node_id = node["node_id"]
                text = node["text"]
                log_to_file(f"  Node {node_id}: '{text[:50]}...'")
        else:
            log_to_file("WARNING: No text inputs detected in workflow being sent to ComfyUI")
        
        curl_cmd = [
            'curl', '-s', 
            '-X', 'POST', 
            f'{COMFYUI_URL}/prompt', 
            '-H', 'Content-Type: application/json', 
            '-d', request_data
        ]
        
        # ...existing code...
        
        # Execute the curl command
        try:
            log_to_file(f"Running command: curl -X POST {COMFYUI_URL}/prompt ...")
            result = subprocess.run(curl_cmd, capture_output=True, text=True)
            
            log_to_file(f"Command stdout: {result.stdout}")
            if result.stderr:
                log_to_file(f"Command stderr: {result.stderr}")
                
            # ...rest of the existing function...
            if result.returncode != 0:
                log_to_file(f"Error submitting workflow: Return code {result.returncode}")
                if result.stderr:
                    log_to_file(f"Error details: {result.stderr}")
                return None
                
            if not result.stdout.strip():
                log_to_file("Empty response from ComfyUI server")
                return None
                
            try:
                response = json.loads(result.stdout)
                prompt_id = response.get('prompt_id')
                
                if not prompt_id:
                    log_to_file("No prompt_id in response")
                    log_to_file(f"Full response: {response}")
                    return None
                    
                log_to_file(f"Prompt ID: {prompt_id}")
                
                # Wait for job completion - INCREASED TIMEOUT
                max_retries = 9000  # 10 minutes (up from 180 seconds)
                retry_count = 0
                
                while retry_count < max_retries:
                    time.sleep(1)
                    
                    # Only log every 10th check to reduce log verbosity
                    if retry_count % 10 == 0:
                        log_to_file(f"Checking status: retry {retry_count+1}/{max_retries}")
                    
                    check_cmd = ['curl', '-s', f'{COMFYUI_URL}/history/{prompt_id}']
                    result = subprocess.run(check_cmd, capture_output=True, text=True)
                    
                    # ...remaining code from original function...
                    if result.returncode != 0:
                        log_to_file(f"Error checking status: {result.stderr}")
                        retry_count += 1
                        continue

                    try:
                        history = json.loads(result.stdout)
                        
                        if prompt_id in history:
                            # Check if outputs contain images
                            outputs = history[prompt_id].get('outputs', {})
                            
                            for node_id, output in outputs.items():
                                if 'images' in output:
                                    images = output['images']
                                    
                                    if images:
                                        # Return the first image as our result
                                        image_data = images[0]
                                        image_filename = image_data.get('filename')
                                        
                                        if image_filename:
                                            output_path = os.path.join(COMFYUI_OUTPUT_DIR, image_filename)
                                            
                                            if os.path.exists(output_path):
                                                log_to_file(f"Found processed image at: {output_path}")
                                                return output_path
                                            
                                            # Try to download if not found directly
                                            local_output_path = os.path.join(output_dir, image_filename)
                                            image_url = f"{COMFYUI_URL}/view?filename={image_filename}&type=output"
                                            download_cmd = ['curl', '-s', '-o', local_output_path, image_url]
                                            
                                            dl_result = subprocess.run(download_cmd, capture_output=True)
                                            
                                            if dl_result.returncode == 0 and os.path.exists(local_output_path):
                                                log_to_file(f"Image saved to: {local_output_path}")
                                                return local_output_path
                    
                    except json.JSONDecodeError:
                        log_to_file("Invalid JSON in history response")
                    
                    retry_count += 1
                
                # We've timed out, but let's check for output files directly
                log_to_file("Timed out waiting for ComfyUI, checking for output files directly")
                
                # Look specifically for PNG files with the pattern from the SaveImage node
                comfla_dir = os.path.join(COMFYUI_OUTPUT_DIR, "comfla")
                if os.path.exists(comfla_dir):
                    png_files = [f for f in os.listdir(comfla_dir) if f.endswith('.png') and f.startswith('img_')]
                    if png_files:
                        log_to_file(f"Found {len(png_files)} PNG files with alpha in {comfla_dir}")
                        # Return the directory path
                        return comfla_dir
                
                # No files found
                log_to_file(f"No output files found in {comfla_dir}")
                return None
                
            except json.JSONDecodeError as e:
                log_to_file(f"Error parsing JSON response: {str(e)}")
                log_to_file(f"Raw response: {result.stdout}")
                return None
            
        except Exception as e:
            log_to_file(f"Error processing with ComfyUI: {str(e)}")
            return None
            
    except Exception as e:
        log_to_file(f"Error in process_with_comfyui_api_with_workflow: {str(e)}")
        return None

# Add a function to detect Flame version
def get_flame_version():
    """Detect Flame version to adjust processing behavior"""
    try:
        if hasattr(flame, 'get_version'):
            version = flame.get_version()
            log_to_file(f"Detected Flame version: {version}")
            return version
        elif hasattr(flame, 'version'):
            version = flame.version
            log_to_file(f"Detected Flame version: {version}")
            return version
        else:
            # Try to parse from environment or assume we're on an older version
            log_to_file("Could not detect Flame version directly, assuming 2023.2 or older")
            return "2023.2"
    except Exception as e:
        log_to_file(f"Error detecting Flame version: {str(e)}")
        return "2023.2"  # Default to older version to be safe

# Updated process_with_comfyui function to avoid threading for Flame 2023.2
def process_with_comfyui(selection):
    """Process selected clips with ComfyUI and import results - WITHOUT threading for 2023.2"""
    log_to_file(f"process_with_comfyui called with {len(selection)} items")
    
    # First check for existing files
    if not check_existing_outputs():
        log_to_file("User cancelled due to existing files")
        return
    
    # Show workflow selection dialog
    selected_workflow_path = show_workflow_selection_dialog()
    if selected_workflow_path is None:
        log_to_file("Workflow selection cancelled or no workflow selected")
        show_flame_message("Processing cancelled - no workflow selected")
        return
    
    # Load the selected workflow
    workflow = load_workflow(selected_workflow_path)
    if not workflow:
        log_to_file(f"Failed to load workflow: {selected_workflow_path}")
        show_flame_message(f"Failed to load workflow: {os.path.basename(selected_workflow_path)}")
        return
    
    # Check for text input nodes and show dialog if needed
    text_nodes = detect_text_input_nodes(workflow)
    if text_nodes:
        workflow_name = get_workflow_name(selected_workflow_path)
        text_values = show_text_input_dialog(text_nodes, workflow_name)
        
        if text_values is None:
            log_to_file("Text input dialog cancelled")
            show_flame_message("Processing cancelled - text input dialog closed")
            return
        
        # Update workflow with text inputs
        workflow = update_workflow_with_text_inputs(workflow, text_values)
    
    try:
        if not selection:
            show_flame_message("No items selected")
            return
            
        # Get the first selected clip or segment
        item = selection[0]
        log_to_file(f"Selected item: {item.name}")
        
        # Create unique job directory
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(TEMP_DIR, job_id)
        
        try:
            os.makedirs(job_dir)
            log_to_file(f"Created job directory: {job_dir}")
        except Exception as e:
            log_to_file(f"Error creating job directory: {str(e)}")
            show_flame_message(f"Error creating temp directory: {str(e)}")
            return
        
        # Check if ComfyUI is running
        if not is_comfyui_running():
            log_to_file("ComfyUI server is not running")
            show_flame_message("Error: ComfyUI server is not running at " + COMFYUI_URL)
            return
            
        # Export frames from clip - now returns the path to the first image
        export_successful, image_path = export_frame(item, job_dir)
        
        if not export_successful or not image_path:
            log_to_file("Failed to export frames from clip")
            show_flame_message("Failed to export frames from clip")
            return
        
        log_to_file(f"Image exported to: {image_path}")
        show_flame_message("Starting ComfyUI processing... Please wait and don't close Flame.")
        
        # Get Flame version to decide on threading approach
        flame_version = get_flame_version()
        
        # For Flame 2023.2 or older, run processing synchronously (no threading)
        if flame_version.startswith("2023") or flame_version.startswith("2022") or flame_version.startswith("2021"):
            log_to_file(f"Running in synchronous mode for Flame {flame_version}")
            
            # Execute processing directly (no background thread)
            try:
                # Process with ComfyUI using the workflow
                log_to_file("Starting synchronous ComfyUI processing")
                output_path = process_with_comfyui_api_with_workflow(image_path, job_dir, workflow)
                
                # After processing with ComfyUI:
                comfla_dir = os.path.join(COMFYUI_OUTPUT_DIR, "comfla")
                
                # Check if directory exists and has any files - improved error handling
                if os.path.exists(comfla_dir):
                    png_files = [f for f in os.listdir(comfla_dir) if f.endswith('.png')]
                    if png_files:
                        log_to_file(f"Found {len(png_files)} PNG files in {comfla_dir}")
                        try:
                            # Import results directly
                            import_result = import_png_sequence(selection)
                            if import_result:
                                show_flame_message("Successfully imported PNG sequence!")
                            else:
                                show_flame_message("Failed to import PNG sequence.")
                        except Exception as e:
                            log_to_file(f"Error importing results: {str(e)}")
                            log_to_file(traceback.format_exc())
                            show_flame_message(f"Error during import: {str(e)}")
                    else:
                        show_flame_message("No PNG files found in output directory")
                        log_to_file(f"Directory exists but no PNG files found in {comfla_dir}")
                else:
                    show_flame_message("Output directory not found. Processing may have failed.")
                    log_to_file(f"Output directory not found: {comfla_dir}")
            except Exception as e:
                log_to_file(f"Error in synchronous processing: {str(e)}")
                log_to_file(traceback.format_exc())
                show_flame_message(f"Error during processing: {str(e)}")
        else:
            # For newer Flame versions, use background threading as before
            log_to_file(f"Using background threading for Flame {flame_version}")
            
            # Create a callback function for the background process
            def background_process():
                try:
                    # Process with ComfyUI using the workflow
                    # Pass the loaded workflow directly instead of the path
                    output_path = process_with_comfyui_api_with_workflow(image_path, job_dir, workflow)

                    # After processing with ComfyUI:
                    comfla_dir = os.path.join(COMFYUI_OUTPUT_DIR, "comfla")
                    
                    # Check if directory exists and has any files - improved error handling
                    if os.path.exists(comfla_dir):
                        png_files = [f for f in os.listdir(comfla_dir) if f.endswith('.png')]
                        if png_files:
                            log_to_file(f"Found {len(png_files)} PNG files in {comfla_dir}")
                            try:
                                # Create a callback for importing the results
                                def import_results():
                                    try:
                                        import_result = import_png_sequence(selection)
                                        if import_result:
                                            show_flame_message("Successfully imported PNG sequence!")
                                        else:
                                            show_flame_message("Failed to import PNG sequence.")
                                    except Exception as e:
                                        log_to_file(f"Error in import callback: {str(e)}")
                                        show_flame_message(f"Error during import: {str(e)}")
                                
                                # Use PyCallback to run import on main thread
                                if hasattr(flame, 'PyCallback'):
                                    flame.PyCallback(import_results)
                                else:
                                    # Fallback to direct call if PyCallback not available
                                    import_results()
                                
                            except Exception as e:
                                log_to_file(f"Error scheduling import: {str(e)}")
                                show_flame_message(f"Error scheduling import: {str(e)}")
                        else:
                            show_flame_message("No PNG files found in output directory")
                            log_to_file(f"Directory exists but no PNG files found in {comfla_dir}")
                    else:
                        show_flame_message("Output directory not found. Processing may have failed.")
                        log_to_file(f"Output directory not found: {comfla_dir}")
                        
                except Exception as e:
                    log_to_file(f"Error in background process: {str(e)}")
                    log_to_file(traceback.format_exc())
                    show_flame_message(f"Error during processing: {str(e)}")
            
            # Create and start background thread
            background_thread = threading.Thread(target=background_process)
            background_thread.daemon = True  # Make thread daemon so it doesn't block program exit
            background_thread.start()
            
            show_flame_message("Processing started in background.\nYou can continue working while ComfyUI processes your frames.")
        
    except Exception as e:
        log_to_file(f"Error in process_with_comfyui: {str(e)}")
        log_to_file(traceback.format_exc())
        show_flame_message(f"Error: {str(e)}")

# ...existing code...