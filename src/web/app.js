let ws = null;
let currentModalModule = null;

function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws`);

    ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        switch (msg.type) {
            case 'stats': updateStats(msg.data); break;
            case 'modules': updateModules(msg.data); break;
            case 'log': appendLog(msg.entry); break;
            case 'log_history': msg.entries.forEach(appendLog); break;
            case 'session': updateSession(msg.connected, msg.server); break;
        }
    };

    ws.onclose = () => setTimeout(connectWS, 3000);
    ws.onerror = () => ws.close();
}


function updateSession(connected, server) {
    const badge = document.getElementById('connection-badge');
    const dot = badge.querySelector('.badge-dot');
    const text = badge.querySelector('.badge-text');
    if (connected) {
        text.textContent = server;
        badge.className = 'badge connected';
        showSections();
    } else {
        text.textContent = 'Disconnected';
        badge.className = 'badge disconnected';
    }
}

function showSections() {
    ['stats-section', 'main-grid', 'log-section']
        .forEach(id => document.getElementById(id).classList.remove('hidden'));
}

function updateStats(s) {
    const hpPct = s.hp_max ? (s.hp_current / s.hp_max * 100) : 0;
    const xpPct = s.xp_max ? (s.xp_current / s.xp_max * 100) : 0;

    document.getElementById('hp-bar').style.width = hpPct + '%';
    document.getElementById('hp-text').textContent = `${s.hp_current}/${s.hp_max}`;
    document.getElementById('xp-bar').style.width = xpPct + '%';
    document.getElementById('xp-text').textContent = `${s.xp_current}/${s.xp_max}`;
    document.getElementById('gold-val').textContent = s.gold.toLocaleString();
    document.getElementById('level-val').textContent = s.level;
}

const MODULE_ICONS = {
    inventory: '&#127860;',
    equipment: '&#9876;',
    training: '&#127947;',
    expedition: '&#128739;',
    dungeon: '&#128420;',
    arena: '&#127942;',
    quests: '&#128220;',
    work: '&#9935;',
    packages: '&#128230;',
    smelting: '&#128293;',
};

function updateModules(modules) {
    const container = document.getElementById('modules-list');
    container.innerHTML = '';

    modules.forEach(mod => {
        const row = document.createElement('div');
        row.className = 'module-row' + (mod.locked ? ' locked' : '');

        const nextText = mod.next_run_in > 0 ? formatTime(mod.next_run_in) : (mod.running ? '...' : '--');
        const statusText = mod.locked ? mod.lock_reason : mod.last_result || '--';
        const icon = MODULE_ICONS[mod.name] || '&#9679;';

        row.innerHTML = `
            <button class="module-toggle ${mod.enabled ? 'on' : 'off'}"
                    onclick="toggleModule('${mod.name}', ${!mod.enabled})"
                    ${mod.locked ? 'disabled' : ''}>
                ${mod.enabled ? 'ON' : 'OFF'}
            </button>
            <span class="module-name">${icon} ${mod.name}</span>
            <span class="module-status">${statusText}</span>
            <span class="module-next">${nextText}</span>
            <button class="module-config-btn" onclick="openConfig('${mod.name}')">&#9881;</button>
        `;
        container.appendChild(row);
    });
}

function appendLog(entry) {
    const container = document.getElementById('log-container');
    const div = document.createElement('div');
    div.className = 'log-entry';

    const t = new Date(entry.time * 1000);
    const timeStr = t.toLocaleTimeString('en-GB');

    div.innerHTML = `
        <span class="log-time">${timeStr}</span>
        <span class="log-module">${entry.module}</span>
        <span class="log-msg">${entry.message}</span>
        <span class="log-status ${entry.status}">${entry.status}</span>
    `;

    container.prepend(div);

    while (container.children.length > 100) {
        container.removeChild(container.lastChild);
    }
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

async function toggleModule(name, enabled) {
    await fetch(`/api/modules/${name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
    });
    refreshModules();
}

async function refreshModules() {
    const res = await fetch('/api/modules');
    const data = await res.json();
    updateModules(data);
}

async function botStart() {
    await fetch('/api/bot/start', { method: 'POST' });
    document.getElementById('btn-start').disabled = true;
    document.getElementById('btn-stop').disabled = false;
}

async function botStop() {
    await fetch('/api/bot/stop', { method: 'POST' });
    document.getElementById('btn-start').disabled = false;
    document.getElementById('btn-stop').disabled = true;
}

