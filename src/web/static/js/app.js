// Layout Verifier - Furnace UI JavaScript
// Uses Electron native dialogs when available, falls back to path input for browser

// State
let sessionId = window.SESSION_ID || null;
let hasExcel = false;
let hasLayouts = false;

// Check if running in Electron
const isElectron = window.electronAPI && window.electronAPI.isElectron;

// DOM Elements
const excelZone = document.getElementById('excel-zone');
const layoutsZone = document.getElementById('layouts-zone');
const excelFileDisplay = document.getElementById('excel-file');
const layoutsFileDisplay = document.getElementById('layouts-file');
const layoutsProgress = document.getElementById('layouts-progress');
const excelPathInput = document.getElementById('excel-path-input');
const layoutsPathInput = document.getElementById('layouts-path-input');
const processBtn = document.getElementById('process-btn');
const outputZone = document.getElementById('output-zone');
const outputStats = document.getElementById('output-stats');
const downloadBtn = document.getElementById('download-btn');
const resetBtn = document.getElementById('reset-btn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupDropZone(excelZone, 'excel');
    setupDropZone(layoutsZone, 'layouts');
    setupPathInputs();
    setupButtons();

    // Hide path inputs in Electron (we use native dialogs)
    if (isElectron) {
        excelPathInput.style.display = 'none';
        layoutsPathInput.style.display = 'none';

        // Update hints for Electron
        document.querySelector('#excel-zone .drop-zone-hint').textContent = 'Click to browse';
        document.querySelector('#layouts-zone .drop-zone-hint').textContent = 'Click to select folder';
    }
});

// Setup drop zone event handlers
function setupDropZone(zone, type) {
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.add('drag-over'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.remove('drag-over'), false);
    });

    // Handle dropped files (Electron provides full paths)
    zone.addEventListener('drop', (e) => handleDrop(e, type), false);

    // Click to open native dialog
    zone.addEventListener('click', (e) => {
        if (e.target.tagName !== 'INPUT') {
            openFileDialog(type);
        }
    }, false);
}

function setupPathInputs() {
    // Excel path input - Enter key submits
    excelPathInput.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const path = excelPathInput.value.trim();
            if (path) {
                await setExcelPath(path);
            }
        }
    });

    // Layouts path input - Enter key submits (folder path)
    layoutsPathInput.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const path = layoutsPathInput.value.trim();
            if (path) {
                await setLayoutsFolder(path);
            }
        }
    });

    // Prevent click propagation on inputs
    excelPathInput.addEventListener('click', (e) => e.stopPropagation());
    layoutsPathInput.addEventListener('click', (e) => e.stopPropagation());
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

async function openFileDialog(type) {
    if (isElectron) {
        // Use Electron native dialogs
        if (type === 'excel') {
            const filePath = await window.electronAPI.selectExcelFile();
            if (filePath) {
                await setExcelPath(filePath);
            }
        } else {
            // Select individual .ai files (not a folder)
            const filePaths = await window.electronAPI.selectLayoutFiles();
            if (filePaths && filePaths.length > 0) {
                await setLayoutsPaths(filePaths);
            }
        }
    } else {
        // Fall back to file input (browser mode)
        const input = document.createElement('input');
        input.type = 'file';

        if (type === 'excel') {
            input.accept = '.xlsx,.xls,.xlsm';
        } else {
            input.accept = '.ai';
            input.multiple = true;
        }

        input.onchange = (e) => {
            if (e.target.files.length > 0) {
                handleFiles(e.target.files, type);
            }
        };

        input.click();
    }
}

function handleDrop(e, type) {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFiles(files, type);
    }
}

async function handleFiles(files, type) {
    if (type === 'excel') {
        await handleExcelFile(files[0]);
    } else {
        await handleLayoutFiles(files);
    }
}

async function handleExcelFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();

    if (!['xlsx', 'xls', 'xlsm'].includes(ext)) {
        alert('Please select an Excel file (.xlsx, .xls, or .xlsm)');
        return;
    }

    // In Electron, file.path contains the full path
    let filePath = file.path;

    if (!filePath) {
        // Browser mode - ask to use path input
        if (!isElectron) {
            alert('Please paste the full file path in the text box below.');
            excelPathInput.focus();
        }
        return;
    }

    await setExcelPath(filePath);
}

