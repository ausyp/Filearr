// Escape text for safe insertion into innerHTML (file names can contain <, &, quotes)
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Encode a value as a JS string literal usable inside an onclick="..." attribute,
// so names like "Ocean's Eleven" don't break the handler
function jsArg(value) {
    return escapeHtml(JSON.stringify(String(value)));
}

function baseName(path) {
    return String(path || '').split('/').pop() || String(path || '');
}

// The backend stores naive UTC timestamps, so mark them as UTC before
// converting, otherwise the browser treats them as local time
function parseServerTime(value) {
    if (!value) return null;
    const hasZone = /([zZ]|[+-]\d\d:?\d\d)$/.test(value);
    return new Date(hasZone ? value : value + 'Z');
}

// One date format everywhere: time only for today, otherwise date and time
function formatTime(value) {
    const d = parseServerTime(value);
    if (!d || isNaN(d)) return '';
    const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (d.toDateString() === new Date().toDateString()) return time;
    return d.toLocaleDateString([], { day: 'numeric', month: 'short' }) + ', ' + time;
}

// Fill in every <time data-utc="..."> rendered by the server
function localizeTimes(root = document) {
    root.querySelectorAll('time[data-utc]').forEach(el => {
        el.textContent = formatTime(el.dataset.utc);
        el.title = parseServerTime(el.dataset.utc).toLocaleString();
    });
}

// Map any status the backend produces to a colour tone
const STATUS_TONES = {
    processed: 'success', success: 'success', moved: 'success',
    detected: 'info', dry_run: 'info', scan: 'info', running: 'info',
    ignored: 'warning', skipped: 'warning', skip: 'warning',
    failed: 'danger', rejected: 'danger', error: 'danger',
};

function statusTone(status) {
    return STATUS_TONES[String(status || '').toLowerCase()] || '';
}

function statusLabel(status) {
    const s = String(status || '').replace(/_/g, ' ');
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function badge(status) {
    const tone = statusTone(status);
    return `<span class="badge${tone ? ' badge-' + tone : ''}">${escapeHtml(statusLabel(status))}</span>`;
}

function toast(message, type = 'info') {
    const box = document.getElementById('toasts');
    if (!box) return;
    const el = document.createElement('div');
    el.className = 'toast ' + type;
    el.textContent = message;
    box.appendChild(el);
    setTimeout(() => el.remove(), type === 'error' ? 6000 : 3500);
}

// fetch wrapper that throws with the server's own message on failure
async function api(url, options = {}) {
    const resp = await fetch(url, options);
    let data = null;
    try { data = await resp.json(); } catch (e) { /* empty body */ }
    const failed = !resp.ok || (data && (data.status === 'error' || (data.error && !data.status)));
    if (failed) {
        const msg = (data && (data.message || data.detail || data.error)) || `Request failed (${resp.status})`;
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
}

// In-page replacement for confirm()/prompt(). Resolves to false when cancelled,
// true when confirmed, or the entered text when `input` is given.
function confirmDialog({ title, message, confirmText = 'Confirm', danger = false, input = null }) {
    return new Promise(resolve => {
        const wrap = document.createElement('div');
        wrap.className = 'modal';
        wrap.style.display = 'flex';
        wrap.innerHTML = `
            <div class="modal-content" role="dialog" aria-modal="true">
                <div class="modal-header">
                    <h2>${escapeHtml(title)}</h2>
                    <button type="button" class="close" data-act="cancel" aria-label="Close">&times;</button>
                </div>
                <div class="modal-body">
                    ${message ? `<p>${escapeHtml(message)}</p>` : ''}
                    ${input ? `<div class="field"><label>${escapeHtml(input.label)}</label>
                        <input type="text" value="${escapeHtml(input.value || '')}" style="width:100%"></div>` : ''}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn" data-act="cancel">Cancel</button>
                    <button type="button" class="btn ${danger ? 'btn-danger' : 'btn-primary'}" data-act="ok">${escapeHtml(confirmText)}</button>
                </div>
            </div>`;
        const field = wrap.querySelector('input');
        const finish = ok => {
            wrap.remove();
            document.removeEventListener('keydown', onKey);
            resolve(ok ? (field ? field.value : true) : false);
        };
        const onKey = e => {
            if (e.key === 'Escape') finish(false);
            if (e.key === 'Enter') finish(true);
        };
        wrap.addEventListener('click', e => {
            if (e.target === wrap || e.target.closest('[data-act="cancel"]')) finish(false);
            if (e.target.closest('[data-act="ok"]')) finish(true);
        });
        document.addEventListener('keydown', onKey);
        document.body.appendChild(wrap);
        (field || wrap.querySelector('[data-act="ok"]')).focus();
    });
}

// Shared by the Settings and Cleanup forms
function browseFolder(inputId) {
    const input = document.getElementById(inputId);
    folderBrowser.open(input.value || '/media', selectedPath => {
        input.value = selectedPath;
        input.dispatchEvent(new Event('input', { bubbles: true }));
    });
}

document.addEventListener('DOMContentLoaded', () => localizeTimes());
