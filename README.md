# YouTube Downloader

A versatile and user-friendly YouTube media downloader that supports both a native **Desktop Graphical Interface (GUI)** and a modern **Web-App Interface (Docker-ready)**. Both implementations share a unified Python backend core powered by `yt-dlp` and `ffmpeg`.

---

## 🏗️ Core Architecture & Implementation Details

The application is structured using a modular architecture that separates the core download engine from the user interfaces:

```
youtube_downloader/
├── core/                  # Unified business logic (shared engine)
│   └── downloader.py      # Wrapper around yt-dlp to handle downloads and callbacks
├── desktop/               # Desktop Graphical User Interface
│   └── desktop_app.py     # CustomTkinter interface
├── web/                   # Web Application
│   ├── backend/           # FastAPI websocket server
│   └── frontend/          # React + Vite frontend
├── ffmpeg.exe             # Static Windows FFmpeg binary
├── icon.ico               # Application Icon
└── build.py               # PyInstaller executable builder script
```

### 1. Unified Download Engine (`core/downloader.py`)
Both the web app and the desktop app run the same central function, `download_video`. This function wraps `yt-dlp` and configures output templates, formatting (MP4 video/M4A audio merge, or extraction to MP3), and custom execution paths.
Crucially, it supports callback hooks (`on_progress`, `on_success`, `on_error`, `on_log`) which allow the calling UI to receive real-time stdout and state changes.

### 2. Desktop UI Implementation (`desktop/desktop_app.py`)
Built with `customtkinter`, a modern styled wrapper around Python's standard `tkinter`. It executes the download engine inside a background `threading.Thread` to prevent blocking the Tkinter event loop, posting UI state updates (such as progress bars and logging boxes) using Tkinter's thread-safe `.after()` mechanism.

### 3. Web App Implementation (`web/`)
- **Backend (`web/backend/app.py`):** A `FastAPI` server. It hosts a WebSocket endpoint `/ws/download` which accepts client configurations and runs the core downloading engine. Thread callbacks capture download events and relay them in JSON format down the WebSocket. FastAPI also serves the compiled static React files.
- **Frontend (`web/frontend/`):** A single-page `React` application styled with vanilla CSS. It connects to the FastAPI websocket, handles user configuration inputs, displays a real-time progress bar, and prints scrolling log lines.

---

## 🎨 User Experience (UX) Comparison

### 💻 Standalone Desktop Implementation
- **Visuals:** Native window matching system appearance modes (Light/Dark). The UI features structured entry boxes, dropdown menus, and a progress bar.
- **Interaction Flow:**
  1. Paste YouTube URL.
  2. Choose browser cookie source if needed for private/age-restricted media.
  3. Toggle "Audio Only" if MP3 format is desired.
  4. Click "Download Video".
  5. The program retrieves the user's local operating system `Downloads` folder (e.g., `~/Downloads`) and writes the output file directly.
- **Local Control:** A button to directly open the target directory in the system's native file explorer (`Explorer`, `Finder`, or `xdg-open`).

### 🌐 Browser Web-App Implementation
- **Visuals:** Modern web UI with a clean containerized panel, smooth transitions, and responsive grid layouts.
- **Interaction Flow:**
  1. Open browser to the hosted IP/port.
  2. Input URL and configure options (cookies, audio extract).
  3. Click "Download Video" which opens a WebSocket stream.
  4. The downloading process runs inside the server/Docker container. Files are temporarily written to the configured `/downloads` volume directory on the host machine.
- **Network Agnostic:** Can be hosted on a central server, allowing multiple clients to trigger downloads remotely to a central storage location (e.g., a NAS).

---

## 🚀 Installation & Launch Instructions

### Prerequisites
- **Python 3.10 or higher** (for local execution)
- **Node.js 20+** & **npm** (only if building/developing the web frontend natively without Docker)
- **Docker** (recommended for running the web-app version)

---

### 1. 🆕 NEW WINDOWS INSTALL (Automated Script)

For Windows systems, we provide a unified interactive setup utility to fully automate dependency resolution, environment configuration, launching, and executable packaging.

#### Quick Start
1. Ensure **Python 3.10+** (ensure you check the box to **"Add python.exe to PATH"** during installation) and **Node.js** (for native web) or **Docker Desktop** (for containerized mode) are installed.
2. Run the automated script from the root folder:
   ```cmd
   .\setup_windows.bat
   ```

#### Utility Script Options:
*   **[1] Install Dependencies:** Automatically upgrades pip, installs required python libraries (`customtkinter`, `yt-dlp`, `imageio-ffmpeg`, FastAPI, uvicorn), and installs React node modules.
*   **[2] Launch Desktop App:** Starts the CustomTkinter GUI wrapper natively.
*   **[3] Compile Desktop App:** Bundles all python scripts, icons, and `ffmpeg.exe` into a single standalone portable executable (`.\dist\youtube_downloader.exe`) via PyInstaller.
*   **[4] Run Web Application (Native):** Spins up the backend FastAPI server and frontend Vite server in separate Command Prompt windows.
*   **[5] Run Web Application (Docker):** Builds and runs the Docker Compose container network.

