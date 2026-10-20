# Deploying Filearr with Portainer

Portainer is a powerful UI for managing Docker containers. Here are the two best ways to run Filearr in Portainer.

## Method 1: Prebuilt image from GitHub (Recommended)
GitHub Actions builds the image on every push and publishes it to GitHub Container Registry:

- `ghcr.io/ausyp/filearr:test2` (and `:main`, `:test1`): latest build of that branch
- `ghcr.io/ausyp/filearr:latest`: latest build of `main`
- `ghcr.io/ausyp/filearr:sha-<commit>`: a specific commit

### Set up the stack once
1.  In Portainer go to **Stacks** > **Add stack**, name it `filearr`.
2.  Choose **Repository** (URL `https://github.com/ausyp/filearr`, reference `refs/heads/test2`, compose path `docker-compose.yml`) or paste `docker-compose.yml` into the **Web editor**.
3.  Under **Environment variables**, add the values from `.env.example`. At minimum:
    - `MEDIA_PATH`: host folder holding your media (mounted at `/media`)
    - `DATA_PATH`: host folder for the database, e.g. `/opt/filearr/data`
    - `TMDB_API_KEY`
    - `FILEARR_TAG`: which image tag to run (default `test2`)
4.  Click **Deploy the stack**.

These variables live in the stack, so they don't need re-entering for each update.

### Update after a merge
Wait for the **Docker image** workflow to finish on GitHub, then open the stack in Portainer and click **Update the stack** with **Re-pull image** turned on (or **Pull and redeploy** for a Git stack).

> If the image pull is refused, the package is private: on GitHub open the `filearr` package > **Package settings** > **Change visibility** > Public, or add a ghcr.io registry in Portainer with a token that has `read:packages`.

> **Note**: Settings saved in the app's **Settings** page take priority over these environment variables.

## Method 2: The "Local CLI" Way (Easiest if running locally)
If Portainer is running on the same machine as your code, you can start the stack via command line, and Portainer will automatically detect and manage it.

1.  Open your terminal/PowerShell in `c:\Users\reach\Documents\Filearr`.
2.  Run the command:
    ```powershell
    docker-compose up -d --build
    ```
3.  Go to Portainer > **Containers**.
4.  You will see `filearr` running there. You can view logs, restart, or stop it directly from the Portainer UI.

## Important: Volume Paths on Windows
If you are running verify that your `docker-compose.yml` uses the correct Windows path format. 
Docker Desktop for Windows often mounts drives like `c:/` as `/run/desktop/mnt/host/c/` or just `/c/`.

**Example `docker-compose.yml` needed for Windows:**
```yaml
volumes:
  - /c/Users/reach/Media:/media
  - ./data:/data
```
Make sure to update your `docker-compose.yml` before deploying!
