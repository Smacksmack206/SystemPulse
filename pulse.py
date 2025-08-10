# start_systempulse.py
# A single, self-contained script to set up the project structure and run the app.

import os
import textwrap
import uvicorn
import psutil
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

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
    """),

}

def setup_project_if_needed():
    """Checks for the project root directory and creates the full structure if not found."""
    if os.path.exists(PROJECT_ROOT):
        print(f"Project directory '{PROJECT_ROOT}' already exists. Skipping setup.")
        return

    print(f"Creating project structure in './{PROJECT_ROOT}'...")
    os.makedirs(PROJECT_ROOT)

    # Create directories and nested files first
    for parent, items in PROJECT_STRUCTURE.items():
        parent_path = os.path.join(PROJECT_ROOT, parent)
        os.makedirs(parent_path, exist_ok=True)
        for item in items:
            # Check if it's a file or just a directory to create
            if "/" in item or "." in item:
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
                dir_path = os.path.join(parent_path, item)
                os.makedirs(dir_path, exist_ok=True)
                print(f"  Created directory: {dir_path}")

    # Create root files after directories are created
    for filename, content in FILE_CONTENT.items():
        with open(os.path.join(PROJECT_ROOT, filename), 'w') as f:
            f.write(content.strip())
        print(f"  Created file: {os.path.join(PROJECT_ROOT, filename)}")
    
    # Create the main.py file in src with specific content
    main_py_content = textwrap.dedent("""
        # This file will eventually contain the main application logic.
        # For now, the server is run from the root start_systempulse.py script.
        print("SystemPulse main entry point.")
    """)
    with open(os.path.join(PROJECT_ROOT, "src", "main.py"), 'w') as f:
        f.write(main_py_content.strip())
    print(f"  Created file: {os.path.join(PROJECT_ROOT, 'src', 'main.py')}")

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

        /* 2. Operator */
        body.theme-operator { background-color: #1E1E1E; color: #E0E0E0; font-family: "SF Mono", "Fira Code", "Source Code Pro", monospace; }
        .theme-operator .header { background-color: #252526; border-bottom: 1px solid #3A3A3A; }
        .theme-operator .card { background-color: #252526; border: 1px solid #3A3A3A; box-shadow: none; }
        .theme-operator .primary-accent { color: #39FF14; }
        .theme-operator select { border: 1px solid #5A5A5A; background-color: #2D2D2D; color: #E0E0E0; }

        /* 3. Neo-Kyoto */
        body.theme-neo-kyoto { background-color: #0D0221; color: #F0F0F0; }
        .theme-neo-kyoto .header { background-color: rgba(13, 2, 33, 0.8); border-bottom: 1px solid #F900F9; backdrop-filter: blur(10px); }
        .theme-neo-kyoto .card { background-color: rgba(255,255,255,0.05); border: 1px solid #00F5D4; box-shadow: 0 0 15px rgba(0, 245, 212, 0.2); }
        .theme-neo-kyoto .primary-accent { color: #F900F9; }
        .theme-neo-kyoto select { border: 1px solid #F900F9; background-color: #1A0A3A; color: #F0F0F0; }

        /* --- Layout & Components --- */
        .header { padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 10; }
        .header h1 { margin: 0; font-size: 1.5rem; }
        .theme-selector label { margin-right: 0.5rem; font-size: 0.9rem; opacity: 0.8; }
        select { padding: 0.5rem; border-radius: 8px; font-size: 0.9rem; cursor: pointer; }
        .dashboard { padding: 2rem; display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; }
        .card { padding: 1.5rem; border-radius: 12px; transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .card h2 { margin-top: 0; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; }
        .card .value { font-size: 2.5rem; font-weight: 600; }
    </style>
</head>
<body class="theme-clarity">

    <header class="header">
        <h1>System<span class="primary-accent">Pulse</span></h1>
        <div class="theme-selector">
            <label for="theme-select">Theme:</label>
            <select id="theme-select">
                <option value="clarity">Clarity</option>
                <option value="operator">Operator</option>
                <option value="neo-kyoto">Neo-Kyoto</option>
            </select>
        </div>
    </header>

    <main class="dashboard">
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
    </main>

    <script>
        // --- Theme Switcher Logic ---
        const themeSelector = document.getElementById('theme-select');
        const body = document.body;

        themeSelector.addEventListener('change', (event) => {
            body.className = ''; // Clear existing theme classes
            body.classList.add(`theme-${event.target.value}`);
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

        // Initial call and update every 2 seconds
        updateSystemInfo();
        setInterval(updateSystemInfo, 2000);
    </script>

</body>
</html>
"""

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
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk.percent
    }

# ==============================================================================
# PART 3: MAIN EXECUTION
# This runs the setup and then starts the server.
# ==============================================================================

if __name__ == "__main__":
    # Step 1: Create the project structure if it doesn't exist.
    setup_project_if_needed()

    # Step 2: Start the web server.
    print("\nStarting SystemPulse server...")
    print("Access the dashboard at http://127.0.0.1:8000")
    print("Press CTRL+C to stop the server.")
    uvicorn.run(app, host="127.0.0.1", port=8000)
