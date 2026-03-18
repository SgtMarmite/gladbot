const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    browserLogin: () => ipcRenderer.invoke('browser-login'),
});