#### FFmpeg Path Resolution on Windows
On Windows, the download engine in `core/downloader.py` utilizes a custom three-tiered FFmpeg resolver:
1.  **Bundled Directory:** Checks if running inside a PyInstaller package (`_MEIPASS`) where `ffmpeg.exe` is bundled.
2.  **System PATH:** Searches the OS environment variable paths for a global `ffmpeg` command.
3.  **Python Wheel:** Falls back to `imageio-ffmpeg`'s precompiled executable binaries.

---

### 2. Standalone Desktop App (Unix / Manual Run)

To run the desktop client manually or on Unix-based systems:

1. **Install python dependencies:**
   ```bash
   pip install customtkinter yt-dlp imageio-ffmpeg
   ```
   *(Note: `imageio-ffmpeg` supplies the necessary `ffmpeg` binary automatically for Linux/macOS).*

2. **Launch the desktop interface:**
   ```bash
   python3 desktop/desktop_app.py
   ```

3. **Build a standalone executable (optional):**
   If you want to package the app into a single executable, first install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
   Then run the build script:
   ```bash
   python3 build.py
   ```
   This uses PyInstaller to bundle dependencies, the system icon, and ffmpeg into the `dist/` directory.

---

### 3. Web Application

#### Option A: Running via Docker (Recommended)
You only need Docker installed.

1. Navigate to the project root.
2. Start the application:
   ```bash
   docker compose -f web/docker-compose.yml up --build -d
   ```
3. Open your browser and navigate to: `http://localhost:8081` (or the configured Traefik rule). Downloads will save to the local `./web/downloads` directory.

> [!WARNING]
> **Windows WSL2 volume permissions:** When deploying on Windows with Docker Desktop, ensure the mapped directory `.\web\downloads` is shareable and has appropriate write permissions in your Docker Desktop Settings -> Resources -> File sharing.

#### Option B: Running Natively (For Development)
You will need two terminals.

**Terminal 1: Frontend Development Server**
```bash
cd web/frontend
npm install
npm run dev
```
*(This starts the Vite dev server at `http://localhost:5173`)*

**Terminal 2: Backend API & WebSocket Server**
```bash
cd web/backend
pip install -r requirements.txt
python3 app.py
```
*(This starts the FastAPI server at `http://localhost:8000`)*

---

### 4. 🦙 Ollama AI Setup & Model Configuration

If you want to use the AI Summarization feature, you must have Ollama running and the appropriate model pulled.

#### Setup Guide
1. **Download Ollama:** Visit [ollama.com](https://ollama.com/) and download the client matching your operating system (Windows, macOS, or Linux).
2. **Install & Start Ollama:** Run the installer and launch the Ollama application so that the background service is running.
3. **Pull Default Models:**
   The application defaults to `llama3:8b` for generating transcript summaries. Pull this model by running the following command in your terminal or Command Prompt:
   ```bash
   ollama pull llama3:8b
   ```
   *Note: If you have a system with limited VRAM or RAM, you can pull a lighter, faster model like `llama3.2:1b` instead:*
   ```bash
   ollama pull llama3.2:1b
   ```
   You can change the active model name directly in the settings panel of the Desktop GUI or the Web interface.

---

## 🎯 Use Cases

- **Offline Media Consumption:** Save educational content, tutorials, or music for offline access.
- **Audio Extraction:** Convert music videos or podcasts directly to high-quality `.mp3` format.
- **Age-Restricted & Private Content Bypass:** When videos require authentication, selecting your default browser (e.g., `chrome`, `firefox`) prompts the downloader to read session cookies, validating access securely without typing passwords.
- **Shared Network Downloader:** Deploy the Docker container on a home server (NAS, Raspberry Pi) to allow anyone on the network to download videos to a centralized repository.

---

## ⚙️ Critical Dependencies

| Dependency | Purpose | Desktop | Web-App |
| :--- | :--- | :---: | :---: |
| **yt-dlp** | Core download library, handles downloading and merging streams | Yes | Yes |
| **FFmpeg** | Required for merging video and audio streams, or converting to MP3 | Yes | Yes |
| **CustomTkinter** | Renders the desktop user interface widgets | Yes | No |
| **FastAPI** | Backend web server and WebSocket broadcaster | No | Yes |
| **Uvicorn** | ASGI server to run the FastAPI app | No | Yes |
| **React & Vite** | Interactive frontend single-page application | No | Yes |
| **Docker** | Containerization tool to bundle backend, frontend, and dependencies | No | Yes |

---

## ⚠️ Disclaimer

This repository may reference, integrate, or build upon third-party software, libraries, frameworks, or tools. Such references do not imply ownership, endorsement, or affiliation with those projects. All third-party software remains the property of its respective authors and is subject to its own license terms.

**Use of any code in this repository is entirely at your own risk.** No warranties, guarantees, or assurances of any kind are provided — express or implied — regarding fitness for purpose, security, reliability, or correctness. The author(s) of this repository accept no liability for any damages, losses, or issues arising from the use of this code or any third-party dependencies it references.

Always review third-party licenses and conduct your own due diligence before using any software in production environments.
