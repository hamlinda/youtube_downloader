import sys
import os

# Ensure the root directory is in sys.path so desktop_app can find core modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from desktop.desktop_app import YouTubeDownloaderApp

if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
