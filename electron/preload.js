// Preload script - exposes safe APIs to the renderer process
const { contextBridge, ipcRenderer } = require('electron');

// Expose native file dialog APIs to the web page
contextBridge.exposeInMainWorld('electronAPI', {
    // Open native file dialog for Excel file
    selectExcelFile: () => ipcRenderer.invoke('select-excel-file'),

    // Open native folder dialog for layouts folder
    selectLayoutsFolder: () => ipcRenderer.invoke('select-layouts-folder'),

    // Open native file dialog for multiple .ai files
    selectLayoutFiles: () => ipcRenderer.invoke('select-layout-files'),

    // Flag to indicate we're running in Electron
    isElectron: true
});
