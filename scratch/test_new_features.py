import requests
import os

BASE_URL = "http://localhost:8000"

def test_upload_list_delete():
    # 1. Create a dummy MP4 file for testing
    dummy_filename = "test_upload_file.mp4"
    with open(dummy_filename, "wb") as f:
        f.write(b"dummy mp4 video content for testing")
        
    print(f"Created temporary dummy file: {dummy_filename}")
    
    try:
        # 2. Test POST /api/upload
        print("Testing POST /api/upload...")
        with open(dummy_filename, "rb") as f:
            files = {"file": (dummy_filename, f, "video/mp4")}
            response = requests.post(f"{BASE_URL}/api/upload", files=files)
            
        print("Upload Response status:", response.status_code)
        print("Upload Response JSON:", response.json())
        assert response.status_code == 200
        assert response.json()["filename"] == dummy_filename
        
        # 3. Test GET /api/videos
        print("\nTesting GET /api/videos...")
        response = requests.get(f"{BASE_URL}/api/videos")
        print("List Response status:", response.status_code)
        videos = response.json()
        print("Saved Videos:")
        found_test_file = False
        for video in videos:
            print(f"- {video['filename']}: {video['size']} bytes, expires_in {video['expires_in']:.1f}s")
            if video["filename"] == dummy_filename:
                found_test_file = True
                assert video["size"] == len(b"dummy mp4 video content for testing")
                assert video["expires_in"] > 0
                
        assert found_test_file, "Uploaded test file was not found in the videos list!"
        
        # 4. Test DELETE /api/videos/{filename}
        print(f"\nTesting DELETE /api/videos/{dummy_filename}...")
        response = requests.delete(f"{BASE_URL}/api/videos/{dummy_filename}")
        print("Delete Response status:", response.status_code)
        print("Delete Response JSON:", response.json())
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify it is deleted
        response = requests.get(f"{BASE_URL}/api/videos")
        videos = response.json()
        found_test_file_after_delete = False
        for video in videos:
            if video["filename"] == dummy_filename:
                found_test_file_after_delete = True
        assert not found_test_file_after_delete, "Uploaded test file was still found after deletion!"
        
        print("\n✅ All REST endpoint tests passed successfully!")
        
    finally:
        # Clean up local file
        if os.path.exists(dummy_filename):
            os.remove(dummy_filename)

if __name__ == "__main__":
    test_upload_list_delete()
