import os
import sys
import asyncio
import time
import glob
import shutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading

# Add parent directory to sys.path to import core module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.downloader import download_video, get_ffmpeg_path
from core.summary_engine import DEFAULT_OLLAMA_URL, transcribe_audio, save_summary_files, summarize_transcript

# Default downloads directory (local web/downloads folder relative to workspace, or fallback to user's Downloads)
DEFAULT_DOWNLOADS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "web", "downloads")
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", DEFAULT_DOWNLOADS)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Periodic background cleanup of downloaded/uploaded files older than 24 hours
def start_cleanup_task():
    def cleanup_worker():
        while True:
            try:
                if os.path.exists(DOWNLOAD_DIR):
                    now = time.time()
                    # Find all .mp4 files
                    mp4_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.mp4"))
                    for file_path in mp4_files:
                        mtime = os.path.getmtime(file_path)
                        # 24 hours = 86400 seconds
                        if now - mtime > 24 * 3600:
                            try:
                                os.remove(file_path)
                                print(f"[Cleanup] Deleted expired video: {file_path}")
                                
                                # Clean up associated files if they exist
                                base_name, _ = os.path.splitext(file_path)
                                for ext in ["_transcript.txt", "_summary.txt", ".mp3"]:
                                    assoc_file = base_name + ext
                                    if os.path.exists(assoc_file):
                                        os.remove(assoc_file)
                                        print(f"[Cleanup] Deleted associated file: {assoc_file}")
                            except Exception as e:
                                print(f"[Cleanup] Error deleting {file_path}: {e}")
            except Exception as e:
                print(f"[Cleanup] Error in worker: {e}")
            # Run cleanup check every 10 minutes
            time.sleep(600)

    thread = threading.Thread(target=cleanup_worker, daemon=True)
    thread.start()

@app.on_event("startup")
async def startup_event():
    start_cleanup_task()

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Save the file under its original safe filename
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(DOWNLOAD_DIR, safe_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"filename": safe_filename, "status": "uploaded"}

@app.get("/api/videos")
async def list_videos():
    if not os.path.exists(DOWNLOAD_DIR):
        return []
    
    mp4_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.mp4"))
    videos_list = []
    now = time.time()
    
    for file_path in mp4_files:
        try:
            stat = os.stat(file_path)
            filename = os.path.basename(file_path)
            base_name, _ = os.path.splitext(filename)
            
            created_at = stat.st_mtime
            age = now - created_at
            expires_in = max(0.0, 24 * 3600 - age)
            
            # Check associated files
            has_transcript = os.path.exists(os.path.join(DOWNLOAD_DIR, f"{base_name}_transcript.txt"))
            has_summary = os.path.exists(os.path.join(DOWNLOAD_DIR, f"{base_name}_summary.txt"))
            
            videos_list.append({
                "filename": filename,
                "size": stat.st_size,
                "created_at": created_at,
                "expires_in": expires_in,
                "has_transcript": has_transcript,
                "has_summary": has_summary
            })
        except Exception:
            pass
            
    # Sort by creation time descending (newest first)
    videos_list.sort(key=lambda x: x["created_at"], reverse=True)
    return videos_list

