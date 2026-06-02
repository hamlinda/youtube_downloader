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

# List of critical dependencies required to run the desktop app
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
import threading

# Add the parent directory to sys.path so we can import 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.downloader import download_video

# Set up appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Video Downloader")
        self.geometry("650x650")
        self.minsize(550, 550)

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
        self.title_label.pack(pady=(10, 10))

        # Tabview
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)
        
        self.download_tab = self.tabview.add("Download")
        self.summary_tab = self.tabview.add("AI Summary & Settings")

        # === DOWNLOAD TAB ===
        # URL Input
        self.url_label = ctk.CTkLabel(self.download_tab, text="YouTube URL:")
        self.url_label.pack(anchor="w", padx=10, pady=(10, 0))
        self.url_entry = ctk.CTkEntry(self.download_tab, placeholder_text="https://www.youtube.com/watch?v=...", width=400)
        self.url_entry.pack(fill=ctk.X, padx=10, pady=(0, 15))

        # Authentication Options
        self.auth_frame = ctk.CTkFrame(self.download_tab, fg_color="transparent")
        self.auth_frame.pack(fill=ctk.X, padx=10, pady=(0, 15))
        
        self.auth_label = ctk.CTkLabel(self.auth_frame, text="Authentication (Browser Cookies):")
        self.auth_label.pack(side=ctk.LEFT, padx=(0, 10))
        
        self.browsers = ["None", "chrome", "firefox", "edge", "opera", "safari", "vivaldi", "brave"]
        self.auth_dropdown = ctk.CTkOptionMenu(self.auth_frame, values=self.browsers)
        self.auth_dropdown.pack(side=ctk.LEFT)

        # Download Path
        self.path_frame = ctk.CTkFrame(self.download_tab, fg_color="transparent")
        self.path_frame.pack(fill=ctk.X, padx=10, pady=(0, 20))
        
        self.default_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.path_label = ctk.CTkLabel(self.path_frame, text=f"Save to: {self.default_path}", text_color="gray")
        self.path_label.pack(side=ctk.LEFT)

        self.open_folder_btn = ctk.CTkButton(self.path_frame, text="Open Folder", width=100, height=24, command=self.open_download_folder)
        self.open_folder_btn.pack(side=ctk.LEFT, padx=(20, 0))

        # Download Options Frame
        self.options_frame = ctk.CTkFrame(self.download_tab, fg_color="transparent")
        self.options_frame.pack(fill=ctk.X, padx=10, pady=(0, 15))

        self.audio_only_var = ctk.BooleanVar(value=False)
        self.audio_checkbox = ctk.CTkCheckBox(self.options_frame, text="Audio Only (MP3)", variable=self.audio_only_var)
        self.audio_checkbox.pack(side=ctk.LEFT, padx=(0, 20))

        self.summarize_var = ctk.BooleanVar(value=False)
        self.summarize_checkbox = ctk.CTkCheckBox(self.options_frame, text="Summarize Video (via AI)", variable=self.summarize_var)
        self.summarize_checkbox.pack(side=ctk.LEFT)

        # Download Button
        self.download_button = ctk.CTkButton(self.download_tab, text="Download Video", command=self.start_download)
        self.download_button.pack(pady=(0, 15))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.download_tab)
        self.progress_bar.pack(fill=ctk.X, padx=10, pady=(0, 10))
        self.progress_bar.set(0)
        
        # Status Label
        self.status_label = ctk.CTkLabel(self.download_tab, text="Ready", text_color="gray")
        self.status_label.pack(pady=(0, 5))

        # Log Text Box
        self.log_box = ctk.CTkTextbox(self.download_tab, height=120)
        self.log_box.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_box.configure(state="disabled")

        # === AI SUMMARY & SETTINGS TAB ===
        # Settings group
        self.settings_frame = ctk.CTkFrame(self.summary_tab, fg_color="transparent")
        self.settings_frame.pack(fill=ctk.X, padx=10, pady=(10, 10))
        
        self.ollama_url_label = ctk.CTkLabel(self.settings_frame, text="Ollama URL:")
        self.ollama_url_label.pack(side=ctk.LEFT, padx=(0, 5))
        self.ollama_url_entry = ctk.CTkEntry(self.settings_frame, width=180)
        self.ollama_url_entry.insert(0, "http://localhost:11434")
        self.ollama_url_entry.pack(side=ctk.LEFT, padx=(0, 15))
        
        self.ollama_model_label = ctk.CTkLabel(self.settings_frame, text="Model:")
        self.ollama_model_label.pack(side=ctk.LEFT, padx=(0, 5))
        self.ollama_model_entry = ctk.CTkEntry(self.settings_frame, width=120)
        self.ollama_model_entry.insert(0, "llama3:8b")
        self.ollama_model_entry.pack(side=ctk.LEFT)

        # AI Summary Area
        self.summary_label = ctk.CTkLabel(self.summary_tab, text="AI Summary:", font=ctk.CTkFont(weight="bold"))
        self.summary_label.pack(anchor="w", padx=10, pady=(5, 2))
        self.summary_box = ctk.CTkTextbox(self.summary_tab, height=150)
        self.summary_box.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.summary_box.configure(state="disabled")

        # Transcript Area
        self.transcript_label = ctk.CTkLabel(self.summary_tab, text="Full Transcript (with timestamps):", font=ctk.CTkFont(weight="bold"))
        self.transcript_label.pack(anchor="w", padx=10, pady=(5, 2))
        self.transcript_box = ctk.CTkTextbox(self.summary_tab, height=150)
        self.transcript_box.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.transcript_box.configure(state="disabled")

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
        # Must be called from main thread, use .after if needed but for log it usually works or we wrap it
        self.after(0, self._log_internal, message, is_error)
        
    def _log_internal(self, message, is_error):
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
                import re
                percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
                percent = float(percent_str.replace('%', '').strip())
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                self.after(0, self._update_progress_ui, percent / 100.0, f"Downloading: {percent:.1f}% at {speed} ETA: {eta}")
            except Exception as e:
                pass

    def _update_progress_ui(self, percent, text):
        self.progress_bar.set(percent)
        self.status_label.configure(text=text, text_color="white")

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
        summarize = self.summarize_var.get()
        ollama_url = self.ollama_url_entry.get().strip()
        ollama_model = self.ollama_model_entry.get().strip()
        
        self.download_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", ctk.END)
        self.log_box.configure(state="disabled")
        
        # Clear summary and transcript boxes
        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", ctk.END)
        self.summary_box.configure(state="disabled")
        
        self.transcript_box.configure(state="normal")
        self.transcript_box.delete("1.0", ctk.END)
        self.transcript_box.configure(state="disabled")

        self.log(f"Starting download for: {url}")
        if browser != "None":
            self.log(f"Using {browser} cookies for authentication.")

        self.download_thread = threading.Thread(
            target=self.download_worker, 
            args=(url, browser, audio_only, summarize, ollama_url, ollama_model), 
            daemon=True
        )
        self.download_thread.start()

    def download_worker(self, url, browser, audio_only, summarize, ollama_url, ollama_model):
        download_video(
            url=url,
            default_path=self.default_path,
            browser=browser,
            audio_only=audio_only,
            on_progress=self.progress_hook,
            on_success=self.download_finished_success,
            on_error=self.download_finished_error,
            on_log=self.log,
            summarize=summarize,
            ollama_url=ollama_url,
            ollama_model=ollama_model
        )

    def download_finished_success(self, summary=None, transcript=None, *args, **kwargs):
        self.after(0, self._success_ui, summary, transcript)
        
    def _success_ui(self, summary=None, transcript=None, *args, **kwargs):
        self.log("Download successfully completed!")
        self.progress_bar.set(1.0)
        self.status_label.configure(text="Download Finished!", text_color="green")
        self.download_button.configure(state="normal")
        
        if summary:
            self.summary_box.configure(state="normal")
            self.summary_box.insert(ctk.END, summary)
            self.summary_box.configure(state="disabled")
            
        if transcript:
            self.transcript_box.configure(state="normal")
            self.transcript_box.insert(ctk.END, transcript)
            self.transcript_box.configure(state="disabled")
            
        if summary or transcript:
            try:
                self.tabview.set("AI Summary & Settings")
            except Exception:
                pass


    def download_finished_error(self, error_message):
        self.after(0, self._error_ui, error_message)
        
    def _error_ui(self, error_message):
        self.log("=== ERROR OCCURRED ===", is_error=True)
        self.log(error_message, is_error=True)
        
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
