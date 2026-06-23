import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.downloader import download_video

def main():
    url = "https://www.youtube.com/watch?v=mrwaFv7Ajuc"
    download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
    os.makedirs(download_dir, exist_ok=True)
    
    print("Testing download...")
    
    def on_progress(d):
        if d['status'] == 'downloading':
            print(f"Progress: {d.get('_percent_str', 'N/A')}", end='\r')
            
    def on_success(**kwargs):
        print("\nSuccess! Downloaded files:")
        for k, v in kwargs.items():
            print(f"  {k}: {v}")
            
    def on_error(err):
        print(f"\nError: {err}")
        
    def on_log(msg, *args, **kwargs):
        print(f"Log: {msg}")

    download_video(
        url=url,
        default_path=download_dir,
        browser="None",
        audio_only=False,
        on_progress=on_progress,
        on_success=on_success,
        on_error=on_error,
        on_log=on_log,
        summarize=False
    )

if __name__ == "__main__":
    main()