@app.delete("/api/videos/{filename}")
async def delete_video(filename: str):
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(DOWNLOAD_DIR, safe_filename)
    
    if not os.path.exists(file_path):
        return {"status": "error", "message": "File not found"}
        
    try:
        os.remove(file_path)
        # Clean up associated files
        base_name, _ = os.path.splitext(safe_filename)
        for ext in ["_transcript.txt", "_summary.txt", ".mp3"]:
            assoc_file = os.path.join(DOWNLOAD_DIR, base_name + ext)
            if os.path.exists(assoc_file):
                os.remove(assoc_file)
        return {"status": "success", "message": f"Deleted {safe_filename} and associated collateral."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        data = await websocket.receive_json()
        filename = data.get("filename")
        summarize = data.get("summarize", False)
        ollama_url = data.get("ollama_url", DEFAULT_OLLAMA_URL)
        ollama_model = data.get("ollama_model", "llama3:8b")
        
        if not filename:
            await manager.send_json({"type": "error", "message": "Filename is required"}, websocket)
            manager.disconnect(websocket)
            return
            
        safe_filename = os.path.basename(filename)
        video_path = os.path.join(DOWNLOAD_DIR, safe_filename)
        
        if not os.path.exists(video_path):
            await manager.send_json({"type": "error", "message": "File not found on server"}, websocket)
            manager.disconnect(websocket)
            return
            
        loop = asyncio.get_running_loop()
        
        def on_log(msg, is_error=False, *args, **kwargs):
            formatted_msg = f"❌ {msg}" if is_error else msg
            asyncio.run_coroutine_threadsafe(
                manager.send_json({"type": "log", "message": formatted_msg}, websocket), loop
            )
            
        def run_transcription():
            try:
                ffmpeg_path = get_ffmpeg_path()
                if not ffmpeg_path:
                    asyncio.run_coroutine_threadsafe(
                        manager.send_json({"type": "error", "message": "FFmpeg not found! Cannot extract audio for transcription."}, websocket), loop
                    )
                    return
                
                base_path, _ = os.path.splitext(video_path)
                mp3_path = base_path + ".mp3"
                
                on_log("Extracting audio track for transcription...")
                import subprocess
                # Extract to 16kHz mono MP3
                cmd = [ffmpeg_path, "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", "-ab", "128k", "-y", mp3_path]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                on_log(f"Audio extracted successfully: {os.path.basename(mp3_path)}")
                
                # 1. Transcribe audio
                raw_text, formatted_text = transcribe_audio(mp3_path, on_log=on_log)
                transcript = formatted_text
                
                # 2. Summarize (if checked)
                summary = None
                if summarize:
                    summary = summarize_transcript(raw_text, ollama_url=ollama_url, model=ollama_model, on_log=on_log)
                    
                # 3. Save files
                t_file, s_file = save_summary_files(mp3_path, formatted_text, summary or "")
                on_log(f"📝 Saved transcript to: {os.path.basename(t_file)}")
                if summarize and s_file:
                    on_log(f"📝 Saved summary to: {os.path.basename(s_file)}")
                    
                # Clean up intermediate mp3 file
                if os.path.exists(mp3_path):
                    try:
                        os.remove(mp3_path)
                        on_log("Cleaned up temporary audio extraction file.")
                    except Exception:
                        pass
                
                payload = {
                    "type": "success",
                    "message": "Transcription completed!",
                    "transcript": transcript,
                    "transcript_file": os.path.basename(t_file) if t_file else None
                }
                if summarize:
                    payload["summary"] = summary
                    payload["summary_file"] = os.path.basename(s_file) if s_file else None
                    
                asyncio.run_coroutine_threadsafe(
                    manager.send_json(payload, websocket), loop
                )
                
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    manager.send_json({"type": "error", "message": str(e)}, websocket), loop
                )
                
        thread = threading.Thread(target=run_transcription)
        thread.start()
        
        while thread.is_alive():
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await manager.send_json({"type": "error", "message": str(e)}, websocket)
        manager.disconnect(websocket)

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
        ollama_url = data.get("ollama_url", DEFAULT_OLLAMA_URL)
        ollama_model = data.get("ollama_model", "llama3:8b")
        start_time = data.get("start_time") or None
        end_time = data.get("end_time") or None

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

        def on_log(msg, is_error=False, *args, **kwargs):
            formatted_msg = f"❌ {msg}" if is_error else msg
            asyncio.run_coroutine_threadsafe(
                manager.send_json({"type": "log", "message": formatted_msg}, websocket), loop
            )

        def on_success(summary=None, transcript=None, video_file=None, audio_file=None, transcript_file=None, summary_file=None, *args, **kwargs):
            payload = {"type": "success", "message": "Download completed!"}
            if summary:
                payload["summary"] = summary
            if transcript:
                payload["transcript"] = transcript
            if video_file:
                payload["video_file"] = video_file
            if audio_file:
                payload["audio_file"] = audio_file
            if transcript_file:
                payload["transcript_file"] = transcript_file
            if summary_file:
                payload["summary_file"] = summary_file
            asyncio.run_coroutine_threadsafe(
                manager.send_json(payload, websocket), loop
            )

        def on_error(err):
            asyncio.run_coroutine_threadsafe(
                manager.send_json({"type": "error", "message": err}, websocket), loop
            )

        # Default web download path (in container this would map to a volume)
        download_path = DOWNLOAD_DIR
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
                ollama_model=ollama_model,
                start_time=start_time,
                end_time=end_time
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

# Ensure the downloads directory exists and mount it to serve downloaded files
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")

# Mount the static frontend build at the root path
# This assumes the frontend is built into web/frontend/dist
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
