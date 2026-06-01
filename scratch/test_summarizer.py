import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.summary_engine import format_time, save_summary_files
from core.downloader import download_video, get_ffmpeg_path

class TestVideoSummarization(unittest.TestCase):
    
    def test_format_time(self):
        self.assertEqual(format_time(0), "00:00")
        self.assertEqual(format_time(61), "01:01")
        self.assertEqual(format_time(3605), "60:05")

    def test_save_summary_files_path_traversal_safety(self):
        # We test that path traversal characters are properly sanitized
        malicious_mp3_path = "/home/dlh/Downloads/../../../etc/passwd.mp3"
        transcript = "This is a transcript."
        summary = "This is a summary."
        
        with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            # We call save_summary_files, which should resolve base_name safely
            t_path, s_path = save_summary_files(malicious_mp3_path, transcript, summary)
            
            # The directory should be extracted safely, but the filename is sanitized via os.path.basename
            # malicious_mp3_path's dirname is /home/dlh/Downloads/../../../etc
            # and the basename is passwd.mp3 (with passwd as base_name)
            # The final paths should be:
            # transcript: /home/dlh/Downloads/../../../etc/passwd_transcript.txt
            # summary: /home/dlh/Downloads/../../../etc/passwd_summary.txt
            # This ensures that even if we try to inject relative traversal in the filename, 
            # os.path.basename extracts just "passwd.mp3" preventing traversal to files like "/etc/passwd_transcript.txt"
            
            self.assertTrue(t_path.endswith("passwd_transcript.txt"))
            self.assertTrue(s_path.endswith("passwd_summary.txt"))
            
            # Verify file write operations were called
            mock_file.assert_any_call(t_path, "w", encoding="utf-8")
            mock_file.assert_any_call(s_path, "w", encoding="utf-8")

    @patch("core.downloader.yt_dlp.YoutubeDL")
    @patch("core.downloader.get_ffmpeg_path")
    @patch("subprocess.run")
    @patch("core.summary_engine.transcribe_audio")
    @patch("core.summary_engine.summarize_transcript")
    @patch("core.summary_engine.save_summary_files")
    def test_download_video_with_summarize(self, mock_save, mock_summarize, mock_transcribe, mock_sub_run, mock_ffmpeg, mock_ytdl):
        # Set up mocks
        mock_ffmpeg.return_value = "/usr/bin/ffmpeg"
        mock_transcribe.return_value = ("Raw text", "Formatted text")
        mock_summarize.return_value = "Summary text"
        mock_save.return_value = ("t.txt", "s.txt")
        
        # Mock yt-dlp downloader behavior
        instance = mock_ytdl.return_value.__enter__.return_value
        instance.extract_info.return_value = {"title": "Test Video"}
        instance.prepare_filename.return_value = "/home/dlh/Downloads/Test Video.mp4"
        
        # Patch check_dependencies to avoid installing on test
        with patch("core.summary_engine.check_dependencies") as mock_check_deps, \
             patch("os.path.exists") as mock_exists:
            
            mock_exists.side_effect = lambda path: True if path in ["/usr/bin/ffmpeg", "/home/dlh/Downloads/Test Video.mp4", "/home/dlh/Downloads/Test Video.mp3"] else False
            
            success_mock = MagicMock()
            log_mock = MagicMock()
            
            # Trigger download
            download_video(
                url="https://youtube.com/watch?v=123",
                default_path="/home/dlh/Downloads",
                browser="None",
                audio_only=False,
                on_success=success_mock,
                on_log=log_mock,
                summarize=True
            )
            
            # Assert FFmpeg was run to extract audio (since audio_only=False and summarize=True)
            mock_sub_run.assert_called_once()
            cmd_run = mock_sub_run.call_args[0][0]
            self.assertIn("/usr/bin/ffmpeg", cmd_run)
            self.assertIn("/home/dlh/Downloads/Test Video.mp4", cmd_run)
            self.assertIn("/home/dlh/Downloads/Test Video.mp3", cmd_run)
            
            # Assert transcription was triggered
            mock_transcribe.assert_called_once_with("/home/dlh/Downloads/Test Video.mp3", on_log=log_mock)
            
            # Assert summary was triggered
            mock_summarize.assert_called_once_with("Raw text", ollama_url="http://localhost:11434", model="llama3:8b", on_log=log_mock)
            
            # Assert save files was triggered
            mock_save.assert_called_once_with("/home/dlh/Downloads/Test Video.mp3", "Formatted text", "Summary text")
            
            # Assert success callback got the summary & transcript
            success_mock.assert_called_once_with(summary="Summary text", transcript="Formatted text")

if __name__ == "__main__":
    unittest.main()
