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
                   on_progress=None, on_success=None, on_error=None, on_log=None,
                   summarize=False, ollama_url="http://localhost:11434", ollama_model="llama3:8b"):
    
    def internal_progress_hook(d):
        if on_progress:
            on_progress(d)
        
        if d['status'] == 'finished' and on_log:
            on_log("Download chunk finished, processing file...")

    # If summarize is requested, we need ffmpeg. Force check it early.
    ffmpeg_path = get_ffmpeg_path()
    if summarize and not ffmpeg_path:
        if on_error:
            on_error("FFmpeg not found! Cannot extract audio for transcription.")
        return

    outtmpl = os.path.join(default_path, '%(title)s.%(ext)s')
    
    # If summarize is True but audio_only is False, we download video, then extract MP3.
    # So we don't change ydl_opts formats, we let yt-dlp run as requested by the user.
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

    if ffmpeg_path:
        ydl_opts['ffmpeg_location'] = ffmpeg_path

    if browser != "None":
        ydl_opts['cookiesfrombrowser'] = (browser,)

    try:
        if on_log:
            on_log("Fetching video info...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            prepared_filename = ydl.prepare_filename(info)
        
        # Determine downloaded paths
        base_path, _ = os.path.splitext(prepared_filename)
        mp3_path = None
        
        if audio_only:
            mp3_path = base_path + ".mp3"
            if not os.path.exists(mp3_path) and os.path.exists(prepared_filename):
                mp3_path = prepared_filename
        else:
            video_path = base_path + ".mp4"
            if not os.path.exists(video_path) and os.path.exists(prepared_filename):
                video_path = prepared_filename
                
            if summarize:
                mp3_path = base_path + ".mp3"
                if on_log:
                    on_log("Extracting audio track for transcription...")
                
                import subprocess
                # Extract to 16kHz mono MP3 for optimal transcription
                cmd = [ffmpeg_path, "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", "-ab", "128k", "-y", mp3_path]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if on_log:
                    on_log(f"Audio extracted successfully: {os.path.basename(mp3_path)}")

        summary = None
        transcript = None
        
        if summarize and mp3_path and os.path.exists(mp3_path):
            from core.summary_engine import transcribe_audio, summarize_transcript, save_summary_files
            
            # 1. Transcribe audio
            raw_text, formatted_text = transcribe_audio(mp3_path, on_log=on_log)
            transcript = formatted_text
            
            # 2. Summarize
            summary = summarize_transcript(raw_text, ollama_url=ollama_url, model=ollama_model, on_log=on_log)
            
            # 3. Save files
            t_file, s_file = save_summary_files(mp3_path, formatted_text, summary)
            if on_log:
                on_log(f"📝 Saved transcript to: {os.path.basename(t_file)}")
                on_log(f"📝 Saved summary to: {os.path.basename(s_file)}")
                
            # Clean up intermediate mp3 file if it was a video download
            if not audio_only and os.path.exists(mp3_path):
                try:
                    os.remove(mp3_path)
                    if on_log:
                        on_log("Cleaned up temporary audio extraction file.")
                except Exception:
                    pass

        if on_success:
            # Pass summary and transcript back
            on_success(summary=summary, transcript=transcript)
            
    except yt_dlp.utils.DownloadError as e:
        if on_error:
            on_error(str(e))
    except Exception as e:
        if on_error:
            on_error(traceback.format_exc())