const MODULE_CONFIG_FIELDS = {
    inventory: [
        { key: 'heal_threshold', label: 'Heal Threshold (%)', type: 'number', min: 0, max: 100, transform: v => v / 100 },
        { key: 'auto_buy_food', label: 'Auto-Buy Food from NPC', type: 'checkbox' },
    ],
    equipment: [
        { key: 'sell_below_quality', label: 'Sell Below Quality (0=white,1=green,2=blue,3=purple)', type: 'number', min: 0, max: 5 },
        { key: 'compare_to_equipped', label: 'Compare to Equipped', type: 'checkbox' },
        { key: 'auto_equip', label: 'Auto-Equip Better Gear', type: 'checkbox' },
    ],
    training: [
        { key: 'priority_weights.strength', label: 'Strength Weight', type: 'number', min: 0, max: 10 },
        { key: 'priority_weights.dexterity', label: 'Dexterity Weight', type: 'number', min: 0, max: 10 },
        { key: 'priority_weights.agility', label: 'Agility Weight', type: 'number', min: 0, max: 10 },
        { key: 'priority_weights.constitution', label: 'Constitution Weight', type: 'number', min: 0, max: 10 },
        { key: 'priority_weights.charisma', label: 'Charisma Weight', type: 'number', min: 0, max: 10 },
        { key: 'priority_weights.intelligence', label: 'Intelligence Weight', type: 'number', min: 0, max: 10 },
        { key: 'gold_reserve', label: 'Gold Reserve (min to keep)', type: 'number', min: 0 },
    ],
    expedition: [
        { key: 'auto_location', label: 'Auto-Pick Best Location', type: 'checkbox' },
        { key: 'location', label: 'Location (1-12)', type: 'number', min: 1, max: 12 },
        { key: 'stage', label: 'Stage (1-4)', type: 'number', min: 1, max: 4 },
        { key: 'speed_factor', label: 'Speed Factor (1=normal, 2=speed)', type: 'number', min: 1, max: 4 },
    ],
    dungeon: [
        { key: 'location', label: 'Dungeon Location (0-5)', type: 'number', min: 0, max: 5 },
        { key: 'difficulty', label: 'Difficulty', type: 'select', options: ['Normal', 'Advanced'] },
        { key: 'speed_factor', label: 'Speed Factor (1=normal, 2=speed)', type: 'number', min: 1, max: 4 },
    ],
    arena: [
        { key: 'arena_type', label: 'Arena Type (1=local, 2=provinciarum, 3=circus)', type: 'number', min: 1, max: 3 },
        { key: 'max_level_diff', label: 'Max Level Difference', type: 'number', min: 1, max: 50 },
    ],
    quests: [
        { key: 'auto_cycle', label: 'Auto-Cycle Quests', type: 'checkbox' },
    ],
    work: [
        { key: 'job_type', label: 'Job Type (1-7)', type: 'number', min: 1, max: 7 },
        { key: 'work_duration', label: 'Work Duration (hours)', type: 'number', min: 1, max: 8 },
    ],
    packages: [],
    smelting: [
        { key: 'max_quality', label: 'Smelt Below Quality (0=white, 1=green)', type: 'number', min: 0, max: 4 },
        { key: 'slot', label: 'Forge Slot', type: 'number', min: 1, max: 3 },
    ],
};

function getNestedValue(obj, path) {
    return path.split('.').reduce((o, k) => (o && o[k] !== undefined) ? o[k] : '', obj);
}

function setNestedValue(obj, path, value) {
    const keys = path.split('.');
    let curr = obj;
    for (let i = 0; i < keys.length - 1; i++) {
        if (!curr[keys[i]]) curr[keys[i]] = {};
        curr = curr[keys[i]];
    }
    curr[keys[keys.length - 1]] = value;
}

async function openConfig(name) {
    currentModalModule = name;
    const fields = MODULE_CONFIG_FIELDS[name] || [];
    if (!fields.length) return;

    const res = await fetch('/api/modules');
    const modules = await res.json();
    const mod = modules.find(m => m.name === name);
    if (!mod) return;

    const icon = MODULE_ICONS[name] || '';
    document.getElementById('modal-title').innerHTML = `${icon} ${name}`;

    const body = document.getElementById('modal-body');
    body.innerHTML = '';

    fields.forEach(f => {
        const div = document.createElement('div');
        div.className = 'config-field';
        const val = getNestedValue(mod.config, f.key);

        if (f.type === 'checkbox') {
            div.innerHTML = `<label><input type="checkbox" data-key="${f.key}" ${val ? 'checked' : ''}> ${f.label}</label>`;
        } else if (f.type === 'select') {
            const opts = f.options.map(o => `<option ${o === val ? 'selected' : ''}>${o}</option>`).join('');
            div.innerHTML = `<label>${f.label}</label><select data-key="${f.key}">${opts}</select>`;
        } else {
            const displayVal = f.transform ? val * 100 : val;
            div.innerHTML = `<label>${f.label}</label><input type="number" data-key="${f.key}" value="${displayVal}" min="${f.min || 0}" max="${f.max || 9999}">`;
        }
        body.appendChild(div);
    });

    document.getElementById('module-modal').classList.remove('hidden');
}

async function saveModuleConfig() {
    const fields = MODULE_CONFIG_FIELDS[currentModalModule] || [];
    const config = {};

    fields.forEach(f => {
        const el = document.querySelector(`[data-key="${f.key}"]`);
        if (!el) return;

        let value;
        if (f.type === 'checkbox') {
            value = el.checked;
        } else if (f.type === 'select') {
            value = el.value;
        } else {
            value = parseFloat(el.value);
            if (f.transform) value = f.transform(value);
        }
        setNestedValue(config, f.key, value);
    });

    await fetch(`/api/modules/${currentModalModule}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config }),
    });

    closeModal();
    refreshModules();
}

function closeModal() {
    document.getElementById('module-modal').classList.add('hidden');
    currentModalModule = null;
}

async function browserLogin() {
    const hint = document.getElementById('browser-login-hint');

    if (!window.electronAPI) {
        hint.textContent = 'Not running inside Electron. Use the desktop app.';
        hint.style.color = '#c04040';
        return;
    }

    hint.textContent = 'Opening browser... log in and click Play.';
    hint.style.color = '#d4b830';

    try {
        const result = await window.electronAPI.browserLogin();
        if (result.ok) {
            hint.textContent = `Connected to ${result.server}!`;
            hint.style.color = '#5a8a40';
            updateSession(true, result.server);
            showSections();
            refreshModules();
        } else {
            hint.textContent = result.message || 'Login failed';
            hint.style.color = '#c04040';
        }
    } catch (e) {
        hint.textContent = 'Error: ' + e.message;
        hint.style.color = '#c04040';
    }
}

connectWS();
