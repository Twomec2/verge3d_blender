const { app, BrowserWindow } = require('electron');

function createWindow() {
    // create the browser window
    const win = new BrowserWindow({
        width: 1280,
        height: 800,
        webPreferences: {
            nodeIntegration: true
        }
    });

    // and load the main file of the app
    win.loadFile('${mainHTML}');
}

app.whenReady().then(createWindow);
