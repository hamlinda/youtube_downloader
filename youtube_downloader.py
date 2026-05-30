import subprocess
import sys
import os
import site

# Ensure user-specific site-packages are added to sys.path in case we do a --user install fallback
try:
    user_site = site.getusersitepackages()
    site.addsitedir(user_site)
except Exception:
    pass

# Check if tkinter (standard Python GUI library) is installed.
# On Linux, this is a system package and cannot be installed via pip.
try:
    import tkinter
except ImportError:
    print("\n❌ ERROR: 'tkinter' is missing from your Python installation.")
    if sys.platform.startswith("linux"):
        print("On Linux, tkinter is a system dependency. Please install it using your package manager:")
        print("\n    sudo apt-get install python3-tk\n")
    else:
        print("Please install tkinter for your Python distribution.")
    sys.exit(1)

# List of critical dependencies required to run the app
dependencies = ["customtkinter", "yt-dlp", "imageio-ffmpeg"]

for dep in dependencies:
    # Map pip packages containing dashes to import names
    import_name = dep.replace("-", "_")
    try:
        __import__(import_name)
    except ImportError:
        print(f"📦 Installing missing runtime dependency: '{dep}'...")
        try:
            # First try standard install
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ Successfully installed '{dep}'")
        except Exception:
            # Fallback to system-wide Packages override if PEP 668 is active
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", dep])
                print(f"✅ Successfully installed '{dep}' (system-wide)")
            except Exception as e:
                print(f"❌ Error installing '{dep}': {e}")
                sys.exit(1)

# Ensure paths are refreshed again after installations
try:
    site.addsitedir(site.getusersitepackages())
except Exception:
    pass

import customtkinter as ctk
import yt_dlp
import threading
import traceback

try:
    if hasattr(sys, "_MEIPASS"):
        FFMPEG_PATH = os.path.join(sys._MEIPASS, "ffmpeg.exe")
    else:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = None

