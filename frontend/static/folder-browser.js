// Folder Browser Module for Filearr
// Provides reusable folder browsing functionality

class FolderBrowser {
    constructor() {
        this.currentPath = '/media';
        this.callback = null;
        this.createModal();
    }

    createModal() {
        // Create modal HTML
        const modalHTML = `
            <div id="folderBrowserModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Choose a folder</h2>
                        <button type="button" class="close" onclick="folderBrowser.close()" aria-label="Close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p class="muted">Current folder: <code id="currentPath">/media</code></p>
                        <div id="folderList" class="folder-list">
                            <p class="empty">Loading...</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn" onclick="folderBrowser.close()">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="folderBrowser.selectCurrent()">Use this folder</button>
                    </div>
                </div>
            </div>
        `;

        // Add to document if not exists
        if (!document.getElementById('folderBrowserModal')) {
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }
    }

    async open(startPath, callback) {
        this.currentPath = startPath || '/media';
        this.callback = callback;

        document.getElementById('folderBrowserModal').style.display = 'flex';
        await this.loadDirectory(this.currentPath);
    }

    close() {
        document.getElementById('folderBrowserModal').style.display = 'none';
    }

    async loadDirectory(path) {
        this.currentPath = path;
        document.getElementById('currentPath').textContent = path;

        const folderList = document.getElementById('folderList');
        folderList.innerHTML = '<p class="empty">Loading...</p>';

        try {
            const response = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
            const data = await response.json();

            if (data.error) {
                folderList.innerHTML = `<p class="empty" style="color: var(--danger);">${escapeHtml(data.error)}</p>`;
                return;
            }

            let html = '';

            // Add parent directory link if not at root
            if (data.parent_path && data.parent_path !== path) {
                html += `<div class="folder-item" onclick="folderBrowser.loadDirectory(${jsArg(data.parent_path)})">⬆️ <strong>Up one level</strong></div>`;
            }

            // Add directories
            if (data.directories && data.directories.length > 0) {
                data.directories.forEach(dir => {
                    const fullPath = `${data.current_path}/${dir}`.replace('//', '/');
                    html += `<div class="folder-item" onclick="folderBrowser.loadDirectory(${jsArg(fullPath)})">📁 ${escapeHtml(dir)}</div>`;
                });
            } else {
                html += '<p class="empty">No subfolders here.</p>';
            }

            folderList.innerHTML = html;

        } catch (error) {
            folderList.innerHTML = `<p class="empty" style="color: var(--danger);">Could not load this folder: ${escapeHtml(error.message)}</p>`;
        }
    }

    selectCurrent() {
        if (this.callback) {
            this.callback(this.currentPath);
        }
        this.close();
    }
}

// Global instance
const folderBrowser = new FolderBrowser();
