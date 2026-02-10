# Deploying MediaMind with Portainer

Portainer is a powerful UI for managing Docker containers. Here are the two best ways to run MediaMind in Portainer.

## Method 1: The "Git Repository" Way (Recommended for Portainer)
This method allows Portainer to pull the code directly from a repository, build the image, and deploy the stack.

### 1. Push Code to Git
First, create a repository on GitHub (or GitLab/Bitbucket) and push the project files from `c:\Users\reach\Documents\Filearr` to it.
Ensure the repository structure is:
```
/repo-root
  ├── docker-compose.yml
  ├── Dockerfile
  ├── backend/
  └── frontend/
```

### 2. Configure Portainer Stack
1.  Log in to Portainer.
2.  Go to **Stacks** > **Add stack**.
3.  Name the stack: `mediamind`.
4.  Select **Git Repository** (instead of Web editor).
5.  **Repository URL**: Paste your repository URL (e.g., `https://github.com/yourusername/mediamind.git`).
6.  **Compose path**: `docker-compose.yml` (default).
7.  **Environment variables**: 
    - add `TMDB_API_KEY`: `your_key_here`
    - add `INPUT_DIR`: path on host (e.g., `/c/Users/reach/Downloads`)
    - add `OUTPUT_DIR`: path on host (e.g., `/c/Users/reach/Media`)
8.  Click **Deploy the stack**.

## Method 2: The "Local CLI" Way (Easiest if running locally)
If Portainer is running on the same machine as your code, you can start the stack via command line, and Portainer will automatically detect and manage it.

1.  Open your terminal/PowerShell in `c:\Users\reach\Documents\Filearr`.
2.  Run the command:
    ```powershell
    docker-compose up -d --build
    ```
3.  Go to Portainer > **Containers**.
4.  You will see `mediamind` running there. You can view logs, restart, or stop it directly from the Portainer UI.

## Important: Volume Paths on Windows
If you are running verify that your `docker-compose.yml` uses the correct Windows path format. 
Docker Desktop for Windows often mounts drives like `c:/` as `/run/desktop/mnt/host/c/` or just `/c/`.

**Example `docker-compose.yml` needed for Windows:**
```yaml
volumes:
  - /c/Users/reach/Downloads:/input
  - /c/Users/reach/Media:/output
  - ./data:/data
```
Make sure to update your `docker-compose.yml` before deploying!
