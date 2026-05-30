import os
import sys
import yt_dlp
import traceback

def get_ffmpeg_path():
    try:
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, "ffmpeg.exe")
        else:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

def download_video(url, default_path, browser="None", audio_only=False, 
                   on_progress=None, on_success=None, on_error=None, on_log=None):
    
    def internal_progress_hook(d):
        if on_progress:
            on_progress(d)
        
        if d['status'] == 'finished' and on_log:
            on_log("Download chunk finished, processing file...")

    outtmpl = os.path.join(default_path, '%(title)s.%(ext)s')
    
    if audio_only:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'progress_hooks': [internal_progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
    else:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': outtmpl,
            'progress_hooks': [internal_progress_hook],
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }

    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        ydl_opts['ffmpeg_location'] = ffmpeg_path

    if browser != "None":
        ydl_opts['cookiesfrombrowser'] = (browser,)

    try:
        if on_log:
            on_log("Fetching video info...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if on_success:
            on_success()
            
    except yt_dlp.utils.DownloadError as e:
        if on_error:
            on_error(str(e))
    except Exception as e:
        if on_error:
            on_error(traceback.format_exc())
