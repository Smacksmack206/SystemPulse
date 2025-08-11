# start_systempulse.py
# A single, self-contained script to set up the project structure and run the app.

import os
import textwrap
import uvicorn
import psutil
import time
import platform
import socket
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# ==============================================================================
# PART 1: PROJECT SETUP LOGIC
# This section defines the project structure and creates it if it doesn't exist.
# ==============================================================================

PROJECT_ROOT = "systempulse"

# The proposed project structure as a dictionary
PROJECT_STRUCTURE = {
    "config": ["settings.yaml"],
    "frontend": ["src/", "static/", "svelte.config.js"],
    "scripts": ["build_app.sh"],
    "src": [
        "__init__.py",
        "api/__init__.py", "api/system.py", "api/network.py",
        "core/__init__.py", "core/analysis.py", "core/cleaner.py", "core/scanner.py",
        "models/__init__.py", "models/system_models.py",
        "utils/__init__.py", "utils/helpers.py"
    ],
    "tests": ["__init__.py", "test_api.py", "test_core.py"]
}

# Content for some of the initial files
FILE_CONTENT = {
    "pyproject.toml": textwrap.dedent("""
        [project]
        name = "systempulse"
        version = "0.1.0"
        description = "A modern system utility and monitoring tool."
        dependencies = [
            "fastapi",
            "uvicorn[standard]",
            "psutil",
        ]
    """),
    "README.md": "# SystemPulse\nA modern system utility and monitoring tool.",
    ".gitignore": textwrap.dedent("""
        __pycache__/
        *.pyc
        .env
        /dist
        /build
        *.spec
        venv/
    """)
}

def setup_project_if_needed():
    """Checks for the project root directory and creates the full structure if not found."""
    if os.path.exists(PROJECT_ROOT):
        return

    print(f"Creating project structure in './{PROJECT_ROOT}'...")
    os.makedirs(PROJECT_ROOT)

    # Create directories and nested files first
    for parent, items in PROJECT_STRUCTURE.items():
        parent_path = os.path.join(PROJECT_ROOT, parent)
        os.makedirs(parent_path, exist_ok=True)
        for item in items:
            # Check if it's a directory (ends with /) or a file
            if item.endswith('/'):
                # It's a directory
                dir_path = os.path.join(parent_path, item.rstrip('/'))
                os.makedirs(dir_path, exist_ok=True)
                print(f"  Created directory: {dir_path}")
            elif "/" in item:
                # It's a nested file
                path_parts = item.split('/')
                dir_path = os.path.join(parent_path, *path_parts[:-1])
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                
                file_path = os.path.join(parent_path, item)
                with open(file_path, 'w') as f:
                    # Add a placeholder comment to empty python files
                    if item.endswith('.py'):
                        f.write("# Placeholder\n")
                print(f"  Created file: {file_path}")
            else:
                # It's a regular file in the parent directory
                file_path = os.path.join(parent_path, item)
                with open(file_path, 'w') as f:
                    # Add a placeholder comment to empty python files
                    if item.endswith('.py'):
                        f.write("# Placeholder\n")
                print(f"  Created file: {file_path}")

    # Create root files after directories are created
    for filename, content in FILE_CONTENT.items():
        with open(os.path.join(PROJECT_ROOT, filename), 'w') as f:
            f.write(content.strip())
        print(f"  Created file: {os.path.join(PROJECT_ROOT, filename)}")

    print("\nProject setup complete.")


# ==============================================================================
# PART 2: FastAPI APPLICATION
# This is the actual web server and UI.
# ==============================================================================

app = FastAPI()

