# Filearr - Intelligent Movie Ingestion & Cleanup

Filearr is a comprehensive, Dockerized application for automating movie organization, metadata fetching, and quality management. It is designed to work alongside Radarr and Plex.

## Features

- **Automated Ingestion**: Watches an input folder for new media files.
- **Intelligent Sorting**:
    - Detects language via audio tracks (ffprobe).
    - Routes Malayalam movies to a dedicated folder.
    - Routes all other languages to the standard Movies folder.
- **Quality Control**:
    - Scores files based on resolution, codec, and audio quality.
    - Detects and rejects CAM/TS copies.
    - (Future) Auto-upgrades existing files with better versions.
- **Manual Cleanup Mode**:
    - Web UI to scan existing folders and normalize filenames/structure.
    - Dry-run support to preview changes safely.
- **Web Dashboard**:
    - Monitor recent processed files.
    - View rejected files.
    - Trigger manual cleanup jobs.

## Installation

1.  **Duplicate `.env.example` to `.env`** (create one if not exists) and add your TMDB API Key:
    ```env
    TMDB_API_KEY=your_api_key_here
    ```

2.  **Update `docker-compose.yml` volumes**:
    Ensure the paths on the left side of the colon match your host machine's directory structure.
    ```yaml
    volumes:
      - /path/to/downloads:/input
      - /path/to/media:/output
      - ./data:/data
    ```

3.  **Run with Docker Compose**:
    ```bash
    docker-compose up -d --build
    ```

4.  **Access the Dashboard**:
    Open your browser and navigate to `http://localhost:8090`.

## Directory Structure

We recommend mounting a single volume (e.g., your entire media library) to `/media` inside the container. This allows you to freely select input and output folders using the web UI.

**Recommended Docker Volume:**
- `/path/to/your/library:/media`

**Default Internal Paths:**
- Input: `/media/downloads`
- Movies: `/media/movies`
- Malayalam Movies: `/media/movies/malayalam` (or similar, configurable)
- Rejected: `/media/movies/.rejected`
- Trash: `/media/movies/.trash`

You can change all these paths in the **Settings** page.

## Development

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Watchdog.
- **Frontend**: Jinja2 Templates, HTML/CSS.
- **Database**: SQLite (stored in `./data/filearr.db`).

## License

MIT
