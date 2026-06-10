import os
import sys
import logging
import traceback
import socket

logger = logging.getLogger(__name__)

def get_platform_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

PLATFORM_IP = get_platform_ip()
DEFAULT_OLLAMA_URL = f"http://{PLATFORM_IP}:11434"


def check_dependencies(on_log=None):
    """
    Check if required packages for transcription and summarization are installed.
    Installs them on-demand if missing.
    """
    for dep in ["faster-whisper", "requests"]:
        import_name = dep.replace("-", "_")
        try:
            __import__(import_name)
        except ImportError:
            if on_log:
                on_log(f"📦 Installing missing dependency: '{dep}' for summarization...")
            else:
                print(f"📦 Installing missing dependency: '{dep}'...")
            
            import subprocess
            try:
                # Standard pip install
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                if on_log:
                    on_log(f"✅ Successfully installed '{dep}'")
            except Exception:
                try:
                    # Fallback for PEP 668 managed environments
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", dep])
                    if on_log:
                        on_log(f"✅ Successfully installed '{dep}' (system-wide)")
                except Exception as e:
                    err_msg = f"❌ Error installing '{dep}': {e}"
                    if on_log:
                        on_log(err_msg, is_error=True)
                    raise RuntimeError(err_msg)

def format_time(seconds):
    """Format seconds into MM:SS format."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def transcribe_audio(audio_path, model_size="base", on_log=None):
    """
    Transcribe the MP3 file using faster-whisper.
    Returns a tuple of (full_raw_text, formatted_text_with_timestamps).
    """
    # Ensure dependencies are loaded
    check_dependencies(on_log)
    
    from faster_whisper import WhisperModel
    
    if on_log:
        on_log(f"Loading Whisper model '{model_size}' (running on CPU, INT8)...")
    
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        if on_log:
            on_log("Whisper model loaded. Transcribing audio...")
        
        segments_gen, info = model.transcribe(audio_path, beam_size=5)
        if on_log:
            on_log(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
            
        raw_segments = []
        formatted_segments = []
        
        for segment in segments_gen:
            text = segment.text.strip()
            if text:
                raw_segments.append(text)
                time_str = f"[{format_time(segment.start)} - {format_time(segment.end)}]"
                formatted_segments.append(f"{time_str} {text}")
                
        full_raw_text = " ".join(raw_segments)
        formatted_text = "\n".join(formatted_segments)
        
        if on_log:
            on_log(f"Transcription finished successfully. Character count: {len(full_raw_text)}")
        return full_raw_text, formatted_text
        
    except Exception as e:
        err_msg = f"Error during Whisper transcription: {e}"
        if on_log:
            on_log(err_msg, is_error=True)
        # Log traceback detail
        logger.error(traceback.format_exc())
        return f"Transcription Error: {e}", f"Transcription Error: {e}"

def call_ollama_api(prompt, ollama_url, model):
    import requests
    url = f"{ollama_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    result = response.json()
    return result.get("response", "No response from model.")

def chunk_text(text, max_chars=12000):
    lines = text.split("\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
    for line in lines:
        if current_length + len(line) + 1 > max_chars:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line) + 1
            
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    return chunks

def summarize_transcript(transcript_text, ollama_url=DEFAULT_OLLAMA_URL, model="llama3:8b", on_log=None):
    """
    Summarize transcript text using a local Ollama instance.
    """
    check_dependencies(on_log)
    
    if not transcript_text.strip() or transcript_text.startswith("Transcription Error:"):
        return "Cannot summarize: Transcript is empty or transcription failed."
        
    chunks = chunk_text(transcript_text, max_chars=12000)
    
    try:
        if len(chunks) == 1:
            if on_log:
                on_log(f"Requesting summary from Ollama at {ollama_url} (model: {model})...")
            
            prompt = (
                "Please summarize the following video transcription. "
                "Highlight key points, main topics, and actionable take-aways:\n\n"
                f"Transcript:\n{chunks[0]}"
            )
            summary = call_ollama_api(prompt, ollama_url, model)
            if on_log:
                on_log("Summary generated successfully.")
            return summary
            
        # Multiple chunks
        if on_log:
            on_log(f"Transcript is large ({len(transcript_text)} chars). Splitting into {len(chunks)} chunks for summarization...")
            
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            if on_log:
                on_log(f"Requesting summary for section {i+1}/{len(chunks)} from Ollama...")
            prompt = (
                f"Please summarize this section of the video transcription:\n\n"
                f"{chunk}"
            )
            summary = call_ollama_api(prompt, ollama_url, model)
            chunk_summaries.append(summary)
            
        if on_log:
            on_log("Consolidating section summaries into final summary...")
            
        combined_summaries = "\n\n".join(
            [f"Summary of Section {i+1}:\n{s}" for i, s in enumerate(chunk_summaries)]
        )
        
        final_prompt = (
            "Please combine and consolidate the following section summaries of a video transcript "
            "into a single, cohesive final summary. Highlight the key points, main topics, and actionable take-aways:\n\n"
            f"{combined_summaries}"
        )
        
        final_summary = call_ollama_api(final_prompt, ollama_url, model)
        if on_log:
            on_log("Final summary generated successfully.")
        return final_summary
        
    except Exception as e:
        err_msg = f"Error communicating with local Ollama server: {e}"
        if on_log:
            on_log(err_msg, is_error=True)
        return f"Summarization Error: Make sure your Ollama URL {ollama_url} is correct, the server is running, and the model '{model}' is installed."

def save_summary_files(mp3_path, transcript_content, summary_content):
    """
    Safely save transcript and summary text files.
    """
    # Retrieve directory and base filename
    directory = os.path.dirname(mp3_path)
    base_name = os.path.splitext(os.path.basename(mp3_path))[0]
    
    # Sanitize base_name using os.path.basename to prevent path traversal
    safe_base = os.path.basename(base_name)
    
    transcript_path = os.path.join(directory, f"{safe_base}_transcript.txt")
    summary_path = os.path.join(directory, f"{safe_base}_summary.txt")
    
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_content)
        
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_content)
        
    return transcript_path, summary_path
