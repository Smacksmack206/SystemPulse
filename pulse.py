# start_systempulse.py
# A single, self-contained script to set up the project structure and run the app.

import os
import textwrap
import uvicorn
import psutil
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any

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
    "src/main.py": textwrap.dedent("""
        # This file will eventually contain the main application logic.
        # For now, the server is run from the root start_systempulse.py script.
        print("SystemPulse main entry point.")
    """)
}

def setup_project_if_needed():
    """Checks for the project root directory and creates the full structure if not found."""
    if os.path.exists(PROJECT_ROOT):
        # print(f"Project directory '{PROJECT_ROOT}' already exists. Skipping setup.")
        return

    print(f"Creating project structure in './{PROJECT_ROOT}'...")
    os.makedirs(PROJECT_ROOT)

    # Create root files
    for filename, content in FILE_CONTENT.items():
        with open(os.path.join(PROJECT_ROOT, filename), 'w') as f:
            f.write(content.strip())
        print(f"  Created file: {os.path.join(PROJECT_ROOT, filename)}")

    # Create directories and nested files
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
    
    # Finally, create the main.py file in src
    with open(os.path.join(PROJECT_ROOT, "src", "main.py"), 'w') as f:
        f.write(FILE_CONTENT["src/main.py"])
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
        .loading { opacity: 0.6; }
    </style>
</head>
<body class="theme-clarity">

    <header class="header">
        <h1>System<span class="primary-accent">Pulse</span></h1>
        <div class="header-controls">
            <div class="nav-tabs">
                <div class="nav-tab active" data-tab="system">System Monitor</div>
                <div class="nav-tab" data-tab="files">File Cleaner</div>
            </div>
            <div class="theme-selector">
                <label for="theme-select">Theme:</label>
                <select id="theme-select">
                    <option value="clarity">Clarity</option>
                    <option value="operator">Operator</option>
                    <option value="neo-kyoto">Neo-Kyoto</option>
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

        <!-- File Cleaner Dashboard -->
        <div id="files-dashboard" class="dashboard-section">
            <div class="card file-cleaner-card">
                <h2>Large File Scanner</h2>
                <p style="opacity: 0.8; margin-bottom: 1.5rem;">Find and manage files larger than 100MB in your home directory. Use this tool to free up disk space by removing unnecessary large files.</p>
                <div class="file-actions">
                    <button id="scan-btn" class="btn btn-scan">Scan for Large Files</button>
                    <button id="delete-btn" class="btn btn-delete" disabled>Delete Selected Files</button>
                </div>
                <div id="file-list" class="file-list">
                    <p>Click "Scan for Large Files" to find files larger than 100MB in your home directory.</p>
                </div>
            </div>
            <div class="card">
                <h2>Scan Statistics</h2>
                <div id="scan-stats">
                    <p><strong>Files Found:</strong> <span id="files-count">0</span></p>
                    <p><strong>Total Size:</strong> <span id="total-size">0 B</span></p>
                    <p><strong>Largest File:</strong> <span id="largest-file">None</span></p>
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
                deleteBtn.textContent = 'Delete Selected';
            }
        });

        // Initial call and set intervals
        updateSystemInfo();
        updateNetworkInfo();
        setInterval(updateSystemInfo, 2000);
        setInterval(updateNetworkInfo, 5000); // Network data updates less frequently
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


# --- File Cleaner Models ---
class DeleteFilesRequest(BaseModel):
    files: List[str]


@app.get("/api/files/scan", response_model=List[Dict[str, Any]])
async def scan_large_files():
    """Scans the user's home directory for files larger than 1GB."""
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
                # Additional safety check - only allow deletion of files in user's home directory
                if not str(path).startswith(str(Path.home())):
                    errors.append(f"Cannot delete file outside home directory: {file_path}")
                    continue
                    
                path.unlink()
                deleted_count += 1
            else:
                errors.append(f"File not found or not a file: {file_path}")
        except Exception as e:
            errors.append(f"Error deleting {file_path}: {str(e)}")
    
    if errors:
        raise HTTPException(status_code=400, detail=f"Some files could not be deleted: {'; '.join(errors)}")
    
    return {"deleted_count": deleted_count, "message": f"Successfully deleted {deleted_count} file(s)"}


# ==============================================================================
# PART 3: MAIN EXECUTION
# This runs the setup and then starts the server.
# ==============================================================================

if __name__ == "__main__":
    # Step 1: Create the project structure if it doesn't exist.
    setup_project_if_needed()

    # Step 2: Start the web server.
    print("\nStarting SystemPulse server...")
    print("Access the dashboard at http://127.0.0.1:8080")
    print("Press CTRL+C to stop the server.")
    uvicorn.run(app, host="127.0.0.1", port=8080)
