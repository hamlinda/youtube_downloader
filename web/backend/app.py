import os
import sys
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading

# Add parent directory to sys.path to import core module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.downloader import download_video

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_json(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/download")
async def websocket_download(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        data = await websocket.receive_json()
        url = data.get("url")
        audio_only = data.get("audio_only", False)
        browser = data.get("browser", "None")
        summarize = data.get("summarize", False)
        ollama_url = data.get("ollama_url", "http://localhost:11434")
        ollama_model = data.get("ollama_model", "llama3:8b")

        if not url:
            await manager.send_json({"type": "error", "message": "URL is required"}, websocket)
            manager.disconnect(websocket)
            return

        # Create callbacks that send messages over websocket
        loop = asyncio.get_running_loop()

        def on_progress(d):
            if d['status'] == 'downloading':
                try:
                    percent_str = d.get('_percent_str', '0.0%')
                    import re
                    percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
                    percent = float(percent_str.replace('%', '').strip())
                    speed = d.get('_speed_str', 'N/A')
                    eta = d.get('_eta_str', 'N/A')
                    
                    asyncio.run_coroutine_threadsafe(
                        manager.send_json({
                            "type": "progress",
                            "percent": percent,
                            "speed": speed,
                            "eta": eta
                        }, websocket),
                        loop
                    )
                except Exception:
                    pass

        def on_log(msg):
            asyncio.run_coroutine_threadsafe(
                manager.send_json({"type": "log", "message": msg}, websocket), loop
            )

        def on_success(summary=None, transcript=None):
            payload = {"type": "success", "message": "Download completed!"}
            if summary:
                payload["summary"] = summary
            if transcript:
                payload["transcript"] = transcript
            asyncio.run_coroutine_threadsafe(
                manager.send_json(payload, websocket), loop
            )

        def on_error(err):
            asyncio.run_coroutine_threadsafe(
                manager.send_json({"type": "error", "message": err}, websocket), loop
            )

        # Default web download path (in container this would map to a volume)
        download_path = os.environ.get("DOWNLOAD_DIR", os.path.join(os.path.expanduser('~'), 'Downloads'))
        if not os.path.exists(download_path):
            os.makedirs(download_path, exist_ok=True)
            
        def run_downloader():
            download_video(
                url, 
                download_path, 
                browser, 
                audio_only, 
                on_progress, 
                on_success, 
                on_error, 
                on_log,
                summarize=summarize,
                ollama_url=ollama_url,
                ollama_model=ollama_model
            )

        thread = threading.Thread(target=run_downloader)
        thread.start()

        # Keep websocket alive while downloading
        while thread.is_alive():
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await manager.send_json({"type": "error", "message": str(e)}, websocket)
        manager.disconnect(websocket)

# Mount the static frontend build at the root path
# This assumes the frontend is built into web/frontend/dist
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