# --- HTML, CSS, and JavaScript for the Frontend ---
# This is all embedded here for simplicity.
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SystemPulse</title>
    <style>  
      /* Basic Reset & Font */
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            transition: background-color 0.3s, color 0.3s;
        }

        /* --- Theme Palettes --- */
        /* 1. Clarity (Default) */
        body.theme-clarity { background-color: #F2F2F7; color: #333333; }
        .theme-clarity .header { background-color: #FFFFFF; border-bottom: 1px solid #E5E5EA; }
        .theme-clarity .card { background-color: #FFFFFF; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .theme-clarity .primary-accent { color: #0A84FF; }
        .theme-clarity select { border: 1px solid #D1D1D6; background-color: #FFFFFF; color: #333; }
        .theme-clarity .connection-item { border-bottom: 1px solid #E5E5EA; }

        /* 2. Operator */
        body.theme-operator { background-color: #1E1E1E; color: #E0E0E0; font-family: "SF Mono", "Fira Code", "Source Code Pro", monospace; }
        .theme-operator .header { background-color: #252526; border-bottom: 1px solid #3A3A3A; }
        .theme-operator .card { background-color: #252526; border: 1px solid #3A3A3A; box-shadow: none; }
        .theme-operator .primary-accent { color: #39FF14; }
        .theme-operator select { border: 1px solid #5A5A5A; background-color: #2D2D2D; color: #E0E0E0; }
        .theme-operator .connection-item { border-bottom: 1px solid #3A3A3A; }

        /* 3. Neo-Kyoto */
        body.theme-neo-kyoto { background-color: #0D0221; color: #F0F0F0; }
        .theme-neo-kyoto .header { background-color: rgba(13, 2, 33, 0.8); border-bottom: 1px solid #F900F9; backdrop-filter: blur(10px); }
        .theme-neo-kyoto .card { background-color: rgba(255,255,255,0.05); border: 1px solid #00F5D4; box-shadow: 0 0 15px rgba(0, 245, 212, 0.2); }
        .theme-neo-kyoto .primary-accent { color: #F900F9; }
        .theme-neo-kyoto select { border: 1px solid #F900F9; background-color: #1A0A3A; color: #F0F0F0; }
        .theme-neo-kyoto .connection-item { border-bottom: 1px solid rgba(0, 245, 212, 0.3); }

        /* 4. Ocean Sunset (Teal & Pink) */
        body.theme-ocean-sunset { background: linear-gradient(135deg, #0D4F8C 0%, #2E8B8B 50%, #FF6B9D 100%); color: #FFFFFF; }
        .theme-ocean-sunset .header { background-color: rgba(13, 79, 140, 0.9); border-bottom: 1px solid #2E8B8B; backdrop-filter: blur(10px); }
        .theme-ocean-sunset .card { background-color: rgba(255, 255, 255, 0.1); border: 1px solid #2E8B8B; box-shadow: 0 8px 32px rgba(46, 139, 139, 0.3); backdrop-filter: blur(10px); }
        .theme-ocean-sunset .primary-accent { color: #FF6B9D; }
        .theme-ocean-sunset select { border: 1px solid #2E8B8B; background-color: rgba(46, 139, 139, 0.3); color: #FFFFFF; }
        .theme-ocean-sunset .connection-item { border-bottom: 1px solid rgba(46, 139, 139, 0.3); }

        /* 5. Forest Fire (Green & Orange) */
        body.theme-forest-fire { background: linear-gradient(135deg, #1B4332 0%, #2D5016 50%, #FF8500 100%); color: #F1FAEE; }
        .theme-forest-fire .header { background-color: rgba(27, 67, 50, 0.9); border-bottom: 1px solid #52B788; backdrop-filter: blur(10px); }
        .theme-forest-fire .card { background-color: rgba(241, 250, 238, 0.1); border: 1px solid #52B788; box-shadow: 0 8px 32px rgba(82, 183, 136, 0.2); backdrop-filter: blur(10px); }
        .theme-forest-fire .primary-accent { color: #FF8500; }
        .theme-forest-fire select { border: 1px solid #52B788; background-color: rgba(82, 183, 136, 0.3); color: #F1FAEE; }
        .theme-forest-fire .connection-item { border-bottom: 1px solid rgba(82, 183, 136, 0.3); }

        /* 6. Midnight Aurora (Purple & Blue) */
        body.theme-midnight-aurora { background: linear-gradient(135deg, #1A0B3D 0%, #3C1A78 50%, #00D4FF 100%); color: #E8E3FF; }
        .theme-midnight-aurora .header { background-color: rgba(26, 11, 61, 0.9); border-bottom: 1px solid #7B2CBF; backdrop-filter: blur(10px); }
        .theme-midnight-aurora .card { background-color: rgba(232, 227, 255, 0.1); border: 1px solid #7B2CBF; box-shadow: 0 8px 32px rgba(123, 44, 191, 0.3); backdrop-filter: blur(10px); }
        .theme-midnight-aurora .primary-accent { color: #00D4FF; }
        .theme-midnight-aurora select { border: 1px solid #7B2CBF; background-color: rgba(123, 44, 191, 0.3); color: #E8E3FF; }
        .theme-midnight-aurora .connection-item { border-bottom: 1px solid rgba(123, 44, 191, 0.3); } 
       /* --- Layout & Components --- */
        .header { padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 10; }
        .header h1 { margin: 0; font-size: 1.5rem; }
        .header-controls { display: flex; align-items: center; gap: 2rem; }
        .theme-selector label { margin-right: 0.5rem; font-size: 0.9rem; opacity: 0.8; }
        select { padding: 0.5rem; border-radius: 8px; font-size: 0.9rem; cursor: pointer; }
        
        /* Navigation Tabs */
        .nav-tabs { display: flex; gap: 0.5rem; }
        .nav-tab { padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; font-size: 0.9rem; transition: all 0.2s; }
        .nav-tab.active { font-weight: bold; }
        .theme-clarity .nav-tab { background-color: #E5E5EA; color: #333; }
        .theme-clarity .nav-tab.active { background-color: #0A84FF; color: white; }
        .theme-operator .nav-tab { background-color: #3A3A3A; color: #E0E0E0; }
        .theme-operator .nav-tab.active { background-color: #39FF14; color: #1E1E1E; }
        .theme-neo-kyoto .nav-tab { background-color: rgba(255,255,255,0.1); color: #F0F0F0; }
        .theme-neo-kyoto .nav-tab.active { background-color: #F900F9; color: #0D0221; }
        .theme-ocean-sunset .nav-tab { background-color: rgba(46, 139, 139, 0.3); color: #FFFFFF; }
        .theme-ocean-sunset .nav-tab.active { background-color: #FF6B9D; color: #0D4F8C; }
        .theme-forest-fire .nav-tab { background-color: rgba(82, 183, 136, 0.3); color: #F1FAEE; }
        .theme-forest-fire .nav-tab.active { background-color: #FF8500; color: #1B4332; }
        .theme-midnight-aurora .nav-tab { background-color: rgba(123, 44, 191, 0.3); color: #E8E3FF; }
        .theme-midnight-aurora .nav-tab.active { background-color: #00D4FF; color: #1A0B3D; }
        
        .dashboard { padding: 2rem; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
        .dashboard-section { display: none; }
        .dashboard-section.active { display: grid; }
        .card { padding: 1.5rem; border-radius: 12px; transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .card h2 { margin-top: 0; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; }
        .card .value { font-size: 2.5rem; font-weight: 600; }
        
        /* Network Card Specifics */
        .network-card { grid-column: 1 / -1; } /* Span full width */
        .network-list { max-height: 250px; overflow-y: auto; padding-right: 10px; }
        .connection-item { display: flex; justify-content: space-between; padding: 0.75rem 0.25rem; font-size: 0.9rem; }
        .connection-item:last-child { border-bottom: none; }
        .connection-address { flex: 1; }
        .connection-status { font-weight: bold; min-width: 120px; text-align: right; }

        /* File Cleaner Card Specifics */
        .file-cleaner-card { grid-column: 1 / -1; } /* Span full width */
        .file-list { max-height: 300px; overflow-y: auto; padding-right: 10px; }
        .file-item { display: flex; align-items: center; padding: 0.75rem 0.25rem; font-size: 0.9rem; }
        .file-item:last-child { border-bottom: none; }
        .file-checkbox { margin-right: 1rem; }
        .file-info { flex: 1; display: flex; justify-content: space-between; }
        .file-path { flex: 1; word-break: break-all; }
        .file-size { font-weight: bold; min-width: 100px; text-align: right; margin-left: 1rem; }
        .file-actions { margin-top: 1rem; display: flex; gap: 1rem; }
        .btn { padding: 0.75rem 1.5rem; border: none; border-radius: 8px; cursor: pointer; font-size: 0.9rem; transition: opacity 0.2s; }
        .btn:hover { opacity: 0.8; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-scan { background-color: #0A84FF; color: white; }
        .btn-delete { background-color: #FF3B30; color: white; }
        .theme-operator .btn-scan { background-color: #39FF14; color: #1E1E1E; }
        .theme-operator .btn-delete { background-color: #FF6B6B; color: #1E1E1E; }
        .theme-neo-kyoto .btn-scan { background-color: #00F5D4; color: #0D0221; }
        .theme-neo-kyoto .btn-delete { background-color: #F900F9; color: #0D0221; }
        .theme-ocean-sunset .btn-scan { background-color: #2E8B8B; color: white; }
        .theme-ocean-sunset .btn-delete { background-color: #FF6B9D; color: white; }
        .theme-forest-fire .btn-scan { background-color: #52B788; color: white; }
        .theme-forest-fire .btn-delete { background-color: #FF8500; color: white; }
        .theme-midnight-aurora .btn-scan { background-color: #7B2CBF; color: white; }
        .theme-midnight-aurora .btn-delete { background-color: #00D4FF; color: #1A0B3D; }
        .loading { opacity: 0.6; } 
       /* Container Management Specifics */
        .container-item { display: flex; justify-content: space-between; align-items: center; padding: 1rem; margin-bottom: 0.5rem; border-radius: 8px; }
        .container-info { flex: 1; }
        .container-name { font-weight: bold; }
        .container-image { opacity: 0.7; font-size: 0.9rem; }
        .container-status { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; margin-right: 0.5rem; }
        .status-running { background-color: #28a745; color: white; }
        .status-stopped { background-color: #6c757d; color: white; }
        .status-paused { background-color: #ffc107; color: black; }
        .container-actions { display: flex; gap: 0.25rem; }
        .btn-container { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
        .container-selection { margin-right: 1rem; }

        /* File Browser Specifics */
        .file-browser { margin-top: 2rem; }
        .file-browser-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .current-path { font-family: monospace; padding: 0.5rem; border-radius: 4px; flex: 1; margin-right: 1rem; }
        .theme-clarity .current-path { background-color: #F8F8F8; border: 1px solid #D1D1D6; }
        .theme-operator .current-path { background-color: #2D2D2D; border: 1px solid #5A5A5A; color: #E0E0E0; }
        .theme-neo-kyoto .current-path { background-color: rgba(255,255,255,0.1); border: 1px solid #F900F9; color: #F0F0F0; }
        .theme-ocean-sunset .current-path { background-color: rgba(46, 139, 139, 0.3); border: 1px solid #2E8B8B; color: #FFFFFF; }
        .theme-forest-fire .current-path { background-color: rgba(82, 183, 136, 0.3); border: 1px solid #52B788; color: #F1FAEE; }
        .theme-midnight-aurora .current-path { background-color: rgba(123, 44, 191, 0.3); border: 1px solid #7B2CBF; color: #E8E3FF; }
        
        .file-browser-controls { display: flex; gap: 0.5rem; }
        .btn-small { padding: 0.5rem 1rem; font-size: 0.8rem; }
        .file-browser-list { max-height: 400px; overflow-y: auto; }
        .file-browser-item { display: flex; align-items: center; padding: 0.5rem; cursor: pointer; border-radius: 4px; margin-bottom: 2px; }
        .file-browser-item:hover { opacity: 0.8; }
        .theme-clarity .file-browser-item:hover { background-color: #F0F0F0; }
        .theme-operator .file-browser-item:hover { background-color: #3A3A3A; }
        .theme-neo-kyoto .file-browser-item:hover { background-color: rgba(255,255,255,0.1); }
        .theme-ocean-sunset .file-browser-item:hover { background-color: rgba(46, 139, 139, 0.2); }
        .theme-forest-fire .file-browser-item:hover { background-color: rgba(82, 183, 136, 0.2); }
        .theme-midnight-aurora .file-browser-item:hover { background-color: rgba(123, 44, 191, 0.2); }
        
        .file-icon { margin-right: 0.5rem; font-size: 1.2rem; }
        .file-name { flex: 1; }
        .file-size-small { font-size: 0.8rem; opacity: 0.7; min-width: 80px; text-align: right; }
        .file-date { font-size: 0.8rem; opacity: 0.7; min-width: 120px; text-align: right; margin-left: 1rem; }
        .hidden-file { opacity: 0.6; }
        .selected-file { font-weight: bold; }
        .theme-clarity .selected-file { background-color: #0A84FF; color: white; }
        .theme-operator .selected-file { background-color: #39FF14; color: #1E1E1E; }
        .theme-neo-kyoto .selected-file { background-color: #F900F9; color: #0D0221; }
        .theme-ocean-sunset .selected-file { background-color: #FF6B9D; color: white; }
        .theme-forest-fire .selected-file { background-color: #FF8500; color: white; }
        .theme-midnight-aurora .selected-file { background-color: #00D4FF; color: #1A0B3D; }

        /* Media Player Specifics */
        .media-player { margin-top: 1rem; }
        .media-controls { display: flex; gap: 0.5rem; margin-bottom: 1rem; align-items: center; }
        .media-file-input { flex: 1; }
        .media-display { text-align: center; padding: 2rem; border-radius: 8px; min-height: 300px; display: flex; align-items: center; justify-content: center; }
        .theme-clarity .media-display { background-color: #F8F8F8; border: 2px dashed #D1D1D6; }
        .theme-operator .media-display { background-color: #2D2D2D; border: 2px dashed #5A5A5A; }
        .theme-neo-kyoto .media-display { background-color: rgba(255,255,255,0.05); border: 2px dashed #F900F9; }
        .theme-ocean-sunset .media-display { background-color: rgba(46, 139, 139, 0.2); border: 2px dashed #2E8B8B; }
        .theme-forest-fire .media-display { background-color: rgba(82, 183, 136, 0.2); border: 2px dashed #52B788; }
        .theme-midnight-aurora .media-display { background-color: rgba(123, 44, 191, 0.2); border: 2px dashed #7B2CBF; }

        /* Network Tools Specifics */
        .network-tool { margin-bottom: 2rem; }
        .network-input { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        .network-input input { flex: 1; padding: 0.5rem; border-radius: 4px; }
        .network-output { max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 0.9rem; padding: 1rem; border-radius: 4px; }
        .theme-clarity .network-output { background-color: #F8F8F8; border: 1px solid #D1D1D6; }
        .theme-operator .network-output { background-color: #2D2D2D; border: 1px solid #5A5A5A; color: #E0E0E0; }
        .theme-neo-kyoto .network-output { background-color: rgba(255,255,255,0.05); border: 1px solid #F900F9; color: #F0F0F0; }
        .theme-ocean-sunset .network-output { background-color: rgba(46, 139, 139, 0.3); border: 1px solid #2E8B8B; color: #FFFFFF; }
        .theme-forest-fire .network-output { background-color: rgba(82, 183, 136, 0.3); border: 1px solid #52B788; color: #F1FAEE; }
        .theme-midnight-aurora .network-output { background-color: rgba(123, 44, 191, 0.3); border: 1px solid #7B2CBF; color: #E8E3FF; }
    </style>
</head>
<body class="theme-clarity"> 
   <header class="header">
        <h1>System<span class="primary-accent">Pulse</span></h1>
        <div class="header-controls">
            <div class="nav-tabs">
                <div class="nav-tab active" data-tab="system">System Monitor</div>
                <div class="nav-tab" data-tab="processes">Processes</div>
                <div class="nav-tab" data-tab="disk">Disk Analyzer</div>
                <div class="nav-tab" data-tab="network">Network Tools</div>
                <div class="nav-tab" data-tab="files">File Manager</div>
                <div class="nav-tab" data-tab="containers">Containers</div>
                <div class="nav-tab" data-tab="media">Media Player</div>
                <div class="nav-tab" data-tab="info">System Info</div>
            </div>
            <div class="theme-selector">
                <label for="theme-select">Theme:</label>
                <select id="theme-select">
                    <option value="clarity">Clarity</option>
                    <option value="operator">Operator</option>
                    <option value="neo-kyoto">Neo-Kyoto</option>
                    <option value="ocean-sunset">Ocean Sunset</option>
                    <option value="forest-fire">Forest Fire</option>
                    <option value="midnight-aurora">Midnight Aurora</option>
                </select>
            </div>
        </div>
    </header>

    <main class="dashboard">
        <!-- System Monitor Dashboard -->
        <div id="system-dashboard" class="dashboard-section active">
            <div class="card">
                <h2>CPU Usage</h2>
                <p id="cpu-usage" class="value">--%</p>
            </div>
            <div class="card">
                <h2>Memory Usage</h2>
                <p id="mem-usage" class="value">--%</p>
            </div>
            <div class="card">
                <h2>Disk Usage</h2>
                <p id="disk-usage" class="value">--%</p>
            </div>
            <div class="card network-card">
                <h2>Active Connections</h2>
                <div id="network-list" class="network-list">
                    <!-- Network data will be injected here by JavaScript -->
                </div>
            </div>
        </div>

        <!-- Process Monitor Dashboard -->
        <div id="processes-dashboard" class="dashboard-section">
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Running Processes</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Monitor and manage running processes on your system.</p>
                <div class="process-list" id="process-list">
                    <p>Loading processes...</p>
                </div>
            </div>
        </div>

        <!-- Disk Analyzer Dashboard -->
        <div id="disk-dashboard" class="dashboard-section">
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Disk Usage Analysis</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Analyze disk usage across all mounted drives and directories.</p>
                <div id="disk-list">
                    <p>Loading disk information...</p>
                </div>
            </div>
        </div> 
       <!-- Network Tools Dashboard -->
        <div id="network-dashboard" class="dashboard-section">
            <div class="card">
                <h2>Ping Tool</h2>
                <div class="network-tool">
                    <div class="network-input">
                        <input type="text" id="ping-host" placeholder="Enter hostname or IP address" value="google.com">
                        <button id="ping-btn" class="btn btn-scan">Ping</button>
                        <button id="ping-stop-btn" class="btn btn-delete" disabled>Stop</button>
                    </div>
                    <div id="ping-output" class="network-output">Ready to ping...</div>
                </div>
            </div>
            <div class="card">
                <h2>Traceroute</h2>
                <div class="network-tool">
                    <div class="network-input">
                        <input type="text" id="traceroute-host" placeholder="Enter hostname or IP address" value="google.com">
                        <button id="traceroute-btn" class="btn btn-scan">Traceroute</button>
                    </div>
                    <div id="traceroute-output" class="network-output">Ready to trace route...</div>
                </div>
            </div>
            <div class="card network-card">
                <h2>Network Interfaces</h2>
                <div class="network-stats" id="network-interfaces">
                    <p>Loading network interfaces...</p>
                </div>
            </div>
            <div class="card network-card">
                <h2>Active Connections</h2>
                <div id="network-connections" class="network-list">
                    <p>Loading connections...</p>
                </div>
            </div>
            <div class="card">
                <h2>Packet Capture</h2>
                <div class="network-tool">
                    <div class="network-input">
                        <select id="capture-interface">
                            <option value="">Select interface...</option>
                        </select>
                        <button id="capture-start-btn" class="btn btn-scan">Start Capture</button>
                        <button id="capture-stop-btn" class="btn btn-delete" disabled>Stop</button>
                    </div>
                    <div id="capture-output" class="network-output">Select an interface to start packet capture...</div>
                </div>
            </div>
        </div>

        <!-- File Manager Dashboard -->
        <div id="files-dashboard" class="dashboard-section">
            <div class="card file-cleaner-card">
                <h2>System File Browser</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Browse and manage files throughout your entire system. Execute files, view content, and manage permissions.</p>
                <div class="file-browser">
                    <div class="file-browser-header">
                        <input type="text" id="current-path" class="current-path" readonly>
                        <div class="file-browser-controls">
                            <button id="root-btn" class="btn btn-small btn-scan">Root</button>
                            <button id="home-btn" class="btn btn-small btn-scan">Home</button>
                            <button id="up-btn" class="btn btn-small btn-scan">Up</button>
                            <button id="refresh-btn" class="btn btn-small btn-scan">Refresh</button>
                            <button id="execute-btn" class="btn btn-small execute-btn" disabled>Execute</button>
                            <button id="delete-selected-btn" class="btn btn-small btn-delete" disabled>Delete Selected</button>
                        </div>
                    </div>
                    <div id="file-browser-list" class="file-browser-list">
                        <p>Loading files...</p>
                    </div>
                    <div id="file-preview" class="file-preview" style="display: none;">
                        <h3>File Preview</h3>
                        <div id="preview-content"></div>
                    </div>
                </div>
            </div>
            <div class="card file-cleaner-card">
                <h2>Large File Scanner</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Find and manage files larger than 100MB. Use this tool to free up disk space.</p>
                <div class="file-actions">
                    <button id="scan-btn" class="btn btn-scan">Scan for Large Files</button>
                    <button id="delete-btn" class="btn btn-delete" disabled>Delete Selected Files</button>
                </div>
                <div id="file-list" class="file-list">
                    <p>Click "Scan for Large Files" to find files larger than 100MB.</p>
                </div>
                <div id="scan-stats" style="margin-top: 1rem;">
                    <p><strong>Files Found:</strong> <span id="files-count">0</span></p>
                    <p><strong>Total Size:</strong> <span id="total-size">0 B</span></p>
                    <p><strong>Largest File:</strong> <span id="largest-file">None</span></p>
                </div>
            </div>
        </div> 
       <!-- Container Management Dashboard -->
        <div id="containers-dashboard" class="dashboard-section">
            <div class="card">
                <h2>Docker Hub Search</h2>
                <div class="network-input" style="margin-bottom: 1rem;">
                    <input type="text" id="docker-search-input" placeholder="Search Docker Hub (e.g., nginx, postgres)">
                    <button id="docker-search-btn" class="btn btn-scan">Search</button>
                </div>
                <div id="docker-search-results" class="file-browser-list" style="max-height: 200px;">
                    <p>Enter a search term to find Docker images</p>
                </div>
            </div>
            <div class="card">
                <h2>Run New Container</h2>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                    <input type="text" id="run-image-input" placeholder="Image name (e.g., nginx:latest)">
                    <input type="text" id="run-name-input" placeholder="Container name (optional)">
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                    <input type="text" id="run-ports-input" placeholder="Ports (e.g., 8080:80)">
                    <input type="text" id="run-volumes-input" placeholder="Volumes (e.g., /host:/container)">
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                    <select id="run-platform-select">
                        <option value="linux/amd64">Linux AMD64</option>
                        <option value="linux/arm64">Linux ARM64</option>
                        <option value="darwin/amd64">macOS Intel</option>
                        <option value="darwin/arm64">macOS Apple Silicon</option>
                    </select>
                    <select id="run-runtime-select">
                        <option value="docker">Docker Runtime</option>
                        <option value="containerd">Containerd</option>
                        <option value="virtualization-framework">Apple Virtualization</option>
                    </select>
                </div>
                <button id="run-container-btn" class="btn btn-scan">Run Container</button>
            </div>
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Container Management</h2>
                <div class="file-actions" style="margin-bottom: 2rem;">
                    <button id="refresh-containers-btn" class="btn btn-scan">Refresh</button>
                    <button id="start-selected-btn" class="btn btn-scan" disabled>Start Selected</button>
                    <button id="stop-selected-btn" class="btn btn-delete" disabled>Stop Selected</button>
                    <button id="pause-selected-btn" class="btn btn-delete" disabled>Pause Selected</button>
                    <button id="delete-selected-btn" class="btn btn-delete" disabled>Delete Selected</button>
                    <button id="select-all-btn" class="btn btn-small btn-scan">Select All</button>
                </div>
                <div id="containers-list">
                    <p>Loading containers...</p>
                </div>
            </div>
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Docker Images</h2>
                <div class="file-actions" style="margin-bottom: 1rem;">
                    <button id="refresh-images-btn" class="btn btn-scan">Refresh Images</button>
                    <button id="delete-image-btn" class="btn btn-delete" disabled>Delete Selected Image</button>
                </div>
                <div id="images-list" class="file-browser-list" style="max-height: 300px;">
                    <p>Loading images...</p>
                </div>
            </div>
        </div>

        <!-- Media Player Dashboard -->
        <div id="media-dashboard" class="dashboard-section">
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Media Player</h2>
                <div class="media-player">
                    <div class="media-controls">
                        <input type="file" id="media-file-input" class="media-file-input" accept="audio/*,video/*,image/*,.mkv,.avi,.mov,.wmv,.flv,.webm">
                        <button id="play-btn" class="btn btn-scan" disabled>Play</button>
                        <button id="pause-btn" class="btn btn-delete" disabled>Pause</button>
                        <button id="stop-btn" class="btn btn-delete" disabled>Stop</button>
                    </div>
                    <div id="media-display" class="media-display">
                        <p>Select a media file to play</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- System Info Dashboard -->
        <div id="info-dashboard" class="dashboard-section">
            <div class="card">
                <h2>System Information</h2>
                <div class="info-grid" id="system-info">
                    <p>Loading system information...</p>
                </div>
            </div>
            <div class="card">
                <h2>Hardware Information</h2>
                <div class="info-grid" id="hardware-info">
                    <p>Loading hardware information...</p>
                </div>
            </div>
        </div>
    </main> 
   <script>
        // --- Theme Switcher Logic ---
        const themeSelector = document.getElementById('theme-select');
        const body = document.body;

        themeSelector.addEventListener('change', (event) => {
            body.className = ''; // Clear existing theme classes
            body.classList.add(`theme-${event.target.value}`);
        });

        // --- Navigation Logic ---
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // Remove active class from all tabs and sections
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active'));
                
                // Add active class to clicked tab
                tab.classList.add('active');
                
                // Show corresponding dashboard section
                const tabName = tab.dataset.tab;
                document.getElementById(`${tabName}-dashboard`).classList.add('active');
            });
        });

        // --- Data Fetching Logic ---
        function updateSystemInfo() {
            fetch('/api/system')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('cpu-usage').textContent = `${data.cpu_percent}%`;
                    document.getElementById('mem-usage').textContent = `${data.memory_percent}%`;
                    document.getElementById('disk-usage').textContent = `${data.disk_percent}%`;
                })
                .catch(error => console.error('Error fetching system info:', error));
        }
        
        function updateNetworkInfo() {
            fetch('/api/network')
                .then(response => response.json())
                .then(connections => {
                    const listElement = document.getElementById('network-list');
                    listElement.innerHTML = ''; // Clear old data

                    if (connections.length === 0) {
                        listElement.innerHTML = '<p>No active connections found.</p>';
                        return;
                    }

                    connections.forEach(conn => {
                        const item = document.createElement('div');
                        item.className = 'connection-item';
                        
                        const localAddr = conn.local_address.replace('::ffff:', ''); // Clean up IPv6 mapped IPv4
                        const remoteAddr = conn.remote_address.replace('::ffff:', '');

                        item.innerHTML = `
                            <span class="connection-address"><b>${localAddr}</b> &#8594; ${remoteAddr}</span>
                            <span class="connection-status">${conn.status}</span>
                        `;
                        listElement.appendChild(item);
                    });
                })
                .catch(error => console.error('Error fetching network info:', error));
        }

        // --- File Cleaner Logic ---
        let scannedFiles = [];
        
        function formatFileSize(bytes) {
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            if (bytes === 0) return '0 B';
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        function updateFileList(files) {
            const listElement = document.getElementById('file-list');
            listElement.innerHTML = '';
            
            if (files.length === 0) {
                listElement.innerHTML = '<p>No large files found (>100MB).</p>';
                updateScanStats(files);
                return;
            }
            
            files.forEach((file, index) => {
                const item = document.createElement('div');
                item.className = 'file-item connection-item';
                
                // Shorten the file path for display
                const shortPath = file.path.length > 60 ? '...' + file.path.slice(-57) : file.path;
                
                item.innerHTML = `
                    <input type="checkbox" class="file-checkbox" data-index="${index}">
                    <div class="file-info">
                        <span class="file-path" title="${file.path}">${shortPath}</span>
                        <span class="file-size">${formatFileSize(file.size)}</span>
                    </div>
                `;
                listElement.appendChild(item);
            });
            
            // Add event listeners to checkboxes
            document.querySelectorAll('.file-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', updateDeleteButton);
            });
            
            updateScanStats(files);
        }    
    function updateScanStats(files) {
            document.getElementById('files-count').textContent = files.length;
            
            const totalSize = files.reduce((sum, file) => sum + file.size, 0);
            document.getElementById('total-size').textContent = formatFileSize(totalSize);
            
            if (files.length > 0) {
                const largestFile = files[0]; // Already sorted by size
                const shortPath = largestFile.path.split('/').pop(); // Just filename
                document.getElementById('largest-file').textContent = `${shortPath} (${formatFileSize(largestFile.size)})`;
            } else {
                document.getElementById('largest-file').textContent = 'None';
            }
        }
        
        function updateDeleteButton() {
            const checkedBoxes = document.querySelectorAll('.file-checkbox:checked');
            const deleteBtn = document.getElementById('delete-btn');
            deleteBtn.disabled = checkedBoxes.length === 0;
        }
        
        document.getElementById('scan-btn').addEventListener('click', async () => {
            const scanBtn = document.getElementById('scan-btn');
            const listElement = document.getElementById('file-list');
            
            scanBtn.disabled = true;
            scanBtn.textContent = 'Scanning...';
            listElement.innerHTML = '<p>Scanning for large files... This may take a moment.</p>';
            listElement.classList.add('loading');
            
            try {
                const response = await fetch('/api/files/scan');
                const files = await response.json();
                scannedFiles = files;
                updateFileList(files);
            } catch (error) {
                console.error('Error scanning files:', error);
                listElement.innerHTML = '<p>Error scanning files. Please try again.</p>';
            } finally {
                scanBtn.disabled = false;
                scanBtn.textContent = 'Scan for Large Files';
                listElement.classList.remove('loading');
            }
        });
        
        document.getElementById('delete-btn').addEventListener('click', async () => {
            const checkedBoxes = document.querySelectorAll('.file-checkbox:checked');
            const filesToDelete = Array.from(checkedBoxes).map(cb => 
                scannedFiles[parseInt(cb.dataset.index)]
            );
            
            if (filesToDelete.length === 0) return;
            
            const totalSize = filesToDelete.reduce((sum, file) => sum + file.size, 0);
            const confirmMessage = `Are you sure you want to delete ${filesToDelete.length} file(s)? This will free up ${formatFileSize(totalSize)} of space. This action cannot be undone.`;
            
            if (!confirm(confirmMessage)) return;
            
            const deleteBtn = document.getElementById('delete-btn');
            deleteBtn.disabled = true;
            deleteBtn.textContent = 'Deleting...';
            
            try {
                const response = await fetch('/api/files/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ files: filesToDelete.map(f => f.path) })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert(`Successfully deleted ${result.deleted_count} file(s).`);
                    // Refresh the file list
                    document.getElementById('scan-btn').click();
                } else {
                    alert(`Error: ${result.detail}`);
                }
            } catch (error) {
                console.error('Error deleting files:', error);
                alert('Error deleting files. Please try again.');
            } finally {
                deleteBtn.disabled = false;
                deleteBtn.textContent = 'Delete Selected Files';
            }
        });

        // Update functions based on active tab
        function updateActiveTab() {
            const activeTab = document.querySelector('.nav-tab.active').dataset.tab;
            
            switch(activeTab) {
                case 'system':
                    updateSystemInfo();
                    updateNetworkInfo();
                    break;
                case 'processes':
                    updateProcessList();
                    break;
                case 'disk':
                    updateDiskInfo();
                    break;
                case 'network':
                    updateNetworkInterfaces();
                    updateNetworkConnections();
                    break;
                case 'files':
                    loadFileBrowser(currentPath);
                    break;
                case 'containers':
                    updateContainers();
                    updateDockerImages();
                    break;
                case 'media':
                    initializeMediaPlayer();
                    break;
                case 'info':
                    updateSystemInfoPage();
                    break;
            }
        }

        // --- Process Monitor Logic ---
        function updateProcessList() {
            fetch('/api/processes')
                .then(response => response.json())
                .then(processes => {
                    const listElement = document.getElementById('process-list');
                    listElement.innerHTML = '';
                    
                    if (processes.length === 0) {
                        listElement.innerHTML = '<p>No processes found</p>';
                        return;
                    }
                    
                    processes.forEach(proc => {
                        const item = document.createElement('div');
                        item.className = 'connection-item';
                        
                        item.innerHTML = `
                            <div style="display: flex; justify-content: space-between; width: 100%;">
                                <span style="flex: 2;">${proc.name}</span>
                                <span style="flex: 1; text-align: center;">PID: ${proc.pid}</span>
                                <span style="flex: 1; text-align: center;">CPU: ${proc.cpu_percent}%</span>
                                <span style="flex: 1; text-align: right;">MEM: ${proc.memory_percent}%</span>
                            </div>
                        `;
                        listElement.appendChild(item);
                    });
                })
                .catch(error => {
                    console.error('Error fetching processes:', error);
                    document.getElementById('process-list').innerHTML = '<p>Error loading processes</p>';
                });
        }

        // --- Disk Analyzer Logic ---
        function updateDiskInfo() {
            fetch('/api/disk')
                .then(response => response.json())
                .then(disks => {
                    const listElement = document.getElementById('disk-list');
                    listElement.innerHTML = '';
                    
                    disks.forEach(disk => {
                        const item = document.createElement('div');
                        item.className = 'connection-item';
                        
                        const usedPercent = disk.percent;
                        
                        item.innerHTML = `
                            <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
                                <div style="flex: 2;">
                                    <div style="font-weight: bold;">${disk.device}</div>
                                    <div style="opacity: 0.7; font-size: 0.9rem;">${disk.mountpoint}</div>
                                </div>
                                <div style="flex: 2; text-align: center;">
                                    <div style="width: 100px; height: 8px; background: rgba(0,0,0,0.1); border-radius: 4px; overflow: hidden; margin: 0 auto;">
                                        <div style="width: ${usedPercent}%; height: 100%; background: #0A84FF; transition: width 0.3s;"></div>
                                    </div>
                                </div>
                                <div style="flex: 1; text-align: right;">
                                    <div>${formatFileSize(disk.used)} / ${formatFileSize(disk.total)}</div>
                                    <div>${usedPercent}% used</div>
                                </div>
                            </div>
                        `;
                        listElement.appendChild(item);
                    });
                })
                .catch(error => {
                    console.error('Error fetching disk info:', error);
                    document.getElementById('disk-list').innerHTML = '<p>Error loading disk information</p>';
                });
        }

        // --- Network Monitor Logic ---
        function updateNetworkInterfaces() {
            fetch('/api/network/interfaces')
                .then(response => response.json())
                .then(interfaces => {
                    const listElement = document.getElementById('network-interfaces');
                    listElement.innerHTML = '';
                    
                    Object.entries(interfaces).forEach(([name, stats]) => {
                        const item = document.createElement('div');
                        item.className = 'card';
                        item.style.padding = '1rem';
                        item.style.marginBottom = '0.5rem';
                        
                        item.innerHTML = `
                            <div style="font-weight: bold; margin-bottom: 0.5rem;">${name}</div>
                            <div style="font-size: 0.9rem; opacity: 0.8;">
                                <div>Sent: ${formatFileSize(stats.bytes_sent)}</div>
                                <div>Received: ${formatFileSize(stats.bytes_recv)}</div>
                                <div>Packets Sent: ${stats.packets_sent}</div>
                                <div>Packets Received: ${stats.packets_recv}</div>
                            </div>
                        `;
                        listElement.appendChild(item);
                    });
                })
                .catch(error => console.error('Error fetching network interfaces:', error));
        }

        function updateNetworkConnections() {
            fetch('/api/network')
                .then(response => response.json())
                .then(connections => {
                    const listElement = document.getElementById('network-connections');
                    listElement.innerHTML = '';

                    if (connections.length === 0) {
                        listElement.innerHTML = '<p>No active connections found.</p>';
                        return;
                    }

                    connections.forEach(conn => {
                        const item = document.createElement('div');
                        item.className = 'connection-item';
                        
                        const localAddr = conn.local_address.replace('::ffff:', '');
                        const remoteAddr = conn.remote_address.replace('::ffff:', '');

                        item.innerHTML = `
                            <span class="connection-address"><b>${localAddr}</b> &#8594; ${remoteAddr}</span>
                            <span class="connection-status">${conn.status}</span>
                        `;
                        listElement.appendChild(item);
                    });
                })
                .catch(error => console.error('Error fetching network connections:', error));
        }

        // --- Container Management Logic ---
        function updateContainers() {
            fetch('/api/containers')
                .then(response => response.json())
                .then(data => {
                    const listElement = document.getElementById('containers-list');
                    
                    if (!data.docker_installed) {
                        listElement.innerHTML = `<p>${data.message || 'Docker is not installed'}</p>`;
                        return;
                    }
                    
                    if (data.error) {
                        listElement.innerHTML = `<p>Error: ${data.error}</p>`;
                        return;
                    }
                    
                    if (data.containers.length === 0) {
                        listElement.innerHTML = '<p>No containers found</p>';
                        return;
                    }
                    
                    listElement.innerHTML = '';
                    data.containers.forEach(container => {
                        const item = document.createElement('div');
                        item.className = 'connection-item';
                        
                        const statusClass = container.state === 'running' ? 'status-running' : 
                                          container.state === 'paused' ? 'status-paused' : 'status-stopped';
                        
                        item.innerHTML = `
                            <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
                                <input type="checkbox" class="container-selection" data-id="${container.id}" style="margin-right: 1rem;">
                                <div style="flex: 2;">
                                    <div style="font-weight: bold;">${container.name}</div>
                                    <div style="opacity: 0.7; font-size: 0.9rem;">${container.image}</div>
                                </div>
                                <div style="flex: 1; text-align: center;">
                                    <span class="container-status ${statusClass}" style="padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">${container.state}</span>
                                </div>
                                <div style="flex: 1; text-align: right; opacity: 0.7; font-size: 0.9rem;">
                                    ${container.status}
                                </div>
                            </div>
                        `;
                        
                        listElement.appendChild(item);
                    });
                })
                .catch(error => {
                    console.error('Error fetching containers:', error);
                    document.getElementById('containers-list').innerHTML = '<p>Error loading containers</p>';
                });
        }
        
        function updateDockerImages() {
            fetch('/api/docker/images')
                .then(response => response.json())
                .then(data => {
                    const listElement = document.getElementById('images-list');
                    
                    if (data.error) {
                        listElement.innerHTML = `<p>Error: ${data.error}</p>`;
                        return;
                    }
                    
                    if (data.images.length === 0) {
                        listElement.innerHTML = '<p>No Docker images found</p>';
                        return;
                    }
                    
                    listElement.innerHTML = '';
                    data.images.forEach(image => {
                        const item = document.createElement('div');
                        item.className = 'file-browser-item';
                        
                        item.innerHTML = `
                            <input type="radio" name="selected-image" class="image-selection" data-id="${image.id}" style="margin-right: 0.5rem;">
                            <span class="file-icon">📦</span>
                            <div class="file-info">
                                <span class="file-name">${image.repository}:${image.tag}</span>
                                <span class="file-size-small">${image.size}</span>
                            </div>
                            <span class="file-date">${image.created}</span>
                        `;
                        
                        listElement.appendChild(item);
                    });
                })
                .catch(error => {
                    console.error('Error fetching images:', error);
                    document.getElementById('images-list').innerHTML = '<p>Error loading images</p>';
                });
        }
        
        function initializeMediaPlayer() {
            console.log('Media player initialized');
        }
        
        function updateSystemInfoPage() {
            fetch('/api/system/info')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(info => {
                    const systemElement = document.getElementById('system-info');
                    const hardwareElement = document.getElementById('hardware-info');
                    
                    if (systemElement) {
                        systemElement.innerHTML = `
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">Operating System:</span><span style="text-align: right;">${info.system.os}</span></div>
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">Architecture:</span><span style="text-align: right;">${info.system.architecture}</span></div>
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">Hostname:</span><span style="text-align: right;">${info.system.hostname}</span></div>
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">Uptime:</span><span style="text-align: right;">${info.system.uptime}</span></div>
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">Boot Time:</span><span style="text-align: right;">${info.system.boot_time}</span></div>
                        `;
                    }
                    
                    if (hardwareElement) {
                        hardwareElement.innerHTML = `
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">CPU:</span><span style="text-align: right;">${info.hardware.cpu}</span></div>
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">CPU Cores:</span><span style="text-align: right;">${info.hardware.cpu_cores}</span></div>
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">CPU Threads:</span><span style="text-align: right;">${info.hardware.cpu_threads}</span></div>
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">CPU Frequency:</span><span style="text-align: right;">${info.hardware.cpu_freq}</span></div>
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">Total Memory:</span><span style="text-align: right;">${formatFileSize(info.hardware.total_memory)}</span></div>
                            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;"><span style="font-weight: bold; opacity: 0.8;">Available Memory:</span><span style="text-align: right;">${formatFileSize(info.hardware.available_memory)}</span></div>
                        `;
                    }
                })
                .catch(error => {
                    console.error('Error fetching system info:', error);
                    const systemElement = document.getElementById('system-info');
                    const hardwareElement = document.getElementById('hardware-info');
                    if (systemElement) systemElement.innerHTML = '<p>Error loading system information</p>';
                    if (hardwareElement) hardwareElement.innerHTML = '<p>Error loading hardware information</p>';
                });
        }

        // --- File Browser Logic ---
        let currentPath = '/';
        let selectedFile = null;

        function loadFileBrowser(path = '/') {
            currentPath = path;
            document.getElementById('current-path').value = path;
            
            fetch(`/api/files/browse?path=${encodeURIComponent(path)}`)
                .then(response => response.json())
                .then(data => {
                    const listElement = document.getElementById('file-browser-list');
                    listElement.innerHTML = '';
                    
                    // Add parent directory if not at root
                    if (data.parent_path) {
                        const parentItem = document.createElement('div');
                        parentItem.className = 'file-browser-item';
                        parentItem.innerHTML = `
                            <span class="file-icon">📁</span>
                            <span class="file-name">..</span>
                            <span class="file-size-small">-</span>
                            <span class="file-date">-</span>
                        `;
                        parentItem.onclick = () => loadFileBrowser(data.parent_path);
                        listElement.appendChild(parentItem);
                    }
                    
                    data.items.forEach(item => {
                        const fileItem = document.createElement('div');
                        fileItem.className = `file-browser-item ${item.hidden ? 'hidden-file' : ''}`;
                        
                        const icon = item.is_directory ? '📁' : '📄';
                        const size = item.is_directory ? '-' : formatFileSize(item.size);
                        const date = new Date(item.modified).toLocaleDateString();
                        
                        fileItem.innerHTML = `
                            <span class="file-icon">${icon}</span>
                            <span class="file-name">${item.name}</span>
                            <span class="file-size-small">${size}</span>
                            <span class="file-date">${date}</span>
                        `;
                        
                        fileItem.onclick = () => {
                            // Remove previous selection
                            document.querySelectorAll('.file-browser-item').forEach(el => el.classList.remove('selected-file'));
                            fileItem.classList.add('selected-file');
                            selectedFile = item;
                            
                            // Enable/disable buttons
                            document.getElementById('execute-btn').disabled = !item.is_directory && !item.name.includes('.');
                            document.getElementById('delete-selected-btn').disabled = false;
                            
                            if (item.is_directory) {
                                // Double-click to enter directory
                                setTimeout(() => {
                                    if (fileItem.classList.contains('selected-file')) {
                                        loadFileBrowser(item.path);
                                    }
                                }, 300);
                            }
                        };
                        
                        listElement.appendChild(fileItem);
                    });
                })
                .catch(error => {
                    console.error('Error loading file browser:', error);
                    document.getElementById('file-browser-list').innerHTML = '<p>Error loading files</p>';
                });
        }

        // File browser event listeners
        document.getElementById('root-btn').onclick = () => loadFileBrowser('/');
        document.getElementById('home-btn').onclick = () => loadFileBrowser('/Users');
        document.getElementById('up-btn').onclick = () => {
            const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
            loadFileBrowser(parentPath);
        };
        document.getElementById('refresh-btn').onclick = () => loadFileBrowser(currentPath);

        // Initialize file browser with home directory
        loadFileBrowser('/Users');

        // Initial call and set intervals
        updateActiveTab();
        setInterval(updateActiveTab, 3000); // Update every 3 seconds
    </script>

</body>
</html>
"""

# --- API Models ---
class DeleteFilesRequest(BaseModel):
    files: List[str]

class KillProcessRequest(BaseModel):
    pid: int

class BrowseDirectoryRequest(BaseModel):
    path: str

class DeleteBrowserFilesRequest(BaseModel):
    files: List[str]

class NetworkToolRequest(BaseModel):
    host: str

class ExecuteFileRequest(BaseModel):
    file_path: str

class ContainerActionRequest(BaseModel):
    container_ids: List[str]
    action: str

class DockerSearchRequest(BaseModel):
    query: str
    limit: int = 25

class DockerPullRequest(BaseModel):
    image: str
    tag: str = "latest"

class DockerRunRequest(BaseModel):
    image: str
    name: str = ""
    ports: List[str] = []
    volumes: List[str] = []
    environment: List[str] = []
    platform: str = "linux/amd64"  # linux/amd64, linux/arm64, darwin/amd64, darwin/arm64
    runtime: str = "docker"  # docker, containerd, virtualization-framework

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serves the main HTML dashboard."""
    return HTMLResponse(content=html_content)

@app.get("/api/system")
async def get_system_info():
    """Provides core system metrics using psutil."""
    cpu_percent = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": memory.percent,
        "disk_percent": disk.percent
    }

@app.get("/api/network", response_model=List[Dict[str, Any]])
async def get_network_info():
    """Provides a list of active network connections."""
    connections = []
    try:
        # We only care about established TCP connections for this view
        net_connections = psutil.net_connections(kind='inet')
        for conn in net_connections:
            # Skip connections that are just listening and have no remote address
            if conn.status == 'LISTEN' or not conn.raddr:
                continue

            # Format local address
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
            
            # Format remote address
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"

            connections.append({
                "local_address": laddr,
                "remote_address": raddr,
                "status": conn.status
            })
    except psutil.AccessDenied:
        # Handle cases where the script doesn't have enough permissions
        return [{"local_address": "Access Denied", "remote_address": "Run with sudo/admin", "status": "ERROR"}]
    
    # Return a limited number of connections to not overwhelm the UI
    return connections[:20]

@app.get("/api/files/scan", response_model=List[Dict[str, Any]])
async def scan_large_files():
    """Scans the user's home directory for files larger than 100MB."""
    large_files = []
    home_dir = Path.home()
    min_size = 100 * 1024 * 1024  # 100MB in bytes
    
    try:
        # Common directories to scan for large files
        scan_dirs = [
            home_dir / "Downloads",
            home_dir / "Documents", 
            home_dir / "Desktop",
            home_dir / "Movies",
            home_dir / "Pictures",
        ]
        
        # Add the home directory itself but limit depth
        scan_dirs.append(home_dir)
        
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
                
            try:
                # For home directory, only scan files directly in it, not subdirectories
                if scan_dir == home_dir:
                    files_to_check = [f for f in scan_dir.iterdir() if f.is_file()]
                else:
                    # For other directories, scan recursively but with reasonable depth limit
                    files_to_check = []
                    for root, dirs, files in os.walk(scan_dir):
                        # Limit depth to avoid scanning too deep
                        level = root.replace(str(scan_dir), '').count(os.sep)
                        if level < 3:  # Max 3 levels deep
                            for file in files:
                                files_to_check.append(Path(root) / file)
                        else:
                            dirs.clear()  # Don't go deeper
                
                for file_path in files_to_check:
                    try:
                        if file_path.is_file():
                            stat = file_path.stat()
                            if stat.st_size >= min_size:
                                large_files.append({
                                    "path": str(file_path),
                                    "size": stat.st_size,
                                    "modified": time.ctime(stat.st_mtime)
                                })
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
                        
            except (OSError, PermissionError):
                # Skip directories we can't access
                continue
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning files: {str(e)}")
    
    # Sort by size (largest first) and limit results
    large_files.sort(key=lambda x: x["size"], reverse=True)
    return large_files[:50]  # Limit to 50 files to avoid overwhelming the UI

@app.post("/api/files/delete")
async def delete_files(request: DeleteFilesRequest):
    """Deletes the specified files after user confirmation."""
    deleted_count = 0
    errors = []
    
    for file_path in request.files:
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                deleted_count += 1
            else:
                errors.append(f"File not found or not a file: {file_path}")
        except Exception as e:
            errors.append(f"Error deleting {file_path}: {str(e)}")
    
    if errors:
        raise HTTPException(status_code=400, detail=f"Some files could not be deleted: {'; '.join(errors)}")
    
    return {"deleted_count": deleted_count, "message": f"Successfully deleted {deleted_count} file(s)"}


@app.get("/api/processes", response_model=List[Dict[str, Any]])
async def get_processes():
    """Get list of running processes with CPU and memory usage."""
    processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] is None:
                    pinfo['cpu_percent'] = 0.0
                if pinfo['memory_percent'] is None:
                    pinfo['memory_percent'] = 0.0
                    
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': round(pinfo['cpu_percent'], 1),
                    'memory_percent': round(pinfo['memory_percent'], 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching processes: {str(e)}")
    
    # Sort by CPU usage (highest first) and limit to top 50
    processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
    return processes[:50]


@app.get("/api/disk", response_model=List[Dict[str, Any]])
async def get_disk_usage():
    """Get disk usage information for all mounted drives."""
    disks = []
    try:
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': round((usage.used / usage.total) * 100, 1)
                })
            except PermissionError:
                continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching disk info: {str(e)}")
    
    return disks


@app.get("/api/network/interfaces", response_model=Dict[str, Any])
async def get_network_interfaces():
    """Get network interface statistics."""
    try:
        stats = psutil.net_io_counters(pernic=True)
        return {name: {
            'bytes_sent': stat.bytes_sent,
            'bytes_recv': stat.bytes_recv,
            'packets_sent': stat.packets_sent,
            'packets_recv': stat.packets_recv,
            'errin': stat.errin,
            'errout': stat.errout,
            'dropin': stat.dropin,
            'dropout': stat.dropout
        } for name, stat in stats.items()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching network interfaces: {str(e)}")


@app.get("/api/files/browse")
async def browse_files(path: str = "/"):
    """Browse files and directories at the specified path."""
    try:
        import os
        import stat
        from datetime import datetime
        
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Path not found")
        
        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        items = []
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    stat_info = os.stat(item_path)
                    is_dir = os.path.isdir(item_path)
                    
                    items.append({
                        'name': item,
                        'path': item_path,
                        'is_directory': is_dir,
                        'size': stat_info.st_size if not is_dir else 0,
                        'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        'permissions': oct(stat_info.st_mode)[-3:],
                        'hidden': item.startswith('.')
                    })
                except (OSError, PermissionError):
                    continue
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Sort directories first, then files
        items.sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
        
        return {
            'current_path': path,
            'parent_path': os.path.dirname(path) if path != '/' else None,
            'items': items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error browsing files: {str(e)}")


@app.get("/api/system/info", response_model=Dict[str, Any])
async def get_system_info_detailed():
    """Get detailed system and hardware information."""
    try:
        # System info
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            boot_time_str = boot_time.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            uptime_str = "Unknown"
            boot_time_str = "Unknown"
        
        # CPU info
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_freq_current = round(cpu_freq.current, 2) if cpu_freq and cpu_freq.current else "Unknown"
        except Exception:
            cpu_freq_current = "Unknown"
        
        # Memory info
        try:
            memory = psutil.virtual_memory()
            total_memory = memory.total
            available_memory = memory.available
        except Exception:
            total_memory = 0
            available_memory = 0
        
        # CPU info
        try:
            cpu_cores = psutil.cpu_count(logical=False) or "Unknown"
            cpu_threads = psutil.cpu_count(logical=True) or "Unknown"
        except Exception:
            cpu_cores = "Unknown"
            cpu_threads = "Unknown"
        
        # Processor info
        try:
            processor = platform.processor()
            if not processor:
                processor = f"{platform.machine()} CPU"
        except Exception:
            processor = "Unknown CPU"
        
        return {
            'system': {
                'os': f"{platform.system()} {platform.release()}",
                'version': platform.version(),
                'architecture': platform.machine(),
                'hostname': socket.gethostname(),
                'uptime': uptime_str,
                'boot_time': boot_time_str
            },
            'hardware': {
                'cpu': processor,
                'cpu_cores': cpu_cores,
                'cpu_threads': cpu_threads,
                'cpu_freq': f"{cpu_freq_current} MHz" if cpu_freq_current != "Unknown" else "Unknown",
                'total_memory': total_memory,
                'available_memory': available_memory
            }
        }
    except Exception as e:
        # Return a basic response if everything fails
        return {
            'system': {
                'os': f"{platform.system()} {platform.release()}",
                'version': "Unknown",
                'architecture': platform.machine(),
                'hostname': socket.gethostname(),
                'uptime': "Unknown",
                'boot_time': "Unknown"
            },
            'hardware': {
                'cpu': "Unknown CPU",
                'cpu_cores': "Unknown",
                'cpu_threads': "Unknown", 
                'cpu_freq': "Unknown",
                'total_memory': 0,
                'available_memory': 0
            }
        }


@app.get("/api/containers")
async def get_containers():
    """Get list of Docker containers."""
    try:
        # Check if Docker is installed and daemon is running
        result = subprocess.run(['docker', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            if 'Cannot connect to the Docker daemon' in result.stderr:
                return {'containers': [], 'docker_installed': True, 'error': 'Docker daemon not running. Start Docker Desktop.'}
            return {'containers': [], 'docker_installed': False, 'message': 'Docker not installed'}
        
        # Try different format approaches for better compatibility
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', 'table {{.ID}}\\t{{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {'containers': [], 'docker_installed': True, 'error': result.stderr}
        
        containers = []
        lines = result.stdout.strip().split('\n')
        
        if len(lines) > 1:  # Skip header
            for line in lines[1:]:
                if line and not line.startswith('CONTAINER'):
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        # Determine state from status
                        status = parts[3]
                        state = 'running' if 'Up' in status else 'stopped'
                        if 'Paused' in status:
                            state = 'paused'
                        
                        containers.append({
                            'id': parts[0][:12],
                            'name': parts[1],
                            'image': parts[2],
                            'status': parts[3],
                            'state': state,
                            'ports': parts[4] if len(parts) > 4 else ''
                        })
        
        return {'containers': containers, 'docker_installed': True}
        
    except subprocess.TimeoutExpired:
        return {'containers': [], 'docker_installed': True, 'error': 'Docker command timed out. Check Docker Desktop.'}
    except FileNotFoundError:
        return {'containers': [], 'docker_installed': False, 'message': 'Docker not found. Install Docker Desktop.'}
    except Exception as e:
        return {'containers': [], 'docker_installed': True, 'error': f'Docker error: {str(e)}'}


@app.get("/api/docker/images")
async def get_docker_images():
    """Get list of local Docker images."""
    try:
        result = subprocess.run(
            ['docker', 'images', '--format', 'table {{.Repository}}\\t{{.Tag}}\\t{{.ID}}\\t{{.CreatedAt}}\\t{{.Size}}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {'images': [], 'error': result.stderr}
        
        images = []
        lines = result.stdout.strip().split('\n')
        
        if len(lines) > 1:  # Skip header
            for line in lines[1:]:
                parts = line.split('\t')
                if len(parts) >= 5:
                    images.append({
                        'repository': parts[0],
                        'tag': parts[1],
                        'id': parts[2][:12],
                        'created': parts[3],
                        'size': parts[4]
                    })
        
        return {'images': images}
        
    except subprocess.TimeoutExpired:
        return {'images': [], 'error': 'Command timed out'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting images: {str(e)}")

# ==============================================================================
# PART 3: MAIN EXECUTION
# This runs the setup and then starts the server.
# ==============================================================================

if __name__ == "__main__":
    # Step 1: Create the project structure if it doesn't exist.
    setup_project_if_needed()

    # Step 2: Start the web server.
    print("\nStarting SystemPulse server...")
    print("Access the dashboard at http://127.0.0.1:3001")
    print("Press CTRL+C to stop the server.")
    uvicorn.run(app, host="127.0.0.1", port=3001)