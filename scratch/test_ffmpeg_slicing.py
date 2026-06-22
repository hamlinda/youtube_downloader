import os
import subprocess
import shutil

def verify_ffmpeg_slicing():
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
            
    if not ffmpeg_path:
        print("❌ FFmpeg not found in PATH or imageio_ffmpeg!")
        return

    input_file = "test_slicing_input.mp4"
    output_file = "test_slicing_output.mp4"
    
    try:
        # 1. Generate a dummy 5-second valid video using FFmpeg
        print("Generating mock 5-second video...")
        cmd_gen = [
            ffmpeg_path, "-y", 
            "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=30", 
            "-c:v", "libx264", "-pix_fmt", "yuv420p", input_file
        ]
        subprocess.run(cmd_gen, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("Mock video generated successfully.")
        
        # 2. Slice from 00:02 to 00:04 (2 seconds duration)
        print("Testing FFmpeg slice command (-ss 2 to 4)...")
        cmd_slice = [
            ffmpeg_path, "-y", "-i", input_file,
            "-ss", "00:00:02", "-to", "00:00:04",
            "-c", "copy", output_file
        ]
        subprocess.run(cmd_slice, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        assert os.path.exists(output_file), "Output file was not created!"
        
        # 3. Check duration of the sliced output file
        print("Checking sliced video duration using ffprobe...")
        ffprobe_path = shutil.which("ffprobe")
        if ffprobe_path:
            cmd_probe = [
                ffprobe_path, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", output_file
            ]
            duration_str = subprocess.check_output(cmd_probe).decode("utf-8").strip()
            duration = float(duration_str)
            print(f"Sliced video duration: {duration} seconds")
            # Durations can slightly vary based on keyframes, but it should be around 2.0 seconds
            assert 1.5 <= duration <= 2.5, f"Unexpected sliced duration: {duration}s"
            print("✅ Duration verification passed!")
        else:
            print("⚠️ ffprobe not found, skipping duration check (output file exists).")
            
        print("✅ FFmpeg slicing test complete! All checks passed.")
        
    finally:
        # Clean up files
        for f in [input_file, output_file]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    verify_ffmpeg_slicing()
