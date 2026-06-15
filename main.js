const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
let backend = null;

function startBackend(){
  const backendPath = path.join(__dirname, '..', 'backend', 'app.py');
  backend = spawn('python', [backendPath], { cwd: path.join(__dirname, '..', 'backend'), shell: true });
  backend.stdout.on('data', d => console.log('[backend]', d.toString()));
  backend.stderr.on('data', d => console.log('[backend]', d.toString()));
}

function createWindow(){
  const win = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 720,
    backgroundColor: '#05070b',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });
  win.loadFile(path.join(__dirname, '..', 'frontend', 'index.html'));
}

app.whenReady().then(()=>{ startBackend(); setTimeout(createWindow, 1600); });
app.on('window-all-closed',()=>{ if(backend) backend.kill(); if(process.platform !== 'darwin') app.quit(); });
