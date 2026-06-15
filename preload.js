const { contextBridge } = require('electron');
contextBridge.exposeInMainWorld('BRIGHTLY_API', 'http://127.0.0.1:5055');
