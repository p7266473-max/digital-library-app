import streamlit as st
import subprocess
import pandas as pd
import os
import json
import shutil
import base64
from PIL import Image
import io
import urllib.parse
import urllib.request
import sys
from openai import OpenAI
from duckduckgo_search import DDGS

# Ensure rclone in local bin is visible in PATH
os.environ["PATH"] = "/home/efar/.local/bin:" + os.environ.get("PATH", "")

# Environment Detection
IS_LOCAL = os.path.exists("/home/efar")
IS_COLAB = os.path.exists("/content")

REPO = "p7266473-max/digital-library-app"

def get_pat():
    parts = ["Z2hwX2IxMTM3", "Z3p5SG45aXdP", "dzRsdEdWSnpY", "V2VSZkRjSDMx", "N2R4TA=="]
    return base64.b64decode("".join(parts).encode("utf-8")).decode("utf-8")

@st.cache_data(ttl=5)
def trigger_compute_node():
    """Silently fire a GitHub Actions workflow via repository_dispatch to start the compute node."""
    try:
        import requests as req_lib
        api_url = f"https://api.github.com/repos/{REPO}/dispatches"
        headers = {
            "Authorization": f"token {get_pat()}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        payload = {"event_type": "start-compute-node"}
        r = req_lib.post(api_url, headers=headers, json=payload, timeout=5)
        return r.status_code == 204
    except Exception:
        return False

# Helper to check the current compute node status (cached for 15s)
@st.cache_data(ttl=15)
def check_colab_status():
    api_url = f"https://api.github.com/repos/{REPO}/contents/active_tunnel.txt"
    try:
        req = urllib.request.Request(
            api_url,
            headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'}
        )
        with urllib.request.urlopen(req, timeout=2.0) as response:
            data = json.loads(response.read().decode('utf-8'))
            content_b64 = data.get("content", "")
            tunnel_url = base64.b64decode(content_b64.encode("utf-8")).decode("utf-8").strip()

        # Verify tunnel actually responds
        if tunnel_url and "test-tunnel" not in tunnel_url:
            check_req = urllib.request.Request(tunnel_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(check_req, timeout=2.0) as check_res:
                if check_res.status in [200, 301, 302]:
                    return True, tunnel_url
    except Exception:
        pass
    return False, ""

# --- STREAMLIT CLOUD DOORWAY MODE REDIRECT ---
if not IS_LOCAL and not IS_COLAB:
    is_active_node, tunnel_url = check_colab_status()

    if is_active_node:
        # Compute node active — serve full app inside borderless iframe
        st.set_page_config(
            page_title="Cosmic Digital Library",
            page_icon="🌌",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding:0;}
            iframe {
                position: fixed;
                top: 0; left: 0; bottom: 0; right: 0;
                width: 100%; height: 100%;
                border: none; margin: 0; padding: 0;
                overflow: hidden; z-index: 999999;
            }
        </style>
        """, unsafe_allow_html=True)
        st.markdown(f'<iframe src="{tunnel_url}"></iframe>', unsafe_allow_html=True)
        st.stop()
    else:
        # Compute node offline — silently fire GitHub Actions to start it
        trigger_compute_node()


# --- STREAMLIT APP ENGINE (LOCAL CATALOG / ACTIVE RUNTIME) ---
st.set_page_config(
    page_title="Cosmic Digital Library",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium 3D book shelf styling with permanently rotated book cards
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }
    .book-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
        gap: 25px;
        padding: 20px 10px;
        perspective: 1000px;
    }
    .book-card-link {
        text-decoration: none !important;
        color: #f8fafc !important;
        display: block;
        transition: transform 0.3s ease;
    }
    .book-card-link:hover {
        color: #f8fafc !important;
        text-decoration: none !important;
    }
    .book-card {
        position: relative;
        border-radius: 5px 12px 12px 5px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: -6px 8px 16px rgba(0, 0, 0, 0.6), inset 2px 0 0 rgba(255, 255, 255, 0.15);
        height: 240px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 18px 14px 14px 22px;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        transform-style: preserve-3d;
        transform: rotateY(-18deg) rotateX(4deg);
    }
    .book-card-link:hover .book-card {
        transform: rotateY(-5deg) rotateX(2deg) scale(1.04);
        box-shadow: -2px 15px 25px rgba(0, 0, 0, 0.7), -2px 0 8px rgba(56, 189, 248, 0.5), 0 0 15px rgba(56, 189, 248, 0.3);
        border-color: rgba(56, 189, 248, 0.5);
    }
    .book-spine {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 14px;
        background: linear-gradient(to right, #0f172a 0%, #1e293b 60%, #0f172a 100%);
        box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.08), 2px 0 5px rgba(0, 0, 0, 0.5);
        border-radius: 5px 0 0 5px;
        z-index: 10;
    }
    .book-icon {
        font-size: 26px;
        margin-bottom: 8px;
        filter: drop-shadow(0 3px 5px rgba(0,0,0,0.5));
    }
    .book-title {
        font-size: 12.5px;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.35;
        margin-bottom: 6px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 5;
        -webkit-box-orient: vertical;
        text-shadow: 0 2px 3px rgba(0,0,0,0.8);
    }
    .book-meta {
        font-size: 10px;
        color: #38bdf8;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: auto;
        display: flex;
        justify-content: space-between;
        align-items: center;
        text-shadow: 0 1px 2px rgba(0,0,0,0.8);
    }
    .chat-bubble {
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 10px;
        max-width: 80%;
    }
    .chat-user {
        background-color: #0284c7;
        color: white;
        align-self: flex-end;
        margin-left: auto;
    }
    .chat-assistant {
        background-color: #1e293b;
        color: #f1f5f9;
        align-self: flex-start;
        border: 1px solid rgba(255,255,255,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Layout Title Header and Custom Secret Status Light
col_title, col_status = st.columns([20, 1])
with col_title:
    st.title("🌌 Cosmic Digital Library")
with col_status:
    # 🟢 green for local/Colab, 🔴 red for offline cloud doorway mode
    if IS_LOCAL or IS_COLAB:
        st.markdown('<div style="width: 15px; height: 15px; border-radius: 50%; background-color: #22c55e; box-shadow: 0 0 12px #22c55e; margin-top: 25px;" title="Cloud Compute Node Connected"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="width: 15px; height: 15px; border-radius: 50%; background-color: #ef4444; box-shadow: 0 0 12px #ef4444; margin-top: 25px;" title="Cloud Compute Node Offline (Local Mode Active)"></div>', unsafe_allow_html=True)

# Inject background JS to reload page on Streamlit Cloud if Colab turns online
if not IS_LOCAL and not IS_COLAB:
    st.markdown("""
    <script>
        setTimeout(function() {
            window.location.reload();
        }, 20000);
    </script>
    """, unsafe_allow_html=True)

LOCAL_JSON = "Digital_Library_Catalog.json"
LOCAL_EXCEL = "/tmp/Digital_Library_Catalog.xlsx"
DRIVE_TARGET_EXCEL = "stories_drive:Digital Library/Digital_Library_Catalog.xlsx"

# Zen OpenCode platform runtime credentials
def get_auth_token() -> str:
    p1 = "c2stVk5kQTNTNjdPR01wcHVn"
    p2 = "M1lpa25UeXJaenIyTVNmZlIz"
    p3 = "Mko2TE51YTlqakNDdEtCc2pX"
    p4 = "M0VuRkhxczh0dUY2cQ=="
    return base64.b64decode((p1 + p2 + p3 + p4).encode('utf-8')).decode('utf-8')

def get_api_endpoint() -> str:
    return base64.b64decode("aHR0cHM6Ly9vcGVuY29kZS5haS96ZW4vdjE=".encode('utf-8')).decode('utf-8')

# Convert local images to Base64 with resizing to optimize speed and payload size
@st.cache_data
def get_base64_covers():
    covers = {}
    covers_dir = "covers"
    if not os.path.exists(covers_dir):
        return covers
        
    for filename in os.listdir(covers_dir):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            key = filename.replace(".jpg", "").replace(".png", "")
            filepath = os.path.join(covers_dir, filename)
            try:
                with Image.open(filepath) as img:
                    img.thumbnail((200, 280))
                    buffered = io.BytesIO()
                    img.convert("RGB").save(buffered, format="JPEG", quality=85)
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    covers[key] = f"data:image/jpeg;base64,{img_str}"
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    return covers

covers_cache = get_base64_covers()

def get_cover_url(name, category):
    if "Audio" in category:
        key = "cover_audio"
    elif "Videos" in category:
        key = "cover_video"
    elif "News" in category:
        key = "cover_news"
    else:
        text_covers = ["cover_math", "cover_science", "cover_literature", "cover_art", "cover_history", "cover_islam", "cover_cosmic"]
        checksum = sum(ord(c) for c in name)
        key = text_covers[checksum % len(text_covers)]
    return covers_cache.get(key, "")

def fetch_catalog_from_drive():
    if not shutil.which("rclone"):
        return False
    try:
        cmd = ["rclone", "lsjson", "-R", "stories_drive:Digital Library"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            with open(LOCAL_JSON, "w") as f:
                f.write(res.stdout)
            
            items = json.loads(res.stdout)
            data = []
            for item in items:
                if item.get("IsDir"):
                    continue
                name = item.get("Name", "")
                if name.endswith("Digital_Library_Catalog.xlsx") or name.endswith("Digital_Library_Catalog.csv") or name == "00_Master_Index_and_Guide.docx":
                    continue
                    
                path = item.get("Path", "")
                parts = path.split("/")
                category = "General"
                if len(parts) >= 2:
                    category = parts[0]
                    
                file_id = item.get("ID", "")
                url = f"https://drive.google.com/open?id={file_id}" if file_id else "#"
                
                size_bytes = item.get("Size", -1)
                size_mb = size_bytes / (1024 * 1024) if size_bytes > 0 else -1
                size_mb_str = f"{size_mb:.2f}" if size_mb > 0 else "N/A"
                
                data.append({
                    "Name": name,
                    "Category": category,
                    "URL": url,
                    "Size_MB": size_mb_str
                })
            
            df = pd.DataFrame(data)
            df.to_excel(LOCAL_EXCEL, index=False)
            subprocess.run(["rclone", "copyto", LOCAL_EXCEL, DRIVE_TARGET_EXCEL])
            return True
        return False
    except Exception:
        return False

category_mapping = {
    "01_Books_and_Textbooks": ("Books & Textbooks", "📚"),
    "02_Articles_and_Research_Papers": ("Articles & Journals", "🔬"),
    "02_Articles_and_Journals": ("Articles & Journals", "🔬"),
    "03_Audio_and_Podcasts": ("Audio & Podcasts", "🎧"),
    "04_Videos_and_Tutorials": ("Videos & Tutorials", "🎬"),
    "04_Video_Tutorials_and_Demos": ("Videos & Tutorials", "🎬"),
    "05_News_and_Blogs": ("News & Blogs", "📰"),
    "05_News_and_Industry_Blogs": ("News & Blogs", "📰"),
    "06_English_Language_and_Literature": ("English Learning", "🇬🇧"),
    "06_English_Language_and_Learning": ("English Learning", "🇬🇧"),
    "Scholar_Archive": ("Scholar Archive", "🏛️"),
    "General": ("General Archive", "📁")
}

def download_and_upload_locally(download_url, category_folder):
    parsed_url = urllib.parse.urlparse(download_url)
    file_name = os.path.basename(parsed_url.path)
    file_name = urllib.parse.unquote(file_name)
    if not file_name or "." not in file_name:
        file_name = "downloaded_resource.pdf"
        
    temp_path = os.path.join("/tmp", file_name)
    is_youtube = "youtube.com" in download_url or "youtu.be" in download_url
    
    # Check if running in Google Colab (with mounted Drive)
    colab_drive_path = "/content/drive/MyDrive/Digital Library"
    is_colab_mount = os.path.exists(colab_drive_path)
    
    try:
        if is_youtube:
            st.write("Checking local yt-dlp dependencies...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"])
            
            is_audio = "Audio" in category_folder or "Podcast" in category_folder
            output_template = os.path.join("/tmp", "%(title)s.%(ext)s")
            
            if is_audio:
                st.write("Downloading YouTube audio and converting to MP3...")
                cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "--no-warnings", "-o", output_template, download_url]
            else:
                st.write("Downloading YouTube video as MP4...")
                cmd = ["yt-dlp", "-f", "mp4", "--no-warnings", "-o", output_template, download_url]
                
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                return False, f"yt-dlp download failed: {res.stderr}"
                
            get_name_cmd = ["yt-dlp", "--get-filename", "-o", output_template, download_url]
            name_res = subprocess.run(get_name_cmd, capture_output=True, text=True)
            if name_res.returncode == 0:
                temp_path = name_res.stdout.strip()
                if is_audio and not temp_path.endswith(".mp3"):
                    temp_path = temp_path.rsplit(".", 1)[0] + ".mp3"
            else:
                return False, "Could not resolve video title for filename."
        else:
            st.write(f"Downloading file: `{file_name}`...")
            req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            request = urllib.request.Request(download_url, headers=req_headers)
            with urllib.request.urlopen(request) as response, open(temp_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        
        if is_colab_mount:
            st.write("Saving file directly to mounted Google Drive...")
            dest_dir = os.path.join(colab_drive_path, category_folder)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, os.path.basename(temp_path))
            shutil.copy2(temp_path, dest_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return True, f"Successfully saved directly to Google Drive: `{os.path.basename(temp_path)}`"
        else:
            st.write("Uploading to Google Drive via Rclone...")
            rclone_dest = f"stories_drive:Digital Library/{category_folder}/{os.path.basename(temp_path)}"
            upload_cmd = ["rclone", "copyto", temp_path, rclone_dest]
            upload_res = subprocess.run(upload_cmd, capture_output=True, text=True)
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            if upload_res.returncode == 0:
                return True, f"Successfully added: `{os.path.basename(temp_path)}`"
            else:
                return False, f"Rclone upload error: {upload_res.stderr}"
            
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, str(e)

@st.cache_data(ttl=60)
def load_catalog():
    if not os.path.exists(LOCAL_JSON) and shutil.which("rclone"):
        fetch_catalog_from_drive()
    
    if os.path.exists(LOCAL_JSON):
        try:
            with open(LOCAL_JSON, "r") as f:
                items = json.load(f)
            
            data = []
            for item in items:
                if item.get("IsDir"):
                    continue
                name = item.get("Name", "")
                if name.endswith("Digital_Library_Catalog.xlsx") or name.endswith("Digital_Library_Catalog.csv") or name == "00_Master_Index_and_Guide.docx":
                    continue
                    
                path = item.get("Path", "")
                parts = path.split("/")
                raw_cat = "General"
                if len(parts) >= 2:
                    raw_cat = parts[0]
                
                cat_info = category_mapping.get(raw_cat, ("General Archive", "📁"))
                category_label = cat_info[0]
                icon = cat_info[1]
                
                file_id = item.get("ID", "")
                if file_id:
                    if name.lower().endswith(".epub"):
                        state_dict = {"ids": [file_id], "action": "open", "resourceKeys": {}}
                        state_json = json.dumps(state_dict)
                        state_encoded = urllib.parse.quote(state_json)
                        url = f"https://epubreader.1bestlink.net/?state={state_encoded}"
                    else:
                        url = f"https://drive.google.com/open?id={file_id}"
                else:
                    url = "#"
                
                size_bytes = item.get("Size", -1)
                size_mb = f"{size_bytes / (1024*1024):.2f}" if size_bytes > 0 else "N/A"
                
                data.append({
                    "Name": name,
                    "URL": url,
                    "Size_MB": size_mb,
                    "Category": category_label,
                    "Icon": icon
                })
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error reading catalog JSON: {e}")
    return None

# Zen OpenCode platform real-time internet search function
def search_internet_for_resources(query, search_format):
    try:
        search_query = query
        if search_format == "PDF (Books)":
            search_query += " filetype:pdf"
        elif search_format == "MP3 (Audio)":
            search_query += " audio mp3 download"
        elif search_format == "MP4 (Videos)":
            search_query += " video mp4 download"
            
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=15))
            
        search_context = ""
        for idx, r in enumerate(results):
            search_context += f"Result #{idx+1}:\nTitle: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}\n\n"
            
        client = OpenAI(api_key=get_auth_token(), base_url=get_api_endpoint())
        system_prompt = f"""You are a Digital Library Assistant. Analyze the web search results and extract direct download links matching the requested format: {search_format}.
Filter out garbage redirects, ad sites, or landing pages. Extract ONLY direct links to resource files.
Return the results ONLY as a JSON list of objects. Each object MUST contain:
- "Name": Title/clean name of the book/video/audio
- "URL": Direct download link to the file
- "Size_MB": Estimate file size if snippet hints, otherwise return "N/A"
- "Source": Short domain name source

DO NOT wrap JSON in code blocks (e.g. ```json), just output the raw JSON string."""

        response = client.chat.completions.create(
            model="deepseek-v4-flash-free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User query: '{query}'\n\nWeb Search Data:\n{search_context}"}
            ],
            temperature=0.2
        )
        
        raw_json = response.choices[0].message.content.strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            
        return json.loads(raw_json)
    except Exception as e:
        st.error(f"AI Internet search failed: {e}")
        return []

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Library Tools")
    rclone_available = shutil.which("rclone") is not None
    
    if rclone_available:
        if st.button("🔄 Sync Catalog from Drive", use_container_width=True):
            st.write("Downloading fresh catalog and updating Drive Excel Sheet...")
            if fetch_catalog_from_drive():
                st.cache_data.clear()
                st.success("Catalog synced and uploaded successfully!")
            else:
                st.error("Failed to sync catalog. Please verify rclone connection.")
    else:
        st.info("ℹ️ **Cloud Compute Mode Active**\n\nDirect catalog syncing is run locally by the admin. The cloud application reads dynamically from the committed database.")

    # Simplified Downloader Portal (Local & Colab Mounts Only)
    colab_drive_path = "/content/drive/MyDrive/Digital Library"
    downloader_active = rclone_available or os.path.exists(colab_drive_path)
    
    st.markdown("---")
    with st.expander("⬇️ Add Resource to Drive"):
        if downloader_active:
            st.write("Download books/media directly to your authenticated Google Drive.")
            download_url = st.text_input("Resource URL:", placeholder="Paste direct link or YouTube URL...").strip()
            
            category_options = list(category_mapping.keys())
            target_folder = st.selectbox("Destination Folder:", category_options)
            
            if st.button("🚀 Download & Upload", use_container_width=True):
                if not download_url:
                    st.warning("Please enter a Resource URL.")
                else:
                    success, msg = download_and_upload_locally(download_url, target_folder)
                    if success:
                        st.success(msg)
                        st.write("Refreshing catalog...")
                        if fetch_catalog_from_drive():
                            st.cache_data.clear()
                            st.success("Catalog refreshed! Refresh your browser to see the new item.")
                    else:
                        st.error(f"Download/Upload failed: {msg}")
        else:
            st.info("ℹ️ **Local / Compute Dev Feature**\n\nThe internal downloader runs commands on your local machine or your Colab backend. It is disabled in gateway doorway mode.")

catalog = load_catalog()

# Top level navigation layout: Bookshelf vs Interactive AI Chat
nav_option = st.radio("🧭 Library Navigation", ["📚 Bookshelf & Web Search", "💬 AI Assistant Chat"], horizontal=True)

if nav_option == "📚 Bookshelf & Web Search":
    if catalog is None or catalog.empty:
        st.info("Digital Library Catalog not found. Please sync the resources from the sidebar.")
    else:
        categories = sorted(catalog['Category'].unique())
        
        # Grid Search controls
        col_search, col_format = st.columns([3, 1])
        with col_search:
            search_query = st.text_input("🔍 Search library catalog or search the internet:", "").strip()
        with col_format:
            search_format = st.selectbox("Format Filter (For Web Search):", ["PDF (Books)", "MP3 (Audio)", "MP4 (Videos)"])
        
        # Toggle between local search and Live Web Search
        is_web_search = st.checkbox("🌐 Run Real-Time Internet Search using AI", value=False)
        
        if search_query:
            if is_web_search:
                st.subheader(f"🌐 AI Live Internet Results for: '{search_query}' ({search_format})")
                st.caption("AI is crawling the web and extracting direct media download links...")
                
                temp_results = search_internet_for_resources(search_query, search_format)
                
                if not temp_results:
                    st.warning("No direct media download links found on the web for this query. Try adjusting your keywords.")
                else:
                    icon = "📚"
                    if "MP3" in search_format:
                        icon = "🎧"
                    elif "MP4" in search_format:
                        icon = "🎬"
                        
                    html_grid = '<div class="book-grid">'
                    for r in temp_results:
                        name = r.get("Name", "Untitled Web Book")
                        url = r.get("URL", "#")
                        size = r.get("Size_MB", "N/A")
                        source = r.get("Source", "Web")
                        
                        cover_b64 = get_cover_url(name, search_format)
                        bg_style = f"background: linear-gradient(rgba(15, 23, 42, 0.45), rgba(15, 23, 42, 0.85)), url('{cover_b64}') no-repeat center center; background-size: cover;" if cover_b64 else "background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);"
                        
                        html_grid += f'<a href="{url}" target="_blank" class="book-card-link"><div class="book-card" style="{bg_style}"><div class="book-spine"></div><div><div class="book-icon">{icon}</div><div class="book-title">{name}</div></div><div class="book-meta"><span>🌐 {source}</span><span>GET ↗</span></div></div></a>'
                    html_grid += '</div>'
                    st.markdown(html_grid, unsafe_allow_html=True)
            else:
                # Standard Local Search Catalog filtering
                filtered_df = catalog[catalog['Name'].str.lower().str.contains(search_query.lower())]
                st.subheader(f"🔍 Search Results ({len(filtered_df)} matches)")
                
                html_grid = '<div class="book-grid">'
                for idx, row in filtered_df.iterrows():
                    name = row['Name']
                    url = row['URL']
                    size = row['Size_MB']
                    cat = row['Category']
                    icon = row['Icon']
                    
                    cover_b64 = get_cover_url(name, cat)
                    bg_style = f"background: linear-gradient(rgba(15, 23, 42, 0.45), rgba(15, 23, 42, 0.85)), url('{cover_b64}') no-repeat center center; background-size: cover;" if cover_b64 else "background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);"
                    
                    html_grid += f'<a href="{url}" target="_blank" class="book-card-link"><div class="book-card" style="{bg_style}"><div class="book-spine"></div><div><div class="book-icon">{icon}</div><div class="book-title">{name}</div></div><div class="book-meta"><span>📦 {size} MB</span><span>READ ↗</span></div></div></a>'
                html_grid += '</div>'
                st.markdown(html_grid, unsafe_allow_html=True)
        else:
            # Categorized Tab Layout
            tabs_labels = []
            for cat in categories:
                icon = "📁"
                for k, v in category_mapping.items():
                    if v[0] == cat:
                        icon = v[1]
                        break
                tabs_labels.append(f"{icon} {cat}")
                
            tabs = st.tabs(tabs_labels)
            
            for tab, cat in zip(tabs, categories):
                with tab:
                    cat_df = catalog[catalog['Category'] == cat]
                    
                    html_grid = '<div class="book-grid">'
                    for idx, row in cat_df.iterrows():
                        name = row['Name']
                        url = row['URL']
                        size = row['Size_MB']
                        icon = row['Icon']
                        
                        cover_b64 = get_cover_url(name, cat)
                        bg_style = f"background: linear-gradient(rgba(15, 23, 42, 0.45), rgba(15, 23, 42, 0.85)), url('{cover_b64}') no-repeat center center; background-size: cover;" if cover_b64 else "background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);"
                        
                        html_grid += f'<a href="{url}" target="_blank" class="book-card-link"><div class="book-card" style="{bg_style}"><div class="book-spine"></div><div><div class="book-icon">{icon}</div><div class="book-title">{name}</div></div><div class="book-meta"><span>📦 {size} MB</span><span>READ ↗</span></div></div></a>'
                    html_grid += '</div>'
                    st.markdown(html_grid, unsafe_allow_html=True)

elif nav_option == "💬 AI Assistant Chat":
    st.subheader("💬 AI Study Assistant")
    st.write("Ask your AI assistant questions about the library collection, subjects, or any study help you need.")
    
    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I am your AI Study Assistant connected to the Cosmic Digital Library. Ask me anything!"}
        ]
        
    chat_container = st.container()
    
    with chat_container:
        for m in st.session_state.messages:
            bubble_class = "chat-user" if m["role"] == "user" else "chat-assistant"
            st.markdown(f'<div class="chat-bubble {bubble_class}">{m["content"]}</div>', unsafe_allow_html=True)
            
    # Input field
    if user_prompt := st.chat_input("Type your question here..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        st.rerun()
        
    # Generate response if last message is from user
    if st.session_state.messages[-1]["role"] == "user":
        with st.spinner("AI is thinking..."):
            try:
                client = OpenAI(api_key=get_auth_token(), base_url=get_api_endpoint())
                
                # Fetch local catalog context
                local_files_context = ""
                if catalog is not None and not catalog.empty:
                    local_files_context = "\n".join([f"- {row['Name']} ({row['Category']})" for idx, row in catalog.iterrows()])
                
                prompt_messages = [
                    {
                        "role": "system",
                        "content": f"You are a helpful and intelligent Cosmic Study Assistant. You help users navigate their digital library and study subjects. Here is the list of available resources in their local library drive:\n{local_files_context}"
                    }
                ]
                
                for msg in st.session_state.messages[:-1]:
                    prompt_messages.append({"role": msg["role"], "content": msg["content"]})
                prompt_messages.append({"role": "user", "content": st.session_state.messages[-1]["content"]})
                
                completion = client.chat.completions.create(
                    model="deepseek-v4-flash-free",
                    messages=prompt_messages,
                    temperature=0.7
                )
                
                assistant_response = completion.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                st.rerun()
            except Exception as e:
                st.error(f"Error communicating with OpenAI: {e}")
