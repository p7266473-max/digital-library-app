import streamlit as st
import subprocess
import pandas as pd
import os
import json
import shutil

# Ensure rclone in local bin is visible in PATH
os.environ["PATH"] = "/home/efar/.local/bin:" + os.environ.get("PATH", "")

st.set_page_config(
    page_title="Cosmic Digital Library",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium 3D book widget styling
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }
    .book-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 30px;
        padding: 20px 0;
    }
    .book-card {
        position: relative;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 6px 16px 16px 6px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4), inset 3px 0 0 rgba(255, 255, 255, 0.1);
        height: 320px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 24px 20px 20px 28px;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        transform-style: preserve-3d;
        perspective: 1000px;
    }
    .book-card:hover {
        transform: rotateY(-12deg) translateY(-8px);
        box-shadow: 15px 20px 30px rgba(0, 0, 0, 0.5), -2px 0 5px rgba(56, 189, 248, 0.3), 0 0 15px rgba(56, 189, 248, 0.1);
        border-color: rgba(56, 189, 248, 0.3);
    }
    .book-spine {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 14px;
        background: linear-gradient(to right, #0f172a 0%, #1e293b 60%, #0f172a 100%);
        box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.08), 2px 0 5px rgba(0, 0, 0, 0.4);
        border-radius: 6px 0 0 6px;
        z-index: 10;
    }
    .book-icon {
        font-size: 32px;
        margin-bottom: 12px;
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.3));
    }
    .book-title {
        font-size: 14px;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.4;
        margin-bottom: 8px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 5;
        -webkit-box-orient: vertical;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    .book-meta {
        font-size: 11px;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: auto;
    }
    .book-btn {
        margin-top: 14px;
        background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
        color: #0f172a !important;
        font-weight: 800;
        text-align: center;
        padding: 8px 12px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 12px;
        box-shadow: 0 4px 8px rgba(56, 189, 248, 0.2);
        transition: all 0.2s ease;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        width: 100%;
        box-sizing: border-box;
    }
    .book-btn:hover {
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        box-shadow: 0 6px 12px rgba(56, 189, 248, 0.35);
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

st.title("🌌 Cosmic Digital Library")
st.write("Lightweight metadata catalog with direct high-speed Google Drive access.")

LOCAL_JSON = "Digital_Library_Catalog.json"
LOCAL_EXCEL = "/tmp/Digital_Library_Catalog.xlsx"
DRIVE_TARGET_EXCEL = "stories_drive:Digital Library/Digital_Library_Catalog.xlsx"

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
        
        # Render search result grid with 3D Book Cover style
        html_grid = '<div class="book-grid">'
        for idx, row in filtered_df.iterrows():
            name = row['Name']
            url = row['URL']
            size = row['Size_MB']
            cat = row['Category']
            icon = row['Icon']
            
            # Single-line HTML string representing the 3D book cover card
            html_grid += f'<div class="book-card"><div class="book-spine"></div><div><div class="book-icon">{icon}</div><div class="book-title">{name}</div></div><div><div class="book-meta">📦 {size} MB | 📁 {cat}</div><a href="{url}" target="_blank" class="book-btn">🔗 Read Book</a></div></div>'
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
                
                # Render grid with 3D Book Cover style
                html_grid = '<div class="book-grid">'
                for idx, row in cat_df.iterrows():
                    name = row['Name']
                    url = row['URL']
                    size = row['Size_MB']
                    icon = row['Icon']
                    
                    # Single-line HTML string representing the 3D book cover card
                    html_grid += f'<div class="book-card"><div class="book-spine"></div><div><div class="book-icon">{icon}</div><div class="book-title">{name}</div></div><div><div class="book-meta">📦 {size} MB</div><a href="{url}" target="_blank" class="book-btn">🔗 Read Book</a></div></div>'
                html_grid += '</div>'
                st.markdown(html_grid, unsafe_allow_html=True)
