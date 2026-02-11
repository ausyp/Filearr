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
            <div id="folderBrowserModal" class="modal" style="display: none;">
                <div class="modal-content" style="max-width: 600px; max-height: 70vh;">
                    <div class="modal-header">
                        <h3>Browse Folders</h3>
                        <span class="close" onclick="folderBrowser.close()">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom: 15px;">
                            <strong>Current Path:</strong> <code id="currentPath">/media</code>
                        </div>
                        <div id="folderList" style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: #f9f9f9;">
                            <p>Loading...</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="folderBrowser.close()">Cancel</button>
                        <button class="btn btn-primary" onclick="folderBrowser.selectCurrent()">Select This Folder</button>
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

        document.getElementById('folderBrowserModal').style.display = 'block';
        await this.loadDirectory(this.currentPath);
    }

    close() {
        document.getElementById('folderBrowserModal').style.display = 'none';
    }

    async loadDirectory(path) {
        this.currentPath = path;
        document.getElementById('currentPath').textContent = path;

        const folderList = document.getElementById('folderList');
        folderList.innerHTML = '<p>Loading...</p>';

        try {
            const response = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
            const data = await response.json();

            if (data.error) {
                folderList.innerHTML = `<p style="color: red;">Error: ${data.error}</p>`;
                return;
            }

            let html = '';

            // Add parent directory link if not at root
            if (data.parent_path && data.parent_path !== path) {
                html += `
                    <div class="folder-item" onclick="folderBrowser.loadDirectory('${data.parent_path}')" style="cursor: pointer; padding: 8px; margin: 4px 0; background: #fff; border-radius: 4px;">
                        📁 <strong>.. (Parent Directory)</strong>
                    </div>
                `;
            }

            // Add directories
            if (data.directories && data.directories.length > 0) {
                data.directories.forEach(dir => {
                    const fullPath = `${path}/${dir}`.replace('//', '/');
                    html += `
                        <div class="folder-item" onclick="folderBrowser.loadDirectory('${fullPath}')" style="cursor: pointer; padding: 8px; margin: 4px 0; background: #fff; border-radius: 4px; border: 1px solid #e0e0e0;">
                            📁 ${dir}
                        </div>
                    `;
                });
            } else {
                html += '<p style="color: #666;">No subdirectories found.</p>';
            }

            folderList.innerHTML = html;

        } catch (error) {
            folderList.innerHTML = `<p style="color: red;">Error loading directory: ${error.message}</p>`;
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