# Set up appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Video Downloader")
        self.geometry("600x550")
        self.minsize(500, 450)

        icon_path = "icon.ico"
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "icon.ico")
        
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        # Title Label
        self.title_label = ctk.CTkLabel(self.main_frame, text="YouTube Video Downloader", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(10, 20))

        # URL Input
        self.url_label = ctk.CTkLabel(self.main_frame, text="YouTube URL:")
        self.url_label.pack(anchor="w", padx=10)
        self.url_entry = ctk.CTkEntry(self.main_frame, placeholder_text="https://www.youtube.com/watch?v=...", width=400)
        self.url_entry.pack(fill=ctk.X, padx=10, pady=(0, 15))

        # Authentication Options
        self.auth_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.auth_frame.pack(fill=ctk.X, padx=10, pady=(0, 15))
        
        self.auth_label = ctk.CTkLabel(self.auth_frame, text="Authentication (Browser Cookies):")
        self.auth_label.pack(side=ctk.LEFT, padx=(0, 10))
        
        self.browsers = ["None", "chrome", "firefox", "edge", "opera", "safari", "vivaldi", "brave"]
        self.auth_dropdown = ctk.CTkOptionMenu(self.auth_frame, values=self.browsers)
        self.auth_dropdown.pack(side=ctk.LEFT)

        # Download Path
        self.path_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.path_frame.pack(fill=ctk.X, padx=10, pady=(0, 20))
        
        self.default_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.path_label = ctk.CTkLabel(self.path_frame, text=f"Save to: {self.default_path}", text_color="gray")
        self.path_label.pack(side=ctk.LEFT)

        self.open_folder_btn = ctk.CTkButton(self.path_frame, text="Open Folder", width=100, height=24, command=self.open_download_folder)
        self.open_folder_btn.pack(side=ctk.LEFT, padx=(20, 0))

        # Download Options
        self.audio_only_var = ctk.BooleanVar(value=False)
        self.audio_checkbox = ctk.CTkCheckBox(self.main_frame, text="Audio Only (MP3)", variable=self.audio_only_var)
        self.audio_checkbox.pack(pady=(0, 10))

        # Download Button
        self.download_button = ctk.CTkButton(self.main_frame, text="Download Video", command=self.start_download)
        self.download_button.pack(pady=(0, 20))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.pack(fill=ctk.X, padx=10, pady=(0, 10))
        self.progress_bar.set(0)
        
        # Status Label
        self.status_label = ctk.CTkLabel(self.main_frame, text="Ready", text_color="gray")
        self.status_label.pack(pady=(0, 5))

        # Log Text Box
        self.log_box = ctk.CTkTextbox(self.main_frame, height=100)
        self.log_box.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_box.configure(state="disabled")

        self.download_thread = None

    def open_download_folder(self):
        try:
            if sys.platform == 'win32':
                os.startfile(self.default_path)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.Popen(['open', self.default_path])
            else:
                import subprocess
                subprocess.Popen(['xdg-open', self.default_path])
        except Exception as e:
            self.log(f"Error opening folder: {e}", is_error=True)

    def log(self, message, is_error=False):
        self.log_box.configure(state="normal")
        self.log_box.insert(ctk.END, message + "\n")
        self.log_box.see(ctk.END)
        self.log_box.configure(state="disabled")
        if is_error:
            self.status_label.configure(text="Error occurred", text_color="red")
        else:
            self.status_label.configure(text=message, text_color="gray")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                # _percent_str might have ansi escape codes
                percent_str = d.get('_percent_str', '0.0%')
                # Clean up ansi codes if present
                import re
                percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
                percent = float(percent_str.replace('%', '').strip())
                self.progress_bar.set(percent / 100.0)
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                self.status_label.configure(text=f"Downloading: {percent:.1f}% at {speed} ETA: {eta}", text_color="white")
            except Exception as e:
                pass
        elif d['status'] == 'finished':
            self.progress_bar.set(1.0)
            self.status_label.configure(text="Download complete, finalizing...", text_color="green")
            self.log("Download chunk finished, processing file...")

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log("Error: Please enter a YouTube URL.", is_error=True)
            return

        if self.download_thread and self.download_thread.is_alive():
            self.log("Error: A download is already in progress.", is_error=True)
            return

        browser = self.auth_dropdown.get()
        audio_only = self.audio_only_var.get()
        
        self.download_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", ctk.END)
        self.log_box.configure(state="disabled")
        self.log(f"Starting download for: {url}")
        if browser != "None":
            self.log(f"Using {browser} cookies for authentication.")

        self.download_thread = threading.Thread(target=self.download_worker, args=(url, browser, audio_only), daemon=True)
        self.download_thread.start()

    def download_worker(self, url, browser, audio_only):
        outtmpl = os.path.join(self.default_path, '%(title)s.%(ext)s')
        
        if audio_only:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': outtmpl,
                'progress_hooks': [self.progress_hook],
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
                'progress_hooks': [self.progress_hook],
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
            }

        if FFMPEG_PATH:
            ydl_opts['ffmpeg_location'] = FFMPEG_PATH

        if browser != "None":
            ydl_opts['cookiesfrombrowser'] = (browser,)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log("Fetching video info...")
                ydl.download([url])
            
            self.after(0, self.download_finished_success)
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            self.after(0, lambda msg=error_msg: self.download_finished_error(msg))
        except Exception as e:
            error_msg = traceback.format_exc()
            self.after(0, lambda msg=error_msg: self.download_finished_error(msg))

    def download_finished_success(self):
        self.log("Download successfully completed!")
        self.status_label.configure(text="Download Finished!", text_color="green")
        self.download_button.configure(state="normal")

    def download_finished_error(self, error_message):
        self.log("=== ERROR OCCURRED ===", is_error=True)
        self.log(error_message, is_error=True)
        
        # Provide actionable advice based on common errors
        if "Sign in to confirm your age" in error_message or "age-restricted" in error_message:
            self.log("\nACTIONABLE ADVICE: This video is age-restricted. Please select your primary browser from the 'Authentication' dropdown (where you are logged into YouTube) and try again.")
        elif "members-only content" in error_message:
            self.log("\nACTIONABLE ADVICE: This is a members-only video. Please select your primary browser from the 'Authentication' dropdown and ensure you are logged into an account that has membership access.")
        elif "Private video" in error_message:
             self.log("\nACTIONABLE ADVICE: This is a private video. Ensure you have access and are logged in via the selected browser.")
        elif "Requested format is not available" in error_message:
             self.log("\nACTIONABLE ADVICE: The requested video format is not available for this video.")
        elif "cookies" in error_message.lower() or "cookie database" in error_message.lower():
             self.log("\nACTIONABLE ADVICE: There was an issue reading cookies from your browser. Chrome/Edge restrict cookie access. Try these solutions:\n"
                      "1. Fully close the browser (ensure it's not running in the system tray) and try again.\n"
                      "2. Use Firefox instead (select 'firefox' from the dropdown) as it does not lock cookies in the same way.\n"
                      "3. Ensure the browser is installed in the default location.")
             
        self.download_button.configure(state="normal")

if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