async function setExcelPath(filePath) {
    // Show loading state
    excelZone.classList.add('loading');
    excelFileDisplay.textContent = 'Validating...';

    try {
        const response = await fetch(`/api/set/excel?session_id=${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: filePath })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to set Excel file');
        }

        const data = await response.json();
        sessionId = data.session_id;

        // Update UI
        excelZone.classList.remove('loading');
        excelZone.classList.add('has-file');
        excelFileDisplay.textContent = data.filename;
        excelPathInput.value = '';
        hasExcel = true;
        updateProcessButton();

    } catch (error) {
        excelZone.classList.remove('loading');
        excelFileDisplay.textContent = '';
        alert(`Error: ${error.message}`);
    }
}

async function handleLayoutFiles(files) {
    // Filter for .ai files only
    const aiFiles = Array.from(files).filter(f =>
        f.name.toLowerCase().endsWith('.ai')
    );

    if (aiFiles.length === 0) {
        alert('Please select .ai files only');
        return;
    }

    // In Electron, file.path contains the full path
    const paths = aiFiles.map(f => f.path).filter(p => p);

    if (paths.length === 0) {
        if (!isElectron) {
            alert('Please paste the folder path in the text box below.');
            layoutsPathInput.focus();
        }
        return;
    }

    await setLayoutsPaths(paths);
}

async function setLayoutsPaths(paths) {
    // Show loading state with count
    layoutsZone.classList.add('loading');
    layoutsFileDisplay.textContent = `Validating ${paths.length} files...`;
    layoutsProgress.textContent = '';

    try {
        const response = await fetch(`/api/set/layouts?session_id=${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths: paths })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to set layout files');
        }

        const data = await response.json();
        sessionId = data.session_id;

        // Update UI
        layoutsZone.classList.remove('loading');
        layoutsZone.classList.add('has-file');
        layoutsFileDisplay.textContent = `${data.count} file${data.count > 1 ? 's' : ''} selected`;
        layoutsPathInput.value = '';

        // Show warning if some files were invalid
        if (data.invalid && data.invalid.length > 0) {
            layoutsProgress.textContent = `${data.invalid.length} file(s) skipped`;
        } else {
            layoutsProgress.textContent = '';
        }

        hasLayouts = true;
        updateProcessButton();

    } catch (error) {
        layoutsZone.classList.remove('loading');
        layoutsFileDisplay.textContent = '';
        layoutsProgress.textContent = '';
        alert(`Error: ${error.message}`);
    }
}

async function setLayoutsFolder(folderPath) {
    // Show loading state
    layoutsZone.classList.add('loading');
    layoutsFileDisplay.textContent = 'Scanning folder...';
    layoutsProgress.textContent = '';

    try {
        const response = await fetch(`/api/set/layouts?session_id=${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder: folderPath })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to scan folder');
        }

        const data = await response.json();
        sessionId = data.session_id;

        // Update UI
        layoutsZone.classList.remove('loading');
        layoutsZone.classList.add('has-file');
        layoutsFileDisplay.textContent = `${data.count} file${data.count > 1 ? 's' : ''} found`;
        layoutsPathInput.value = '';

        // Show warning if some files were invalid
        if (data.invalid && data.invalid.length > 0) {
            layoutsProgress.textContent = `${data.invalid.length} file(s) skipped`;
        } else {
            layoutsProgress.textContent = '';
        }

        hasLayouts = true;
        updateProcessButton();

    } catch (error) {
        layoutsZone.classList.remove('loading');
        layoutsFileDisplay.textContent = '';
        layoutsProgress.textContent = '';
        alert(`Error: ${error.message}`);
    }
}

function updateProcessButton() {
    processBtn.disabled = !(hasExcel && hasLayouts);
}

function setupButtons() {
    processBtn.addEventListener('click', startProcessing);
    downloadBtn.addEventListener('click', downloadResult);
    resetBtn.addEventListener('click', resetSession);
}

async function startProcessing() {
    if (!hasExcel || !hasLayouts) return;

    // Update UI to processing state
    processBtn.classList.add('processing');
    processBtn.disabled = true;
    outputZone.classList.remove('complete', 'error');
    outputStats.innerHTML = '<div class="processing-text">Verifying layouts...</div>';
    downloadBtn.style.display = 'none';

    try {
        const response = await fetch(`/api/process?session_id=${sessionId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Processing failed');
        }

        const data = await response.json();

        // Update UI to complete state
        processBtn.classList.remove('processing');
        outputZone.classList.add('complete');

        // Show stats
        outputStats.innerHTML = `
            <div>Products found: ${data.products_found}</div>
            <div>
                <span class="stat-green">${data.cells_green} matched</span> |
                <span class="stat-red">${data.cells_red} missing</span> |
                <span class="stat-yellow">${data.cells_yellow} unchecked</span>
            </div>
        `;

        downloadBtn.style.display = 'inline-block';

    } catch (error) {
        processBtn.classList.remove('processing');
        outputZone.classList.add('error');
        outputStats.innerHTML = `<div style="color: var(--error-red);">Error: ${error.message}</div>`;
        processBtn.disabled = false;
    }
}

function downloadResult() {
    window.location.href = `/api/download/${sessionId}`;
}

async function resetSession() {
    try {
        const response = await fetch(`/api/reset/${sessionId}`, {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            sessionId = data.session_id;
        }
    } catch (error) {
        console.error('Reset error:', error);
    }

    // Reset UI
    hasExcel = false;
    hasLayouts = false;

    excelZone.classList.remove('has-file', 'loading');
    layoutsZone.classList.remove('has-file', 'loading');
    excelFileDisplay.textContent = '';
    layoutsFileDisplay.textContent = '';
    layoutsProgress.textContent = '';
    excelPathInput.value = '';
    layoutsPathInput.value = '';

    processBtn.classList.remove('processing');
    processBtn.disabled = true;

    outputZone.classList.remove('complete', 'error');
    outputStats.innerHTML = '';
    downloadBtn.style.display = 'none';
}
