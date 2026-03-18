const { app, BrowserWindow, ipcMain, session } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

const LOBBY_URL = 'https://lobby.gladiatus.gameforge.com/';
const GAME_URL_RE = /\/game\/index\.php.*sh=/;
const LOGIN_PARTITION = 'persist:gladiatus-login';

let mainWindow = null;
let pythonProcess = null;
let backendPort = null;

function isDev() {
    return !app.isPackaged;
}

function getPythonPath() {
    if (isDev()) {
        return null;
    }
    const binary = process.platform === 'win32' ? 'gladbot.exe' : 'gladbot';
    return path.join(process.resourcesPath, 'gladbot', binary);
}

async function findFreePort() {
    const { default: getPort } = await import('get-port');
    return getPort();
}

function spawnPython(port) {
    if (isDev()) {
        const projectRoot = path.resolve(__dirname, '..');
        const venvDir = process.platform === 'win32' ? 'Scripts' : 'bin';
        const venvPython = path.join(projectRoot, '.venv', venvDir, 'python');
        pythonProcess = spawn(venvPython, ['-m', 'src.main', '--port', String(port)], {
            cwd: projectRoot,
            stdio: ['ignore', 'pipe', 'pipe'],
        });
    } else {
        const binaryPath = getPythonPath();
        pythonProcess = spawn(binaryPath, ['--port', String(port)], {
            stdio: ['ignore', 'pipe', 'pipe'],
        });
    }

    pythonProcess.stdout.on('data', (data) => {
        process.stdout.write(`[python] ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        process.stderr.write(`[python] ${data}`);
    });

    pythonProcess.on('exit', (code) => {
        console.log(`Python process exited with code ${code}`);
        pythonProcess = null;
    });
}

function pollBackend(port, retries = 60, interval = 500) {
    return new Promise((resolve, reject) => {
        let attempt = 0;
        const check = () => {
            const req = http.get(`http://127.0.0.1:${port}/api/session/status`, (res) => {
                if (res.statusCode === 200) {
                    resolve();
                } else {
                    retry();
                }
            });
            req.on('error', retry);
            req.setTimeout(1000, () => {
                req.destroy();
                retry();
            });
        };
        const retry = () => {
            attempt++;
            if (attempt >= retries) {
                reject(new Error('Backend did not start in time'));
            } else {
                setTimeout(check, interval);
            }
        };
        check();
    });
}

function createMainWindow(port) {
    mainWindow = new BrowserWindow({
        width: 920,
        height: 760,
        title: 'Gladbot',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });

    mainWindow.loadURL(`http://127.0.0.1:${port}/`);

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function handleBrowserLogin(port) {
    return new Promise((resolve) => {
        const loginWindow = new BrowserWindow({
            width: 1024,
            height: 720,
            title: 'Gladiatus Login',
            webPreferences: {
                partition: LOGIN_PARTITION,
                contextIsolation: true,
                nodeIntegration: false,
            },
        });

        const loginSession = session.fromPartition(LOGIN_PARTITION);

        loginSession.webRequest.onCompleted({ urls: ['*://*/*'] }, (details) => {
            const url = details.url;
            if (!resolved && GAME_URL_RE.test(url)) {
                console.log('[login] Game response completed:', url.substring(0, 100));
                captureSession(url);
            }
        });

        loginWindow.loadURL(LOBBY_URL);

        let resolved = false;

        const captureSession = async (url) => {
            if (resolved) return;
            resolved = true;

            try {
                const parsedUrl = new URL(url);
                const domain = parsedUrl.hostname;

                const allCookies = await loginSession.cookies.get({});
                const relevant = allCookies.filter(
                    (c) => domain.endsWith(c.domain.replace(/^\./, '')) || c.domain.replace(/^\./, '').endsWith(domain)
                );
                console.log(`[login] Captured ${relevant.length}/${allCookies.length} cookies for ${domain}`);
                const cookieHeader = relevant.map((c) => `${c.name}=${c.value}`).join('; ');

                const postData = JSON.stringify({ url, cookie_header: cookieHeader });
                const result = await new Promise((res, rej) => {
                    const req = http.request(
                        {
                            hostname: '127.0.0.1',
                            port: port,
                            path: '/api/session/inject',
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Content-Length': Buffer.byteLength(postData),
                            },
                        },
                        (resp) => {
                            let body = '';
                            resp.on('data', (chunk) => (body += chunk));
                            resp.on('end', () => res(JSON.parse(body)));
                        }
                    );
                    req.on('error', rej);
                    req.write(postData);
                    req.end();
                });

                loginWindow.close();
                resolve(result);
            } catch (err) {
                loginWindow.close();
                resolve({ ok: false, message: err.message });
            }
        };

        loginWindow.on('closed', () => {
            resolve({ ok: false, message: 'Login window closed' });
        });
    });
}

app.whenReady().then(async () => {
    try {
        backendPort = await findFreePort();
        console.log(`Starting backend on port ${backendPort}`);

        spawnPython(backendPort);
        await pollBackend(backendPort);

        createMainWindow(backendPort);

        ipcMain.handle('browser-login', () => handleBrowserLogin(backendPort));
    } catch (err) {
        console.error('Failed to start:', err);
        app.quit();
    }
});

app.on('window-all-closed', () => {
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
    app.quit();
});

app.on('before-quit', () => {
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
});
