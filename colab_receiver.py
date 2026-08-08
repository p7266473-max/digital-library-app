# ==============================================================================
# GOOGLE COLAB DOWNLOADER RECEIVER SCRIPT
# ==============================================================================
# Instructions:
# 1. Open Google Colab (https://colab.research.google.com) and create a new notebook.
# 2. Copy and paste this entire code block into a single code cell.
# 3. Run the cell. Follow the prompt to authorize Google Drive access.
# 4. Once it starts, it will print a public Cloudflare URL (e.g. https://xxx.trycloudflare.com).
# 5. Copy that URL and paste it into the "Colab Downloader Portal" in your Streamlit sidebar.
# ==============================================================================

# 1. Mount Google Drive
from google.colab import drive
import os
print("Mounting Google Drive...")
drive.mount('/content/drive')

# Ensure the target Digital Library root exists
drive_path = "/content/drive/MyDrive/Digital Library"
os.makedirs(drive_path, exist_ok=True)
print(f"Verified target root: {drive_path}")

# 2. Install FastAPI, Uvicorn, and Cloudflared dependencies
print("Installing dependencies...")
!pip install -q fastapi uvicorn pydantic requests nest-asyncio
print("Downloading Cloudflare Tunnel binary...")
!curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
!dpkg -i cloudflared.deb

# 3. Define FastAPI App
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import threading
import nest_asyncio
import requests

# Enable running uvicorn inside Jupyter environments
nest_asyncio.apply()

app = FastAPI(title="Colab Book Downloader Service")

class DownloadRequest(BaseModel):
    download_url: str
    category_folder: str
    file_name: str

@app.post("/download")
def download_file(req: DownloadRequest):
    # Map the folder path
    target_dir = os.path.join(drive_path, req.category_folder)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, req.file_name)
    print(f"\n[INCOMING] Request to download: {req.download_url}")
    print(f"[TARGET] Saving to: {file_path}")
    
    try:
        # Run wget inside Colab for high-speed download
        cmd = ["wget", "-q", "--show-progress", "-O", file_path, req.download_url]
        # Run process and wait for completion
        process = subprocess.run(cmd, capture_output=True)
        
        if process.returncode == 0:
            print(f"[SUCCESS] Download completed for: {req.file_name}")
            return {"status": "success", "message": f"Successfully downloaded and saved: {req.file_name}"}
        else:
            err_msg = process.stderr.decode()
            print(f"[ERROR] wget failed: {err_msg}")
            raise HTTPException(status_code=500, detail=f"Download failed: {err_msg}")
    except Exception as e:
        print(f"[EXCEPTION] Failed to process download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 4. Start Background Cloudflare Tunnel
def start_cloudflare_tunnel():
    print("Starting Cloudflare Tunnel...")
    # Cloudflared will output logs to stdout. We parse it to find the trycloudflare.com URL.
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    url_found = False
    for line in proc.stdout:
        if "trycloudflare.com" in line:
            parts = line.split()
            for part in parts:
                if "trycloudflare.com" in part and part.startswith("https://"):
                    print("\n" + "="*70)
                    print("🚀 COLAB DOWNLOADER RECEIVER IS RUNNING SUCCESSFULLY!")
                    print(f"YOUR TUNNEL URL: {part.strip()}")
                    print("Copy the URL above and paste it in the Streamlit Sidebar Downloader.")
                    print("="*70 + "\n")
                    url_found = True
                    break
            if url_found:
                break

# Run tunnel thread
tunnel_thread = threading.Thread(target=start_cloudflare_tunnel, daemon=True)
tunnel_thread.start()

# 5. Run FastAPI Server (blocking)
print("Starting FastAPI web service on port 8000...")
uvicorn.run(app, host="127.0.0.1", port=8000)
