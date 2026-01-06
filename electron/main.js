// Electron main process
// Launches the FastAPI backend and opens the UI in a native window

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;
const PORT = 8765; // Use a different port to avoid conflicts

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 800,
        height: 700,
        minWidth: 600,
        minHeight: 500,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        title: 'Layout Verifier',
        icon: path.join(__dirname, 'icon.png'),
        autoHideMenuBar: true,
    });

    // Wait for backend to start, then load the UI
    waitForBackend().then(() => {
        mainWindow.loadURL(`http://127.0.0.1:${PORT}`);
    }).catch(err => {
        console.error('Failed to start backend:', err);
        mainWindow.loadFile(path.join(__dirname, 'error.html'));
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startPythonBackend() {
    // Find Python executable - prefer venv if it exists
    const projectRoot = path.join(__dirname, '..');
    let pythonCmd;

    if (process.platform === 'win32') {
        // Check for venv on Windows
        const venvPython = path.join(projectRoot, 'venv', 'Scripts', 'python.exe');
        pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python';
    } else {
        // Check for venv on Unix
        const venvPython = path.join(projectRoot, 'venv', 'bin', 'python');
        pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
    }

    console.log(`Using Python: ${pythonCmd}`);

    // Start the FastAPI server
    const args = [
        '-m', 'uvicorn',
        'web.app:app',
        '--host', '127.0.0.1',
        '--port', PORT.toString(),
        '--log-level', 'info'
    ];

    // Set working directory to src folder
    const cwd = path.join(projectRoot, 'src');

    console.log(`Starting backend with cwd: ${cwd}`);
    console.log(`Python command: ${pythonCmd}`);
    console.log(`Args: ${args.join(' ')}`);

    pythonProcess = spawn(pythonCmd, args, {
        cwd: cwd,
        env: { ...process.env, PYTHONPATH: cwd },
        stdio: ['ignore', 'pipe', 'pipe'],
        shell: process.platform === 'win32'  // Use shell on Windows for better path handling
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Backend: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Backend stderr: ${data}`);
    });

    pythonProcess.on('error', (err) => {
        console.error(`Backend spawn error: ${err.message}`);
    });

    pythonProcess.on('close', (code, signal) => {
        console.log(`Backend process exited with code ${code}, signal ${signal}`);
    });

    return pythonProcess;
}

async function waitForBackend(maxAttempts = 50) {
    const http = require('http');

    // Give the process a moment to start
    await new Promise(r => setTimeout(r, 2000));

    for (let i = 0; i < maxAttempts; i++) {
        console.log(`Checking backend... attempt ${i + 1}/${maxAttempts}`);
        try {
            await new Promise((resolve, reject) => {
                const options = {
                    hostname: '127.0.0.1',
                    port: PORT,
                    path: '/',
                    method: 'GET',
                    timeout: 2000
                };
                const req = http.request(options, (res) => {
                    console.log(`Backend responded with status: ${res.statusCode}`);
                    // Consume response data to free up memory
                    res.resume();
                    resolve();
                });
                req.on('error', (err) => {
                    console.log(`Request error: ${err.message}`);
                    reject(err);
                });
                req.on('timeout', () => {
                    req.destroy();
                    reject(new Error('timeout'));
                });
                req.end();
            });
            console.log('Backend is ready');
            return;
        } catch (e) {
            await new Promise(r => setTimeout(r, 500));
        }
    }
    throw new Error('Backend failed to start');
}

function setupIpcHandlers() {
    // IPC handlers for file dialogs
    ipcMain.handle('select-excel-file', async () => {
        const result = await dialog.showOpenDialog(mainWindow, {
            title: 'Select Excel File',
            filters: [
                { name: 'Excel Files', extensions: ['xlsx', 'xls', 'xlsm'] }
            ],
            properties: ['openFile']
        });

        if (result.canceled || result.filePaths.length === 0) {
            return null;
        }
        return result.filePaths[0];
    });

    ipcMain.handle('select-layouts-folder', async () => {
        const result = await dialog.showOpenDialog(mainWindow, {
            title: 'Select Folder with .ai Files',
            properties: ['openDirectory']
        });

        if (result.canceled || result.filePaths.length === 0) {
            return null;
        }
        return result.filePaths[0];
    });

    ipcMain.handle('select-layout-files', async () => {
        const result = await dialog.showOpenDialog(mainWindow, {
            title: 'Select Layout Files (.ai)',
            filters: [
                { name: 'Adobe Illustrator Files', extensions: ['ai'] },
                { name: 'All Files', extensions: ['*'] }
            ],
            properties: ['openFile', 'multiSelections']
        });

        if (result.canceled || result.filePaths.length === 0) {
            return null;
        }

        // Filter to only .ai files in case user selected "All Files"
        const aiFiles = result.filePaths.filter(f =>
            f.toLowerCase().endsWith('.ai')
        );

        return aiFiles.length > 0 ? aiFiles : null;
    });
}

// App lifecycle
app.whenReady().then(() => {
    setupIpcHandlers();
    startPythonBackend();
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    // Kill the Python backend
    if (pythonProcess) {
        pythonProcess.kill();
    }

    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
});
