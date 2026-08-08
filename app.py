import streamlit as st
import subprocess
import pandas as pd
import os
import json
import shutil
import base64
from PIL import Image
import io
import requests
import urllib.parse

# Ensure rclone in local bin is visible in PATH
os.environ["PATH"] = "/home/efar/.local/bin:" + os.environ.get("PATH", "")

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
</style>
""", unsafe_allow_html=True)

st.title("🌌 Cosmic Digital Library")
st.write("Lightweight metadata catalog with direct high-speed Google Drive access.")

LOCAL_JSON = "Digital_Library_Catalog.json"
LOCAL_EXCEL = "/tmp/Digital_Library_Catalog.xlsx"
DRIVE_TARGET_EXCEL = "stories_drive:Digital Library/Digital_Library_Catalog.xlsx"
TUNNEL_CONFIG = "colab_tunnel.txt"

# Persist Colab Tunnel URL across sessions
def load_tunnel_url():
    if os.path.exists(TUNNEL_CONFIG):
        try:
            with open(TUNNEL_CONFIG, "r") as f:
                return f.read().strip()
        except:
            pass
    return ""

def save_tunnel_url(url):
    try:
        with open(TUNNEL_CONFIG, "w") as f:
            f.write(url.strip())
    except:
        pass

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
                url = f"https://drive.google.com/open?id={file_id}" if file_id else "#"
                
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

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Library Tools")
    if shutil.which("rclone"):
        if st.button("🔄 Sync Catalog from Drive", use_container_width=True):
            st.write("Downloading fresh catalog and updating Drive Excel Sheet...")
            if fetch_catalog_from_drive():
                st.cache_data.clear()
                st.success("Catalog synced and uploaded successfully!")
            else:
                st.error("Failed to sync catalog. Please verify rclone connection.")
    else:
        st.info("ℹ️ **Cloud Mode Active**\n\nAuto-sync via Rclone is disabled in the cloud. To update library items, run the app locally, click Sync, and push the updated `Digital_Library_Catalog.json` to GitHub.")

    # Persistent Colab Connection Configuration
    st.markdown("---")
    with st.expander("⚙️ Colab Server Settings"):
        current_tunnel = load_tunnel_url()
        colab_url = st.text_input("Colab Tunnel URL:", value=current_tunnel, placeholder="https://xxx.trycloudflare.com").strip()
        if colab_url != current_tunnel:
            save_tunnel_url(colab_url)
            st.toast("Colab Tunnel URL saved!", icon="💾")

    # Simplified Downloader Portal
    with st.expander("⬇️ Colab Downloader"):
        st.write("Stream books directly to Google Drive via Colab.")
        download_url = st.text_input("Book Download URL:", placeholder="Paste direct download link...").strip()
        
        category_options = list(category_mapping.keys())
        target_folder = st.selectbox("Destination Folder:", category_options)
        
        if st.button("🚀 Start Cloud Download", use_container_width=True):
            if not colab_url:
                st.warning("Please configure your Colab Tunnel URL first in the 'Colab Server Settings' section above.")
            elif "youtube.com" in colab_url or "youtu.be" in colab_url:
                st.error("⚠️ **Invalid Configuration:** You entered a YouTube URL in the **Colab Tunnel URL** field. Please paste your Cloudflare Tunnel URL (e.g. `https://xxx.trycloudflare.com`) in the **Colab Server Settings** expander, and put your YouTube link in the **Book Download URL** field.")
            elif not download_url:
                st.warning("Please enter a Book Download URL.")
            else:
                # Automatically extract filename from the download URL path
                parsed_url = urllib.parse.urlparse(download_url)
                file_name = os.path.basename(parsed_url.path)
                file_name = urllib.parse.unquote(file_name)
                
                # Fallback if URL doesn't have a clear filename
                if not file_name or "." not in file_name:
                    file_name = "downloaded_resource.pdf"
                
                api_url = f"{colab_url.rstrip('/')}/download"
                st.write(f"Streaming request to Colab for: `{file_name}`...")
                
                try:
                    payload = {
                        "download_url": download_url,
                        "category_folder": target_folder,
                        "file_name": file_name
                    }
                    response = requests.post(api_url, json=payload, timeout=120)
                    
                    if response.status_code == 200:
                        res_data = response.json()
                        if res_data.get("status") == "success":
                            st.success(f"🎉 Success!\n\n{res_data.get('message')}\n\nRefreshed library will show the book once you sync.")
                        else:
                            st.error(f"Error: {res_data.get('message')}")
                    else:
                        st.error(f"Colab service returned status code {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection to Colab failed. Verify your Tunnel URL is active and typed correctly. Details: {e}")

catalog = load_catalog()

if catalog is None or catalog.empty:
    st.info("Digital Library Catalog not found. Please sync the resources from the sidebar.")
else:
    categories = sorted(catalog['Category'].unique())
    
    # Global search
    search_query = st.text_input("🔍 Search books, audio, and video files:", "").strip().lower()
    
    if search_query:
        filtered_df = catalog[catalog['Name'].str.lower().str.contains(search_query)]
        st.subheader(f"🔍 Search Results ({len(filtered_df)} matches)")
        
        # Render search result grid with clickable 3D Book Cover cards with cover artwork
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
                
                # Render grid with clickable 3D Book Cover cards with cover artwork
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
