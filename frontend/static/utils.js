// Escape text for safe insertion into innerHTML (file names can contain <, &, quotes)
function escapeHtml(value) {
    return String(value)
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
