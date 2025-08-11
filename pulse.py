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
import argparse
import json
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
        .network-output { max-height: 300px; overflow-y: auto; overflow-x: auto; font-family: monospace; font-size: 0.9rem; padding: 1rem; border-radius: 4px; word-wrap: break-word; white-space: pre-wrap; }
        .theme-clarity .network-output { background-color: #F8F8F8; border: 1px solid #D1D1D6; }
        .theme-operator .network-output { background-color: #2D2D2D; border: 1px solid #5A5A5A; color: #E0E0E0; }
        .theme-neo-kyoto .network-output { background-color: rgba(255,255,255,0.05); border: 1px solid #F900F9; color: #F0F0F0; }
        .theme-ocean-sunset .network-output { background-color: rgba(46, 139, 139, 0.3); border: 1px solid #2E8B8B; color: #FFFFFF; }
        .theme-forest-fire .network-output { background-color: rgba(82, 183, 136, 0.3); border: 1px solid #52B788; color: #F1FAEE; }
        .theme-midnight-aurora .network-output { background-color: rgba(123, 44, 191, 0.3); border: 1px solid #7B2CBF; color: #E8E3FF; }

        /* Terminal-specific styling */
        .terminal-output { 
            max-height: 600px; 
            width: 100%;
            max-width: 800px;
            overflow-y: auto; 
            overflow-x: hidden; 
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; 
            font-size: 0.85rem; 
            padding: 1.5rem; 
            border-radius: 12px; 
            background-color: #1a1a1a !important; 
            color: #00ff00 !important; 
            border: 3px solid #333 !important;
            word-wrap: break-word; 
            word-break: break-all;
            white-space: pre-wrap;
            line-height: 1.5;
            box-shadow: inset 0 0 15px rgba(0,0,0,0.7), 0 4px 20px rgba(0,0,0,0.3);
            box-sizing: border-box;
            margin: 0 auto;
            position: relative;
        }

        .terminal-output::-webkit-scrollbar {
            width: 8px;
        }

        .terminal-output::-webkit-scrollbar-track {
            background: #2a2a2a;
            border-radius: 4px;
        }

        .terminal-output::-webkit-scrollbar-thumb {
            background: #00ff00;
            border-radius: 4px;
        }

        .terminal-output::-webkit-scrollbar-thumb:hover {
            background: #00cc00;
        }

        /* Terminal container constraints */
        .terminal-interface {
            max-width: 100%;
            overflow: hidden;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 1rem;
        }

        .terminal-input {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            width: 100%;
            max-width: 800px;
            box-sizing: border-box;
            position: sticky;
            top: 0;
            background: inherit;
            z-index: 10;
            padding: 0.5rem;
            border-radius: 8px;
        }

        .terminal-input input {
            flex: 1;
            padding: 0.75rem;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9rem;
            border: 2px solid #333;
            border-radius: 6px;
            background-color: #2a2a2a;
            color: #00ff00;
            max-width: 100%;
            min-width: 0;
            box-sizing: border-box;
        }

        .terminal-input input:focus {
            outline: none;
            border-color: #00ff00;
            box-shadow: 0 0 5px rgba(0, 255, 0, 0.3);
        }

        .terminal-shortcuts {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            justify-content: center;
            width: 100%;
            max-width: 800px;
        }

        /* Ensure dashboard cards don't expand */
        .dashboard {
            overflow-x: hidden;
        }

        .card {
            max-width: 100%;
            overflow: hidden;
            box-sizing: border-box;
        }
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
                <div class="nav-tab" data-tab="services">Services</div>
                <div class="nav-tab" data-tab="terminal">Terminal</div>
                <div class="nav-tab" data-tab="torrents">Torrents</div>
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

        <!-- Services Dashboard -->
        <div id="services-dashboard" class="dashboard-section">
            <div class="card">
                <h2>VNC Server</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Manage VNC server for remote desktop access.</p>
                <div class="service-controls">
                    <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                        <button id="vnc-start-btn" class="btn btn-scan">Start VNC</button>
                        <button id="vnc-stop-btn" class="btn btn-delete">Stop VNC</button>
                        <button id="vnc-status-btn" class="btn btn-scan">Check Status</button>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label>VNC Port: </label>
                        <input type="number" id="vnc-port" value="5900" min="5900" max="5999" style="width: 100px; padding: 0.25rem;">
                        <label style="margin-left: 1rem;">Password: </label>
                        <input type="password" id="vnc-password" placeholder="VNC password" style="width: 150px; padding: 0.25rem;">
                    </div>
                    <div id="vnc-output" class="network-output" style="max-height: 200px;">
                        <p>VNC server not running</p>
                    </div>
                </div>
            </div>
            <div class="card">
                <h2>Samba Shares</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Manage Samba file shares for network access.</p>
                <div class="service-controls">
                    <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                        <button id="samba-start-btn" class="btn btn-scan">Start Samba</button>
                        <button id="samba-stop-btn" class="btn btn-delete">Stop Samba</button>
                        <button id="samba-status-btn" class="btn btn-scan">Check Status</button>
                        <button id="samba-shares-btn" class="btn btn-scan">List Shares</button>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <input type="text" id="share-path" placeholder="/path/to/share" style="flex: 1; padding: 0.25rem; margin-right: 0.5rem;">
                        <input type="text" id="share-name" placeholder="share-name" style="width: 150px; padding: 0.25rem; margin-right: 0.5rem;">
                        <button id="add-share-btn" class="btn btn-scan">Add Share</button>
                    </div>
                    <div id="samba-output" class="network-output" style="max-height: 250px;">
                        <p>Click "Check Status" to see Samba status</p>
                    </div>
                </div>
            </div>
            <div class="card">
                <h2>System Services</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Monitor and manage system services.</p>
                <div class="service-controls">
                    <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                        <input type="text" id="service-name" placeholder="service-name" style="flex: 1; padding: 0.25rem;">
                        <button id="service-start-btn" class="btn btn-scan">Start</button>
                        <button id="service-stop-btn" class="btn btn-delete">Stop</button>
                        <button id="service-status-btn" class="btn btn-scan">Status</button>
                        <button id="service-list-btn" class="btn btn-scan">List All</button>
                    </div>
                    <div id="services-output" class="network-output" style="max-height: 300px;">
                        <p>Enter a service name or click "List All" to see services</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Terminal Dashboard -->
        <div id="terminal-dashboard" class="dashboard-section">
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Terminal</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Execute commands on the host system terminal.</p>
                <div class="terminal-interface">
                    <div class="terminal-input">
                        <input type="text" id="terminal-command" placeholder="Enter command (e.g., ls -la, ps aux, df -h)">
                        <button id="terminal-execute-btn" class="btn btn-scan">Execute</button>
                        <button id="clear-terminal-btn" class="btn btn-delete">Clear</button>
                    </div>
                    <div class="terminal-shortcuts">
                        <button class="btn btn-small btn-scan" onclick="setCommand('ls -la')">ls -la</button>
                        <button class="btn btn-small btn-scan" onclick="setCommand('ps aux')">ps aux</button>
                        <button class="btn btn-small btn-scan" onclick="setCommand('df -h')">df -h</button>
                        <button class="btn btn-small btn-scan" onclick="setCommand('top -l 1')">top</button>
                        <button class="btn btn-small btn-scan" onclick="setCommand('netstat -an')">netstat</button>
                        <button class="btn btn-small btn-scan" onclick="setCommand('whoami')">whoami</button>
                        <button class="btn btn-small btn-scan" onclick="setCommand('pwd')">pwd</button>
                        <button class="btn btn-small btn-scan" onclick="setCommand('uname -a')">system info</button>
                        <button class="btn btn-small btn-scan" onclick="setCommand('sudo -l')">sudo</button>
                        <button class="btn btn-small btn-scan" onclick="setCommand('history')">history</button>
                    </div>
                    <div id="terminal-output" class="terminal-output">
                        <p style="color: #00ff00;">SystemPulse Terminal - Ready</p>
                        <p style="color: #888;">Type commands above or click shortcuts</p>
                    </div>
                </div>
            </div>
        </div>



        <!-- Torrents Dashboard -->
        <div id="torrents-dashboard" class="dashboard-section">
            <div class="card">
                <h2>Tor Network</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Connect to Tor network for anonymous browsing and downloads.</p>
                <div class="service-controls">
                    <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                        <button id="tor-start-btn" class="btn btn-scan">Start Tor</button>
                        <button id="tor-stop-btn" class="btn btn-delete">Stop Tor</button>
                        <button id="tor-status-btn" class="btn btn-scan">Check Status</button>
                        <button id="tor-newid-btn" class="btn btn-scan">New Identity</button>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label>SOCKS Port: </label>
                        <input type="number" id="tor-socks-port" value="9050" min="1024" max="65535" style="width: 100px; padding: 0.25rem;">
                        <label style="margin-left: 1rem;">Control Port: </label>
                        <input type="number" id="tor-control-port" value="9051" min="1024" max="65535" style="width: 100px; padding: 0.25rem;">
                    </div>
                    <div id="tor-output" class="network-output" style="max-height: 200px;">
                        <p>Tor not running. Click "Start Tor" to begin.</p>
                    </div>
                </div>
            </div>
            <div class="card">
                <h2>Torrent Downloads</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Download torrents through Tor network for privacy.</p>
                <div class="torrent-controls">
                    <div style="margin-bottom: 1rem;">
                        <input type="text" id="torrent-url" placeholder="Magnet link or .torrent URL" style="flex: 1; padding: 0.5rem; width: 70%; margin-right: 0.5rem;">
                        <button id="add-torrent-btn" class="btn btn-scan">Add Torrent</button>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label>Download Path: </label>
                        <input type="text" id="download-path" value="/tmp/torrents" style="width: 200px; padding: 0.25rem; margin-right: 0.5rem;">
                        <button id="browse-path-btn" class="btn btn-small btn-scan">Browse</button>
                        <label style="margin-left: 1rem;">Use Tor: </label>
                        <input type="checkbox" id="use-tor-proxy" checked>
                    </div>
                    <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                        <button id="start-all-btn" class="btn btn-scan">Start All</button>
                        <button id="pause-all-btn" class="btn btn-delete">Pause All</button>
                        <button id="clear-completed-btn" class="btn btn-scan">Clear Completed</button>
                        <button id="refresh-torrents-btn" class="btn btn-scan">Refresh</button>
                    </div>
                    <div id="torrents-list" class="file-browser-list" style="max-height: 400px;">
                        <p>No active torrents. Add a magnet link or torrent file to begin.</p>
                    </div>
                </div>
            </div>
            <div class="card">
                <h2>Torrent Search</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Search for torrents across multiple sites (through Tor).</p>
                <div class="search-controls">
                    <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                        <input type="text" id="search-query" placeholder="Search for torrents..." style="flex: 1; padding: 0.5rem;">
                        <select id="search-category" style="padding: 0.5rem;">
                            <option value="all">All Categories</option>
                            <option value="movies">Movies</option>
                            <option value="tv">TV Shows</option>
                            <option value="music">Music</option>
                            <option value="games">Games</option>
                            <option value="software">Software</option>
                            <option value="books">Books</option>
                        </select>
                        <button id="search-torrents-btn" class="btn btn-scan">Search</button>
                    </div>
                    <div id="search-results" class="file-browser-list" style="max-height: 350px;">
                        <p>Enter a search term and click "Search" to find torrents.</p>
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
                case 'services':
                    initializeServices();
                    break;
                case 'terminal':
                    initializeTerminal();
                    break;
                case 'torrents':
                    initializeTorrents();
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
                            <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
                                <span style="flex: 2;">${proc.name}</span>
                                <span style="flex: 1; text-align: center;">PID: ${proc.pid}</span>
                                <span style="flex: 1; text-align: center;">CPU: ${proc.cpu_percent}%</span>
                                <span style="flex: 1; text-align: center;">MEM: ${proc.memory_percent}%</span>
                                <button class="btn btn-delete btn-small" onclick="killProcess(${proc.pid})" style="margin-left: 0.5rem;">Kill</button>
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

        function killProcess(pid) {
            if (confirm(`Are you sure you want to kill process ${pid}?`)) {
                fetch('/api/processes/kill', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ pid: pid })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(`Process ${pid} killed successfully`);
                        updateProcessList(); // Refresh the list
                    } else {
                        alert(`Failed to kill process: ${data.message}`);
                    }
                })
                .catch(error => {
                    console.error('Error killing process:', error);
                    alert('Error killing process');
                });
            }
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
        
        let currentMedia = null;
        
        function initializeMediaPlayer() {
            const fileInput = document.getElementById('media-file-input');
            const playBtn = document.getElementById('play-btn');
            const pauseBtn = document.getElementById('pause-btn');
            const stopBtn = document.getElementById('stop-btn');
            const mediaDisplay = document.getElementById('media-display');
            
            fileInput.addEventListener('change', (event) => {
                const file = event.target.files[0];
                if (!file) return;
                
                // Clear previous media
                if (currentMedia) {
                    currentMedia.pause();
                    currentMedia = null;
                }
                
                const fileURL = URL.createObjectURL(file);
                const fileType = file.type;
                
                mediaDisplay.innerHTML = '';
                
                if (fileType.startsWith('video/') || file.name.toLowerCase().endsWith('.mkv') || file.name.toLowerCase().endsWith('.avi') || file.name.toLowerCase().endsWith('.mov')) {
                    // Video player - support common video formats including MKV
                    currentMedia = document.createElement('video');
                    currentMedia.src = fileURL;
                    currentMedia.controls = true;
                    currentMedia.style.maxWidth = '100%';
                    currentMedia.style.maxHeight = '400px';
                    
                    // Add error handling for unsupported codecs
                    currentMedia.addEventListener('error', (e) => {
                        mediaDisplay.innerHTML = `
                            <p>⚠️ Video format not supported by browser</p>
                            <p>File: ${file.name}</p>
                            <p>Try using VLC or another media player for this file type.</p>
                        `;
                    });
                    
                    mediaDisplay.appendChild(currentMedia);
                } else if (fileType.startsWith('audio/')) {
                    // Audio player
                    currentMedia = document.createElement('audio');
                    currentMedia.src = fileURL;
                    currentMedia.controls = true;
                    currentMedia.style.width = '100%';
                    mediaDisplay.appendChild(currentMedia);
                    
                    // Add visual indicator for audio
                    const audioInfo = document.createElement('div');
                    audioInfo.innerHTML = `
                        <h3>🎵 ${file.name}</h3>
                        <p>Audio file loaded</p>
                    `;
                    audioInfo.style.marginBottom = '1rem';
                    mediaDisplay.insertBefore(audioInfo, currentMedia);
                } else if (fileType.startsWith('image/')) {
                    // Image viewer
                    const img = document.createElement('img');
                    img.src = fileURL;
                    img.style.maxWidth = '100%';
                    img.style.maxHeight = '400px';
                    img.style.objectFit = 'contain';
                    mediaDisplay.appendChild(img);
                    
                    const imageInfo = document.createElement('div');
                    imageInfo.innerHTML = `<h3>🖼️ ${file.name}</h3>`;
                    imageInfo.style.marginBottom = '1rem';
                    mediaDisplay.insertBefore(imageInfo, img);
                } else {
                    mediaDisplay.innerHTML = '<p>Unsupported file type</p>';
                    return;
                }
                
                // Enable controls
                playBtn.disabled = false;
                pauseBtn.disabled = false;
                stopBtn.disabled = false;
            });
            
            playBtn.addEventListener('click', () => {
                if (currentMedia && currentMedia.play) {
                    currentMedia.play();
                }
            });
            
            pauseBtn.addEventListener('click', () => {
                if (currentMedia && currentMedia.pause) {
                    currentMedia.pause();
                }
            });
            
            stopBtn.addEventListener('click', () => {
                if (currentMedia) {
                    currentMedia.pause();
                    currentMedia.currentTime = 0;
                }
            });
        }

        function initializeServices() {
            // VNC Server controls
            document.getElementById('vnc-start-btn').onclick = () => {
                const port = document.getElementById('vnc-port').value;
                const password = document.getElementById('vnc-password').value;
                
                fetch('/api/services/vnc/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ port: parseInt(port), password: password })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('vnc-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('vnc-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('vnc-stop-btn').onclick = () => {
                fetch('/api/services/vnc/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('vnc-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('vnc-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('vnc-status-btn').onclick = () => {
                fetch('/api/services/vnc/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('vnc-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('vnc-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            // Samba controls
            document.getElementById('samba-start-btn').onclick = () => {
                fetch('/api/services/samba/start', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('samba-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('samba-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('samba-stop-btn').onclick = () => {
                fetch('/api/services/samba/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('samba-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('samba-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('samba-status-btn').onclick = () => {
                fetch('/api/services/samba/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('samba-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('samba-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('samba-shares-btn').onclick = () => {
                fetch('/api/services/samba/shares')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('samba-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('samba-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('add-share-btn').onclick = () => {
                const path = document.getElementById('share-path').value;
                const name = document.getElementById('share-name').value;
                
                if (!path || !name) {
                    alert('Please enter both path and share name');
                    return;
                }
                
                fetch('/api/services/samba/add-share', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: path, name: name })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('samba-output').innerHTML = data.output || data.message;
                    document.getElementById('share-path').value = '';
                    document.getElementById('share-name').value = '';
                })
                .catch(error => {
                    document.getElementById('samba-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            // System services controls
            document.getElementById('service-start-btn').onclick = () => {
                const serviceName = document.getElementById('service-name').value;
                if (!serviceName) return;
                
                fetch('/api/services/system/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service: serviceName })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('services-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('services-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('service-stop-btn').onclick = () => {
                const serviceName = document.getElementById('service-name').value;
                if (!serviceName) return;
                
                fetch('/api/services/system/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service: serviceName })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('services-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('services-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('service-status-btn').onclick = () => {
                const serviceName = document.getElementById('service-name').value;
                if (!serviceName) return;
                
                fetch(`/api/services/system/status?service=${serviceName}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('services-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('services-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('service-list-btn').onclick = () => {
                fetch('/api/services/system/list')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('services-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('services-output').innerHTML = `Error: ${error.message}`;
                });
            };
        }

        let terminalInitialized = false;
        let globalExecuting = false;
        
        function initializeTerminal() {
            // Prevent multiple initializations
            if (terminalInitialized) {
                console.log('Terminal already initialized, skipping...');
                return;
            }
            
            const commandInput = document.getElementById('terminal-command');
            const executeBtn = document.getElementById('terminal-execute-btn');
            const clearBtn = document.getElementById('clear-terminal-btn');
            const terminalOutput = document.getElementById('terminal-output');
            
            // Check if elements exist
            if (!commandInput || !executeBtn || !clearBtn || !terminalOutput) {
                console.error('Terminal elements not found:', {
                    commandInput: !!commandInput,
                    executeBtn: !!executeBtn,
                    clearBtn: !!clearBtn,
                    terminalOutput: !!terminalOutput
                });
                return;
            }
            
            terminalInitialized = true;
            console.log('Terminal initialized successfully');
            
            // Auto-focus the input when terminal is initialized
            setTimeout(() => commandInput.focus(), 100);
            
            // Execute command on Enter key
            commandInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    executeCommand();
                }
            });
            
            let isExecuting = false;
            
            function executeCommand() {
                const command = commandInput.value.trim();
                if (!command || isExecuting || globalExecuting) return;
                
                isExecuting = true;
                globalExecuting = true;
                console.log('Executing command:', command); // Debug log
                
                // Add command to output
                const commandLine = document.createElement('div');
                commandLine.innerHTML = `<span style="color: #00ff00;">$ ${command}</span>`;
                commandLine.style.wordWrap = 'break-word';
                commandLine.style.wordBreak = 'break-all';
                commandLine.style.maxWidth = '100%';
                terminalOutput.appendChild(commandLine);
                
                executeBtn.disabled = true;
                executeBtn.textContent = 'Executing...';
                
                fetch('/api/terminal/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: command })
                })
                .then(response => response.json())
                .then(data => {
                    const outputDiv = document.createElement('div');
                    outputDiv.style.whiteSpace = 'pre-wrap';
                    outputDiv.style.wordWrap = 'break-word';
                    outputDiv.style.wordBreak = 'break-all';
                    outputDiv.style.marginBottom = '1rem';
                    outputDiv.style.maxWidth = '100%';
                    outputDiv.style.overflow = 'hidden';
                    
                    if (data.error) {
                        outputDiv.style.color = '#ff6b6b';
                        outputDiv.textContent = data.error;
                    } else {
                        outputDiv.style.color = '#ffffff';
                        outputDiv.textContent = data.output || 'Command executed successfully';
                    }
                    
                    terminalOutput.appendChild(outputDiv);
                    terminalOutput.scrollTop = terminalOutput.scrollHeight;
                    
                    executeBtn.disabled = false;
                    executeBtn.textContent = 'Execute';
                    commandInput.value = '';
                    commandInput.focus(); // Keep input focused
                    isExecuting = false; // Reset execution flag
                    globalExecuting = false; // Reset global flag
                    
                    // Scroll input into view if needed
                    commandInput.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                })
                .catch(error => {
                    const errorDiv = document.createElement('div');
                    errorDiv.style.color = '#ff6b6b';
                    errorDiv.textContent = `Error: ${error.message}`;
                    terminalOutput.appendChild(errorDiv);
                    terminalOutput.scrollTop = terminalOutput.scrollHeight;
                    
                    executeBtn.disabled = false;
                    executeBtn.textContent = 'Execute';
                    commandInput.focus(); // Keep input focused
                    isExecuting = false; // Reset execution flag
                    globalExecuting = false; // Reset global flag
                });
            }
            
            // Set up event listeners (remove any existing ones first)
            executeBtn.onclick = null;
            clearBtn.onclick = null;
            
            executeBtn.onclick = executeCommand;
            clearBtn.onclick = () => {
                terminalOutput.innerHTML = '<p style="color: #00ff00;">SystemPulse Terminal - Ready</p><p style="color: #888;">Type commands above or click shortcuts</p>';
            };
        }

        function setCommand(command) {
            const input = document.getElementById('terminal-command');
            input.value = command;
            input.focus();
            input.setSelectionRange(command.length, command.length); // Cursor at end
        }



        function initializeTorrents() {
            // Tor controls
            document.getElementById('tor-start-btn').onclick = () => {
                const socksPort = document.getElementById('tor-socks-port').value;
                const controlPort = document.getElementById('tor-control-port').value;
                
                fetch('/api/tor/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ socks_port: parseInt(socksPort), control_port: parseInt(controlPort) })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('tor-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('tor-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('tor-stop-btn').onclick = () => {
                fetch('/api/tor/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('tor-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('tor-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('tor-status-btn').onclick = () => {
                fetch('/api/tor/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('tor-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('tor-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            document.getElementById('tor-newid-btn').onclick = () => {
                fetch('/api/tor/newid', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('tor-output').innerHTML = data.output || data.message;
                })
                .catch(error => {
                    document.getElementById('tor-output').innerHTML = `Error: ${error.message}`;
                });
            };
            
            // Torrent controls
            document.getElementById('add-torrent-btn').onclick = () => {
                const url = document.getElementById('torrent-url').value;
                const downloadPath = document.getElementById('download-path').value;
                const useTor = document.getElementById('use-tor-proxy').checked;
                
                if (!url) {
                    alert('Please enter a magnet link or torrent URL');
                    return;
                }
                
                fetch('/api/torrents/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, download_path: downloadPath, use_tor: useTor })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('torrent-url').value = '';
                        refreshTorrentsList();
                    } else {
                        alert(data.message || 'Failed to add torrent');
                    }
                })
                .catch(error => {
                    alert(`Error: ${error.message}`);
                });
            };
            
            document.getElementById('refresh-torrents-btn').onclick = refreshTorrentsList;
            
            document.getElementById('start-all-btn').onclick = () => {
                fetch('/api/torrents/start-all', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    refreshTorrentsList();
                })
                .catch(error => alert(`Error: ${error.message}`));
            };
            
            document.getElementById('pause-all-btn').onclick = () => {
                fetch('/api/torrents/pause-all', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    refreshTorrentsList();
                })
                .catch(error => alert(`Error: ${error.message}`));
            };
            
            document.getElementById('clear-completed-btn').onclick = () => {
                fetch('/api/torrents/clear-completed', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    refreshTorrentsList();
                })
                .catch(error => alert(`Error: ${error.message}`));
            };
            
            document.getElementById('search-torrents-btn').onclick = () => {
                const query = document.getElementById('search-query').value;
                const category = document.getElementById('search-category').value;
                
                if (!query) {
                    alert('Please enter a search term');
                    return;
                }
                
                document.getElementById('search-results').innerHTML = '<p>Searching...</p>';
                
                fetch('/api/torrents/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, category: category })
                })
                .then(response => response.json())
                .then(data => {
                    displaySearchResults(data.results || []);
                })
                .catch(error => {
                    document.getElementById('search-results').innerHTML = `Error: ${error.message}`;
                });
            };
            
            // Initialize torrents list
            refreshTorrentsList();
        }
        
        function refreshTorrentsList() {
            fetch('/api/torrents/list')
                .then(response => response.json())
                .then(data => {
                    const listElement = document.getElementById('torrents-list');
                    
                    if (!data.torrents || data.torrents.length === 0) {
                        listElement.innerHTML = '<p>No active torrents. Add a magnet link or torrent file to begin.</p>';
                        return;
                    }
                    
                    listElement.innerHTML = '';
                    data.torrents.forEach(torrent => {
                        const item = document.createElement('div');
                        item.className = 'file-browser-item';
                        
                        const progress = torrent.progress || 0;
                        const status = torrent.status || 'unknown';
                        const speed = torrent.download_speed || 0;
                        
                        item.innerHTML = `
                            <div style="width: 100%; padding: 0.5rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                    <span style="font-weight: bold;">${torrent.name}</span>
                                    <span>${status}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; opacity: 0.8;">
                                    <span>Progress: ${progress.toFixed(1)}%</span>
                                    <span>Speed: ${formatSpeed(speed)}</span>
                                </div>
                                <div style="width: 100%; background-color: #333; height: 4px; border-radius: 2px; margin-top: 0.5rem;">
                                    <div style="width: ${progress}%; background-color: #00ff00; height: 100%; border-radius: 2px;"></div>
                                </div>
                            </div>
                        `;
                        
                        listElement.appendChild(item);
                    });
                })
                .catch(error => {
                    document.getElementById('torrents-list').innerHTML = `Error: ${error.message}`;
                });
        }
        
        function displaySearchResults(results) {
            const resultsElement = document.getElementById('search-results');
            
            if (!results || results.length === 0) {
                resultsElement.innerHTML = '<p>No results found.</p>';
                return;
            }
            
            resultsElement.innerHTML = '';
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'file-browser-item';
                item.style.cursor = 'pointer';
                
                item.innerHTML = `
                    <div style="width: 100%; padding: 0.5rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="font-weight: bold;">${result.name}</span>
                            <span style="color: #00ff00;">${result.size || 'Unknown'}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.9rem; opacity: 0.8;">
                            <span>Seeds: ${result.seeds || 0} | Peers: ${result.peers || 0}</span>
                            <span>${result.category || 'Unknown'}</span>
                        </div>
                    </div>
                `;
                
                item.onclick = () => {
                    if (result.magnet) {
                        document.getElementById('torrent-url').value = result.magnet;
                    }
                };
                
                resultsElement.appendChild(item);
            });
        }
        
        function formatSpeed(bytesPerSecond) {
            if (bytesPerSecond < 1024) return bytesPerSecond + ' B/s';
            if (bytesPerSecond < 1024 * 1024) return (bytesPerSecond / 1024).toFixed(1) + ' KB/s';
            if (bytesPerSecond < 1024 * 1024 * 1024) return (bytesPerSecond / (1024 * 1024)).toFixed(1) + ' MB/s';
            return (bytesPerSecond / (1024 * 1024 * 1024)).toFixed(1) + ' GB/s';
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

        // Network tools event listeners
        let pingProcess = null;
        
        document.getElementById('ping-btn').onclick = () => {
            const host = document.getElementById('ping-host').value;
            if (!host) return;
            
            document.getElementById('ping-btn').disabled = true;
            document.getElementById('ping-stop-btn').disabled = false;
            document.getElementById('ping-output').innerHTML = `Pinging ${host}...\n`;
            
            fetch('/api/network/ping', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ host: host })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('ping-output').innerHTML = data.output;
                document.getElementById('ping-btn').disabled = false;
                document.getElementById('ping-stop-btn').disabled = true;
            })
            .catch(error => {
                document.getElementById('ping-output').innerHTML = `Error: ${error.message}`;
                document.getElementById('ping-btn').disabled = false;
                document.getElementById('ping-stop-btn').disabled = true;
            });
        };
        
        document.getElementById('traceroute-btn').onclick = () => {
            const host = document.getElementById('traceroute-host').value;
            if (!host) return;
            
            document.getElementById('traceroute-btn').disabled = true;
            document.getElementById('traceroute-output').innerHTML = `Tracing route to ${host}...\n`;
            
            fetch('/api/network/traceroute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ host: host })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('traceroute-output').innerHTML = data.output;
                document.getElementById('traceroute-btn').disabled = false;
            })
            .catch(error => {
                document.getElementById('traceroute-output').innerHTML = `Error: ${error.message}`;
                document.getElementById('traceroute-btn').disabled = false;
            });
        };

        // Load network interfaces for packet capture
        fetch('/api/network/interfaces')
            .then(response => response.json())
            .then(interfaces => {
                const select = document.getElementById('capture-interface');
                select.innerHTML = '<option value="">Select interface...</option>';
                Object.keys(interfaces).forEach(name => {
                    const option = document.createElement('option');
                    option.value = name;
                    option.textContent = name;
                    select.appendChild(option);
                });
            });

        // Docker Hub search event listener
        document.getElementById('docker-search-btn').onclick = () => {
            const query = document.getElementById('docker-search-input').value;
            if (!query) return;
            
            document.getElementById('docker-search-btn').disabled = true;
            document.getElementById('docker-search-results').innerHTML = '<p>Searching Docker Hub...</p>';
            
            fetch('/api/docker/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                const resultsElement = document.getElementById('docker-search-results');
                if (data.error) {
                    resultsElement.innerHTML = `<p>Error: ${data.error}</p>`;
                } else if (data.results.length === 0) {
                    resultsElement.innerHTML = '<p>No results found</p>';
                } else {
                    resultsElement.innerHTML = '';
                    data.results.forEach(image => {
                        const item = document.createElement('div');
                        item.className = 'file-browser-item';
                        item.innerHTML = `
                            <span class="file-icon">🐳</span>
                            <div class="file-info">
                                <span class="file-name">${image.name}</span>
                                <span class="file-size-small">${image.star_count} ⭐</span>
                            </div>
                            <span class="file-date">${image.description || 'No description'}</span>
                        `;
                        resultsElement.appendChild(item);
                    });
                }
                document.getElementById('docker-search-btn').disabled = false;
            })
            .catch(error => {
                document.getElementById('docker-search-results').innerHTML = `<p>Error: ${error.message}</p>`;
                document.getElementById('docker-search-btn').disabled = false;
            });
        };

        // Packet capture event listeners
        document.getElementById('capture-start-btn').onclick = () => {
            const interface = document.getElementById('capture-interface').value;
            if (!interface) {
                alert('Please select a network interface');
                return;
            }
            
            document.getElementById('capture-start-btn').disabled = true;
            document.getElementById('capture-stop-btn').disabled = false;
            document.getElementById('capture-output').innerHTML = `Starting packet capture on ${interface}...\n`;
            
            fetch('/api/network/capture/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ interface: interface, count: 20 })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('capture-output').innerHTML = data.output;
                document.getElementById('capture-start-btn').disabled = false;
                document.getElementById('capture-stop-btn').disabled = true;
            })
            .catch(error => {
                document.getElementById('capture-output').innerHTML = `Error: ${error.message}`;
                document.getElementById('capture-start-btn').disabled = false;
                document.getElementById('capture-stop-btn').disabled = true;
            });
        };

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


@app.post("/api/processes/kill")
async def kill_process(request: KillProcessRequest):
    """Kill a process by PID."""
    try:
        process = psutil.Process(request.pid)
        process.terminate()
        # Wait a bit to see if it terminates gracefully
        try:
            process.wait(timeout=3)
        except psutil.TimeoutExpired:
            # Force kill if it doesn't terminate gracefully
            process.kill()
        
        return {"success": True, "message": f"Process {request.pid} killed successfully"}
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail=f"Process {request.pid} not found")
    except psutil.AccessDenied:
        raise HTTPException(status_code=403, detail=f"Access denied to kill process {request.pid}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error killing process: {str(e)}")


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


class NetworkToolRequest(BaseModel):
    host: str

@app.post("/api/network/ping")
async def ping_host(request: NetworkToolRequest):
    """Ping a host and return the output."""
    try:
        result = subprocess.run(
            ['ping', '-c', '4', request.host],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {"output": result.stdout + result.stderr}
    except subprocess.TimeoutExpired:
        return {"output": "Ping timed out"}
    except Exception as e:
        return {"output": f"Error: {str(e)}"}

@app.post("/api/network/traceroute")
async def traceroute_host(request: NetworkToolRequest):
    """Traceroute to a host and return the output."""
    try:
        # Use appropriate command for each OS
        if platform.system() == 'Darwin':  # macOS
            cmd = ['traceroute', '-m', '15', request.host]
        elif platform.system() == 'Windows':
            cmd = ['tracert', request.host]
        else:  # Linux
            cmd = ['traceroute', request.host]
            
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # Increased to 2 minutes
        )
        
        if result.returncode != 0 and result.stderr:
            return {"output": f"Error: {result.stderr}"}
        
        return {"output": result.stdout or result.stderr}
    except subprocess.TimeoutExpired:
        return {"output": "Traceroute timed out after 30 seconds"}
    except FileNotFoundError:
        return {"output": "Traceroute command not found. Please install network utilities."}
    except Exception as e:
        return {"output": f"Error: {str(e)}"}


class PacketCaptureRequest(BaseModel):
    interface: str
    count: int = 10

@app.post("/api/network/capture/start")
async def start_packet_capture(request: PacketCaptureRequest):
    """Start packet capture on specified interface."""
    try:
        # Use tcpdump for packet capture (requires sudo)
        cmd = ['sudo', 'tcpdump', '-i', request.interface, '-c', str(request.count), '-n']
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {"output": f"Error: {result.stderr}"}
        
        return {"output": result.stdout + result.stderr}
    except subprocess.TimeoutExpired:
        return {"output": "Packet capture timed out"}
    except Exception as e:
        return {"output": f"Error: {str(e)}"}


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
        result = subprocess.run(['docker', 'version'], capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            if 'Cannot connect to the Docker daemon' in result.stderr:
                return {'containers': [], 'docker_installed': True, 'error': 'Docker daemon not running. Start Docker Desktop from Applications.'}
            elif 'docker.sock' in result.stderr:
                return {'containers': [], 'docker_installed': True, 'error': 'Docker Desktop not running. Launch Docker Desktop app.'}
            return {'containers': [], 'docker_installed': False, 'message': 'Docker not installed. Install Docker Desktop from docker.com'}
        
        # Try different format approaches for better compatibility
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', 'table {{.ID}}\\t{{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'],
            capture_output=True,
            text=True,
            timeout=30
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
        return {'containers': [], 'docker_installed': True, 'error': 'Docker command timed out. Try: docker ps -a'}
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
            timeout=30
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
        return {'images': [], 'error': 'Docker images command timed out. Try: docker images'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting images: {str(e)}")


class DockerSearchRequest(BaseModel):
    query: str

@app.post("/api/docker/search")
async def search_docker_hub(request: DockerSearchRequest):
    """Search Docker Hub for images."""
    try:
        result = subprocess.run(
            ['docker', 'search', '--limit', '10', request.query],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {'results': [], 'error': result.stderr}
        
        results = []
        lines = result.stdout.strip().split('\n')
        
        if len(lines) > 1:  # Skip header
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 5:
                    # Join description parts (everything after the 4th column)
                    description = ' '.join(parts[4:]) if len(parts) > 4 else ''
                    results.append({
                        'name': parts[0],
                        'description': description,
                        'star_count': parts[2],
                        'official': '[OK]' in parts[3],
                        'automated': '[OK]' in parts[4] if len(parts) > 4 else False
                    })
        
        return {'results': results}
        
    except subprocess.TimeoutExpired:
        return {'results': [], 'error': 'Search timed out'}
    except Exception as e:
        return {'results': [], 'error': f"Error searching Docker Hub: {str(e)}"}

# Services API Models
class VNCStartRequest(BaseModel):
    port: int = 5900
    password: str = ""

class ServiceRequest(BaseModel):
    service: str

class SambaShareRequest(BaseModel):
    path: str
    name: str

# VNC Server API Endpoints
@app.post("/api/services/vnc/start")
async def start_vnc_server(request: VNCStartRequest):
    """Start VNC/Screen Sharing server."""
    try:
        if platform.system() == "Darwin":  # macOS
            # For macOS, provide instructions since programmatic enabling requires special permissions
            try:
                # Check if Screen Sharing is already enabled
                result = subprocess.run(['launchctl', 'list', 'com.apple.screensharing'], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    return {"message": "Screen Sharing appears to be enabled", 
                           "output": "Screen Sharing is running.\nConnect using VNC viewer to this machine's IP address on port 5900.\n\nTo verify: System Preferences > Sharing > Screen Sharing should be checked."}
                else:
                    return {"message": "Screen Sharing not enabled", 
                           "output": "To enable Screen Sharing on macOS:\n\n1. Open System Preferences (or System Settings on newer macOS)\n2. Go to Sharing\n3. Check 'Screen Sharing' or 'Remote Management'\n4. Set access permissions as needed\n5. Connect using VNC viewer to this machine's IP on port 5900\n\nNote: Programmatic enabling requires special system permissions."}
            except:
                return {"message": "macOS Screen Sharing Instructions", 
                       "output": "To enable Screen Sharing:\n1. Open System Preferences > Sharing\n2. Check 'Screen Sharing'\n3. Connect using VNC viewer to this machine's IP on port 5900"}
        else:
            # Linux VNC server
            result = subprocess.run(
                ['vncserver', f':{request.port - 5900}', '-geometry', '1920x1080', '-depth', '24'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {"message": f"VNC server started on port {request.port}", "output": result.stdout}
            else:
                return {"message": "Failed to start VNC server", "output": result.stderr}
            
    except subprocess.TimeoutExpired:
        return {"message": "VNC start command timed out", "output": ""}
    except FileNotFoundError:
        if platform.system() == "Darwin":
            return {"message": "macOS Screen Sharing", 
                   "output": "Enable Screen Sharing in System Preferences > Sharing > Screen Sharing"}
        else:
            return {"message": "VNC server not installed", "output": "Install with: apt install tightvncserver"}
    except Exception as e:
        return {"message": f"Error with VNC: {str(e)}", "output": ""}

@app.post("/api/services/vnc/stop")
async def stop_vnc_server():
    """Stop VNC/Screen Sharing server."""
    try:
        if platform.system() == "Darwin":  # macOS
            # Try to disable Screen Sharing on macOS
            result = subprocess.run([
                'sudo', 'launchctl', 'unload', '-w', 
                '/System/Library/LaunchDaemons/com.apple.screensharing.plist'
            ], capture_output=True, text=True, timeout=10)
            
            # Also try the newer way
            result2 = subprocess.run([
                'sudo', 'systemsetup', '-setremotelogin', 'off'
            ], capture_output=True, text=True, timeout=10)
            
            return {"message": "Attempting to disable macOS Screen Sharing", 
                   "output": f"Screen Sharing disable command executed.\nTo manually disable: System Preferences > Sharing > Uncheck Screen Sharing\n\nOutput: {result.stdout + result.stderr}"}
        else:
            # Linux VNC server
            result = subprocess.run(['vncserver', '-kill', ':0'], capture_output=True, text=True, timeout=10)
            return {"message": "VNC server stopped", "output": result.stdout + result.stderr}
    except FileNotFoundError:
        if platform.system() == "Darwin":
            return {"message": "macOS Screen Sharing", "output": "Disable Screen Sharing in System Preferences > Sharing > Screen Sharing"}
        else:
            return {"message": "VNC server not found", "output": ""}
    except Exception as e:
        return {"message": f"Error stopping VNC: {str(e)}", "output": ""}

@app.get("/api/services/vnc/status")
async def vnc_status():
    """Get VNC/Screen Sharing server status."""
    try:
        if platform.system() == "Darwin":  # macOS
            # Check if Screen Sharing is enabled
            result = subprocess.run(['launchctl', 'list', 'com.apple.screensharing'], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Also check if the service is actually running
                ps_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                screen_sharing = [line for line in ps_result.stdout.split('\n') if 'screensharing' in line.lower() or 'vnc' in line.lower()]
                
                status_output = f"Screen Sharing service status:\n{result.stdout}\n"
                if screen_sharing:
                    status_output += f"\nRunning processes:\n" + '\n'.join(screen_sharing)
                
                return {"message": "macOS Screen Sharing status", "output": status_output}
            else:
                return {"message": "Screen Sharing not enabled", "output": "Enable in System Preferences > Sharing > Screen Sharing"}
        else:
            # Linux VNC server
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            vnc_processes = [line for line in result.stdout.split('\n') if 'Xvnc' in line or 'vncserver' in line]
            
            if vnc_processes:
                return {"message": "VNC server is running", "output": '\n'.join(vnc_processes)}
            else:
                return {"message": "VNC server is not running", "output": "No VNC processes found"}
    except Exception as e:
        return {"message": f"Error checking VNC status: {str(e)}", "output": ""}

# Samba API Endpoints
@app.post("/api/services/samba/start")
async def start_samba():
    """Start Samba service."""
    try:
        if platform.system() == "Darwin":  # macOS
            # For macOS, provide instructions for File Sharing
            return {"message": "macOS File Sharing Instructions", 
                   "output": "To enable File Sharing (SMB) on macOS:\n\n1. Open System Preferences > Sharing\n2. Check 'File Sharing'\n3. Click 'Options...' and enable 'Share files and folders using SMB'\n4. Select user accounts to share via SMB\n5. Access from other devices using smb://[this-mac-ip]\n\nNote: macOS uses built-in SMB sharing, not traditional Samba service."}
        else:  # Linux
            result = subprocess.run(['sudo', 'systemctl', 'start', 'smbd'], capture_output=True, text=True, timeout=10)
            return {"message": "Samba service started", "output": result.stdout + result.stderr}
    except Exception as e:
        return {"message": f"Error starting Samba: {str(e)}", "output": ""}

@app.post("/api/services/samba/stop")
async def stop_samba():
    """Stop Samba service."""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(['sudo', 'launchctl', 'unload', '/System/Library/LaunchDaemons/com.apple.smbd.plist'], 
                                  capture_output=True, text=True, timeout=10)
        else:  # Linux
            result = subprocess.run(['sudo', 'systemctl', 'stop', 'smbd'], capture_output=True, text=True, timeout=10)
        
        return {"message": "Samba service stopped", "output": result.stdout + result.stderr}
    except Exception as e:
        return {"message": f"Error stopping Samba: {str(e)}", "output": ""}

@app.get("/api/services/samba/status")
async def samba_status():
    """Get Samba service status."""
    try:
        if platform.system() == "Darwin":  # macOS
            # Check for macOS File Sharing
            result = subprocess.run(['launchctl', 'list'], capture_output=True, text=True, timeout=10)
            
            # Look for file sharing related services
            sharing_services = []
            for line in result.stdout.split('\n'):
                if any(service in line.lower() for service in ['smb', 'sharing', 'netfs']):
                    sharing_services.append(line)
            
            if sharing_services:
                return {"message": "macOS File Sharing Status", 
                       "output": f"File sharing related services:\n" + '\n'.join(sharing_services) + 
                                f"\n\nTo check: System Preferences > Sharing > File Sharing"}
            else:
                return {"message": "File Sharing not detected", 
                       "output": "Enable File Sharing in System Preferences > Sharing > File Sharing"}
        else:  # Linux
            result = subprocess.run(['systemctl', 'status', 'smbd'], capture_output=True, text=True, timeout=10)
            return {"message": "Samba status", "output": result.stdout + result.stderr}
    except Exception as e:
        return {"message": f"Error checking Samba status: {str(e)}", "output": ""}

@app.get("/api/services/samba/shares")
async def list_samba_shares():
    """List Samba shares."""
    try:
        result = subprocess.run(['smbclient', '-L', 'localhost', '-N'], capture_output=True, text=True, timeout=10)
        return {"message": "Samba shares", "output": result.stdout + result.stderr}
    except FileNotFoundError:
        if platform.system() == "Darwin":
            return {"message": "smbclient not found. Install with: brew install samba", "output": ""}
        else:
            return {"message": "smbclient not found. Install with: apt install smbclient", "output": ""}
    except Exception as e:
        return {"message": f"Error listing shares: {str(e)}", "output": ""}

@app.post("/api/services/samba/add-share")
async def add_samba_share(request: SambaShareRequest):
    """Add a new Samba share."""
    try:
        # This is a simplified example - in practice, you'd modify smb.conf
        share_config = f"""
[{request.name}]
    path = {request.path}
    browseable = yes
    read only = no
    guest ok = yes
"""
        return {"message": f"Share configuration for '{request.name}'", "output": share_config}
    except Exception as e:
        return {"message": f"Error adding share: {str(e)}", "output": ""}

# System Services API Endpoints
@app.post("/api/services/system/start")
async def start_system_service(request: ServiceRequest):
    """Start a system service."""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(['sudo', 'launchctl', 'load', f'/System/Library/LaunchDaemons/{request.service}.plist'], 
                                  capture_output=True, text=True, timeout=10)
        else:  # Linux
            result = subprocess.run(['sudo', 'systemctl', 'start', request.service], capture_output=True, text=True, timeout=10)
        
        return {"message": f"Service {request.service} started", "output": result.stdout + result.stderr}
    except Exception as e:
        return {"message": f"Error starting service: {str(e)}", "output": ""}

@app.post("/api/services/system/stop")
async def stop_system_service(request: ServiceRequest):
    """Stop a system service."""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(['sudo', 'launchctl', 'unload', f'/System/Library/LaunchDaemons/{request.service}.plist'], 
                                  capture_output=True, text=True, timeout=10)
        else:  # Linux
            result = subprocess.run(['sudo', 'systemctl', 'stop', request.service], capture_output=True, text=True, timeout=10)
        
        return {"message": f"Service {request.service} stopped", "output": result.stdout + result.stderr}
    except Exception as e:
        return {"message": f"Error stopping service: {str(e)}", "output": ""}

@app.get("/api/services/system/status")
async def system_service_status(service: str):
    """Get system service status."""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(['launchctl', 'list', service], capture_output=True, text=True, timeout=10)
        else:  # Linux
            result = subprocess.run(['systemctl', 'status', service], capture_output=True, text=True, timeout=10)
        
        return {"message": f"Status for {service}", "output": result.stdout + result.stderr}
    except Exception as e:
        return {"message": f"Error checking service status: {str(e)}", "output": ""}

@app.get("/api/services/system/list")
async def list_system_services():
    """List all system services."""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(['launchctl', 'list'], capture_output=True, text=True, timeout=15)
        else:  # Linux
            result = subprocess.run(['systemctl', 'list-units', '--type=service'], capture_output=True, text=True, timeout=15)
        
        return {"message": "System services", "output": result.stdout}
    except Exception as e:
        return {"message": f"Error listing services: {str(e)}", "output": ""}

# Tor and Torrents API Models
class TorStartRequest(BaseModel):
    socks_port: int = 9050
    control_port: int = 9051

class TorrentAddRequest(BaseModel):
    url: str
    download_path: str = "/tmp/torrents"
    use_tor: bool = True

class TorrentSearchRequest(BaseModel):
    query: str
    category: str = "all"

# Tor API Endpoints
@app.post("/api/tor/start")
async def start_tor(request: TorStartRequest):
    """Start Tor service."""
    try:
        # Check if Tor is already running
        check_result = subprocess.run(['pgrep', '-f', 'tor'], capture_output=True, text=True)
        if check_result.returncode == 0:
            return {"message": "Tor is already running", "output": f"Tor process found: PID {check_result.stdout.strip()}"}
        
        # Create torrc configuration
        torrc_content = f"""SocksPort {request.socks_port}
ControlPort {request.control_port}
DataDirectory /tmp/tor_data
Log notice file /tmp/tor.log
RunAsDaemon 1
"""
        
        # Write torrc file
        torrc_path = "/tmp/torrc"
        with open(torrc_path, 'w') as f:
            f.write(torrc_content)
        
        # Create data directory
        os.makedirs("/tmp/tor_data", exist_ok=True)
        
        # Start Tor as daemon
        result = subprocess.Popen(
            ['tor', '-f', torrc_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for Tor to start
        time.sleep(2)
        
        # Check if Tor started successfully
        check_result = subprocess.run(['pgrep', '-f', 'tor'], capture_output=True, text=True)
        if check_result.returncode == 0:
            return {"message": f"Tor started successfully on SOCKS port {request.socks_port}", 
                   "output": f"Tor daemon started with PID: {check_result.stdout.strip()}\nSOCKS proxy: 127.0.0.1:{request.socks_port}\nControl port: {request.control_port}"}
        else:
            return {"message": "Failed to start Tor daemon", "output": "Tor process not found after startup attempt"}
            
    except FileNotFoundError:
        return {"message": "Tor not installed", "output": "Install Tor with: brew install tor (macOS) or apt install tor (Linux)"}
    except Exception as e:
        return {"message": f"Error starting Tor: {str(e)}", "output": ""}

@app.post("/api/tor/stop")
async def stop_tor():
    """Stop Tor service."""
    try:
        result = subprocess.run(['pkill', '-f', 'tor'], capture_output=True, text=True, timeout=10)
        return {"message": "Tor stopped", "output": result.stdout + result.stderr}
    except Exception as e:
        return {"message": f"Error stopping Tor: {str(e)}", "output": ""}

@app.get("/api/tor/status")
async def tor_status():
    """Get Tor service status."""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        tor_processes = [line for line in result.stdout.split('\n') if 'tor' in line.lower() and 'grep' not in line]
        
        if tor_processes:
            return {"message": "Tor is running", "output": '\n'.join(tor_processes)}
        else:
            return {"message": "Tor is not running", "output": "No Tor processes found"}
    except Exception as e:
        return {"message": f"Error checking Tor status: {str(e)}", "output": ""}

@app.post("/api/tor/newid")
async def tor_new_identity():
    """Request new Tor identity."""
    try:
        # Send NEWNYM signal to Tor control port
        result = subprocess.run(
            ['echo', 'AUTHENTICATE ""\nSIGNAL NEWNYM\nQUIT'],
            capture_output=True,
            text=True
        )
        
        # Try to connect to control port and send signal
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', 9051))
            sock.send(b'AUTHENTICATE ""\r\n')
            sock.recv(1024)
            sock.send(b'SIGNAL NEWNYM\r\n')
            response = sock.recv(1024)
            sock.send(b'QUIT\r\n')
            sock.close()
            
            return {"message": "New Tor identity requested", "output": response.decode()}
        except:
            return {"message": "New identity requested (control port not accessible)", "output": ""}
            
    except Exception as e:
        return {"message": f"Error requesting new identity: {str(e)}", "output": ""}

# Torrent API Endpoints
@app.post("/api/torrents/add")
async def add_torrent(request: TorrentAddRequest):
    """Add a torrent for download."""
    try:
        # Create download directory
        os.makedirs(request.download_path, exist_ok=True)
        
        # Store torrent info in a simple JSON file for persistence
        torrents_file = "/tmp/active_torrents.json"
        
        # Load existing torrents
        active_torrents = []
        if os.path.exists(torrents_file):
            try:
                with open(torrents_file, 'r') as f:
                    active_torrents = json.loads(f.read())
            except:
                active_torrents = []
        
        if request.url.startswith('magnet:'):
            # Extract name from magnet link
            import urllib.parse
            parsed = urllib.parse.parse_qs(request.url.split('?')[1])
            name = parsed.get('dn', ['Unknown Torrent'])[0]
            
            # Create torrent entry
            torrent_entry = {
                "id": len(active_torrents) + 1,
                "name": name,
                "url": request.url,
                "download_path": request.download_path,
                "use_tor": request.use_tor,
                "status": "added",
                "progress": 0.0,
                "download_speed": 0,
                "size": "Unknown",
                "added_time": time.time()
            }
            
            active_torrents.append(torrent_entry)
            
            # Save torrents
            with open(torrents_file, 'w') as f:
                f.write(json.dumps(active_torrents, indent=2))
            
            return {"success": True, "message": f"Magnet link added: {name}"}
            
        elif request.url.endswith('.torrent'):
            # Handle torrent file URL
            torrent_entry = {
                "id": len(active_torrents) + 1,
                "name": os.path.basename(request.url),
                "url": request.url,
                "download_path": request.download_path,
                "use_tor": request.use_tor,
                "status": "added",
                "progress": 0.0,
                "download_speed": 0,
                "size": "Unknown",
                "added_time": time.time()
            }
            
            active_torrents.append(torrent_entry)
            
            # Save torrents
            with open(torrents_file, 'w') as f:
                f.write(json.dumps(active_torrents, indent=2))
            
            return {"success": True, "message": f"Torrent file added: {os.path.basename(request.url)}"}
        else:
            return {"success": False, "message": "Invalid torrent URL or magnet link"}
            
    except Exception as e:
        return {"success": False, "message": f"Error adding torrent: {str(e)}"}

@app.get("/api/torrents/list")
async def list_torrents():
    """List active torrents."""
    try:
        torrents_file = "/tmp/active_torrents.json"
        
        if not os.path.exists(torrents_file):
            return {"torrents": []}
        
        # Load torrents from file
        with open(torrents_file, 'r') as f:
            active_torrents = json.loads(f.read())
        
        # Simulate progress updates for demo
        import random
        for torrent in active_torrents:
            if torrent["status"] == "added":
                torrent["status"] = "downloading"
                torrent["progress"] = random.uniform(0, 100)
                torrent["download_speed"] = random.randint(100000, 5000000)  # 100KB/s to 5MB/s
            elif torrent["status"] == "downloading" and torrent["progress"] < 100:
                torrent["progress"] = min(100, torrent["progress"] + random.uniform(0, 5))
                if torrent["progress"] >= 100:
                    torrent["status"] = "completed"
                    torrent["download_speed"] = 0
        
        # Save updated progress
        with open(torrents_file, 'w') as f:
            f.write(json.dumps(active_torrents, indent=2))
        
        return {"torrents": active_torrents}
        
    except Exception as e:
        return {"torrents": [], "error": f"Error listing torrents: {str(e)}"}

@app.post("/api/torrents/search")
async def search_torrents(request: TorrentSearchRequest):
    """Search for torrents."""
    try:
        # Enhanced demo search results with more realistic data
        import random
        
        # Generate realistic search results
        results = []
        for i in range(random.randint(3, 8)):
            # Generate realistic torrent names based on category
            if request.category == "movies":
                names = [f"{request.query} (2023) 1080p BluRay", f"{request.query} 4K HDR", f"{request.query} Directors Cut"]
            elif request.category == "tv":
                names = [f"{request.query} S01E01-E10", f"{request.query} Complete Series", f"{request.query} Season 1"]
            elif request.category == "music":
                names = [f"{request.query} - Discography", f"{request.query} - Greatest Hits", f"{request.query} - Live Album"]
            elif request.category == "games":
                names = [f"{request.query} - PC Game", f"{request.query} - Repack", f"{request.query} - Deluxe Edition"]
            elif request.category == "software":
                names = [f"{request.query} - Full Version", f"{request.query} - Professional", f"{request.query} - Portable"]
            else:
                names = [f"{request.query} - Result {i+1}", f"{request.query} - Alternative", f"{request.query} - HD Version"]
            
            name = random.choice(names)
            
            # Generate realistic sizes
            if request.category == "movies":
                size_mb = random.randint(1500, 8000)
            elif request.category == "tv":
                size_mb = random.randint(500, 15000)
            elif request.category == "music":
                size_mb = random.randint(50, 500)
            elif request.category == "games":
                size_mb = random.randint(2000, 50000)
            else:
                size_mb = random.randint(100, 5000)
            
            if size_mb > 1024:
                size = f"{size_mb/1024:.1f} GB"
            else:
                size = f"{size_mb} MB"
            
            # Generate realistic hash for magnet link
            import hashlib
            hash_input = f"{name}{i}".encode()
            torrent_hash = hashlib.sha1(hash_input).hexdigest()
            
            result = {
                "name": name,
                "size": size,
                "seeds": random.randint(5, 500),
                "peers": random.randint(1, 100),
                "category": request.category if request.category != "all" else random.choice(["movies", "tv", "music", "games", "software"]),
                "magnet": f"magnet:?xt=urn:btih:{torrent_hash}&dn={name.replace(' ', '+')}&tr=udp://tracker.example.com:80"
            }
            
            results.append(result)
        
        # Sort by seeds (most popular first)
        results.sort(key=lambda x: x["seeds"], reverse=True)
        
        return {"results": results}
        
    except Exception as e:
        return {"results": [], "error": f"Error searching torrents: {str(e)}"}

@app.post("/api/torrents/start-all")
async def start_all_torrents():
    """Start all paused torrents."""
    try:
        torrents_file = "/tmp/active_torrents.json"
        
        if not os.path.exists(torrents_file):
            return {"success": True, "message": "No torrents to start"}
        
        with open(torrents_file, 'r') as f:
            active_torrents = json.loads(f.read())
        
        started_count = 0
        for torrent in active_torrents:
            if torrent["status"] == "paused":
                torrent["status"] = "downloading"
                started_count += 1
        
        with open(torrents_file, 'w') as f:
            f.write(json.dumps(active_torrents, indent=2))
        
        return {"success": True, "message": f"Started {started_count} torrents"}
        
    except Exception as e:
        return {"success": False, "message": f"Error starting torrents: {str(e)}"}

@app.post("/api/torrents/pause-all")
async def pause_all_torrents():
    """Pause all active torrents."""
    try:
        torrents_file = "/tmp/active_torrents.json"
        
        if not os.path.exists(torrents_file):
            return {"success": True, "message": "No torrents to pause"}
        
        with open(torrents_file, 'r') as f:
            active_torrents = json.loads(f.read())
        
        paused_count = 0
        for torrent in active_torrents:
            if torrent["status"] == "downloading":
                torrent["status"] = "paused"
                torrent["download_speed"] = 0
                paused_count += 1
        
        with open(torrents_file, 'w') as f:
            f.write(json.dumps(active_torrents, indent=2))
        
        return {"success": True, "message": f"Paused {paused_count} torrents"}
        
    except Exception as e:
        return {"success": False, "message": f"Error pausing torrents: {str(e)}"}

@app.post("/api/torrents/clear-completed")
async def clear_completed_torrents():
    """Remove completed torrents from the list."""
    try:
        torrents_file = "/tmp/active_torrents.json"
        
        if not os.path.exists(torrents_file):
            return {"success": True, "message": "No torrents to clear"}
        
        with open(torrents_file, 'r') as f:
            active_torrents = json.loads(f.read())
        
        original_count = len(active_torrents)
        active_torrents = [t for t in active_torrents if t["status"] != "completed"]
        cleared_count = original_count - len(active_torrents)
        
        with open(torrents_file, 'w') as f:
            f.write(json.dumps(active_torrents, indent=2))
        
        return {"success": True, "message": f"Cleared {cleared_count} completed torrents"}
        
    except Exception as e:
        return {"success": False, "message": f"Error clearing torrents: {str(e)}"}

# Terminal API Endpoints
class TerminalRequest(BaseModel):
    command: str

@app.post("/api/terminal/execute")
async def execute_terminal_command(request: TerminalRequest):
    """Execute a terminal command."""
    try:
        # Execute the command (all commands allowed - user has sudo access)
        # Use bash with shell configuration sourced for aliases and functions
        shell_cmd = f"source ~/.bashrc 2>/dev/null || source ~/.bash_profile 2>/dev/null || true; {request.command}"
        result = subprocess.run(
            ['/bin/bash', '-c', shell_cmd],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.expanduser('~'),  # Start in home directory
            env=os.environ.copy()  # Preserve environment variables
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        
        if result.returncode != 0:
            return {"output": output or f"Command '{request.command}' exited with code {result.returncode}"}
        
        # Handle empty output better
        if not output.strip():
            if request.command.strip() in ['alias', 'history', 'jobs', 'set']:
                return {"output": f"No output from '{request.command}' (command executed successfully)"}
            else:
                return {"output": "(no output)"}
        
        return {"output": output}
        
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 30 seconds"}
    except Exception as e:
        return {"error": f"Error executing command: {str(e)}"}

# ==============================================================================
# PART 3: PORT MANAGEMENT
# Smart port detection and management functions
# ==============================================================================

def is_port_in_use(port):
    """Check if a port is currently in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True

def get_process_on_port(port):
    """Get the process ID and name using a specific port."""
    try:
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pid = result.stdout.strip().split('\n')[0]
            
            # Get process name
            proc_result = subprocess.run(['ps', '-p', pid, '-o', 'comm='], capture_output=True, text=True)
            process_name = proc_result.stdout.strip() if proc_result.returncode == 0 else 'unknown'
            
            return int(pid), process_name
        return None, None
    except Exception as e:
        print(f"Error checking process on port {port}: {e}")
        return None, None

def kill_process_on_port(port):
    """Kill the process using a specific port."""
    pid, process_name = get_process_on_port(port)
    if pid:
        try:
            subprocess.run(['kill', '-9', str(pid)], check=True)
            print(f"✅ Killed process {process_name} (PID: {pid}) on port {port}")
            return True
        except subprocess.CalledProcessError:
            print(f"❌ Failed to kill process {process_name} (PID: {pid}) on port {port}")
            return False
    return False

def find_available_port(start_port=3000, max_attempts=100):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    return None

def handle_port_conflict(preferred_port):
    """Handle port conflicts with user interaction."""
    if not is_port_in_use(preferred_port):
        return preferred_port
    
    pid, process_name = get_process_on_port(preferred_port)
    
    print(f"\n⚠️  Port {preferred_port} is already in use!")
    if pid and process_name:
        print(f"   Process: {process_name} (PID: {pid})")
    
    print("\nOptions:")
    print("1. Find another available port automatically")
    print("2. Kill the process and use this port")
    print("3. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1/2/3): ").strip()
            
            if choice == '1':
                # Find alternative port
                alt_port = find_available_port(preferred_port + 1)
                if alt_port:
                    print(f"✅ Found available port: {alt_port}")
                    return alt_port
                else:
                    print("❌ No available ports found in range")
                    continue
                    
            elif choice == '2':
                # Kill process on port
                if pid:
                    confirm = input(f"Are you sure you want to kill {process_name} (PID: {pid})? (y/N): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        if kill_process_on_port(preferred_port):
                            # Wait a moment for port to be released
                            time.sleep(1)
                            if not is_port_in_use(preferred_port):
                                print(f"✅ Port {preferred_port} is now available")
                                return preferred_port
                            else:
                                print(f"❌ Port {preferred_port} is still in use")
                                continue
                        else:
                            print("❌ Failed to kill process")
                            continue
                    else:
                        print("Operation cancelled")
                        continue
                else:
                    print("❌ No process found to kill")
                    continue
                    
            elif choice == '3':
                print("Exiting...")
                exit(0)
                
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
                continue
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            exit(0)
        except Exception as e:
            print(f"Error: {e}")
            continue

def scan_and_display_ports(start_port=3000, end_port=3010):
    """Scan and display port usage in a range."""
    print(f"\n🔍 Scanning ports {start_port}-{end_port}:")
    print("-" * 50)
    
    for port in range(start_port, end_port + 1):
        if is_port_in_use(port):
            pid, process_name = get_process_on_port(port)
            status = f"❌ USED - {process_name} (PID: {pid})" if pid else "❌ USED"
        else:
            status = "✅ FREE"
        
        print(f"Port {port:4d}: {status}")
    
    print("-" * 50)

# ==============================================================================
# PART 4: MAIN EXECUTION
# This runs the setup and then starts the server.
# ==============================================================================

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SystemPulse - System Monitoring Dashboard')
    parser.add_argument('-p', '--port', type=int, default=3004, help='Preferred port (default: 3004)')
    parser.add_argument('--auto-port', action='store_true', help='Automatically find available port')
    parser.add_argument('--kill-port', action='store_true', help='Kill process on port if occupied')
    parser.add_argument('--scan-ports', type=str, help='Scan port range (e.g., 3000-3010)')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    
    args = parser.parse_args()
    
    # Handle port scanning request
    if args.scan_ports:
        try:
            start, end = map(int, args.scan_ports.split('-'))
            scan_and_display_ports(start, end)
            exit(0)
        except ValueError:
            print("❌ Invalid port range format. Use: --scan-ports 3000-3010")
            exit(1)
    
    # Step 1: Create the project structure if it doesn't exist.
    setup_project_if_needed()

    # Step 2: Smart port management
    preferred_port = args.port
    
    print("\n🚀 SystemPulse Server Startup")
    print("=" * 40)
    
    # Check if preferred port is available
    if is_port_in_use(preferred_port):
        print(f"⚠️  Preferred port {preferred_port} is in use")
        
        if args.auto_port:
            # Automatically find available port
            selected_port = find_available_port(preferred_port + 1)
            if selected_port:
                print(f"✅ Auto-selected available port: {selected_port}")
            else:
                print("❌ No available ports found")
                exit(1)
        elif args.kill_port:
            # Automatically kill process on port
            pid, process_name = get_process_on_port(preferred_port)
            if pid:
                print(f"🔪 Killing process {process_name} (PID: {pid}) on port {preferred_port}")
                if kill_process_on_port(preferred_port):
                    time.sleep(1)
                    if not is_port_in_use(preferred_port):
                        selected_port = preferred_port
                        print(f"✅ Port {preferred_port} is now available")
                    else:
                        print(f"❌ Port {preferred_port} is still in use")
                        exit(1)
                else:
                    print("❌ Failed to kill process")
                    exit(1)
            else:
                print("❌ No process found to kill")
                exit(1)
        else:
            # Show port scan and interactive handling
            scan_and_display_ports(max(3000, preferred_port - 5), preferred_port + 10)
            selected_port = handle_port_conflict(preferred_port)
    else:
        selected_port = preferred_port
        print(f"✅ Port {selected_port} is available")

    # Step 3: Start the web server
    print(f"\n🌐 Starting SystemPulse server on {args.host}:{selected_port}...")
    print(f"📱 Access the dashboard at http://{args.host}:{selected_port}")
    print("⏹️  Press CTRL+C to stop the server.")
    print("=" * 40)
    
    try:
        uvicorn.run(app, host=args.host, port=selected_port)
    except KeyboardInterrupt:
        print("\n\n👋 SystemPulse server stopped gracefully")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        
        # If server fails to start, offer to scan ports again
        print("\n🔍 Would you like to scan for available ports?")
        if input("Scan ports? (y/N): ").strip().lower() in ['y', 'yes']:
            scan_and_display_ports(3000, 3020)