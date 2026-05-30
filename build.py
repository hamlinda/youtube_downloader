import subprocess
import sys
import site

# Ensure user-specific site-packages are added to sys.path in case we do a --user / system-wide install fallback
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
        print("Once installed, please run 'python3 build.py' again to rebuild the application.")
    else:
        print("Please install tkinter for your Python distribution and try again.")
    sys.exit(1)

# List of critical dependencies required to run and build the desktop app
dependencies = ["pyinstaller", "customtkinter", "yt-dlp", "imageio-ffmpeg"]

print("Checking and installing build dependencies...")
for dep in dependencies:
    # Map pip packages containing dashes to import names
    import_name = dep.replace("-", "_")
    try:
        __import__(import_name)
    except ImportError:
        print(f"📦 Installing missing dependency: '{dep}'...")
        try:
            # First try standard install
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ Successfully installed '{dep}'")
        except Exception:
            # If standard install fails (e.g. PEP 668 externally managed environment), retry with system packages override
            print(f"⚠️ Standard install failed. Retrying with --break-system-packages...")
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

# Now import PyInstaller and run the builder
import PyInstaller.__main__

# Use correct path separator for PyInstaller --add-data depending on platform (semicolon for Windows, colon for Unix)
sep = ';' if sys.platform == 'win32' else ':'

print("Starting PyInstaller packaging process...")
PyInstaller.__main__.run([
    'desktop/desktop_app.py',
    '--name=youtube_downloader',
    '--onefile',
    '--windowed',
    '--icon=icon.ico',
    f'--add-data=icon.ico{sep}.',
    f'--add-data=ffmpeg.exe{sep}.',
])
